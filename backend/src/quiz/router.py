from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlmodel import select

from src.auth.dependencies import CurrentUser
from src.canvas.dependencies import CanvasToken
from src.canvas.service import CanvasQuizExportService, ContentExtractionService
from src.common import Message
from src.database import execute_in_transaction
from src.deps import SessionDep
from src.exceptions import ServiceError
from src.logging_config import get_logger
from src.question.mcq_generation_service import MCQGenerationService

from .models import Quiz
from .schemas import QuizCreate
from .service import QuizService

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
        quiz_service = QuizService(session)
        quiz = quiz_service.create_quiz(quiz_data, current_user.id)

        # Trigger content extraction in the background
        background_tasks.add_task(
            extract_content_for_quiz,
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
        raise HTTPException(
            status_code=500, detail="Failed to create quiz. Please try again."
        )


@router.get("/{quiz_id}", response_model=Quiz)
def get_quiz(
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> Quiz:
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
    logger.info(
        "quiz_retrieval_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
    )

    try:
        quiz_service = QuizService(session)
        quiz = quiz_service.get_quiz_by_id(quiz_id)

        if not quiz:
            logger.warning(
                "quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Verify ownership
        if quiz.owner_id != current_user.id:
            logger.warning(
                "quiz_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        logger.info(
            "quiz_retrieval_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
        )

        return quiz

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "quiz_retrieval_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve quiz. Please try again."
        )


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
        quiz_service = QuizService(session)
        quizzes = quiz_service.get_user_quizzes(current_user.id)

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
        raise HTTPException(
            status_code=500, detail="Failed to retrieve quizzes. Please try again."
        )


async def extract_content_for_quiz(
    quiz_id: UUID, course_id: int, module_ids: list[int], canvas_token: str
) -> None:
    """
    Orchestrates the content extraction task using a robust two-transaction approach.

    Transaction 1: Reserve the job (very fast)
    I/O Operation: Extract content from Canvas (outside transaction)
    Transaction 2: Save the result (very fast)
    """
    logger.info(
        "content_extraction_started",
        quiz_id=str(quiz_id),
        course_id=course_id,
        module_count=len(module_ids),
    )

    # === Transaction 1: Reserve the Job (very fast) ===
    async def _reserve_job(session: Any, quiz_id: UUID) -> dict[str, Any] | None:
        """Reserve the extraction job and return quiz settings if successful."""
        quiz_service = QuizService(session)
        quiz = await quiz_service.get_quiz_for_update(session, quiz_id)

        if not quiz:
            logger.error("content_extraction_quiz_not_found", quiz_id=str(quiz_id))
            return None

        if quiz.content_extraction_status in ["processing", "completed"]:
            logger.info(
                "content_extraction_job_already_taken",
                quiz_id=str(quiz_id),
                current_status=quiz.content_extraction_status,
            )
            return None  # Job already taken or completed

        # Reserve the job
        quiz.content_extraction_status = "processing"
        await session.flush()  # Make status visible immediately

        # Return quiz settings for later use
        return {
            "target_questions": quiz.question_count,
            "llm_model": quiz.llm_model,
            "llm_temperature": quiz.llm_temperature,
        }

    quiz_settings = await execute_in_transaction(
        _reserve_job, quiz_id, isolation_level="REPEATABLE READ", retries=3
    )

    if not quiz_settings:
        logger.info(
            "content_extraction_skipped",
            quiz_id=str(quiz_id),
            reason="job_already_running_or_complete",
        )
        return

    # === Slow I/O Operation (occurs outside any transaction) ===
    try:
        extraction_service = ContentExtractionService(canvas_token, course_id)
        extracted_content = await extraction_service.extract_content_for_modules(
            module_ids
        )
        content_summary = extraction_service.get_content_summary(extracted_content)

        logger.info(
            "content_extraction_completed",
            quiz_id=str(quiz_id),
            course_id=course_id,
            modules_processed=content_summary["modules_processed"],
            total_pages=content_summary["total_pages"],
            total_word_count=content_summary["total_word_count"],
        )

        final_status = "completed"

    except Exception as e:
        logger.error(
            "content_extraction_failed_during_api_call",
            quiz_id=str(quiz_id),
            course_id=course_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        extracted_content = None
        final_status = "failed"

    # === Transaction 2: Save the Result (very fast) ===
    async def _save_result(
        session: Any,
        quiz_id: UUID,
        content: dict[str, Any] | None,
        status: str,
    ) -> None:
        """Save the extraction result to the quiz."""
        quiz_service = QuizService(session)
        quiz = await quiz_service.get_quiz_for_update(session, quiz_id)
        if not quiz:
            logger.error(
                "content_extraction_quiz_not_found_during_save", quiz_id=str(quiz_id)
            )
            return

        quiz.content_extraction_status = status
        if status == "completed" and content is not None:
            quiz.extracted_content = content
            quiz.content_extracted_at = datetime.now(timezone.utc)

    await execute_in_transaction(
        _save_result,
        quiz_id,
        extracted_content,
        final_status,
        isolation_level="REPEATABLE READ",
        retries=3,
    )

    # If extraction was successful, trigger question generation
    if final_status == "completed" and quiz_settings:
        logger.info(
            "auto_triggering_question_generation",
            quiz_id=str(quiz_id),
            target_questions=quiz_settings["target_questions"],
            llm_model=quiz_settings["llm_model"],
        )
        await generate_questions_for_quiz(
            quiz_id=quiz_id,
            target_question_count=quiz_settings["target_questions"],
            llm_model=quiz_settings["llm_model"],
            llm_temperature=quiz_settings["llm_temperature"],
        )


async def generate_questions_for_quiz(
    quiz_id: UUID, target_question_count: int, llm_model: str, llm_temperature: float
) -> None:
    """
    Orchestrates the question generation task using a robust two-transaction approach.

    Transaction 1: Reserve the job (very fast)
    I/O Operation: Generate questions via LLM (outside transaction)
    Transaction 2: Save the result (very fast)
    """
    logger.info(
        "question_generation_started",
        quiz_id=str(quiz_id),
        target_questions=target_question_count,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
    )

    # === Transaction 1: Reserve the Job (very fast) ===
    async def _reserve_generation_job(session: Any, quiz_id: UUID) -> bool:
        """Reserve the question generation job."""
        quiz_service = QuizService(session)
        quiz = await quiz_service.get_quiz_for_update(session, quiz_id)

        if not quiz:
            logger.error("question_generation_quiz_not_found", quiz_id=str(quiz_id))
            return False

        if quiz.llm_generation_status in ["processing", "completed"]:
            logger.info(
                "question_generation_job_already_taken",
                quiz_id=str(quiz_id),
                current_status=quiz.llm_generation_status,
            )
            return False  # Job already taken or completed

        # Reserve the job
        quiz.llm_generation_status = "processing"
        await session.flush()  # Make status visible immediately
        return True

    should_proceed = await execute_in_transaction(
        _reserve_generation_job, quiz_id, isolation_level="REPEATABLE READ", retries=3
    )

    if not should_proceed:
        logger.info(
            "question_generation_skipped",
            quiz_id=str(quiz_id),
            reason="job_already_running_or_complete",
        )
        return

    # === Slow I/O Operation (occurs outside any transaction) ===
    try:
        mcq_service = MCQGenerationService()
        results = await mcq_service.generate_mcqs_for_quiz(
            quiz_id=quiz_id,
            target_question_count=target_question_count,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
        )

        if results["success"]:
            final_status = "completed"
            logger.info(
                "question_generation_completed",
                quiz_id=str(quiz_id),
                questions_generated=results["questions_generated"],
                target_questions=target_question_count,
            )
        else:
            final_status = "failed"
            logger.error(
                "question_generation_failed_during_llm_call",
                quiz_id=str(quiz_id),
                error_message=results["error_message"],
            )

    except Exception as e:
        logger.error(
            "question_generation_failed_during_llm_call",
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        final_status = "failed"

    # === Transaction 2: Save the Result (very fast) ===
    async def _save_generation_result(
        session: Any,
        quiz_id: UUID,
        status: str,
    ) -> None:
        """Save the generation result to the quiz."""
        quiz_service = QuizService(session)
        quiz = await quiz_service.get_quiz_for_update(session, quiz_id)
        if not quiz:
            logger.error(
                "question_generation_quiz_not_found_during_save", quiz_id=str(quiz_id)
            )
            return

        quiz.llm_generation_status = status

    await execute_in_transaction(
        _save_generation_result,
        quiz_id,
        final_status,
        isolation_level="REPEATABLE READ",
        retries=3,
    )


@router.post("/{quiz_id}/extract-content")
async def trigger_content_extraction(
    quiz_id: UUID,
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
        HTTPException: 500 if unable to trigger extraction
    """
    logger.info(
        "manual_content_extraction_triggered",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
    )

    try:
        # Get the quiz and verify ownership with locking
        stmt = select(Quiz).where(Quiz.id == quiz_id).with_for_update()
        quiz = session.exec(stmt).first()

        if not quiz:
            logger.warning(
                "manual_extraction_quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != current_user.id:
            logger.warning(
                "manual_extraction_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Check if extraction is already in progress
        if quiz.content_extraction_status == "processing":
            logger.warning(
                "manual_extraction_already_in_progress",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                current_status=quiz.content_extraction_status,
            )
            raise HTTPException(
                status_code=409, detail="Content extraction is already in progress"
            )

        # Reset extraction status to pending
        quiz.content_extraction_status = "pending"
        quiz.extracted_content = None
        quiz.content_extracted_at = None
        session.add(quiz)
        session.commit()

        # Get selected modules from the quiz
        selected_modules = quiz.selected_modules
        module_ids = [int(module_id) for module_id in selected_modules.keys()]

        # Trigger content extraction in the background
        background_tasks.add_task(
            extract_content_for_quiz,
            quiz_id,
            quiz.canvas_course_id,
            module_ids,
            canvas_token,
        )

        logger.info(
            "manual_content_extraction_started",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            module_count=len(module_ids),
        )

        return {"message": "Content extraction started"}

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "manual_content_extraction_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to trigger content extraction"
        )


@router.delete("/{quiz_id}", response_model=Message)
def delete_quiz_endpoint(
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> Message:
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
        quiz_service = QuizService(session)
        success = quiz_service.delete_quiz(quiz_id, current_user.id)

        if not success:
            logger.warning(
                "quiz_deletion_failed_not_found_or_unauthorized",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        logger.info(
            "quiz_deletion_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
        )

        return Message(message="Quiz deleted successfully")

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
        raise HTTPException(
            status_code=500, detail="Failed to delete quiz. Please try again."
        )


@router.post("/{quiz_id}/generate-questions")
async def trigger_question_generation(
    quiz_id: UUID,
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
        quiz_id=str(quiz_id),
    )

    try:
        # Get the quiz and verify ownership
        quiz_service = QuizService(session)
        quiz = quiz_service.get_quiz_by_id(quiz_id)

        if not quiz:
            logger.warning(
                "manual_generation_quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != current_user.id:
            logger.warning(
                "manual_generation_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Check if content extraction is completed
        if quiz.content_extraction_status != "completed":
            logger.warning(
                "manual_generation_content_not_ready",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                content_status=quiz.content_extraction_status,
            )
            raise HTTPException(
                status_code=400,
                detail="Content extraction must be completed before generating questions",
            )

        # Check if question generation is already in progress
        if quiz.llm_generation_status == "processing":
            logger.warning(
                "manual_generation_already_in_progress",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                current_status=quiz.llm_generation_status,
            )
            raise HTTPException(
                status_code=409, detail="Question generation is already in progress"
            )

        # Reset generation status to pending
        quiz.llm_generation_status = "pending"
        session.add(quiz)
        session.commit()

        # Trigger question generation in the background
        background_tasks.add_task(
            generate_questions_for_quiz,
            quiz_id,
            quiz.question_count,
            quiz.llm_model,
            quiz.llm_temperature,
        )

        logger.info(
            "manual_question_generation_started",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_count=quiz.question_count,
            llm_model=quiz.llm_model,
        )

        return {"message": "Question generation started"}

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "manual_question_generation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to trigger question generation"
        )


@router.get("/{quiz_id}/questions/stats")
def get_quiz_question_stats(
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
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
        quiz_id=str(quiz_id),
    )

    try:
        # Verify quiz exists and user owns it
        quiz_service = QuizService(session)
        quiz = quiz_service.get_quiz_by_id(quiz_id)
        if not quiz:
            logger.warning(
                "question_stats_quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != current_user.id:
            logger.warning(
                "question_stats_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Get question counts
        from src.question.service import QuestionService

        question_service = QuestionService(session)
        stats = question_service.get_question_counts_by_quiz_id(quiz_id)

        logger.info(
            "question_stats_retrieval_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            total_questions=stats["total"],
            approved_questions=stats["approved"],
        )

        return stats

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "question_stats_retrieval_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve question stats. Please try again.",
        )


async def export_quiz_to_canvas_background(quiz_id: UUID, canvas_token: str) -> None:
    """
    Background task to export a quiz to Canvas LMS.

    This function runs asynchronously after the export endpoint is called.
    It handles the complete Canvas quiz creation and question export process.
    """
    logger.info(
        "canvas_export_background_task_started",
        quiz_id=str(quiz_id),
    )

    try:
        # Initialize Canvas export service
        export_service = CanvasQuizExportService(canvas_token)

        # Export quiz to Canvas
        result = await export_service.export_quiz_to_canvas(quiz_id)

        logger.info(
            "canvas_export_background_task_completed",
            quiz_id=str(quiz_id),
            success=result.get("success", False),
            canvas_quiz_id=result.get("canvas_quiz_id"),
            exported_questions=result.get("exported_questions", 0),
        )

    except Exception as e:
        logger.error(
            "canvas_export_background_task_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )


@router.post("/{quiz_id}/export")
async def export_quiz_to_canvas(
    quiz_id: UUID,
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
        quiz_id=str(quiz_id),
    )

    try:
        # Verify quiz exists and user owns it
        quiz_service = QuizService(session)
        quiz = quiz_service.get_quiz_by_id(quiz_id)
        if not quiz:
            logger.warning(
                "quiz_export_quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != current_user.id:
            logger.warning(
                "quiz_export_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Check if already exported
        if quiz.export_status == "completed" and quiz.canvas_quiz_id:
            logger.warning(
                "quiz_export_already_completed",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                canvas_quiz_id=quiz.canvas_quiz_id,
            )
            raise HTTPException(
                status_code=409, detail="Quiz has already been exported to Canvas"
            )

        # Check if export is already in progress
        if quiz.export_status == "processing":
            logger.warning(
                "quiz_export_already_in_progress",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(
                status_code=409, detail="Quiz export is already in progress"
            )

        # Check if quiz has approved questions
        from src.question.service import QuestionService

        question_service = QuestionService(session)
        approved_questions = question_service.get_approved_questions_by_quiz_id(quiz_id)
        if not approved_questions:
            logger.warning(
                "quiz_export_no_approved_questions",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(
                status_code=400, detail="Quiz has no approved questions to export"
            )

        # Trigger background export
        background_tasks.add_task(
            export_quiz_to_canvas_background,
            quiz_id,
            canvas_token,
        )

        logger.info(
            "quiz_export_background_task_triggered",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            approved_questions_count=len(approved_questions),
        )

        return {"message": "Quiz export started"}

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "quiz_export_endpoint_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to start quiz export. Please try again."
        )
