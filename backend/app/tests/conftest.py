import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app import crud
from app.core.db import engine, init_db
from app.main import app
from app.models import Quiz, User, UserCreate


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        quiz_statement = delete(Quiz)
        session.execute(quiz_statement)
        user_statement = delete(User)
        session.execute(user_statement)
        session.commit()


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
