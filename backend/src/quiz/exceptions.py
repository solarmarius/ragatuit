"""Orchestration-specific exceptions for quiz operations."""

from typing import Any

from src.exceptions import ServiceError

from .schemas import FailureReason


class OrchestrationError(ServiceError):
    """Base exception for orchestration errors."""

    def __init__(self, message: str, quiz_id: str | None = None):
        super().__init__(message, 500)
        self.quiz_id = quiz_id


class ContentInsufficientError(OrchestrationError):
    """Raised when content is insufficient for question generation."""

    def __init__(
        self,
        message: str,
        quiz_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(f"Insufficient content: {message}", quiz_id)
        self.details = details or {}


class AutoTriggerError(OrchestrationError):
    """Raised when auto-trigger question generation fails."""

    def __init__(
        self,
        message: str,
        quiz_id: str | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(f"Auto-trigger failed: {message}", quiz_id)
        self.original_error = original_error


class OrchestrationTimeoutError(OrchestrationError):
    """Raised when orchestration operation times out."""

    def __init__(
        self, operation: str, timeout_seconds: int, quiz_id: str | None = None
    ):
        super().__init__(
            f"{operation} timed out after {timeout_seconds} seconds", quiz_id
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class StatusTransitionError(OrchestrationError):
    """Raised when an invalid status transition is attempted."""

    def __init__(
        self, current_status: str, target_status: str, quiz_id: str | None = None
    ):
        super().__init__(
            f"Invalid status transition from {current_status} to {target_status}",
            quiz_id,
        )
        self.current_status = current_status
        self.target_status = target_status


def categorize_generation_error(
    exception: Exception | None, error_message: str | None = None
) -> FailureReason:
    """
    Categorize generation errors into appropriate failure reasons.

    Args:
        exception: The exception that occurred during generation
        error_message: Optional error message from the generation process

    Returns:
        Appropriate FailureReason for the error type
    """
    if isinstance(exception, ContentInsufficientError):
        # This indicates no meaningful content was available for generation
        return FailureReason.NO_CONTENT_FOUND
    elif isinstance(exception, OrchestrationTimeoutError):
        # Categorize timeout based on operation type
        operation = getattr(exception, "operation", "unknown")
        if "content_extraction" in operation:
            return FailureReason.CONTENT_EXTRACTION_ERROR
        else:
            # Default to generation error for question generation timeouts
            return FailureReason.LLM_GENERATION_ERROR
    elif error_message and "No questions generated" in error_message:
        # This indicates the LLM failed to generate any questions
        return FailureReason.NO_QUESTIONS_GENERATED
    else:
        # Default to LLM generation error for other failures
        return FailureReason.LLM_GENERATION_ERROR
