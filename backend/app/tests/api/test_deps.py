from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlmodel import Session

from app import crud
from app.api.deps import get_canvas_token, get_current_user, get_db
from app.config import settings
from app.models import UserCreate
from app.security import ALGORITHM, create_access_token


def test_get_db() -> None:
    """Test database session dependency"""
    db_generator = get_db()
    session = next(db_generator)

    # Should return a Session instance
    assert isinstance(session, Session)

    # Should be able to close the session
    try:
        db_generator.close()
    except StopIteration:
        pass  # Expected when generator is exhausted


def test_get_current_user_valid_token(db: Session) -> None:
    """Test get_current_user with valid JWT token"""
    # Create a test user
    user_in = UserCreate(
        canvas_id=123,
        name="Test User",
        access_token="test_token",
        refresh_token="refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # Create valid JWT token
    token = create_access_token(
        str(user.id), timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # Test get_current_user
    result_user = get_current_user(db, credentials)

    assert result_user.id == user.id
    assert result_user.canvas_id == user.canvas_id
    assert result_user.name == user.name


def test_get_current_user_invalid_token_format(db: Session) -> None:
    """Test get_current_user with invalid token format"""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="invalid_token"
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, credentials)

    assert exc_info.value.status_code == 403
    assert "Could not validate credentials" in exc_info.value.detail


def test_get_current_user_expired_token(db: Session) -> None:
    """Test get_current_user with expired token"""
    # Create expired token
    import time

    expired_token = jwt.encode(
        {"exp": time.time() - 3600, "sub": "some_user_id"},  # Expired 1 hour ago
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=expired_token
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, credentials)

    assert exc_info.value.status_code == 403
    assert "Could not validate credentials" in exc_info.value.detail


def test_get_current_user_wrong_secret(db: Session) -> None:
    """Test get_current_user with token signed with wrong secret"""
    # Create token with wrong secret
    wrong_token = jwt.encode(
        {"exp": 9999999999, "sub": "some_user_id"}, "wrong_secret", algorithm=ALGORITHM
    )

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=wrong_token)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, credentials)

    assert exc_info.value.status_code == 403
    assert "Could not validate credentials" in exc_info.value.detail


def test_get_current_user_malformed_payload(db: Session) -> None:
    """Test get_current_user with malformed token payload"""
    # Create token with missing sub field
    malformed_token = jwt.encode(
        {"exp": 9999999999},  # Missing 'sub' field
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=malformed_token
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, credentials)

    # Missing sub field results in None being passed to session.get() which returns None
    # This triggers the "User not found" case
    assert exc_info.value.status_code == 404
    assert "User not found" in exc_info.value.detail


def test_get_current_user_nonexistent_user(db: Session) -> None:
    """Test get_current_user with token for non-existent user"""
    import uuid

    non_existent_id = str(uuid.uuid4())

    # Create valid token for non-existent user
    token = jwt.encode(
        {"exp": 9999999999, "sub": non_existent_id},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, credentials)

    assert exc_info.value.status_code == 404
    assert "User not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_canvas_token_valid(db: Session) -> None:
    """Test get_canvas_token with valid user and token"""
    # Create user with future expiry
    from datetime import datetime, timedelta, timezone

    user_in = UserCreate(
        canvas_id=123,
        name="Test User",
        access_token="valid_canvas_token",
        refresh_token="refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # Set expiry to future
    future_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
    user.expires_at = future_expiry
    db.add(user)
    db.commit()

    # Test get_canvas_token
    token = await get_canvas_token(user, db)
    assert token == "valid_canvas_token"


@pytest.mark.asyncio
async def test_get_canvas_token_valid_token(db: Session) -> None:
    """Test get_canvas_token with valid token that doesn't need refresh"""
    from datetime import datetime, timedelta, timezone

    user_in = UserCreate(
        canvas_id=123,
        name="Test User",
        access_token="valid_token",
        refresh_token="refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # Set expiry to far future so no refresh needed
    future_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=2)
    user.expires_at = future_expiry
    db.add(user)
    db.commit()

    token = await get_canvas_token(user, db)
    assert token == "valid_token"


def test_get_canvas_token_dependency_structure() -> None:
    """Test that get_canvas_token is properly annotated as a dependency"""
    # This is a simple test to verify the dependency annotation exists
    from app.api.deps import CanvasToken

    assert CanvasToken is not None
