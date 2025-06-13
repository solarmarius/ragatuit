import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from typing import Generator

from backend.main import app  # Import your FastAPI app
from backend.db import get_session # Original get_session
from backend.config import Settings # To potentially override settings

# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite:///./test_db_for_tests.db" # Or "sqlite:///:memory:" for pure in-memory
# Using a file-based SQLite for tests can be easier to inspect/debug if needed.
# Using :memory: is faster but data vanishes immediately after connection closes.

# Create a test engine
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}) # check_same_thread for SQLite

# Dependency override for get_session
def override_get_session() -> Generator[Session, None, None]:
    """
    Provides a test database session that rolls back transactions after each test.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection)
    try:
        yield db
    finally:
        db.close()
        transaction.rollback() # Rollback to keep test db clean
        connection.close()

# Fixture for the TestClient
@pytest.fixture(scope="module") # module scope for client, session scope for db overrides
def client() -> Generator[TestClient, None, None]:
    """
    Provides a TestClient instance for the FastAPI application.
    Applies the test database session override.
    """
    app.dependency_overrides[get_session] = override_get_session

    # Create tables for the test database module for all tests in a module
    # For session scope, you'd move this into a session-scoped fixture that client depends on
    SQLModel.metadata.create_all(test_engine)

    with TestClient(app) as c:
        yield c

    # Clean up: drop all tables after the module tests are done
    SQLModel.metadata.drop_all(test_engine)
    # If using a file DB and want to remove it after tests:
    # import os
    # if os.path.exists("./test_db_for_tests.db"):
    #    os.remove("./test_db_for_tests.db")


# Fixture for a single test database session (if needed directly in tests)
@pytest.fixture(scope="function") # function scope for individual test isolation
def db_session() -> Generator[Session, None, None]:
    """
    Provides a direct test database session for tests that might need to interact
    with the DB outside of API calls.
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

# Potential settings override fixture (example)
# @pytest.fixture
# def test_settings() -> Settings:
#     # Example: override JWT secret for testing
#     return Settings(JWT_SECRET="test_secret", ALGORITHM="HS256", ACCESS_TOKEN_EXPIRE_MINUTES=5)

# Apply settings override if defined (example)
# def override_get_settings():
#    return Settings(JWT_SECRET="test_secret", ...) # your test settings
# app.dependency_overrides[get_settings_dependency_from_your_app] = override_get_settings
