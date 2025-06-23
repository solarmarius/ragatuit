import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.core.security import (
    TokenEncryption,
    create_access_token,
    ensure_valid_canvas_token,
)
from app.models import UserCreate


def test_encrypt_decrypt_token() -> None:
    """Test basic token encryption and decryption"""
    encryption = TokenEncryption()
    original_token = "test_access_token_12345"

    # Encrypt token
    encrypted = encryption.encrypt_token(original_token)

    # Token should be encrypted (different from original)
    assert encrypted != original_token
    assert len(encrypted) > 0

    # Decrypt token
    decrypted = encryption.decrypt_token(encrypted)
    assert decrypted == original_token


def test_encrypt_empty_token() -> None:
    """Test encryption of empty tokens"""
    encryption = TokenEncryption()

    # Empty string should return empty string
    assert encryption.encrypt_token("") == ""


def test_decrypt_empty_token() -> None:
    """Test decryption of empty tokens"""
    encryption = TokenEncryption()

    # Empty string should return empty string
    assert encryption.decrypt_token("") == ""


def test_decrypt_invalid_token() -> None:
    """Test decryption of invalid/corrupted tokens"""
    encryption = TokenEncryption()

    # Invalid base64
    with pytest.raises(ValueError, match="Invalid encrypted token"):
        encryption.decrypt_token("invalid_token")

    # Valid base64 but invalid encryption
    invalid_encrypted = base64.urlsafe_b64encode(b"not_encrypted_data").decode()
    with pytest.raises(ValueError, match="Invalid encrypted token"):
        encryption.decrypt_token(invalid_encrypted)


def test_encrypt_different_tokens_produce_different_results() -> None:
    """Test that different tokens produce different encrypted results"""
    encryption = TokenEncryption()

    token1 = "token_one"
    token2 = "token_two"

    encrypted1 = encryption.encrypt_token(token1)
    encrypted2 = encryption.encrypt_token(token2)

    assert encrypted1 != encrypted2
    assert encryption.decrypt_token(encrypted1) == token1
    assert encryption.decrypt_token(encrypted2) == token2


def test_multiple_encryption_instances_are_compatible() -> None:
    """Test that multiple TokenEncryption instances can decrypt each other's tokens"""
    encryption1 = TokenEncryption()
    encryption2 = TokenEncryption()

    original_token = "cross_instance_token"
    encrypted = encryption1.encrypt_token(original_token)
    decrypted = encryption2.decrypt_token(encrypted)

    assert decrypted == original_token


def test_long_token_encryption() -> None:
    """Test encryption of very long tokens"""
    encryption = TokenEncryption()

    # Create a very long token
    long_token = "a" * 1000 + "b" * 1000 + "c" * 1000

    encrypted = encryption.encrypt_token(long_token)
    decrypted = encryption.decrypt_token(encrypted)

    assert decrypted == long_token


def test_create_access_token_basic() -> None:
    """Test basic JWT token creation"""
    subject = "test_user_id"
    expires_delta = timedelta(minutes=30)

    token = create_access_token(subject, expires_delta)

    # Token should be a string
    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify token
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
    assert payload["sub"] == subject

    # Check expiration is set correctly
    exp_timestamp = payload["exp"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    expected_exp = datetime.now(timezone.utc) + expires_delta

    # Allow 5 second tolerance for test execution time
    assert abs((exp_datetime - expected_exp).total_seconds()) < 5


def test_create_access_token_different_subjects() -> None:
    """Test token creation with different subject types"""
    expires_delta = timedelta(minutes=15)

    # String subject
    token1 = create_access_token("string_subject", expires_delta)
    payload1 = jwt.decode(token1, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
    assert payload1["sub"] == "string_subject"

    # Integer subject (should be converted to string)
    token2 = create_access_token(12345, expires_delta)
    payload2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
    assert payload2["sub"] == "12345"

    # UUID subject
    import uuid

    test_uuid = uuid.uuid4()
    token3 = create_access_token(test_uuid, expires_delta)
    payload3 = jwt.decode(token3, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
    assert payload3["sub"] == str(test_uuid)


def test_create_access_token_different_expiration_times() -> None:
    """Test token creation with different expiration times"""
    subject = "test_user"

    # Short expiration
    short_token = create_access_token(subject, timedelta(minutes=1))
    short_payload = jwt.decode(
        short_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
    )

    # Long expiration
    long_token = create_access_token(subject, timedelta(days=7))
    long_payload = jwt.decode(
        long_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
    )

    # Long token should expire later than short token
    assert long_payload["exp"] > short_payload["exp"]


@pytest.mark.asyncio
async def test_ensure_valid_canvas_token_no_refresh_needed(db: Session) -> None:
    """Test when token is valid and doesn't need refresh"""
    # Create user with token that expires in the future
    future_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
    user_in = UserCreate(
        canvas_id=123,
        name="Test User",
        access_token="valid_token",
        refresh_token="refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # Set expiry manually (simulating database state)
    user.expires_at = future_expiry
    db.add(user)
    db.commit()

    # Should return the token without refresh
    token = await ensure_valid_canvas_token(db, user)
    assert token == "valid_token"


@pytest.mark.asyncio
async def test_ensure_valid_canvas_token_refresh_success(db: Session) -> None:
    """Test token refresh when token expires soon"""
    # Create user with token that expires soon
    soon_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=2)
    user_in = UserCreate(
        canvas_id=123,
        name="Test User",
        access_token="old_token",
        refresh_token="refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)
    user.expires_at = soon_expiry
    db.add(user)
    db.commit()

    with patch("app.api.routes.auth.refresh_canvas_token") as mock_refresh:
        mock_refresh.return_value = None  # Successful refresh

        with patch("app.crud.get_decrypted_access_token") as mock_get_token:
            mock_get_token.return_value = "refreshed_token"

            token = await ensure_valid_canvas_token(db, user)
            assert token == "refreshed_token"
            mock_refresh.assert_called_once_with(user, db)


@pytest.mark.asyncio
async def test_ensure_valid_canvas_token_401_error(db: Session) -> None:
    """Test handling of 401 error during token refresh"""
    # Create user with expired token
    past_expiry = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    user_in = UserCreate(
        canvas_id=123,
        name="Test User",
        access_token="expired_token",
        refresh_token="refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)
    user.expires_at = past_expiry
    db.add(user)
    db.commit()

    with patch("app.api.routes.auth.refresh_canvas_token") as mock_refresh:
        # Simulate 401 error (invalid refresh token)
        mock_refresh.side_effect = HTTPException(
            status_code=401, detail="Invalid token"
        )

        with patch("app.crud.clear_user_tokens") as mock_clear:
            with pytest.raises(HTTPException) as exc_info:
                await ensure_valid_canvas_token(db, user)

            assert exc_info.value.status_code == 401
            assert "Canvas session expired" in exc_info.value.detail
            mock_clear.assert_called_once_with(db, user)


@pytest.mark.asyncio
async def test_ensure_valid_canvas_token_503_error(db: Session) -> None:
    """Test handling of 503 error during token refresh"""
    # Create user with expired token
    past_expiry = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    user_in = UserCreate(
        canvas_id=123,
        name="Test User",
        access_token="expired_token",
        refresh_token="refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)
    user.expires_at = past_expiry
    db.add(user)
    db.commit()

    with patch("app.api.routes.auth.refresh_canvas_token") as mock_refresh:
        # Simulate 503 error (Canvas temporarily unavailable)
        mock_refresh.side_effect = HTTPException(
            status_code=503, detail="Service unavailable"
        )

        with pytest.raises(HTTPException) as exc_info:
            await ensure_valid_canvas_token(db, user)

        assert exc_info.value.status_code == 503
        assert "Canvas temporarily unavailable" in exc_info.value.detail


@pytest.mark.asyncio
async def test_ensure_valid_canvas_token_no_expiry_date(db: Session) -> None:
    """Test handling when user has no expiry date set"""
    user_in = UserCreate(
        canvas_id=123,
        name="Test User",
        access_token="token_no_expiry",
        refresh_token="refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)
    # expires_at is None by default

    with patch("app.crud.get_decrypted_access_token") as mock_get_token:
        mock_get_token.return_value = "token_no_expiry"

        token = await ensure_valid_canvas_token(db, user)
        assert token == "token_no_expiry"
