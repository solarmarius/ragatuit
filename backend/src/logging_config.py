"""
Logging configuration for the application.

This module sets up structured logging using structlog with environment-specific
configurations. It provides JSON output for production and human-readable output
for development.
"""

import logging
import logging.config
import sys
from typing import Any

import structlog

from src.config import settings


# Context variables for request tracking
class LogContext:
    """Context manager for adding request/user context to logs."""

    def __init__(self) -> None:
        from contextvars import ContextVar

        self.request_id: ContextVar[str] = ContextVar("request_id", default="")
        self.request_method: ContextVar[str] = ContextVar("request_method", default="")
        self.request_path: ContextVar[str] = ContextVar("request_path", default="")
        self.user_id: ContextVar[str] = ContextVar("user_id", default="")
        self.canvas_id: ContextVar[int] = ContextVar("canvas_id", default=0)

    def set_request_context(self, request_id: str, method: str, path: str) -> None:
        """Set request context for logging."""
        self.request_id.set(request_id)
        self.request_method.set(method)
        self.request_path.set(path)

    def set_user_context(self, user_id: str, canvas_id: int = 0) -> None:
        """Set user context for logging."""
        self.user_id.set(user_id)
        if canvas_id:
            self.canvas_id.set(canvas_id)

    def clear_context(self) -> None:
        """Clear all context variables."""
        self.request_id.set("")
        self.request_method.set("")
        self.request_path.set("")
        self.user_id.set("")
        self.canvas_id.set(0)


# Global context instance
log_context = LogContext()


def configure_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up structlog with different configurations based on environment:
    - Development: Human-readable console output with colors
    - Production: JSON structured logs for aggregation
    """
    # Configure standard library logging first
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=_get_log_level(),
    )

    # Configure structlog processors
    processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Add context processors
        _add_request_context,
        _add_user_context,
    ]

    # Environment-specific final processor
    if settings.ENVIRONMENT == "local":
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Configure third-party loggers
    _configure_third_party_loggers()


def _get_log_level() -> int:
    """Get log level based on environment."""
    log_levels = {
        "local": logging.DEBUG,
        "staging": logging.INFO,
        "production": logging.WARNING,
    }
    return log_levels.get(settings.ENVIRONMENT, logging.INFO)


def _add_request_context(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add request context to log entries.

    This processor adds request-specific information like request_id,
    method, and path to all log entries within a request context.
    """
    if log_context.request_id.get():
        event_dict["request_id"] = log_context.request_id.get()
    if log_context.request_method.get():
        event_dict["method"] = log_context.request_method.get()
    if log_context.request_path.get():
        event_dict["path"] = log_context.request_path.get()

    return event_dict


def _add_user_context(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add user context to log entries.

    This processor adds user-specific information like user_id and canvas_id
    to log entries when available.
    """
    if log_context.user_id.get():
        event_dict["user_id"] = log_context.user_id.get()
    if log_context.canvas_id.get():
        event_dict["canvas_id"] = log_context.canvas_id.get()

    return event_dict


def _configure_third_party_loggers() -> None:
    """Configure logging levels for third-party libraries."""
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)

    # Keep FastAPI logs at INFO level
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str = "") -> Any:
    """
    Get a configured logger instance.

    Args:
        name: Logger name, defaults to the calling module's name

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)
