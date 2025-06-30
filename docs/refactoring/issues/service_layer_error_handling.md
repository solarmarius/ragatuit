# 17. Service Layer Error Handling

## Priority: Medium

**Estimated Effort**: 2 days
**Python Version**: 3.10+
**Dependencies**: structlog, FastAPI

## Problem Statement

### Current Situation

Service methods lack standardized error handling, leading to inconsistent error responses, poor error messages, and difficulty debugging production issues. Each service handles errors differently, making the system unpredictable.

### Why It's a Problem

- **Inconsistent Error Responses**: Different error formats across services
- **Poor User Experience**: Generic error messages don't help users
- **Debugging Difficulty**: Insufficient error context in logs
- **No Error Recovery**: Services fail without retry or fallback
- **Missing Error Metrics**: Cannot track error patterns
- **Security Risks**: May expose internal details in errors

### Affected Modules

- `app/services/content_extraction.py` - Basic error handling
- `app/services/mcq_generation.py` - Minimal error handling
- `app/services/canvas_quiz_export.py` - No retry logic
- All service layer modules

### Technical Debt Assessment

- **Risk Level**: Medium - Impacts reliability and debugging
- **Impact**: All service operations and user experience
- **Cost of Delay**: Increases with service complexity

## Current Implementation Analysis

```python
# File: app/services/content_extraction.py (inconsistent handling)
class ContentExtractionService:
    async def extract_and_clean_content(self, module_ids: list[int]) -> dict:
        """PROBLEM: Generic exception handling."""
        all_content = {}

        for module_id in module_ids:
            try:
                content = await self.fetch_module_items(module_id)
                all_content[str(module_id)] = content
            except Exception as e:
                # PROBLEM: Logs error but continues silently
                logger.error(f"Failed to extract module {module_id}: {e}")
                # User never knows this module failed!

        return all_content

    async def _extract_page_content(self, page_url: str) -> str:
        """PROBLEM: Exposes internal errors."""
        try:
            response = await self._make_request_with_retry(page_url, headers)
            # ... process ...
        except httpx.HTTPError as e:
            # PROBLEM: Raw exception bubbles up
            raise e  # Exposes internal URLs and implementation

# File: app/services/mcq_generation.py (minimal handling)
async def generate_question(self, state: MCQGenerationState):
    """PROBLEM: No structured error handling."""
    try:
        # Generate question...
        response = await self._call_llm(prompt)
        return self._parse_response(response)
    except Exception as e:
        # PROBLEM: Sets generic error, loses context
        state["error_message"] = str(e)
        return state

# File: app/api/routes/quiz.py (error propagation issues)
@router.post("/{quiz_id}/generate-questions")
async def generate_questions_endpoint(...):
    try:
        result = await mcq_generation_service.generate_mcqs_for_quiz(...)
        if not result.get("success"):
            # PROBLEM: Generic 500 error
            raise HTTPException(status_code=500, detail="Generation failed")
    except Exception as e:
        # PROBLEM: All errors become 500s
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
```

### Current Error Patterns

```python
# Pattern 1: Silent failures
try:
    result = await risky_operation()
except Exception:
    logger.error("Failed")  # Continues with partial data

# Pattern 2: Generic errors
except Exception as e:
    raise HTTPException(500, "Something went wrong")  # Unhelpful

# Pattern 3: Exposed internals
except httpx.HTTPError as e:
    raise e  # Exposes URLs, tokens, implementation

# Pattern 4: Lost context
except SpecificError as e:
    raise Exception("Failed")  # Original error type lost
```

### Python Anti-patterns Identified

- **Bare Except**: Catching all exceptions blindly
- **Silent Failures**: Logging but not handling errors
- **Generic Messages**: Uninformative error messages
- **Missing Context**: No error metadata or correlation
- **Type Erasure**: Converting specific errors to generic

## Proposed Solution

### Pythonic Approach

Implement a comprehensive error handling strategy with custom exception hierarchy, error context preservation, structured error responses, and proper error recovery mechanisms.

### Design Patterns

- **Exception Hierarchy**: Domain-specific exceptions
- **Error Context**: Rich error information
- **Result Pattern**: Explicit success/failure returns
- **Retry Pattern**: Configurable retry strategies
- **Circuit Breaker**: Prevent cascading failures

### Code Examples

```python
# File: app/core/exceptions.py (NEW - Exception hierarchy)
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class RagUITException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "error_id": self.error_id,
                "timestamp": self.timestamp.isoformat()
            }
        }

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to log format with full context."""
        return {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
            "cause_type": type(self.cause).__name__ if self.cause else None,
            "timestamp": self.timestamp.isoformat()
        }

# Service-specific exceptions
class ServiceException(RagUITException):
    """Base for service layer errors."""
    pass

class ExternalServiceException(ServiceException):
    """External service errors (Canvas, OpenAI)."""

    def __init__(
        self,
        service: str,
        message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=f"{service.upper()}_SERVICE_ERROR",
            status_code=503,  # Service Unavailable
            details={
                "service": service,
                "external_status_code": status_code,
                "retry_after": retry_after
            },
            **kwargs
        )

class ValidationException(ServiceException):
    """Data validation errors."""

    def __init__(self, field: str, message: str, value: Any = None, **kwargs):
        super().__init__(
            message=f"Validation error for {field}: {message}",
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={
                "field": field,
                "value": str(value) if value else None,
                "validation_message": message
            },
            **kwargs
        )

class ResourceNotFoundException(ServiceException):
    """Resource not found errors."""

    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            error_code=f"{resource_type.upper()}_NOT_FOUND",
            status_code=404,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            },
            **kwargs
        )

class QuotaExceededException(ServiceException):
    """Quota/limit exceeded errors."""

    def __init__(self, resource: str, limit: int, current: int, **kwargs):
        super().__init__(
            message=f"Quota exceeded for {resource}: {current}/{limit}",
            error_code="QUOTA_EXCEEDED",
            status_code=429,
            details={
                "resource": resource,
                "limit": limit,
                "current": current,
                "percentage": round(current / limit * 100, 2)
            },
            **kwargs
        )

# File: app/core/error_handler.py (NEW - Centralized error handling)
from typing import TypeVar, Callable, Optional, Union
from functools import wraps
import asyncio
from app.core.logging_config import get_logger

logger = get_logger("error_handler")

T = TypeVar('T')

class ErrorHandler:
    """Centralized error handling with recovery strategies."""

    @staticmethod
    def handle_service_errors(
        operation: str,
        raise_on_error: bool = True,
        default_return: Optional[T] = None
    ):
        """Decorator for service method error handling."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                try:
                    return await func(*args, **kwargs)
                except RagUITException:
                    # Already handled, just log and re-raise
                    raise
                except httpx.HTTPError as e:
                    # Convert to service exception
                    service_error = ExternalServiceException(
                        service="http",
                        message=f"HTTP error during {operation}",
                        status_code=e.response.status_code if hasattr(e, 'response') else None,
                        cause=e
                    )
                    logger.error(
                        "service_http_error",
                        **service_error.to_log_dict(),
                        operation=operation
                    )
                    if raise_on_error:
                        raise service_error
                    return default_return
                except json.JSONDecodeError as e:
                    # Convert to validation exception
                    validation_error = ValidationException(
                        field="response",
                        message="Invalid JSON response",
                        value=str(e.doc)[:100] if hasattr(e, 'doc') else None,
                        cause=e
                    )
                    logger.error(
                        "service_validation_error",
                        **validation_error.to_log_dict(),
                        operation=operation
                    )
                    if raise_on_error:
                        raise validation_error
                    return default_return
                except Exception as e:
                    # Unexpected error
                    service_error = ServiceException(
                        message=f"Unexpected error during {operation}",
                        error_code="INTERNAL_ERROR",
                        cause=e
                    )
                    logger.error(
                        "service_unexpected_error",
                        **service_error.to_log_dict(),
                        operation=operation,
                        exc_info=True
                    )
                    if raise_on_error:
                        raise service_error
                    return default_return

            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                try:
                    return func(*args, **kwargs)
                except RagUITException:
                    raise
                except Exception as e:
                    service_error = ServiceException(
                        message=f"Unexpected error during {operation}",
                        error_code="INTERNAL_ERROR",
                        cause=e
                    )
                    logger.error(
                        "service_unexpected_error",
                        **service_error.to_log_dict(),
                        operation=operation,
                        exc_info=True
                    )
                    if raise_on_error:
                        raise service_error
                    return default_return

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator

    @staticmethod
    async def with_retry(
        func: Callable,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        exceptions: tuple = (ExternalServiceException,)
    ) -> T:
        """Execute function with retry logic."""

        attempt = 0
        last_error = None

        while attempt < max_attempts:
            try:
                return await func()
            except exceptions as e:
                attempt += 1
                last_error = e

                if attempt >= max_attempts:
                    logger.error(
                        "retry_exhausted",
                        attempts=attempt,
                        error=str(e)
                    )
                    raise

                wait_time = backoff_factor ** (attempt - 1)
                logger.warning(
                    "retry_attempt",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    wait_time=wait_time,
                    error=str(e)
                )

                await asyncio.sleep(wait_time)

        raise last_error

# File: app/services/content_extraction.py (UPDATED with proper error handling)
from app.core.exceptions import (
    ExternalServiceException,
    ValidationException,
    ResourceNotFoundException
)
from app.core.error_handler import ErrorHandler

class ContentExtractionService:
    @ErrorHandler.handle_service_errors("content_extraction")
    async def extract_and_clean_content(
        self,
        module_ids: list[int]
    ) -> dict[str, Any]:
        """Extract content with proper error handling."""

        all_content = {}
        failed_modules = []

        for module_id in module_ids:
            try:
                content = await self._extract_module_with_retry(module_id)
                all_content[str(module_id)] = content
            except ExternalServiceException as e:
                # Log but continue with other modules
                logger.warning(
                    "module_extraction_failed",
                    module_id=module_id,
                    error_id=e.error_id,
                    service=e.details.get("service")
                )
                failed_modules.append({
                    "module_id": module_id,
                    "error": e.message,
                    "error_code": e.error_code
                })

        # Return partial success with metadata
        return {
            "content": all_content,
            "metadata": {
                "total_modules": len(module_ids),
                "successful_modules": len(all_content),
                "failed_modules": failed_modules,
                "extraction_complete": len(failed_modules) == 0
            }
        }

    async def _extract_module_with_retry(self, module_id: int) -> dict:
        """Extract single module with retry."""

        async def extract():
            return await self.fetch_module_items(module_id)

        return await ErrorHandler.with_retry(
            extract,
            max_attempts=3,
            exceptions=(ExternalServiceException, httpx.HTTPError)
        )

    @ErrorHandler.handle_service_errors("fetch_module_items")
    async def fetch_module_items(self, module_id: int) -> list[dict]:
        """Fetch module items with structured error handling."""

        url = f"{self.canvas_base_url}/courses/{self.course_id}/modules/{module_id}/items"
        headers = {"Authorization": f"Bearer {self.canvas_token}"}

        try:
            response = await self._make_request_with_retry(url, headers)

            if response.status_code == 404:
                raise ResourceNotFoundException(
                    resource_type="module",
                    resource_id=str(module_id)
                )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            # Sanitize error to not expose token
            safe_url = url.replace(self.canvas_token, "***")
            raise ExternalServiceException(
                service="canvas",
                message=f"Failed to fetch module {module_id}",
                status_code=getattr(e.response, 'status_code', None),
                cause=e,
                details={"url": safe_url, "module_id": module_id}
            )

# File: app/services/result.py (NEW - Result pattern)
from typing import Generic, TypeVar, Optional, Union
from dataclasses import dataclass

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

@dataclass
class Result(Generic[T, E]):
    """Result pattern for explicit success/failure handling."""

    value: Optional[T] = None
    error: Optional[E] = None

    @property
    def is_success(self) -> bool:
        return self.error is None

    @property
    def is_failure(self) -> bool:
        return self.error is not None

    def unwrap(self) -> T:
        """Get value or raise error."""
        if self.is_failure:
            raise self.error
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get value or return default."""
        return self.value if self.is_success else default

    @classmethod
    def success(cls, value: T) -> "Result[T, E]":
        return cls(value=value)

    @classmethod
    def failure(cls, error: E) -> "Result[T, E]":
        return cls(error=error)

# File: app/services/mcq_generation.py (UPDATED with Result pattern)
class MCQGenerationService:
    async def generate_mcqs_for_quiz(
        self,
        quiz_id: UUID,
        target_count: int,
        model: str,
        temperature: float
    ) -> Result[dict, ServiceException]:
        """Generate MCQs with explicit error handling."""

        try:
            # Validate inputs
            if target_count <= 0 or target_count > 100:
                return Result.failure(
                    ValidationException(
                        field="target_count",
                        message="Must be between 1 and 100",
                        value=target_count
                    )
                )

            # Load quiz
            quiz = await self._load_quiz(quiz_id)
            if not quiz:
                return Result.failure(
                    ResourceNotFoundException(
                        resource_type="quiz",
                        resource_id=str(quiz_id)
                    )
                )

            # Generate questions
            questions = await self._generate_with_retry(
                quiz.content_dict,
                target_count,
                model,
                temperature
            )

            # Save to database
            await self._save_questions(quiz_id, questions)

            return Result.success({
                "quiz_id": str(quiz_id),
                "questions_generated": len(questions),
                "model_used": model,
                "status": "completed"
            })

        except ServiceException as e:
            logger.error(
                "mcq_generation_failed",
                **e.to_log_dict(),
                quiz_id=str(quiz_id)
            )
            return Result.failure(e)
        except Exception as e:
            error = ServiceException(
                message="Unexpected error during MCQ generation",
                error_code="MCQ_GENERATION_ERROR",
                cause=e
            )
            logger.error(
                "mcq_generation_unexpected_error",
                **error.to_log_dict(),
                quiz_id=str(quiz_id),
                exc_info=True
            )
            return Result.failure(error)

# File: app/api/routes/quiz.py (UPDATED error responses)
from app.core.exceptions import RagUITException

@router.post("/{quiz_id}/generate-questions")
async def generate_questions_endpoint(
    quiz_id: UUID,
    generation_request: MCQGenerationRequest,
    current_user: CurrentUser,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Generate questions with proper error responses."""

    try:
        # Verify ownership
        quiz = get_quiz_by_id(session, quiz_id)
        if not quiz:
            raise ResourceNotFoundException(
                resource_type="quiz",
                resource_id=str(quiz_id)
            )

        if quiz.owner_id != current_user.id:
            raise ServiceException(
                message="You don't have permission to access this quiz",
                error_code="PERMISSION_DENIED",
                status_code=403
            )

        # Start generation
        background_tasks.add_task(
            generate_questions_task,
            quiz_id,
            generation_request,
            current_user.id
        )

        return {
            "message": "Question generation started",
            "quiz_id": str(quiz_id),
            "status": "processing"
        }

    except RagUITException as e:
        # Service exceptions become proper HTTP responses
        logger.warning(
            "api_service_error",
            **e.to_log_dict(),
            endpoint="generate_questions",
            quiz_id=str(quiz_id)
        )
        raise HTTPException(
            status_code=e.status_code,
            detail=e.to_dict()
        )
    except Exception as e:
        # Unexpected errors are logged but not exposed
        error_id = str(uuid.uuid4())
        logger.error(
            "api_unexpected_error",
            error_id=error_id,
            endpoint="generate_questions",
            quiz_id=str(quiz_id),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "error_id": error_id
                }
            }
        )

# File: app/middleware/error_middleware.py (NEW)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except RagUITException as e:
            # Application errors get structured response
            return JSONResponse(
                status_code=e.status_code,
                content=e.to_dict(),
                headers={
                    "X-Error-ID": e.error_id
                }
            )
        except Exception as e:
            # Unexpected errors get generic response
            error_id = str(uuid.uuid4())
            logger.error(
                "unhandled_error",
                error_id=error_id,
                path=request.url.path,
                method=request.method,
                exc_info=True
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "error_id": error_id
                    }
                },
                headers={
                    "X-Error-ID": error_id
                }
            )
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   ├── exceptions.py            # NEW: Exception hierarchy
│   │   ├── error_handler.py         # NEW: Error handling utilities
│   │   └── result.py                # NEW: Result pattern
│   ├── middleware/
│   │   └── error_middleware.py      # NEW: Global error handling
│   ├── services/
│   │   ├── content_extraction.py    # UPDATE: Structured errors
│   │   ├── mcq_generation.py        # UPDATE: Result pattern
│   │   └── canvas_quiz_export.py    # UPDATE: Error handling
│   ├── api/
│   │   └── routes/
│   │       └── quiz.py              # UPDATE: Error responses
│   ├── main.py                      # UPDATE: Add middleware
│   └── tests/
│       └── test_error_handling.py   # NEW: Error tests
```

### Configuration

```python
# app/core/config.py additions
class Settings(BaseSettings):
    # Error handling settings
    EXPOSE_ERROR_DETAILS: bool = False  # Only in dev
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0
    ERROR_LOG_RETENTION_DAYS: int = 30
    INCLUDE_ERROR_ID_IN_RESPONSE: bool = True
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/core/test_error_handling.py
import pytest
from app.core.exceptions import (
    ServiceException,
    ExternalServiceException,
    ValidationException
)
from app.core.error_handler import ErrorHandler

def test_exception_hierarchy():
    """Test exception creation and properties."""

    error = ExternalServiceException(
        service="canvas",
        message="API timeout",
        status_code=504,
        retry_after=60
    )

    assert error.error_code == "CANVAS_SERVICE_ERROR"
    assert error.status_code == 503
    assert error.details["service"] == "canvas"
    assert error.details["retry_after"] == 60
    assert error.error_id is not None

def test_exception_serialization():
    """Test exception converts to API format."""

    error = ValidationException(
        field="email",
        message="Invalid format",
        value="not-an-email"
    )

    api_response = error.to_dict()
    assert api_response["error"]["code"] == "VALIDATION_ERROR"
    assert "email" in api_response["error"]["message"]
    assert api_response["error"]["details"]["field"] == "email"

@pytest.mark.asyncio
async def test_error_handler_decorator():
    """Test error handling decorator."""

    @ErrorHandler.handle_service_errors("test_operation")
    async def failing_operation():
        raise ValueError("Test error")

    with pytest.raises(ServiceException) as exc_info:
        await failing_operation()

    assert exc_info.value.error_code == "INTERNAL_ERROR"
    assert exc_info.value.cause.args[0] == "Test error"

@pytest.mark.asyncio
async def test_retry_logic():
    """Test retry with backoff."""

    attempt_count = 0

    async def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ExternalServiceException(
                service="test",
                message="Temporary failure"
            )
        return "success"

    result = await ErrorHandler.with_retry(
        flaky_operation,
        max_attempts=3
    )

    assert result == "success"
    assert attempt_count == 3

def test_result_pattern():
    """Test Result pattern usage."""

    # Success case
    success_result = Result.success({"data": "value"})
    assert success_result.is_success
    assert success_result.unwrap() == {"data": "value"}

    # Failure case
    error = ValidationException("field", "invalid")
    failure_result = Result.failure(error)
    assert failure_result.is_failure
    assert failure_result.unwrap_or({}) == {}

    with pytest.raises(ValidationException):
        failure_result.unwrap()
```

### Integration Tests

```python
# File: app/tests/api/test_error_responses.py
from fastapi.testclient import TestClient

def test_api_error_response_format(client: TestClient):
    """Test API returns structured errors."""

    # Request non-existent resource
    response = client.get(
        "/api/quiz/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 404
    error_data = response.json()

    assert "error" in error_data
    assert error_data["error"]["code"] == "QUIZ_NOT_FOUND"
    assert "error_id" in error_data["error"]
    assert "X-Error-ID" in response.headers

def test_validation_error_response(client: TestClient):
    """Test validation errors are properly formatted."""

    response = client.post(
        "/api/quiz/",
        json={
            "title": "",  # Invalid - empty title
            "canvas_course_id": -1  # Invalid - negative ID
        },
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 422  # FastAPI validation
    error_data = response.json()
    assert "detail" in error_data
    assert len(error_data["detail"]) >= 2

@pytest.mark.asyncio
async def test_external_service_error_handling(
    client: TestClient,
    httpx_mock
):
    """Test external service errors are handled."""

    # Mock Canvas API failure
    httpx_mock.add_response(
        status_code=503,
        headers={"Retry-After": "60"}
    )

    response = client.post(
        "/api/quiz/123/extract-content",
        headers={"Authorization": "Bearer valid-token"}
    )

    assert response.status_code == 503
    error_data = response.json()
    assert error_data["error"]["code"] == "CANVAS_SERVICE_ERROR"
    assert error_data["error"]["details"]["retry_after"] == 60
```

## Code Quality Improvements

### Error Monitoring

```python
# Integration with error tracking services
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# In app/main.py
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        before_send=lambda event, hint: filter_sensitive_data(event)
    )

def filter_sensitive_data(event):
    """Remove sensitive data from error reports."""
    # Remove tokens, passwords, etc.
    if "request" in event:
        if "headers" in event["request"]:
            event["request"]["headers"].pop("authorization", None)
    return event
```

### Error Metrics

```python
from prometheus_client import Counter, Histogram

error_counter = Counter(
    'application_errors_total',
    'Total application errors',
    ['error_code', 'service', 'operation']
)

error_response_time = Histogram(
    'error_handling_duration_seconds',
    'Time spent handling errors',
    ['error_type']
)

# Update error handler to record metrics
def record_error_metrics(error: RagUITException, operation: str):
    error_counter.labels(
        error_code=error.error_code,
        service=error.details.get('service', 'unknown'),
        operation=operation
    ).inc()
```

## Migration Strategy

### Phase 1: Add Error Infrastructure

1. Create exception hierarchy
2. Implement error handler
3. Add error middleware

### Phase 2: Update Services

1. Update one service at a time
2. Replace generic exceptions
3. Add retry logic

### Phase 3: Update API Layer

1. Update error responses
2. Add error documentation
3. Update client handling

### Rollback Plan

```python
# Feature flag for new error handling
if settings.USE_STRUCTURED_ERRORS:
    app.add_middleware(ErrorHandlingMiddleware)
    # Use new exception classes
else:
    # Keep existing error handling
    pass
```

## Success Criteria

### Error Quality Metrics

- **Error Context**: 100% of errors have correlation IDs
- **Error Types**: <5% "Internal Error" responses
- **Recovery Rate**: >80% of retryable errors succeed
- **User Messages**: 100% user-friendly error messages

### Operational Metrics

- **MTTR**: 50% reduction in error investigation time
- **Error Rate**: Baseline established and monitored
- **Retry Success**: >90% within 3 attempts

---
