"""Test database configuration and utilities."""

import asyncio
import logging
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, select

from src.auth.models import User
from src.config import settings

logger = logging.getLogger(__name__)

# Test database URL - use a separate test database
TEST_DATABASE_URL = str(settings.SQLALCHEMY_DATABASE_URI).replace(
    settings.POSTGRES_DB, f"{settings.POSTGRES_DB}_test"
)

# Test async database URL
TEST_ASYNC_DATABASE_URL = TEST_DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)


def get_test_engine() -> Engine:
    """Create test database engine with proper configuration."""
    return create_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,  # No connection pooling for tests
        echo=False,  # Disable SQL logging in tests
        connect_args={"options": "-c timezone=UTC"},
    )


def get_test_async_engine() -> AsyncEngine:
    """Create test async database engine."""
    return create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
        connect_args={"server_settings": {"timezone": "UTC"}},
    )


@contextmanager
def get_test_session() -> Generator[Session, None, None]:
    """
    Get a test database session with automatic rollback.

    Creates a transaction that is rolled back after the test completes,
    ensuring test isolation.
    """
    engine = get_test_engine()
    connection = engine.connect()
    transaction = connection.begin()

    try:
        session = Session(bind=connection)
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@asynccontextmanager
async def get_test_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a test async database session with automatic rollback.

    Creates a transaction that is rolled back after the test completes,
    ensuring test isolation.
    """
    engine = get_test_async_engine()
    connection = await engine.connect()
    transaction = await connection.begin()

    try:
        session = AsyncSession(bind=connection)
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


def _ensure_test_database_exists() -> None:
    """Ensure test database exists before creating tables."""
    try:
        # Import here to avoid circular imports
        from scripts.setup.create_test_db import create_test_database as create_db

        create_db()
    except Exception as e:
        logger.warning(f"Could not create test database: {e}")
        # Continue anyway - maybe the database already exists
        pass


def create_test_database() -> None:
    """Create test database tables."""
    # First ensure the test database exists
    _ensure_test_database_exists()

    # Then create tables
    engine = get_test_engine()
    SQLModel.metadata.create_all(engine)


def drop_test_database() -> None:
    """Drop test database tables."""
    engine = get_test_engine()
    SQLModel.metadata.drop_all(engine)


def reset_test_database() -> None:
    """Reset test database by dropping and recreating all tables."""
    drop_test_database()
    create_test_database()


class DatabaseTestMixin:
    """Mixin class providing database testing utilities."""

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a test session for the test class."""
        with get_test_session() as session:
            yield session

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async test session for the test class."""
        async with get_test_async_session() as session:
            yield session

    def create_test_user(self, session: Session, **kwargs: Any) -> User:
        """Create a test user with default values."""
        from tests.factories import UserFactory

        user = UserFactory.build(**kwargs)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


# Event listeners for test database logging
@event.listens_for(get_test_engine(), "connect")
def receive_connect(dbapi_connection: Any, _connection_record: Any) -> None:
    """Disable foreign key checks for SQLite if needed."""
    # This is primarily for SQLite testing, but PostgreSQL handles FK properly
    pass


@event.listens_for(get_test_engine(), "begin")
def receive_begin(conn: Any) -> None:
    """Log transaction begin in tests."""
    pass
