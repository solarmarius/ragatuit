"""Validation functions for quiz operations."""

from collections.abc import Callable
from uuid import UUID

from sqlmodel import Session

from src.exceptions import ResourceNotFoundError

from .models import Quiz
from .schemas import Status


def is_quiz_owned_by_user(quiz: Quiz, user_id: UUID) -> bool:
    """
    Check if quiz is owned by the specified user.

    Args:
        quiz: Quiz instance
        user_id: User ID to check ownership

    Returns:
        True if user owns the quiz
    """
    return quiz.owner_id == user_id


def is_quiz_ready_for_extraction(quiz: Quiz) -> bool:
    """
    Check if quiz is ready for content extraction.

    Args:
        quiz: Quiz instance

    Returns:
        True if quiz can be used for content extraction
    """
    return quiz.content_extraction_status != Status.PROCESSING


def is_quiz_ready_for_generation(quiz: Quiz) -> bool:
    """
    Check if quiz is ready for question generation.

    Args:
        quiz: Quiz instance

    Returns:
        True if quiz can be used for question generation
    """
    return (
        quiz.content_extraction_status == Status.COMPLETED
        and quiz.llm_generation_status != Status.PROCESSING
    )


def is_quiz_ready_for_export(quiz: Quiz) -> bool:
    """
    Check if quiz is ready for Canvas export.

    Args:
        quiz: Quiz instance

    Returns:
        True if quiz can be exported to Canvas
    """
    return (
        not (quiz.export_status == Status.COMPLETED and quiz.canvas_quiz_id)
        and quiz.export_status != Status.PROCESSING
    )


def verify_quiz_ownership(session: Session, quiz_id: UUID, user_id: UUID) -> Quiz:
    """
    Verify that a user owns a quiz.

    Args:
        session: Database session
        quiz_id: Quiz ID
        user_id: User ID to verify ownership

    Returns:
        Quiz instance if ownership verified

    Raises:
        ResourceNotFoundError: If quiz not found or user doesn't own it
    """
    quiz = session.get(Quiz, quiz_id)
    if not quiz or not is_quiz_owned_by_user(quiz, user_id):
        raise ResourceNotFoundError("Quiz")
    return quiz


def create_extraction_validator() -> Callable[[Quiz], bool]:
    """
    Create a validator function for content extraction readiness.

    Returns:
        Function that validates quiz for content extraction
    """

    def validate_for_extraction(quiz: Quiz) -> bool:
        """
        Validate quiz for content extraction.

        Args:
            quiz: Quiz to validate

        Returns:
            True if quiz is ready for content extraction
        """
        return is_quiz_ready_for_extraction(quiz)

    return validate_for_extraction


def create_generation_validator() -> Callable[[Quiz], bool]:
    """
    Create a validator function for question generation readiness.

    Returns:
        Function that validates quiz for question generation
    """

    def validate_for_generation(quiz: Quiz) -> bool:
        """
        Validate quiz for question generation.

        Args:
            quiz: Quiz to validate

        Returns:
            True if quiz is ready for question generation
        """
        return is_quiz_ready_for_generation(quiz)

    return validate_for_generation


def create_export_validator() -> Callable[[Quiz], bool]:
    """
    Create a validator function for Canvas export readiness.

    Returns:
        Function that validates quiz for Canvas export
    """

    def validate_for_export(quiz: Quiz) -> bool:
        """
        Validate quiz for Canvas export.

        Args:
            quiz: Quiz to validate

        Returns:
            True if quiz is ready for export
        """
        return is_quiz_ready_for_export(quiz)

    return validate_for_export


def validate_quiz_for_content_extraction(
    session: Session, quiz_id: UUID, user_id: UUID
) -> Quiz:
    """
    Validate quiz is ready for content extraction.

    Args:
        session: Database session
        quiz_id: Quiz ID
        user_id: User ID (must be owner)

    Returns:
        Quiz instance if validation passes

    Raises:
        ResourceNotFoundError: If quiz not found or user doesn't own it
        ValueError: If quiz status doesn't allow extraction
    """
    quiz = verify_quiz_ownership(session, quiz_id, user_id)

    if not is_quiz_ready_for_extraction(quiz):
        raise ValueError("Content extraction is already in progress")

    return quiz


def validate_quiz_for_question_generation(
    session: Session, quiz_id: UUID, user_id: UUID
) -> Quiz:
    """
    Validate quiz is ready for question generation.

    Args:
        session: Database session
        quiz_id: Quiz ID
        user_id: User ID (must be owner)

    Returns:
        Quiz instance if validation passes

    Raises:
        ResourceNotFoundError: If quiz not found or user doesn't own it
        ValueError: If quiz status doesn't allow generation
    """
    quiz = verify_quiz_ownership(session, quiz_id, user_id)

    if not is_quiz_ready_for_generation(quiz):
        if quiz.content_extraction_status != Status.COMPLETED:
            raise ValueError(
                "Content extraction must be completed before generating questions"
            )
        if quiz.llm_generation_status == Status.PROCESSING:
            raise ValueError("Question generation is already in progress")

    return quiz


def validate_quiz_for_export(session: Session, quiz_id: UUID, user_id: UUID) -> Quiz:
    """
    Validate quiz is ready for Canvas export.

    Args:
        session: Database session
        quiz_id: Quiz ID
        user_id: User ID (must be owner)

    Returns:
        Quiz instance if validation passes

    Raises:
        ResourceNotFoundError: If quiz not found or user doesn't own it
        ValueError: If quiz status doesn't allow export
    """
    quiz = verify_quiz_ownership(session, quiz_id, user_id)

    if not is_quiz_ready_for_export(quiz):
        if quiz.export_status == Status.COMPLETED and quiz.canvas_quiz_id:
            raise ValueError("Quiz has already been exported to Canvas")
        if quiz.export_status == Status.PROCESSING:
            raise ValueError("Quiz export is already in progress")

    return quiz
