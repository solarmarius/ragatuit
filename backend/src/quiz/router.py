from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.auth.dependencies import CurrentUser
from src.canvas.dependencies import CanvasToken
from src.database import SessionDep
from src.exceptions import ServiceError
from src.logging_config import get_logger

from .constants import ERROR_MESSAGES, SUCCESS_MESSAGES
from .dependencies import (
    QuizOwnership,
    QuizOwnershipWithLock,
    validate_content_extraction_ready,
    validate_export_ready,
    validate_question_generation_ready,
    validate_quiz_has_approved_questions,
)
from .flows import (
    quiz_content_extraction_flow,
    quiz_export_background_flow,
    quiz_question_generation_flow,
)
from .models import Quiz
from .schemas import QuizCreate
from .service import (
    create_quiz,
    delete_quiz,
    get_user_quizzes,
    prepare_content_extraction,
    prepare_question_generation,
)

router = APIRouter(prefix="/quiz", tags=["quiz"])
logger = get_logger("quiz")


@router.post("/", response_model=Quiz)
async def create_new_quiz(
    quiz_data: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> Quiz:
    """
    Create a new quiz with the specified settings.

    Creates a quiz with Canvas course integration, module selection, and LLM configuration.
    The quiz is associated with the authenticated user as the owner.

    **Parameters:**
        quiz_data (QuizCreate): Quiz creation data including:
            - canvas_course_id: Canvas course ID
            - canvas_course_name: Canvas course name
            - selected_modules: Dict mapping module IDs to names
            - title: Quiz title
            - question_count: Number of questions to generate (1-200, default 100)
            - llm_model: LLM model to use (default "o3")
            - llm_temperature: LLM temperature setting (0.0-2.0, default 1)

    **Returns:**
        Quiz: The created quiz object with generated UUID and timestamps

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 400 if quiz data is invalid
        HTTPException: 500 if database operation fails

    **Example Request:**
        ```json
        {
            "canvas_course_id": 12345,
            "canvas_course_name": "Introduction to AI",
            "selected_modules": {"173467": "Machine Learning Basics"},
            "title": "AI Fundamentals Quiz",
            "question_count": 50,
            "llm_model": "gpt-4o",
            "llm_temperature": 1
        }
        ```
    """
    logger.info(
        "quiz_creation_initiated",
        user_id=str(current_user.id),
        canvas_id=current_user.canvas_id,
        canvas_course_id=quiz_data.canvas_course_id,
        question_count=quiz_data.question_count,
        llm_model=quiz_data.llm_model,
    )

    try:
        quiz = create_quiz(session, quiz_data, current_user.id)

        # Trigger content extraction in the background
        background_tasks.add_task(
            quiz_content_extraction_flow,
            quiz.id,
            quiz_data.canvas_course_id,
            [int(module_id) for module_id in quiz_data.selected_modules.keys()],
            canvas_token,
        )

        logger.info(
            "quiz_creation_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            canvas_course_id=quiz_data.canvas_course_id,
            question_count=quiz_data.question_count,
        )

        return quiz

    except Exception as e:
        logger.error(
            "quiz_creation_failed",
            user_id=str(current_user.id),
            canvas_course_id=quiz_data.canvas_course_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["creation_failed"])


@router.get("/{quiz_id}", response_model=Quiz)
def get_quiz(quiz: QuizOwnership) -> Quiz:
    """
    Retrieve a quiz by its ID.

    Returns the quiz details if the authenticated user is the owner.
    Includes all quiz settings, Canvas course information, and selected modules.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz to retrieve

    **Returns:**
        Quiz: The quiz object with all details

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if quiz not found or user doesn't own it
        HTTPException: 500 if database operation fails

    **Example Response:**
        ```json
        {
            "id": "12345678-1234-5678-9abc-123456789abc",
            "owner_id": "87654321-4321-8765-cba9-987654321abc",
            "canvas_course_id": 12345,
            "canvas_course_name": "Introduction to AI",
            "selected_modules": "{\"173467\": \"Machine Learning Basics\"}",
            "title": "AI Fundamentals Quiz",
            "question_count": 50,
            "llm_model": "gpt-4o",
            "llm_temperature": 1,
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z"
        }
        ```
    """
    return quiz


@router.get("/", response_model=list[Quiz])
def get_user_quizzes_endpoint(
    current_user: CurrentUser,
    session: SessionDep,
) -> list[Quiz]:
    """
    Retrieve all quizzes created by the authenticated user.

    Returns a list of all quizzes owned by the current user, ordered by creation date
    (most recent first). Each quiz includes full details including settings and metadata.

    **Returns:**
        List[Quiz]: List of quiz objects owned by the user

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 500 if database operation fails

    **Example Response:**
        ```json
        [
            {
                "id": "12345678-1234-5678-9abc-123456789abc",
                "owner_id": "87654321-4321-8765-cba9-987654321abc",
                "canvas_course_id": 12345,
                "canvas_course_name": "Introduction to AI",
                "selected_modules": "{\"173467\": \"Machine Learning Basics\"}",
                "title": "AI Fundamentals Quiz",
                "question_count": 50,
                "llm_model": "gpt-4o",
                "llm_temperature": 1,
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z"
            }
        ]
        ```
    """
    logger.info(
        "user_quizzes_retrieval_initiated",
        user_id=str(current_user.id),
    )

    try:
        quizzes = get_user_quizzes(session, current_user.id)

        logger.info(
            "user_quizzes_retrieval_completed",
            user_id=str(current_user.id),
            quiz_count=len(quizzes),
        )

        return quizzes

    except ServiceError:
        # Service errors are automatically handled by global handlers
        raise
    except Exception as e:
        logger.error(
            "user_quizzes_retrieval_failed",
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["retrieval_failed"])


@router.post("/{quiz_id}/extract-content")
async def trigger_content_extraction(
    quiz: QuizOwnershipWithLock,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """
    Manually trigger content extraction for a quiz.

    This endpoint allows users to retry content extraction if it failed
    or trigger extraction manually. It can be called multiple times.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz to extract content for

    **Returns:**
        dict: Status message indicating extraction has been triggered

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if quiz not found or user doesn't own it
        HTTPException: 409 if extraction already in progress
        HTTPException: 500 if unable to trigger extraction
    """
    logger.info(
        "manual_content_extraction_triggered",
        user_id=str(current_user.id),
        quiz_id=str(quiz.id),
    )

    try:
        # Validate quiz status
        validate_content_extraction_ready(quiz)

        # Prepare extraction using service layer
        extraction_params = prepare_content_extraction(
            session, quiz.id, current_user.id
        )

        # Trigger content extraction in the background
        background_tasks.add_task(
            quiz_content_extraction_flow,
            quiz.id,
            extraction_params["course_id"],
            extraction_params["module_ids"],
            canvas_token,
        )

        logger.info(
            "manual_content_extraction_started",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            module_count=len(extraction_params["module_ids"]),
        )

        return {"message": SUCCESS_MESSAGES["content_extraction_started"]}

    except ValueError as e:
        logger.warning(
            "manual_extraction_validation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            error=str(e),
        )
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(
            "manual_content_extraction_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=ERROR_MESSAGES["extraction_trigger_failed"]
        )


@router.delete("/{quiz_id}", response_model=None)
def delete_quiz_endpoint(
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> None:
    """
    Delete a quiz by its ID.

    **⚠️ DESTRUCTIVE OPERATION ⚠️**

    Permanently removes a quiz and all its associated data from the system.
    This action cannot be undone. Only the quiz owner can delete their own quizzes.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz to delete

    **Returns:**
        Message: Confirmation message that the quiz was deleted

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if quiz not found or user doesn't own it
        HTTPException: 500 if database operation fails

    **Usage:**
        DELETE /api/v1/quiz/{quiz_id}
        Authorization: Bearer <jwt_token>

    **Example Response:**
        ```json
        {
            "message": "Quiz deleted successfully"
        }
        ```

    **Data Removed:**
    - Quiz record and all settings
    - Extracted content data
    - Quiz metadata and timestamps
    - Progress tracking information

    **Security:**
    - Only quiz owners can delete their own quizzes
    - Ownership verification prevents unauthorized deletions
    - Comprehensive audit logging for deletion events

    **Note:**
    This operation is permanent. The quiz cannot be recovered after deletion.
    """
    logger.info(
        "quiz_deletion_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
    )

    try:
        success = delete_quiz(session, quiz_id, current_user.id)

        if not success:
            logger.warning(
                "quiz_deletion_failed_not_found_or_unauthorized",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(
                status_code=404, detail=ERROR_MESSAGES["quiz_not_found"]
            )

        logger.info(
            "quiz_deletion_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "quiz_deletion_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["deletion_failed"])


@router.post("/{quiz_id}/generate-questions")
async def trigger_question_generation(
    quiz: QuizOwnership,
    current_user: CurrentUser,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """
    Manually trigger question generation for a quiz.

    This endpoint allows users to trigger question generation after content
    extraction is complete. It uses the quiz's existing LLM settings.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz to generate questions for

    **Returns:**
        dict: Status message indicating generation has been triggered

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if quiz not found or user doesn't own it
        HTTPException: 400 if content extraction not completed
        HTTPException: 409 if question generation already in progress
        HTTPException: 500 if unable to trigger generation
    """
    logger.info(
        "manual_question_generation_triggered",
        user_id=str(current_user.id),
        quiz_id=str(quiz.id),
    )

    try:
        # Validate quiz status
        validate_question_generation_ready(quiz)

        # Prepare generation using service layer
        generation_params = prepare_question_generation(
            session, quiz.id, current_user.id
        )

        # Trigger question generation in the background
        background_tasks.add_task(
            quiz_question_generation_flow,
            quiz.id,
            generation_params["question_count"],
            generation_params["llm_model"],
            generation_params["llm_temperature"],
        )

        logger.info(
            "manual_question_generation_started",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            question_count=generation_params["question_count"],
            llm_model=generation_params["llm_model"],
        )

        return {"message": SUCCESS_MESSAGES["question_generation_started"]}

    except ValueError as e:
        logger.warning(
            "manual_generation_validation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            error=str(e),
        )

        # Map ValueError to appropriate HTTP status
        if "Content extraction must be completed" in str(e):
            status_code = 400
        else:
            status_code = 409

        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(
            "manual_question_generation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=ERROR_MESSAGES["generation_trigger_failed"]
        )


@router.get("/{quiz_id}/questions/stats")
async def get_quiz_question_stats(
    quiz: QuizOwnership,
    current_user: CurrentUser,
    session: SessionDep,  # noqa: ARG001
) -> dict[str, int]:
    """
    Get question statistics for a quiz.

    Returns the total number of questions and approved questions for the quiz.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz to get stats for

    **Returns:**
        dict: Dictionary with 'total' and 'approved' question counts

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if quiz not found or user doesn't own it
        HTTPException: 500 if database operation fails
    """
    logger.info(
        "question_stats_retrieval_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz.id),
    )

    try:
        # Get question counts
        from src.question.di import get_container
        from src.question.services import QuestionPersistenceService

        container = get_container()
        persistence_service = container.resolve(QuestionPersistenceService)
        full_stats = await persistence_service.get_question_statistics(quiz_id=quiz.id)

        # Convert to expected format for backward compatibility
        stats = {
            "total": full_stats["total_questions"],
            "approved": full_stats["approved_questions"],
        }

        logger.info(
            "question_stats_retrieval_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            total_questions=stats["total"],
            approved_questions=stats["approved"],
        )

        return stats

    except Exception as e:
        logger.error(
            "question_stats_retrieval_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES["stats_retrieval_failed"],
        )


@router.post("/{quiz_id}/export")
async def export_quiz_to_canvas(
    quiz: QuizOwnership,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """
    Export a quiz to Canvas LMS.

    Triggers background export of the quiz to Canvas. Only the quiz owner can export
    their own quizzes. The export process runs asynchronously and the quiz status
    can be checked via the quiz detail endpoint.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz to export

    **Returns:**
        dict: Export initiation status message

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if quiz not found or user doesn't own it
        HTTPException: 400 if quiz has no approved questions
        HTTPException: 409 if export already in progress or completed
        HTTPException: 500 if unable to start export

    **Example Response:**
        ```json
        {
            "message": "Quiz export started"
        }
        ```

    **Usage:**
        After calling this endpoint, poll the quiz detail endpoint to check
        the export_status field for progress updates.
    """
    logger.info(
        "quiz_export_endpoint_called",
        user_id=str(current_user.id),
        quiz_id=str(quiz.id),
    )

    try:
        # Validate quiz status for export
        validate_export_ready(quiz)

        # Validate quiz has approved questions
        await validate_quiz_has_approved_questions(quiz, session)

        # Trigger background export
        background_tasks.add_task(
            quiz_export_background_flow,
            quiz.id,
            canvas_token,
        )

        logger.info(
            "quiz_export_background_task_triggered",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
        )

        return {"message": SUCCESS_MESSAGES["export_started"]}

    except ValueError as e:
        logger.warning(
            "quiz_export_validation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            error=str(e),
        )
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions as-is (from validate_quiz_has_approved_questions)
        raise
    except Exception as e:
        logger.error(
            "quiz_export_endpoint_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=ERROR_MESSAGES["export_trigger_failed"]
        )
