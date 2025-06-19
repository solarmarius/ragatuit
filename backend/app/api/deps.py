from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.security import ensure_valid_canvas_token
from app.models import TokenPayload, User

reusable_oauth2 = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides database sessions.

    Creates and manages database sessions for API endpoints using SQLModel/SQLAlchemy.
    Ensures proper session lifecycle with automatic cleanup and connection management.

    **Yields:**
        Session: SQLModel database session ready for CRUD operations

    **Lifecycle:**
    1. Creates new database session from engine connection pool
    2. Yields session to the requesting endpoint/dependency
    3. Automatically closes session when request completes (success or error)
    4. Returns connection to pool for reuse

    **Usage as Dependency:**
        >>> @router.get("/users/{user_id}")
        >>> def get_user(user_id: int, session: SessionDep):
        ...     return session.get(User, user_id)

    **Error Handling:**
    - Session automatically rolls back on unhandled exceptions
    - Connection automatically returns to pool on any exit
    - No manual session management required in endpoints

    **Performance:**
    - Uses connection pooling for efficient database access
    - Session per request pattern ensures isolation
    - Automatic cleanup prevents connection leaks

    **Thread Safety:**
    Each request gets its own session instance, ensuring thread safety.
    """
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[HTTPAuthorizationCredentials, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, credentials: TokenDep) -> User:
    """
    FastAPI dependency that validates JWT tokens and returns the authenticated user.

    Extracts and validates JWT tokens from Authorization headers, then loads the
    corresponding user from the database. This is the core authentication dependency
    used by all protected API endpoints.

    **Parameters:**
        session (SessionDep): Database session from get_db() dependency
        credentials (TokenDep): HTTP Bearer token from Authorization header

    **Returns:**
        User: Authenticated user object from database

    **Authentication Flow:**
    1. Extracts JWT token from 'Authorization: Bearer <token>' header
    2. Validates token signature using application SECRET_KEY
    3. Decodes token payload and validates structure (exp, sub fields)
    4. Looks up user in database using token subject (user UUID)
    5. Returns user object if found

    **Usage as Dependency:**
        >>> @router.get("/protected")
        >>> def protected_endpoint(current_user: CurrentUser):
        ...     return {"user": current_user.name}

    **Raises:**
        HTTPException: 403 Forbidden if token is invalid, expired, or malformed
        HTTPException: 404 Not Found if token is valid but user doesn't exist

    **Token Validation:**
    - Verifies HMAC-SHA256 signature to prevent tampering
    - Checks expiration timestamp to prevent stale token usage
    - Validates token structure and required fields
    - Ensures user still exists in database

    **Security Considerations:**
    - Tokens cannot be forged without the SECRET_KEY
    - Expired tokens are automatically rejected
    - User deletion invalidates all tokens for that user
    - No session state - purely token-based authentication

    **Error Scenarios:**
    - Malformed JWT: 403 Forbidden
    - Invalid signature: 403 Forbidden
    - Expired token: 403 Forbidden
    - Valid token, deleted user: 404 Not Found
    - Missing Authorization header: Handled by HTTPBearer dependency
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[security.ALGORITHM],
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_canvas_token(current_user: CurrentUser, session: SessionDep) -> str:
    """
    FastAPI dependency that provides a valid Canvas OAuth access token.

    Ensures the authenticated user has a valid Canvas access token for making
    Canvas API requests. Automatically refreshes expired tokens when possible.

    **Parameters:**
        current_user (CurrentUser): Authenticated user from JWT token validation
        session (SessionDep): Database session for token updates

    **Returns:**
        str: Valid Canvas OAuth access token ready for API requests

    **Token Management:**
    1. Checks if current Canvas token expires within 5 minutes
    2. If expiring soon, attempts automatic refresh using stored refresh token
    3. Updates database with new token and expiration time
    4. Returns decrypted access token for immediate use

    **Usage as Dependency:**
        >>> @router.get("/canvas/courses")
        >>> async def get_courses(canvas_token: CanvasToken):
        ...     # Use canvas_token for Canvas API requests
        ...     headers = {"Authorization": f"Bearer {canvas_token}"}

    **Automatic Token Refresh:**
    - Triggers when token expires within 5 minutes
    - Uses stored Canvas refresh token to get new access token
    - Updates user record with new token and expiration
    - Transparent to API consumers

    **Error Handling:**
        HTTPException: 401 if refresh fails and user needs to re-authenticate
        HTTPException: 503 if Canvas API is temporarily unavailable

    **Canvas API Integration:**
    Returned token can be used directly in Canvas API requests:
    - Canvas REST API calls
    - GraphQL API requests
    - File uploads/downloads
    - Any Canvas LMS operation requiring authentication

    **Security:**
    - Tokens are decrypted on-demand from secure database storage
    - Automatic refresh maintains seamless user experience
    - Failed refresh triggers re-authentication for security
    """
    return await ensure_valid_canvas_token(session, current_user)


CanvasToken = Annotated[str, Depends(get_canvas_token)]
