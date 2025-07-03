"""Quiz module dependencies for FastAPI dependency injection."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlmodel import select

from src.auth.dependencies import CurrentUser
from src.database import SessionDep
from src.logging_config import get_logger

from .models import Quiz
from .service import get_quiz_by_id

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
        HTTPException: 409 if extraction already in progress
    """
    if quiz.content_extraction_status == "processing":
        logger.warning(
            "content_extraction_already_in_progress",
            quiz_id=str(quiz.id),
            current_status=quiz.content_extraction_status,
        )
        raise HTTPException(
            status_code=409, detail="Content extraction is already in progress"
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
    if quiz.content_extraction_status != "completed":
        logger.warning(
            "question_generation_content_not_ready",
            quiz_id=str(quiz.id),
            content_status=quiz.content_extraction_status,
        )
        raise HTTPException(
            status_code=400,
            detail="Content extraction must be completed before generating questions",
        )

    if quiz.llm_generation_status == "processing":
        logger.warning(
            "question_generation_already_in_progress",
            quiz_id=str(quiz.id),
            current_status=quiz.llm_generation_status,
        )
        raise HTTPException(
            status_code=409, detail="Question generation is already in progress"
        )


def validate_export_ready(quiz: Quiz) -> None:
    """
    Validate that quiz export can be triggered.

    Args:
        quiz: Quiz to validate

    Raises:
        HTTPException: 409 if already exported or export in progress
    """
    if quiz.export_status == "completed" and quiz.canvas_quiz_id:
        logger.warning(
            "quiz_export_already_completed",
            quiz_id=str(quiz.id),
            canvas_quiz_id=quiz.canvas_quiz_id,
        )
        raise HTTPException(
            status_code=409, detail="Quiz has already been exported to Canvas"
        )

    if quiz.export_status == "processing":
        logger.warning(
            "quiz_export_already_in_progress",
            quiz_id=str(quiz.id),
        )
        raise HTTPException(
            status_code=409, detail="Quiz export is already in progress"
        )


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
