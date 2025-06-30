"""Quiz service for business logic."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from app.exceptions import ResourceNotFoundError
from app.logging_config import get_logger

from .models import Quiz
from .schemas import QuizCreate

logger = get_logger("quiz_service")


class QuizService:
    """Service class for quiz operations."""

    def __init__(self, session: Session):
        self.session = session

    def create_quiz(self, quiz_create: QuizCreate, owner_id: UUID) -> Quiz:
        """
        Create a new quiz.

        Args:
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
            str(module_id): name
            for module_id, name in quiz_create.selected_modules.items()
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

        self.session.add(quiz)
        self.session.commit()
        self.session.refresh(quiz)

        logger.info(
            "quiz_created_successfully",
            quiz_id=str(quiz.id),
            owner_id=str(owner_id),
        )

        return quiz

    def get_quiz_by_id(self, quiz_id: UUID) -> Quiz | None:
        """
        Get quiz by ID.

        Args:
            quiz_id: Quiz ID

        Returns:
            Quiz instance or None
        """
        return self.session.get(Quiz, quiz_id)

    def get_user_quizzes(self, user_id: UUID) -> list[Quiz]:
        """
        Get all quizzes for a user.

        Args:
            user_id: User ID

        Returns:
            List of user's quizzes
        """
        statement = (
            select(Quiz)
            .where(Quiz.owner_id == user_id)
            .order_by(Quiz.created_at.desc())  # type: ignore
        )
        return list(self.session.exec(statement).all())

    def delete_quiz(self, quiz_id: UUID, user_id: UUID) -> bool:
        """
        Delete a quiz if owned by the user.

        Args:
            quiz_id: Quiz ID
            user_id: User ID (must be owner)

        Returns:
            True if deleted, False if not found or not owner
        """
        quiz = self.session.get(Quiz, quiz_id)
        if quiz and quiz.owner_id == user_id:
            self.session.delete(quiz)
            self.session.commit()
            logger.info(
                "quiz_deleted",
                quiz_id=str(quiz_id),
                user_id=str(user_id),
            )
            return True
        return False

    async def get_quiz_for_update(
        self, session: AsyncSession, quiz_id: UUID
    ) -> Quiz | None:
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
        self, session: AsyncSession, quiz_id: UUID
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

    def update_quiz_content(
        self,
        quiz_id: UUID,
        status: str,
        extracted_content: dict[str, Any] | None = None,
        content_extracted_at: datetime | None = None,
    ) -> Quiz:
        """
        Update quiz content extraction results.

        Args:
            quiz_id: Quiz ID
            status: Content extraction status
            extracted_content: Extracted content data
            content_extracted_at: Timestamp of extraction

        Returns:
            Updated quiz

        Raises:
            ResourceNotFoundError: If quiz not found
        """
        quiz = self.session.get(Quiz, quiz_id)
        if not quiz:
            raise ResourceNotFoundError("Quiz")

        quiz.content_extraction_status = status
        if extracted_content is not None:
            quiz.extracted_content = extracted_content
        if content_extracted_at is not None:
            quiz.content_extracted_at = content_extracted_at

        self.session.add(quiz)
        self.session.commit()
        self.session.refresh(quiz)

        return quiz

    def update_quiz_generation_status(self, quiz_id: UUID, status: str) -> Quiz:
        """
        Update quiz LLM generation status.

        Args:
            quiz_id: Quiz ID
            status: Generation status

        Returns:
            Updated quiz

        Raises:
            ResourceNotFoundError: If quiz not found
        """
        quiz = self.session.get(Quiz, quiz_id)
        if not quiz:
            raise ResourceNotFoundError("Quiz")

        quiz.llm_generation_status = status
        self.session.add(quiz)
        self.session.commit()
        self.session.refresh(quiz)

        return quiz

    def update_quiz_export(
        self,
        quiz_id: UUID,
        status: str,
        canvas_quiz_id: str | None = None,
        exported_at: datetime | None = None,
    ) -> Quiz:
        """
        Update quiz export results.

        Args:
            quiz_id: Quiz ID
            status: Export status
            canvas_quiz_id: Canvas quiz ID after export
            exported_at: Timestamp of export

        Returns:
            Updated quiz

        Raises:
            ResourceNotFoundError: If quiz not found
        """
        quiz = self.session.get(Quiz, quiz_id)
        if not quiz:
            raise ResourceNotFoundError("Quiz")

        quiz.export_status = status
        if canvas_quiz_id is not None:
            quiz.canvas_quiz_id = canvas_quiz_id
        if exported_at is not None:
            quiz.exported_at = exported_at

        self.session.add(quiz)
        self.session.commit()
        self.session.refresh(quiz)

        return quiz
