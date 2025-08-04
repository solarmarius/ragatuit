"""Tests for authentication service layer."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session

from tests.common_mocks import mock_auth_tokens
from tests.conftest import create_user_in_session
from tests.test_data import get_unique_user_data


def test_create_user_success(session: Session):
    """Test successful user creation with valid data."""
    from src.auth.schemas import UserCreate
    from src.auth.service import create_user

    # Use centralized test data
    test_data = get_unique_user_data()
    user_data = UserCreate(
        canvas_id=test_data["canvas_id"],
        name=test_data["name"],
        access_token=test_data["access_token"],
        refresh_token=test_data["refresh_token"],
    )

    with mock_auth_tokens() as (mock_encrypt, _):
        user = create_user(session, user_data)

    # Verify user was created with correct data
    assert user.canvas_id == test_data["canvas_id"]
    assert user.name == test_data["name"]
    assert user.access_token == f"encrypted_{test_data['access_token']}"
    assert user.refresh_token == f"encrypted_{test_data['refresh_token']}"
    assert user.token_type == "Bearer"
    assert user.onboarding_completed is False
    assert user.created_at is not None
    assert isinstance(user.id, uuid.UUID)

    # Verify tokens were encrypted
    mock_encrypt.assert_any_call(test_data["access_token"])
    mock_encrypt.assert_any_call(test_data["refresh_token"])


def test_create_user_persisted_to_database(session: Session):
    """Test that created user is persisted to database."""
    from src.auth.schemas import UserCreate
    from src.auth.service import create_user

    # Use centralized test data with overrides
    test_data = get_unique_user_data(canvas_id=67890)
    test_data["name"] = "Persistent User"

    user_data = UserCreate(
        canvas_id=test_data["canvas_id"],
        name=test_data["name"],
        access_token=test_data["access_token"],
        refresh_token=test_data["refresh_token"],
    )

    with mock_auth_tokens(encrypt_pattern="enc_{token}") as (_, _):
        user = create_user(session, user_data)

    # Verify user exists in database
    db_user = session.get(user.__class__, user.id)
    assert db_user is not None
    assert db_user.canvas_id == 67890
    assert db_user.name == "Persistent User"


def test_update_user_tokens_access_only(session: Session):
    """Test updating only access token."""
    from src.auth.service import update_user_tokens

    user = create_user_in_session(session)
    original_refresh = user.refresh_token

    new_expires = datetime.now(timezone.utc) + timedelta(hours=2)

    with mock_auth_tokens(encrypt_pattern="new_encrypted_{token}") as (mock_encrypt, _):
        updated_user = update_user_tokens(
            session=session,
            user=user,
            access_token="new_access_token",
            expires_at=new_expires,
        )

    assert updated_user.access_token == "new_encrypted_new_access_token"
    assert updated_user.refresh_token == original_refresh  # Unchanged
    assert updated_user.expires_at == new_expires
    mock_encrypt.assert_called_once_with("new_access_token")


def test_update_user_tokens_both_tokens(session: Session):
    """Test updating both access and refresh tokens."""
    from src.auth.service import update_user_tokens

    user = create_user_in_session(session)

    new_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    with mock_auth_tokens(encrypt_pattern="new_encrypted_{token}") as (mock_encrypt, _):
        updated_user = update_user_tokens(
            session=session,
            user=user,
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            expires_at=new_expires,
        )

    assert updated_user.access_token == "new_encrypted_new_access_token"
    assert updated_user.refresh_token == "new_encrypted_new_refresh_token"
    assert updated_user.expires_at == new_expires

    # Verify both tokens were encrypted
    mock_encrypt.assert_any_call("new_access_token")
    mock_encrypt.assert_any_call("new_refresh_token")


def test_clear_user_tokens(session: Session):
    """Test successful token clearing."""
    from src.auth.service import clear_user_tokens

    user = create_user_in_session(session)

    cleared_user = clear_user_tokens(session, user)

    assert cleared_user.access_token == ""
    assert cleared_user.refresh_token == ""
    assert cleared_user.expires_at is None


def test_get_user_by_canvas_id_existing(session: Session):
    """Test retrieving an existing user by Canvas ID."""
    from src.auth.service import get_user_by_canvas_id

    created_user = create_user_in_session(session, canvas_id=99999)

    found_user = get_user_by_canvas_id(session, 99999)

    assert found_user is not None
    assert found_user.id == created_user.id
    assert found_user.canvas_id == 99999
    assert found_user.name == created_user.name


def test_get_user_by_canvas_id_nonexistent(session: Session):
    """Test retrieving a non-existent user returns None."""
    from src.auth.service import get_user_by_canvas_id

    found_user = get_user_by_canvas_id(session, 999999)
    assert found_user is None


def test_get_user_by_id_existing(session: Session):
    """Test retrieving an existing user by UUID."""
    from src.auth.service import get_user_by_id

    created_user = create_user_in_session(session)

    found_user = get_user_by_id(session, created_user.id)

    assert found_user is not None
    assert found_user.id == created_user.id
    assert found_user.canvas_id == created_user.canvas_id
    assert found_user.name == created_user.name


def test_get_user_by_id_nonexistent(session: Session):
    """Test retrieving a non-existent user by UUID returns None."""
    from src.auth.service import get_user_by_id

    random_uuid = uuid.uuid4()
    found_user = get_user_by_id(session, random_uuid)
    assert found_user is None


def test_get_decrypted_access_token(session: Session):
    """Test decrypting access token."""
    from src.auth.service import get_decrypted_access_token

    user = create_user_in_session(session, access_token="encrypted_access_token")

    with mock_auth_tokens(decrypt_pattern="decrypted_access_token") as (
        _,
        mock_decrypt,
    ):
        decrypted = get_decrypted_access_token(user)

    assert decrypted == "decrypted_access_token"
    mock_decrypt.assert_called_once_with("encrypted_access_token")


def test_get_decrypted_refresh_token(session: Session):
    """Test decrypting refresh token."""
    from src.auth.service import get_decrypted_refresh_token

    user = create_user_in_session(session, refresh_token="encrypted_refresh_token")

    with mock_auth_tokens(decrypt_pattern="decrypted_refresh_token") as (
        _,
        mock_decrypt,
    ):
        decrypted = get_decrypted_refresh_token(user)

    assert decrypted == "decrypted_refresh_token"
    mock_decrypt.assert_called_once_with("encrypted_refresh_token")


def test_user_lifecycle_complete(session: Session):
    """Test complete user lifecycle: create, update, lookup, clear."""
    from src.auth.schemas import UserCreate
    from src.auth.service import (
        clear_user_tokens,
        create_user,
        get_user_by_canvas_id,
        get_user_by_id,
        update_user_tokens,
    )

    # Create user with centralized data
    test_data = get_unique_user_data(canvas_id=11111)
    test_data["name"] = "Lifecycle User"

    user_data = UserCreate(
        canvas_id=test_data["canvas_id"],
        name=test_data["name"],
        access_token=test_data["access_token"],
        refresh_token=test_data["refresh_token"],
    )

    with mock_auth_tokens(encrypt_pattern="enc_{token}") as (_, _):
        user = create_user(session, user_data)

    # Verify creation
    assert user.canvas_id == 11111
    found_user = get_user_by_canvas_id(session, 11111)
    assert found_user is not None
    assert found_user.id == user.id

    # Update tokens
    new_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    with mock_auth_tokens(encrypt_pattern="new_{token}") as (_, _):
        updated_user = update_user_tokens(
            session=session,
            user=user,
            access_token="updated_access",
            refresh_token="updated_refresh",
            expires_at=new_expires,
        )

    assert updated_user.expires_at == new_expires

    # Clear tokens
    cleared_user = clear_user_tokens(session, user)
    assert cleared_user.access_token == ""
    assert cleared_user.refresh_token == ""

    # Verify user still exists but with cleared tokens
    final_user = get_user_by_id(session, user.id)
    assert final_user is not None
    assert final_user.access_token == ""


@pytest.mark.parametrize(
    "canvas_id,name,expected_name",
    [
        (1, "Regular Name", "Regular Name"),
        (2, "", ""),  # Empty name
        (3, "Very Long Name " * 10, "Very Long Name " * 10),  # Long name
        (4, "Special-Chars@123", "Special-Chars@123"),  # Special characters
    ],
)
def test_create_user_various_names(
    session: Session, canvas_id: int, name: str, expected_name: str
):
    """Test user creation with various name formats."""
    from src.auth.schemas import UserCreate
    from src.auth.service import create_user

    # Use centralized test data with overrides
    test_data = get_unique_user_data(canvas_id=canvas_id)

    user_data = UserCreate(
        canvas_id=canvas_id,
        name=name,
        access_token=test_data["access_token"],
        refresh_token=test_data["refresh_token"],
    )

    with mock_auth_tokens(encrypt_pattern="enc_{token}") as (_, _):
        user = create_user(session, user_data)

    assert user.name == expected_name

    # Verify lookup still works
    from src.auth.service import get_user_by_canvas_id

    found = get_user_by_canvas_id(session, canvas_id)
    assert found.name == expected_name
