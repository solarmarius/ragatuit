import pytest
from datetime import timedelta, datetime, timezone
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlmodel import Session

from backend.auth import (
    create_access_token,
    verify_token,
    get_current_user,
    TokenData,
    settings as auth_settings, # Direct import of settings instance from auth.py
    oauth2_scheme
)
from backend.api.models import User
from backend.config import Settings # For creating a test settings instance if needed

# Re-use the db_session fixture from conftest.py for tests needing DB access
from .conftest import db_session

# --- Tests for create_access_token ---
def test_create_access_token_basic():
    data = {"user_id": 123}
    token = create_access_token(data)
    assert isinstance(token, str)

    payload = jwt.decode(token, auth_settings.JWT_SECRET, algorithms=[auth_settings.ALGORITHM])
    assert payload["user_id"] == 123
    assert "exp" in payload

def test_create_access_token_with_custom_expiry():
    data = {"user_id": 456}
    expires_delta = timedelta(minutes=5)
    token = create_access_token(data, expires_delta=expires_delta)

    payload = jwt.decode(token, auth_settings.JWT_SECRET, algorithms=[auth_settings.ALGORITHM])
    assert payload["user_id"] == 456

    expected_exp = datetime.now(timezone.utc) + expires_delta
    actual_exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    # Allow a small delta for comparison due to execution time
    assert abs((actual_exp - expected_exp).total_seconds()) < 5

# --- Tests for verify_token ---
# Mocking Depends(oauth2_scheme) is a bit tricky for direct unit test.
# verify_token is more easily tested via an endpoint that uses it, or by manually providing a token.
# For a direct unit test, we can simulate the dependency.

async def fake_oauth2_scheme_valid_token() -> str:
    """Provides a valid token for testing verify_token directly."""
    payload = {"user_id": 789, "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    token = jwt.encode(payload, auth_settings.JWT_SECRET, algorithm=auth_settings.ALGORITHM)
    return token

async def fake_oauth2_scheme_expired_token() -> str:
    """Provides an expired token."""
    payload = {"user_id": 789, "exp": datetime.now(timezone.utc) - timedelta(minutes=15)}
    token = jwt.encode(payload, auth_settings.JWT_SECRET, algorithm=auth_settings.ALGORITHM)
    return token

async def fake_oauth2_scheme_no_user_id_token() -> str:
    """Provides a token without user_id."""
    payload = {"sub": "wrong_claim", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    token = jwt.encode(payload, auth_settings.JWT_SECRET, algorithm=auth_settings.ALGORITHM)
    return token

async def fake_oauth2_scheme_invalid_token_format() -> str:
    return "this.is.not.a.jwt"


@pytest.mark.asyncio
async def test_verify_token_valid():
    token = await fake_oauth2_scheme_valid_token()
    token_data = await verify_token(token=token) # Manually pass token
    assert token_data.user_id == 789

@pytest.mark.asyncio
async def test_verify_token_expired():
    token = await fake_oauth2_scheme_expired_token()
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token=token)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_verify_token_no_user_id():
    token = await fake_oauth2_scheme_no_user_id_token()
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token=token)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_verify_token_invalid_format():
    token = await fake_oauth2_scheme_invalid_token_format()
    with pytest.raises(HTTPException) as exc_info: # Should raise JWTError, caught by verify_token
        await verify_token(token=token)
    assert exc_info.value.status_code == 401

# --- Tests for get_current_user ---
# This function depends on verify_token and get_session.
# We need a user in the test database.

@pytest.mark.asyncio
async def test_get_current_user_valid(db_session: Session):
    # 1. Create a user in the test DB
    test_user_data = {"canvas_id": "gcuid1", "email": "gcu1@example.com", "name": "Gcu User1"}
    user = User(**test_user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None # Ensure user.id is populated

    # 2. Create a valid TokenData for this user
    valid_token_data = TokenData(user_id=user.id)

    # 3. Call get_current_user
    # We pass valid_token_data directly, simulating it came from a successful verify_token
    retrieved_user = await get_current_user(token_data=valid_token_data, session=db_session)

    assert retrieved_user is not None
    assert retrieved_user.id == user.id
    assert retrieved_user.email == test_user_data["email"]

@pytest.mark.asyncio
async def test_get_current_user_not_found(db_session: Session): # db_session is not strictly needed here if not creating user
    non_existent_user_id = 99999
    invalid_token_data = TokenData(user_id=non_existent_user_id)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token_data=invalid_token_data, session=db_session)
    assert exc_info.value.status_code == 404
    assert "User not found" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_current_user_no_userid_in_token_data(db_session: Session):
    # This tests if token_data somehow has user_id=None
    # (verify_token should prevent this, but good for defense)
    token_data_no_id = TokenData(user_id=None)
    with pytest.raises(HTTPException) as exc_info:
         await get_current_user(token_data=token_data_no_id, session=db_session)
    # The error raised might be the one from verify_token if user_id is None in payload,
    # or the one in get_current_user if token_data.user_id is None by other means.
    # Based on current get_current_user, it should be 404 "User ID not in token"
    assert exc_info.value.status_code == 404
    assert "User ID not in token" in exc_info.value.detail
