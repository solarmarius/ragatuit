# Backend Refactoring Implementation Specification

## Overview

This document provides the detailed implementation specification for refactoring the Rag@UiT backend from its current monolithic structure to a modular, domain-driven architecture following FastAPI best practices.

## Current State Analysis

### Monolithic Files
- `app/models.py` (272 lines) - Contains all SQLModel database models and Pydantic schemas
- `app/crud.py` (537 lines) - Contains all database operations for all models

### Current Directory Structure
```
backend/app/
├── api/routes/          # Route handlers
│   ├── auth.py         # Authentication endpoints
│   ├── canvas.py       # Canvas LMS endpoints
│   ├── quiz.py         # Quiz management endpoints
│   ├── questions.py    # Question management endpoints
│   └── users.py        # User management endpoints
├── core/               # Core infrastructure
│   ├── config.py       # Application configuration
│   ├── db.py           # Database connection
│   ├── dependencies.py # Service dependency injection
│   ├── exceptions.py   # Base exceptions
│   ├── global_exception_handler.py # Exception handlers
│   ├── logging_config.py # Logging setup
│   ├── retry.py        # Retry decorators
│   ├── security.py     # JWT and password utilities
│   └── middleware/
│       └── logging_middleware.py
├── services/           # Business logic
│   ├── canvas_auth.py  # Canvas OAuth service
│   ├── canvas_quiz_export.py # Quiz export to Canvas
│   ├── content_extraction.py # Canvas content extraction
│   └── mcq_generation.py # LangGraph MCQ generation
├── tests/              # Test suite
├── models.py           # All models and schemas (monolithic)
├── crud.py             # All CRUD operations (monolithic)
└── main.py             # FastAPI app initialization
```

## Target Architecture

### Domain-Driven Module Structure
```
backend/app/
├── auth/               # Authentication domain
│   ├── __init__.py
│   ├── router.py      # Auth endpoints
│   ├── schemas.py     # Auth Pydantic schemas
│   ├── models.py      # User SQLModel
│   ├── service.py     # Auth business logic + CRUD
│   ├── dependencies.py # Auth dependencies
│   ├── constants.py   # Auth constants
│   ├── exceptions.py  # Auth-specific exceptions
│   └── utils.py       # Auth utilities
├── quiz/               # Quiz management domain
│   ├── __init__.py
│   ├── router.py      # Quiz endpoints
│   ├── schemas.py     # Quiz Pydantic schemas
│   ├── models.py      # Quiz SQLModel
│   ├── service.py     # Quiz business logic + CRUD
│   ├── dependencies.py # Quiz dependencies
│   ├── constants.py   # Quiz constants
│   └── exceptions.py  # Quiz-specific exceptions
├── question/           # Question generation domain
│   ├── __init__.py
│   ├── router.py      # Question endpoints
│   ├── schemas.py     # Question Pydantic schemas
│   ├── models.py      # Question SQLModel
│   ├── service.py     # MCQ generation + CRUD
│   ├── dependencies.py # Question dependencies
│   ├── constants.py   # Question constants
│   └── exceptions.py  # Question-specific exceptions
├── canvas/             # Canvas LMS integration
│   ├── __init__.py
│   ├── router.py      # Canvas endpoints
│   ├── schemas.py     # Canvas Pydantic schemas
│   ├── service.py     # Canvas services
│   ├── dependencies.py # Canvas dependencies
│   ├── constants.py   # Canvas constants
│   ├── exceptions.py  # Canvas-specific exceptions
│   └── utils.py       # Canvas utilities
├── middleware/         # App-wide middleware
│   ├── __init__.py
│   └── logging.py     # Request logging
├── config.py          # Global configuration
├── database.py        # Database setup
├── exceptions.py      # Global exceptions
├── logging_config.py  # Logging configuration
├── retry.py           # Retry decorators
├── security.py        # Security utilities
└── main.py            # FastAPI app
```

## Implementation Phases

### Phase 1: Foundation Setup

**Files to Move:**
| From | To | Action |
|------|-----|--------|
| `app/core/config.py` | `app/config.py` | Move as-is |
| `app/core/db.py` | `app/database.py` | Move and rename |
| `app/core/exceptions.py` | `app/exceptions.py` | Move |
| `app/core/global_exception_handler.py` | `app/exceptions.py` | Merge into exceptions.py |
| `app/core/logging_config.py` | `app/logging_config.py` | Move as-is |
| `app/core/retry.py` | `app/retry.py` | Move as-is |
| `app/core/security.py` | `app/security.py` | Move as-is |
| `app/core/middleware/logging_middleware.py` | `app/middleware/logging.py` | Move to new structure |

**Actions:**
1. Create directories: `auth/`, `quiz/`, `question/`, `canvas/`, `middleware/`
2. Move core infrastructure files
3. Update imports in moved files
4. Create `__init__.py` files for each module
5. Run tests and fix import issues
6. Commit changes

### Phase 2: Auth Module Migration

**Models to Extract from `models.py`:**
```python
# SQLModel
- User (table=True)

# Pydantic Schemas
- UserBase
- UserCreate
- UserCreateOpen
- UserUpdate
- UserOut
- UpdatePassword
- TokenPayload
- Token
- NewPassword
- AuthResponse
```

**CRUD to Extract from `crud.py`:**
```python
- get_user_by_email()
- get_user_by_canvas_id()
- create_user()
- update_user()
- authenticate()
- update_encrypted_canvas_tokens()
- get_canvas_tokens()
```

**Services to Move:**
- `services/canvas_auth.py` → Merge into `auth/service.py`

**Routes to Move:**
- `api/routes/auth.py` → `auth/router.py`

**Dependencies to Extract:**
- `get_current_user()` from various files → `auth/dependencies.py`
- OAuth2 scheme setup → `auth/dependencies.py`

**Actions:**
1. Create auth module structure
2. Extract User model and auth schemas
3. Create AuthService class combining CRUD and canvas_auth logic
4. Move auth routes
5. Create auth dependencies
6. Update imports throughout codebase
7. Migrate auth tests
8. Run tests and fix issues
9. Commit changes

### Phase 3: Canvas Module Migration

**Schemas to Create in `canvas/schemas.py`:**
```python
- CanvasCourse
- CanvasModule
- CanvasModuleItem
- CanvasPage
- CanvasFile
- ExtractedContent
- QuizExportRequest
- QuizExportResponse
```

**Services to Move:**
- `services/content_extraction.py` → `canvas/service.py` (ContentExtractionService)
- `services/canvas_quiz_export.py` → `canvas/service.py` (CanvasQuizExportService)

**Routes to Move:**
- `api/routes/canvas.py` → `canvas/router.py`

**Dependencies to Create:**
- Canvas service factories → `canvas/dependencies.py`

**Actions:**
1. Create canvas module structure
2. Define Canvas-specific schemas
3. Move content extraction and quiz export services
4. Create unified CanvasService or keep separate services
5. Move canvas routes
6. Create canvas dependencies
7. Update imports
8. Migrate canvas tests
9. Run tests and fix issues
10. Commit changes

### Phase 4: Quiz Module Migration

**Models to Extract from `models.py`:**
```python
# SQLModel
- Quiz (table=True)

# Pydantic Schemas
- QuizBase
- QuizCreate
- QuizUpdate
- QuizOut
- QuizList
- LLMSettings
```

**CRUD to Extract from `crud.py`:**
```python
- create_quiz()
- get_quiz()
- get_quizzes()
- update_quiz()
- delete_quiz()
- get_user_quizzes()
```

**Routes to Move:**
- `api/routes/quiz.py` → `quiz/router.py`

**Actions:**
1. Create quiz module structure
2. Extract Quiz model and schemas
3. Create QuizService class with CRUD operations
4. Move quiz routes
5. Create quiz dependencies
6. Update imports
7. Migrate quiz tests
8. Run tests and fix issues
9. Commit changes

### Phase 5: Question Module Migration

**Models to Extract from `models.py`:**
```python
# SQLModel
- Question (table=True)

# Pydantic Schemas
- QuestionBase
- QuestionCreate
- QuestionUpdate
- QuestionOut
- MCQGenerationRequest
- MCQGenerationResponse
- QuestionApprovalUpdate
```

**CRUD to Extract from `crud.py`:**
```python
- create_question()
- get_question()
- get_questions_by_quiz()
- update_question()
- delete_question()
- approve_question()
- reject_question()
- get_approved_questions()
```

**Services to Move:**
- `services/mcq_generation.py` → `question/service.py` (MCQGenerationService with LangGraph)

**Routes to Move:**
- `api/routes/questions.py` → `question/router.py`

**Dependencies to Extract:**
- MCQGenerationService dependency → `question/dependencies.py`

**Actions:**
1. Create question module structure
2. Extract Question model and schemas
3. Move MCQ generation service (preserve LangGraph workflow)
4. Create QuestionService combining CRUD and generation
5. Move question routes
6. Create question dependencies
7. Update imports
8. Migrate question tests
9. Run tests and fix issues
10. Commit changes

### Phase 6: Integration & Cleanup

**Files to Delete:**
- `app/models.py` (now empty)
- `app/crud.py` (now empty)
- `app/core/` directory (now empty)
- `app/api/` directory (now empty)
- `app/services/` directory (now empty)
- `app/core/dependencies.py` (contents distributed)

**Updates Required:**
- `app/main.py` - Update all router imports
- All test files - Update imports
- Alembic migrations - Update model imports
- Any remaining import statements

**Actions:**
1. Update main.py router imports
2. Delete old empty files and directories
3. Search and replace all old import paths
4. Update alembic env.py imports
5. Run full test suite
6. Fix any remaining import issues
7. Commit changes

### Phase 7: Final Validation

**Validation Steps:**
1. Run full test suite: `bash scripts/test.sh`
2. Run linting: `bash scripts/lint.sh`
3. Check type hints: `mypy app`
4. Format code: `ruff format app`
5. Test API manually
6. Update documentation
7. Final commit

## Import Path Changes

### Model Imports
```python
# Before
from app.models import User, Quiz, Question

# After
from app.auth.models import User
from app.quiz.models import Quiz
from app.question.models import Question
```

### Schema Imports
```python
# Before
from app.models import UserCreate, QuizOut, QuestionUpdate

# After
from app.auth.schemas import UserCreate
from app.quiz.schemas import QuizOut
from app.question.schemas import QuestionUpdate
```

### Service Imports
```python
# Before
from app.crud import create_user, get_quiz
from app.services.mcq_generation import MCQGenerationService

# After
from app.auth.service import AuthService
from app.quiz.service import QuizService
from app.question.service import MCQGenerationService
```

### Router Imports
```python
# Before
from app.api.routes import auth, quiz, questions, canvas

# After
from app.auth.router import router as auth_router
from app.quiz.router import router as quiz_router
from app.question.router import router as question_router
from app.canvas.router import router as canvas_router
```

## Testing Strategy

### Test Structure Migration
```
tests/
├── auth/
│   ├── test_router.py    # From test_auth.py
│   ├── test_service.py   # From test_user CRUD
│   └── test_models.py    # New model tests
├── quiz/
│   ├── test_router.py    # From test_quiz.py
│   ├── test_service.py   # From test_quiz CRUD
│   └── test_models.py    # New model tests
├── question/
│   ├── test_router.py    # From test_questions.py
│   ├── test_service.py   # From test_mcq_generation
│   └── test_models.py    # New model tests
├── canvas/
│   ├── test_router.py    # From test_canvas.py
│   └── test_service.py   # From test_content_extraction
└── test_main.py          # App-level tests
```

### Test Migration Process
1. Copy test file to new location
2. Update all imports
3. Run test individually
4. Fix any issues
5. Ensure test coverage maintained

## Risk Mitigation

### Import Cycles
- Use TYPE_CHECKING imports where needed
- Avoid circular dependencies between modules
- Use dependency injection for cross-module needs

### Database Migrations
- Alembic imports must be updated carefully
- Test migrations after model moves
- Keep model table names unchanged

### API Compatibility
- No endpoint URLs should change
- Request/response schemas must remain identical
- Maintain backward compatibility

## Success Criteria

1. All tests pass (100% of existing tests)
2. No API breaking changes
3. Clean module boundaries (no circular imports)
4. Improved code organization
5. Maintained or improved performance
6. Type checking passes
7. Linting passes
8. Documentation updated

## Rollback Plan

Each phase creates a single commit, allowing easy rollback:
```bash
git revert HEAD  # Rollback last phase
git revert HEAD~2..HEAD  # Rollback last 2 phases
```

## Timeline

- Phase 1: 2 hours
- Phase 2: 3 hours
- Phase 3: 2 hours
- Phase 4: 2 hours
- Phase 5: 3 hours
- Phase 6: 2 hours
- Phase 7: 1 hour

Total estimated time: 15 hours

## Notes

- LangGraph workflow in MCQ generation must be preserved exactly
- Canvas OAuth flow must remain unchanged
- JWT authentication flow must remain unchanged
- All environment variables remain the same
- Database schema remains unchanged (no new migrations)
