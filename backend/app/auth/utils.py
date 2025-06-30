"""
Utility functions for authentication module.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from jose import jwt

from app.config import settings
from app.logging_config import get_logger

from .schemas import TokenPayload

logger = get_logger("auth_utils")

ALGORITHM = "HS256"


def create_access_token(
    subject: Union[str, int], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    **Parameters:**
        subject: The subject of the token (usually user ID)
        expires_delta: Optional custom expiration time

    **Returns:**
        str: Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def generate_oauth_state() -> str:
    """Generate a secure random state for OAuth."""
    return secrets.token_urlsafe(32)


def verify_oauth_state(state: Optional[str], expected_state: Optional[str]) -> bool:
    """
    Verify OAuth state parameter.

    **Parameters:**
        state: State from OAuth callback
        expected_state: Expected state value

    **Returns:**
        bool: True if states match, False otherwise
    """
    if not state or not expected_state:
        return False
    return secrets.compare_digest(state, expected_state)
