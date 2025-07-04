# FastAPI + LangGraph Codebase Refactoring Analysis

## Executive Summary

After conducting a thorough code review of the Rag@UiT FastAPI backend codebase with LangGraph integration, I've identified several critical areas requiring immediate attention and refactoring.

### Critical Issues Requiring Immediate Attention

1. **Circular dependency risk** between security module and auth routes
2. **Hardcoded API URLs** in content extraction service
3. **Database connection pooling not configured** - using default SQLModel settings
4. **Lack of proper transaction management** in background tasks
5. **Missing dependency injection pattern** for services
6. **No proper error recovery mechanism** in LangGraph workflow
7. **Inefficient N+1 query patterns** in question retrieval

### Estimated Effort for Refactoring

- **Phase 1 (Critical Issues)**: 1-2 weeks
- **Phase 2 (Performance Optimizations)**: 2-3 weeks
- **Phase 3 (Code Quality Improvements)**: 3-4 weeks
- **Total Estimated Effort**: 6-9 weeks

## Detailed Findings

### 1. Architecture & Structure

**Current State:**
The application follows a basic layered architecture with:

- Entry point: `main.py`
- API routes in `api/routes/`
- Business logic mixed between routes and services
- CRUD operations in a single `crud.py` file
- Services lack proper abstraction and dependency injection

**Issues Identified:**

1. Circular import risk between `core/security.py` and `api/routes/auth.py`
2. Services instantiated as global singletons without proper lifecycle management
3. Mixed responsibilities in route handlers (business logic + HTTP handling)
4. No clear separation between domain models and API models
5. Background tasks create new database sessions without proper connection management

**Recommendations:**

1. **Implement proper dependency injection for services:**

```python
# Before (current implementation)
# In mcq_generation.py
mcq_generation_service = MCQGenerationService()

# In quiz.py route
await mcq_generation_service.generate_mcqs_for_quiz(...)

# After (recommended)
# services/base.py
from abc import ABC, abstractmethod
from typing import Protocol

class MCQGenerationServiceProtocol(Protocol):
    async def generate_mcqs_for_quiz(
        self, quiz_id: UUID, target_count: int, model: str, temperature: float
    ) -> dict[str, Any]: ...

# services/dependencies.py
from functools import lru_cache
from app.services.mcq_generation import MCQGenerationService

@lru_cache()
def get_mcq_service() -> MCQGenerationService:
    return MCQGenerationService()

MCQServiceDep = Annotated[MCQGenerationService, Depends(get_mcq_service)]

# In routes
async def generate_questions(
    mcq_service: MCQServiceDep,
    # ... other deps
):
    await mcq_service.generate_mcqs_for_quiz(...)
```

**Reasoning:** This provides better testability, lifecycle management, and removes global state.

2. **Fix circular dependency issue:**

```python
# Before (circular import risk)
# In security.py
from app.api.routes.auth import refresh_canvas_token  # Circular!

# After (using dependency injection)
# security.py
from typing import Protocol

class TokenRefresher(Protocol):
    async def refresh_canvas_token(self, user: User, session: Session) -> None: ...

async def ensure_valid_canvas_token(
    session: Session,
    user: User,
    token_refresher: TokenRefresher | None = None
) -> str:
    # Use injected refresher instead of importing
    if token_refresher:
        await token_refresher.refresh_canvas_token(user, session)
```

**Reasoning:** Breaks circular dependency and improves testability.

### 2. Database Layer

**Current State:**

- Using SQLModel with basic SQLAlchemy engine
- No connection pooling configuration
- JSON fields stored as strings with manual parsing
- Missing database indexes on frequently queried fields
- Background tasks create new sessions without proper management

**Issues Identified:**

1. Default connection pool settings may cause connection exhaustion
2. JSON string storage is inefficient and error-prone
3. Missing indexes on `quiz.owner_id`, `question.quiz_id`
4. No query optimization for bulk operations
5. Risk of connection leaks in background tasks

**Recommendations:**

1. **Configure proper connection pooling:**

```python
# Before
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

# After
from sqlalchemy.pool import QueuePool

engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    poolclass=QueuePool,
    pool_size=20,  # Number of connections to maintain
    max_overflow=40,  # Maximum overflow connections
    pool_timeout=30,  # Timeout before error
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Test connections before using
    echo_pool=settings.ENVIRONMENT == "local",  # Log pool checkouts in dev
)
```

**Reasoning:** Prevents connection exhaustion under load and improves reliability.

2. **Use proper JSON columns:**

```python
# Before
class Quiz(SQLModel, table=True):
    selected_modules: str = Field(description="JSON array of selected modules")
    extracted_content: str | None = Field(default=None)

    @property
    def modules_dict(self) -> dict[int, str]:
        try:
            return json.loads(self.selected_modules)
        except:
            return {}

# After
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

class Quiz(SQLModel, table=True):
    selected_modules: dict[int, str] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default={})
    )
    extracted_content: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )
```

**Reasoning:** Native JSON support provides better performance, type safety, and querying capabilities.

3. **Add missing indexes:**

```python
# In new migration
def upgrade():
    op.create_index('ix_quiz_owner_id', 'quiz', ['owner_id'])
    op.create_index('ix_quiz_canvas_course_id', 'quiz', ['canvas_course_id'])
    op.create_index('ix_question_quiz_id', 'question', ['quiz_id'])
    op.create_index('ix_question_is_approved', 'question', ['quiz_id', 'is_approved'])
```

**Reasoning:** Significantly improves query performance for common access patterns.

### 3. API Design

**Current State:**

- RESTful design with some inconsistencies
- Background tasks triggered from API endpoints
- Mixed sync/async patterns
- Inconsistent error responses
- No API versioning strategy beyond URL prefix

**Issues Identified:**

1. Background tasks don't properly handle database sessions
2. No request ID tracking for debugging
3. Missing pagination on list endpoints
4. Inconsistent response formats
5. No proper OpenAPI schema customization

**Recommendations:**

1. **Implement proper background task management:**

```python
# Before
async def extract_content_for_quiz(quiz_id: UUID, ...):
    with Session(engine) as session:  # Risk of connection leak!
        # ... work

# After
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

class BackgroundTaskManager:
    def __init__(self, engine):
        self.engine = engine

    @asynccontextmanager
    async def get_session(self):
        async with AsyncSession(self.engine) as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

# Usage
async def extract_content_for_quiz(quiz_id: UUID, task_manager: BackgroundTaskManager):
    async with task_manager.get_session() as session:
        # ... work with proper cleanup
```

**Reasoning:** Ensures proper session lifecycle and prevents connection leaks.

2. **Add pagination to list endpoints:**

```python
# Before
@router.get("/", response_model=list[Quiz])
def get_user_quizzes_endpoint(current_user: CurrentUser, session: SessionDep):
    return get_user_quizzes(session, current_user.id)

# After
from app.models import PaginatedResponse

@router.get("/", response_model=PaginatedResponse[Quiz])
def get_user_quizzes_endpoint(
    current_user: CurrentUser,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    total = session.exec(
        select(func.count(Quiz.id)).where(Quiz.owner_id == current_user.id)
    ).one()

    items = session.exec(
        select(Quiz)
        .where(Quiz.owner_id == current_user.id)
        .order_by(desc(Quiz.created_at))
        .offset(skip)
        .limit(limit)
    ).all()

    return PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )
```

**Reasoning:** Prevents memory issues with large datasets and improves API usability.

### 4. CRUD Operations

**Current State:**

- All CRUD operations in a single 500+ line file
- No repository pattern implementation
- Mixed transaction management
- Some operations lack proper error handling
- Direct model manipulation without validation

**Issues Identified:**

1. Single file becoming too large and hard to maintain
2. No bulk operations optimization
3. Inconsistent transaction boundaries
4. Missing audit trail for changes
5. No soft delete implementation

**Recommendations:**

1. **Implement repository pattern:**

```python
# repositories/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type
from sqlmodel import SQLModel, Session, select
from uuid import UUID

ModelType = TypeVar("ModelType", bound=SQLModel)

class BaseRepository(ABC, Generic[ModelType]):
    def __init__(self, session: Session, model: Type[ModelType]):
        self.session = session
        self.model = model

    def get(self, id: UUID) -> ModelType | None:
        return self.session.get(self.model, id)

    def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        self.session.delete(obj)
        self.session.commit()

# repositories/quiz.py
class QuizRepository(BaseRepository[Quiz]):
    def __init__(self, session: Session):
        super().__init__(session, Quiz)

    def get_by_owner(self, owner_id: UUID, skip: int = 0, limit: int = 20) -> list[Quiz]:
        return list(self.session.exec(
            select(Quiz)
            .where(Quiz.owner_id == owner_id)
            .order_by(desc(Quiz.created_at))
            .offset(skip)
            .limit(limit)
        ).all())

    def create_with_modules(self, quiz_data: QuizCreate, owner_id: UUID) -> Quiz:
        quiz = Quiz(**quiz_data.model_dump(), owner_id=owner_id)
        self.session.add(quiz)
        self.session.commit()
        self.session.refresh(quiz)
        return quiz
```

**Reasoning:** Provides better organization, testability, and reusability.

2. **Implement bulk operations:**

```python
# repositories/question.py
class QuestionRepository(BaseRepository[Question]):
    def create_bulk(self, questions: list[QuestionCreate]) -> list[Question]:
        # Use bulk_insert_mappings for better performance
        question_dicts = [q.model_dump() for q in questions]
        self.session.bulk_insert_mappings(Question, question_dicts)
        self.session.commit()

        # Return created questions
        quiz_id = questions[0].quiz_id
        return self.get_by_quiz(quiz_id)

    def approve_bulk(self, question_ids: list[UUID]) -> int:
        # Use bulk update for better performance
        stmt = (
            update(Question)
            .where(Question.id.in_(question_ids))
            .values(is_approved=True, approved_at=datetime.now(timezone.utc))
        )
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount
```

**Reasoning:** Significantly improves performance for bulk operations.

### 5. Service Layer & Business Logic

**Current State:**

- Services instantiated as global singletons
- Mixed sync/async patterns
- Business logic scattered between routes and services
- No proper error handling in service methods
- Hardcoded configuration values

**Issues Identified:**

1. Global service instances prevent proper testing
2. ContentExtractionService has hardcoded Canvas URL
3. No circuit breaker for external API calls
4. Missing retry logic standardization
5. No caching layer for expensive operations

**Recommendations:**

1. **Remove hardcoded values and add configuration:**

```python
# Before
class ContentExtractionService:
    def __init__(self, canvas_token: str, course_id: int):
        self.canvas_base_url = "http://canvas-mock:8001/api/v1"  # Hardcoded!

# After
class ContentExtractionService:
    def __init__(self, canvas_token: str, course_id: int, canvas_base_url: str | None = None):
        self.canvas_base_url = canvas_base_url or str(settings.CANVAS_BASE_URL)
        # Remove /api/v1 if included in base URL
        if self.canvas_base_url.endswith('/api/v1'):
            self.canvas_base_url = self.canvas_base_url[:-7]
        self.canvas_base_url = f"{self.canvas_base_url}/api/v1"
```

**Reasoning:** Improves flexibility and removes environment-specific hardcoding.

2. **Implement circuit breaker for external APIs:**

```python
# services/circuit_breaker.py
from datetime import datetime, timedelta
import asyncio

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )

    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

# Usage in ContentExtractionService
class ContentExtractionService:
    def __init__(self, ...):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=httpx.HTTPError
        )

    async def _make_request_with_retry(self, url: str, headers: dict):
        return await self.circuit_breaker.call(
            self._make_actual_request, url, headers
        )
```

**Reasoning:** Prevents cascading failures and improves system resilience.

### 6. LangGraph Integration

**Current State:**

- Basic LangGraph workflow implementation
- No proper error recovery in workflow steps
- Synchronous LLM calls in async context
- No monitoring or observability
- Limited retry logic for LLM calls

**Issues Identified:**

1. No graceful degradation when LLM fails
2. Missing workflow state persistence
3. No cost tracking for LLM usage
4. Inefficient content chunking strategy
5. No caching of generated questions

**Recommendations:**

1. **Implement proper error recovery in workflow:**

```python
# Before
def should_continue_generation(self, state: MCQGenerationState) -> str:
    if state["error_message"] is not None:
        return "save_questions"  # Just stop

# After
from enum import Enum

class WorkflowAction(str, Enum):
    CONTINUE = "generate_question"
    RETRY_CHUNK = "retry_current_chunk"
    SKIP_CHUNK = "skip_to_next_chunk"
    SAVE = "save_questions"
    ERROR_RECOVERY = "error_recovery"

class MCQGenerationService:
    def __init__(self):
        self.max_chunk_retries = 3
        self.chunk_retry_counts = {}

    def should_continue_generation(self, state: MCQGenerationState) -> str:
        chunk_id = state["current_chunk_index"]

        # Check for errors
        if state.get("last_error"):
            retry_count = self.chunk_retry_counts.get(chunk_id, 0)

            if retry_count < self.max_chunk_retries:
                self.chunk_retry_counts[chunk_id] = retry_count + 1
                return WorkflowAction.RETRY_CHUNK
            else:
                # Skip this chunk and continue
                state["current_chunk_index"] += 1
                return WorkflowAction.SKIP_CHUNK

        # Normal flow
        if state["questions_generated"] >= state["target_question_count"]:
            return WorkflowAction.SAVE

        if state["current_chunk_index"] >= len(state["content_chunks"]):
            return WorkflowAction.SAVE

        return WorkflowAction.CONTINUE

    async def error_recovery(self, state: MCQGenerationState) -> MCQGenerationState:
        """Handle error recovery with fallback strategies"""
        error_type = state.get("last_error_type")

        if error_type == "rate_limit":
            # Wait and retry
            await asyncio.sleep(60)
            state["retry_after_recovery"] = True
        elif error_type == "content_too_long":
            # Split chunk further
            current_chunk = state["content_chunks"][state["current_chunk_index"]]
            smaller_chunks = self._split_chunk(current_chunk, max_size=1500)
            # Insert smaller chunks
            state["content_chunks"][state["current_chunk_index"]:state["current_chunk_index"]+1] = smaller_chunks

        state["last_error"] = None
        state["last_error_type"] = None
        return state
```

**Reasoning:** Provides resilient workflow execution with proper error handling.

2. **Add workflow state persistence:**

```python
# models.py
class WorkflowState(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: UUID = Field(foreign_key="quiz.id", index=True)
    workflow_type: str
    state_data: dict[str, Any] = Field(sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    status: str  # running, completed, failed, paused

# services/mcq_generation.py
class MCQGenerationService:
    async def save_workflow_state(
        self,
        session: Session,
        quiz_id: UUID,
        state: MCQGenerationState
    ):
        workflow_state = session.exec(
            select(WorkflowState)
            .where(WorkflowState.quiz_id == quiz_id)
            .where(WorkflowState.workflow_type == "mcq_generation")
            .where(WorkflowState.status == "running")
        ).first()

        if not workflow_state:
            workflow_state = WorkflowState(
                quiz_id=quiz_id,
                workflow_type="mcq_generation",
                state_data=state,
                status="running"
            )
            session.add(workflow_state)
        else:
            workflow_state.state_data = state
            workflow_state.updated_at = datetime.utcnow()

        session.commit()

    async def resume_workflow(self, quiz_id: UUID) -> MCQGenerationState | None:
        """Resume interrupted workflow from saved state"""
        with Session(engine) as session:
            workflow_state = session.exec(
                select(WorkflowState)
                .where(WorkflowState.quiz_id == quiz_id)
                .where(WorkflowState.workflow_type == "mcq_generation")
                .where(WorkflowState.status == "running")
                .order_by(desc(WorkflowState.created_at))
            ).first()

            if workflow_state:
                return workflow_state.state_data
            return None
```

**Reasoning:** Allows workflows to be resumed after failures or system restarts.

### 7. Security, Error Handling, and Logging

**Current State:**

- Basic JWT authentication
- Structured logging with appropriate detail
- Token encryption for Canvas tokens
- Some error handling inconsistencies
- No rate limiting implementation

**Issues Identified:**

1. No rate limiting on API endpoints
2. Missing request ID correlation
3. Some sensitive data might be logged
4. No API key authentication option
5. Missing security headers

**Recommendations:**

1. **Implement rate limiting:**

```python
# middleware/rate_limit.py
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        self._cleanup_task = None

    async def check_rate_limit(self, key: str) -> bool:
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > minute_ago
        ]

        if len(self.requests[key]) >= self.requests_per_minute:
            return False

        self.requests[key].append(now)
        return True

# middleware/rate_limit_middleware.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Use IP + user ID as key
        client_ip = request.client.host
        user_id = request.state.user_id if hasattr(request.state, "user_id") else "anonymous"
        rate_limit_key = f"{client_ip}:{user_id}"

        if not await self.rate_limiter.check_rate_limit(rate_limit_key):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )

        response = await call_next(request)
        return response

# In main.py
rate_limiter = RateLimiter(requests_per_minute=60)
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
```

**Reasoning:** Prevents API abuse and ensures fair usage.

2. **Add request ID correlation:**

```python
# middleware/request_id.py
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Add to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        structlog.contextvars.unbind_contextvars("request_id")
        return response

# Update logging to include request_id automatically
```

**Reasoning:** Enables tracking requests across services and logs.

## Refactoring Roadmap

### Phase 1 - Critical Issues (1-2 weeks)

1. **Fix circular dependency** between security and auth modules
2. **Configure database connection pooling** with proper settings
3. **Remove hardcoded URLs** from ContentExtractionService
4. **Implement proper session management** in background tasks
5. **Add missing database indexes** for performance
6. **Fix transaction boundaries** in background tasks

### Phase 2 - Performance Optimizations (2-3 weeks)

1. **Implement repository pattern** with bulk operations
2. **Add caching layer** for expensive operations
3. **Optimize N+1 queries** with eager loading
4. **Implement pagination** on all list endpoints
5. **Add circuit breaker** for external API calls
6. **Convert JSON string fields** to native JSON columns

### Phase 3 - Code Quality Improvements (3-4 weeks)

1. **Implement dependency injection** for all services
2. **Add comprehensive error recovery** in LangGraph workflow
3. **Implement workflow state persistence**
4. **Add rate limiting middleware**
5. **Implement request ID correlation**
6. **Refactor CRUD into domain repositories**
7. **Add API versioning strategy**
8. **Implement comprehensive testing**

## Best Practices Checklist

- ✅ SOLID principles adherence - Needs improvement in Single Responsibility
- ✅ DRY (Don't Repeat Yourself) - Some duplication in route handlers
- ✅ Proper async/await usage - Generally good, some improvements needed
- ✅ Comprehensive error handling - Good structured logging, needs consistency
- ⚠️ Security best practices - Missing rate limiting and some headers
- ⚠️ Performance optimization - Missing indexes and connection pooling
- ⚠️ Testing coverage - Limited test coverage observed

## Answers to Specific Questions

1. **Are there any circular dependencies between modules?**

   - Yes, potential circular dependency between `core/security.py` and `api/routes/auth.py`

2. **Is the database session management optimized for concurrent requests?**

   - No, using default connection pool settings which may cause issues under load

3. **Are background tasks properly implemented for long-running operations?**

   - Partially, but session management in background tasks needs improvement

4. **Is the LangGraph integration following async patterns correctly?**

   - Yes, but could benefit from better error recovery and state persistence

5. **Are there any security vulnerabilities in the current implementation?**

   - Missing rate limiting, potential for resource exhaustion

6. **Can any CRUD operations be optimized with bulk operations?**

   - Yes, question creation and approval can use bulk operations

7. **Is proper caching implemented where appropriate?**

   - No caching layer implemented currently

8. **Are API responses consistent and following a standard format?**
   - Mostly consistent, but pagination is missing on list endpoints

## Conclusion

The codebase shows good foundational patterns with structured logging and clean separation of concerns. However, it requires significant refactoring to address scalability, maintainability, and reliability concerns. The recommended phased approach allows for incremental improvements while maintaining system stability.

Priority should be given to fixing the critical issues in Phase 1, particularly the database connection pooling and circular dependency issues, as these pose immediate risks to system stability and scalability.
