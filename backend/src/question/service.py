"""Question service functions following the quiz module pattern."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import asc, func, select

# Removed unused transaction import
from src.logging_config import get_logger

from .types import (
    Question,
    # QuestionDifficulty,  # Unused
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

    # Get question type registry
    question_registry = get_question_type_registry()

    # Format questions while in session context
    formatted_questions = []
    for question in questions:
        try:
            # Get question type implementation
            question_impl = question_registry.get_question_type(question.question_type)

            # Validate and get typed data
            typed_data = question_impl.validate_data(question.question_data)

            # Format for display
            display_data = question_impl.format_for_display(typed_data)

            formatted_question = {
                "id": str(question.id),
                "quiz_id": str(question.quiz_id),
                "question_type": question.question_type.value,
                "question_data": question.question_data,  # Include raw data for API compatibility
                "difficulty": question.difficulty.value
                if question.difficulty
                else None,
                "tags": question.tags or [],
                "is_approved": question.is_approved,
                "approved_at": question.approved_at.isoformat()
                if question.approved_at
                else None,
                "created_at": question.created_at.isoformat()
                if question.created_at
                else None,
                "updated_at": question.updated_at.isoformat()
                if question.updated_at
                else None,
                "canvas_item_id": question.canvas_item_id,
                **display_data,  # Merge in the formatted question content for convenience
            }

            formatted_questions.append(formatted_question)

        except Exception as format_error:
            logger.error(
                "question_formatting_failed",
                question_id=str(question.id),
                error=str(format_error),
            )
            # Return basic question data on formatting failure
            formatted_questions.append(
                {
                    "id": str(question.id),
                    "quiz_id": str(question.quiz_id),
                    "question_type": question.question_type.value,
                    "question_data": question.question_data,  # Required by API schema
                    "difficulty": question.difficulty.value
                    if question.difficulty
                    else None,
                    "tags": question.tags or [],
                    "is_approved": question.is_approved,
                    "approved_at": question.approved_at.isoformat()
                    if question.approved_at
                    else None,
                    "created_at": question.created_at.isoformat()
                    if question.created_at
                    else None,
                    "updated_at": question.updated_at.isoformat()
                    if question.updated_at
                    else None,
                    "canvas_item_id": question.canvas_item_id,
                    "formatting_error": str(format_error),
                }
            )

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


async def get_question_statistics(
    session: AsyncSession,
    quiz_id: UUID | None = None,
    question_type: QuestionType | None = None,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Get question statistics.

    Args:
        session: Database session
        quiz_id: Filter by quiz ID (optional)
        question_type: Filter by question type (optional)
        user_id: Filter by user ID (optional)

    Returns:
        Dictionary with statistics
    """
    logger.debug(
        "question_statistics_started",
        quiz_id=str(quiz_id) if quiz_id else None,
        question_type=question_type.value if question_type else None,
        user_id=str(user_id) if user_id else None,
    )

    # Build base query
    statement = select(
        func.count().label("total"),
        func.sum(cast(Question.is_approved, Integer)).label("approved"),
        Question.question_type,
    )

    # Add filters
    if quiz_id:
        statement = statement.where(Question.quiz_id == quiz_id)

    if question_type:
        statement = statement.where(Question.question_type == question_type)

    if user_id:
        # Need to join with quiz to filter by user
        from src.quiz.models import Quiz

        statement = statement.join(Quiz).where(Quiz.owner_id == user_id)

    # Group by question type
    statement = statement.group_by(Question.question_type)

    result = await session.execute(statement)
    rows = result.all()

    # Process results
    total_questions = 0
    approved_questions = 0
    by_question_type: dict[str, dict[str, int | float]] = {}

    for row in rows:
        total = int(row.total or 0)
        approved = int(row.approved or 0)
        question_type_value = row.question_type.value

        total_questions += total
        approved_questions += approved
        by_question_type[question_type_value] = {
            "total": total,
            "approved": approved,
            "approval_rate": approved / total if total > 0 else 0.0,
        }

    # Calculate overall approval rate
    approval_rate = approved_questions / total_questions if total_questions > 0 else 0.0

    statistics = {
        "total_questions": total_questions,
        "approved_questions": approved_questions,
        "by_question_type": by_question_type,
        "approval_rate": approval_rate,
    }

    logger.debug(
        "question_statistics_completed",
        total_questions=statistics["total_questions"],
        approved_questions=statistics["approved_questions"],
        approval_rate=statistics["approval_rate"],
    )

    return statistics


def format_question_for_display(question: Question) -> dict[str, Any]:
    """
    Format a question for display/API response.

    Args:
        question: Question to format

    Returns:
        Formatted question data
    """
    try:
        # Get question type registry
        question_registry = get_question_type_registry()

        # Get question type implementation
        question_impl = question_registry.get_question_type(question.question_type)

        # Validate and get typed data
        typed_data = question_impl.validate_data(question.question_data)

        # Format for display
        display_data = question_impl.format_for_display(typed_data)

        return {
            "id": str(question.id),
            "quiz_id": str(question.quiz_id),
            "question_type": question.question_type.value,
            "question_data": question.question_data,
            "difficulty": question.difficulty.value if question.difficulty else None,
            "tags": question.tags or [],
            "is_approved": question.is_approved,
            "approved_at": question.approved_at.isoformat()
            if question.approved_at
            else None,
            "created_at": question.created_at.isoformat()
            if question.created_at
            else None,
            "updated_at": question.updated_at.isoformat()
            if question.updated_at
            else None,
            "canvas_item_id": question.canvas_item_id,
            **display_data,  # Merge in the formatted question content
        }

    except Exception as e:
        logger.error(
            "question_formatting_failed",
            question_id=str(question.id),
            error=str(e),
        )
        # Return basic question data on error
        return {
            "id": str(question.id),
            "quiz_id": str(question.quiz_id),
            "question_type": question.question_type.value,
            "question_data": question.question_data,
            "difficulty": question.difficulty.value if question.difficulty else None,
            "tags": question.tags or [],
            "is_approved": question.is_approved,
            "approved_at": question.approved_at.isoformat()
            if question.approved_at
            else None,
            "created_at": question.created_at.isoformat()
            if question.created_at
            else None,
            "updated_at": question.updated_at.isoformat()
            if question.updated_at
            else None,
            "canvas_item_id": question.canvas_item_id,
            "formatting_error": str(e),
        }
