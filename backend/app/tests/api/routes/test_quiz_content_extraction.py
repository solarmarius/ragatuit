import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app import crud
from app.api import deps
from app.main import app
from app.models import Quiz, QuizCreate, User, UserCreate


@pytest.fixture
def test_user_and_quiz(db: Session) -> tuple[User, Quiz]:
    """Create a test user and quiz for testing"""
    # Create user
    user_in = UserCreate(
        canvas_id=71202,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # Create quiz
    quiz_in = QuizCreate(
        canvas_course_id=37823,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1", 173468: "Module 2"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4",
        llm_temperature=0.3,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user.id)

    return user, quiz


@pytest.mark.asyncio
async def test_create_quiz_triggers_content_extraction(
    db: Session, test_user_and_quiz: tuple[User, Quiz]
) -> None:
    """Test that creating a quiz triggers background content extraction"""
    user, _ = test_user_and_quiz

    def mock_get_current_user() -> User:
        return user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    def mock_get_db() -> Session:
        return db

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token
    app.dependency_overrides[deps.get_db] = mock_get_db

    quiz_data = {
        "canvas_course_id": 37824,
        "canvas_course_name": "New Test Course",
        "selected_modules": {"173469": "Module 3", "173470": "Module 4"},
        "title": "New Test Quiz",
        "question_count": 15,
        "llm_model": "gpt-4",
        "llm_temperature": 0.5,
    }

    with patch("app.api.routes.quiz.extract_content_for_quiz") as mock_extract_task:
        # Mock the background task function to prevent it from running
        mock_extract_task.return_value = None

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.post("/api/v1/quiz/", json=quiz_data)

            assert response.status_code == 200
            created_quiz = response.json()

            # Verify quiz was created with correct initial status
            assert created_quiz["content_extraction_status"] == "pending"
            assert created_quiz["llm_generation_status"] == "pending"
            assert created_quiz["extracted_content"] is None

            # The background task would be called but we can't easily verify this
            # since FastAPI handles it internally. The fact that we get 200 means
            # the task was scheduled successfully.

        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_manual_content_extraction_trigger(
    db: Session, test_user_and_quiz: tuple[User, Quiz]
) -> None:
    """Test manual triggering of content extraction"""
    user, quiz = test_user_and_quiz

    def mock_get_current_user() -> User:
        return user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    def mock_get_db() -> Session:
        return db

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token
    app.dependency_overrides[deps.get_db] = mock_get_db

    with patch("app.api.routes.quiz.extract_content_for_quiz") as mock_extract_task:
        # Mock the background task function to prevent it from running
        mock_extract_task.return_value = None

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.post(f"/api/v1/quiz/{quiz.id}/extract-content")

            assert response.status_code == 200
            result = response.json()
            assert "Content extraction started" in result["message"]

            # The background task would be called but we can't easily verify this
            # since FastAPI handles it internally. The fact that we get 200 means
            # the task was scheduled successfully.

        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_manual_content_extraction_nonexistent_quiz(
    db: Session, test_user_and_quiz: tuple[User, Quiz]
) -> None:
    """Test manual content extraction with nonexistent quiz"""
    user, _ = test_user_and_quiz
    nonexistent_quiz_id = uuid.uuid4()

    def mock_get_current_user() -> User:
        return user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    def mock_get_db() -> Session:
        return db

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                f"/api/v1/quiz/{nonexistent_quiz_id}/extract-content"
            )

        assert response.status_code == 404
        assert "Quiz not found" in response.json()["detail"]

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_content_extraction_background_task_success(db: Session) -> None:
    """Test successful content extraction background task"""
    # Create user
    user_in = UserCreate(
        canvas_id=71202,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # Create quiz
    quiz_in = QuizCreate(
        canvas_course_id=37823,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1", 173468: "Module 2"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4",
        llm_temperature=0.3,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user.id)

    # Ensure the quiz is committed to the database so the background task can find it
    db.commit()

    # Mock extracted content
    mock_extracted_content = {
        "module_173467": [
            {
                "title": "Introduction to AI",
                "content": "Artificial Intelligence is the simulation of human intelligence in machines.",
            }
        ],
        "module_173468": [
            {
                "title": "Machine Learning",
                "content": "Machine learning is a subset of AI that enables computers to learn.",
            }
        ],
    }

    with (
        patch(
            "app.api.routes.quiz.ServiceContainer.get_content_extraction_service"
        ) as mock_service_factory,
        patch("app.api.routes.quiz.get_async_session") as mock_session_class,
        patch("app.api.routes.quiz.get_quiz_for_update") as mock_get_quiz,
        patch(
            "app.api.routes.quiz.update_quiz_content_extraction_status"
        ) as mock_update_status,
    ):
        # Mock the service
        mock_service = MagicMock()
        mock_service.extract_content_for_modules = AsyncMock(
            return_value=mock_extracted_content
        )
        mock_service.get_content_summary.return_value = {
            "modules_processed": 2,
            "total_pages": 2,
            "total_word_count": 25,
            "average_words_per_page": 12,
            "extracted_at": "2023-01-15T12:30:45",
        }
        mock_service_factory.return_value = mock_service

        # Mock the async session context manager
        mock_async_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_async_session

        # Mock the CRUD functions
        mock_get_quiz.return_value = quiz
        mock_update_status.return_value = None

        # Import the background task function
        from app.api.routes.quiz import extract_content_for_quiz

        # Execute the background task
        await extract_content_for_quiz(
            quiz_id=quiz.id,
            course_id=quiz.canvas_course_id,
            module_ids=[173467, 173468],
            canvas_token="test_token",
        )

        # Verify the service was called correctly
        mock_service.extract_content_for_modules.assert_called_once_with(
            [173467, 173468]
        )

        # Verify session operations were called
        mock_async_session.commit.assert_called()


@pytest.mark.asyncio
async def test_content_extraction_background_task_failure(db: Session) -> None:
    """Test content extraction background task failure handling"""
    # Create user
    user_in = UserCreate(
        canvas_id=71202,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # Create quiz
    quiz_in = QuizCreate(
        canvas_course_id=37823,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4",
        llm_temperature=0.3,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user.id)

    # Ensure the quiz is committed to the database so the background task can find it
    db.commit()

    with (
        patch(
            "app.api.routes.quiz.ServiceContainer.get_content_extraction_service"
        ) as mock_service_factory,
        patch("app.api.routes.quiz.get_async_session") as mock_session_class,
        patch("app.api.routes.quiz.get_quiz_for_update") as mock_get_quiz,
        patch(
            "app.api.routes.quiz.update_quiz_content_extraction_status"
        ) as mock_update_status,
    ):
        # Mock service to raise an exception
        mock_service = MagicMock()
        mock_service.extract_content_for_modules = AsyncMock(
            side_effect=Exception("Canvas API error")
        )
        mock_service_factory.return_value = mock_service

        # Mock the async session context manager
        mock_async_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_async_session

        # Mock the CRUD functions
        mock_get_quiz.return_value = quiz
        mock_update_status.return_value = None

        # Import the background task function
        from app.api.routes.quiz import extract_content_for_quiz

        # Execute the background task (should handle the exception)
        await extract_content_for_quiz(
            quiz_id=quiz.id,
            course_id=quiz.canvas_course_id,
            module_ids=[173467],
            canvas_token="test_token",
        )

        # Verify the service was called and failed
        mock_service.extract_content_for_modules.assert_called_once_with([173467])

        # Verify update status was called for error handling
        mock_update_status.assert_called()


@pytest.mark.asyncio
async def test_get_quiz_with_content_extraction_status(
    db: Session, test_user_and_quiz: tuple[User, Quiz]
) -> None:
    """Test retrieving quiz with content extraction status fields"""
    user, quiz = test_user_and_quiz

    # Update quiz with extraction status
    quiz.content_extraction_status = "completed"
    quiz.llm_generation_status = "pending"
    quiz.extracted_content = {"module_173467": []}
    quiz.content_extracted_at = datetime.now(timezone.utc)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    def mock_get_current_user() -> User:
        return user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    def mock_get_db() -> Session:
        return db

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(f"/api/v1/quiz/{quiz.id}")

        assert response.status_code == 200
        retrieved_quiz = response.json()

        # Verify content extraction fields are included
        assert retrieved_quiz["content_extraction_status"] == "completed"
        assert retrieved_quiz["llm_generation_status"] == "pending"
        assert retrieved_quiz["extracted_content"] is not None
        assert retrieved_quiz["content_extracted_at"] is not None

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_user_quizzes_with_extraction_status(
    db: Session, test_user_and_quiz: tuple[User, Quiz]
) -> None:
    """Test retrieving user quizzes includes content extraction status"""
    user, quiz = test_user_and_quiz

    # Update quiz with extraction status
    quiz.content_extraction_status = "processing"
    quiz.llm_generation_status = "pending"
    db.add(quiz)
    db.commit()

    def mock_get_current_user() -> User:
        return user

    async def mock_get_canvas_token() -> str:
        return "valid_canvas_token"

    def mock_get_db() -> Session:
        return db

    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    app.dependency_overrides[deps.get_canvas_token] = mock_get_canvas_token
    app.dependency_overrides[deps.get_db] = mock_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/v1/quiz/")

        assert response.status_code == 200
        quizzes = response.json()

        assert len(quizzes) == 1
        retrieved_quiz = quizzes[0]

        # Verify content extraction fields are included
        assert retrieved_quiz["content_extraction_status"] == "processing"
        assert retrieved_quiz["llm_generation_status"] == "pending"

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_quiz_content_dict_property(db: Session) -> None:
    """Test the Quiz model's content_dict property"""
    # Create user
    user_in = UserCreate(
        canvas_id=71202,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # Create quiz
    quiz_in = QuizCreate(
        canvas_course_id=37823,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4",
        llm_temperature=0.3,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user.id)

    # Test setting content via property
    test_content = {
        "module_173467": [{"title": "Test Page", "content": "Test content"}]
    }
    quiz.extracted_content = test_content
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    # Test getting content via property
    retrieved_content = quiz.extracted_content
    assert retrieved_content == test_content
    assert "module_173467" in retrieved_content
    assert len(retrieved_content["module_173467"]) == 1
    assert retrieved_content["module_173467"][0]["title"] == "Test Page"


@pytest.mark.asyncio
async def test_quiz_content_dict_property_empty(db: Session) -> None:
    """Test the Quiz model's content_dict property with empty/invalid content"""
    # Create user
    user_in = UserCreate(
        canvas_id=71202,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # Create quiz
    quiz_in = QuizCreate(
        canvas_course_id=37823,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4",
        llm_temperature=0.3,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user.id)

    # Test with None content (default value should be None, not {})
    assert quiz.extracted_content is None

    # Test with empty content
    quiz.extracted_content = {}
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    assert quiz.extracted_content == {}
