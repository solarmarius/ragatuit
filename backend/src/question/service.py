"""Question service functions following the quiz module pattern."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import asc, select

# Removed unused transaction import
from src.config import get_logger

from .formatters import format_questions_batch
from .types import (
    Question,
    QuestionType,
    get_question_type_registry,
)

logger = get_logger("question_service")


async def save_questions(
    session: AsyncSession,
    quiz_id: UUID,
    question_type: QuestionType,
    questions_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Save a batch of questions to the database.

    Args:
        session: Database session
        quiz_id: Quiz identifier
        question_type: Type of questions being saved
        questions_data: List of question data dictionaries

    Returns:
        Dictionary with save results
    """
    logger.info(
        "questions_save_started",
        quiz_id=str(quiz_id),
        question_type=question_type.value,
        question_count=len(questions_data),
    )

    saved_questions = []
    validation_errors = []
    question_registry = get_question_type_registry()

    for i, question_data in enumerate(questions_data):
        try:
            # Validate question data using question type implementation
            question_impl = question_registry.get_question_type(question_type)
            validated_data = question_impl.validate_data(question_data)

            # Create question with polymorphic data
            question = Question(
                quiz_id=quiz_id,
                question_type=question_type,
                question_data=validated_data.dict(),
                difficulty=question_data.get("difficulty"),
                tags=question_data.get("tags"),
                is_approved=False,
            )

            session.add(question)
            saved_questions.append(question)

        except Exception as e:
            error_msg = f"Question {i + 1}: {str(e)}"
            validation_errors.append(error_msg)
            logger.warning(
                "question_validation_failed",
                quiz_id=str(quiz_id),
                question_index=i,
                error=str(e),
            )

    if validation_errors:
        return {
            "success": False,
            "saved_count": 0,
            "total_count": len(questions_data),
            "errors": validation_errors,
        }

    # Commit all questions
    await session.commit()

    # Refresh all questions to get IDs
    for question in saved_questions:
        await session.refresh(question)

    logger.info(
        "questions_save_completed",
        quiz_id=str(quiz_id),
        saved_count=len(saved_questions),
        total_count=len(questions_data),
    )

    return {
        "success": True,
        "saved_count": len(saved_questions),
        "total_count": len(questions_data),
        "question_ids": [str(q.id) for q in saved_questions],
        "errors": [],
    }


async def get_questions_by_quiz(
    session: AsyncSession,
    quiz_id: UUID,
    question_type: QuestionType | None = None,
    approved_only: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> list[Question]:
    """
    Get questions for a quiz.

    Args:
        session: Database session
        quiz_id: Quiz identifier
        question_type: Filter by question type (optional)
        approved_only: Only return approved questions
        limit: Maximum number of questions to return
        offset: Number of questions to skip

    Returns:
        List of questions
    """
    logger.debug(
        "questions_retrieval_started",
        quiz_id=str(quiz_id),
        question_type=question_type.value if question_type else None,
        approved_only=approved_only,
        limit=limit,
        offset=offset,
    )

    # Build query
    statement = select(Question).where(Question.quiz_id == quiz_id)

    if question_type:
        statement = statement.where(Question.question_type == question_type)

    if approved_only:
        statement = statement.where(Question.is_approved)

    # Add ordering
    statement = statement.order_by(asc(Question.created_at), asc(Question.id))

    # Add pagination
    if offset > 0:
        statement = statement.offset(offset)

    if limit:
        statement = statement.limit(limit)

    result = await session.execute(statement)
    questions = list(result.scalars().all())

    logger.debug(
        "questions_retrieval_completed",
        quiz_id=str(quiz_id),
        questions_found=len(questions),
    )

    return questions


async def get_formatted_questions_by_quiz(
    session: AsyncSession,
    quiz_id: UUID,
    question_type: QuestionType | None = None,
    approved_only: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Get questions for a quiz and format them for display in a single session.

    Args:
        session: Database session
        quiz_id: Quiz identifier
        question_type: Filter by question type (optional)
        approved_only: Only return approved questions
        limit: Maximum number of questions to return
        offset: Number of questions to skip

    Returns:
        List of formatted question dictionaries
    """
    logger.debug(
        "formatted_questions_retrieval_started",
        quiz_id=str(quiz_id),
        question_type=question_type.value if question_type else None,
        approved_only=approved_only,
        limit=limit,
        offset=offset,
    )

    # Get questions
    questions = await get_questions_by_quiz(
        session, quiz_id, question_type, approved_only, limit, offset
    )

    # Format questions using the new formatter module
    formatted_questions = format_questions_batch(questions)

    logger.debug(
        "formatted_questions_retrieval_completed",
        quiz_id=str(quiz_id),
        questions_found=len(formatted_questions),
    )

    return formatted_questions


async def get_question_by_id(
    session: AsyncSession, question_id: UUID
) -> Question | None:
    """
    Get a specific question by ID.

    Args:
        session: Database session
        question_id: Question identifier

    Returns:
        Question instance or None if not found
    """
    result = await session.execute(select(Question).where(Question.id == question_id))
    return result.scalar_one_or_none()


async def approve_question(session: AsyncSession, question_id: UUID) -> Question | None:
    """
    Approve a question by ID.

    Args:
        session: Database session
        question_id: Question identifier

    Returns:
        Updated question instance or None if not found
    """
    logger.debug("question_approval_started", question_id=str(question_id))

    # Get the question
    question = await get_question_by_id(session, question_id)
    if not question:
        logger.warning("question_not_found_for_approval", question_id=str(question_id))
        return None

    # Update approval status
    question.is_approved = True
    question.approved_at = datetime.now(timezone.utc)
    question.updated_at = datetime.now(timezone.utc)

    session.add(question)
    await session.commit()
    await session.refresh(question)

    logger.info("question_approved_successfully", question_id=str(question_id))
    return question


async def update_question(
    session: AsyncSession,
    question_id: UUID,
    updates: dict[str, Any],
) -> Question | None:
    """
    Update a question with the provided data.

    Args:
        session: Database session
        question_id: Question identifier
        updates: Dictionary of fields to update

    Returns:
        Updated question instance or None if not found
    """
    logger.debug("question_update_started", question_id=str(question_id))

    # Get the question
    question = await get_question_by_id(session, question_id)
    if not question:
        logger.warning("question_not_found_for_update", question_id=str(question_id))
        return None

    # Apply updates
    for field, value in updates.items():
        if hasattr(question, field):
            setattr(question, field, value)

    question.updated_at = datetime.now(timezone.utc)

    session.add(question)
    await session.commit()
    await session.refresh(question)

    logger.info("question_updated_successfully", question_id=str(question_id))
    return question


async def delete_question(
    session: AsyncSession, question_id: UUID, quiz_owner_id: UUID
) -> bool:
    """
    Delete a question by ID (with ownership verification).

    Args:
        session: Database session
        question_id: Question identifier
        quiz_owner_id: Quiz owner ID for verification

    Returns:
        True if deleted, False if not found or unauthorized
    """
    logger.debug("question_deletion_started", question_id=str(question_id))

    # Get question with quiz ownership check
    from src.quiz.models import Quiz

    result = await session.execute(
        select(Question)
        .join(Quiz)
        .where(Question.id == question_id)
        .where(Quiz.owner_id == quiz_owner_id)
    )
    question = result.scalar_one_or_none()

    if not question:
        logger.warning("question_not_found_for_deletion", question_id=str(question_id))
        return False

    await session.delete(question)
    await session.commit()

    logger.info("question_deleted_successfully", question_id=str(question_id))
    return True


async def prepare_questions_for_export(quiz_id: UUID) -> list[dict[str, Any]]:
    """
    Load approved questions and extract their data for export.

    This function loads questions in their own session context and extracts
    all needed data before the session closes to avoid DetachedInstanceError.

    Args:
        quiz_id: UUID of the quiz to load questions for

    Returns:
        List of question data dictionaries ready for export
    """
    from src.database import get_async_session
    from src.question.types import get_question_type_registry

    async with get_async_session() as async_session:
        # Load approved questions with all needed data
        approved_questions = await get_questions_by_quiz(
            async_session, quiz_id=quiz_id, approved_only=True
        )

        if not approved_questions:
            logger.error("no_approved_questions_for_export", quiz_id=str(quiz_id))
            return []

        # Extract all data while questions are still bound to session
        question_registry = get_question_type_registry()
        question_data = []

        for question in approved_questions:
            try:
                question_impl = question_registry.get_question_type(
                    question.question_type
                )
                typed_data = question.get_typed_data(question_registry)
                exported_data = question_impl.format_for_export(typed_data)
                exported_data["id"] = question.id
                question_data.append(exported_data)
            except ValueError as e:
                # Log unsupported question types
                logger.warning(
                    "unsupported_question_type_for_export",
                    quiz_id=str(quiz_id),
                    question_id=str(question.id),
                    question_type=question.question_type.value,
                    error=str(e),
                )

        logger.debug(
            "question_data_extracted_for_export",
            quiz_id=str(quiz_id),
            questions_extracted=len(question_data),
        )

        return question_data


async def update_question_canvas_ids(
    session: AsyncSession,
    question_data_list: list[dict[str, Any]],
    export_results: list[dict[str, Any]],
) -> None:
    """
    Update question Canvas item IDs after successful export.

    Args:
        session: Database session
        question_data_list: List of question data used for export
        export_results: List of export results from Canvas API
    """
    logger.debug(
        "updating_question_canvas_ids",
        question_count=len(question_data_list),
        result_count=len(export_results),
    )

    for question_data, export_result in zip(
        question_data_list, export_results, strict=False
    ):
        if export_result.get("success"):
            question_obj = await session.get(Question, question_data["id"])
            if question_obj:
                question_obj.canvas_item_id = export_result.get("item_id")

    logger.debug("question_canvas_ids_updated")
