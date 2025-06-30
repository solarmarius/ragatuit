Backend Refactoring Memory File

Conversation Overview

Main Topic: Implementing a comprehensive backend refactoring for the Rag@UiT application,
transforming it from a monolithic structure to a modular, domain-driven architecture following
FastAPI best practices.

Primary Objective: Execute the refactoring plan documented in
/Users/mariussolaas/ragatuit/docs/REFACTORING_PLAN.md to reorganize the backend into
feature-based modules (auth, quiz, question, canvas).

Current Status:

- Phase 1 (Foundation Setup) ✅ COMPLETED and committed
- Phase 2 (Auth Module Migration) 🔄 IN PROGRESS - about 80% complete

Important Context

User Information

- User: Marius Solaas
- Project: Rag@UiT - A Canvas LMS quiz generator using LLMs
- Working Directory: /Users/mariussolaas/ragatuit/backend
- Environment: macOS (Darwin 24.5.0), Python 3.12.7
- Git Branch: restructure-backend-v2

Project Specifications

- Tech Stack: FastAPI, SQLModel, PostgreSQL, LangGraph (for MCQ generation)
- Key Features: Canvas OAuth, quiz generation, question management, LLM integration
- Testing: Pytest with coverage, pre-commit hooks
- Development: Docker Compose setup, virtual environment with uv

Refactoring Requirements

1. Follow exact structure from FastAPI best practices guide
2. Maintain 100% API compatibility
3. Preserve all existing functionality
4. Keep tests passing at each phase
5. Commit after each phase

Work Completed

Phase 1: Foundation Setup ✅

Completed Actions:

1. Created module directories: auth/, quiz/, question/, canvas/, middleware/
2. Moved core infrastructure files:


    - core/config.py → config.py
    - core/db.py → database.py (renamed)
    - core/exceptions.py → exceptions.py (merged with global_exception_handler.py)
    - core/logging_config.py → logging_config.py
    - core/retry.py → retry.py
    - core/security.py → security.py
    - core/middleware/logging_middleware.py → middleware/logging.py

3. Updated all imports throughout codebase
4. Fixed all linting issues
5. All tests passing (74 tests)
6. Committed with message: "refactor: setup foundation and move core infrastructure"

Phase 2: Auth Module Migration (IN PROGRESS)

Completed:

1. Created auth module structure:


    - auth/models.py - User SQLModel
    - auth/schemas.py - UserCreate, UserPublic, TokenPayload, etc.
    - auth/service.py - AuthService class with user CRUD and canvas_auth logic
    - auth/dependencies.py - get_current_user, CurrentUser type
    - auth/router.py - Auth endpoints moved from api/routes/auth.py
    - auth/constants.py - Auth constants
    - auth/exceptions.py - Auth-specific exceptions
    - auth/utils.py - create_access_token and OAuth utilities
    - auth/__init__.py - Module exports

2. Removed auth-related models from app/models.py
3. Updated api/main.py to import auth router from new location
4. Fixed circular import issues with TYPE_CHECKING
5. Updated many imports throughout codebase

Still In Progress:

- Updating test files to use AuthService instead of crud functions
- Removing user CRUD functions from crud.py
- Fixing remaining import issues

Current Challenges

Issue 1: Test Failures

The app/tests/crud/test_user.py tests are failing because:

1. They still reference crud functions that have been moved to AuthService
2. Need to update all test imports and function calls

Issue 2: Import Updates Needed

Many files still import from old locations:

- Tests importing UserCreate from app.models instead of app.auth.schemas
- Tests using crud.create_user instead of AuthService.create_user
- Various files importing create_access_token from wrong location

Code Structure Changes

Old Structure

app/
├── models.py (monolithic - all models and schemas)
├── crud.py (monolithic - all CRUD operations)
├── core/
│ ├── config.py
│ ├── db.py
│ ├── security.py
│ └── ...
└── api/routes/
├── auth.py
└── ...

New Structure (Partial)

app/
├── auth/
│ ├── models.py (User model only)
│ ├── schemas.py (auth schemas)
│ ├── service.py (AuthService with CRUD)
│ ├── router.py (auth endpoints)
│ ├── dependencies.py
│ └── ...
├── config.py (moved from core/)
├── database.py (renamed from core/db.py)
├── exceptions.py (merged with global_exception_handler)
└── ...

Critical Implementation Details

Circular Import Prevention

Using TYPE_CHECKING to avoid circular imports between User and Quiz models:

# In auth/models.py

from typing import TYPE_CHECKING
if TYPE_CHECKING:
from app.models import Quiz

# In models.py

from typing import TYPE_CHECKING
if TYPE_CHECKING:
from app.auth.models import User

Service Pattern

Moving from function-based CRUD to service classes:

# Old: crud.create_user(session, user_create)

# New: AuthService(session).create_user(user_create)

Import Path Changes

- from app.models import User → from app.auth.models import User
- from app.models import UserCreate → from app.auth.schemas import UserCreate
- from app.core.config import settings → from app.config import settings
- from app.api.routes.auth import router → from app.auth import router

Next Steps (Immediate)

1. Fix test_user.py:


    - Replace all crud. calls with AuthService equivalents
    - Update imports to use new paths
    - Ensure auth_service is instantiated before use

2. Clean up remaining imports:


    - Run systematic search/replace for old import paths
    - Update all test files
    - Verify no references to deleted files remain

3. Complete Phase 2:


    - Run all auth-related tests
    - Fix any remaining issues
    - Run full test suite
    - Run linting (bash scripts/lint.sh)
    - Commit: "refactor: migrate auth module to domain structure"

Remaining Phases

Phase 3: Canvas Module Migration

- Create canvas/schemas.py
- Move content_extraction.py → canvas/service.py
- Move canvas routes
- Update tests

Phase 4: Quiz Module Migration

- Extract Quiz model and schemas
- Move quiz CRUD to service
- Migrate quiz routes
- Update tests

Phase 5: Question Module Migration

- Extract Question model and schemas
- Move MCQ generation service (preserve LangGraph!)
- Migrate question routes
- Update tests

Phase 6: Integration & Cleanup

- Update main.py
- Delete old empty directories
- Fix all remaining imports

Phase 7: Final Validation

- Full test suite
- Linting
- Documentation updates

Command Reference

Testing Commands

source .venv/bin/activate
python -m pytest app/tests/crud/test_user.py -v # Single test file
bash scripts/test.sh # Full test suite

Linting Commands

source .venv/bin/activate
mypy app
ruff check app --fix
ruff format app
bash scripts/lint.sh # All linting

Git Commands Used

git add -A
git commit -m "refactor: [phase description]"

Error Patterns Encountered

1. Circular Import: User ↔ Quiz relationship


    - Solution: TYPE_CHECKING imports

2. Test Import Failures: Tests importing from moved modules


    - Solution: Update import paths systematically

3. SQLAlchemy Table Redefinition: User model defined twice


    - Solution: Remove from old location before importing new

File Locations Reference

- Specification: /Users/mariussolaas/ragatuit/backend/REFACTORING_IMPLEMENTATION_SPEC.md
- Refactoring Plan: /Users/mariussolaas/ragatuit/docs/REFACTORING_PLAN.md
- Main Work Directory: /Users/mariussolaas/ragatuit/backend/app/
- Tests: /Users/mariussolaas/ragatuit/backend/app/tests/

User Preferences Noted

1. Wants linting run before commits
2. Prefers step-by-step execution with validation
3. Wants tests passing at each phase
4. Expects clear commit messages per phase
5. Values maintaining API compatibility

Critical Notes

- LangGraph Integration: Must preserve MCQ generation workflow exactly
- Canvas OAuth: Flow must remain unchanged
- Pre-commit Hooks: Auto-fix some issues on commit
- Docker Environment: Some tests fail outside Docker (canvas-mock connectivity)

This refactoring is transforming a working but monolithic codebase into a clean, modular
architecture while maintaining all functionality. The key challenge is managing the
interdependencies during the transition.
