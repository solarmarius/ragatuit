import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from app.auth.models import User
from app.config import settings
from app.database import (
    check_database_health,
    engine,
    get_session,
)


def test_connection_pool_configuration() -> None:
    """Test pool is configured correctly."""
    pool = engine.pool

    if settings.ENVIRONMENT != "test":  # type: ignore[comparison-overlap]
        # Use getattr to avoid mypy errors on Pool attributes
        assert getattr(pool, "size", lambda: 0)() == settings.DATABASE_POOL_SIZE
        assert getattr(pool, "_max_overflow", 0) == settings.DATABASE_MAX_OVERFLOW
        assert getattr(pool, "_timeout", 0) == settings.DATABASE_POOL_TIMEOUT
        assert getattr(pool, "_recycle", 0) == settings.DATABASE_POOL_RECYCLE


def test_concurrent_connections() -> None:
    """Test pool handles concurrent requests."""

    def make_query() -> int:
        with get_session() as session:
            result = session.execute(text("SELECT 1"))
            time.sleep(0.1)  # Simulate work
            scalar_result = result.scalar()
            return int(scalar_result) if scalar_result is not None else 0

    # Run 50 concurrent queries
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(make_query) for _ in range(50)]
        results = [f.result() for f in futures]

    assert all(r == 1 for r in results)
    assert getattr(engine.pool, "checkedout", lambda: 0)() == 0  # All returned


def test_session_context_manager_rollback(db: Session) -> None:
    """Test session rollback on error."""
    # db fixture ensures database is available
    _ = db  # Mark as used for linter
    with pytest.raises(ValueError):
        with get_session() as session:
            # Make changes
            user = User(
                name="test", canvas_id=9999, access_token="abc", refresh_token="def"
            )
            session.add(user)
            # Force error
            raise ValueError("Test error")

    # Verify rollback occurred
    with get_session() as session:
        count = len(session.exec(select(User).where(User.name == "test")).all())
        assert count == 0


def test_database_health_check() -> None:
    """Test health check function."""
    health = check_database_health()

    assert health["status"] == "healthy"
    assert "pool_size" in health
    assert "checked_out_connections" in health
    assert health["available"] >= 0
