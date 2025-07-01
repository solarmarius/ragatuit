"""
Request logging middleware for FastAPI.

This middleware logs all HTTP requests and responses with structured logging,
including timing information, request/response metadata, and correlation IDs.
"""

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.logging_config import get_logger, log_context


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.

    Features:
    - Generates unique request IDs for tracing
    - Logs request start and completion
    - Measures request duration
    - Adds structured context to all logs within request
    - Handles exceptions gracefully
    """

    def __init__(self, app: Any, exclude_paths: list[str] | None = None) -> None:
        """
        Initialize logging middleware.

        Args:
            app: FastAPI application instance
            exclude_paths: List of paths to exclude from logging (e.g., health checks)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
        ]
        self.logger = get_logger("middleware.logging")

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process HTTP request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Set request context for all logs in this request
        log_context.set_request_context(
            request_id=request_id, method=request.method, path=request.url.path
        )

        # Add request ID to request state for access in handlers
        request.state.request_id = request_id

        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Log request start
        start_time = time.time()
        self.logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=client_ip,
            user_agent=user_agent,
            content_length=request.headers.get("content-length"),
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log successful response
            self.logger.info(
                "request_completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                response_size=response.headers.get("content-length"),
            )

            # Add correlation headers to response
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Calculate duration for failed request
            duration = time.time() - start_time

            # Log error
            self.logger.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )

            # Re-raise the exception
            raise

        finally:
            # Clear context after request
            log_context.clear_context()

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.

        Handles various proxy headers and fallbacks.

        Args:
            request: HTTP request

        Returns:
            Client IP address as string
        """
        # Check for forwarded headers (common with reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header (some proxies use this)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"


def add_user_to_logs(request: Request, user_id: str, canvas_id: int = 0) -> None:
    """
    Add user context to logs for the current request.

    This function should be called from authentication middleware or
    route handlers when user information becomes available.

    Args:
        request: Current HTTP request
        user_id: User's unique identifier
        canvas_id: User's Canvas ID (optional)
    """
    log_context.set_user_context(user_id, canvas_id)

    # Also log the authentication event
    logger = get_logger("auth")
    logger.info(
        "user_authenticated",
        user_id=user_id,
        canvas_id=canvas_id,
        request_id=getattr(request.state, "request_id", "unknown"),
    )
