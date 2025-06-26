from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.models import Question, Quiz, User


@pytest.fixture
def mock_user() -> User:
    """Create a mock user for testing."""
    return User(
        id=uuid4(),
        canvas_id=12345,
        name="Test User",
        email="test@example.com",
    )


@pytest.fixture
def mock_quiz(mock_user: User) -> Quiz:
    """Create a mock quiz for testing."""
    return Quiz(
        id=uuid4(),
        owner_id=mock_user.id,
        canvas_course_id=67890,
        canvas_course_name="Test Course",
        selected_modules='{"1": "Module 1"}',
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )


@pytest.fixture
def mock_question(mock_quiz: Quiz) -> Question:
    """Create a mock question for testing."""
    return Question(
        id=uuid4(),
        quiz_id=mock_quiz.id,
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
        is_approved=False,
    )


def test_get_quiz_questions_success(
    mock_user: User, mock_quiz: Quiz, mock_question: Question
) -> None:
    """Test successful retrieval of quiz questions."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with (
            patch("app.api.routes.questions.get_quiz_by_id", return_value=mock_quiz),
            patch(
                "app.api.routes.questions.get_questions_by_quiz_id",
                return_value=[mock_question],
            ),
        ):
            with TestClient(app) as client:
                response = client.get(f"/api/v1/quiz/{mock_quiz.id}/questions")

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["question_text"] == mock_question.question_text
                assert data[0]["option_a"] == mock_question.option_a
                assert data[0]["correct_answer"] == mock_question.correct_answer
                assert data[0]["is_approved"] == mock_question.is_approved
    finally:
        app.dependency_overrides.clear()


def test_get_quiz_questions_quiz_not_found(mock_user: User) -> None:
    """Test quiz questions retrieval when quiz doesn't exist."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        quiz_id = uuid4()
        with patch("app.api.routes.questions.get_quiz_by_id", return_value=None):
            with TestClient(app) as client:
                response = client.get(f"/api/v1/quiz/{quiz_id}/questions")

                assert response.status_code == 404
                assert response.json()["detail"] == "Quiz not found"
    finally:
        app.dependency_overrides.clear()


def test_get_quiz_questions_access_denied(mock_user: User) -> None:
    """Test quiz questions retrieval when user doesn't own the quiz."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        # Create a quiz owned by a different user
        other_user_quiz = Quiz(
            id=uuid4(),
            owner_id=uuid4(),  # Different owner
            canvas_course_id=67890,
            canvas_course_name="Other User's Course",
            selected_modules='{"1": "Module 1"}',
            title="Other User's Quiz",
            question_count=10,
            llm_model="gpt-4o",
            llm_temperature=1,
        )

        with patch(
            "app.api.routes.questions.get_quiz_by_id", return_value=other_user_quiz
        ):
            with TestClient(app) as client:
                response = client.get(f"/api/v1/quiz/{other_user_quiz.id}/questions")

                assert response.status_code == 404
                assert response.json()["detail"] == "Quiz not found"
    finally:
        app.dependency_overrides.clear()


def test_get_question_success(
    mock_user: User, mock_quiz: Quiz, mock_question: Question
) -> None:
    """Test successful retrieval of a specific question."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with (
            patch("app.api.routes.questions.get_quiz_by_id", return_value=mock_quiz),
            patch(
                "app.api.routes.questions.get_question_by_id",
                return_value=mock_question,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/api/v1/quiz/{mock_quiz.id}/questions/{mock_question.id}"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["id"] == str(mock_question.id)
                assert data["question_text"] == mock_question.question_text
                assert data["quiz_id"] == str(mock_quiz.id)
    finally:
        app.dependency_overrides.clear()


def test_get_question_not_found(mock_user: User, mock_quiz: Quiz) -> None:
    """Test question retrieval when question doesn't exist."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        question_id = uuid4()
        with (
            patch("app.api.routes.questions.get_quiz_by_id", return_value=mock_quiz),
            patch("app.api.routes.questions.get_question_by_id", return_value=None),
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/api/v1/quiz/{mock_quiz.id}/questions/{question_id}"
                )

                assert response.status_code == 404
                assert response.json()["detail"] == "Question not found"
    finally:
        app.dependency_overrides.clear()


def test_get_question_quiz_mismatch(
    mock_user: User, mock_quiz: Quiz, mock_question: Question
) -> None:
    """Test question retrieval when question doesn't belong to the specified quiz."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        other_quiz_id = uuid4()
        mock_question.quiz_id = other_quiz_id  # Question belongs to different quiz

        with (
            patch("app.api.routes.questions.get_quiz_by_id", return_value=mock_quiz),
            patch(
                "app.api.routes.questions.get_question_by_id",
                return_value=mock_question,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/api/v1/quiz/{mock_quiz.id}/questions/{mock_question.id}"
                )

                assert response.status_code == 404
                assert response.json()["detail"] == "Question not found"
    finally:
        app.dependency_overrides.clear()


def test_update_question_success(
    mock_user: User, mock_quiz: Quiz, mock_question: Question
) -> None:
    """Test successful question update."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        update_data = {
            "question_text": "Updated question text",
            "option_a": "Updated option A",
            "correct_answer": "B",
        }

        updated_question = Question(**{**mock_question.model_dump(), **update_data})

        with (
            patch("app.api.routes.questions.get_quiz_by_id", return_value=mock_quiz),
            patch(
                "app.api.routes.questions.get_question_by_id",
                return_value=mock_question,
            ),
            patch(
                "app.api.routes.questions.update_question",
                return_value=updated_question,
            ),
        ):
            with TestClient(app) as client:
                response = client.put(
                    f"/api/v1/quiz/{mock_quiz.id}/questions/{mock_question.id}",
                    json=update_data,
                )

                assert response.status_code == 200
                data = response.json()
                assert data["question_text"] == update_data["question_text"]
                assert data["option_a"] == update_data["option_a"]
                assert data["correct_answer"] == update_data["correct_answer"]
    finally:
        app.dependency_overrides.clear()


def test_approve_question_success(
    mock_user: User, mock_quiz: Quiz, mock_question: Question
) -> None:
    """Test successful question approval."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        approved_question = Question(**mock_question.model_dump())
        approved_question.is_approved = True

        with (
            patch("app.api.routes.questions.get_quiz_by_id", return_value=mock_quiz),
            patch(
                "app.api.routes.questions.get_question_by_id",
                return_value=mock_question,
            ),
            patch(
                "app.api.routes.questions.approve_question",
                return_value=approved_question,
            ),
        ):
            with TestClient(app) as client:
                response = client.put(
                    f"/api/v1/quiz/{mock_quiz.id}/questions/{mock_question.id}/approve"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["is_approved"] is True
    finally:
        app.dependency_overrides.clear()


def test_approve_question_not_found(mock_user: User, mock_quiz: Quiz) -> None:
    """Test question approval when question doesn't exist."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        question_id = uuid4()
        with (
            patch("app.api.routes.questions.get_quiz_by_id", return_value=mock_quiz),
            patch("app.api.routes.questions.get_question_by_id", return_value=None),
        ):
            with TestClient(app) as client:
                response = client.put(
                    f"/api/v1/quiz/{mock_quiz.id}/questions/{question_id}/approve"
                )

                assert response.status_code == 404
                assert response.json()["detail"] == "Question not found"
    finally:
        app.dependency_overrides.clear()


def test_delete_question_success(
    mock_user: User, mock_quiz: Quiz, mock_question: Question
) -> None:
    """Test successful question deletion."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with (
            patch("app.api.routes.questions.get_quiz_by_id", return_value=mock_quiz),
            patch("app.api.routes.questions.delete_question", return_value=True),
        ):
            with TestClient(app) as client:
                response = client.delete(
                    f"/api/v1/quiz/{mock_quiz.id}/questions/{mock_question.id}"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Question deleted successfully"
    finally:
        app.dependency_overrides.clear()


def test_delete_question_not_found(mock_user: User, mock_quiz: Quiz) -> None:
    """Test question deletion when question doesn't exist."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        question_id = uuid4()
        with (
            patch("app.api.routes.questions.get_quiz_by_id", return_value=mock_quiz),
            patch("app.api.routes.questions.delete_question", return_value=False),
        ):
            with TestClient(app) as client:
                response = client.delete(
                    f"/api/v1/quiz/{mock_quiz.id}/questions/{question_id}"
                )

                assert response.status_code == 404
                assert response.json()["detail"] == "Question not found"
    finally:
        app.dependency_overrides.clear()


def test_question_routes_require_authentication() -> None:
    """Test that question routes require authentication."""
    quiz_id = uuid4()
    question_id = uuid4()

    with TestClient(app) as client:
        # Test GET questions
        response = client.get(f"/api/v1/quiz/{quiz_id}/questions")
        assert response.status_code == 403

        # Test GET specific question
        response = client.get(f"/api/v1/quiz/{quiz_id}/questions/{question_id}")
        assert response.status_code == 403

        # Test PUT update question
        response = client.put(
            f"/api/v1/quiz/{quiz_id}/questions/{question_id}",
            json={"question_text": "Updated"},
        )
        assert response.status_code == 403

        # Test PUT approve question
        response = client.put(f"/api/v1/quiz/{quiz_id}/questions/{question_id}/approve")
        assert response.status_code == 403

        # Test DELETE question
        response = client.delete(f"/api/v1/quiz/{quiz_id}/questions/{question_id}")
        assert response.status_code == 403


def test_server_error_handling(mock_user: User, mock_quiz: Quiz) -> None:
    """Test server error handling in question routes."""

    def mock_get_current_user() -> User:
        return mock_user

    def mock_get_db() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        with patch(
            "app.api.routes.questions.get_quiz_by_id",
            side_effect=Exception("Database error"),
        ):
            with TestClient(app) as client:
                response = client.get(f"/api/v1/quiz/{mock_quiz.id}/questions")

                assert response.status_code == 500
                assert "Failed to retrieve questions" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
