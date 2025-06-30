from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.auth.models import User
from app.auth.service import AuthService
from app.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_login_canvas() -> None:
    """Test Canvas login redirect"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/auth/login/canvas")

    assert response.status_code == 307
    assert "canvas" in response.headers["location"]
    assert "client_id" in response.headers["location"]
    assert "redirect_uri" in response.headers["location"]
    assert "state" in response.headers["location"]


@pytest.mark.asyncio
@patch("app.api.routes.auth.httpx.AsyncClient")
@patch("app.auth.router.AuthService")
async def test_auth_canvas_callback_new_user(
    mock_auth_service_class: MagicMock, mock_httpx: MagicMock
) -> None:
    """Test Canvas callback for new user"""
    # Mock Canvas token response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "canvas_access_token",
        "refresh_token": "canvas_refresh_token",
        "expires_in": 3600,
        "user": {"id": "123", "name": "Test User"},
    }
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    mock_response.text = "success"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    # Mock AuthService instance
    mock_auth_service = MagicMock()
    mock_auth_service.get_user_by_canvas_id.return_value = None
    mock_user = User(id=1, canvas_id="123", name="Test User")
    mock_auth_service.create_user.return_value = mock_user
    mock_auth_service_class.return_value = mock_auth_service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as ac:
        response = await ac.get(
            "/api/v1/auth/callback/canvas?code=test_code&state=test_state"
        )

    # Should redirect to frontend with success token
    assert response.status_code == 307
    assert response.headers["location"].startswith(
        f"{settings.FRONTEND_HOST}/login/success?token="
    )

    # Verify create_user was called
    mock_auth_service.create_user.assert_called_once()


@pytest.mark.asyncio
@patch("app.api.routes.auth.httpx.AsyncClient")
@patch("app.auth.router.AuthService")
async def test_auth_canvas_callback_existing_user(
    mock_auth_service_class: MagicMock, mock_httpx: MagicMock
) -> None:
    """Test Canvas callback for existing user"""
    # Mock Canvas token response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "canvas_access_token",
        "refresh_token": "canvas_refresh_token",
        "expires_in": 3600,
        "user": {"id": "123", "name": "Test User"},
    }
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    mock_response.text = "success"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    # Mock AuthService instance
    mock_auth_service = MagicMock()
    mock_user = User(id=1, canvas_id="123", name="Test User")
    mock_auth_service.get_user_by_canvas_id.return_value = mock_user
    mock_auth_service.update_user_tokens.return_value = mock_user
    mock_auth_service_class.return_value = mock_auth_service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as ac:
        response = await ac.get(
            "/api/v1/auth/callback/canvas?code=test_code&state=test_state"
        )

    # Should redirect to frontend with success token
    assert response.status_code == 307
    assert response.headers["location"].startswith(
        f"{settings.FRONTEND_HOST}/login/success?token="
    )

    # Verify update_user_tokens was called
    mock_auth_service.update_user_tokens.assert_called_once()


@pytest.mark.asyncio
@patch("app.api.routes.auth.httpx.AsyncClient")
async def test_auth_canvas_callback_canvas_error(mock_httpx: MagicMock) -> None:
    """Test Canvas callback when Canvas returns error"""
    mock_client = AsyncMock()
    mock_response = MagicMock()

    # Create a proper mock response for HTTPStatusError
    mock_error_response = MagicMock()
    mock_error_response.status_code = 400
    mock_error_response.text = "Canvas authentication failed"

    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Canvas error", request=MagicMock(), response=mock_error_response
    )
    mock_response.status_code = 400
    mock_response.text = "Canvas authentication failed"
    mock_client.post.return_value = mock_response
    mock_httpx.return_value.__aenter__.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as ac:
        response = await ac.get(
            "/api/v1/auth/callback/canvas?code=test_code&state=test_state"
        )

    # Should redirect to frontend with error
    assert response.status_code == 307
    assert response.headers["location"].startswith(
        f"{settings.FRONTEND_HOST}/login?error="
    )
    assert "Canvas%20OAUTH%20error" in response.headers["location"]


@pytest.mark.asyncio
async def test_auth_canvas_callback_missing_code() -> None:
    """Test Canvas callback without authorization code"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as ac:
        response = await ac.get("/api/v1/auth/callback/canvas?state=test_state")

    # Should redirect to frontend with error
    assert response.status_code == 307
    assert response.headers["location"].startswith(
        f"{settings.FRONTEND_HOST}/login?error="
    )
    assert "Authorization%20code%20not%20provided" in response.headers["location"]


@pytest.mark.asyncio
@patch("app.auth.router.AuthService")
async def test_logout_canvas(mock_auth_service_class: MagicMock) -> None:
    """Test Canvas logout"""
    # Mock authenticated user
    mock_user = User(id=1, canvas_id="123", name="Test User")

    # Mock AuthService instance
    mock_auth_service = MagicMock()
    mock_auth_service.get_decrypted_access_token.return_value = "test_token"
    mock_auth_service_class.return_value = mock_auth_service

    # Override the dependency
    def mock_get_current_user() -> User:
        return mock_user

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.delete("/api/v1/auth/logout")

        assert response.status_code == 200
        assert "disconnected successfully" in response.json()["message"]
        mock_auth_service.clear_user_tokens.assert_called_once()
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_canvas_invalid_base_url() -> None:
    """Test login with invalid Canvas base URL"""
    with patch("app.config.settings.CANVAS_BASE_URL", "invalid-url"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/v1/auth/login/canvas")

    assert response.status_code == 400
    assert "Invalid Canvas base URL" in response.json()["detail"]
