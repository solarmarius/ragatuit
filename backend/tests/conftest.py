import pytest
import respx
from app.db.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .mocks import canvas_data

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_db_engine
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    """Create a test client with a test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def canvas_oauth_config():
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "redirect_uri": "https://yourapp.test/auth/canvas/callback",
        "canvas_base_url": "https://uit.instructure.com",
    }


@pytest.fixture
def mock_canvas_oauth_token_response():
    with respx.mock as mock:
        mock.post("https://canvas.example.com/login/oauth2/token").respond(
            200, json=canvas_data.MOCK_CANVAS_TOKEN_RESPONSE
        )
        yield mock


@pytest.fixture
def mock_canvas_user_profile():
    with respx.mock as mock:
        mock.get("https://canvas.example.com/api/v1/users/self/profile").respond(
            200, json=canvas_data.MOCK_CANVAS_USER_PROFILE
        )
        yield mock


@pytest.fixture
def mock_canvas_courses_response():
    with respx.mock as mock:
        mock.get("https://canvas.example.com/api/v1/courses").respond(
            200, json=canvas_data.MOCK_CANVAS_COURSES
        )
        yield mock
