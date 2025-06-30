# Backend Refactoring Plan: Adopting FastAPI Best Practices Structure

## Executive Summary

This document outlines a comprehensive plan to refactor our Rag@UiT backend from its current structure to the **exact modular, feature-based structure** recommended in the [FastAPI best practices guide](https://github.com/zhanymkanov/fastapi-best-practices). The refactoring will transform our monolithic models and CRUD operations into a clean, domain-driven architecture.

## A. Adopting the Guide's Structure

### Current vs. Target Structure Mapping

Our new structure will **exactly match** the guide's recommended layout:

```
backend/
├── alembic/                    # Database migrations (existing)
├── app/
│   ├── auth/                   # Authentication domain
│   │   ├── router.py          # OAuth endpoints, token management
│   │   ├── schemas.py         # TokenPayload, CanvasTokens, etc.
│   │   ├── models.py          # User model with Canvas integration
│   │   ├── dependencies.py    # Auth dependencies (get_current_user)
│   │   ├── config.py          # Auth-specific settings
│   │   ├── constants.py       # JWT settings, OAuth URLs
│   │   ├── exceptions.py      # AuthenticationError, TokenExpired
│   │   ├── service.py         # CanvasAuthService logic
│   │   └── utils.py           # Token encryption, JWT handling
│   │
│   ├── quiz/                   # Quiz management domain
│   │   ├── router.py          # Quiz CRUD endpoints
│   │   ├── schemas.py         # QuizCreate, QuizResponse, etc.
│   │   ├── models.py          # Quiz SQLModel
│   │   ├── dependencies.py    # Quiz-specific deps
│   │   ├── config.py          # Quiz configuration
│   │   ├── constants.py       # Quiz statuses, limits
│   │   ├── exceptions.py      # QuizNotFound, InvalidStatus
│   │   ├── service.py         # Quiz business logic
│   │   └── utils.py           # Quiz helpers
│   │
│   ├── question/               # Question management domain
│   │   ├── router.py          # Question CRUD, approval
│   │   ├── schemas.py         # QuestionCreate, QuestionUpdate
│   │   ├── models.py          # Question SQLModel
│   │   ├── dependencies.py    # Question dependencies
│   │   ├── config.py          # Question settings
│   │   ├── constants.py       # Question types, statuses
│   │   ├── exceptions.py      # QuestionNotFound, etc.
│   │   ├── service.py         # MCQGenerationService
│   │   └── utils.py           # Question formatting
│   │
│   ├── canvas/                 # Canvas LMS integration
│   │   ├── router.py          # Course/module endpoints
│   │   ├── schemas.py         # CanvasCourse, CanvasModule
│   │   ├── models.py          # Canvas-related models
│   │   ├── dependencies.py    # Canvas client deps
│   │   ├── config.py          # Canvas API settings
│   │   ├── constants.py       # API endpoints, limits
│   │   ├── exceptions.py      # CanvasAPIError, etc.
│   │   ├── service.py         # ContentExtraction, QuizExport
│   │   └── utils.py           # URL builders, API helpers
│   │
│   ├── config.py              # Global app configuration
│   ├── main.py                # FastAPI app initialization
│   ├── database.py            # Database connection setup
│   ├── exceptions.py          # Global exceptions
│   ├── models.py              # Global models
│   ├── logging_config.py.     # Logging
│   └── middleware/            # App-wide middleware
│       ├── logging.py
│       └── cors.py
│
├── tests/                      # Test suite (restructured)
│   ├── auth/
│   ├── quiz/
│   ├── question/
│   └── canvas/
│
│
└── scripts/                    # Utility scripts
```

### Component Migration Mapping

| Current Location                     | New Location                       | Notes                      |
| ------------------------------------ | ---------------------------------- | -------------------------- |
| `app/models.py` → User               | `src/auth/models.py`               | Extract User model only    |
| `app/models.py` → TokenPayload       | `src/auth/schemas.py`              | Authentication schemas     |
| `app/crud.py` → User CRUD            | `src/auth/service.py`              | User operations as service |
| `app/api/routes/auth.py`             | `src/auth/router.py`               | Keep route structure       |
| `app/services/canvas_auth.py`        | `src/auth/service.py`              | Merge into auth service    |
| `app/models.py` → Quiz               | `src/quiz/models.py`               | Extract Quiz model         |
| `app/crud.py` → Quiz CRUD            | `src/quiz/service.py`              | Quiz operations            |
| `app/api/routes/quiz.py`             | `src/quiz/router.py`               | Quiz endpoints             |
| `app/models.py` → Question           | `src/question/models.py`           | Extract Question model     |
| `app/services/mcq_generation.py`     | `src/question/service.py`          | Generation logic           |
| `app/api/routes/canvas.py`           | `src/canvas/router.py`             | Canvas endpoints           |
| `app/services/content_extraction.py` | `src/canvas/service.py`            | Extraction logic           |
| `app/core/*`                         | `src/config.py`, `src/middleware/` | Split by concern           |

## B. Feature Module Implementation (Following the Guide)

### Example: Authentication Module Structure

```python
# src/auth/router.py
from fastapi import APIRouter, Depends
from .schemas import LoginRequest, TokenResponse
from .service import AuthService
from .dependencies import get_auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    return await service.canvas_oauth_login(request)

# src/auth/schemas.py
from pydantic import BaseModel
from datetime import datetime

class TokenPayload(BaseModel):
    sub: int
    exp: datetime
    canvas_user_id: int

class CanvasTokens(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime

# src/auth/models.py
from sqlmodel import SQLModel, Field
from datetime import datetime

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int = Field(primary_key=True)
    canvas_user_id: int = Field(unique=True, index=True)
    email: str
    full_name: str
    encrypted_canvas_token: str | None
    encrypted_refresh_token: str | None
    canvas_token_expires_at: datetime | None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# src/auth/service.py
from typing import Optional
from sqlmodel import Session, select
from .models import User
from .schemas import CanvasTokens
from .utils import encrypt_token, decrypt_token
from ..database import get_session

class AuthService:
    def __init__(self, session: Session):
        self.session = session

    async def create_user(self, user_data: dict) -> User:
        user = User(**user_data)
        self.session.add(user)
        self.session.commit()
        return user

    async def update_canvas_tokens(self, user_id: int, tokens: CanvasTokens) -> User:
        user = self.session.get(User, user_id)
        user.encrypted_canvas_token = encrypt_token(tokens.access_token)
        user.encrypted_refresh_token = encrypt_token(tokens.refresh_token)
        user.canvas_token_expires_at = tokens.expires_at
        self.session.commit()
        return user

# src/auth/dependencies.py
from fastapi import Depends, HTTPException
from sqlmodel import Session
from .service import AuthService
from ..database import get_session

def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(session)

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Token validation logic
    pass
```

### Module Interaction Pattern

```python
# Cross-module dependency example
# src/quiz/service.py
from ..auth.models import User
from ..canvas.service import CanvasService
from .models import Quiz

class QuizService:
    def __init__(self, session: Session, canvas_service: CanvasService):
        self.session = session
        self.canvas_service = canvas_service

    async def create_quiz_from_canvas(self, user: User, course_id: str) -> Quiz:
        # Fetch content using canvas service
        content = await self.canvas_service.extract_course_content(
            user.canvas_tokens,
            course_id
        )
        # Create quiz with extracted content
        quiz = Quiz(user_id=user.id, content=content)
        self.session.add(quiz)
        self.session.commit()
        return quiz
```

## C. Implementation Plan

### Phase 1: Foundation - Create the Guide's Structure (Week 1)

**Objectives:**

- Set up exact directory structure from the guide
- Create core infrastructure files
- Establish import patterns

**Tasks:**

1. Create `src/` directory structure

   ```bash
   mkdir -p src/{auth,quiz,question,canvas}/{router,schemas,models,dependencies,config,constants,exceptions,service,utils}
   ```

2. Move core infrastructure:

   - `app/core/config.py` → `src/config.py`
   - `app/core/db.py` → `src/database.py`
   - Create `src/main.py` with minimal app setup

3. Set up module `__init__.py` files with proper exports

4. Update import paths in `pyproject.toml`:
   ```toml
   [tool.poetry]
   packages = [{include = "src"}]
   ```

**Timeline:** 3-4 days
**Resources:** 1 senior developer

### Phase 2: Core Migration Following the Guide's Patterns (Week 2-3)

**Objectives:**

- Migrate authentication module completely
- Establish patterns for other modules
- Ensure all tests pass

**Tasks:**

1. **Auth Module Migration (Days 1-3)**

   - Extract User model from `models.py`
   - Split auth schemas into `auth/schemas.py`
   - Move auth CRUD to `auth/service.py`
   - Migrate auth routes maintaining API compatibility
   - Create auth-specific exceptions and constants
   - Update all auth tests

2. **Canvas Module Migration (Days 4-6)**

   - Extract Canvas models and schemas
   - Consolidate Canvas services
   - Create Canvas-specific configuration
   - Migrate Canvas routes
   - Update Canvas tests

3. **Pattern Validation (Days 7-8)**
   - Review migrated modules against guide
   - Document patterns for remaining modules
   - Create migration checklist

**Timeline:** 8 days
**Resources:** 2 developers

### Phase 3: Complete Migration to Guide's Structure (Week 4-5)

**Objectives:**

- Migrate remaining modules
- Ensure zero deviation from guide structure
- Maintain backward compatibility

**Tasks:**

1. **Quiz Module Migration (Days 1-3)**

   - Extract Quiz model and schemas
   - Create Quiz service from CRUD operations
   - Implement Quiz router
   - Add transaction management in service layer
   - Update Quiz tests

2. **Question Module Migration (Days 4-6)**

   - Extract Question model and schemas
   - Merge MCQ generation into Question service
   - Create Question router with approval workflow
   - Implement Question-specific utilities
   - Update Question tests

3. **Cross-Module Integration (Days 7-8)**
   - Update dependency injection patterns
   - Ensure proper service composition
   - Validate all module interactions
   - Performance testing

**Timeline:** 8 days
**Resources:** 2 developers

### Phase 4: Validation and Cleanup (Week 6)

**Objectives:**

- Remove old structure completely
- Validate against guide requirements
- Update all documentation

**Tasks:**

1. **Structure Validation (Days 1-2)**

   - Compare final structure with guide
   - Ensure all naming conventions match
   - Validate module boundaries
   - Check for any deviations

2. **Legacy Cleanup (Days 3-4)**

   - Remove old `app/` structure
   - Delete monolithic `models.py` and `crud.py`
   - Update all import statements
   - Clean up unused dependencies

3. **Testing Suite (Days 5-6)**
   - Run full test suite
   - Update test structure to match modules
   - Add integration tests for new structure
   - Performance benchmarking

**Timeline:** 6 days
**Resources:** 1 senior developer, 1 QA engineer

### Phase 5: Documentation Alignment (Week 7)

**Objectives:**

- Create comprehensive documentation
- Update development guides
- Train team on new structure

**Tasks:**

1. **Technical Documentation (Days 1-3)**

   - Create module documentation
   - Document service interfaces
   - Update API documentation
   - Create dependency graphs

2. **Developer Guides (Days 4-5)**
   - Update CLAUDE.md with new structure
   - Create "Adding a New Feature" guide
   - Document testing patterns
   - Update CI/CD configurations

**Timeline:** 5 days
**Resources:** 1 developer, 1 technical writer

## D. Centralized Logging Strategy

### Overview

A consistent logging strategy across all modules is essential for debugging, monitoring, and maintaining the modular architecture. This strategy ensures that logs are structured, contextual, and traceable across service boundaries.

### Core Logging Components

#### 1. **Logger Factory Pattern**

```python
# src/logging_config.py
import logging
import sys
from contextvars import ContextVar
from typing import Optional
import structlog
from pythonjsonlogger import jsonlogger

# Context variable for request tracking
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_context: ContextVar[Optional[int]] = ContextVar('user_id', default=None)

def get_logger(name: str) -> structlog.BoundLogger:
    """
    Factory function to create module-specific loggers with consistent configuration.

    Usage:
        from src.logging_config import get_logger
        logger = get_logger(__name__)
    """
    return structlog.get_logger(name)

def configure_logging(log_level: str = "INFO", json_logs: bool = True):
    """Configure structured logging for the entire application."""

    # Configure processors
    processors = [
        structlog.contextvars.merge_contextvars,  # Merge context variables
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_request_context,  # Custom processor for request context
        add_module_context,   # Add module information
    ]

    if json_logs:
        processors.extend([
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer()
        ])

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.StandardLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def add_request_context(logger, method_name, event_dict):
    """Add request context to all log entries."""
    request_id = request_id_context.get()
    user_id = user_id_context.get()

    if request_id:
        event_dict['request_id'] = request_id
    if user_id:
        event_dict['user_id'] = user_id

    return event_dict

def add_module_context(logger, method_name, event_dict):
    """Add module information to log entries."""
    # Extract module from logger name (e.g., 'src.quiz.service' -> 'quiz')
    parts = logger.name.split('.')
    if len(parts) >= 2 and parts[0] == 'src':
        event_dict['module'] = parts[1]

    return event_dict
```

#### 2. **Module-Specific Logger Pattern**

Each module gets its logger using a consistent pattern:

```python
# src/quiz/service.py
from src.logging_config import get_logger

logger = get_logger(__name__)  # Creates logger: "src.quiz.service"

class QuizService:
    def create_quiz(self, user: User, quiz_data: QuizCreate) -> Quiz:
        logger.info(
            "creating_quiz",
            user_id=user.id,
            course_id=quiz_data.canvas_course_id,
            title=quiz_data.title
        )

        try:
            quiz = Quiz(**quiz_data.model_dump(), user_id=user.id)
            self.session.add(quiz)
            self.session.commit()

            logger.info(
                "quiz_created",
                quiz_id=quiz.id,
                status=quiz.status
            )
            return quiz

        except Exception as e:
            logger.error(
                "quiz_creation_failed",
                error=str(e),
                exc_info=True
            )
            raise
```

#### 3. **Request Context Middleware**

```python
# src/middleware/logging.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time
from src.logging_config import request_id_context, user_id_context, get_logger

logger = get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request_id_context.set(request_id)

        # Add to headers for tracing
        request.state.request_id = request_id

        # Log request start
        start_time = time.time()
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None
        )

        try:
            response = await call_next(request)

            # Log request completion
            duration = time.time() - start_time
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2)
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
                exc_info=True
            )
            raise
        finally:
            # Clear context
            request_id_context.set(None)
            user_id_context.set(None)
```

#### 4. **Authentication Context Propagation**

```python
# src/auth/dependencies.py
from src.logging_config import user_id_context

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Validate token and get user
    user = await validate_token(token)

    # Set user context for logging
    user_id_context.set(user.id)

    return user
```

### Logging Standards

#### 1. **Log Levels by Module**

| Module         | Default Level | Description                             |
| -------------- | ------------- | --------------------------------------- |
| `src.auth`     | INFO          | Authentication events, token operations |
| `src.quiz`     | INFO          | Quiz lifecycle events                   |
| `src.question` | INFO          | Question generation, approval           |
| `src.canvas`   | DEBUG         | External API calls, detailed tracing    |
| `src.database` | WARNING       | Query performance, connection issues    |

#### 2. **Structured Log Format**

All logs follow a consistent structure:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "src.quiz.service",
  "module": "quiz",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123,
  "event": "quiz_created",
  "quiz_id": 456,
  "duration_ms": 145.32
}
```

#### 3. **Event Naming Conventions**

- Use snake_case for event names
- Past tense for completed actions: `quiz_created`, `question_approved`
- Present continuous for ongoing actions: `extracting_content`, `generating_questions`
- Failed suffix for errors: `authentication_failed`, `api_call_failed`

### Integration Examples

#### 1. **Service Layer Logging**

```python
# src/canvas/service.py
class CanvasService:
    def __init__(self):
        self.logger = get_logger(__name__)

    async def fetch_course_modules(self, course_id: str) -> List[Module]:
        self.logger.debug(
            "fetching_course_modules",
            course_id=course_id,
            api_endpoint=f"/courses/{course_id}/modules"
        )

        with self.logger.contextualize(course_id=course_id):
            # All logs within this block include course_id
            try:
                response = await self.client.get(f"/courses/{course_id}/modules")
                modules = response.json()

                self.logger.info(
                    "course_modules_fetched",
                    module_count=len(modules)
                )
                return modules

            except CanvasAPIError as e:
                self.logger.error(
                    "canvas_api_failed",
                    error_code=e.code,
                    error_message=str(e)
                )
                raise
```

#### 2. **Cross-Module Tracing**

```python
# src/quiz/service.py
async def generate_questions(self, quiz_id: int):
    with self.logger.contextualize(quiz_id=quiz_id, operation="question_generation"):
        self.logger.info("starting_question_generation")

        # Canvas service logs will include quiz_id context
        content = await self.canvas_service.extract_content(quiz.course_id)

        # Question service logs will include quiz_id context
        questions = await self.question_service.generate_mcqs(content)

        self.logger.info(
            "question_generation_complete",
            question_count=len(questions)
        )
```

### Monitoring Integration

#### 1. **Log Aggregation Configuration**

```python
# src/config.py
class LoggingSettings(BaseSettings):
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"

    # External logging services
    enable_sentry: bool = False
    sentry_dsn: Optional[str] = None

    # ELK Stack
    enable_elk: bool = False
    logstash_host: Optional[str] = None
    logstash_port: int = 5000

    # CloudWatch
    enable_cloudwatch: bool = False
    cloudwatch_log_group: Optional[str] = None
```

#### 2. **Performance Logging Decorator**

```python
# src/utils/logging.py
from functools import wraps
import time

def log_performance(operation: str):
    """Decorator to log operation performance."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    f"{operation}_completed",
                    duration_ms=round(duration * 1000, 2),
                    function=func.__name__
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{operation}_failed",
                    duration_ms=round(duration * 1000, 2),
                    function=func.__name__,
                    error=str(e),
                    exc_info=True
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Similar implementation for sync functions
            pass

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Usage
@log_performance("quiz_creation")
async def create_quiz(self, user: User, quiz_data: QuizCreate) -> Quiz:
    # Function implementation
    pass
```

### Testing Logging

```python
# tests/test_logging.py
import pytest
from structlog.testing import LogCapture

@pytest.fixture
def log_capture():
    """Capture logs during tests."""
    with LogCapture() as capture:
        yield capture

def test_quiz_creation_logging(log_capture):
    # Test implementation
    service.create_quiz(user, quiz_data)

    # Verify logs
    assert log_capture.has("quiz_created")
    assert log_capture.entries[0]["quiz_id"] == 123
    assert log_capture.entries[0]["user_id"] == 456
```

### Migration Checklist for Logging

- [ ] Install structlog and python-json-logger
- [ ] Create centralized `src/logging_config.py`
- [ ] Add logging middleware to FastAPI app
- [ ] Update each module to use `get_logger(__name__)`
- [ ] Replace print statements and basic logging
- [ ] Add contextual information to all log calls
- [ ] Configure log aggregation service
- [ ] Add performance logging decorators
- [ ] Update tests to verify logging behavior
- [ ] Document logging standards in developer guide

## E. Risk Assessment and Mitigation

### Technical Risks

1. **Import Cycle Risk**

   - **Mitigation:** Strict module boundaries, dependency injection
   - **Detection:** Pre-commit hooks with import analysis

2. **Test Breakage**

   - **Mitigation:** Incremental migration, maintain test coverage
   - **Detection:** CI pipeline with coverage requirements

3. **Performance Regression**
   - **Mitigation:** Benchmark before/after each phase
   - **Detection:** Load testing, query analysis

### Process Risks

1. **Ongoing Development Conflicts**

   - **Mitigation:** Feature freeze during core migration phases
   - **Detection:** Daily standup coordination

2. **Knowledge Transfer**
   - **Mitigation:** Pair programming, documentation sprints
   - **Detection:** Code review metrics

## E. Success Metrics

### Structural Compliance

- ✓ 100% alignment with guide's directory structure
- ✓ All modules follow consistent internal structure
- ✓ No deviations from recommended patterns

### Code Quality

- ✓ Maintained or improved test coverage (>90%)
- ✓ Reduced circular dependencies to zero
- ✓ Improved module cohesion scores

### Developer Experience

- ✓ Reduced onboarding time by 50%
- ✓ Faster feature development (measured in story points)
- ✓ Improved code review velocity

### Performance

- ✓ No regression in API response times
- ✓ Maintained or improved database query efficiency
- ✓ Reduced memory footprint

## Implementation Checklist

### Pre-Migration

- [ ] Team alignment meeting
- [ ] Development environment setup
- [ ] Backup current structure
- [ ] Feature freeze announcement

### Per-Module Checklist

- [ ] Extract models to `module/models.py`
- [ ] Extract schemas to `module/schemas.py`
- [ ] Create service from CRUD operations
- [ ] Migrate routes to `module/router.py`
- [ ] Add module-specific dependencies
- [ ] Create configuration if needed
- [ ] Define constants
- [ ] Add custom exceptions
- [ ] Implement utilities
- [ ] Update tests
- [ ] Update imports
- [ ] Validate against guide

### Post-Migration

- [ ] Full regression testing
- [ ] Performance validation
- [ ] Documentation review
- [ ] Team training
- [ ] Retrospective

## Conclusion

This refactoring plan provides a systematic approach to transforming our backend to exactly match the FastAPI best practices guide structure. By following this plan, we'll achieve a modular, maintainable, and scalable architecture that aligns with industry standards and facilitates future development.
