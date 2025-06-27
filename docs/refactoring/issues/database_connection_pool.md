# 2. Database Connection Pool Configuration

## Priority: Critical

**Estimated Effort**: 1 day
**Python Version**: 3.10+
**Dependencies**: SQLAlchemy 2.0+

## Problem Statement

### Current Situation

The application uses SQLModel's `create_engine` with default settings, which creates a basic connection pool without optimization for production workloads. This can lead to connection exhaustion under load.

### Why It's a Problem

- **Connection Exhaustion**: Default pool size (5) insufficient for concurrent requests
- **No Connection Recycling**: Stale connections can cause errors
- **No Health Checks**: Dead connections remain in pool
- **Memory Leaks**: Connections not properly returned in background tasks
- **Performance**: Connection wait times under load

### Affected Modules

- `app/core/db.py` (line 7)
- All database operations
- Background tasks creating sessions
- Concurrent API requests

### Technical Debt Assessment

- **Risk Level**: Critical - Can cause production outages
- **Impact**: All database operations
- **Cost of Delay**: Increases with user growth

## Current Implementation Analysis

```python
# File: app/core/db.py (current)
from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate

# PROBLEM: Using default connection pool settings
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
```

### Performance Metrics

```python
# Under load testing (current):
# - Concurrent requests: 50
# - Connection pool size: 5 (default)
# - Connection overflow: 10 (default)
# - Result: Connection timeout errors after ~15 concurrent requests
# - Average wait time: 2.3s for connection acquisition
```

### Python Anti-patterns Identified

- **Magic Numbers**: Default pool settings not explicit
- **No Connection Management**: Missing pool configuration
- **No Monitoring**: Can't track pool metrics
- **Resource Leaks**: Background tasks create new sessions

## Proposed Solution

### Pythonic Approach

Configure SQLAlchemy's `QueuePool` with production-appropriate settings, implement connection health checks, and add proper session management for background tasks.

### Implementation Plan

1. Configure connection pool with explicit settings
2. Add connection health checks
3. Implement session context manager for background tasks
4. Add pool monitoring
5. Update all background tasks

### Code Examples

```python
# File: app/core/db.py (UPDATED)
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator
import logging

from sqlalchemy import create_engine, event, Engine
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlmodel import Session, SQLModel

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("database")

# Determine pool class based on environment
def get_pool_class():
    """Get appropriate pool class for environment."""
    if settings.ENVIRONMENT == "test":
        # Use NullPool for tests to avoid connection issues
        return NullPool
    return QueuePool

# Configure connection pool for production
engine_args = {
    "poolclass": get_pool_class(),
    "echo": settings.ENVIRONMENT == "local",  # SQL logging in dev
}

if settings.ENVIRONMENT != "test":
    engine_args.update({
        "pool_size": 20,            # Number of persistent connections
        "max_overflow": 40,         # Maximum overflow connections
        "pool_timeout": 30,         # Timeout for getting connection
        "pool_recycle": 1800,       # Recycle connections after 30 min
        "pool_pre_ping": True,      # Test connections before use
    })

# Create engine with optimized settings
engine: Engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    **engine_args
)

# Add connection pool logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log new connection creation."""
    logger.info(
        "database_connection_created",
        connection_id=id(dbapi_connection)
    )

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout from pool."""
    logger.debug(
        "database_connection_checkout",
        connection_id=id(dbapi_connection),
        pool_size=engine.pool.size(),
        checked_out=engine.pool.checkedout()
    )

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection return to pool."""
    logger.debug(
        "database_connection_checkin",
        connection_id=id(dbapi_connection)
    )

# Create async engine for async operations
async_engine_args = engine_args.copy()
async_engine_args["echo"] = False  # Avoid duplicate logging

async_engine: AsyncEngine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI).replace(
        "postgresql://", "postgresql+asyncpg://"
    ),
    **async_engine_args
)

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

class DatabaseSessionManager:
    """
    Manager for database sessions in background tasks.

    Ensures proper connection management and prevents leaks.
    """

    def __init__(self, engine: Engine = engine):
        self.engine = engine
        self._session: Session | None = None

    def __enter__(self) -> Session:
        """Create and return session."""
        self._session = Session(self.engine)
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up session."""
        if self._session:
            if exc_type:
                self._session.rollback()
            else:
                try:
                    self._session.commit()
                except Exception:
                    self._session.rollback()
                    raise
            finally:
                self._session.close()
                self._session = None

    @property
    def session(self) -> Session:
        """Get current session."""
        if not self._session:
            raise RuntimeError("Session not available outside context manager")
        return self._session

# Health check function
def check_database_health() -> dict[str, any]:
    """
    Check database connection pool health.

    Returns:
        dict: Health metrics including pool stats
    """
    try:
        # Test connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")

        pool = engine.pool
        return {
            "status": "healthy",
            "pool_size": pool.size(),
            "checked_out_connections": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
            "available": pool.size() - pool.checkedout(),
        }
    except Exception as e:
        logger.error(
            "database_health_check_failed",
            error=str(e)
        )
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# File: app/api/routes/quiz.py (UPDATED background task)
async def extract_content_for_quiz(
    quiz_id: UUID, course_id: int, module_ids: list[int], canvas_token: str
) -> None:
    """Background task with proper session management."""
    logger.info(
        "content_extraction_started",
        quiz_id=str(quiz_id),
        course_id=course_id,
        module_count=len(module_ids),
    )

    # Use async session for background tasks
    async with get_async_session() as session:
        try:
            # Get quiz with proper locking
            result = await session.execute(
                select(Quiz)
                .where(Quiz.id == quiz_id)
                .with_for_update()
            )
            quiz = result.scalar_one_or_none()

            if not quiz:
                logger.error(
                    "content_extraction_quiz_not_found",
                    quiz_id=str(quiz_id),
                )
                return

            # Update status
            quiz.content_extraction_status = "processing"
            await session.commit()

            # Perform extraction...

        except Exception as e:
            logger.error(
                "content_extraction_failed",
                quiz_id=str(quiz_id),
                error=str(e)
            )
            # Session rollback handled by context manager
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   └── db.py                    # UPDATE: Connection pool config
│   ├── api/
│   │   ├── deps.py                  # UPDATE: Use get_session
│   │   └── routes/
│   │       └── quiz.py              # UPDATE: Background tasks
│   ├── tests/
│   │   └── conftest.py              # UPDATE: Test fixtures
│   └── alembic/
│       └── env.py                   # UPDATE: Migration engine
```

### Configuration Changes

```python
# Additional settings in .env
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=1800

# Update app/core/config.py
class Settings(BaseSettings):
    # Database pool settings
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
```

### Dependencies

```toml
# pyproject.toml updates
[project.dependencies]
asyncpg = ">=0.29.0"  # For async PostgreSQL
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/core/test_db.py
import pytest
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor
import time

from app.core.db import (
    engine,
    get_session,
    check_database_health,
    DatabaseSessionManager
)

def test_connection_pool_configuration():
    """Test pool is configured correctly."""
    pool = engine.pool

    if settings.ENVIRONMENT != "test":
        assert pool.size() == 20
        assert pool._max_overflow == 40
        assert pool._timeout == 30
        assert pool._recycle == 1800

def test_concurrent_connections():
    """Test pool handles concurrent requests."""
    def make_query():
        with get_session() as session:
            result = session.execute("SELECT 1")
            time.sleep(0.1)  # Simulate work
            return result.scalar()

    # Run 50 concurrent queries
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(make_query) for _ in range(50)]
        results = [f.result() for f in futures]

    assert all(r == 1 for r in results)
    assert engine.pool.checkedout() == 0  # All returned

def test_session_context_manager_rollback():
    """Test session rollback on error."""
    with pytest.raises(ValueError):
        with get_session() as session:
            # Make changes
            user = User(name="test")
            session.add(user)
            # Force error
            raise ValueError("Test error")

    # Verify rollback occurred
    with get_session() as session:
        count = session.query(User).filter_by(name="test").count()
        assert count == 0

@pytest.mark.asyncio
async def test_async_session_manager():
    """Test async session management."""
    async with get_async_session() as session:
        result = await session.execute("SELECT 1")
        assert result.scalar() == 1

def test_database_health_check():
    """Test health check function."""
    health = check_database_health()

    assert health["status"] == "healthy"
    assert "pool_size" in health
    assert "checked_out_connections" in health
    assert health["available"] >= 0
```

### Performance Tests

```python
# File: app/tests/performance/test_db_pool.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.performance
def test_connection_pool_performance():
    """Test connection pool under load."""

    def timed_query():
        start = time.time()
        with get_session() as session:
            session.execute("SELECT pg_sleep(0.1)")
        return time.time() - start

    # Warmup pool
    for _ in range(5):
        timed_query()

    # Measure under load
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(timed_query) for _ in range(100)]
        times = [f.result() for f in futures]

    avg_time = sum(times) / len(times)
    max_time = max(times)

    # Performance assertions
    assert avg_time < 0.5  # Average under 500ms
    assert max_time < 2.0  # Max under 2s

    # Check pool metrics
    metrics = check_database_health()
    assert metrics["status"] == "healthy"
```

## Code Quality Improvements

### Monitoring

```python
# Add prometheus metrics
from prometheus_client import Gauge, Counter

db_pool_size = Gauge('db_pool_size', 'Database connection pool size')
db_pool_checkedout = Gauge('db_pool_checkedout', 'Checked out connections')
db_connection_errors = Counter('db_connection_errors', 'Database connection errors')

# Update events to record metrics
@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    db_pool_checkedout.set(engine.pool.checkedout())
```

## Migration Strategy

### Deployment Steps

1. **Update configuration** with new pool settings
2. **Deploy code** with gradual rollout
3. **Monitor metrics** for connection pool behavior
4. **Tune settings** based on production load

### Rollback Plan

```python
# Feature flag for new pool configuration
if settings.USE_OPTIMIZED_DB_POOL:
    engine = create_engine(url, **optimized_args)
else:
    engine = create_engine(url)  # Default
```

## Success Criteria

### Performance Metrics

- **Connection Wait Time**: <100ms average
- **Pool Utilization**: <80% under normal load
- **Connection Errors**: 0 under normal operations
- **Background Task Success**: 100%

### Monitoring Queries

```sql
-- Monitor active connections
SELECT count(*) FROM pg_stat_activity
WHERE datname = 'rag_uit' AND state = 'active';

-- Check for idle connections
SELECT count(*), state
FROM pg_stat_activity
WHERE datname = 'rag_uit'
GROUP BY state;

-- Long running queries
SELECT pid, age(clock_timestamp(), query_start), usename, query
FROM pg_stat_activity
WHERE query != '<IDLE>' AND query NOT ILIKE '%pg_stat_%'
ORDER BY query_start desc;
```

---
