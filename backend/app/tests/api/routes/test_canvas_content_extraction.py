import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.auth.models import User
from app.main import app

# ==================== MODULE ITEMS ENDPOINT TESTS ====================


@pytest.mark.asyncio
async def test_get_module_items_success() -> None:
    """Test successful module items retrieval"""
    course_id = 37823
    module_id = 173467

    # Mock Canvas API response
    mock_module_items: list[dict[str, Any]] = [
        {
            "id": 1001,
            "title": "Introduction to AI",
            "type": "Page",
            "html_url": "https://canvas.uit.no/courses/37823/pages/introduction-to-ai",
            "page_url": "introduction-to-ai",
            "url": "https://canvas.uit.no/api/v1/courses/37823/pages/introduction-to-ai",
        },
        {
            "id": 1002,
            "title": "Assignment 1",
            "type": "Assignment",
            "html_url": "https://canvas.uit.no/courses/37823/assignments/5001",
            "assignment_id": 5001,
            "url": "https://canvas.uit.no/api/v1/courses/37823/assignments/5001",
        },
        {
            "id": 1003,
            "title": "Machine Learning Basics",
            "type": "Page",
            "html_url": "https://canvas.uit.no/courses/37823/pages/ml-basics",
            "page_url": "ml-basics",
            "url": "https://canvas.uit.no/api/v1/courses/37823/pages/ml-basics",
        },
    ]

    # Mock authenticated user
    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test Teacher",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        # Mock Canvas API response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_module_items
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/modules/{module_id}/items"
                )

            assert response.status_code == 200
            items = response.json()

            # Should return all items with processed fields
            assert len(items) == 3
            assert items[0]["id"] == 1001
            assert items[0]["title"] == "Introduction to AI"
            assert items[0]["type"] == "Page"
            assert items[0]["page_url"] == "introduction-to-ai"
            assert items[1]["id"] == 1002
            assert items[1]["title"] == "Assignment 1"
            assert items[1]["type"] == "Assignment"
            assert items[2]["id"] == 1003
            assert items[2]["title"] == "Machine Learning Basics"
            assert items[2]["type"] == "Page"

            # Verify Canvas API was called correctly
            mock_client.get.assert_called_once_with(
                f"http://canvas-mock:8001/api/v1/courses/{course_id}/modules/{module_id}/items",
                headers={
                    "Authorization": "Bearer valid_canvas_token",
                    "Accept": "application/json",
                },
            )
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_module_items_empty_module() -> None:
    """Test module items retrieval for module with no items"""
    course_id = 37823
    module_id = 173467

    # Mock Canvas API response with empty items
    mock_module_items: list[Any] = []

    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test Teacher",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_module_items
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/modules/{module_id}/items"
                )

            assert response.status_code == 200
            items = response.json()
            assert len(items) == 0  # No items
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_module_items_invalid_parameters() -> None:
    """Test module items retrieval with invalid parameters"""
    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # Test invalid course_id
            response = await ac.get("/api/v1/canvas/courses/0/modules/173467/items")
            assert response.status_code == 400
            assert (
                "Course ID and Module ID must be positive integers"
                in response.json()["detail"]
            )

            # Test invalid module_id
            response = await ac.get("/api/v1/canvas/courses/37823/modules/-1/items")
            assert response.status_code == 400
            assert (
                "Course ID and Module ID must be positive integers"
                in response.json()["detail"]
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_module_items_unauthorized() -> None:
    """Test module items retrieval when user doesn't have access to module"""
    course_id = 37823
    module_id = 99999  # Module user doesn't have access to

    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        # Mock Canvas API 403 response
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        mock_http_error = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.get.side_effect = mock_http_error
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/modules/{module_id}/items"
                )

            assert response.status_code == 403
            assert (
                "You don't have access to this course or module"
                in response.json()["detail"]
            )
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_module_items_malformed_data() -> None:
    """Test module items retrieval with malformed Canvas API response"""
    course_id = 37823
    module_id = 173467

    # Mock Canvas API response with malformed data
    mock_module_items: list[dict[str, Any] | str] = [
        {
            "id": 1001,
            "title": "Valid Item",
            "type": "Page",
            "page_url": "valid-page",
        },
        {
            # Missing id field
            "title": "Invalid Item 1",
            "type": "Page",
        },
        {
            "id": 1003,
            # Missing title field
            "type": "Page",
        },
        {
            "id": "1004",  # String ID (should be converted)
            "title": "Item with String ID",
            "type": "Page",
        },
        "invalid_item_type",  # Not a dict
    ]

    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_module_items
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/modules/{module_id}/items"
                )

            assert response.status_code == 200
            items = response.json()

            # Should only return valid items (3 out of 5 - missing title gets "Untitled")
            assert len(items) == 3
            assert items[0]["id"] == 1001
            assert items[0]["title"] == "Valid Item"
            assert items[1]["id"] == 1003  # Missing title becomes "Untitled"
            assert items[1]["title"] == "Untitled"
            assert items[2]["id"] == 1004  # Converted from string
            assert items[2]["title"] == "Item with String ID"
        finally:
            app.dependency_overrides.clear()


# ==================== PAGE CONTENT ENDPOINT TESTS ====================


@pytest.mark.asyncio
async def test_get_page_content_success() -> None:
    """Test successful page content retrieval"""
    course_id = 37823
    page_url = "introduction-to-ai"

    # Mock Canvas API response
    mock_page_content = {
        "title": "Introduction to AI",
        "body": "<h1>Introduction</h1><p>Artificial Intelligence is the simulation of human intelligence in machines.</p>",
        "url": "introduction-to-ai",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-02T12:00:00Z",
        "published": True,
    }

    # Mock authenticated user
    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test Teacher",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        # Mock Canvas API response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_page_content
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/pages/{page_url}"
                )

            assert response.status_code == 200
            page = response.json()

            # Should return processed page content
            assert page["title"] == "Introduction to AI"
            assert "Artificial Intelligence is the simulation" in page["body"]
            assert page["url"] == "introduction-to-ai"
            assert page["created_at"] == "2023-01-01T12:00:00Z"
            assert page["updated_at"] == "2023-01-02T12:00:00Z"

            # Verify Canvas API was called correctly
            mock_client.get.assert_called_once_with(
                f"http://canvas-mock:8001/api/v1/courses/{course_id}/pages/{page_url}",
                headers={
                    "Authorization": "Bearer valid_canvas_token",
                    "Accept": "application/json",
                },
            )
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_page_content_special_characters() -> None:
    """Test page content retrieval with special characters in URL"""
    course_id = 37823
    page_url = "test page with spaces & symbols"

    mock_page_content = {
        "title": "Test Page",
        "body": "<h1>Test Content</h1>",
        "url": page_url,
    }

    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_page_content
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/pages/{page_url}"
                )

            assert response.status_code == 200
            page = response.json()
            assert page["title"] == "Test Page"

            # Verify URL encoding was applied
            expected_encoded_url = "test%20page%20with%20spaces%20%26%20symbols"
            mock_client.get.assert_called_once_with(
                f"http://canvas-mock:8001/api/v1/courses/{course_id}/pages/{expected_encoded_url}",
                headers={
                    "Authorization": "Bearer valid_canvas_token",
                    "Accept": "application/json",
                },
            )
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_page_content_invalid_parameters() -> None:
    """Test page content retrieval with invalid parameters"""
    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # Test invalid course_id
            response = await ac.get("/api/v1/canvas/courses/0/pages/test-page")
            assert response.status_code == 400
            assert "Course ID must be a positive integer" in response.json()["detail"]

            # Test empty page_url
            response = await ac.get("/api/v1/canvas/courses/37823/pages/")
            assert response.status_code == 404  # FastAPI route not found

            # Test whitespace-only page_url
            response = await ac.get("/api/v1/canvas/courses/37823/pages/%20%20")
            assert response.status_code == 400
            assert "Page URL cannot be empty" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_page_content_page_not_found() -> None:
    """Test page content retrieval when page doesn't exist"""
    course_id = 37823
    page_url = "nonexistent-page"

    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        # Mock Canvas API 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_http_error = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.get.side_effect = mock_http_error
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/pages/{page_url}"
                )

            assert response.status_code == 404
            assert "Page not found in this course" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_page_content_malformed_response() -> None:
    """Test page content retrieval with malformed Canvas API response"""
    course_id = 37823
    page_url = "test-page"

    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        # Mock non-dict response
        mock_response = MagicMock()
        mock_response.json.return_value = "invalid response format"
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/pages/{page_url}"
                )

            assert response.status_code == 500
            assert "Invalid response format from Canvas" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_page_content_empty_body_handling() -> None:
    """Test page content retrieval with empty or None body"""
    course_id = 37823
    page_url = "empty-page"

    mock_page_content = {
        "title": "Empty Page",
        "body": None,  # None body should be handled
        "url": "empty-page",
    }

    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_page_content
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/pages/{page_url}"
                )

            assert response.status_code == 200
            page = response.json()
            assert page["title"] == "Empty Page"
            assert page["body"] == ""  # None should be converted to empty string
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_page_content_network_error() -> None:
    """Test page content retrieval when network connection to Canvas fails"""
    course_id = 37823
    page_url = "test-page"

    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        # Mock network error
        mock_request_error = httpx.RequestError("Connection failed")

        mock_client = AsyncMock()
        mock_client.get.side_effect = mock_request_error
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    f"/api/v1/canvas/courses/{course_id}/pages/{page_url}"
                )

            assert response.status_code == 503
            assert "Failed to connect to Canvas API" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
