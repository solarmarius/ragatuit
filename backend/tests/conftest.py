"""Pytest configuration and fixtures for the test suite."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlmodel import Session

# Import after ensuring test environment
os.environ["ENVIRONMENT"] = "test"

from src.auth.models import User
from src.database import get_session_dep
from src.main import app
from tests.database import (
    create_test_database,
    drop_test_database,
    get_test_async_session,
    get_test_session,
    reset_test_database,
)
from tests.factories import QuestionFactory, QuizFactory, UserFactory
from tests.test_data import (
    DEFAULT_CANVAS_COURSE,
    DEFAULT_CANVAS_MODULES,
    DEFAULT_QUIZ_CONFIG,
    DEFAULT_USER_DATA,
    get_unique_quiz_config,
    get_unique_user_data,
)


def pytest_configure(config: Any) -> None:
    """Configure pytest settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line(
        "markers", "canvas: marks tests that interact with Canvas API"
    )
    config.addinivalue_line(
        "markers", "openai: marks tests that interact with OpenAI API"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    """Set up test database for the entire test session."""
    # Create test database tables
    create_test_database()

    yield

    # Clean up after all tests
    drop_test_database()


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    """Reset database before each test to ensure isolation."""
    reset_test_database()
    yield


@pytest.fixture
def session() -> Generator[Session, None, None]:
    """Provide a database session for testing."""
    with get_test_session() as test_session:
        yield test_session


@pytest_asyncio.fixture
async def async_session():
    """Provide an async database session for testing."""
    async with get_test_async_session() as test_session:
        yield test_session


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    """Provide a test client with database dependency override."""

    def get_test_session_override() -> Generator[Session, None, None]:
        """Override the database session dependency."""
        yield session

    app.dependency_overrides[get_session_dep] = get_test_session_override

    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(async_session) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async test client for testing async endpoints."""

    def get_test_session_override():
        """Override with async session (simplified for async testing)."""
        return async_session

    app.dependency_overrides[get_session_dep] = get_test_session_override

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# User fixtures


@pytest.fixture
def user(session: Session) -> User:
    """Create a test user."""
    UserFactory._meta.sqlalchemy_session = session
    user = UserFactory.build()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def user_with_onboarding(session: Session) -> User:
    """Create a test user who has completed onboarding."""
    UserFactory._meta.sqlalchemy_session = session
    user = UserFactory.build(onboarding_completed=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def expired_user(session: Session) -> User:
    """Create a test user with expired token."""
    UserFactory._meta.sqlalchemy_session = session
    user = UserFactory.build(expired_token=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def admin_user(session: Session) -> User:
    """Create an admin test user."""
    UserFactory._meta.sqlalchemy_session = session
    user = UserFactory.build(canvas_id=1, name="Admin User", onboarding_completed=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# Quiz fixtures


@pytest.fixture
def quiz(session: Session, user: User):
    """Create a test quiz."""
    QuizFactory._meta.sqlalchemy_session = session
    quiz = QuizFactory.build(owner=user)
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    return quiz


@pytest.fixture
def quiz_with_content(session: Session, user: User):
    """Create a quiz with extracted content."""
    QuizFactory._meta.sqlalchemy_session = session
    quiz = QuizFactory.build(owner=user, with_extracted_content=True)
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    return quiz


@pytest.fixture
def completed_quiz(session: Session, user: User):
    """Create a completed quiz exported to Canvas."""
    QuizFactory._meta.sqlalchemy_session = session
    quiz = QuizFactory.build(
        owner=user,
        with_extracted_content=True,
        with_generated_questions=True,
        exported_to_canvas=True,
    )
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    return quiz


# Question fixtures


@pytest.fixture
def question(session: Session, quiz):
    """Create a test question."""
    QuestionFactory._meta.sqlalchemy_session = session
    question = QuestionFactory.build(quiz=quiz)
    session.add(question)
    session.commit()
    session.refresh(question)
    return question


@pytest.fixture
def approved_question(session: Session, quiz):
    """Create an approved test question."""
    QuestionFactory._meta.sqlalchemy_session = session
    question = QuestionFactory.build(quiz=quiz, approved=True)
    session.add(question)
    session.commit()
    session.refresh(question)
    return question


@pytest.fixture
def multiple_questions(session: Session, quiz):
    """Create multiple test questions."""
    QuestionFactory._meta.sqlalchemy_session = session
    questions = []
    for _ in range(5):
        question = QuestionFactory.build(quiz=quiz)
        session.add(question)
        questions.append(question)
    session.commit()
    for question in questions:
        session.refresh(question)
    return questions


# Factory helper functions


def create_user_in_session(session: Session, **kwargs) -> User:
    """Helper to create a user properly in the given session."""
    UserFactory._meta.sqlalchemy_session = session
    # Use centralized defaults with overrides
    user_data = get_unique_user_data()
    user_data.update(kwargs)
    user = UserFactory.build(**user_data)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_quiz_in_session(session: Session, owner: User = None, **kwargs) -> "Quiz":
    """Helper to create a quiz properly in the given session."""
    if owner is None:
        owner = create_user_in_session(session)

    QuizFactory._meta.sqlalchemy_session = session

    # Calculate question_count from selected_modules if present
    if "selected_modules" in kwargs:
        question_count = 0
        for module in kwargs["selected_modules"].values():
            for batch in module.get("question_batches", []):
                question_count += batch.get("count", 0)
        kwargs["question_count"] = question_count

    quiz = QuizFactory.build(owner=owner, **kwargs)
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    return quiz


def create_question_in_session(session: Session, quiz=None, **kwargs):
    """Helper to create a question properly in the given session."""
    if quiz is None:
        quiz = create_quiz_in_session(session)

    QuestionFactory._meta.sqlalchemy_session = session
    question = QuestionFactory.build(quiz=quiz, **kwargs)
    session.add(question)
    session.commit()
    session.refresh(question)
    return question


# Async versions of helper functions for async sessions


async def create_user_in_async_session(session, **kwargs) -> User:
    """Helper to create a user properly in the given async session."""
    import uuid
    from datetime import datetime, timedelta, timezone

    from src.auth.models import User

    # Use centralized defaults with overrides
    user_data = get_unique_user_data()
    user_data.update(
        {
            "id": uuid.uuid4(),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            **kwargs,
        }
    )

    user = User(**user_data)
    session.add(user)
    await session.flush()  # Use flush instead of commit to keep transaction open
    await session.refresh(user)
    return user


async def create_quiz_in_async_session(session, owner: User = None, **kwargs):
    """Helper to create a quiz properly in the given async session."""
    import uuid

    from src.quiz.models import Quiz

    if owner is None:
        owner = await create_user_in_async_session(session)

    # Use centralized defaults with overrides
    quiz_config = get_unique_quiz_config()

    # Handle question_count parameter for backward compatibility by converting to selected_modules
    if "selected_modules" not in kwargs:
        question_count = kwargs.get("question_count", 10)
        # Create default modules with question batches that match the desired question count
        kwargs["selected_modules"] = {
            "module_1": {
                "name": "Introduction",
                "question_batches": [
                    {"question_type": "multiple_choice", "count": question_count}
                ],
            }
        }

    # Calculate question_count from selected_modules
    question_count = 0
    for module in kwargs["selected_modules"].values():
        for batch in module.get("question_batches", []):
            question_count += batch.get("count", 0)

    quiz_data = {
        "id": uuid.uuid4(),
        "owner_id": owner.id,
        **quiz_config,
        "selected_modules": kwargs["selected_modules"],
        "question_count": question_count,
        **kwargs,
    }

    # Remove fields that shouldn't be passed to Quiz constructor
    filtered_kwargs = {
        k: v for k, v in quiz_data.items() if k not in ["question_count"]
    }

    quiz = Quiz(**filtered_kwargs)
    quiz.question_count = question_count  # Set after creation
    session.add(quiz)
    await session.flush()  # Use flush instead of commit to keep transaction open
    await session.refresh(quiz)

    # Store the owner reference for easier access
    quiz.owner = owner
    quiz.owner_id = owner.id

    return quiz


async def create_question_in_async_session(session, quiz=None, **kwargs):
    """Helper to create a question properly in the given async session."""
    import uuid

    from src.question.models import Question, QuestionDifficulty, QuestionType

    if quiz is None:
        quiz = await create_quiz_in_async_session(session)

    # Store owner_id before committing question to avoid relationship loading issues later
    stored_owner_id = quiz.owner_id
    stored_owner = quiz.owner

    # Create question with defaults if not provided
    question_data = {
        "id": uuid.uuid4(),
        "quiz_id": quiz.id,
        "question_type": kwargs.get("question_type", QuestionType.MULTIPLE_CHOICE),
        "question_data": kwargs.get(
            "question_data",
            {
                "question_text": "What is the capital of France?",
                "options": [
                    {"text": "Paris", "is_correct": True},
                    {"text": "London", "is_correct": False},
                    {"text": "Berlin", "is_correct": False},
                    {"text": "Madrid", "is_correct": False},
                ],
                "explanation": "Paris is the capital and largest city of France.",
            },
        ),
        "difficulty": kwargs.get("difficulty", QuestionDifficulty.MEDIUM),
        "is_approved": kwargs.get("is_approved", False),
        **kwargs,
    }

    question = Question(**question_data)
    session.add(question)
    await session.flush()  # Use flush instead of commit to keep transaction open
    await session.refresh(question)

    # Store the quiz reference for easier access in tests (but don't assign non-existent fields)
    # Note: These are dynamic attributes for test convenience, not model fields
    object.__setattr__(question, "quiz", quiz)
    object.__setattr__(question, "quiz_owner_id", stored_owner_id)
    object.__setattr__(question, "owner", stored_owner)

    return question


# Authentication fixtures


@pytest.fixture
def auth_headers(user: User) -> dict[str, str]:
    """Create authentication headers for API requests."""
    # In a real implementation, you'd generate a proper JWT token here
    # For testing, we'll use a mock token that corresponds to the user
    return {
        "Authorization": f"Bearer test_token_{user.canvas_id}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def mock_canvas_api() -> Generator[MagicMock, None, None]:
    """Mock Canvas API responses using centralized data."""
    from tests.common_mocks import mock_canvas_api as _mock_canvas_api

    with _mock_canvas_api(
        courses=[DEFAULT_CANVAS_COURSE],
        modules=DEFAULT_CANVAS_MODULES,
    ) as mock:
        yield mock


@pytest.fixture
def mock_openai_api() -> Generator[MagicMock, None, None]:
    """Mock OpenAI API responses using centralized utilities."""
    from tests.common_mocks import mock_openai_api as _mock_openai_api

    with _mock_openai_api() as mock:
        yield mock


# Canvas integration test data fixtures


@pytest.fixture
def canvas_course_data() -> dict[str, Any]:
    """Canvas course data for testing using centralized data."""
    return DEFAULT_CANVAS_COURSE.copy()


@pytest.fixture
def canvas_modules_data() -> list[dict[str, Any]]:
    """Canvas modules data for testing using centralized data."""
    return [module.copy() for module in DEFAULT_CANVAS_MODULES]


@pytest.fixture
def extracted_content_data() -> dict[str, Any]:
    """Extracted content data for testing."""
    return {
        "modules": [
            {
                "id": "456",
                "name": "Introduction to Programming",
                "content": "Programming is the process of creating a set of instructions that tell a computer how to perform a task...",
                "content_length": 1500,
            },
            {
                "id": "457",
                "name": "Data Structures and Algorithms",
                "content": "Data structures are ways of organizing and storing data so that they can be accessed and worked with efficiently...",
                "content_length": 2000,
            },
        ],
        "total_content_length": 3500,
        "extraction_metadata": {
            "extraction_method": "canvas_api",
            "modules_processed": 2,
            "extraction_time": "2024-01-01T12:00:00Z",
        },
    }


# Manual module test fixtures


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content for testing file uploads."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"


@pytest.fixture
def manual_module_data() -> dict[str, Any]:
    """Sample manual module creation data."""
    return {
        "name": "Test Manual Module",
        "text_content": "This is sample content for testing manual module creation.",
    }


@pytest.fixture
def manual_module_response_data() -> dict[str, Any]:
    """Sample manual module response data."""
    return {
        "module_id": "manual_test123",
        "name": "Test Manual Module",
        "content_preview": "This is sample content for testing...",
        "full_content": "This is sample content for testing manual module creation.",
        "word_count": 10,
        "processing_metadata": {"source": "manual_text", "processing_time": 0.1},
    }


@pytest.fixture
def mixed_quiz_data() -> dict[str, Any]:
    """Quiz data with both Canvas and manual modules."""
    return {
        "canvas_course_id": 123,
        "canvas_course_name": "Mixed Content Course",
        "selected_modules": {
            "456": {
                "name": "Canvas Module",
                "source_type": "canvas",
                "question_batches": [
                    {
                        "question_type": "multiple_choice",
                        "count": 10,
                        "difficulty": "medium",
                    }
                ],
            },
            "manual_abc123": {
                "name": "Manual Module",
                "source_type": "manual",
                "content": "Manual content for mixed quiz",
                "word_count": 6,
                "processing_metadata": {"source": "manual_upload"},
                "content_type": "text",
                "question_batches": [
                    {"question_type": "true_false", "count": 5, "difficulty": "easy"}
                ],
            },
        },
        "title": "Mixed Module Quiz",
    }


@pytest.fixture
def mock_content_processors():
    """Mock content extraction processors."""
    processors = MagicMock()
    processors.__contains__ = MagicMock(return_value=True)
    processors.__getitem__ = MagicMock(return_value=MagicMock())
    return processors


@pytest.fixture
def mock_manual_module_factory():
    """Factory for creating mock manual modules."""

    def create_manual_module(
        module_id: str = "manual_test123",
        name: str = "Test Manual Module",
        content: str = "Test manual content",
        word_count: int = 3,
        source_type: str = "manual",
        content_type: str = "text",
        processing_metadata: dict | None = None,
    ) -> dict[str, Any]:
        if processing_metadata is None:
            processing_metadata = {"source": "manual_text"}

        return {
            "module_id": module_id,
            "name": name,
            "content": content,
            "word_count": word_count,
            "source_type": source_type,
            "content_type": content_type,
            "processing_metadata": processing_metadata,
        }

    return create_manual_module


# Pytest configuration for async tests
pytest_plugins = ("pytest_asyncio",)
