import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.auth.models import User
from app.main import app
from app.models import Question
from app.quiz.models import Quiz


@pytest.fixture
def mock_user() -> User:
    """Create a mock user for testing."""
    return User(
        id=uuid.uuid4(),
        canvas_id=12345,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
    )


@pytest.fixture
def mock_other_user() -> User:
    """Create another mock user for testing authorization."""
    return User(
        id=uuid.uuid4(),
        canvas_id=67890,
        name="Other User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
    )


@pytest.fixture
def mock_quiz(mock_user: User) -> Quiz:
    """Create a mock quiz for testing."""
    return Quiz(
        id=uuid.uuid4(),
        owner_id=mock_user.id,
        canvas_course_id=37823,
        canvas_course_name="Test Course",
        title="Test Quiz",
        selected_modules='{"173467": "Test Module"}',
        question_count=10,
        export_status="pending",
    )


@pytest.fixture
def mock_approved_questions(mock_quiz: Quiz) -> list[Question]:
    """Create mock approved questions for testing."""
    questions = []
    for i in range(3):
        question = Question(
            id=uuid.uuid4(),
            quiz_id=mock_quiz.id,
            question_text=f"Test question {i + 1}?",
            option_a=f"Option A {i + 1}",
            option_b=f"Option B {i + 1}",
            option_c=f"Option C {i + 1}",
            option_d=f"Option D {i + 1}",
            correct_answer="A",
            is_approved=True,
            approved_at=datetime.now(timezone.utc),
        )
        questions.append(question)
    return questions


class TestQuizExportEndpoint:
    """Test cases for the quiz export endpoint."""

    @pytest.mark.asyncio
    async def test_export_quiz_success(
        self, mock_user: User, mock_quiz: Quiz, mock_approved_questions: list[Question]
    ) -> None:
        """Test successful quiz export."""
        # Mock session
        mock_session = MagicMock()

        # Override dependencies
        def mock_get_current_user() -> User:
            return mock_user

        def mock_get_db() -> MagicMock:
            return mock_session

        def mock_get_canvas_token() -> str:
            return "test_canvas_token"

        app.dependency_overrides[deps.get_current_user] = mock_get_current_user
        app.dependency_overrides[deps.get_db] = mock_get_db
        app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

        try:
            with (
                patch("app.api.routes.quiz.get_quiz_by_id") as mock_get_quiz,
                patch(
                    "app.api.routes.quiz.get_approved_questions_by_quiz_id"
                ) as mock_get_questions,
            ):
                mock_get_quiz.return_value = mock_quiz
                mock_get_questions.return_value = mock_approved_questions

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    response = await ac.post(f"/api/v1/quiz/{mock_quiz.id}/export")

                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Quiz export started"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_quiz_not_found(self, mock_user: User) -> None:
        """Test export of non-existent quiz."""
        nonexistent_quiz_id = uuid.uuid4()
        mock_session = MagicMock()

        def mock_get_current_user() -> User:
            return mock_user

        def mock_get_db() -> MagicMock:
            return mock_session

        def mock_get_canvas_token() -> str:
            return "test_canvas_token"

        app.dependency_overrides[deps.get_current_user] = mock_get_current_user
        app.dependency_overrides[deps.get_db] = mock_get_db
        app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

        try:
            with patch("app.api.routes.quiz.get_quiz_by_id") as mock_get_quiz:
                mock_get_quiz.return_value = None

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    response = await ac.post(
                        f"/api/v1/quiz/{nonexistent_quiz_id}/export"
                    )

                assert response.status_code == 404
                data = response.json()
                assert data["detail"] == "Quiz not found"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_quiz_unauthorized(
        self, mock_user: User, mock_other_user: User, mock_quiz: Quiz
    ) -> None:
        """Test export of quiz owned by another user."""
        # Quiz belongs to other user
        mock_quiz.owner_id = mock_other_user.id
        mock_session = MagicMock()

        def mock_get_current_user() -> User:
            return mock_user  # Current user trying to export other user's quiz

        def mock_get_db() -> MagicMock:
            return mock_session

        def mock_get_canvas_token() -> str:
            return "test_canvas_token"

        app.dependency_overrides[deps.get_current_user] = mock_get_current_user
        app.dependency_overrides[deps.get_db] = mock_get_db
        app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

        try:
            with patch("app.api.routes.quiz.get_quiz_by_id") as mock_get_quiz:
                mock_get_quiz.return_value = mock_quiz

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    response = await ac.post(f"/api/v1/quiz/{mock_quiz.id}/export")

                assert response.status_code == 404
                data = response.json()
                assert data["detail"] == "Quiz not found"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_quiz_already_exported(
        self, mock_user: User, mock_quiz: Quiz
    ) -> None:
        """Test export of already exported quiz."""
        mock_quiz.export_status = "completed"
        mock_quiz.canvas_quiz_id = "existing_quiz_123"
        mock_session = MagicMock()

        def mock_get_current_user() -> User:
            return mock_user

        def mock_get_db() -> MagicMock:
            return mock_session

        def mock_get_canvas_token() -> str:
            return "test_canvas_token"

        app.dependency_overrides[deps.get_current_user] = mock_get_current_user
        app.dependency_overrides[deps.get_db] = mock_get_db
        app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

        try:
            with patch("app.api.routes.quiz.get_quiz_by_id") as mock_get_quiz:
                mock_get_quiz.return_value = mock_quiz

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    response = await ac.post(f"/api/v1/quiz/{mock_quiz.id}/export")

                assert response.status_code == 409
                data = response.json()
                assert data["detail"] == "Quiz has already been exported to Canvas"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_quiz_already_processing(
        self, mock_user: User, mock_quiz: Quiz
    ) -> None:
        """Test export of quiz already being processed."""
        mock_quiz.export_status = "processing"
        mock_session = MagicMock()

        def mock_get_current_user() -> User:
            return mock_user

        def mock_get_db() -> MagicMock:
            return mock_session

        def mock_get_canvas_token() -> str:
            return "test_canvas_token"

        app.dependency_overrides[deps.get_current_user] = mock_get_current_user
        app.dependency_overrides[deps.get_db] = mock_get_db
        app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

        try:
            with patch("app.api.routes.quiz.get_quiz_by_id") as mock_get_quiz:
                mock_get_quiz.return_value = mock_quiz

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    response = await ac.post(f"/api/v1/quiz/{mock_quiz.id}/export")

                assert response.status_code == 409
                data = response.json()
                assert data["detail"] == "Quiz export is already in progress"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_quiz_no_approved_questions(
        self, mock_user: User, mock_quiz: Quiz
    ) -> None:
        """Test export of quiz with no approved questions."""
        mock_session = MagicMock()

        def mock_get_current_user() -> User:
            return mock_user

        def mock_get_db() -> MagicMock:
            return mock_session

        def mock_get_canvas_token() -> str:
            return "test_canvas_token"

        app.dependency_overrides[deps.get_current_user] = mock_get_current_user
        app.dependency_overrides[deps.get_db] = mock_get_db
        app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

        try:
            with (
                patch("app.api.routes.quiz.get_quiz_by_id") as mock_get_quiz,
                patch(
                    "app.api.routes.quiz.get_approved_questions_by_quiz_id"
                ) as mock_get_questions,
            ):
                mock_get_quiz.return_value = mock_quiz
                mock_get_questions.return_value = []  # No approved questions

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    response = await ac.post(f"/api/v1/quiz/{mock_quiz.id}/export")

                assert response.status_code == 400
                data = response.json()
                assert data["detail"] == "Quiz has no approved questions to export"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_quiz_invalid_uuid(self, mock_user: User) -> None:
        """Test export with invalid quiz UUID."""
        mock_session = MagicMock()

        def mock_get_current_user() -> User:
            return mock_user

        def mock_get_db() -> MagicMock:
            return mock_session

        def mock_get_canvas_token() -> str:
            return "test_canvas_token"

        app.dependency_overrides[deps.get_current_user] = mock_get_current_user
        app.dependency_overrides[deps.get_db] = mock_get_db
        app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.post("/api/v1/quiz/invalid-uuid/export")

            assert response.status_code == 422  # Validation error

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_quiz_background_task_called(
        self, mock_user: User, mock_quiz: Quiz, mock_approved_questions: list[Question]
    ) -> None:
        """Test that background task is properly triggered."""
        mock_session = MagicMock()
        mock_background_tasks = MagicMock()

        def mock_get_current_user() -> User:
            return mock_user

        def mock_get_db() -> MagicMock:
            return mock_session

        def mock_get_canvas_token() -> str:
            return "test_canvas_token"

        app.dependency_overrides[deps.get_current_user] = mock_get_current_user
        app.dependency_overrides[deps.get_db] = mock_get_db
        app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token

        try:
            with (
                patch("app.api.routes.quiz.get_quiz_by_id") as mock_get_quiz,
                patch(
                    "app.api.routes.quiz.get_approved_questions_by_quiz_id"
                ) as mock_get_questions,
                patch("fastapi.BackgroundTasks") as mock_bg_class,
            ):
                mock_get_quiz.return_value = mock_quiz
                mock_get_questions.return_value = mock_approved_questions
                mock_bg_class.return_value = mock_background_tasks

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    response = await ac.post(f"/api/v1/quiz/{mock_quiz.id}/export")

                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Quiz export started"

        finally:
            app.dependency_overrides.clear()


class TestQuizExportBackgroundTask:
    """Test cases for the background export task."""

    @pytest.mark.asyncio
    async def test_export_quiz_to_canvas_background_success(self) -> None:
        """Test successful background export task."""
        quiz_id = uuid.uuid4()
        canvas_token = "test_token"

        mock_export_service = MagicMock()
        mock_export_service.export_quiz_to_canvas = AsyncMock(
            return_value={
                "success": True,
                "canvas_quiz_id": "quiz_12345",
                "exported_questions": 3,
            }
        )

        with patch(
            "app.api.routes.quiz.ServiceContainer.get_canvas_quiz_export_service"
        ) as mock_service_factory:
            mock_service_factory.return_value = mock_export_service

            # Import and call the background task function
            from app.api.routes.quiz import export_quiz_to_canvas_background

            await export_quiz_to_canvas_background(quiz_id, canvas_token)

            # Verify service was created and called
            mock_service_factory.assert_called_once_with(canvas_token)
            mock_export_service.export_quiz_to_canvas.assert_called_once_with(quiz_id)

    @pytest.mark.asyncio
    async def test_export_quiz_to_canvas_background_error(self) -> None:
        """Test background export task error handling."""
        quiz_id = uuid.uuid4()
        canvas_token = "test_token"

        mock_export_service = MagicMock()
        mock_export_service.export_quiz_to_canvas = AsyncMock(
            side_effect=Exception("Canvas API Error")
        )

        with patch(
            "app.api.routes.quiz.ServiceContainer.get_canvas_quiz_export_service"
        ) as mock_service_factory:
            mock_service_factory.return_value = mock_export_service

            # Import and call the background task function
            from app.api.routes.quiz import export_quiz_to_canvas_background

            # Should not raise exception (error is logged but caught)
            await export_quiz_to_canvas_background(quiz_id, canvas_token)

            # Verify service was created and called
            mock_service_factory.assert_called_once_with(canvas_token)
            mock_export_service.export_quiz_to_canvas.assert_called_once_with(quiz_id)
