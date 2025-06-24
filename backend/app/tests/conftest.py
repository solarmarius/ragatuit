import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app import crud
from app.core.config import settings
from app.main import app
from app.models import UserCreate


def create_test_database() -> None:
    """Create the test database if it doesn't exist."""
    # Connect to default postgres database to create test database
    admin_engine = create_engine(
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    )

    test_db_name = f"{settings.POSTGRES_DB}_test"

    try:
        with admin_engine.connect() as conn:
            # Check if test database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": test_db_name},
            )

            if not result.fetchone():
                # Create test database
                conn.execute(text("COMMIT"))  # End any existing transaction
                conn.execute(text(f"CREATE DATABASE {test_db_name}"))
                print(f"Created test database: {test_db_name}")
            else:
                print(f"Test database already exists: {test_db_name}")
    except Exception as e:
        print(f"Warning: Could not create test database: {e}")
        print("Make sure PostgreSQL is running and accessible")
    finally:
        admin_engine.dispose()


# Create test database programmatically
create_test_database()

# Create test engine using separate test database
test_engine = create_engine(
    str(settings.SQLALCHEMY_TEST_DATABASE_URI),
    echo=False,  # Set to True for SQL query debugging
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    """
    Set up test database for the entire test session.

    Creates tables at the start and cleans up at the end.
    This runs automatically for all tests.
    """
    # Create tables at the start of test session
    SQLModel.metadata.create_all(test_engine)

    yield

    # Clean up at the end of test session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Provide a clean database session for each test.

    Uses the isolated test database, not the development database.
    Each test gets a fresh transaction that is rolled back after the test.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def user_id(db: Session) -> uuid.UUID:
    """Create a user and return its ID"""
    user_in = UserCreate(
        canvas_id=12345,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    user = crud.create_user(session=db, user_create=user_in)
    return user.id


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
