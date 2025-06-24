from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlmodel import Session, select

from app.api.deps import CanvasToken, CurrentUser, SessionDep
from app.core.db import engine
from app.core.logging_config import get_logger
from app.crud import create_quiz, get_quiz_by_id, get_user_quizzes
from app.models import Quiz, QuizCreate
from app.services.content_extraction import ContentExtractionService

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
            - llm_model: LLM model to use (default "o3-pro")
            - llm_temperature: LLM temperature setting (0.0-2.0, default 0.3)

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
            "llm_temperature": 0.3
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
            extract_content_for_quiz,
            quiz.id,
            quiz_data.canvas_course_id,
            list(quiz_data.selected_modules.keys()),
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
            "llm_temperature": 0.3,
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
        quiz = get_quiz_by_id(session, quiz_id)

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
                "llm_temperature": 0.3,
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
    Background task to extract content from Canvas modules for a quiz.

    This function runs asynchronously after quiz creation to fetch and process
    content from the selected Canvas modules.
    """
    logger.info(
        "content_extraction_started",
        quiz_id=str(quiz_id),
        course_id=course_id,
        module_count=len(module_ids),
    )

    # Create a new database session for the background task
    with Session(engine) as session:
        try:
            # Use SELECT FOR UPDATE to prevent race conditions
            stmt = select(Quiz).where(Quiz.id == quiz_id).with_for_update()
            quiz = session.exec(stmt).first()

            if not quiz:
                logger.error(
                    "content_extraction_quiz_not_found",
                    quiz_id=str(quiz_id),
                )
                return

            # Check if extraction is already in progress to prevent duplicate work
            if quiz.content_extraction_status == "processing":
                logger.warning(
                    "content_extraction_already_in_progress",
                    quiz_id=str(quiz_id),
                    current_status=quiz.content_extraction_status,
                )
                return

            # Atomically update status to processing
            quiz.content_extraction_status = "processing"
            session.add(quiz)
            session.commit()

            # Initialize content extraction service
            extraction_service = ContentExtractionService(canvas_token, course_id)

            # Extract content from all selected modules
            extracted_content = await extraction_service.extract_content_for_modules(
                module_ids
            )

            # Get content summary for logging
            content_summary = extraction_service.get_content_summary(extracted_content)

            # Update quiz with extracted content using fresh lock
            stmt = select(Quiz).where(Quiz.id == quiz_id).with_for_update()
            quiz = session.exec(stmt).first()

            if quiz:
                quiz.content_dict = extracted_content
                quiz.content_extraction_status = "completed"
                quiz.content_extracted_at = datetime.now(timezone.utc)
                session.add(quiz)
                session.commit()

            logger.info(
                "content_extraction_completed",
                quiz_id=str(quiz_id),
                course_id=course_id,
                modules_processed=content_summary["modules_processed"],
                total_pages=content_summary["total_pages"],
                total_word_count=content_summary["total_word_count"],
            )

        except Exception as e:
            logger.error(
                "content_extraction_failed",
                quiz_id=str(quiz_id),
                course_id=course_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

            # Update quiz status to failed with locking
            try:
                stmt = select(Quiz).where(Quiz.id == quiz_id).with_for_update()
                quiz = session.exec(stmt).first()
                if quiz:
                    quiz.content_extraction_status = "failed"
                    session.add(quiz)
                    session.commit()
            except Exception as update_error:
                logger.error(
                    "content_extraction_status_update_failed",
                    quiz_id=str(quiz_id),
                    error=str(update_error),
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
        selected_modules = quiz.modules_dict
        module_ids = list(selected_modules.keys())

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
