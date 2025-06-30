"""
Simple global exception handlers for FastAPI.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ServiceError
from app.core.logging_config import get_logger

logger = get_logger("error_handler")


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
