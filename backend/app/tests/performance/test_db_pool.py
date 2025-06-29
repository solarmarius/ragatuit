import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from app.core.db import check_database_health, get_session


@pytest.mark.performance
def test_connection_pool_performance() -> None:
    """Test connection pool under load."""

    def timed_query() -> float:
        start = time.time()
        with get_session() as session:
            session.execute(text("SELECT pg_sleep(0.1)"))
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
