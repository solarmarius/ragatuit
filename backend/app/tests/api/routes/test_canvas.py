import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.main import app
from app.models import CanvasCourse, User


@pytest.mark.asyncio
async def test_get_courses_success() -> None:
    """Test successful course retrieval with teacher enrollment"""
    # Mock Canvas API response
    mock_canvas_courses = [
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
            assert "Canvas API error: 500" in response.json()["detail"]
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
