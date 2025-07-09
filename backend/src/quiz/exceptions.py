"""Orchestration-specific exceptions for quiz operations."""

from typing import Any

from src.exceptions import ServiceError


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
