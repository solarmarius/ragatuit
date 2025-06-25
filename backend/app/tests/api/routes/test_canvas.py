import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.main import app
from app.models import CanvasCourse, CanvasModule, User


@pytest.mark.asyncio
async def test_get_courses_success() -> None:
    """Test successful course retrieval with teacher enrollment"""
    # Mock Canvas API response
    mock_canvas_courses: list[dict[str, Any]] = [
        {
            "id": 37823,
            "name": "SB_ME_INF-0005 Praktisk kunstig intelligens",
            "account_id": 27925,
            "enrollments": [
                {
                    "type": "teacher",
                    "role": "TeacherEnrollment",
                    "role_id": 4,
                    "user_id": 71202,
                    "enrollment_state": "active",
                }
            ],
        },
        {
            "id": 37824,
            "name": "SB_ME_INF-0006 Bruk av generativ KI",
            "account_id": 27925,
            "enrollments": [
                {
                    "type": "teacher",
                    "role": "TeacherEnrollment",
                    "role_id": 4,
                    "user_id": 71202,
                    "enrollment_state": "active",
                }
            ],
        },
        {
            "id": 37825,
            "name": "Student Course",
            "account_id": 27925,
            "enrollments": [
                {
                    "type": "student",
                    "role": "StudentEnrollment",
                    "role_id": 3,
                    "user_id": 71202,
                    "enrollment_state": "active",
                }
            ],
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
        mock_response.json.return_value = mock_canvas_courses
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses")

            assert response.status_code == 200
            courses = response.json()

            # Should only return teacher courses (2 out of 3)
            assert len(courses) == 2
            assert courses[0]["id"] == 37823
            assert courses[0]["name"] == "SB_ME_INF-0005 Praktisk kunstig intelligens"
            assert courses[1]["id"] == 37824
            assert courses[1]["name"] == "SB_ME_INF-0006 Bruk av generativ KI"

            # Verify Canvas API was called correctly
            mock_client.get.assert_called_once_with(
                "http://canvas-mock:8001/api/v1/courses",
                headers={
                    "Authorization": "Bearer valid_canvas_token",
                    "Accept": "application/json",
                },
            )
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_courses_no_teacher_enrollments() -> None:
    """Test course retrieval when user has no teacher enrollments"""
    # Mock Canvas API response with only student enrollments
    mock_canvas_courses = [
        {
            "id": 37825,
            "name": "Student Course",
            "account_id": 27925,
            "enrollments": [
                {
                    "type": "student",
                    "role": "StudentEnrollment",
                    "role_id": 3,
                    "user_id": 71202,
                    "enrollment_state": "active",
                }
            ],
        }
    ]

    mock_user = User(
        id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        canvas_id=71202,
        name="Test Student",
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
        mock_response.json.return_value = mock_canvas_courses
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses")

            assert response.status_code == 200
            courses = response.json()
            assert len(courses) == 0  # No teacher courses
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_courses_no_access_token() -> None:
    """Test course retrieval when user has no Canvas access token"""
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
        raise HTTPException(
            status_code=401,
            detail="Canvas session expired, Please re-login.",
        )

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/v1/canvas/courses")

        assert response.status_code == 401
        assert "Canvas session expired" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_courses_canvas_unauthorized() -> None:
    """Test course retrieval when Canvas returns 401 (expired token)"""
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
        return "expired_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        # Mock Canvas API 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_http_error = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.get.side_effect = mock_http_error
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses")

            assert response.status_code == 401
            assert "Canvas access token invalid" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_courses_canvas_api_error() -> None:
    """Test course retrieval when Canvas API returns server error"""
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
        # Mock Canvas API 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_http_error = httpx.HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.get.side_effect = mock_http_error
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses")

            assert response.status_code == 503
            assert (
                "Canvas service is temporarily unavailable. Please try again later."
                in response.json()["detail"]
            )
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_courses_network_error() -> None:
    """Test course retrieval when network connection to Canvas fails"""
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
                response = await ac.get("/api/v1/canvas/courses")

            assert response.status_code == 503
            assert "Failed to connect to Canvas API" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_courses_malformed_canvas_data() -> None:
    """Test course retrieval with malformed Canvas API response"""
    # Mock Canvas API response with missing required fields
    mock_canvas_courses = [
        {
            "id": 37823,
            "name": "Valid Course",
            "enrollments": [
                {
                    "type": "teacher",
                    "role": "TeacherEnrollment",
                }
            ],
        },
        {
            # Missing id field
            "name": "Invalid Course 1",
            "enrollments": [{"type": "teacher"}],
        },
        {
            "id": 37825,
            # Missing name field
            "enrollments": [{"type": "teacher"}],
        },
        {
            "id": 37826,
            "name": "Course without enrollments",
            # Missing enrollments field
        },
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
        mock_response.json.return_value = mock_canvas_courses
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses")

            assert response.status_code == 200
            courses = response.json()

            # Should only return the valid course (1 out of 4)
            assert len(courses) == 1
            assert courses[0]["id"] == 37823
            assert courses[0]["name"] == "Valid Course"
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_courses_unauthorized_no_jwt() -> None:
    """Test course retrieval without authentication"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/canvas/courses")

    # Should return 403 because no authentication provided
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_file_info_success() -> None:
    """Test successful file info retrieval"""
    mock_file_data = {
        "id": 3611093,
        "folder_id": 708060,
        "display_name": "linear_algebra_in_4_pages.pdf",
        "filename": "linear_algebra_in_4_pages.pdf",
        "uuid": "DbkzelfegXe2xwtsWlcwJyUg074Kwk3rSxKyC32x",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3611093/download?download_frd=1&verifier=DbkzelfegXe2xwtsWlcwJyUg074Kwk3rSxKyC32x",
        "size": 258646,
        "created_at": "2025-06-25T06:24:29Z",
        "updated_at": "2025-06-25T06:24:29Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-06-25T06:24:29Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
    }

    mock_user = User(
        id=uuid.uuid4(),
        canvas_id=71202,
        name="Test User",
        access_token="valid_access_token",
        refresh_token="valid_refresh_token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_file_data
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses/37823/files/3611093")

            assert response.status_code == 200
            file_info = response.json()

            # Check essential fields are present and correct
            assert file_info["id"] == 3611093
            assert file_info["display_name"] == "linear_algebra_in_4_pages.pdf"
            assert file_info["filename"] == "linear_algebra_in_4_pages.pdf"
            assert file_info["content-type"] == "application/pdf"
            assert file_info["mime_class"] == "pdf"
            assert file_info["size"] == 258646
            assert "download" in file_info["url"]  # Contains download URL

            # Verify Canvas API was called with correct parameters
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "courses/37823/files/3611093" in call_args[0][0]
            assert (
                call_args[1]["headers"]["Authorization"] == "Bearer valid_canvas_token"
            )

        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_file_info_invalid_parameters() -> None:
    """Test file info retrieval with invalid parameters"""
    mock_user = User(
        id=uuid.uuid4(),
        canvas_id=71202,
        name="Test User",
        access_token="valid_access_token",
        refresh_token="valid_refresh_token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
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
            # Test negative course ID
            response = await ac.get("/api/v1/canvas/courses/-1/files/123")
            assert response.status_code == 400

            # Test zero course ID
            response = await ac.get("/api/v1/canvas/courses/0/files/123")
            assert response.status_code == 400

            # Test negative file ID
            response = await ac.get("/api/v1/canvas/courses/123/files/-1")
            assert response.status_code == 400

            # Test zero file ID
            response = await ac.get("/api/v1/canvas/courses/123/files/0")
            assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_file_info_canvas_errors() -> None:
    """Test file info retrieval with various Canvas API errors"""
    mock_user = User(
        id=uuid.uuid4(),
        canvas_id=71202,
        name="Test User",
        access_token="valid_access_token",
        refresh_token="valid_refresh_token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client

        # Test 401 Unauthorized
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        mock_response_401.text = "Unauthorized"
        mock_http_error_401 = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response_401
        )
        mock_client.get.side_effect = mock_http_error_401

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses/37823/files/3611093")
            assert response.status_code == 401
        finally:
            pass

        # Test 403 Forbidden
        mock_response_403 = MagicMock()
        mock_response_403.status_code = 403
        mock_response_403.text = "Forbidden"
        mock_http_error_403 = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=mock_response_403
        )
        mock_client.get.side_effect = mock_http_error_403

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses/37823/files/3611093")
            assert response.status_code == 403
        finally:
            pass

        # Test 404 Not Found
        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404
        mock_response_404.text = "Not Found"
        mock_http_error_404 = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response_404
        )
        mock_client.get.side_effect = mock_http_error_404

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses/37823/files/3611093")
            assert response.status_code == 404
        finally:
            pass

        # Test 500 Server Error
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.text = "Internal Server Error"
        mock_http_error_500 = httpx.HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=mock_response_500
        )
        mock_client.get.side_effect = mock_http_error_500

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses/37823/files/3611093")
            assert response.status_code == 503  # Maps to service unavailable
        finally:
            pass

        # Test network error
        mock_request_error = httpx.RequestError("Connection failed")
        mock_client.get.side_effect = mock_request_error

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses/37823/files/3611093")
            assert response.status_code == 503
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_file_info_invalid_response() -> None:
    """Test file info retrieval with invalid Canvas response format"""
    mock_user = User(
        id=uuid.uuid4(),
        canvas_id=71202,
        name="Test User",
        access_token="valid_access_token",
        refresh_token="valid_refresh_token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    def mock_get_current_user() -> User:
        return mock_user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        mock_response = MagicMock()
        mock_response.json.return_value = (
            "invalid_response_format"  # String instead of dict
        )
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/canvas/courses/37823/files/3611093")

            assert response.status_code == 500
            error_detail = response.json()
            assert "Invalid response format" in error_detail["detail"]

        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_canvas_course_model() -> None:
    """Test CanvasCourse model validation"""
    # Valid course
    course = CanvasCourse(id=123, name="Test Course")
    assert course.id == 123
    assert course.name == "Test Course"

    # Test serialization
    course_dict = course.model_dump()
    assert course_dict == {"id": 123, "name": "Test Course"}

    # Test deserialization
    course_from_dict = CanvasCourse.model_validate(
        {"id": 456, "name": "Another Course"}
    )
    assert course_from_dict.id == 456
    assert course_from_dict.name == "Another Course"


# ==================== MODULE ENDPOINT TESTS ====================


@pytest.mark.asyncio
async def test_get_course_modules_success() -> None:
    """Test successful module retrieval for a course"""
    course_id = 37823

    # Mock Canvas API response
    mock_canvas_modules: list[dict[str, Any]] = [
        {
            "id": 173467,
            "name": "Templates",
            "position": 1,
            "unlock_at": None,
            "require_sequential_progress": False,
            "published": True,
            "items_count": 0,
        },
        {
            "id": 173468,
            "name": "Ressurssider for studenter",
            "position": 2,
            "unlock_at": None,
            "require_sequential_progress": False,
            "published": True,
            "items_count": 2,
        },
        {
            "id": 173469,
            "name": "Hjelperessurser for underviser",
            "position": 3,
            "unlock_at": None,
            "require_sequential_progress": False,
            "published": False,
            "items_count": 1,
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
        mock_response.json.return_value = mock_canvas_modules
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(f"/api/v1/canvas/courses/{course_id}/modules")

            assert response.status_code == 200
            modules = response.json()

            # Should return all modules (simplified to id and name only)
            assert len(modules) == 3
            assert modules[0]["id"] == 173467
            assert modules[0]["name"] == "Templates"
            assert modules[1]["id"] == 173468
            assert modules[1]["name"] == "Ressurssider for studenter"
            assert modules[2]["id"] == 173469
            assert modules[2]["name"] == "Hjelperessurser for underviser"

            # Should only have id and name fields (simplified model)
            for module in modules:
                assert list(module.keys()) == ["id", "name"]

            # Verify Canvas API was called correctly
            mock_client.get.assert_called_once_with(
                f"http://canvas-mock:8001/api/v1/courses/{course_id}/modules",
                headers={
                    "Authorization": "Bearer valid_canvas_token",
                    "Accept": "application/json",
                },
            )
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_course_modules_empty_course() -> None:
    """Test module retrieval for course with no modules"""
    course_id = 37823

    # Mock Canvas API response with empty modules
    mock_canvas_modules: list[Any] = []

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
        mock_response.json.return_value = mock_canvas_modules
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(f"/api/v1/canvas/courses/{course_id}/modules")

            assert response.status_code == 200
            modules = response.json()
            assert len(modules) == 0  # No modules
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_course_modules_unauthorized() -> None:
    """Test module retrieval when user doesn't have access to course"""
    course_id = 99999  # Course user doesn't have access to

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
                response = await ac.get(f"/api/v1/canvas/courses/{course_id}/modules")

            assert response.status_code == 403
            assert "You don't have access to this course" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_course_modules_malformed_data() -> None:
    """Test module retrieval with malformed Canvas API response"""
    course_id = 37823

    # Mock Canvas API response with malformed data
    mock_canvas_modules: list[dict[str, Any] | str] = [
        {
            "id": 173467,
            "name": "Valid Module",
            "position": 1,
        },
        {
            # Missing id field
            "name": "Invalid Module 1",
            "position": 2,
        },
        {
            "id": 173469,
            # Missing name field
            "position": 3,
        },
        {
            "id": "173470",  # String ID (should be converted)
            "name": "Module with String ID",
            "position": 4,
        },
        "invalid_module_type",  # Not a dict
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
        mock_response.json.return_value = mock_canvas_modules
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(f"/api/v1/canvas/courses/{course_id}/modules")

            assert response.status_code == 200
            modules = response.json()

            # Should only return valid modules (2 out of 5)
            assert len(modules) == 2
            assert modules[0]["id"] == 173467
            assert modules[0]["name"] == "Valid Module"
            assert modules[1]["id"] == 173470  # Converted from string
            assert modules[1]["name"] == "Module with String ID"
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_course_modules_canvas_token_expired() -> None:
    """Test module retrieval when Canvas token is expired"""
    course_id = 37823

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
        return "expired_canvas_token"

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

    with patch("app.api.routes.canvas.httpx.AsyncClient") as mock_httpx:
        # Mock Canvas API 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_http_error = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.get.side_effect = mock_http_error
        mock_httpx.return_value.__aenter__.return_value = mock_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(f"/api/v1/canvas/courses/{course_id}/modules")

            assert response.status_code == 401
            assert "Canvas access token invalid" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_course_modules_network_error() -> None:
    """Test module retrieval when network connection to Canvas fails"""
    course_id = 37823

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
                response = await ac.get(f"/api/v1/canvas/courses/{course_id}/modules")

            assert response.status_code == 503
            assert "Failed to connect to Canvas API" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_canvas_module_model() -> None:
    """Test CanvasModule model validation"""
    # Valid module
    module = CanvasModule(id=123, name="Test Module")
    assert module.id == 123
    assert module.name == "Test Module"

    # Test serialization
    module_dict = module.model_dump()
    assert module_dict == {"id": 123, "name": "Test Module"}

    # Test deserialization
    module_from_dict = CanvasModule.model_validate(
        {"id": 456, "name": "Another Module"}
    )
    assert module_from_dict.id == 456
    assert module_from_dict.name == "Another Module"
