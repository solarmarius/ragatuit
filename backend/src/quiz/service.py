"""Quiz service for business logic."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from src.exceptions import ResourceNotFoundError
from src.logging_config import get_logger

from .models import Quiz
from .schemas import QuizCreate, Status

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

    @staticmethod
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

    @staticmethod
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

    def verify_quiz_ownership(self, quiz_id: UUID, user_id: UUID) -> Quiz:
        """
        Verify that a user owns a quiz.

        Args:
            quiz_id: Quiz ID
            user_id: User ID to verify ownership

        Returns:
            Quiz instance if ownership verified

        Raises:
            ResourceNotFoundError: If quiz not found or user doesn't own it
        """
        quiz = self.session.get(Quiz, quiz_id)
        if not quiz or quiz.owner_id != user_id:
            raise ResourceNotFoundError("Quiz")
        return quiz

    def validate_quiz_for_content_extraction(
        self, quiz_id: UUID, user_id: UUID
    ) -> Quiz:
        """
        Validate quiz is ready for content extraction.

        Args:
            quiz_id: Quiz ID
            user_id: User ID (must be owner)

        Returns:
            Quiz instance if validation passes

        Raises:
            ResourceNotFoundError: If quiz not found or user doesn't own it
            ValueError: If quiz status doesn't allow extraction
        """
        quiz = self.verify_quiz_ownership(quiz_id, user_id)

        if quiz.content_extraction_status == Status.PROCESSING:
            raise ValueError("Content extraction is already in progress")

        return quiz

    def validate_quiz_for_question_generation(
        self, quiz_id: UUID, user_id: UUID
    ) -> Quiz:
        """
        Validate quiz is ready for question generation.

        Args:
            quiz_id: Quiz ID
            user_id: User ID (must be owner)

        Returns:
            Quiz instance if validation passes

        Raises:
            ResourceNotFoundError: If quiz not found or user doesn't own it
            ValueError: If quiz status doesn't allow generation
        """
        quiz = self.verify_quiz_ownership(quiz_id, user_id)

        if quiz.content_extraction_status != Status.COMPLETED:
            raise ValueError(
                "Content extraction must be completed before generating questions"
            )

        if quiz.llm_generation_status == Status.PROCESSING:
            raise ValueError("Question generation is already in progress")

        return quiz

    def validate_quiz_for_export(self, quiz_id: UUID, user_id: UUID) -> Quiz:
        """
        Validate quiz is ready for Canvas export.

        Args:
            quiz_id: Quiz ID
            user_id: User ID (must be owner)

        Returns:
            Quiz instance if validation passes

        Raises:
            ResourceNotFoundError: If quiz not found or user doesn't own it
            ValueError: If quiz status doesn't allow export
        """
        quiz = self.verify_quiz_ownership(quiz_id, user_id)

        if quiz.export_status == Status.COMPLETED and quiz.canvas_quiz_id:
            raise ValueError("Quiz has already been exported to Canvas")

        if quiz.export_status == Status.PROCESSING:
            raise ValueError("Quiz export is already in progress")

        return quiz

    def prepare_content_extraction(
        self, quiz_id: UUID, user_id: UUID
    ) -> dict[str, Any]:
        """
        Prepare quiz for content extraction and return module data.

        Args:
            quiz_id: Quiz ID
            user_id: User ID (must be owner)

        Returns:
            Dict with course_id and module_ids for extraction
        """
        quiz = self.validate_quiz_for_content_extraction(quiz_id, user_id)

        # Reset extraction status to pending
        quiz.content_extraction_status = Status.PENDING
        quiz.extracted_content = None
        quiz.content_extracted_at = None
        self.session.add(quiz)
        self.session.commit()

        # Return extraction parameters
        module_ids = [int(module_id) for module_id in quiz.selected_modules.keys()]
        return {
            "course_id": quiz.canvas_course_id,
            "module_ids": module_ids,
        }

    def prepare_question_generation(
        self, quiz_id: UUID, user_id: UUID
    ) -> dict[str, Any]:
        """
        Prepare quiz for question generation and return generation parameters.

        Args:
            quiz_id: Quiz ID
            user_id: User ID (must be owner)

        Returns:
            Dict with generation parameters
        """
        quiz = self.validate_quiz_for_question_generation(quiz_id, user_id)

        # Reset generation status to pending
        quiz.llm_generation_status = Status.PENDING
        self.session.add(quiz)
        self.session.commit()

        return {
            "question_count": quiz.question_count,
            "llm_model": quiz.llm_model,
            "llm_temperature": quiz.llm_temperature,
        }
