from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.auth.models import User
from app.main import app
from app.quiz.models import Quiz


@pytest.mark.asyncio
async def test_create_quiz_success() -> None:
    """Test successful quiz creation"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Mock session
    mock_session = MagicMock()

    # Mock the created quiz
    mock_quiz = Quiz(
        id=uuid4(),
        owner_id=mock_user.id,
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules='{"173467": "Module 1"}',
        title="Test Quiz",
        question_count=100,
        llm_model="o3",
        llm_temperature=0.3,
    )

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.create_quiz", return_value=mock_quiz):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.post(
                    "/api/v1/quiz/",
                    json={
                        "canvas_course_id": 12345,
                        "canvas_course_name": "Test Course",
                        "selected_modules": {"173467": "Module 1"},
                        "title": "Test Quiz",
                        "question_count": 100,
                        "llm_model": "o3",
                        "llm_temperature": 0.3,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["canvas_course_id"] == 12345
        assert data["canvas_course_name"] == "Test Course"
        assert data["title"] == "Test Quiz"
        assert data["question_count"] == 100
        assert data["llm_model"] == "o3"
        assert data["llm_temperature"] == 0.3
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_quiz_with_defaults() -> None:
    """Test quiz creation using default values"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Mock session
    mock_session = MagicMock()

    # Mock the created quiz with defaults
    mock_quiz = Quiz(
        id=uuid4(),
        owner_id=mock_user.id,
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules='{"173467": "Module 1"}',
        title="Default Quiz",
        question_count=100,  # Default
        llm_model="o3",  # Default
        llm_temperature=0.3,  # Default
    )

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.create_quiz", return_value=mock_quiz):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.post(
                    "/api/v1/quiz/",
                    json={
                        "canvas_course_id": 12345,
                        "canvas_course_name": "Test Course",
                        "selected_modules": {"173467": "Module 1"},
                        "title": "Default Quiz",
                        # Omit optional fields to test defaults
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["question_count"] == 100
        assert data["llm_model"] == "o3"
        assert data["llm_temperature"] == 0.3
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_quiz_validation_error() -> None:
    """Test quiz creation with invalid data"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # Missing required fields
            response = await ac.post(
                "/api/v1/quiz/",
                json={
                    "canvas_course_id": 12345,
                    # Missing canvas_course_name, selected_modules, title
                },
            )

        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_quiz_server_error() -> None:
    """Test quiz creation with server error"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.create_quiz", side_effect=Exception("Database error")):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.post(
                    "/api/v1/quiz/",
                    json={
                        "canvas_course_id": 12345,
                        "canvas_course_name": "Test Course",
                        "selected_modules": {"173467": "Module 1"},
                        "title": "Test Quiz",
                    },
                )

        assert response.status_code == 500
        error_detail = response.json()
        assert "Failed to create quiz" in error_detail["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_quiz_by_id_success() -> None:
    """Test successful quiz retrieval by ID"""
    quiz_id = uuid4()
    user_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock authenticated user
    mock_user = User(id=user_id, canvas_id=12345, name="Test User")

    # Mock session
    mock_session = MagicMock()

    # Mock the quiz
    mock_quiz = Quiz(
        id=quiz_id,
        owner_id=user_id,
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules='{"173467": "Module 1"}',
        title="Test Quiz",
        question_count=50,
        llm_model="gpt-4o",
        llm_temperature=0.5,
    )

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.get_quiz_by_id", return_value=mock_quiz):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(f"/api/v1/quiz/{quiz_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(quiz_id)
        assert data["owner_id"] == user_id
        assert data["title"] == "Test Quiz"
        assert data["question_count"] == 50
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_quiz_by_id_not_found() -> None:
    """Test quiz retrieval with non-existent ID"""
    quiz_id = uuid4()

    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.get_quiz_by_id", return_value=None):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(f"/api/v1/quiz/{quiz_id}")

        assert response.status_code == 404
        error_detail = response.json()
        assert "Quiz not found" in error_detail["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_quiz_by_id_access_denied() -> None:
    """Test quiz retrieval when user doesn't own the quiz"""
    quiz_id = uuid4()
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    other_user_id = "987e6543-e21b-43d2-b654-321987654321"

    # Mock authenticated user
    mock_user = User(id=user_id, canvas_id=12345, name="Test User")

    # Mock session
    mock_session = MagicMock()

    # Mock quiz owned by different user
    mock_quiz = Quiz(
        id=quiz_id,
        owner_id=other_user_id,  # Different owner
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules='{"173467": "Module 1"}',
        title="Other User Quiz",
        question_count=50,
        llm_model="gpt-4o",
        llm_temperature=0.5,
    )

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.get_quiz_by_id", return_value=mock_quiz):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(f"/api/v1/quiz/{quiz_id}")

        assert response.status_code == 404
        error_detail = response.json()
        assert "Quiz not found" in error_detail["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_user_quizzes_success() -> None:
    """Test successful retrieval of user's quizzes"""
    user_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock authenticated user
    mock_user = User(id=user_id, canvas_id=12345, name="Test User")

    # Mock session
    mock_session = MagicMock()

    # Mock quiz list
    mock_quizzes = [
        Quiz(
            id=uuid4(),
            owner_id=user_id,
            canvas_course_id=12345,
            canvas_course_name="Course 1",
            selected_modules='{"173467": "Module 1"}',
            title="Quiz 1",
            question_count=50,
            llm_model="gpt-4o",
            llm_temperature=0.3,
        ),
        Quiz(
            id=uuid4(),
            owner_id=user_id,
            canvas_course_id=67890,
            canvas_course_name="Course 2",
            selected_modules='{"173468": "Module 2"}',
            title="Quiz 2",
            question_count=75,
            llm_model="o3",
            llm_temperature=0.5,
        ),
    ]

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.get_user_quizzes", return_value=mock_quizzes):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/quiz/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Quiz 1"
        assert data[1]["title"] == "Quiz 2"
        assert all(quiz["owner_id"] == user_id for quiz in data)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_user_quizzes_empty() -> None:
    """Test retrieval of user's quizzes when none exist"""
    user_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock authenticated user
    mock_user = User(id=user_id, canvas_id=12345, name="Test User")

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.get_user_quizzes", return_value=[]):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/quiz/")

        assert response.status_code == 200
        data = response.json()
        assert data == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_quiz_routes_require_authentication() -> None:
    """Test that all quiz routes require authentication"""
    quiz_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Test POST /api/v1/quiz/
        response = await ac.post(
            "/api/v1/quiz/",
            json={
                "canvas_course_id": 12345,
                "canvas_course_name": "Test Course",
                "selected_modules": {"173467": "Module 1"},
                "title": "Test Quiz",
            },
        )
        assert response.status_code in [401, 403]

        # Test GET /api/v1/quiz/{id}
        response = await ac.get(f"/api/v1/quiz/{quiz_id}")
        assert response.status_code in [401, 403]

        # Test GET /api/v1/quiz/
        response = await ac.get("/api/v1/quiz/")
        assert response.status_code in [401, 403]

        # Test DELETE /api/v1/quiz/{id}
        response = await ac.delete(f"/api/v1/quiz/{quiz_id}")
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_quiz_routes_with_invalid_token() -> None:
    """Test that routes with invalid token return 403"""
    quiz_id = uuid4()
    headers = {"Authorization": "Bearer invalid_token"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Test POST /api/v1/quiz/
        response = await ac.post(
            "/api/v1/quiz/",
            json={
                "canvas_course_id": 12345,
                "canvas_course_name": "Test Course",
                "selected_modules": {"173467": "Module 1"},
                "title": "Test Quiz",
            },
            headers=headers,
        )
        assert response.status_code == 403
        assert "Could not validate credentials" in response.json()["detail"]

        # Test GET /api/v1/quiz/{id}
        response = await ac.get(f"/api/v1/quiz/{quiz_id}", headers=headers)
        assert response.status_code == 403

        # Test GET /api/v1/quiz/
        response = await ac.get("/api/v1/quiz/", headers=headers)
        assert response.status_code == 403

        # Test DELETE /api/v1/quiz/{id}
        response = await ac.delete(f"/api/v1/quiz/{quiz_id}", headers=headers)
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_quiz_field_validation() -> None:
    """Test quiz creation with field validation constraints"""
    # Mock authenticated user
    mock_user = User(
        id="123e4567-e89b-12d3-a456-426614174000", canvas_id=12345, name="Test User"
    )

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # Test invalid question_count (too low)
            response = await ac.post(
                "/api/v1/quiz/",
                json={
                    "canvas_course_id": 12345,
                    "canvas_course_name": "Test Course",
                    "selected_modules": {"173467": "Module 1"},
                    "title": "Test Quiz",
                    "question_count": 0,  # Below minimum
                },
            )
            assert response.status_code == 422

            # Test invalid question_count (too high)
            response = await ac.post(
                "/api/v1/quiz/",
                json={
                    "canvas_course_id": 12345,
                    "canvas_course_name": "Test Course",
                    "selected_modules": {"173467": "Module 1"},
                    "title": "Test Quiz",
                    "question_count": 201,  # Above maximum
                },
            )
            assert response.status_code == 422

            # Test invalid temperature (too low)
            response = await ac.post(
                "/api/v1/quiz/",
                json={
                    "canvas_course_id": 12345,
                    "canvas_course_name": "Test Course",
                    "selected_modules": {"173467": "Module 1"},
                    "title": "Test Quiz",
                    "llm_temperature": -0.1,  # Below minimum
                },
            )
            assert response.status_code == 422

            # Test invalid temperature (too high)
            response = await ac.post(
                "/api/v1/quiz/",
                json={
                    "canvas_course_id": 12345,
                    "canvas_course_name": "Test Course",
                    "selected_modules": {"173467": "Module 1"},
                    "title": "Test Quiz",
                    "llm_temperature": 2.1,  # Above maximum
                },
            )
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_quiz_success() -> None:
    """Test successful quiz deletion"""
    quiz_id = uuid4()
    user_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock authenticated user
    mock_user = User(id=user_id, canvas_id=12345, name="Test User")

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.delete_quiz", return_value=True):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.delete(f"/api/v1/quiz/{quiz_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Quiz deleted successfully"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_quiz_not_found() -> None:
    """Test deleting a non-existent quiz or unauthorized access"""
    quiz_id = uuid4()
    user_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock authenticated user
    mock_user = User(id=user_id, canvas_id=12345, name="Test User")

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.delete_quiz", return_value=False):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.delete(f"/api/v1/quiz/{quiz_id}")

        assert response.status_code == 404
        error_detail = response.json()
        assert "Quiz not found" in error_detail["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_quiz_server_error() -> None:
    """Test quiz deletion with server error"""
    quiz_id = uuid4()
    user_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock authenticated user
    mock_user = User(id=user_id, canvas_id=12345, name="Test User")

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch("app.crud.delete_quiz", side_effect=Exception("Database error")):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.delete(f"/api/v1/quiz/{quiz_id}")

        assert response.status_code == 500
        error_detail = response.json()
        assert "Failed to delete quiz" in error_detail["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_quiz_requires_authentication() -> None:
    """Test that DELETE quiz endpoint requires authentication"""
    quiz_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.delete(f"/api/v1/quiz/{quiz_id}")
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_delete_quiz_with_invalid_token() -> None:
    """Test DELETE quiz with invalid token returns 403"""
    quiz_id = uuid4()
    headers = {"Authorization": "Bearer invalid_token"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.delete(f"/api/v1/quiz/{quiz_id}", headers=headers)
        assert response.status_code == 403
        assert "Could not validate credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_quiz_invalid_uuid() -> None:
    """Test DELETE quiz with invalid UUID format"""
    user_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock authenticated user
    mock_user = User(id=user_id, canvas_id=12345, name="Test User")

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # Invalid UUID format
            response = await ac.delete("/api/v1/quiz/invalid-uuid")

        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_quiz_ownership_verification() -> None:
    """Test that quiz deletion verifies ownership properly"""
    quiz_id = uuid4()
    user_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock authenticated user
    mock_user = User(id=user_id, canvas_id=12345, name="Test User")

    # Mock session
    mock_session = MagicMock()

    # Override dependencies
    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return mock_session

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        # Mock delete_quiz function being called with correct parameters
        with patch("app.crud.delete_quiz") as mock_delete:
            mock_delete.return_value = True

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.delete(f"/api/v1/quiz/{quiz_id}")

            # Verify that delete_quiz was called with the correct parameters
            mock_delete.assert_called_once_with(mock_session, quiz_id, user_id)
            assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
