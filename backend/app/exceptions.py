"""
Simple service exceptions for standardized error handling.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.logging_config import get_logger

logger = get_logger("error_handler")


class ServiceError(Exception):
    """Base exception for service layer errors."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ExternalServiceError(ServiceError):
    """Error when external service (Canvas, OpenAI) fails."""

    def __init__(self, service: str, message: str, status_code: int = 503):
        super().__init__(f"{service} service error: {message}", status_code)
        self.service = service


class ValidationError(ServiceError):
    """Error when data validation fails."""

    def __init__(self, message: str):
        super().__init__(f"Validation error: {message}", 400)


class AuthenticationError(ServiceError):
    """Error when authentication fails."""

    def __init__(self, message: str):
        super().__init__(f"Authentication error: {message}", 401)


class ResourceNotFoundError(ServiceError):
    """Error when a resource is not found."""

    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", 404)


# Exception handlers for FastAPI
async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """Handle ServiceError exceptions."""
    logger.error(
        "service_error",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        status_code=exc.status_code,
    )

    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        "unexpected_error",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )

    return JSONResponse(status_code=500, content={"error": "Internal server error"})
