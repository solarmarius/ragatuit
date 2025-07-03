"""Quiz service functions for business logic."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, cast, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from src.config import get_logger

from .models import Quiz
from .schemas import QuizCreate, Status
from .validators import (
    validate_quiz_for_content_extraction,
    validate_quiz_for_question_generation,
)

logger = get_logger("quiz_service")


def create_quiz(session: Session, quiz_create: QuizCreate, owner_id: UUID) -> Quiz:
    """
    Create a new quiz.

    Args:
        session: Database session
        quiz_create: Quiz creation data
        owner_id: ID of the quiz owner

    Returns:
        Created quiz instance
    """
    logger.info(
        "quiz_creation_requested",
        owner_id=str(owner_id),
        course_id=quiz_create.canvas_course_id,
        title=quiz_create.title,
    )

    # Convert dict[int, str] to dict[str, str] for storage
    selected_modules = {
        str(module_id): name for module_id, name in quiz_create.selected_modules.items()
    }

    quiz = Quiz(
        owner_id=owner_id,
        canvas_course_id=quiz_create.canvas_course_id,
        canvas_course_name=quiz_create.canvas_course_name,
        selected_modules=selected_modules,
        title=quiz_create.title,
        question_count=quiz_create.question_count,
        llm_model=quiz_create.llm_model,
        llm_temperature=quiz_create.llm_temperature,
        updated_at=datetime.now(timezone.utc),
    )

    session.add(quiz)
    session.commit()
    session.refresh(quiz)

    logger.info(
        "quiz_created_successfully",
        quiz_id=str(quiz.id),
        owner_id=str(owner_id),
    )

    return quiz


def get_quiz_by_id(session: Session, quiz_id: UUID) -> Quiz | None:
    """
    Get quiz by ID.

    Args:
        session: Database session
        quiz_id: Quiz ID

    Returns:
        Quiz instance or None
    """
    return session.get(Quiz, quiz_id)


def get_user_quizzes(session: Session, user_id: UUID) -> list[Quiz]:
    """
    Get all quizzes for a user.

    Args:
        session: Database session
        user_id: User ID

    Returns:
        List of user's quizzes
    """
    statement = (
        select(Quiz).where(Quiz.owner_id == user_id).order_by(Quiz.created_at.desc())  # type: ignore
    )
    return list(session.exec(statement).all())


def delete_quiz(session: Session, quiz_id: UUID, user_id: UUID) -> bool:
    """
    Delete a quiz if owned by the user.

    Args:
        session: Database session
        quiz_id: Quiz ID
        user_id: User ID (must be owner)

    Returns:
        True if deleted, False if not found or not owner
    """
    quiz = session.get(Quiz, quiz_id)
    if quiz and quiz.owner_id == user_id:
        session.delete(quiz)
        session.commit()
        logger.info(
            "quiz_deleted",
            quiz_id=str(quiz_id),
            user_id=str(user_id),
        )
        return True
    return False


async def get_quiz_for_update(session: AsyncSession, quiz_id: UUID) -> Quiz | None:
    """
    Get quiz for update with row lock.

    Args:
        session: Async database session
        quiz_id: Quiz ID

    Returns:
        Quiz instance or None
    """
    result = await session.execute(
        select(Quiz).where(Quiz.id == quiz_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def get_content_from_quiz(
    session: AsyncSession, quiz_id: UUID
) -> dict[str, Any] | None:
    """
    Get extracted content from quiz.

    Args:
        session: Async database session
        quiz_id: Quiz ID

    Returns:
        Extracted content or None
    """
    result = await session.execute(
        select(Quiz.extracted_content).where(Quiz.id == quiz_id)
    )
    content = result.scalar_one_or_none()
    return content


async def get_question_counts(session: AsyncSession, quiz_id: UUID) -> dict[str, int]:
    """
    Get question counts for a quiz.

    Args:
        session: Async database session
        quiz_id: Quiz ID

    Returns:
        Dict with 'total' and 'approved' question counts
    """
    # Import Question here to avoid circular imports
    from src.question.models import Question

    logger.debug("question_counts_requested", quiz_id=str(quiz_id))

    # Query for total and approved question counts
    result = await session.execute(
        select(
            func.count().label("total"),
            func.sum(cast(Question.is_approved, Integer)).label("approved"),
        ).where(Question.quiz_id == quiz_id)
    )

    row = result.first()
    if row is None:
        total_count = 0
        approved_count = 0
    else:
        total_count = int(row.total or 0)
        approved_count = int(row.approved or 0)

    counts = {"total": total_count, "approved": approved_count}

    logger.debug(
        "question_counts_retrieved",
        quiz_id=str(quiz_id),
        total=counts["total"],
        approved=counts["approved"],
    )

    return counts


def prepare_content_extraction(
    session: Session, quiz_id: UUID, user_id: UUID
) -> dict[str, Any]:
    """
    Prepare quiz for content extraction and return module data.

    Args:
        session: Database session
        quiz_id: Quiz ID
        user_id: User ID (must be owner)

    Returns:
        Dict with course_id and module_ids for extraction
    """
    quiz = validate_quiz_for_content_extraction(session, quiz_id, user_id)

    # Reset extraction status to pending
    quiz.content_extraction_status = Status.PENDING
    quiz.extracted_content = None
    quiz.content_extracted_at = None
    session.add(quiz)
    session.commit()

    # Return extraction parameters
    module_ids = [int(module_id) for module_id in quiz.selected_modules.keys()]
    return {
        "course_id": quiz.canvas_course_id,
        "module_ids": module_ids,
    }


def prepare_question_generation(
    session: Session, quiz_id: UUID, user_id: UUID
) -> dict[str, Any]:
    """
    Prepare quiz for question generation and return generation parameters.

    Args:
        session: Database session
        quiz_id: Quiz ID
        user_id: User ID (must be owner)

    Returns:
        Dict with generation parameters
    """
    quiz = validate_quiz_for_question_generation(session, quiz_id, user_id)

    # Reset generation status to pending
    quiz.llm_generation_status = Status.PENDING
    session.add(quiz)
    session.commit()

    return {
        "question_count": quiz.question_count,
        "llm_model": quiz.llm_model,
        "llm_temperature": quiz.llm_temperature,
    }


async def reserve_quiz_job(
    session: AsyncSession, quiz_id: UUID, job_type: str
) -> dict[str, Any] | None:
    """
    Reserve a quiz job (content extraction, question generation, export) using row lock.

    Args:
        session: Async database session
        quiz_id: Quiz ID
        job_type: Type of job ('extraction', 'generation', 'export')

    Returns:
        Quiz settings dict if job reserved successfully, None if already taken
    """
    quiz = await get_quiz_for_update(session, quiz_id)

    if not quiz:
        logger.error(
            "quiz_not_found_for_job_reservation",
            quiz_id=str(quiz_id),
            job_type=job_type,
        )
        return None

    # Check current status based on job type
    if job_type == "extraction":
        if quiz.content_extraction_status in ["processing", "completed"]:
            logger.info(
                "job_already_taken",
                quiz_id=str(quiz_id),
                job_type=job_type,
                current_status=quiz.content_extraction_status,
            )
            return None
        quiz.content_extraction_status = "processing"
        settings = {
            "target_questions": quiz.question_count,
            "llm_model": quiz.llm_model,
            "llm_temperature": quiz.llm_temperature,
        }

    elif job_type == "generation":
        if quiz.llm_generation_status in ["processing", "completed"]:
            logger.info(
                "job_already_taken",
                quiz_id=str(quiz_id),
                job_type=job_type,
                current_status=quiz.llm_generation_status,
            )
            return None
        quiz.llm_generation_status = "processing"
        settings = {}

    elif job_type == "export":
        if quiz.export_status == "completed" and quiz.canvas_quiz_id:
            logger.warning(
                "quiz_already_exported",
                quiz_id=str(quiz_id),
                canvas_quiz_id=quiz.canvas_quiz_id,
            )
            return {
                "already_exported": True,
                "canvas_quiz_id": quiz.canvas_quiz_id,
                "course_id": quiz.canvas_course_id,
                "title": quiz.title,
            }
        if quiz.export_status == "processing":
            logger.warning(
                "export_already_processing",
                quiz_id=str(quiz_id),
                current_status=quiz.export_status,
            )
            return None
        quiz.export_status = "processing"
        settings = {
            "already_exported": False,
            "course_id": quiz.canvas_course_id,
            "title": quiz.title,
        }

    else:
        logger.error("invalid_job_type", job_type=job_type)
        return None

    await session.flush()
    return settings


async def update_quiz_status(
    session: AsyncSession,
    quiz_id: UUID,
    status_type: str,
    status_value: str,
    **additional_fields: Any,
) -> None:
    """
    Update quiz status fields in a transaction.

    Args:
        session: Async database session
        quiz_id: Quiz ID
        status_type: Type of status ('content_extraction', 'llm_generation', 'export')
        status_value: Status value ('pending', 'processing', 'completed', 'failed')
        **additional_fields: Additional fields to update (e.g., extracted_content, canvas_quiz_id)
    """
    quiz = await get_quiz_for_update(session, quiz_id)
    if not quiz:
        logger.error("quiz_not_found_during_status_update", quiz_id=str(quiz_id))
        return

    # Update status based on type
    if status_type == "content_extraction":
        quiz.content_extraction_status = status_value
        if status_value == "completed" and "extracted_content" in additional_fields:
            quiz.extracted_content = additional_fields["extracted_content"]
            quiz.content_extracted_at = datetime.now(timezone.utc)

    elif status_type == "llm_generation":
        quiz.llm_generation_status = status_value

    elif status_type == "export":
        quiz.export_status = status_value
        if status_value == "completed":
            if "canvas_quiz_id" in additional_fields:
                quiz.canvas_quiz_id = additional_fields["canvas_quiz_id"]
            quiz.exported_at = datetime.now(timezone.utc)

    logger.debug(
        "quiz_status_updated",
        quiz_id=str(quiz_id),
        status_type=status_type,
        status_value=status_value,
    )
