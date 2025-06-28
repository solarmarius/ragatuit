# 12. Circuit Breaker Pattern for External APIs

## Priority: Critical

**Estimated Effort**: 3 days
**Python Version**: 3.10+
**Dependencies**: httpx, asyncio

## Problem Statement

### Current Situation

The application makes numerous calls to external APIs (Canvas, OpenAI) without proper circuit breaker protection. When these services experience issues, our application continues attempting requests, leading to cascading failures and poor user experience.

### Why It's a Problem

- **Cascading Failures**: External API failures bring down our entire system
- **Resource Exhaustion**: Failed requests consume threads and connections
- **Poor User Experience**: Users wait for timeouts instead of fast failures
- **No Service Recovery**: System doesn't detect when services recover
- **Missing Metrics**: No visibility into external service health
- **Retry Storms**: All requests retry simultaneously, overwhelming recovering services

### Affected Modules

- `app/services/content_extraction.py` - Canvas API calls
- `app/services/canvas_quiz_export.py` - Canvas API calls (no retry logic)
- `app/services/mcq_generation.py` - OpenAI API calls
- All external API integrations

### Technical Debt Assessment

- **Risk Level**: Critical - Can cause complete service outages
- **Impact**: All features dependent on external APIs
- **Cost of Delay**: Increases with each incident

## Current Implementation Analysis

```python
# File: app/services/content_extraction.py (current retry logic)
async def _make_request_with_retry(self, url: str, headers: dict):
    """Current implementation has basic retry but no circuit breaker."""
    retries = 0
    while retries <= self.max_retries:
        try:
            async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    retries += 1
                else:
                    response.raise_for_status()

        except httpx.HTTPError as e:
            retries += 1
            if retries > self.max_retries:
                raise
            # PROBLEM: Exponential backoff keeps trying even during outages
            await asyncio.sleep(2 ** retries)

# File: app/services/canvas_quiz_export.py (no retry logic at all!)
async def create_quiz_in_canvas(self, quiz_data: dict) -> dict:
    """PROBLEM: No retry logic or circuit breaker."""
    headers = {
        "Authorization": f"Bearer {self.canvas_token}",
        "Content-Type": "application/json",
    }

    # Direct call without protection
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{self.canvas_base_url}/courses/{self.course_id}/quizzes",
            headers=headers,
            json=quiz_data,
        )
        response.raise_for_status()  # Will fail hard on any error
        return response.json()
```

### Current Problems

```python
# Scenario: Canvas API is down
# Current behavior:
# 1. First request fails after 30s timeout
# 2. Retry with 2s delay
# 3. Second request fails after 30s timeout
# 4. Retry with 4s delay
# 5. Third request fails after 30s timeout
# 6. Total time: ~96 seconds of waiting
# 7. Next request immediately tries again!

# With 100 concurrent requests during outage:
# - 100 threads/connections blocked
# - 9600 seconds of cumulative wait time
# - System appears frozen to users
```

### Python Anti-patterns Identified

- **No Circuit State Management**: Keeps hitting dead services
- **Missing Fast Fail**: Long timeouts instead of quick failures
- **No Bulkhead Pattern**: One service failure affects all
- **Lack of Monitoring**: No metrics on service health
- **Resource Blocking**: Synchronous waits in async code

## Proposed Solution

### Pythonic Approach

Implement a proper circuit breaker pattern with three states (Closed, Open, Half-Open) using Python async primitives, with health monitoring and graceful degradation.

### Design Patterns

- **Circuit Breaker**: Prevent cascading failures
- **Bulkhead**: Isolate failures by service
- **Health Check**: Monitor service availability
- **Graceful Degradation**: Fallback behaviors

### Code Examples

```python
# File: app/core/circuit_breaker.py (NEW)
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, TypeVar, Generic
import asyncio
from dataclasses import dataclass, field
import logging
from collections import deque

from app.core.logging_config import get_logger

logger = get_logger("circuit_breaker")

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 30.0
    recovery_timeout: int = 60
    expected_exception: type[Exception] = Exception
    fallback_function: Optional[Callable] = None
    name: str = "default"

@dataclass
class CircuitBreakerStats:
    """Statistics for monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    calls_rejected: int = 0
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    state_changes: list[tuple[datetime, CircuitState]] = field(default_factory=list)

T = TypeVar('T')

class CircuitBreaker(Generic[T]):
    """
    Async circuit breaker implementation.

    Prevents cascading failures by failing fast when a service is down.
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        self._half_open_attempts = 0

        # Sliding window for error rate calculation
        self._recent_calls = deque(maxlen=100)

        logger.info(
            "circuit_breaker_initialized",
            name=config.name,
            failure_threshold=config.failure_threshold,
            recovery_timeout=config.recovery_timeout
        )

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result or fallback

        Raises:
            CircuitOpenError: When circuit is open and no fallback
        """
        async with self._lock:
            self.stats.total_calls += 1

            # Check circuit state
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    return await self._handle_open_circuit()

            elif self.state == CircuitState.HALF_OPEN:
                # Limit concurrent attempts during recovery
                if self._half_open_attempts >= 1:
                    return await self._handle_open_circuit()
                self._half_open_attempts += 1

        # Execute the function
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            await self._on_success()
            return result

        except asyncio.TimeoutError as e:
            await self._on_failure(e)
            raise CircuitTimeoutError(
                f"Circuit breaker timeout after {self.config.timeout}s"
            ) from e

        except self.config.expected_exception as e:
            await self._on_failure(e)
            raise

        finally:
            if self.state == CircuitState.HALF_OPEN:
                async with self._lock:
                    self._half_open_attempts -= 1

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            self.stats.successful_calls += 1
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            self._recent_calls.append((datetime.now(), True))

            if self.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()

            logger.debug(
                "circuit_breaker_success",
                name=self.config.name,
                state=self.state.value,
                consecutive_successes=self.stats.consecutive_successes
            )

    async def _on_failure(self, error: Exception):
        """Handle failed call."""
        async with self._lock:
            self.stats.failed_calls += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = datetime.now()
            self._recent_calls.append((datetime.now(), False))

            logger.warning(
                "circuit_breaker_failure",
                name=self.config.name,
                state=self.state.value,
                consecutive_failures=self.stats.consecutive_failures,
                error=str(error)
            )

            if self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            elif (self.state == CircuitState.CLOSED and
                  self.stats.consecutive_failures >= self.config.failure_threshold):
                self._transition_to_open()

    def _should_attempt_reset(self) -> bool:
        """Check if we should try to recover."""
        if not self.stats.last_failure_time:
            return True

        time_since_failure = datetime.now() - self.stats.last_failure_time
        return time_since_failure > timedelta(seconds=self.config.recovery_timeout)

    def _transition_to_open(self):
        """Transition to open state."""
        self.state = CircuitState.OPEN
        self.stats.state_changes.append((datetime.now(), CircuitState.OPEN))

        logger.error(
            "circuit_breaker_opened",
            name=self.config.name,
            consecutive_failures=self.stats.consecutive_failures,
            total_failures=self.stats.failed_calls
        )

    def _transition_to_closed(self):
        """Transition to closed state."""
        self.state = CircuitState.CLOSED
        self.stats.state_changes.append((datetime.now(), CircuitState.CLOSED))
        self.stats.consecutive_failures = 0

        logger.info(
            "circuit_breaker_closed",
            name=self.config.name,
            recovery_successes=self.stats.consecutive_successes
        )

    def _transition_to_half_open(self):
        """Transition to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.stats.state_changes.append((datetime.now(), CircuitState.HALF_OPEN))
        self.stats.consecutive_successes = 0
        self.stats.consecutive_failures = 0

        logger.info(
            "circuit_breaker_half_open",
            name=self.config.name,
            time_since_failure=(datetime.now() - self.stats.last_failure_time).seconds
        )

    async def _handle_open_circuit(self):
        """Handle request when circuit is open."""
        self.stats.calls_rejected += 1

        if self.config.fallback_function:
            logger.info(
                "circuit_breaker_fallback",
                name=self.config.name
            )
            return await self.config.fallback_function()

        raise CircuitOpenError(
            f"Circuit breaker '{self.config.name}' is open. "
            f"Service has been failing since {self.stats.last_failure_time}"
        )

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        error_rate = 0.0
        if self._recent_calls:
            recent_errors = sum(1 for _, success in self._recent_calls if not success)
            error_rate = recent_errors / len(self._recent_calls)

        return {
            "state": self.state.value,
            "total_calls": self.stats.total_calls,
            "successful_calls": self.stats.successful_calls,
            "failed_calls": self.stats.failed_calls,
            "calls_rejected": self.stats.calls_rejected,
            "error_rate": error_rate,
            "consecutive_failures": self.stats.consecutive_failures,
            "last_failure_time": self.stats.last_failure_time,
            "uptime_percentage": (
                self.stats.successful_calls / self.stats.total_calls * 100
                if self.stats.total_calls > 0 else 100.0
            )
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check."""
        stats = self.get_stats()
        stats["is_healthy"] = self.state != CircuitState.OPEN
        return stats

class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    pass

class CircuitTimeoutError(Exception):
    """Raised when circuit breaker timeout occurs."""
    pass

# File: app/services/circuit_breakers.py (NEW)
from functools import lru_cache
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from app.core.config import settings

@lru_cache()
def get_canvas_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for Canvas API."""
    return CircuitBreaker(CircuitBreakerConfig(
        name="canvas_api",
        failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        success_threshold=2,
        timeout=settings.CANVAS_API_TIMEOUT,
        recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
        expected_exception=httpx.HTTPError,
        fallback_function=None  # Could return cached data
    ))

@lru_cache()
def get_openai_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for OpenAI API."""
    return CircuitBreaker(CircuitBreakerConfig(
        name="openai_api",
        failure_threshold=3,  # More tolerant for AI services
        success_threshold=1,
        timeout=60.0,  # Longer timeout for AI
        recovery_timeout=30,  # Faster recovery attempts
        expected_exception=Exception,
        fallback_function=None
    ))

# File: app/services/content_extraction.py (UPDATED)
from app.services.circuit_breakers import get_canvas_circuit_breaker

class ContentExtractionService:
    def __init__(self, canvas_token: str, course_id: int):
        self.canvas_token = canvas_token
        self.course_id = course_id
        self.canvas_base_url = str(settings.CANVAS_BASE_URL)
        self.circuit_breaker = get_canvas_circuit_breaker()

    async def _make_request_with_circuit_breaker(
        self,
        url: str,
        headers: dict,
        method: str = "GET",
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with circuit breaker protection."""

        async def _request():
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    return await client.get(url, headers=headers, **kwargs)
                elif method == "POST":
                    return await client.post(url, headers=headers, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")

        try:
            # Circuit breaker handles retries and failures
            response = await self.circuit_breaker.call(_request)

            if response.status_code == 429:  # Rate limited
                # Handle rate limiting outside circuit breaker
                retry_after = int(response.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after)
                return await self._make_request_with_circuit_breaker(
                    url, headers, method, **kwargs
                )

            response.raise_for_status()
            return response

        except CircuitOpenError:
            logger.error(
                "canvas_api_circuit_open",
                url=url,
                course_id=self.course_id
            )
            # Could return cached content here
            raise CanvasAPIUnavailableError(
                "Canvas API is currently unavailable. Please try again later."
            )

    async def fetch_module_items(self, module_id: int) -> list[dict]:
        """Fetch module items with circuit breaker protection."""
        url = f"{self.canvas_base_url}/courses/{self.course_id}/modules/{module_id}/items"
        headers = {"Authorization": f"Bearer {self.canvas_token}"}

        try:
            response = await self._make_request_with_circuit_breaker(url, headers)
            return response.json()
        except CircuitOpenError:
            # Return empty list or cached data
            logger.warning(
                "module_items_fallback",
                module_id=module_id,
                reason="circuit_open"
            )
            return []

# File: app/services/canvas_quiz_export.py (UPDATED)
class CanvasQuizExportService:
    def __init__(self, canvas_token: str, course_id: int):
        self.canvas_token = canvas_token
        self.course_id = course_id
        self.canvas_base_url = str(settings.CANVAS_BASE_URL)
        self.circuit_breaker = get_canvas_circuit_breaker()

    async def create_quiz_in_canvas(self, quiz_data: dict) -> dict:
        """Create quiz with circuit breaker protection."""
        url = f"{self.canvas_base_url}/courses/{self.course_id}/quizzes"
        headers = {
            "Authorization": f"Bearer {self.canvas_token}",
            "Content-Type": "application/json",
        }

        try:
            response = await self.circuit_breaker.call(
                self._make_post_request,
                url,
                headers,
                quiz_data
            )
            return response.json()

        except CircuitOpenError:
            raise QuizExportUnavailableError(
                "Cannot export quiz to Canvas at this time. "
                "The Canvas service is temporarily unavailable."
            )

    async def _make_post_request(
        self,
        url: str,
        headers: dict,
        data: dict
    ) -> httpx.Response:
        """Make POST request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response

# File: app/api/routes/health.py (NEW endpoint)
from app.services.circuit_breakers import (
    get_canvas_circuit_breaker,
    get_openai_circuit_breaker
)

@router.get("/circuit-breakers")
async def get_circuit_breaker_status() -> dict[str, Any]:
    """Get status of all circuit breakers."""

    canvas_cb = get_canvas_circuit_breaker()
    openai_cb = get_openai_circuit_breaker()

    return {
        "canvas_api": await canvas_cb.health_check(),
        "openai_api": await openai_cb.health_check(),
    }

# File: app/core/monitoring.py (Add metrics)
from prometheus_client import Counter, Gauge, Histogram

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['service']
)

circuit_breaker_failures = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['service']
)

circuit_breaker_rejections = Counter(
    'circuit_breaker_rejections_total',
    'Total calls rejected by circuit breaker',
    ['service']
)
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   ├── circuit_breaker.py       # NEW: Circuit breaker implementation
│   │   ├── monitoring.py            # UPDATE: Add circuit breaker metrics
│   │   └── config.py                # UPDATE: Add configuration
│   ├── services/
│   │   ├── circuit_breakers.py      # NEW: Service-specific breakers
│   │   ├── content_extraction.py    # UPDATE: Use circuit breaker
│   │   ├── canvas_quiz_export.py    # UPDATE: Add circuit breaker
│   │   └── mcq_generation.py        # UPDATE: Use circuit breaker
│   ├── api/
│   │   └── routes/
│   │       └── health.py            # UPDATE: Add circuit breaker status
│   └── tests/
│       └── core/
│           └── test_circuit_breaker.py # NEW: Circuit breaker tests
```

### Configuration Changes

```python
# app/core/config.py additions
class Settings(BaseSettings):
    # Circuit breaker settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60
    CIRCUIT_BREAKER_SUCCESS_THRESHOLD: int = 2
    ENABLE_CIRCUIT_BREAKERS: bool = True
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/core/test_circuit_breaker.py
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError
)

@pytest.fixture
def circuit_breaker():
    """Create test circuit breaker."""
    config = CircuitBreakerConfig(
        name="test",
        failure_threshold=3,
        success_threshold=2,
        timeout=1.0,
        recovery_timeout=1
    )
    return CircuitBreaker(config)

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(circuit_breaker):
    """Test circuit opens after threshold failures."""

    # Mock function that always fails
    failing_func = AsyncMock(side_effect=Exception("Service error"))

    # First failures should go through
    for i in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.stats.consecutive_failures == 3

    # Next call should fail fast
    with pytest.raises(CircuitOpenError):
        await circuit_breaker.call(failing_func)

    assert circuit_breaker.stats.calls_rejected == 1

@pytest.mark.asyncio
async def test_circuit_breaker_recovery(circuit_breaker):
    """Test circuit breaker recovery process."""

    # Open the circuit
    failing_func = AsyncMock(side_effect=Exception("Error"))
    for _ in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

    assert circuit_breaker.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Now use successful function
    success_func = AsyncMock(return_value="success")

    # First call should transition to half-open
    result = await circuit_breaker.call(success_func)
    assert result == "success"
    assert circuit_breaker.state == CircuitState.HALF_OPEN

    # Second success should close circuit
    result = await circuit_breaker.call(success_func)
    assert circuit_breaker.state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_circuit_breaker_timeout(circuit_breaker):
    """Test circuit breaker timeout handling."""

    # Function that takes too long
    async def slow_func():
        await asyncio.sleep(2)
        return "done"

    with pytest.raises(CircuitTimeoutError):
        await circuit_breaker.call(slow_func)

    assert circuit_breaker.stats.failed_calls == 1

@pytest.mark.asyncio
async def test_circuit_breaker_with_fallback():
    """Test fallback function execution."""

    async def fallback():
        return "fallback_value"

    config = CircuitBreakerConfig(
        failure_threshold=1,
        fallback_function=fallback
    )
    cb = CircuitBreaker(config)

    # Open circuit
    failing_func = AsyncMock(side_effect=Exception("Error"))
    with pytest.raises(Exception):
        await cb.call(failing_func)

    # Next call should use fallback
    result = await cb.call(failing_func)
    assert result == "fallback_value"

@pytest.mark.asyncio
async def test_half_open_concurrent_limit(circuit_breaker):
    """Test half-open state limits concurrent attempts."""

    # Open the circuit
    failing_func = AsyncMock(side_effect=Exception("Error"))
    for _ in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

    # Wait for recovery
    await asyncio.sleep(1.1)

    # Slow function for testing concurrency
    call_count = 0

    async def slow_func():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.5)
        return "success"

    # Start multiple concurrent calls
    tasks = [
        asyncio.create_task(circuit_breaker.call(slow_func))
        for _ in range(3)
    ]

    # One should succeed, others should be rejected
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if r == "success")
    error_count = sum(1 for r in results if isinstance(r, CircuitOpenError))

    assert success_count == 1  # Only one allowed through
    assert error_count == 2    # Others rejected
    assert call_count == 1     # Only one actually executed
```

### Integration Tests

```python
# File: app/tests/integration/test_circuit_breaker_integration.py
@pytest.mark.asyncio
async def test_canvas_api_circuit_breaker(httpx_mock):
    """Test Canvas API with circuit breaker."""

    # Mock Canvas API failures
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)

    service = ContentExtractionService("token", 123)

    # First calls should attempt and fail
    for _ in range(3):
        with pytest.raises(httpx.HTTPError):
            await service.fetch_module_items(456)

    # Circuit should now be open
    with pytest.raises(CanvasAPIUnavailableError):
        await service.fetch_module_items(456)

    # Verify circuit breaker stats
    cb = get_canvas_circuit_breaker()
    stats = cb.get_stats()
    assert stats["state"] == "open"
    assert stats["failed_calls"] >= 3
```

## Code Quality Improvements

### Decorators for Easy Use

```python
# File: app/core/circuit_breaker.py (addition)
def with_circuit_breaker(
    circuit_breaker: CircuitBreaker,
    fallback: Optional[Callable] = None
):
    """Decorator to apply circuit breaker to functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await circuit_breaker.call(func, *args, **kwargs)
            except CircuitOpenError:
                if fallback:
                    return await fallback(*args, **kwargs)
                raise
        return wrapper
    return decorator

# Usage example
@with_circuit_breaker(get_canvas_circuit_breaker())
async def fetch_canvas_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

## Migration Strategy

### Phase 1: Add Circuit Breaker Infrastructure
1. Implement circuit breaker classes
2. Add configuration settings
3. Create service-specific breakers
4. Add monitoring and metrics

### Phase 2: Integrate with Services
1. Update ContentExtractionService
2. Update CanvasQuizExportService
3. Update MCQGenerationService
4. Add health check endpoints

### Phase 3: Monitor and Tune
1. Deploy with conservative thresholds
2. Monitor circuit breaker metrics
3. Tune thresholds based on data
4. Add fallback strategies where appropriate

### Rollback Plan

```python
# Feature flag for circuit breakers
if settings.ENABLE_CIRCUIT_BREAKERS:
    response = await self.circuit_breaker.call(make_request)
else:
    response = await make_request()  # Direct call
```

## Success Criteria

### Reliability Metrics

- **Failure Isolation**: 100% of external API failures contained
- **Fast Fail Time**: <100ms when circuit is open (vs 30s timeout)
- **Recovery Detection**: <2 minutes to detect service recovery
- **Error Reduction**: 90% reduction in cascading failures

### Performance Metrics

- **Response Time**: 95th percentile <200ms during outages
- **Resource Usage**: 80% reduction in blocked connections
- **Thread Pool Health**: No thread exhaustion during outages

### Monitoring Queries

```python
# Prometheus queries
# Circuit breaker state over time
circuit_breaker_state{service="canvas_api"}

# Failure rate
rate(circuit_breaker_failures_total[5m])

# Rejection rate (calls blocked)
rate(circuit_breaker_rejections_total[5m])

# Service availability
1 - (circuit_breaker_state{service="canvas_api"} == 1)
```

---
