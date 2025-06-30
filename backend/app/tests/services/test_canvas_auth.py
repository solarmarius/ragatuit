from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlmodel import Session

from app.exceptions import AuthenticationError, ExternalServiceError
from app.models import User
from app.services.canvas_auth import refresh_canvas_token


@pytest.fixture
def mock_user() -> User:
    """Create a mock user with refresh token."""
    return User(
        id="123e4567-e89b-12d3-a456-426614174000",
        canvas_id=12345,
        name="Test User",
        access_token="old_token",
        refresh_token="encrypted_refresh_token",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )


@pytest.mark.asyncio
@patch("app.services.canvas_auth.httpx.AsyncClient")
@patch("app.services.canvas_auth.crud")
async def test_refresh_canvas_token_success(
    mock_crud: MagicMock, mock_httpx: MagicMock, mock_user: User
) -> None:
    """Test successful token refresh."""
    # Setup
    mock_session = MagicMock(spec=Session)
    mock_crud.get_decrypted_refresh_token.return_value = "valid_refresh_token"

    # Mock Canvas response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "expires_in": 3600,
    }
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    # Act
    await refresh_canvas_token(mock_user, mock_session)

    # Assert
    mock_crud.get_decrypted_refresh_token.assert_called_once_with(mock_user)
    mock_client.post.assert_called_once()
    mock_crud.update_user_tokens.assert_called_once_with(
        session=mock_session,
        user=mock_user,
        access_token="new_access_token",
        expires_at=mock_crud.update_user_tokens.call_args[1]["expires_at"],
    )


@pytest.mark.asyncio
async def test_refresh_canvas_token_no_refresh_token() -> None:
    """Test refresh when user has no refresh token."""
    mock_session = MagicMock(spec=Session)
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000",
        canvas_id=12345,
        name="Test User",
        refresh_token="",  # No refresh token
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await refresh_canvas_token(mock_user, mock_session)

    assert exc_info.value.status_code == 401
    assert "No refresh token found" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.canvas_auth.crud")
async def test_refresh_canvas_token_decryption_fails(mock_crud: MagicMock) -> None:
    """Test refresh when token decryption fails."""
    mock_session = MagicMock(spec=Session)
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000",
        canvas_id=12345,
        name="Test User",
        refresh_token="encrypted_token",  # Has refresh token
    )
    mock_crud.get_decrypted_refresh_token.return_value = None  # Decryption failed

    with pytest.raises(AuthenticationError) as exc_info:
        await refresh_canvas_token(mock_user, mock_session)

    assert exc_info.value.status_code == 401
    assert "Refresh token decryption failed" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.canvas_auth.httpx.AsyncClient")
@patch("app.services.canvas_auth.crud")
async def test_refresh_canvas_token_canvas_error(
    mock_crud: MagicMock, mock_httpx: MagicMock, mock_user: User
) -> None:
    """Test refresh when Canvas returns error."""
    mock_session = MagicMock(spec=Session)
    mock_crud.get_decrypted_refresh_token.return_value = "valid_refresh_token"

    # Mock Canvas error response
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Invalid request"

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=mock_response
    )
    mock_httpx.return_value.__aenter__.return_value = mock_client

    with pytest.raises(ExternalServiceError) as exc_info:
        await refresh_canvas_token(mock_user, mock_session)

    assert exc_info.value.status_code == 400
    assert "Token refresh failed" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.canvas_auth.httpx.AsyncClient")
@patch("app.services.canvas_auth.crud")
async def test_refresh_canvas_token_with_url_builder(
    mock_crud: MagicMock, mock_httpx: MagicMock, mock_user: User
) -> None:
    """Test that URL builder is used correctly."""
    mock_session = MagicMock(spec=Session)
    mock_crud.get_decrypted_refresh_token.return_value = "valid_refresh_token"

    # Mock Canvas response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "expires_in": 3600,
    }
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    await refresh_canvas_token(mock_user, mock_session)

    # Verify URL builder was used to construct the token URL
    call_args = mock_client.post.call_args
    token_url = call_args[0][0]
    assert "/login/oauth2/token" in token_url


@pytest.mark.asyncio
@patch("app.services.canvas_auth.httpx.AsyncClient")
@patch("app.services.canvas_auth.crud")
async def test_refresh_canvas_token_expires_at_calculation(
    mock_crud: MagicMock, mock_httpx: MagicMock, mock_user: User
) -> None:
    """Test that expires_at is calculated correctly."""
    mock_session = MagicMock(spec=Session)
    mock_crud.get_decrypted_refresh_token.return_value = "valid_refresh_token"

    # Mock Canvas response with expires_in
    expires_in = 7200  # 2 hours
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "expires_in": expires_in,
    }
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    start_time = datetime.now(timezone.utc)
    await refresh_canvas_token(mock_user, mock_session)
    end_time = datetime.now(timezone.utc)

    # Verify expires_at was set correctly
    mock_crud.update_user_tokens.assert_called_once()
    call_kwargs = mock_crud.update_user_tokens.call_args[1]
    expires_at = call_kwargs["expires_at"]

    # Should be approximately start_time + expires_in seconds
    expected_min = start_time + timedelta(seconds=expires_in)
    expected_max = end_time + timedelta(seconds=expires_in)

    assert expected_min <= expires_at <= expected_max
