import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app  # Assuming your FastAPI app instance is named 'app'
from app.models import Quiz, Question, User, Message
from app.services.canvas_service import CanvasService
from app.api.deps import get_current_user, get_db


# Mark all tests in this module as asyncio if they interact with async parts of the app
# However, TestClient calls are synchronous. We'll use pytest.mark.asyncio for specific helper functions if needed.

@pytest.fixture
def db_session_mock(mocker):
    mock = MagicMock(spec=Session)
    # Mock session.exec().first() and session.exec().all()
    mock.exec.return_value.first.return_value = None # Default to not found
    mock.exec.return_value.all.return_value = []    # Default to empty list
    mock.get.return_value = None # Default for session.get
    return mock

@pytest.fixture
def current_user_mock():
    user = User(
        id=uuid.uuid4(),
        canvas_id=12345,
        name="Test User",
        access_token="dummy_access_token_encrypted", # Store as if encrypted
        refresh_token="dummy_refresh_token_encrypted", # Store as if encrypted
        onboarding_completed=True,
    )
    return user

@pytest.fixture
def client(db_session_mock, current_user_mock, mocker):
    # Mock get_db dependency to use our session mock
    app.dependency_overrides[get_db] = lambda: db_session_mock
    # Mock get_current_user to return our test user
    app.dependency_overrides[get_current_user] = lambda: current_user_mock

    # Mock token_encryption for tests if current_user_mock tokens are plain
    # If they are stored "encrypted", no need to mock decryption unless get_current_user does it.
    # Let's assume get_current_user provides a User object ready for use.

    # Also mock CanvasToken dependency if it's complex, or ensure it can run with dummy data
    mocker.patch("app.api.deps.get_canvas_user_token", return_value="mock_canvas_token_for_deps")


    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {} # Clear overrides after test

# --- Test Data Setup ---

@pytest.fixture
def test_quiz(current_user_mock):
    quiz_id = uuid.uuid4()
    return Quiz(
        id=quiz_id,
        owner_id=current_user_mock.id,
        canvas_course_id=789,
        canvas_course_name="Test Course",
        selected_modules='{"1":"Module 1"}',
        title="Test Quiz for Export",
        question_count=5,
        content_extraction_status="completed",
        llm_generation_status="completed",
        canvas_export_status=None, # Not yet exported
        canvas_quiz_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

@pytest.fixture
def approved_question(test_quiz):
    return Question(
        id=uuid.uuid4(),
        quiz_id=test_quiz.id,
        question_text="What is love?",
        option_a="Baby don't hurt me",
        option_b="No more",
        option_c="A chemical reaction",
        option_d="A fruit",
        correct_answer="A",
        is_approved=True,
        approved_at=datetime.now(timezone.utc)
    )

# --- Mock CanvasService ---
@pytest.fixture
def mock_canvas_service(mocker):
    service_mock = AsyncMock(spec=CanvasService)
    service_mock.create_canvas_quiz.return_value = {
        "id": "canvas_quiz_mock_id",
        "assignment_id": "canvas_assignment_mock_id",
        "title": "Mocked Canvas Quiz"
    }
    service_mock.add_question_to_canvas_quiz.return_value = {
        "id": "canvas_item_mock_id"
    }
    # Patch the CanvasService where it's instantiated in the route
    # This depends on how it's imported/used. If it's `from app.services import CanvasService`
    # and then `canvas_service = CanvasService(...)`, then patch 'app.api.routes.quiz.CanvasService'
    return mocker.patch("app.api.routes.quiz.CanvasService", return_value=service_mock)


# --- Tests ---

def test_export_quiz_success(
    client: TestClient,
    db_session_mock: MagicMock,
    test_quiz: Quiz,
    approved_question: Question,
    mock_canvas_service: AsyncMock, # Fixture for mocked CanvasService
    current_user_mock: User,
    mocker,
):
    # Arrange
    # Setup db_session_mock to return the test_quiz when select().where().with_for_update().first() is called
    # And when get_approved_questions_by_quiz_id is called
    # And when session.get is called in background task

    # Mock for the initial SELECT FOR UPDATE
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    # Mock for get_approved_questions_by_quiz_id (assuming it uses session.exec().all())
    # This function is imported from crud.py, so we need to patch it there or ensure session_mock handles it.
    # For simplicity, let's assume it's called with session and quiz_id
    mocker.patch("app.api.routes.quiz.get_approved_questions_by_quiz_id", return_value=[approved_question])

    # Mock session.get for the background task's re-fetch of the quiz
    db_session_mock.get.return_value = test_quiz

    # Mock BackgroundTasks add_task to run the task immediately for testing
    # This is a common pattern for testing background tasks.
    # The actual background task runs async, so we need to handle that.

    # For this test, we'll focus on the endpoint logic up to scheduling the task.
    # Testing the background task itself is more complex and might need separate setup.
    # Let's assume add_task is called correctly.
    mock_background_tasks = MagicMock()

    # Act
    # Need to patch BackgroundTasks where it's used in the endpoint
    with patch("app.api.routes.quiz.BackgroundTasks", return_value=mock_background_tasks) as mock_bg_tasks_class:
        response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Quiz export to Canvas has been initiated."

    # Verify quiz status was updated to "processing"
    db_session_mock.add.assert_called_with(test_quiz) # test_quiz object should be modified
    assert test_quiz.canvas_export_status == "processing"
    db_session_mock.commit.assert_called()
    db_session_mock.refresh.assert_called_with(test_quiz)

    # Verify background task was scheduled with correct parameters
    mock_bg_tasks_class.return_value.add_task.assert_called_once()
    args, kwargs = mock_bg_tasks_class.return_value.add_task.call_args
    assert kwargs.get("quiz_id") == test_quiz.id
    assert "canvas_token" in kwargs # Check that token is passed
    assert kwargs.get("user_id") == current_user_mock.id


def test_export_quiz_not_found(client: TestClient, db_session_mock: MagicMock):
    # Arrange
    non_existent_quiz_id = uuid.uuid4()
    # db_session_mock.exec().first() already defaults to None

    # Act
    response = client.post(f"/api/v1/quiz/{non_existent_quiz_id}/export")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Quiz not found"

def test_export_quiz_not_owner(
    client: TestClient,
    db_session_mock: MagicMock,
    test_quiz: Quiz,
    current_user_mock: User # Fixture for the logged-in user
):
    # Arrange
    # Modify test_quiz to be owned by someone else
    test_quiz.owner_id = uuid.uuid4() # Different owner

    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    # Act
    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")

    # Assert
    assert response.status_code == 404 # Or 403, depending on desired behavior. Route uses 404.
    assert "Quiz not found (access denied)" in response.json()["detail"]


def test_export_quiz_content_not_ready(client: TestClient, db_session_mock: MagicMock, test_quiz: Quiz):
    test_quiz.content_extraction_status = "pending"
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 400
    assert "Content extraction must be completed" in response.json()["detail"]

def test_export_quiz_llm_not_ready(client: TestClient, db_session_mock: MagicMock, test_quiz: Quiz):
    test_quiz.llm_generation_status = "processing"
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 400
    assert "Question generation must be completed" in response.json()["detail"]

def test_export_quiz_already_processing(client: TestClient, db_session_mock: MagicMock, test_quiz: Quiz):
    test_quiz.canvas_export_status = "processing"
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 409
    assert "Quiz export is already in progress" in response.json()["detail"]

def test_export_quiz_already_exported(client: TestClient, db_session_mock: MagicMock, test_quiz: Quiz):
    test_quiz.canvas_export_status = "success"
    test_quiz.canvas_quiz_id = "existing_canvas_id"
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 409
    assert "Quiz already exported to Canvas with ID: existing_canvas_id" in response.json()["detail"]

def test_export_quiz_no_approved_questions(
    client: TestClient,
    db_session_mock: MagicMock,
    test_quiz: Quiz,
    mocker
):
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    mocker.patch("app.api.routes.quiz.get_approved_questions_by_quiz_id", return_value=[]) # No questions

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 400
    assert "No approved questions to export" in response.json()["detail"]


# --- Test for the background task itself ---
# This is more involved. We'd need to:
# 1. Import the background task function: `from app.api.routes.quiz import run_canvas_export_task`
# 2. Call it directly with `await`
# 3. Mock `Session(engine)` or provide a real test DB session.
# 4. Mock `CanvasService` calls within the task.
# 5. Verify database updates made by the task.

@pytest.mark.asyncio # Mark this test as async
async def test_run_canvas_export_task_success(
    db_session_mock: MagicMock, # Use the same session mock for consistency
    test_quiz: Quiz,
    approved_question: Question,
    current_user_mock: User,
    mock_canvas_service: AsyncMock, # Patched CanvasService instance
    mocker
):
    from app.api.routes.quiz import run_canvas_export_task

    # Arrange: Ensure quiz is in 'processing' state before task runs
    test_quiz.canvas_export_status = "processing"

    # Mock database interactions within the task
    # session.exec().first() for fetching quiz
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    # session.get() for fetching quiz (alternative way it might be fetched)
    db_session_mock.get.return_value = test_quiz # Ensure session.get also returns the quiz

    # get_approved_questions_by_quiz_id
    mocker.patch("app.api.routes.quiz.get_approved_questions_by_quiz_id", return_value=[approved_question])

    # Mock the context manager `with Session(engine) as session:`
    # This ensures our db_session_mock is used by the task.
    mock_engine = MagicMock() # Mock the engine object
    mocker.patch("app.api.routes.quiz.engine", mock_engine)

    # The Session context manager in the task: `with Session(engine) as session:`
    # We want this to yield our db_session_mock.
    @contextlib.contextmanager
    def mock_session_context_manager(*args, **kwargs):
        yield db_session_mock

    mocker.patch("app.api.routes.quiz.Session", side_effect=mock_session_context_manager)

    # Act
    await run_canvas_export_task(
        quiz_id=test_quiz.id,
        canvas_token="test_canvas_token_for_task",
        user_id=current_user_mock.id
    )

    # Assert CanvasService calls
    mock_canvas_service.create_canvas_quiz.assert_called_once()
    # Example: check some args of create_canvas_quiz
    create_args, create_kwargs = mock_canvas_service.create_canvas_quiz.call_args
    assert create_kwargs['course_id'] == test_quiz.canvas_course_id
    assert create_kwargs['quiz_title'] == test_quiz.title
    # Check that points_possible is calculated (1 question * 10 points)
    assert create_kwargs['quiz_settings']['points_possible'] == 10


    mock_canvas_service.add_question_to_canvas_quiz.assert_called_once()
    add_q_args, add_q_kwargs = mock_canvas_service.add_question_to_canvas_quiz.call_args
    assert add_q_kwargs['course_id'] == test_quiz.canvas_course_id
    assert add_q_kwargs['canvas_assignment_id'] == "canvas_assignment_mock_id" # From mock create_canvas_quiz
    assert "<p>What is love?</p>" in add_q_kwargs['question_data']['item_body']


    # Assert database updates
    db_session_mock.add.assert_called_with(test_quiz)
    assert test_quiz.canvas_export_status == "success"
    assert test_quiz.canvas_quiz_id == "canvas_assignment_mock_id"
    assert test_quiz.exported_to_canvas_at is not None
    db_session_mock.commit.assert_called()

@pytest.mark.asyncio
async def test_run_canvas_export_task_canvas_creation_fails(
    db_session_mock: MagicMock,
    test_quiz: Quiz,
    approved_question: Question,
    current_user_mock: User,
    mock_canvas_service: AsyncMock,
    mocker
):
    from app.api.routes.quiz import run_canvas_export_task
    import contextlib # For mocking context manager

    test_quiz.canvas_export_status = "processing"

    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result
    db_session_mock.get.return_value = test_quiz

    mocker.patch("app.api.routes.quiz.get_approved_questions_by_quiz_id", return_value=[approved_question])

    mock_engine = MagicMock()
    mocker.patch("app.api.routes.quiz.engine", mock_engine)
    @contextlib.contextmanager
    def mock_session_context_manager(*args, **kwargs):
        yield db_session_mock
    mocker.patch("app.api.routes.quiz.Session", side_effect=mock_session_context_manager)

    # Simulate CanvasService create_canvas_quiz failure
    mock_canvas_service.create_canvas_quiz.side_effect = HTTPException(status_code=500, detail="Canvas down")

    await run_canvas_export_task(
        quiz_id=test_quiz.id,
        canvas_token="test_token",
        user_id=current_user_mock.id
    )

    db_session_mock.add.assert_called_with(test_quiz)
    assert test_quiz.canvas_export_status == "failed"
    mock_canvas_service.add_question_to_canvas_quiz.assert_not_called() # Should not be called if creation fails
    db_session_mock.commit.assert_called()

# Need to import contextlib for the background task test
# This should be at the top of the test file.
# import contextlib
# For the sake of this tool, I will add it via replace if it's missing later.```python
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import contextlib # Added for mocking session context manager

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models import Quiz, Question, User # Removed Message as it's not directly used here for model validation
from app.services.canvas_service import CanvasService
from app.api.deps import get_current_user, get_db # Assuming get_db is your session dependency


@pytest.fixture
def db_session_mock(mocker):
    mock = MagicMock(spec=Session)
    mock_query_result = MagicMock()
    mock_query_result.first.return_value = None
    mock_query_result.all.return_value = []
    mock.exec.return_value = mock_query_result
    mock.get.return_value = None
    return mock

@pytest.fixture
def current_user_mock():
    user_id_val = uuid.uuid4()
    return User(
        id=user_id_val,
        canvas_id=12345,
        name="Test User",
        access_token="dummy_access_token_encrypted",
        refresh_token="dummy_refresh_token_encrypted",
        onboarding_completed=True,
        # quizzes=[] # Initialize relationships if they are accessed
    )

@pytest.fixture
def client(db_session_mock, current_user_mock, mocker):
    app.dependency_overrides[get_db] = lambda: db_session_mock
    app.dependency_overrides[get_current_user] = lambda: current_user_mock

    # Mock the get_canvas_user_token dependency if it's used by the endpoint directly
    # or if CanvasToken itself performs operations that need mocking.
    # For this endpoint, CanvasToken is just a type hint for the token string.
    mocker.patch("app.api.deps.get_canvas_user_token", return_value="mock_canvas_token_from_deps")

    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {}

@pytest.fixture
def test_quiz_id(): # Separate fixture for ID to avoid recreating UUIDs unintentionally
    return uuid.uuid4()

@pytest.fixture
def test_quiz(current_user_mock, test_quiz_id):
    return Quiz(
        id=test_quiz_id,
        owner_id=current_user_mock.id,
        canvas_course_id=789,
        canvas_course_name="Test Course",
        selected_modules='{"1":"Module 1"}',
        title="Test Quiz for Export",
        question_count=5,
        content_extraction_status="completed",
        llm_generation_status="completed",
        canvas_export_status=None,
        canvas_quiz_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        # questions=[] # Initialize relationships
    )

@pytest.fixture
def approved_question(test_quiz): # Depends on test_quiz to get its ID
    return Question(
        id=uuid.uuid4(),
        quiz_id=test_quiz.id, # Use the ID from the test_quiz fixture
        question_text="What is love?",
        option_a="Baby don't hurt me",
        option_b="No more",
        option_c="A chemical reaction",
        option_d="A fruit",
        correct_answer="A",
        is_approved=True,
        approved_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def mock_canvas_service_instance(mocker): # Renamed to avoid conflict if class is also mocked
    service_mock = AsyncMock(spec=CanvasService)
    service_mock.create_canvas_quiz.return_value = {
        "id": "canvas_quiz_mock_id",
        "assignment_id": "canvas_assignment_mock_id",
        "title": "Mocked Canvas Quiz"
    }
    service_mock.add_question_to_canvas_quiz.return_value = {
        "id": "canvas_item_mock_id"
    }
    return service_mock

@pytest.fixture(autouse=True) # Autouse to ensure it's active for all tests in this file
def patch_canvas_service_instantiation(mocker, mock_canvas_service_instance):
    # Patch where CanvasService is instantiated in the route module.
    # This assumes: from app.services import CanvasService
    # and then: canvas_service = CanvasService(...)
    return mocker.patch("app.api.routes.quiz.CanvasService", return_value=mock_canvas_service_instance)


def test_export_quiz_success(
    client: TestClient,
    db_session_mock: MagicMock,
    test_quiz: Quiz, # The quiz instance
    approved_question: Question,
    # mock_canvas_service_instance is active due to autouse fixture
    current_user_mock: User,
    mocker,
):
    # Arrange
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    mocker.patch("app.api.routes.quiz.get_approved_questions_by_quiz_id", return_value=[approved_question])
    db_session_mock.get.return_value = test_quiz # For background task's refetch

    mock_background_tasks_instance = MagicMock()
    mocker.patch("app.api.routes.quiz.BackgroundTasks", return_value=mock_background_tasks_instance)

    # Act
    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Quiz export to Canvas has been initiated."
    assert test_quiz.canvas_export_status == "processing"
    db_session_mock.add.assert_called_with(test_quiz)
    db_session_mock.commit.assert_called()
    db_session_mock.refresh.assert_called_with(test_quiz)

    mock_background_tasks_instance.add_task.assert_called_once()
    args, kwargs = mock_background_tasks_instance.add_task.call_args
    assert kwargs.get("quiz_id") == test_quiz.id
    assert "canvas_token" in kwargs
    assert kwargs.get("user_id") == current_user_mock.id

def test_export_quiz_not_found(client: TestClient, db_session_mock: MagicMock):
    non_existent_quiz_id = uuid.uuid4()
    # db_session_mock.exec().first() already defaults to None
    response = client.post(f"/api/v1/quiz/{non_existent_quiz_id}/export")
    assert response.status_code == 404
    assert response.json()["detail"] == "Quiz not found"

def test_export_quiz_not_owner(
    client: TestClient,
    db_session_mock: MagicMock,
    test_quiz: Quiz,
):
    test_quiz.owner_id = uuid.uuid4() # Different owner
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 404
    assert "Quiz not found (access denied)" in response.json()["detail"]

def test_export_quiz_content_not_ready(client: TestClient, db_session_mock: MagicMock, test_quiz: Quiz):
    test_quiz.content_extraction_status = "pending"
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 400
    assert "Content extraction must be completed" in response.json()["detail"]

def test_export_quiz_llm_not_ready(client: TestClient, db_session_mock: MagicMock, test_quiz: Quiz):
    test_quiz.llm_generation_status = "processing"
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 400
    assert "Question generation must be completed" in response.json()["detail"]

def test_export_quiz_already_processing(client: TestClient, db_session_mock: MagicMock, test_quiz: Quiz):
    test_quiz.canvas_export_status = "processing"
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 409
    assert "Quiz export is already in progress" in response.json()["detail"]

def test_export_quiz_already_exported(client: TestClient, db_session_mock: MagicMock, test_quiz: Quiz):
    test_quiz.canvas_export_status = "success"
    test_quiz.canvas_quiz_id = "existing_canvas_id"
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 409
    assert "Quiz already exported to Canvas with ID: existing_canvas_id" in response.json()["detail"]

def test_export_quiz_no_approved_questions(
    client: TestClient,
    db_session_mock: MagicMock,
    test_quiz: Quiz,
    mocker
):
    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result

    mocker.patch("app.api.routes.quiz.get_approved_questions_by_quiz_id", return_value=[])

    response = client.post(f"/api/v1/quiz/{test_quiz.id}/export")
    assert response.status_code == 400
    assert "No approved questions to export" in response.json()["detail"]


@pytest.mark.asyncio
async def test_run_canvas_export_task_success(
    db_session_mock: MagicMock,
    test_quiz: Quiz, # Use the quiz instance from fixture
    approved_question: Question,
    current_user_mock: User,
    mock_canvas_service_instance: AsyncMock, # The instance of the mocked service
    mocker
):
    from app.api.routes.quiz import run_canvas_export_task

    test_quiz.canvas_export_status = "processing"

    mock_quiz_query_result = MagicMock() # For session.exec().first()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result
    db_session_mock.get.return_value = test_quiz # For session.get()

    mocker.patch("app.api.routes.quiz.get_approved_questions_by_quiz_id", return_value=[approved_question])

    mock_engine = MagicMock()
    mocker.patch("app.api.routes.quiz.engine", mock_engine)

    @contextlib.contextmanager
    def mock_session_cm(*args, **kwargs):
        yield db_session_mock
    mocker.patch("app.api.routes.quiz.Session", side_effect=mock_session_cm) # Patch the class Session

    await run_canvas_export_task(
        quiz_id=test_quiz.id,
        canvas_token="test_canvas_token_for_task",
        user_id=current_user_mock.id
    )

    mock_canvas_service_instance.create_canvas_quiz.assert_called_once()
    create_args, create_kwargs = mock_canvas_service_instance.create_canvas_quiz.call_args
    assert create_kwargs['course_id'] == test_quiz.canvas_course_id
    assert create_kwargs['quiz_title'] == test_quiz.title
    assert create_kwargs['quiz_settings']['points_possible'] == 10

    mock_canvas_service_instance.add_question_to_canvas_quiz.assert_called_once()
    add_q_args, add_q_kwargs = mock_canvas_service_instance.add_question_to_canvas_quiz.call_args
    assert add_q_kwargs['course_id'] == test_quiz.canvas_course_id
    assert add_q_kwargs['canvas_assignment_id'] == "canvas_assignment_mock_id"
    assert "<p>What is love?</p>" in add_q_kwargs['question_data']['item_body']

    assert test_quiz.canvas_export_status == "success"
    assert test_quiz.canvas_quiz_id == "canvas_assignment_mock_id"
    assert test_quiz.exported_to_canvas_at is not None
    db_session_mock.add.assert_called_with(test_quiz)
    db_session_mock.commit.assert_called()

@pytest.mark.asyncio
async def test_run_canvas_export_task_canvas_creation_fails(
    db_session_mock: MagicMock,
    test_quiz: Quiz,
    approved_question: Question,
    current_user_mock: User,
    mock_canvas_service_instance: AsyncMock,
    mocker
):
    from app.api.routes.quiz import run_canvas_export_task

    test_quiz.canvas_export_status = "processing"

    mock_quiz_query_result = MagicMock()
    mock_quiz_query_result.first.return_value = test_quiz
    db_session_mock.exec.return_value = mock_quiz_query_result
    db_session_mock.get.return_value = test_quiz

    mocker.patch("app.api.routes.quiz.get_approved_questions_by_quiz_id", return_value=[approved_question])

    mock_engine = MagicMock()
    mocker.patch("app.api.routes.quiz.engine", mock_engine)
    @contextlib.contextmanager
    def mock_session_cm(*args, **kwargs):
        yield db_session_mock
    mocker.patch("app.api.routes.quiz.Session", side_effect=mock_session_cm)

    mock_canvas_service_instance.create_canvas_quiz.side_effect = HTTPException(status_code=500, detail="Canvas down")

    await run_canvas_export_task(
        quiz_id=test_quiz.id,
        canvas_token="test_token",
        user_id=current_user_mock.id
    )

    assert test_quiz.canvas_export_status == "failed"
    db_session_mock.add.assert_called_with(test_quiz)
    mock_canvas_service_instance.add_question_to_canvas_quiz.assert_not_called()
    db_session_mock.commit.assert_called()

```
