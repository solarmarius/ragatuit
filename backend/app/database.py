import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool
from sqlmodel import Session, select

from app import crud
from app.auth.models import User
from app.auth.schemas import UserCreate
from app.config import settings
from app.logging_config import get_logger

logger = get_logger("database")


# Determine pool class based on environment
def get_pool_class() -> type:
    """Get appropriate pool class for environment."""
    if settings.ENVIRONMENT == "test":  # type: ignore[comparison-overlap]
        # Use NullPool for tests to avoid connection issues
        return NullPool
    return QueuePool


# Configure connection pool for production
engine_args = {
    "poolclass": get_pool_class(),
    "echo": settings.ENVIRONMENT == "local",  # SQL logging in dev
    # Handle timezone issues with PostgreSQL
    "connect_args": {"options": "-c timezone=UTC"},
}

if settings.ENVIRONMENT != "test" and settings.USE_OPTIMIZED_DB_POOL:  # type: ignore[comparison-overlap]
    engine_args.update(
        {
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
            "pool_recycle": settings.DATABASE_POOL_RECYCLE,
            "pool_pre_ping": True,
        }
    )

# Create engine with optimized settings
engine: Engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), **engine_args)


# Add connection pool logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection: Any, _connection_record: Any) -> None:
    """Log new connection creation."""
    logger.info("database_connection_created", connection_id=id(dbapi_connection))


@event.listens_for(engine, "checkout")
def receive_checkout(
    dbapi_connection: Any, _connection_record: Any, _connection_proxy: Any
) -> None:
    """Log connection checkout from pool."""
    pool = engine.pool
    logger.debug(
        "database_connection_checkout",
        connection_id=id(dbapi_connection),
        pool_size=getattr(pool, "size", lambda: 0)(),
        checked_out=getattr(pool, "checkedout", lambda: 0)(),
    )


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection: Any, _connection_record: Any) -> None:
    """Log connection return to pool."""
    logger.debug("database_connection_checkin", connection_id=id(dbapi_connection))


# Create async engine for async operations
async_engine_args: dict[str, Any] = {
    "echo": False,  # Avoid duplicate logging
    # Handle timezone issues with PostgreSQL
    "connect_args": {
        "server_settings": {
            "timezone": "UTC",
        }
    },
}

# Only add pool settings for non-test environments
if settings.ENVIRONMENT != "test" and settings.USE_OPTIMIZED_DB_POOL:  # type: ignore[comparison-overlap]
    async_engine_args.update(
        {
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
            "pool_recycle": settings.DATABASE_POOL_RECYCLE,
            "pool_pre_ping": True,
        }
    )

async_engine: AsyncEngine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI).replace(
        "postgresql://", "postgresql+asyncpg://"
    ),
    **async_engine_args,
)

# Note: Event listeners removed since all datetime columns are now timezone-aware
# All datetime values should be timezone-aware in the application layer


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Ensures proper session lifecycle and error handling.

    Yields:
        Session: SQLModel session for database operations

    Example:
        with get_session() as session:
            user = session.get(User, user_id)
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.

    For use in async functions and background tasks.

    Yields:
        AsyncSession: Async SQLAlchemy session

    Example:
        async with get_async_session() as session:
            result = await session.execute(select(User))
    """
    async with AsyncSession(async_engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def transaction(
    isolation_level: str | None = None, retries: int = 3
) -> AsyncGenerator[AsyncSession, None]:
    """
    Async transaction context manager with proper isolation and retry logic.

    Provides atomic transaction boundaries for background tasks and operations
    that require consistency guarantees.

    Args:
        isolation_level: Transaction isolation level ("READ COMMITTED",
                        "REPEATABLE READ", "SERIALIZABLE")
        retries: Number of retry attempts for retryable errors (deadlocks, etc.)

    Yields:
        AsyncSession: Async SQLAlchemy session with transaction context

    Example:
        async with transaction(isolation_level="REPEATABLE READ") as session:
            quiz = await session.get(Quiz, quiz_id, with_for_update=True)
            quiz.status = "processing"
            # All changes committed together or rolled back on error
    """
    attempt = 0
    last_exception = None

    while attempt <= retries:
        async with AsyncSession(async_engine) as session:
            try:
                # Begin transaction
                await session.begin()

                # Set isolation level if specified
                if isolation_level:
                    await session.execute(
                        text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
                    )

                logger.debug(
                    "transaction_started",
                    isolation_level=isolation_level,
                    attempt=attempt,
                )

                yield session

                # Commit transaction
                await session.commit()
                logger.debug("transaction_committed", attempt=attempt)
                return

            except Exception as e:
                await session.rollback()
                last_exception = e

                logger.error(
                    "transaction_failed", error=str(e), attempt=attempt, exc_info=True
                )

                # Check if error is retryable
                error_str = str(e).lower()
                retryable_errors = [
                    "deadlock",
                    "serialization failure",
                    "concurrent update",
                    "lock timeout",
                    "could not serialize",
                ]

                is_retryable = any(err in error_str for err in retryable_errors)

                if attempt < retries and is_retryable:
                    attempt += 1
                    logger.info("transaction_retry", attempt=attempt, error=str(e))
                    # Small delay before retry
                    await asyncio.sleep(0.1 * attempt)
                    continue

                # Re-raise if not retryable or max attempts reached
                raise

    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError("Transaction failed after all retry attempts")


async def execute_in_transaction(
    task_func: Any,
    *args: Any,
    isolation_level: str | None = None,
    retries: int = 3,
    **kwargs: Any,
) -> Any:
    """
    Execute a background task function within a transaction context.

    Simple wrapper for background tasks that need transactional guarantees.
    Provides the session as the first argument to the task function.

    Args:
        task_func: Async function to execute (receives session as first arg)
        *args: Additional positional arguments to pass to task_func
        isolation_level: Transaction isolation level
        retries: Number of retry attempts
        **kwargs: Additional keyword arguments to pass to task_func

    Returns:
        Result from task_func execution

    Example:
        async def update_quiz_task(session, quiz_id, status):
            quiz = await session.get(Quiz, quiz_id, with_for_update=True)
            quiz.status = status

        await execute_in_transaction(
            update_quiz_task,
            quiz_id,
            "completed",
            isolation_level="REPEATABLE READ"
        )
    """
    async with transaction(isolation_level=isolation_level, retries=retries) as session:
        return await task_func(session, *args, **kwargs)


# Health check function
def check_database_health() -> dict[str, Any]:
    """
    Check database connection pool health.

    Returns:
        dict: Health metrics including pool stats
    """
    try:
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        pool = engine.pool
        pool_size = getattr(pool, "size", lambda: 0)()
        checked_out = getattr(pool, "checkedout", lambda: 0)()
        overflow = getattr(pool, "overflow", lambda: 0)()
        return {
            "status": "healthy",
            "pool_size": pool_size,
            "checked_out_connections": checked_out,
            "overflow": overflow,
            "total": pool_size + overflow,
            "available": pool_size - checked_out,
        }
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


def init_db(session: Session) -> None:
    """
    Initialize database with any required initial data.

    This function can be used to create default users, settings,
    or other initial data that should exist when the app starts.

    Args:
        session: Database session to use for operations
    """
    user = session.exec(select(User).where(User.canvas_id == 1111)).first()
    if not user:
        user_in = UserCreate(
            canvas_id=1111,
            name="testuser",
            access_token="test_token",
            refresh_token="refresh_test_token",
        )
        user = crud.create_user(session=session, user_create=user_in)
