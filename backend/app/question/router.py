from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.deps import SessionDep
from app.logging_config import get_logger
from app.common import Message

from .models import Question
from .schemas import QuestionPublic, QuestionUpdate
from .service import QuestionService

router = APIRouter(prefix="/quiz", tags=["questions"])
logger = get_logger("questions")


@router.get("/{quiz_id}/questions", response_model=list[QuestionPublic])
def get_quiz_questions(
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> list[Question]:
    """
    Retrieve all questions for a specific quiz.

    Returns all questions (approved and unapproved) for the quiz if the
    authenticated user is the quiz owner.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz to get questions for

    **Returns:**
        list[QuestionPublic]: List of question objects with approval status

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if quiz not found or user doesn't own it
        HTTPException: 500 if database operation fails
    """
    logger.info(
        "quiz_questions_retrieval_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
    )

    # Initialize service
    question_service = QuestionService(session)

    try:
        # Import QuizService locally to avoid circular imports
        from app.quiz.service import QuizService

        # Verify quiz exists and user owns it
        quiz_service = QuizService(session)
        quiz = quiz_service.get_quiz_by_id(quiz_id)
        if not quiz:
            logger.warning(
                "quiz_questions_quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != current_user.id:
            logger.warning(
                "quiz_questions_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Get all questions for the quiz
        questions = question_service.get_questions_by_quiz_id(quiz_id)

        logger.info(
            "quiz_questions_retrieval_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_count=len(questions),
        )

        return questions

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "quiz_questions_retrieval_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve questions. Please try again."
        )


@router.get("/{quiz_id}/questions/{question_id}", response_model=QuestionPublic)
def get_question(
    quiz_id: UUID,
    question_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> Question:
    """
    Retrieve a specific question by its ID.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz the question belongs to
        question_id (UUID): The UUID of the question to retrieve

    **Returns:**
        QuestionPublic: The question object with all details

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if question/quiz not found or user doesn't own the quiz
        HTTPException: 500 if database operation fails
    """
    logger.info(
        "question_retrieval_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_id=str(question_id),
    )

    # Initialize service
    question_service = QuestionService(session)

    try:
        # Import QuizService locally to avoid circular imports
        from app.quiz.service import QuizService

        # Verify quiz exists and user owns it
        quiz_service = QuizService(session)
        quiz = quiz_service.get_quiz_by_id(quiz_id)
        if not quiz:
            logger.warning(
                "question_quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != current_user.id:
            logger.warning(
                "question_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Get the question
        question = question_service.get_question_by_id(question_id)
        if not question:
            logger.warning(
                "question_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                question_id=str(question_id),
            )
            raise HTTPException(status_code=404, detail="Question not found")

        # Verify question belongs to the quiz
        if question.quiz_id != quiz_id:
            logger.warning(
                "question_quiz_mismatch",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                question_id=str(question_id),
                question_quiz_id=str(question.quiz_id),
            )
            raise HTTPException(status_code=404, detail="Question not found")

        logger.info(
            "question_retrieval_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
        )

        return question

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "question_retrieval_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve question. Please try again."
        )


@router.put("/{quiz_id}/questions/{question_id}", response_model=QuestionPublic)
def update_quiz_question(
    quiz_id: UUID,
    question_id: UUID,
    question_update: QuestionUpdate,
    current_user: CurrentUser,
    session: SessionDep,
) -> Question:
    """
    Update a question's content (text, options, correct answer).

    Allows editing of question text, all options (A, B, C, D), and the correct answer.
    The question must belong to a quiz owned by the authenticated user.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz the question belongs to
        question_id (UUID): The UUID of the question to update
        question_update (QuestionUpdate): Updated question data

    **Returns:**
        QuestionPublic: The updated question object

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if question/quiz not found or user doesn't own the quiz
        HTTPException: 400 if validation fails
        HTTPException: 500 if database operation fails
    """
    logger.info(
        "question_update_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_id=str(question_id),
    )

    # Initialize service
    question_service = QuestionService(session)

    try:
        # Import QuizService locally to avoid circular imports
        from app.quiz.service import QuizService

        # Verify quiz exists and user owns it
        quiz_service = QuizService(session)
        quiz = quiz_service.get_quiz_by_id(quiz_id)
        if not quiz:
            logger.warning(
                "question_update_quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != current_user.id:
            logger.warning(
                "question_update_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Get and verify the question
        question = question_service.get_question_by_id(question_id)
        if not question:
            logger.warning(
                "question_update_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                question_id=str(question_id),
            )
            raise HTTPException(status_code=404, detail="Question not found")

        if question.quiz_id != quiz_id:
            logger.warning(
                "question_update_quiz_mismatch",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                question_id=str(question_id),
                question_quiz_id=str(question.quiz_id),
            )
            raise HTTPException(status_code=404, detail="Question not found")

        # Update the question
        updated_question = question_service.update_question(
            question_id, question_update
        )
        if not updated_question:
            raise HTTPException(status_code=500, detail="Failed to update question")

        logger.info(
            "question_update_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
        )

        return updated_question

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "question_update_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to update question. Please try again."
        )


@router.put("/{quiz_id}/questions/{question_id}/approve", response_model=QuestionPublic)
def approve_quiz_question(
    quiz_id: UUID,
    question_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> Question:
    """
    Approve a question for inclusion in the final quiz.

    Sets the question's is_approved status to True and records the approval timestamp.
    Only the quiz owner can approve questions.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz the question belongs to
        question_id (UUID): The UUID of the question to approve

    **Returns:**
        QuestionPublic: The approved question object

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if question/quiz not found or user doesn't own the quiz
        HTTPException: 500 if database operation fails
    """
    logger.info(
        "question_approval_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_id=str(question_id),
    )

    # Initialize service
    question_service = QuestionService(session)

    try:
        # Import QuizService locally to avoid circular imports
        from app.quiz.service import QuizService

        # Verify quiz exists and user owns it
        quiz_service = QuizService(session)
        quiz = quiz_service.get_quiz_by_id(quiz_id)
        if not quiz:
            logger.warning(
                "question_approval_quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != current_user.id:
            logger.warning(
                "question_approval_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Get and verify the question
        question = question_service.get_question_by_id(question_id)
        if not question:
            logger.warning(
                "question_approval_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                question_id=str(question_id),
            )
            raise HTTPException(status_code=404, detail="Question not found")

        if question.quiz_id != quiz_id:
            logger.warning(
                "question_approval_quiz_mismatch",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                question_id=str(question_id),
                question_quiz_id=str(question.quiz_id),
            )
            raise HTTPException(status_code=404, detail="Question not found")

        # Approve the question
        approved_question = question_service.approve_question(question_id)
        if not approved_question:
            raise HTTPException(status_code=500, detail="Failed to approve question")

        logger.info(
            "question_approval_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
        )

        return approved_question

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "question_approval_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to approve question. Please try again."
        )


@router.delete("/{quiz_id}/questions/{question_id}", response_model=Message)
def delete_quiz_question(
    quiz_id: UUID,
    question_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> Message:
    """
    Delete a question from the quiz.

    Permanently removes a question from the quiz. Only the quiz owner can delete questions.

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz the question belongs to
        question_id (UUID): The UUID of the question to delete

    **Returns:**
        Message: Confirmation message that the question was deleted

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if question/quiz not found or user doesn't own the quiz
        HTTPException: 500 if database operation fails
    """
    logger.info(
        "question_deletion_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_id=str(question_id),
    )

    # Initialize service
    question_service = QuestionService(session)

    try:
        # Import QuizService locally to avoid circular imports
        from app.quiz.service import QuizService

        # Verify quiz exists and user owns it
        quiz_service = QuizService(session)
        quiz = quiz_service.get_quiz_by_id(quiz_id)
        if not quiz:
            logger.warning(
                "question_deletion_quiz_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != current_user.id:
            logger.warning(
                "question_deletion_access_denied",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                quiz_owner_id=str(quiz.owner_id),
            )
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Delete the question (service handles ownership verification)
        success = question_service.delete_question(question_id, current_user.id)
        if not success:
            logger.warning(
                "question_deletion_failed_not_found",
                user_id=str(current_user.id),
                quiz_id=str(quiz_id),
                question_id=str(question_id),
            )
            raise HTTPException(status_code=404, detail="Question not found")

        logger.info(
            "question_deletion_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
        )

        return Message(message="Question deleted successfully")

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "question_deletion_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to delete question. Please try again."
        )
