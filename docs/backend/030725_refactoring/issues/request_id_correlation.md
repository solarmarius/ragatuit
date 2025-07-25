# 14. Request ID Correlation

## Priority: High

**Estimated Effort**: 1 day
**Python Version**: 3.10+
**Dependencies**: structlog, FastAPI middleware

## Problem Statement

### Current Situation

The application lacks request ID correlation across services and logs, making it extremely difficult to trace issues through the system, especially in production environments with high traffic and concurrent requests.

### Why It's a Problem

- **Debugging Nightmare**: Cannot trace a single request through logs
- **Support Issues**: Hard to help users with specific problems
- **Performance Analysis**: Cannot track request flow timing
- **Error Investigation**: Difficult to correlate errors across services
- **Distributed Tracing**: No way to follow requests across async tasks
- **Compliance**: May need request tracking for audit requirements

### Affected Modules

- `app/main.py` - Main application setup
- `app/core/logging_config.py` - Logging configuration
- All API routes and services
- Background tasks and async operations

### Technical Debt Assessment

- **Risk Level**: High - Critical for production debugging
- **Impact**: All request handling and logging
- **Cost of Delay**: Increases with system complexity

## Current Implementation Analysis

```python
# File: app/core/logging_config.py (current logging without correlation)
import structlog

def get_logger(name: str):
    """Get a structured logger instance."""
    return structlog.get_logger(name)

# File: app/api/routes/quiz.py (current logging)
logger = get_logger("quiz_routes")

@router.post("/")
async def create_new_quiz(
    quiz_data: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> Quiz:
    # PROBLEM: No request context in logs
    logger.info(
        "quiz_creation_started",
        user_id=str(current_user.id),
        course_id=quiz_data.canvas_course_id,
    )

    quiz = create_quiz(session, quiz_data, current_user.id)

    # PROBLEM: Can't correlate this with the above log
    logger.info(
        "quiz_creation_completed",
        quiz_id=str(quiz.id),
    )

    return quiz

# File: app/services/mcq_generation.py (background task logging)
async def generate_questions_for_quiz(quiz_id: UUID, ...):
    # PROBLEM: Background task has no link to original request
    logger.info(
        "question_generation_started",
        quiz_id=str(quiz_id),
    )

    # If this fails, no way to trace back to original request
```

### Current Debugging Scenario

```python
# User reports: "Quiz creation failed at 2:30 PM"
# Current log search:
# 1. Search for user_id around that time - finds 50 requests
# 2. Search for errors around that time - finds 200 errors
# 3. No way to connect user's request to specific error
# 4. Have to guess which logs belong together

# With high traffic:
# - 1000s of interleaved log lines
# - Multiple users creating quizzes simultaneously
# - Background tasks running async
# - No way to filter to single request flow
```

### Python Anti-patterns Identified

- **No Context Propagation**: Request context lost across calls
- **Manual Log Correlation**: Developers manually adding IDs
- **Async Context Loss**: Context not preserved in background tasks
- **No Standardization**: Different log formats across modules

## Proposed Solution

### Pythonic Approach

Implement request ID correlation using FastAPI middleware with Python's contextvars for async-safe context propagation, ensuring all logs and operations can be traced.

### Design Patterns

- **Middleware Pattern**: Inject request ID early in pipeline
- **Context Pattern**: Use contextvars for async propagation
- **Decorator Pattern**: Auto-inject context into functions
- **Chain of Responsibility**: Pass context through call chain

### Code Examples

```python
# File: app/core/request_context.py (NEW)
from contextvars import ContextVar
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

# Context variables for request-scoped data
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
request_start_time_var: ContextVar[Optional[datetime]] = ContextVar('request_start_time', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
correlation_data_var: ContextVar[Dict[str, Any]] = ContextVar('correlation_data', default={})

class RequestContext:
    """Manager for request-scoped context data."""

    @staticmethod
    def get_request_id() -> Optional[str]:
        """Get current request ID."""
        return request_id_var.get()

    @staticmethod
    def set_request_id(request_id: str) -> None:
        """Set request ID for current context."""
        request_id_var.set(request_id)

    @staticmethod
    def get_user_id() -> Optional[str]:
        """Get current user ID."""
        return user_id_var.get()

    @staticmethod
    def set_user_id(user_id: str) -> None:
        """Set user ID for current context."""
        user_id_var.set(user_id)

    @staticmethod
    def get_correlation_data() -> Dict[str, Any]:
        """Get all correlation data."""
        return {
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "start_time": request_start_time_var.get(),
            **correlation_data_var.get()
        }

    @staticmethod
    def add_correlation_data(**kwargs) -> None:
        """Add additional correlation data."""
        current = correlation_data_var.get()
        correlation_data_var.set({**current, **kwargs})

    @staticmethod
    def clear() -> None:
        """Clear all context data."""
        request_id_var.set(None)
        user_id_var.set(None)
        request_start_time_var.set(None)
        correlation_data_var.set({})

# File: app/middleware/request_id.py (NEW)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

from app.core.request_context import RequestContext
from app.core.logging_config import get_logger

logger = get_logger("request_id_middleware")

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to inject and track request IDs."""

    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = f"req_{uuid.uuid4().hex[:12]}"

        # Set context
        RequestContext.set_request_id(request_id)
        RequestContext.set_request_id(datetime.utcnow())

        # Add to request state for easy access
        request.state.request_id = request_id

        # Log request start
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log request completion
            duration = time.time() - start_time
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_seconds=duration,
            )

            return response

        except Exception as e:
            # Log request failure
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=duration,
                exc_info=True,
            )
            raise
        finally:
            # Clear context
            RequestContext.clear()

# File: app/core/logging_config.py (UPDATED)
import structlog
from structlog.types import EventDict, Processor
from typing import Any, MutableMapping

from app.core.request_context import RequestContext

def add_request_context(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add request context to all log entries."""

    # Add request ID if available
    request_id = RequestContext.get_request_id()
    if request_id:
        event_dict["request_id"] = request_id

    # Add user ID if available
    user_id = RequestContext.get_user_id()
    if user_id:
        event_dict["user_id"] = user_id

    # Add any additional correlation data
    correlation_data = RequestContext.get_correlation_data()
    for key, value in correlation_data.items():
        if key not in event_dict and value is not None:
            event_dict[key] = value

    return event_dict

def setup_logging():
    """Configure structured logging with request context."""

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_request_context,  # Add request context processor
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# File: app/main.py (UPDATED)
from app.middleware.request_id import RequestIDMiddleware
from app.core.logging_config import setup_logging

# Setup logging first
setup_logging()

app = FastAPI(title="Rag@UiT Backend")

# Add request ID middleware early in the chain
app.add_middleware(RequestIDMiddleware)

# File: app/api/deps.py (UPDATED)
from app.core.request_context import RequestContext

async def get_current_user(
    session: SessionDep, token: str = Depends(oauth2_scheme)
) -> User:
    """Get current user and set in context."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise credentials_exception

    user = session.get(User, token_data.sub)
    if not user:
        raise credentials_exception

    # Set user ID in context for logging
    RequestContext.set_user_id(str(user.id))

    return user

# File: app/api/routes/quiz.py (UPDATED with context)
from app.core.request_context import RequestContext

@router.post("/", response_model=Quiz)
async def create_new_quiz(
    request: Request,  # Add request to get request_id
    quiz_data: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> Quiz:
    """Create a new quiz with request tracking."""

    # Add additional context
    RequestContext.add_correlation_data(
        operation="create_quiz",
        canvas_course_id=quiz_data.canvas_course_id,
    )

    logger.info(
        "quiz_creation_started",
        modules_count=len(quiz_data.selected_modules),
    )

    quiz = create_quiz(session, quiz_data, current_user.id)

    # Pass request ID to background task
    background_tasks.add_task(
        extract_content_for_quiz,
        quiz.id,
        quiz.canvas_course_id,
        list(quiz_data.selected_modules.keys()),
        canvas_token,
        request.state.request_id  # Pass request ID
    )

    logger.info(
        "quiz_creation_completed",
        quiz_id=str(quiz.id),
    )

    return quiz

# File: app/api/routes/quiz.py (UPDATED background task)
async def extract_content_for_quiz(
    quiz_id: UUID,
    course_id: int,
    module_ids: list[int],
    canvas_token: str,
    parent_request_id: str,  # Parent request ID
) -> None:
    """Background task with request ID propagation."""

    # Create new request ID for background task but link to parent
    task_request_id = f"task_{uuid.uuid4().hex[:12]}"
    RequestContext.set_request_id(task_request_id)
    RequestContext.add_correlation_data(
        parent_request_id=parent_request_id,
        task_type="content_extraction",
        quiz_id=str(quiz_id),
    )

    logger.info(
        "content_extraction_started",
        course_id=course_id,
        module_count=len(module_ids),
    )

    try:
        # Task implementation...

        logger.info("content_extraction_completed")

    except Exception as e:
        logger.error(
            "content_extraction_failed",
            error=str(e),
            exc_info=True,
        )
    finally:
        RequestContext.clear()

# File: app/core/decorators.py (NEW)
from functools import wraps
from app.core.request_context import RequestContext

def with_request_context(operation: str):
    """Decorator to add operation context to functions."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            RequestContext.add_correlation_data(operation=operation)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            RequestContext.add_correlation_data(operation=operation)
            return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Usage in services
class MCQGenerationService:
    @with_request_context("generate_mcqs")
    async def generate_mcqs_for_quiz(self, quiz_id: UUID, ...):
        logger.info("Starting MCQ generation")  # Will include request_id
        # ...

# File: app/api/routes/health.py (NEW endpoint)
@router.get("/request/{request_id}")
async def get_request_logs(
    request_id: str,
    current_user: CurrentUser,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> dict[str, Any]:
    """Get all logs for a specific request ID (admin only)."""

    # Check admin permission
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # In real implementation, query log storage
    # This is a placeholder for the concept
    logs = await fetch_logs_by_request_id(
        request_id,
        start_time or datetime.utcnow() - timedelta(hours=24),
        end_time or datetime.utcnow()
    )

    return {
        "request_id": request_id,
        "log_count": len(logs),
        "logs": logs
    }

# File: app/core/monitoring.py (Add metrics)
from prometheus_client import Histogram, Counter

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint', 'status']
)

request_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Update middleware to record metrics with request_id labels
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   ├── request_context.py       # NEW: Context management
│   │   ├── logging_config.py        # UPDATE: Add context processor
│   │   ├── decorators.py            # NEW: Context decorators
│   │   └── monitoring.py            # UPDATE: Add request metrics
│   ├── middleware/
│   │   └── request_id.py            # NEW: Request ID middleware
│   ├── api/
│   │   ├── deps.py                  # UPDATE: Set user context
│   │   └── routes/
│   │       ├── quiz.py              # UPDATE: Use context
│   │       └── health.py            # UPDATE: Add log endpoint
│   ├── main.py                      # UPDATE: Add middleware
│   └── tests/
│       └── test_request_context.py  # NEW: Context tests
```

### Configuration Changes

```python
# app/core/config.py additions
class Settings(BaseSettings):
    # Request ID settings
    REQUEST_ID_HEADER: str = "X-Request-ID"
    ENABLE_REQUEST_TRACKING: bool = True
    REQUEST_LOG_RETENTION_DAYS: int = 30

    # Correlation settings
    PROPAGATE_REQUEST_ID_TO_TASKS: bool = True
    INCLUDE_REQUEST_ID_IN_RESPONSES: bool = True
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/core/test_request_context.py
import pytest
from app.core.request_context import RequestContext
import asyncio

def test_request_context_basic():
    """Test basic context operations."""

    # Set context
    RequestContext.set_request_id("test-123")
    RequestContext.set_user_id("user-456")

    # Verify retrieval
    assert RequestContext.get_request_id() == "test-123"
    assert RequestContext.get_user_id() == "user-456"

    # Clear context
    RequestContext.clear()
    assert RequestContext.get_request_id() is None

@pytest.mark.asyncio
async def test_context_isolation_async():
    """Test context isolation between async tasks."""

    async def task1():
        RequestContext.set_request_id("task1-id")
        await asyncio.sleep(0.1)
        return RequestContext.get_request_id()

    async def task2():
        RequestContext.set_request_id("task2-id")
        await asyncio.sleep(0.05)
        return RequestContext.get_request_id()

    # Run tasks concurrently
    results = await asyncio.gather(task1(), task2())

    # Each task should have its own context
    assert results[0] == "task1-id"
    assert results[1] == "task2-id"

def test_correlation_data():
    """Test additional correlation data."""

    RequestContext.set_request_id("test-123")
    RequestContext.add_correlation_data(
        operation="test_op",
        entity_id="entity-789"
    )

    data = RequestContext.get_correlation_data()
    assert data["request_id"] == "test-123"
    assert data["operation"] == "test_op"
    assert data["entity_id"] == "entity-789"

# File: app/tests/middleware/test_request_id_middleware.py
from fastapi.testclient import TestClient
from app.main import app

def test_request_id_generation(client: TestClient):
    """Test automatic request ID generation."""

    response = client.get("/api/health")

    # Should have request ID in response
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"].startswith("req_")

def test_request_id_propagation(client: TestClient):
    """Test request ID propagation from client."""

    custom_id = "client-request-123"
    response = client.get(
        "/api/health",
        headers={"X-Request-ID": custom_id}
    )

    # Should use provided request ID
    assert response.headers["X-Request-ID"] == custom_id

@pytest.mark.asyncio
async def test_request_id_in_logs(client: TestClient, caplog):
    """Test request ID appears in logs."""

    response = client.post(
        "/api/quiz/",
        json={
            "title": "Test Quiz",
            "canvas_course_id": 123,
            "selected_modules": {"1": "Module 1"}
        },
        headers={"Authorization": "Bearer test-token"}
    )

    request_id = response.headers["X-Request-ID"]

    # Check logs contain request ID
    log_records = [r for r in caplog.records if hasattr(r, 'request_id')]
    assert len(log_records) > 0
    assert all(r.request_id == request_id for r in log_records)
```

### Integration Tests

```python
# File: app/tests/integration/test_request_tracking.py
@pytest.mark.asyncio
async def test_request_tracking_through_system(
    client: TestClient,
    test_user,
    mock_canvas_api
):
    """Test request ID tracking through entire flow."""

    # Create quiz with known request ID
    request_id = "test-request-12345"
    response = client.post(
        "/api/quiz/",
        json={
            "title": "Test Quiz",
            "canvas_course_id": 123,
            "selected_modules": {"1": "Module 1"}
        },
        headers={
            "Authorization": f"Bearer {test_user.access_token}",
            "X-Request-ID": request_id
        }
    )

    assert response.status_code == 200
    quiz_id = response.json()["id"]

    # Wait for background task
    await asyncio.sleep(1)

    # Check logs (in real system, would query log storage)
    # Verify all operations have request_id
```

## Code Quality Improvements

### Log Aggregation

```python
# Example structured log output with request correlation
{
    "timestamp": "2024-01-15T10:30:45.123Z",
    "level": "info",
    "logger": "quiz_routes",
    "message": "quiz_creation_started",
    "request_id": "req_abc123def456",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "operation": "create_quiz",
    "canvas_course_id": 12345,
    "modules_count": 5
}

# Query logs for specific request
# Elasticsearch/OpenSearch query example:
{
    "query": {
        "term": {
            "request_id": "req_abc123def456"
        }
    },
    "sort": [
        { "timestamp": "asc" }
    ]
}
```

### Distributed Tracing Integration

```python
# Future enhancement: OpenTelemetry integration
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "request.id": request.state.request_id
            }
        ) as span:
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            return response
```

## Migration Strategy

### Phase 1: Add Infrastructure
1. Implement RequestContext
2. Update logging configuration
3. Add RequestIDMiddleware

### Phase 2: Update Services
1. Update all route handlers
2. Update background tasks
3. Add context decorators

### Phase 3: Monitoring
1. Add log aggregation queries
2. Create debugging tools
3. Train team on usage

### Rollback Plan

```python
# Feature flag for request tracking
if settings.ENABLE_REQUEST_TRACKING:
    app.add_middleware(RequestIDMiddleware)
    structlog.configure(processors=[add_request_context, ...])
else:
    # Original configuration
    structlog.configure(processors=[...])
```

## Success Criteria

### Operational Metrics

- **Log Correlation**: 100% of logs have request_id
- **Debugging Time**: 80% reduction in issue investigation
- **Support Resolution**: 50% faster support ticket resolution
- **Error Tracking**: 100% of errors traceable to request

### Performance Metrics

- **Overhead**: <1ms added latency
- **Memory**: <1KB per request context
- **Log Size**: <5% increase from request_id

### Monitoring Queries

```python
# Sample queries for request tracking

# 1. Find all logs for a request
def get_request_logs(request_id: str):
    return f"""
    SELECT * FROM logs
    WHERE request_id = '{request_id}'
    ORDER BY timestamp ASC
    """

# 2. Find failed requests by user
def get_user_failures(user_id: str, hours: int = 24):
    return f"""
    SELECT DISTINCT request_id, timestamp, error
    FROM logs
    WHERE user_id = '{user_id}'
    AND level = 'error'
    AND timestamp > NOW() - INTERVAL '{hours} hours'
    """

# 3. Trace request flow
def get_request_flow(request_id: str):
    return f"""
    SELECT timestamp, logger, message, operation
    FROM logs
    WHERE request_id = '{request_id}'
    OR parent_request_id = '{request_id}'
    ORDER BY timestamp ASC
    """
```

---
