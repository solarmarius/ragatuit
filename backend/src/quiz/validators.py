"""Validation functions for quiz operations."""

from collections.abc import Callable
from uuid import UUID

from sqlmodel import Session

from src.exceptions import ResourceNotFoundError

from .models import Quiz
from .schemas import QuizStatus


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
    return quiz.status in [QuizStatus.CREATED, QuizStatus.FAILED]


def is_quiz_ready_for_generation(quiz: Quiz) -> bool:
    """
    Check if quiz is ready for question generation.

    Args:
        quiz: Quiz instance

    Returns:
        True if quiz can be used for question generation
    """
    # Can generate questions after content extraction completes or from failed state
    return quiz.status in [QuizStatus.EXTRACTING_CONTENT, QuizStatus.FAILED]


def is_quiz_ready_for_export(quiz: Quiz) -> bool:
    """
    Check if quiz is ready for Canvas export.

    Args:
        quiz: Quiz instance

    Returns:
        True if quiz can be exported to Canvas
    """
    return quiz.status == QuizStatus.READY_FOR_REVIEW


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
        if quiz.status not in [QuizStatus.EXTRACTING_CONTENT, QuizStatus.FAILED]:
            raise ValueError(
                "Content extraction must be completed before generating questions"
            )
        if quiz.status == QuizStatus.GENERATING_QUESTIONS:
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
        if quiz.status == QuizStatus.PUBLISHED and quiz.canvas_quiz_id:
            raise ValueError("Quiz has already been exported to Canvas")
        if quiz.status == QuizStatus.EXPORTING_TO_CANVAS:
            raise ValueError("Quiz export is already in progress")

    return quiz


def is_quiz_ready_for_retry(quiz: Quiz) -> bool:
    """
    Check if quiz can be retried.

    Args:
        quiz: Quiz instance

    Returns:
        True if quiz can be retried
    """
    return quiz.status == QuizStatus.FAILED


def validate_status_transition(current: QuizStatus, target: QuizStatus) -> bool:
    """
    Validate if status transition is allowed.

    Args:
        current: Current quiz status
        target: Target quiz status

    Returns:
        True if transition is allowed
    """
    # Define valid transitions
    valid_transitions = {
        QuizStatus.CREATED: [QuizStatus.EXTRACTING_CONTENT, QuizStatus.FAILED],
        QuizStatus.EXTRACTING_CONTENT: [
            QuizStatus.EXTRACTING_CONTENT,  # Allow self-transition to save extracted content
            QuizStatus.READY_FOR_REVIEW,
            QuizStatus.GENERATING_QUESTIONS,
            QuizStatus.FAILED,
        ],
        QuizStatus.GENERATING_QUESTIONS: [
            QuizStatus.READY_FOR_REVIEW,
            QuizStatus.FAILED,
        ],
        QuizStatus.READY_FOR_REVIEW: [
            QuizStatus.GENERATING_QUESTIONS,
            QuizStatus.EXPORTING_TO_CANVAS,
            QuizStatus.FAILED,
        ],
        QuizStatus.EXPORTING_TO_CANVAS: [QuizStatus.PUBLISHED, QuizStatus.FAILED],
        QuizStatus.PUBLISHED: [QuizStatus.FAILED],  # Can fail after publishing
        QuizStatus.FAILED: [
            QuizStatus.CREATED,
            QuizStatus.EXTRACTING_CONTENT,
            QuizStatus.GENERATING_QUESTIONS,
            QuizStatus.READY_FOR_REVIEW,
        ],  # Can retry from various states
    }

    allowed_next_states = valid_transitions.get(current, [])
    return target in allowed_next_states


def get_quiz_processing_phase(quiz: Quiz) -> str:
    """
    Get human-readable processing phase.

    Args:
        quiz: Quiz instance

    Returns:
        Human-readable phase description
    """
    phase_map = {
        QuizStatus.CREATED: "Ready to start",
        QuizStatus.EXTRACTING_CONTENT: "Extracting content from modules",
        QuizStatus.GENERATING_QUESTIONS: "Generating questions with AI",
        QuizStatus.READY_FOR_REVIEW: "Ready for question review",
        QuizStatus.EXPORTING_TO_CANVAS: "Exporting to Canvas",
        QuizStatus.PUBLISHED: "Published to Canvas",
        QuizStatus.FAILED: "Generation failed",
    }
    return phase_map.get(quiz.status, "Unknown")


def is_quiz_processing(quiz: Quiz) -> bool:
    """
    Check if quiz is currently being processed.

    Args:
        quiz: Quiz instance

    Returns:
        True if quiz is in an active processing state
    """
    return quiz.status in [
        QuizStatus.EXTRACTING_CONTENT,
        QuizStatus.GENERATING_QUESTIONS,
        QuizStatus.EXPORTING_TO_CANVAS,
    ]


def is_quiz_complete(quiz: Quiz) -> bool:
    """
    Check if quiz processing is complete.

    Args:
        quiz: Quiz instance

    Returns:
        True if quiz has completed all processing
    """
    return quiz.status in [QuizStatus.READY_FOR_REVIEW, QuizStatus.PUBLISHED]
