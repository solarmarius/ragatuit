"""Question service for business logic."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Integer, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, asc, col, func, select

from app.logging_config import get_logger

from .models import Question
from .schemas import QuestionCreate, QuestionUpdate

logger = get_logger("question_service")


class QuestionService:
    """Service class for question operations."""

    def __init__(self, session: Session):
        self.session = session

    def create_question(self, question_create: QuestionCreate) -> Question:
        """
        Create a new question for a quiz.

        Args:
            question_create: Question creation data

        Returns:
            Created question instance
        """
        logger.info(
            "question_creation_requested",
            quiz_id=str(question_create.quiz_id),
        )

        question_data = question_create.model_dump()
        current_time = datetime.now(timezone.utc)
        question_data["updated_at"] = current_time

        question = Question.model_validate(question_data)
        self.session.add(question)
        self.session.commit()
        self.session.refresh(question)

        logger.info(
            "question_created_successfully",
            question_id=str(question.id),
            quiz_id=str(question.quiz_id),
        )

        return question

    def get_question_by_id(self, question_id: UUID) -> Question | None:
        """
        Get question by ID.

        Args:
            question_id: Question ID

        Returns:
            Question instance or None
        """
        return self.session.get(Question, question_id)

    def get_questions_by_quiz_id(self, quiz_id: UUID) -> list[Question]:
        """
        Get all questions for a quiz.

        Args:
            quiz_id: Quiz ID

        Returns:
            List of questions ordered by creation date
        """
        statement = (
            select(Question)
            .where(Question.quiz_id == quiz_id)
            .order_by(asc(Question.created_at), asc(Question.id))
        )
        return list(self.session.exec(statement).all())

    def update_question(
        self, question_id: UUID, question_update: QuestionUpdate
    ) -> Question | None:
        """
        Update a question.

        Args:
            question_id: Question ID
            question_update: Update data

        Returns:
            Updated question or None if not found
        """
        question = self.session.get(Question, question_id)
        if not question:
            return None

        # Update only provided fields
        update_data = question_update.model_dump(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                setattr(question, field, value)

            question.updated_at = datetime.now(timezone.utc)
            self.session.add(question)
            self.session.commit()
            self.session.refresh(question)

            logger.info(
                "question_updated",
                question_id=str(question_id),
                fields_updated=list(update_data.keys()),
            )

        return question

    def approve_question(self, question_id: UUID) -> Question | None:
        """
        Approve a question.

        Args:
            question_id: Question ID

        Returns:
            Approved question or None if not found
        """
        question = self.session.get(Question, question_id)
        if not question:
            return None

        question.is_approved = True
        question.approved_at = datetime.now(timezone.utc)
        question.updated_at = datetime.now(timezone.utc)

        self.session.add(question)
        self.session.commit()
        self.session.refresh(question)

        logger.info(
            "question_approved",
            question_id=str(question_id),
            quiz_id=str(question.quiz_id),
        )

        return question

    def delete_question(self, question_id: UUID, quiz_owner_id: UUID) -> bool:
        """
        Delete a question with ownership verification.

        Args:
            question_id: Question ID
            quiz_owner_id: User ID (must own the quiz)

        Returns:
            True if deleted, False if not found or not authorized
        """
        question = self.session.get(Question, question_id)
        if not question:
            return False

        # Get the quiz to verify ownership
        from app.quiz.models import Quiz

        quiz = self.session.get(Quiz, question.quiz_id)
        if not quiz or quiz.owner_id != quiz_owner_id:
            return False

        self.session.delete(question)
        self.session.commit()

        logger.info(
            "question_deleted",
            question_id=str(question_id),
            quiz_id=str(question.quiz_id),
            user_id=str(quiz_owner_id),
        )

        return True

    def get_approved_questions_by_quiz_id(self, quiz_id: UUID) -> list[Question]:
        """
        Get all approved questions for a quiz.

        Args:
            quiz_id: Quiz ID

        Returns:
            List of approved questions
        """
        statement = (
            select(Question)
            .where(Question.quiz_id == quiz_id, Question.is_approved == True)  # noqa: E712
            .order_by(asc(Question.created_at))
        )
        return list(self.session.exec(statement).all())

    async def get_approved_questions_by_quiz_id_async(
        self, session: AsyncSession, quiz_id: UUID
    ) -> list[Question]:
        """
        Get all approved questions for a quiz asynchronously.

        Args:
            session: Async database session
            quiz_id: Quiz ID

        Returns:
            List of approved questions
        """
        statement = (
            select(Question)
            .where(Question.quiz_id == quiz_id, Question.is_approved == True)  # noqa: E712
            .order_by(asc(Question.created_at))
        )
        result = await session.execute(statement)
        return list(result.scalars().all())

    def get_question_counts_by_quiz_id(self, quiz_id: UUID) -> dict[str, int]:
        """
        Get question counts for a quiz.

        Args:
            quiz_id: Quiz ID

        Returns:
            Dictionary with 'total' and 'approved' counts
        """
        statement = select(
            func.count(col(Question.id)),
            func.sum(cast(col(Question.is_approved), Integer)),
        ).where(Question.quiz_id == quiz_id)

        result = self.session.exec(statement).first()

        if result:
            total, approved = result
            return {
                "total": total or 0,
                "approved": approved or 0,
            }
        else:
            return {
                "total": 0,
                "approved": 0,
            }
