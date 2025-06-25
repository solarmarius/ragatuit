from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlmodel import Session, select

from app.api.deps import CanvasToken, CurrentUser, SessionDep
from app.core.db import engine
from app.core.logging_config import get_logger
from app.crud import create_quiz, delete_quiz, get_quiz_by_id, get_user_quizzes
from app.models import Message, Quiz, QuizCreate
from app.services.content_extraction import ContentExtractionService
from app.services.mcq_generation import mcq_generation_service

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

            # Automatically trigger question generation after content extraction completes
            if quiz:
                logger.info(
                    "auto_triggering_question_generation",
                    quiz_id=str(quiz_id),
                    target_questions=quiz.question_count,
                    llm_model=quiz.llm_model,
                )

                # Note: We can't use background_tasks here since this is already a background task
                # Instead, we'll call the function directly as an async task
                await generate_questions_for_quiz(
                    quiz_id=quiz_id,
                    target_question_count=quiz.question_count,
                    llm_model=quiz.llm_model,
                    llm_temperature=quiz.llm_temperature,
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


async def generate_questions_for_quiz(
    quiz_id: UUID, target_question_count: int, llm_model: str, llm_temperature: float
) -> None:
    """
    Background task to generate MCQ questions for a quiz.

    This function runs asynchronously after content extraction is complete to generate
    multiple-choice questions using the LangGraph workflow.
    """
    logger.info(
        "question_generation_started",
        quiz_id=str(quiz_id),
        target_questions=target_question_count,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
    )

    # Create a new database session for the background task
    with Session(engine) as session:
        try:
            # Use SELECT FOR UPDATE to prevent race conditions
            stmt = select(Quiz).where(Quiz.id == quiz_id).with_for_update()
            quiz = session.exec(stmt).first()

            if not quiz:
                logger.error(
                    "question_generation_quiz_not_found",
                    quiz_id=str(quiz_id),
                )
                return

            # Check if generation is already in progress
            if quiz.llm_generation_status == "processing":
                logger.warning(
                    "question_generation_already_in_progress",
                    quiz_id=str(quiz_id),
                    current_status=quiz.llm_generation_status,
                )
                return

            # Atomically update status to processing
            quiz.llm_generation_status = "processing"
            session.add(quiz)
            session.commit()

            # Generate questions using the MCQ generation service
            results = await mcq_generation_service.generate_mcqs_for_quiz(
                quiz_id=quiz_id,
                target_question_count=target_question_count,
                llm_model=llm_model,
                llm_temperature=llm_temperature,
            )

            # Update quiz status based on results using fresh lock
            stmt = select(Quiz).where(Quiz.id == quiz_id).with_for_update()
            quiz = session.exec(stmt).first()

            if quiz:
                if results["success"]:
                    quiz.llm_generation_status = "completed"
                    logger.info(
                        "question_generation_completed",
                        quiz_id=str(quiz_id),
                        questions_generated=results["questions_generated"],
                        target_questions=target_question_count,
                    )
                else:
                    quiz.llm_generation_status = "failed"
                    logger.error(
                        "question_generation_failed",
                        quiz_id=str(quiz_id),
                        error_message=results["error_message"],
                    )

                session.add(quiz)
                session.commit()

        except Exception as e:
            logger.error(
                "question_generation_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

            # Update quiz status to failed with locking
            try:
                stmt = select(Quiz).where(Quiz.id == quiz_id).with_for_update()
                quiz = session.exec(stmt).first()
                if quiz:
                    quiz.llm_generation_status = "failed"
                    session.add(quiz)
                    session.commit()
            except Exception as update_error:
                logger.error(
                    "question_generation_status_update_failed",
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
        success = delete_quiz(session, quiz_id, current_user.id)

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
        quiz = get_quiz_by_id(session, quiz_id)

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
