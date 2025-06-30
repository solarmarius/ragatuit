# Backend Refactoring Plan: Modular Feature-Based Architecture

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Proposed Structure Overview](#proposed-structure-overview)
4. [Feature Module Template](#feature-module-template)
5. [Implementation Plan](#implementation-plan)
6. [Risk Assessment and Mitigation](#risk-assessment-and-mitigation)
7. [Success Metrics](#success-metrics)

## Executive Summary

This document outlines a comprehensive plan to refactor the Rag@UiT backend from its current monolithic structure to a modular, feature-based architecture. The refactoring aims to improve maintainability, scalability, and developer productivity while maintaining all existing functionality.

## Current State Analysis

### Pain Points Identified

1. **Monolithic Models**: All SQLModel entities and Pydantic schemas in single `models.py` (400+ lines)
2. **Centralized CRUD**: All database operations in single `crud.py` file
3. **Flat Service Structure**: Services organized without clear feature boundaries
4. **Mixed Concerns**: Business logic scattered between routes, services, and CRUD operations
5. **Limited Modularity**: Difficult to add/remove features without affecting other parts
6. **Testing Complexity**: Tests mirror source structure but lack feature cohesion
7. **Dependency Management**: No clear dependency injection pattern for services

### Current Structure

```
backend/app/
├── api/
│   ├── routes/        # API endpoints
│   └── deps.py        # Shared dependencies
├── core/              # Core utilities
├── services/          # Business logic (flat)
├── crud.py           # All DB operations
├── models.py         # All models/schemas
└── tests/            # Test mirror structure
```

## Proposed Structure Overview

### New Directory Structure

```
backend/app/
├── common/                      # Shared/cross-cutting concerns
│   ├── __init__.py
│   ├── models/                  # Base models and mixins
│   │   ├── __init__.py
│   │   ├── base.py             # TimestampMixin, UUIDMixin
│   │   └── pagination.py       # Pagination schemas
│   ├── database/               # Database configuration
│   │   ├── __init__.py
│   │   ├── session.py          # Session management
│   │   └── migrations/         # Alembic migrations
│   ├── exceptions/             # Global exceptions
│   │   ├── __init__.py
│   │   ├── base.py            # Base exception classes
│   │   └── handlers.py        # Exception handlers
│   ├── middleware/             # Global middleware
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   └── auth.py
│   └── utils/                  # Shared utilities
│       ├── __init__.py
│       ├── security.py
│       └── retry.py
├── features/                   # Feature modules
│   ├── __init__.py
│   ├── auth/                   # Authentication feature
│   │   ├── __init__.py
│   │   ├── models.py          # Auth-specific models
│   │   ├── schemas.py         # Request/response schemas
│   │   ├── service.py         # Business logic
│   │   ├── repository.py      # Data access layer
│   │   ├── router.py          # API endpoints
│   │   ├── dependencies.py    # Feature dependencies
│   │   ├── exceptions.py      # Feature exceptions
│   │   └── constants.py       # Feature constants
│   ├── users/                  # User management
│   │   └── ... (same structure)
│   ├── canvas/                 # Canvas integration
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── services/          # Multiple services
│   │   │   ├── __init__.py
│   │   │   ├── auth.py        # Canvas OAuth
│   │   │   ├── content.py     # Content extraction
│   │   │   └── export.py      # Quiz export
│   │   ├── repository.py
│   │   ├── router.py
│   │   └── dependencies.py
│   ├── quiz/                   # Quiz management
│   │   └── ... (same structure)
│   └── questions/              # Question management
│       └── ... (same structure)
├── config/                     # Configuration
│   ├── __init__.py
│   ├── settings.py            # Pydantic settings
│   └── logging.py             # Logging config
├── main.py                    # Application entry
└── tests/                     # Test organization
    ├── unit/                  # Unit tests by feature
    │   ├── auth/
    │   ├── users/
    │   └── ...
    ├── integration/           # Integration tests
    └── e2e/                  # End-to-end tests
```

### Architecture Principles

1. **Feature-First Organization**: Each feature is self-contained with its own models, services, and routes
2. **Layered Architecture**: Clear separation between API, Service, and Repository layers
3. **Dependency Injection**: Services use dependency injection for better testability
4. **Domain-Driven Design**: Features represent business domains
5. **SOLID Principles**: Single responsibility, open/closed, interface segregation

## Inter-Feature Communication Strategy

### Communication Patterns

The modular architecture requires clear patterns for inter-feature communication while maintaining loose coupling. We'll implement a hybrid approach:

#### 1. Direct Service Dependencies (Primary Pattern)

For synchronous, tightly-related operations where one feature directly depends on another:

```python
# features/quiz/service.py
from app.features.users.service import UserService
from app.features.canvas.services.content import ContentExtractionService

class QuizService:
    def __init__(
        self,
        repository: QuizRepository,
        user_service: UserService,
        content_service: ContentExtractionService
    ):
        self.repository = repository
        self.user_service = user_service
        self.content_service = content_service

    async def create_quiz_with_content(self, user_id: UUID, quiz_data: QuizCreate):
        # Verify user exists and has permissions
        user = await self.user_service.get_user(user_id)

        # Create quiz
        quiz = await self.repository.create(quiz_data)

        # Extract content asynchronously
        await self.content_service.extract_for_quiz(quiz.id)

        return quiz
```

**When to use**:

- Synchronous operations
- Strong business coupling
- Transactional requirements

#### 2. Event-Driven Communication (Secondary Pattern)

For asynchronous, loosely-coupled operations using an internal event bus:

```python
# common/events/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Callable

class Event(ABC):
    """Base event class"""
    pass

class EventBus:
    """Simple in-memory event bus for development"""
    def __init__(self):
        self._handlers: Dict[type, List[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: Event):
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            await handler(event)

# features/quiz/events.py
from app.common.events.base import Event

class QuizCreatedEvent(Event):
    def __init__(self, quiz_id: UUID, user_id: UUID):
        self.quiz_id = quiz_id
        self.user_id = user_id

# features/questions/handlers.py
async def handle_quiz_created(event: QuizCreatedEvent):
    """Generate initial questions when quiz is created"""
    # Trigger question generation asynchronously
    pass
```

**When to use**:

- Asynchronous operations
- Loose coupling required
- Fire-and-forget scenarios
- Multiple subscribers to same event

**Future Migration Path**: The event bus can be replaced with RabbitMQ/Kafka for production scalability.

#### 3. Shared Domain Services (Tertiary Pattern)

For truly cross-cutting business logic that doesn't belong to any single feature:

```python
# common/services/llm_service.py
class LLMService:
    """Shared service for LLM operations used by multiple features"""

    async def generate_content(self, prompt: str, config: LLMConfig) -> str:
        # Common LLM logic used by quiz, questions, etc.
        pass

# common/services/canvas_client.py
class CanvasAPIClient:
    """Shared Canvas API client used by multiple features"""

    async def fetch_course_content(self, course_id: int) -> CourseContent:
        # Common Canvas API logic
        pass
```

### Communication Guidelines

1. **Prefer Direct Dependencies** for core business flows
2. **Use Events** for notifications and side effects
3. **Extract Shared Services** only when logic is truly generic
4. **Avoid Circular Dependencies** by careful service design
5. **Document Integration Points** in each feature's README

### Dependency Graph

```
┌─────────────┐     ┌─────────────┐
│    Auth     │────▶│    Users    │
└─────────────┘     └─────────────┘
                           │
                           ▼
┌─────────────┐     ┌─────────────┐
│   Canvas    │────▶│    Quiz     │
└─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Questions  │
                    └─────────────┘
```

## Cross-Cutting Concerns Implementation

### Structured Logging

**Library**: `structlog` for structured logging with context propagation

```python
# common/logging/config.py
import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

def configure_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# common/logging/context.py
import contextvars
from typing import Dict, Any

request_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "request_context", default={}
)

class LoggingContextMiddleware:
    """Middleware to inject request context into all logs"""

    async def __call__(self, request: Request, call_next):
        context = {
            "request_id": str(uuid.uuid4()),
            "method": request.method,
            "path": request.url.path,
            "user_id": getattr(request.state, "user_id", None)
        }

        token = request_context.set(context)
        try:
            response = await call_next(request)
            return response
        finally:
            request_context.reset(token)

# Feature usage example
# features/quiz/service.py
import structlog

logger = structlog.get_logger(__name__)

class QuizService:
    async def create_quiz(self, data: QuizCreate) -> Quiz:
        logger.info("creating_quiz", quiz_title=data.title, question_count=data.question_count)

        try:
            quiz = await self.repository.create(data)
            logger.info("quiz_created", quiz_id=str(quiz.id))
            return quiz
        except Exception as e:
            logger.error("quiz_creation_failed", error=str(e), exc_info=True)
            raise
```

### Metrics and Monitoring

**Library**: `prometheus-client` for metrics collection and exposure

```python
# common/metrics/config.py
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from functools import wraps
import time

# Global metrics registry
registry = CollectorRegistry()

# Define common metrics
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    registry=registry
)

active_users = Gauge(
    "active_users_total",
    "Total active users",
    registry=registry
)

# Decorator for timing operations
def track_time(metric_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                operation_duration.labels(operation=metric_name).observe(duration)
                return result
            except Exception as e:
                operation_errors.labels(operation=metric_name).inc()
                raise
        return wrapper
    return decorator

# common/metrics/middleware.py
class MetricsMiddleware:
    async def __call__(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response

# Feature usage
# features/quiz/service.py
from app.common.metrics.config import track_time

class QuizService:
    @track_time("quiz_creation")
    async def create_quiz(self, data: QuizCreate) -> Quiz:
        # Implementation
        pass
```

### Advanced Error Handling

**Pattern**: Layered exception handling with context preservation

```python
# common/exceptions/base.py
from typing import Optional, Dict, Any
from datetime import datetime

class BaseError(Exception):
    """Base exception with context support"""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.context = context or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "timestamp": self.timestamp.isoformat(),
                "context": self.context
            }
        }

# common/exceptions/handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler with logging and metrics"""

    if isinstance(exc, BaseError):
        logger.error(
            "business_error",
            error_code=exc.error_code,
            message=exc.message,
            context=exc.context,
            status_code=exc.status_code
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )

    # Unexpected errors
    logger.exception("unhandled_exception", exc_info=exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )

# Feature-specific exceptions
# features/quiz/exceptions.py
from app.common.exceptions.base import BaseError

class QuizNotFoundError(BaseError):
    def __init__(self, quiz_id: UUID):
        super().__init__(
            message=f"Quiz not found",
            error_code="QUIZ_NOT_FOUND",
            status_code=404,
            context={"quiz_id": str(quiz_id)}
        )

class QuizLimitExceededError(BaseError):
    def __init__(self, user_id: UUID, limit: int):
        super().__init__(
            message=f"Quiz limit exceeded",
            error_code="QUIZ_LIMIT_EXCEEDED",
            status_code=429,
            context={"user_id": str(user_id), "limit": limit}
        )
```

### Integration Example

```python
# main.py
from fastapi import FastAPI
from app.common.logging.config import configure_logging
from app.common.logging.context import LoggingContextMiddleware
from app.common.metrics.middleware import MetricsMiddleware
from app.common.exceptions.handlers import global_exception_handler

# Configure logging before app creation
configure_logging()

app = FastAPI()

# Add middleware in correct order
app.add_middleware(LoggingContextMiddleware)
app.add_middleware(MetricsMiddleware)

# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest
    from app.common.metrics.config import registry
    return Response(generate_latest(registry), media_type="text/plain")
```

## Feature Module Template

### Standard Feature Structure

Each feature module should follow this template:

```python
# features/example_feature/__init__.py
from .router import router
from .service import ExampleService
from .models import ExampleModel

__all__ = ["router", "ExampleService", "ExampleModel"]
```

```python
# features/example_feature/models.py
from sqlmodel import SQLModel, Field
from app.common.models.base import TimestampMixin, UUIDMixin

class ExampleBase(SQLModel):
    """Shared properties"""
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None)

class Example(ExampleBase, UUIDMixin, TimestampMixin, table=True):
    """Database model"""
    __tablename__ = "examples"

    # Relationships
    owner_id: UUID = Field(foreign_key="users.id", index=True)
```

```python
# features/example_feature/schemas.py
from pydantic import BaseModel
from .models import ExampleBase

class ExampleCreate(ExampleBase):
    """Request schema for creation"""
    pass

class ExampleUpdate(BaseModel):
    """Request schema for updates"""
    name: str | None = None
    description: str | None = None

class ExampleResponse(ExampleBase):
    """Response schema"""
    id: UUID
    created_at: datetime
    updated_at: datetime
```

```python
# features/example_feature/repository.py
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Example
from .schemas import ExampleCreate, ExampleUpdate

class ExampleRepository:
    """Data access layer for examples"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: ExampleCreate) -> Example:
        example = Example.model_validate(data)
        self.session.add(example)
        await self.session.commit()
        await self.session.refresh(example)
        return example

    async def get_by_id(self, id: UUID) -> Example | None:
        return await self.session.get(Example, id)

    async def update(self, id: UUID, data: ExampleUpdate) -> Example | None:
        example = await self.get_by_id(id)
        if not example:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(example, field, value)

        await self.session.commit()
        await self.session.refresh(example)
        return example
```

```python
# features/example_feature/service.py
from app.common.exceptions import NotFoundError
from .repository import ExampleRepository
from .schemas import ExampleCreate, ExampleUpdate
from .exceptions import ExampleNotFoundError

class ExampleService:
    """Business logic for examples"""

    def __init__(self, repository: ExampleRepository):
        self.repository = repository

    async def create_example(self, data: ExampleCreate) -> Example:
        # Business logic validations
        return await self.repository.create(data)

    async def get_example(self, id: UUID) -> Example:
        example = await self.repository.get_by_id(id)
        if not example:
            raise ExampleNotFoundError(f"Example {id} not found")
        return example
```

```python
# features/example_feature/router.py
from fastapi import APIRouter, Depends, status
from .dependencies import get_example_service
from .schemas import ExampleCreate, ExampleResponse
from .service import ExampleService

router = APIRouter(prefix="/examples", tags=["examples"])

@router.post("/", response_model=ExampleResponse, status_code=status.HTTP_201_CREATED)
async def create_example(
    data: ExampleCreate,
    service: ExampleService = Depends(get_example_service)
) -> ExampleResponse:
    """Create a new example"""
    example = await service.create_example(data)
    return ExampleResponse.model_validate(example)
```

```python
# features/example_feature/dependencies.py
from fastapi import Depends
from app.common.database.session import get_session
from .repository import ExampleRepository
from .service import ExampleService

async def get_example_repository(
    session: AsyncSession = Depends(get_session)
) -> ExampleRepository:
    return ExampleRepository(session)

async def get_example_service(
    repository: ExampleRepository = Depends(get_example_repository)
) -> ExampleService:
    return ExampleService(repository)
```

## Implementation Plan

### Phase 1: Foundation and Prerequisites (Week 1-2)

**Objectives**: Set up the new structure and core utilities

**Tasks**:

1. Create new directory structure
2. Implement common utilities and base classes
   - Base models with mixins (TimestampMixin, UUIDMixin)
   - Database session management
   - Global exception handlers
   - Shared middleware
3. Set up dependency injection patterns
4. Update configuration management
5. Create feature module template and documentation

**Deliverables**:

- New directory structure in place
- Common utilities implemented
- Developer guide for feature modules
- CI/CD pipeline updates

### Phase 2: Core Features Migration (Week 3-4)

**Objectives**: Migrate 2-3 core features as proof of concept

**Priority Features**:

1. **Auth Feature** (Critical path)
   - Move authentication logic
   - Separate Canvas OAuth from local auth
   - Implement auth service and repository
2. **Users Feature** (Depends on Auth)

   - User CRUD operations
   - Profile management
   - Token management

3. **Canvas Integration** (Independent)
   - OAuth service
   - Content extraction service
   - Canvas API client

**Process**:

1. Create feature directory
2. Extract and refactor models
3. Implement repository layer
4. Refactor business logic into services
5. Update routes to use new services
6. Write comprehensive tests
7. Update imports across codebase

### Phase 3: Systematic Feature Migration (Week 5-8)

**Objectives**: Migrate remaining features systematically

**Migration Order**:

1. **Quiz Feature** (Week 5)
   - Complex feature with multiple services
   - Depends on Users and Canvas
2. **Questions Feature** (Week 6)
   - Depends on Quiz
   - MCQ generation service integration
3. **Utils/Admin Features** (Week 7)
   - Health checks
   - Admin endpoints
   - Monitoring

**Parallel Work**:

- Update test suite structure
- Refactor integration tests
- Documentation updates

### Phase 4: Legacy Code Cleanup (Week 9)

**Objectives**: Remove old code and finalize migration

**Tasks**:

1. Delete old monolithic files
   - Remove `crud.py`
   - Remove old `models.py`
   - Clean up old service structure
2. Update all imports
3. Run comprehensive test suite
4. Performance testing
5. Code quality checks

### Phase 5: Documentation and Knowledge Transfer (Week 10)

**Objectives**: Ensure team adoption and understanding

**Deliverables**:

1. Updated technical documentation
2. Architecture decision records (ADRs)
3. Developer onboarding guide
4. Feature development guide
5. Team training sessions

## Risk Assessment and Mitigation

### Identified Risks

1. **Development Disruption**

   - **Risk**: Ongoing feature development blocked
   - **Mitigation**:
     - Feature branches for refactoring
     - Incremental migration
     - Clear communication of changes

2. **Breaking Changes**

   - **Risk**: API compatibility issues
   - **Mitigation**:
     - Maintain API contracts
     - Comprehensive API tests
     - Gradual deprecation of old endpoints

3. **Data Migration Issues**

   - **Risk**: Database schema conflicts
   - **Mitigation**:
     - Careful migration planning
     - Backup strategies
     - Rollback procedures

4. **Team Resistance**

   - **Risk**: Developers uncomfortable with new structure
   - **Mitigation**:
     - Early involvement in design
     - Comprehensive documentation
     - Pair programming during migration

5. **Performance Regression**
   - **Risk**: New structure introduces latency
   - **Mitigation**:
     - Performance benchmarks
     - Load testing
     - Optimization phase

### Contingency Plans

1. **Rollback Strategy**: Git branches allow full rollback if needed
2. **Partial Migration**: Can pause at any phase if issues arise
3. **Hybrid Approach**: Old and new structures can coexist temporarily

## Success Metrics

### Quantitative Metrics

1. **Code Quality**

   - Reduced cyclomatic complexity (target: <10 per function)
   - Increased test coverage (target: >90%)
   - Reduced code duplication (target: <5%)

2. **Development Velocity**

   - Feature development time reduced by 30%
   - Bug fix time reduced by 40%
   - Onboarding time for new developers reduced by 50%

3. **Performance**
   - API response time maintained or improved
   - Database query optimization
   - Memory usage optimization

### Qualitative Metrics

1. **Developer Satisfaction**

   - Survey before and after refactoring
   - Code review feedback
   - Team productivity assessment

2. **Maintainability**

   - Ease of adding new features
   - Clear separation of concerns
   - Reduced coupling between modules

3. **Documentation Quality**
   - Comprehensive API documentation
   - Clear architecture documentation
   - Up-to-date developer guides

### Measurement Timeline

- **Baseline**: Measure all metrics before refactoring
- **Phase 2**: Measure after core features migration
- **Phase 4**: Final measurement after cleanup
- **3 Months Post**: Long-term impact assessment

## Conclusion

This refactoring plan provides a structured approach to modernizing the Rag@UiT backend architecture. By adopting a modular, feature-based structure, we will achieve better maintainability, scalability, and developer productivity. The phased approach minimizes risk while ensuring continuous delivery of value.

The success of this refactoring depends on clear communication, careful planning, and team commitment. With the application not yet deployed, we have a unique opportunity to implement these changes without legacy constraints, setting a strong foundation for future growth.
