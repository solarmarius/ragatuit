"""
Core orchestration utilities for quiz operations.

This module provides the foundational infrastructure for all quiz orchestration
workflows, including background task safety, timeout handling, and failure management.
"""

import asyncio
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar
from uuid import UUID

from src.config import get_logger
from src.database import execute_in_transaction

from ..exceptions import OrchestrationTimeoutError
from ..schemas import QuizStatus

T = TypeVar("T")

logger = get_logger("quiz_orchestrator_core")


async def safe_background_orchestration(
    operation_func: Callable[..., Any],
    operation_name: str,
    quiz_id: UUID,
    *args: Any,
    **kwargs: Any,
) -> None:
    """
    Safely execute orchestration operations as background tasks with proper exception handling.

    This wrapper ensures that all exceptions, including OrchestrationTimeoutError, are properly
    caught and handled when operations are run as FastAPI background tasks. Without this wrapper,
    background tasks silently swallow exceptions, leaving quizzes stuck in incomplete states.

    Args:
        operation_func: The orchestration function to execute
        operation_name: Name of the operation for logging (e.g., "content_extraction")
        quiz_id: UUID of the quiz being processed
        *args: Arguments to pass to the operation function
        **kwargs: Keyword arguments to pass to the operation function
    """
    # Generate correlation ID for tracking concurrent operations
    correlation_id = str(uuid.uuid4())

    logger.info(
        "background_orchestration_started",
        operation=operation_name,
        quiz_id=str(quiz_id),
        correlation_id=correlation_id,
    )

    try:
        # Execute the orchestration operation
        await operation_func(*args, **kwargs)

        logger.info(
            "background_orchestration_completed",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
        )

    except OrchestrationTimeoutError as timeout_error:
        logger.error(
            "background_orchestration_timeout",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
            timeout_seconds=timeout_error.timeout_seconds,
            error=str(timeout_error),
        )

        # Update quiz status to failed with appropriate failure reason
        await _handle_orchestration_failure(
            quiz_id, operation_name, timeout_error, correlation_id
        )

    except Exception as error:
        logger.error(
            "background_orchestration_error",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
            error=str(error),
            error_type=type(error).__name__,
            exc_info=True,
        )

        # Update quiz status to failed with appropriate failure reason
        await _handle_orchestration_failure(
            quiz_id, operation_name, error, correlation_id
        )


async def _handle_orchestration_failure(
    quiz_id: UUID,
    operation_name: str,
    error: Exception,
    correlation_id: str,
) -> None:
    """
    Handle orchestration failures by updating quiz status appropriately.

    Args:
        quiz_id: UUID of the failed quiz
        operation_name: Name of the operation that failed
        error: The exception that occurred
        correlation_id: Correlation ID for tracking
    """
    logger.warning(
        "orchestration_failure_status_update_initiated",
        operation=operation_name,
        quiz_id=str(quiz_id),
        correlation_id=correlation_id,
        error_type=type(error).__name__,
    )

    try:

        async def _update_failed_status(session: Any, quiz_id: UUID) -> None:
            """Update quiz status to failed with appropriate failure reason."""
            from ..exceptions import determine_failure_reason
            from ..service import update_quiz_status

            # Determine appropriate failure reason based on operation and error
            failure_reason = determine_failure_reason(operation_name, error, str(error))

            await update_quiz_status(
                session, quiz_id, QuizStatus.FAILED, failure_reason
            )

        await execute_in_transaction(
            _update_failed_status,
            quiz_id,
            isolation_level="REPEATABLE READ",
            retries=3,
        )

        logger.info(
            "orchestration_failure_status_updated",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
            new_status="failed",
        )

    except Exception as update_error:
        logger.error(
            "orchestration_failure_status_update_failed",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
            update_error=str(update_error),
            original_error=str(error),
            exc_info=True,
        )
        # If we can't update the status, log as critical for manual intervention


def timeout_operation(
    timeout_seconds: int,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to add timeout to orchestration operations.

    Args:
        timeout_seconds: Maximum time to wait before timing out

    Raises:
        OrchestrationTimeoutError: If operation times out
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                # Extract quiz_id from args if available for better logging
                quiz_id = None
                if args and hasattr(args[0], "hex"):  # UUID has hex attribute
                    quiz_id = str(args[0])
                elif len(args) > 0:
                    quiz_id = str(args[0])

                logger.error(
                    "orchestration_operation_timeout",
                    operation=func.__name__,
                    timeout_seconds=timeout_seconds,
                    quiz_id=quiz_id,
                )

                raise OrchestrationTimeoutError(
                    operation=func.__name__,
                    timeout_seconds=timeout_seconds,
                    quiz_id=quiz_id,
                )

        return wrapper

    return decorator


# Type aliases for dependency injection
ContentExtractorFunc = Callable[[str, int, list[int]], Any]
ContentSummaryFunc = Callable[[dict[str, list[dict[str, str]]]], dict[str, Any]]
QuizCreatorFunc = Callable[[str, int, str, int], Any]
QuestionExporterFunc = Callable[[str, int, str, list[dict[str, Any]]], Any]
