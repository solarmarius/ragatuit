"""
Authentication dependencies for FastAPI.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from src.config import get_logger, settings
from src.database import SessionDep

from .models import User
from .schemas import TokenPayload
from .service import get_user_by_id

logger = get_logger("auth_dependencies")

# OAuth2 scheme for bearer token
reusable_oauth2 = HTTPBearer()


def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(reusable_oauth2)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    Validates the JWT token from the Authorization header and retrieves
    the corresponding user from the database. This is the primary
    authentication dependency for protected endpoints.

    **Parameters:**
        session: Database session (injected)
        credentials: Bearer token from Authorization header (injected)

    **Returns:**
        User: The authenticated user object

    **Raises:**
        HTTPException(401): Invalid token or user not found
        HTTPException(403): Token validation failed

    **Security:**
    - Validates JWT signature using secret key
    - Checks token expiration
    - Verifies user still exists in database
    - Ensures bearer token format

    **Usage:**
        >>> @router.get("/me")
        >>> def get_current_user_info(
        >>>     current_user: Annotated[User, Depends(get_current_user)]
        >>> ):
        >>>     return current_user
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        logger.warning("invalid_jwt_token", error="Token validation failed")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    if not token_data.sub:
        logger.warning("jwt_missing_subject", error="Token has no subject")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    # Get user from database
    from uuid import UUID

    user = get_user_by_id(session, UUID(token_data.sub))
    if not user:
        logger.warning("user_not_found", user_id=token_data.sub)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
