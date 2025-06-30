"""
Canvas-specific exceptions.
"""

from app.exceptions import ServiceError


class CanvasError(ServiceError):
    """Base exception for Canvas-related errors."""

    def __init__(self, message: str = "Canvas error occurred", status_code: int = 500):
        super().__init__(message, status_code)


class CanvasAPIError(CanvasError):
    """Exception for Canvas API communication errors."""

    def __init__(self, message: str = "Canvas API error", status_code: int = 503):
        super().__init__(f"Canvas API error: {message}", status_code)


class CanvasAuthError(CanvasError):
    """Exception for Canvas authentication errors."""

    def __init__(
        self, message: str = "Canvas authentication failed", status_code: int = 401
    ):
        super().__init__(message, status_code)


class CanvasContentError(CanvasError):
    """Exception for content extraction errors."""

    def __init__(
        self, message: str = "Content extraction failed", status_code: int = 422
    ):
        super().__init__(message, status_code)


class CanvasQuizExportError(CanvasError):
    """Exception for quiz export errors."""

    def __init__(self, message: str = "Quiz export failed", status_code: int = 422):
        super().__init__(message, status_code)
