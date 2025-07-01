"""Question persistence service for database operations."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, cast
from sqlmodel import asc, func, select

from src.database import get_async_session, transaction
from src.logging_config import get_logger

from ..types import (
    Question,
    QuestionType,
    get_question_type_registry,
)

logger = get_logger("persistence_service")


class QuestionPersistenceService:
    """
    Service for managing question persistence and database operations.

    Handles creating, updating, retrieving, and deleting questions with
    support for the new polymorphic question system.
    """

    def __init__(self) -> None:
        """Initialize question persistence service."""
        self.question_registry = get_question_type_registry()

    async def save_questions(
        self,
        quiz_id: UUID,
        question_type: QuestionType,
        questions_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Save a batch of questions to the database.

        Args:
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

        try:
            async with transaction(isolation_level="SERIALIZABLE") as session:
                saved_questions = []
                validation_errors = []

                for i, question_data in enumerate(questions_data):
                    try:
                        # Validate question data using question type implementation
                        question_impl = self.question_registry.get_question_type(
                            question_type
                        )
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

                        saved_questions.append(question)

                    except Exception as e:
                        validation_errors.append(
                            {
                                "index": i,
                                "error": str(e),
                                "question_data": question_data,
                            }
                        )

                        logger.warning(
                            "question_validation_failed",
                            quiz_id=str(quiz_id),
                            question_index=i,
                            error=str(e),
                        )

                # Save valid questions
                if saved_questions:
                    session.add_all(saved_questions)
                    await session.flush()  # Get IDs assigned

                result = {
                    "questions_saved": len(saved_questions),
                    "questions_attempted": len(questions_data),
                    "validation_errors": len(validation_errors),
                    "success_rate": len(saved_questions) / len(questions_data)
                    if questions_data
                    else 0,
                    "saved_question_ids": [str(q.id) for q in saved_questions],
                    "errors": validation_errors[:10],  # Limit error details
                }

                logger.info(
                    "questions_save_completed",
                    quiz_id=str(quiz_id),
                    question_type=question_type.value,
                    questions_saved=result["questions_saved"],
                    validation_errors=result["validation_errors"],
                    success_rate=result["success_rate"],
                )

                return result

        except Exception as e:
            logger.error(
                "questions_save_failed",
                quiz_id=str(quiz_id),
                question_type=question_type.value,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_questions_by_quiz(
        self,
        quiz_id: UUID,
        question_type: QuestionType | None = None,
        approved_only: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Question]:
        """
        Get questions for a quiz.

        Args:
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

        try:
            async with get_async_session() as session:
                # Build query
                statement = select(Question).where(Question.quiz_id == quiz_id)

                if question_type:
                    statement = statement.where(Question.question_type == question_type)

                if approved_only:
                    statement = statement.where(Question.is_approved)

                # Add ordering
                statement = statement.order_by(
                    asc(Question.created_at), asc(Question.id)
                )

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

        except Exception as e:
            logger.error(
                "questions_retrieval_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_question_by_id(self, question_id: UUID) -> Question | None:
        """
        Get a specific question by ID.

        Args:
            question_id: Question identifier

        Returns:
            Question or None if not found
        """
        try:
            async with get_async_session() as session:
                question = await session.get(Question, question_id)

                logger.debug(
                    "question_retrieval_by_id",
                    question_id=str(question_id),
                    found=question is not None,
                )

                return question

        except Exception as e:
            logger.error(
                "question_retrieval_by_id_failed",
                question_id=str(question_id),
                error=str(e),
                exc_info=True,
            )
            raise

    async def update_question(
        self, question_id: UUID, updates: dict[str, Any]
    ) -> Question | None:
        """
        Update a question.

        Args:
            question_id: Question identifier
            updates: Dictionary of updates to apply

        Returns:
            Updated question or None if not found
        """
        logger.info(
            "question_update_started",
            question_id=str(question_id),
            update_fields=list(updates.keys()),
        )

        try:
            async with transaction() as session:
                question = await session.get(Question, question_id)

                if not question:
                    logger.warning(
                        "question_update_not_found", question_id=str(question_id)
                    )
                    return None

                # Handle question data updates
                if "question_data" in updates:
                    # Validate new question data
                    question_impl = self.question_registry.get_question_type(
                        question.question_type
                    )
                    validated_data = question_impl.validate_data(
                        updates["question_data"]
                    )
                    question.question_data = validated_data.dict()

                # Handle other field updates
                for field, value in updates.items():
                    if field != "question_data" and hasattr(question, field):
                        setattr(question, field, value)

                # Update timestamp
                question.updated_at = datetime.now(timezone.utc)

                session.add(question)
                await session.flush()
                await session.refresh(question)

                logger.info(
                    "question_update_completed",
                    question_id=str(question_id),
                    updated_fields=list(updates.keys()),
                )

                return question

        except Exception as e:
            logger.error(
                "question_update_failed",
                question_id=str(question_id),
                error=str(e),
                exc_info=True,
            )
            raise

    async def approve_question(self, question_id: UUID) -> Question | None:
        """
        Approve a question.

        Args:
            question_id: Question identifier

        Returns:
            Approved question or None if not found
        """
        logger.info("question_approval_started", question_id=str(question_id))

        try:
            updates = {"is_approved": True, "approved_at": datetime.now(timezone.utc)}

            question = await self.update_question(question_id, updates)

            if question:
                logger.info(
                    "question_approved",
                    question_id=str(question_id),
                    quiz_id=str(question.quiz_id),
                    question_type=question.question_type.value,
                )

            return question

        except Exception as e:
            logger.error(
                "question_approval_failed",
                question_id=str(question_id),
                error=str(e),
                exc_info=True,
            )
            raise

    async def delete_question(self, question_id: UUID, quiz_owner_id: UUID) -> bool:
        """
        Delete a question with ownership verification.

        Args:
            question_id: Question identifier
            quiz_owner_id: Quiz owner user ID for verification

        Returns:
            True if deleted, False if not found or unauthorized
        """
        logger.info(
            "question_deletion_started",
            question_id=str(question_id),
            quiz_owner_id=str(quiz_owner_id),
        )

        try:
            async with transaction() as session:
                question = await session.get(Question, question_id)

                if not question:
                    logger.warning(
                        "question_deletion_not_found", question_id=str(question_id)
                    )
                    return False

                # Verify quiz ownership
                from src.quiz.models import Quiz

                quiz = await session.get(Quiz, question.quiz_id)

                if not quiz or quiz.owner_id != quiz_owner_id:
                    logger.warning(
                        "question_deletion_unauthorized",
                        question_id=str(question_id),
                        quiz_id=str(question.quiz_id),
                        quiz_owner_id=str(quiz_owner_id),
                    )
                    return False

                await session.delete(question)

                logger.info(
                    "question_deleted",
                    question_id=str(question_id),
                    quiz_id=str(question.quiz_id),
                    quiz_owner_id=str(quiz_owner_id),
                )

                return True

        except Exception as e:
            logger.error(
                "question_deletion_failed",
                question_id=str(question_id),
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_question_statistics(
        self,
        quiz_id: UUID | None = None,
        question_type: QuestionType | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Get statistics about questions.

        Args:
            quiz_id: Filter by quiz (optional)
            question_type: Filter by question type (optional)
            user_id: Filter by user (optional)

        Returns:
            Statistics dictionary
        """
        logger.debug(
            "question_statistics_requested",
            quiz_id=str(quiz_id) if quiz_id else None,
            question_type=question_type.value if question_type else None,
            user_id=str(user_id) if user_id else None,
        )

        try:
            async with get_async_session() as session:
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
                approval_rate = (
                    approved_questions / total_questions if total_questions > 0 else 0.0
                )

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

        except Exception as e:
            logger.error("question_statistics_failed", error=str(e), exc_info=True)
            raise

    def format_question_for_display(self, question: Question) -> dict[str, Any]:
        """
        Format a question for display/API response.

        Args:
            question: Question to format

        Returns:
            Formatted question data
        """
        try:
            # Get question type implementation
            question_impl = self.question_registry.get_question_type(
                question.question_type
            )

            # Get typed data
            typed_data = question.get_typed_data(self.question_registry)

            # Format for display
            display_data = question_impl.format_for_display(typed_data)

            # Add metadata
            display_data.update(
                {
                    "id": str(question.id),
                    "quiz_id": str(question.quiz_id),
                    "question_type": question.question_type.value,
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
                }
            )

            return display_data

        except Exception as e:
            logger.error(
                "question_formatting_failed",
                question_id=str(question.id),
                question_type=question.question_type.value,
                error=str(e),
                exc_info=True,
            )

            # Return basic format as fallback
            return {
                "id": str(question.id),
                "quiz_id": str(question.quiz_id),
                "question_type": question.question_type.value,
                "question_data": question.question_data,
                "error": f"Formatting failed: {str(e)}",
            }

    def format_question_for_canvas(self, question: Question) -> dict[str, Any]:
        """
        Format a question for Canvas LMS export.

        Args:
            question: Question to format

        Returns:
            Canvas-formatted question data
        """
        try:
            # Get question type implementation
            question_impl = self.question_registry.get_question_type(
                question.question_type
            )

            # Get typed data
            typed_data = question.get_typed_data(self.question_registry)

            # Format for Canvas
            canvas_data = question_impl.format_for_canvas(typed_data)

            # Add Canvas metadata
            canvas_data.update(
                {
                    "quiz_question_id": str(question.id),
                    "points_possible": canvas_data.get("points_possible", 1),
                }
            )

            return canvas_data

        except Exception as e:
            logger.error(
                "question_canvas_formatting_failed",
                question_id=str(question.id),
                question_type=question.question_type.value,
                error=str(e),
                exc_info=True,
            )
            raise
