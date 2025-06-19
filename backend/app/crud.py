from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.core.security import token_encryption
from app.models import User, UserCreate


def create_user(session: Session, user_create: UserCreate) -> User:
    """
    Create a new user account with encrypted Canvas OAuth tokens.

    Creates a new user record in the database with Canvas OAuth credentials
    securely encrypted for storage. This is called during the OAuth callback
    when a new user authenticates with Canvas for the first time.

    **Parameters:**
        session (Session): Database session for the transaction
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
        >>> user = create_user(session, user_data)
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
            "access_token": token_encryption.encrypt_token(user_create.access_token),
            "refresh_token": token_encryption.encrypt_token(user_create.refresh_token),
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user_tokens(
    session: Session,
    user: User,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
) -> User:
    """Update user's Canvas tokens"""
    # Encrypt tokens
    user.access_token = token_encryption.encrypt_token(access_token)
    if refresh_token:
        user.refresh_token = token_encryption.encrypt_token(refresh_token)

    user.expires_at = expires_at
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def clear_user_tokens(session: Session, user: User) -> User:
    """Clear user's Canvas tokens"""
    user.access_token = ""
    user.refresh_token = ""
    user.expires_at = None

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_canvas_id(session: Session, canvas_id: int) -> User | None:
    """
    Retrieve a user by their Canvas LMS user ID.

    Looks up a user account using their Canvas LMS identifier. This is the primary
    method for finding existing users during OAuth authentication flow.

    **Parameters:**
        session (Session): Database session for the query
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
        >>> user = get_user_by_canvas_id(session, 12345)
        >>> if user:
        ...     print(f"Found user: {user.name}")
        ... else:
        ...     print("User not found, create new account")

    **Security:**
    Canvas ID is not considered sensitive but should only come from trusted Canvas OAuth responses.
    """
    statement = select(User).where(User.canvas_id == canvas_id)
    return session.exec(statement).first()


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    """
    Retrieve a user by their internal UUID.

    Looks up a user account using the internal UUID primary key. This is used
    for authentication middleware and API operations where the user ID comes
    from a validated JWT token.

    **Parameters:**
        session (Session): Database session for the query
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
        >>> user = get_user_by_id(session, user_uuid)
        >>> if user:
        ...     print(f"Authenticated user: {user.name}")
        ... else:
        ...     raise HTTPException(404, "User not found")

    **Security:**
    UUID should only come from validated JWT tokens. Random UUID guessing is
    cryptographically infeasible.
    """
    return session.get(User, user_id)


def get_decrypted_access_token(user: User) -> str:
    """Get decrypted access token"""
    return token_encryption.decrypt_token(user.access_token)


def get_decrypted_refresh_token(user: User) -> str:
    """Get decrypted refresh token"""
    return token_encryption.decrypt_token(user.refresh_token)
