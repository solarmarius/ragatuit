from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import CurrentUser, get_current_user
from app.deps import SessionDep, get_db
from app.security import ensure_valid_canvas_token

reusable_oauth2 = HTTPBearer()
TokenDep = Annotated[HTTPAuthorizationCredentials, Depends(reusable_oauth2)]


# Re-export from auth module for backward compatibility
# CurrentUser is already defined in auth.dependencies

# Re-export CurrentUser from auth module
__all__ = [
    "SessionDep",
    "TokenDep",
    "CurrentUser",
    "CanvasToken",
    "get_canvas_token",
    "get_current_user",
    "get_db",
]


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
