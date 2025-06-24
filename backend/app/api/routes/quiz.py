from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.core.logging_config import get_logger
from app.crud import create_quiz, get_quiz_by_id, get_user_quizzes
from app.models import Quiz, QuizCreate

router = APIRouter(prefix="/quiz", tags=["quiz"])
logger = get_logger("quiz")


@router.post("/", response_model=Quiz)
def create_new_quiz(
    quiz_data: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
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
