"""
Authentication-specific exceptions.
"""

from app.exceptions import AuthenticationError as BaseAuthError
from app.exceptions import ServiceError


class TokenExpiredError(BaseAuthError):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message)


class InvalidTokenError(BaseAuthError):
    """Raised when a token is invalid."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)


class CanvasAuthError(ServiceError):
    """Raised when Canvas OAuth fails."""

    def __init__(self, message: str):
        super().__init__(f"Canvas authentication failed: {message}", 401)
