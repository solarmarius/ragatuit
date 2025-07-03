"""Question formatting utilities using functional approach."""

from collections.abc import Callable
from typing import Any

from src.logging_config import get_logger

from .types import Question, get_question_type_registry

logger = get_logger("question_formatter")


def format_base_fields(question: Question) -> dict[str, Any]:
    """
    Format common question fields shared across all contexts.

    Pure function - same input always produces same output.

    Args:
        question: Question instance

    Returns:
        Dictionary with base question fields
    """
    return {
        "id": str(question.id),
        "quiz_id": str(question.quiz_id),
        "question_type": question.question_type.value,
        "question_data": question.question_data,  # Raw data for API compatibility
        "difficulty": question.difficulty.value if question.difficulty else None,
        "tags": question.tags or [],
        "is_approved": question.is_approved,
        "approved_at": question.approved_at.isoformat()
        if question.approved_at
        else None,
        "created_at": question.created_at.isoformat() if question.created_at else None,
        "updated_at": question.updated_at.isoformat() if question.updated_at else None,
        "canvas_item_id": question.canvas_item_id,
    }


def format_question_display_data(question: Question) -> dict[str, Any]:
    """
    Format question-type-specific display data.

    Args:
        question: Question instance

    Returns:
        Question type-specific display data

    Raises:
        Exception: If formatting fails
    """
    question_registry = get_question_type_registry()
    question_impl = question_registry.get_question_type(question.question_type)

    # Validate and get typed data
    typed_data = question_impl.validate_data(question.question_data)

    # Format for display using question type implementation
    return question_impl.format_for_display(typed_data)


def format_question_for_display(question: Question) -> dict[str, Any]:
    """
    Format a question for API display/response.

    Args:
        question: Question instance to format

    Returns:
        Formatted question dictionary
    """
    try:
        base_fields = format_base_fields(question)
        display_data = format_question_display_data(question)

        return {
            **base_fields,
            **display_data,  # Merge in type-specific display data
        }

    except Exception as e:
        logger.error(
            "question_formatting_failed",
            question_id=str(question.id),
            error=str(e),
        )
        # Return basic question data on formatting failure
        return {
            **format_base_fields(question),
            "formatting_error": str(e),
        }


def format_question_for_export(question: Question) -> dict[str, Any]:
    """
    Format a question for Canvas export.

    Args:
        question: Question instance to format

    Returns:
        Question data formatted for Canvas export

    Raises:
        Exception: If export formatting fails
    """
    question_registry = get_question_type_registry()
    question_impl = question_registry.get_question_type(question.question_type)
    typed_data = question_impl.validate_data(question.question_data)

    # Use Canvas-specific formatting
    return question_impl.format_for_canvas(typed_data)


def format_questions_batch(
    questions: list[Question],
    formatter_func: Callable[[Question], dict[str, Any]] = format_question_for_display,
) -> list[dict[str, Any]]:
    """
    Format multiple questions using the specified formatter function.

    Args:
        questions: List of questions to format
        formatter_func: Function to use for formatting each question

    Returns:
        List of formatted question dictionaries
    """
    return [formatter_func(question) for question in questions]


def create_display_formatter() -> Callable[[Question], dict[str, Any]]:
    """
    Create a display formatter function with error handling.

    Following the pattern from content_extraction/validators.py

    Returns:
        Function that formats questions for display
    """

    def format_for_display(question: Question) -> dict[str, Any]:
        """
        Format question for display with comprehensive error handling.

        Args:
            question: Question to format

        Returns:
            Formatted question data
        """
        return format_question_for_display(question)

    return format_for_display


def create_export_formatter() -> Callable[[Question], dict[str, Any]]:
    """
    Create an export formatter function.

    Returns:
        Function that formats questions for Canvas export
    """

    def format_for_export(question: Question) -> dict[str, Any]:
        """
        Format question for Canvas export.

        Args:
            question: Question to format

        Returns:
            Export-formatted question data

        Raises:
            Exception: If formatting fails
        """
        try:
            return format_question_for_export(question)
        except Exception as e:
            logger.error(
                "question_export_formatting_failed",
                question_id=str(question.id),
                error=str(e),
            )
            raise

    return format_for_export


def create_batch_formatter(
    formatter_func: Callable[[Question], dict[str, Any]] | None = None,
) -> Callable[[list[Question]], list[dict[str, Any]]]:
    """
    Create a batch formatter function.

    Args:
        formatter_func: Optional custom formatter function

    Returns:
        Function that formats multiple questions
    """
    if formatter_func is None:
        formatter_func = format_question_for_display

    def format_batch(questions: list[Question]) -> list[dict[str, Any]]:
        """
        Format multiple questions efficiently.

        Args:
            questions: List of questions to format

        Returns:
            List of formatted question dictionaries
        """
        return format_questions_batch(questions, formatter_func)

    return format_batch
