"""Quiz module dependencies for FastAPI dependency injection."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlmodel import select

from src.auth.dependencies import CurrentUser
from src.config import get_logger
from src.database import SessionDep

from .models import Quiz
from .schemas import QuizStatus
from .service import get_quiz_by_id
from .validators import (
    is_quiz_processing,
    is_quiz_ready_for_export,
    is_quiz_ready_for_extraction,
    is_quiz_ready_for_generation,
)

logger = get_logger("quiz_dependencies")


def verify_quiz_ownership(
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> Quiz:
    """
    Verify that the current user owns the specified quiz.

    Args:
        quiz_id: UUID of the quiz to verify
        current_user: Current authenticated user
        session: Database session

    Returns:
        Quiz object if verification succeeds

    Raises:
        HTTPException: 404 if quiz not found or user doesn't own it
    """
    quiz = get_quiz_by_id(session, quiz_id)

    if not quiz:
        logger.warning(
            "quiz_not_found",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
        )
        raise HTTPException(status_code=404, detail="Quiz not found")

    if quiz.owner_id != current_user.id:
        logger.warning(
            "quiz_access_denied",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            quiz_owner_id=str(quiz.owner_id),
        )
        raise HTTPException(status_code=404, detail="Quiz not found")

    return quiz


def verify_quiz_ownership_with_lock(
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> Quiz:
    """
    Verify quiz ownership and return quiz with row lock for updates.

    Args:
        quiz_id: UUID of the quiz to verify and lock
        current_user: Current authenticated user
        session: Database session

    Returns:
        Quiz object with row lock if verification succeeds

    Raises:
        HTTPException: 404 if quiz not found or user doesn't own it
    """
    # Get the quiz with row lock
    stmt = select(Quiz).where(Quiz.id == quiz_id).with_for_update()
    quiz = session.exec(stmt).first()

    if not quiz:
        logger.warning(
            "quiz_not_found_with_lock",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
        )
        raise HTTPException(status_code=404, detail="Quiz not found")

    if quiz.owner_id != current_user.id:
        logger.warning(
            "quiz_access_denied_with_lock",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            quiz_owner_id=str(quiz.owner_id),
        )
        raise HTTPException(status_code=404, detail="Quiz not found")

    return quiz


def validate_content_extraction_ready(quiz: Quiz) -> None:
    """
    Validate that content extraction can be triggered.

    Args:
        quiz: Quiz to validate

    Raises:
        HTTPException: 409 if extraction already in progress or not ready
    """
    if not is_quiz_ready_for_extraction(quiz):
        if quiz.status == QuizStatus.EXTRACTING_CONTENT:
            logger.warning(
                "content_extraction_already_in_progress",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
            )
            raise HTTPException(
                status_code=409, detail="Content extraction is already in progress"
            )
        elif is_quiz_processing(quiz):
            logger.warning(
                "content_extraction_not_ready_processing",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
            )
            raise HTTPException(
                status_code=409, detail="Quiz is currently being processed"
            )
        else:
            logger.warning(
                "content_extraction_not_ready",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
            )
            raise HTTPException(
                status_code=409,
                detail="Content extraction is not available in current state",
            )


def validate_question_generation_ready(quiz: Quiz) -> None:
    """
    Validate that question generation can be triggered.

    Args:
        quiz: Quiz to validate

    Raises:
        HTTPException: 400 if content extraction not completed
        HTTPException: 409 if generation already in progress
    """
    if not is_quiz_ready_for_generation(quiz):
        if quiz.status == QuizStatus.GENERATING_QUESTIONS:
            logger.warning(
                "question_generation_already_in_progress",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
            )
            raise HTTPException(
                status_code=409, detail="Question generation is already in progress"
            )
        elif quiz.status in [QuizStatus.CREATED, QuizStatus.FAILED]:
            logger.warning(
                "question_generation_content_not_ready",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
            )
            raise HTTPException(
                status_code=400,
                detail="Content extraction must be completed before generating questions",
            )
        else:
            logger.warning(
                "question_generation_not_ready",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
            )
            raise HTTPException(
                status_code=409,
                detail="Question generation is not available in current state",
            )


def validate_question_generation_ready_with_partial_support(quiz: Quiz) -> str:
    """
    Validate that question generation can be triggered with support for partial retries.

    Args:
        quiz: Quiz to validate

    Returns:
        str: Type of generation - "initial" or "retry"

    Raises:
        HTTPException: 400 if content extraction not completed
        HTTPException: 409 if generation already in progress
    """
    if not is_quiz_ready_for_generation(quiz):
        if quiz.status == QuizStatus.GENERATING_QUESTIONS:
            logger.warning(
                "question_generation_already_in_progress",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
            )
            raise HTTPException(
                status_code=409, detail="Question generation is already in progress"
            )
        elif quiz.status in [QuizStatus.CREATED, QuizStatus.FAILED]:
            logger.warning(
                "question_generation_content_not_ready",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
            )
            raise HTTPException(
                status_code=400,
                detail="Content extraction must be completed before generating questions",
            )
        else:
            logger.warning(
                "question_generation_not_ready",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
            )
            raise HTTPException(
                status_code=409,
                detail="Question generation is not available in current state",
            )

    # Determine generation type
    if quiz.status == QuizStatus.READY_FOR_REVIEW_PARTIAL:
        logger.info(
            "question_generation_retry_from_partial",
            quiz_id=str(quiz.id),
            current_status=quiz.status.value,
        )
        return "retry"
    else:
        logger.info(
            "question_generation_initial_attempt",
            quiz_id=str(quiz.id),
            current_status=quiz.status.value,
        )
        return "initial"


def validate_export_ready(quiz: Quiz) -> None:
    """
    Validate that quiz export can be triggered.

    Args:
        quiz: Quiz to validate

    Raises:
        HTTPException: 409 if already exported or export in progress
    """
    if not is_quiz_ready_for_export(quiz):
        if quiz.status == QuizStatus.PUBLISHED and quiz.canvas_quiz_id:
            logger.warning(
                "quiz_export_already_completed",
                quiz_id=str(quiz.id),
                canvas_quiz_id=quiz.canvas_quiz_id,
            )
            raise HTTPException(
                status_code=409, detail="Quiz has already been exported to Canvas"
            )
        elif quiz.status == QuizStatus.EXPORTING_TO_CANVAS:
            logger.warning(
                "quiz_export_already_in_progress",
                quiz_id=str(quiz.id),
            )
            raise HTTPException(
                status_code=409, detail="Quiz export is already in progress"
            )
        else:
            logger.warning(
                "quiz_export_not_ready",
                quiz_id=str(quiz.id),
                current_status=quiz.status,
                failure_reason=quiz.failure_reason
                if quiz.status == QuizStatus.FAILED
                else None,
            )
            raise HTTPException(status_code=409, detail="Quiz is not ready for export")


async def validate_quiz_has_approved_questions(
    quiz: Quiz,
    session: SessionDep,  # noqa: ARG001
) -> None:
    """
    Validate that quiz has approved questions for export.

    Args:
        quiz: Quiz to validate
        session: Database session

    Raises:
        HTTPException: 400 if no approved questions found
    """
    from src.database import get_async_session
    from src.question import service as question_service

    async with get_async_session() as async_session:
        approved_questions = await question_service.get_questions_by_quiz(
            async_session, quiz_id=quiz.id, approved_only=True
        )

    if not approved_questions:
        logger.warning(
            "quiz_export_no_approved_questions",
            quiz_id=str(quiz.id),
        )
        raise HTTPException(
            status_code=400, detail="Quiz has no approved questions to export"
        )


# Type aliases for common dependency combinations
QuizOwnership = Annotated[Quiz, Depends(verify_quiz_ownership)]
QuizOwnershipWithLock = Annotated[Quiz, Depends(verify_quiz_ownership_with_lock)]
