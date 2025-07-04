"""
Dependencies for Canvas module.
"""

from typing import Annotated

from fastapi import Depends

from src.auth.dependencies import CurrentUser
from src.config import settings
from src.database import SessionDep

from .security import ensure_valid_canvas_token
from .url_builder import CanvasURLBuilder


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


def get_canvas_url_builder() -> CanvasURLBuilder:
    """
    FastAPI dependency that provides a configured Canvas URL builder.

    Creates a CanvasURLBuilder instance with the appropriate base URL
    (either real Canvas or mock Canvas based on settings) and API version.

    **Returns:**
        CanvasURLBuilder: Configured URL builder ready for API requests

    **URL Configuration:**
    - Uses CANVAS_MOCK_URL when USE_CANVAS_MOCK is True
    - Falls back to CANVAS_BASE_URL for production/staging
    - Automatically includes the configured API version

    **Usage as Dependency:**
        >>> @router.get("/canvas/courses")
        >>> async def get_courses(url_builder: CanvasURLBuilderDep):
        ...     # Use url_builder for Canvas API URLs
        ...     courses_url = url_builder.build_url("courses")

    **Mock Environment Support:**
    - Automatically switches to mock Canvas URL in test environments
    - Maintains consistent API interface across environments
    - Transparent to API consumers
    """
    # Determine base URL based on environment settings
    base_url = str(settings.CANVAS_BASE_URL)
    if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
        base_url = str(settings.CANVAS_MOCK_URL)

    return CanvasURLBuilder(base_url, settings.CANVAS_API_VERSION)


# Type aliases for dependency injection
CanvasToken = Annotated[str, Depends(get_canvas_token)]
CanvasURLBuilderDep = Annotated[CanvasURLBuilder, Depends(get_canvas_url_builder)]
