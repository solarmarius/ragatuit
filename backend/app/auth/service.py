"""
Authentication service layer combining user CRUD and Canvas OAuth operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlmodel import Session, select

from app import crud
from app.config import settings
from app.encryption import token_encryption
from app.exceptions import AuthenticationError, ExternalServiceError
from app.logging_config import get_logger
from app.retry import retry_on_failure
from app.services.url_builder import CanvasURLBuilder

from .models import User
from .schemas import UserCreate

logger = get_logger("auth_service")


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, session: Session):
        self.session = session

    # User CRUD operations
    def create_user(self, user_create: UserCreate) -> User:
        """
        Create a new user account with encrypted Canvas OAuth tokens.

        Creates a new user record in the database with Canvas OAuth credentials
        securely encrypted for storage. This is called during the OAuth callback
        when a new user authenticates with Canvas for the first time.

        **Parameters:**
            user_create (UserCreate): User data containing Canvas ID, name, and OAuth tokens

        **Returns:**
            User: The newly created user object with encrypted tokens and generated UUID

        **Security:**
        - Canvas access and refresh tokens are encrypted before database storage
        - Uses secure token encryption to protect OAuth credentials at rest
        - Generated UUID serves as internal user identifier separate from Canvas ID

        **Database Operations:**
        1. Validates user data against UserCreate schema
        2. Encrypts sensitive Canvas OAuth tokens
        3. Inserts new user record with auto-generated UUID and timestamps
        4. Commits transaction and refreshes object with database-generated values

        **Fields Set:**
        - `id`: Auto-generated UUID (primary key)
        - `canvas_id`: Canvas LMS user ID (unique)
        - `name`: User's display name from Canvas
        - `access_token`: Encrypted Canvas OAuth access token
        - `refresh_token`: Encrypted Canvas OAuth refresh token
        - `created_at`: Auto-generated timestamp
        - `expires_at`: Set by default, updated during token refresh

        **Example:**
            >>> user_data = UserCreate(
            ...     canvas_id=12345,
            ...     name="John Doe",
            ...     access_token="canvas_access_123",
            ...     refresh_token="canvas_refresh_456"
            ... )
            >>> user = service.create_user(user_data)
            >>> print(user.id)  # UUID('...')
            >>> print(user.canvas_id)  # 12345

        **Note:**
        This function assumes the Canvas ID is unique and not already in use.
        Check with get_user_by_canvas_id() first to handle existing users.
        """
        db_obj = User.model_validate(
            user_create,
            update={
                "canvas_id": user_create.canvas_id,
                "name": user_create.name,
                "access_token": token_encryption.encrypt_token(
                    user_create.access_token
                ),
                "refresh_token": token_encryption.encrypt_token(
                    user_create.refresh_token
                ),
            },
        )
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def update_user_tokens(
        self,
        user: User,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> User:
        """Update user's Canvas tokens"""
        # Encrypt tokens
        user.access_token = token_encryption.encrypt_token(access_token)
        if refresh_token:
            user.refresh_token = token_encryption.encrypt_token(refresh_token)

        user.expires_at = expires_at
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def clear_user_tokens(self, user: User) -> User:
        """Clear user's Canvas tokens"""
        user.access_token = ""
        user.refresh_token = ""
        user.expires_at = None

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_user_by_canvas_id(self, canvas_id: int) -> Optional[User]:
        """
        Retrieve a user by their Canvas LMS user ID.

        Looks up a user account using their Canvas LMS identifier. This is the primary
        method for finding existing users during OAuth authentication flow.

        **Parameters:**
            canvas_id (int): Canvas LMS user ID (unique identifier from Canvas)

        **Returns:**
            User | None: User object if found, None if no user exists with this Canvas ID

        **Usage:**
        - OAuth callback: Check if user already exists before creating new account
        - Authentication: Link Canvas identity to internal user account
        - User lookup: Find user based on Canvas identity

        **Database Query:**
        Performs indexed lookup on canvas_id field (unique constraint ensures at most one result).

        **Example:**
            >>> user = service.get_user_by_canvas_id(12345)
            >>> if user:
            ...     print(f"Found user: {user.name}")
            ... else:
            ...     print("User not found, create new account")

        **Security:**
        Canvas ID is not considered sensitive but should only come from trusted Canvas OAuth responses.
        """
        statement = select(User).where(User.canvas_id == canvas_id)
        return self.session.exec(statement).first()

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieve a user by their internal UUID.

        Looks up a user account using the internal UUID primary key. This is used
        for authentication middleware and API operations where the user ID comes
        from a validated JWT token.

        **Parameters:**
            user_id (UUID): Internal user UUID (from JWT token subject)

        **Returns:**
            User | None: User object if found, None if UUID doesn't exist

        **Usage:**
        - JWT authentication: Validate token subject and load user data
        - API operations: Load user for authenticated requests
        - User validation: Ensure user still exists after token was issued

        **Performance:**
        Uses primary key lookup - fastest possible user query.

        **Example:**
            >>> from uuid import UUID
            >>> user_uuid = UUID('12345678-1234-5678-9abc-123456789abc')
            >>> user = service.get_user_by_id(user_uuid)
            >>> if user:
            ...     print(f"Authenticated user: {user.name}")
            ... else:
            ...     raise HTTPException(404, "User not found")

        **Security:**
        UUID should only come from validated JWT tokens. Random UUID guessing is
        cryptographically infeasible.
        """
        return self.session.get(User, user_id)

    def get_decrypted_access_token(self, user: User) -> str:
        """Get decrypted access token"""
        return token_encryption.decrypt_token(user.access_token)

    def get_decrypted_refresh_token(self, user: User) -> str:
        """Get decrypted refresh token"""
        return token_encryption.decrypt_token(user.refresh_token)


# Canvas OAuth functions (from canvas_auth.py)
@retry_on_failure(max_attempts=2, initial_delay=1.0)
async def refresh_canvas_token(user: User, session: Session) -> None:
    """
    Refresh Canvas access token using the refresh token.

    Args:
        user: User object with encrypted tokens
        session: Database session

    Raises:
        AuthenticationError: When refresh fails (401, 403)
        ExternalServiceError: When Canvas is unavailable
    """
    logger.info(
        "canvas_token_refresh_initiated", user_id=user.id, canvas_id=user.canvas_id
    )

    # Decrypt refresh token
    auth_service = AuthService(session)
    refresh_token = auth_service.get_decrypted_refresh_token(user)

    # Prepare refresh request
    url_builder = CanvasURLBuilder(settings.CANVAS_BASE_URL)
    refresh_url = url_builder.build_oauth_token_url()

    refresh_data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.CANVAS_CLIENT_ID,
        "client_secret": settings.CANVAS_CLIENT_SECRET,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(refresh_url, data=refresh_data)

        if response.status_code == 200:
            token_data = response.json()
            new_access_token = token_data["access_token"]

            # Canvas sometimes returns new refresh token
            new_refresh_token = token_data.get("refresh_token", refresh_token)

            # Calculate expiration (Canvas tokens expire in 1 hour)
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_data.get("expires_in", 3600)
            )

            # Update user tokens in database
            auth_service.update_user_tokens(
                user=user,
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_at=expires_at,
            )

            logger.info(
                "canvas_token_refresh_success",
                user_id=user.id,
                expires_at=expires_at.isoformat(),
            )

        elif response.status_code in [401, 403]:
            logger.error(
                "canvas_token_refresh_auth_failed",
                user_id=user.id,
                status_code=response.status_code,
            )
            # Clear invalid tokens
            auth_service.clear_user_tokens(user)
            raise AuthenticationError(
                "Canvas token refresh failed - please login again"
            )
        else:
            logger.error(
                "canvas_token_refresh_failed",
                user_id=user.id,
                status_code=response.status_code,
                response_text=response.text,
            )
            raise ExternalServiceError(
                "Canvas",
                f"Token refresh failed with status {response.status_code}",
                response.status_code,
            )

    except httpx.RequestError as e:
        logger.error(
            "canvas_token_refresh_request_error",
            user_id=user.id,
            error=str(e),
            exc_info=True,
        )
        raise ExternalServiceError("Canvas", f"Request failed: {str(e)}", 503)
