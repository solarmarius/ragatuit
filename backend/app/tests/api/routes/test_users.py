from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.main import app
from app.models import User


@pytest.mark.asyncio
async def test_read_user_me():
    """Test reading current user profile"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Override the dependency
    def mock_get_current_user():
        return mock_user

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/v1/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == mock_user.name
        # Should not include sensitive fields like tokens
        assert "access_token" not in data
        assert "refresh_token" not in data
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_user_me_name():
    """Test updating current user's name"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Old Name"
    )

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user():
        return mock_user

    def mock_get_db():
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.patch("/api/v1/users/me", json={"name": "New Name"})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

        # Verify session operations were called
        mock_session.add.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_user)
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_user_me_empty_data():
    """Test updating user with empty data returns validation error"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Override dependencies
    def mock_get_current_user():
        return mock_user

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.patch("/api/v1/users/me", json={})

        # Empty data should return validation error
        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_user_me_invalid_field():
    """Test updating user with invalid/protected field"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user():
        return mock_user

    def mock_get_db():
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.patch(
                "/api/v1/users/me",
                json={
                    "name": "New Name",
                    "canvas_id": "999",  # This should be ignored
                    "id": "new-id",  # This should be ignored
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_user_me():
    """Test deleting current user"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user():
        return mock_user

    def mock_get_db():
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.delete("/api/v1/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User deleted successfully"

        # Verify user was deleted from session
        mock_session.delete.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_users_routes_require_authentication():
    """Test that all user routes require authentication"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Test GET /users/me
        response = await ac.get("/api/v1/users/me")
        assert response.status_code in [401, 403]  # Unauthorized or Forbidden

        # Test PATCH /users/me
        response = await ac.patch("/api/v1/users/me", json={"name": "New Name"})
        assert response.status_code in [401, 403]

        # Test DELETE /users/me
        response = await ac.delete("/api/v1/users/me")
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_update_user_me_invalid_json():
    """Test updating user with invalid JSON data"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user():
        return mock_user

    def mock_get_db():
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # Send invalid data type for name
            response = await ac.patch(
                "/api/v1/users/me",
                json={"name": 123},  # Should be string
            )

        assert response.status_code == 422  # Validation error
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_users_routes_with_invalid_token():
    """Test that routes with invalid token return 403"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Test with invalid Authorization header
        headers = {"Authorization": "Bearer invalid_token"}

        response = await ac.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 403
        assert "Could not validate credentials" in response.json()["detail"]

        response = await ac.patch(
            "/api/v1/users/me", json={"name": "Test"}, headers=headers
        )
        assert response.status_code == 403

        response = await ac.delete("/api/v1/users/me", headers=headers)
        assert response.status_code == 403
