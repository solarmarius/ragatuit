# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Rag@UiT is a Canvas LMS quiz generator application that uses language models to generate multiple-choice questions based on course content. The application consists of a FastAPI backend with PostgreSQL database and a React frontend with TypeScript.

**Key Features:**

- Canvas OAuth integration for course access
- AI-powered question generation from course materials
- Question review and approval workflow
- Direct exam creation in Canvas
- Progress tracking and analytics

## Development Commands

### Full Stack Development

```bash
# Start the entire stack with Docker Compose (recommended)
docker compose watch

# View logs for all services
docker compose logs

# View logs for specific service
docker compose logs backend
docker compose logs frontend
```

### Backend Development

```bash
# RUN TESTS
cd backend && source .venv/bin/activate && bash scripts/test.sh

# RUN LINTING
cd backend && source .venv/bin/activate && bash scripts/lint.sh

# Individual linting commands
mypy app
ruff check app
ruff format app --check
```

All backend database migrations should be prompted to the user to be done manually.

### Frontend Development

```bash
# From frontend/ directory
cd frontend

# Install dependencies
npm install

# Run local development server
npm run dev

# Build for production
npm run build

# Run linting and formatting
npm run lint

# Generate API client from backend OpenAPI spec
npm run generate-client

# Run end-to-end tests
npx playwright test
npx playwright test --ui
```

### Cross-Service Commands

```bash
# Generate frontend client from backend API (from project root)
./scripts/generate-client.sh

# Run pre-commit hooks manually
uv run pre-commit run --all-files
```

## Architecture

### Backend (FastAPI + SQLModel + PostgreSQL)

- **Entry Point**: `backend/app/main.py` - FastAPI application setup
- **API Routes**: `backend/app/api/routes/` - auth, users, utils
- **Models**: `backend/app/models.py` - SQLModel database models and Pydantic schemas
- **Database**: `backend/app/core/db.py` - Database connection and session management
- **Security**: `backend/app/core/security.py` - JWT authentication and password hashing
- **Configuration**: `backend/app/core/config.py` - Environment-based settings
- **CRUD Operations**: `backend/app/crud.py` - Database operations
- **Tests**: `backend/app/tests/` - Pytest-based test suite

### Frontend (React + TypeScript + Chakra UI)

- **Entry Point**: `frontend/src/main.tsx` - React application bootstrap
- **Routing**: `frontend/src/routes/` - TanStack Router file-based routing
- **Components**: `frontend/src/components/` - Reusable UI components organized by feature
- **API Client**: `frontend/src/client/` - Auto-generated from backend OpenAPI spec
- **Custom Hooks**: `frontend/src/hooks/` - Reusable React hooks for API, auth, and utilities
- **Theme**: `frontend/src/theme.tsx` - Chakra UI theme configuration
- **Auth Flow**: Canvas OAuth integration with redirect handling

### Frontend Architecture Documentation

Comprehensive documentation for the refactored frontend architecture:

- **📄 `/docs/frontend/ARCHITECTURE.md`** - Complete architectural overview, component organization, and development guidelines
- **📄 `/docs/frontend/CUSTOM_HOOKS.md`** - Detailed documentation for all 9 custom React hooks with usage examples
- **📄 `/docs/frontend/COMPONENT_PATTERNS.md`** - Reusable component patterns and design principles

**Key Frontend Features:**

- **Type Safety**: 100% TypeScript coverage with strict mode
- **Custom Hooks System**: 9 reusable hooks for API operations, state management, and UI interactions
- **Component Library**: Organized components with consistent patterns and JSDoc documentation
- **Performance Optimized**: Memoization, code splitting, and efficient data fetching

### Key Models

- **User**: Canvas user with OAuth tokens and metadata
- **Quiz**: Quiz with consolidated status system (7 states: created, extracting_content, generating_questions, ready_for_review, exporting_to_canvas, published, failed)
- **QuizStatus**: Enum representing the current state of quiz processing
- **FailureReason**: Enum for detailed error tracking when quiz status is failed
- **QuizLanguage**: Enum for supported languages (English: "en", Norwegian: "no")
- **Canvas Integration**: OAuth flow for accessing Canvas courses and content
- **Authentication**: JWT-based session management with Canvas token storage

## Development Workflow

1. **Canvas OAuth Setup**: Users authenticate via Canvas to access course content
2. **Course Selection**: Users select which Canvas course to generate questions from
3. **Quiz Creation**: Quiz created with status `created` and language selection (English/Norwegian)
4. **Content Processing**: Course modules are parsed and prepared for LLM input (status: `extracting_content`)
5. **Question Generation**: Language model generates multiple-choice questions (status: `generating_questions`)
6. **Review Process**: Users approve/reject generated questions (status: `ready_for_review`)
7. **Canvas Export**: Approved questions are exported to Canvas (status: `exporting_to_canvas`)
8. **Quiz Published**: Quiz is successfully published to Canvas (status: `published`)

**Error Handling**: Any step can fail (status: `failed`) with specific failure reasons for debugging.

## Status System Architecture

The application uses a **consolidated status system** with a single `status` field and detailed failure tracking:

### QuizStatus Enum
- `created` - Quiz created, ready to start
- `extracting_content` - Extracting content from Canvas modules
- `generating_questions` - AI generating questions from extracted content
- `ready_for_review` - Questions ready for user review and approval
- `exporting_to_canvas` - Exporting approved questions to Canvas
- `published` - Quiz successfully published to Canvas
- `failed` - Process failed (see failure_reason for details)

### FailureReason Enum
- `content_extraction_error` - Failed to extract content from Canvas
- `no_content_found` - No content found in selected modules
- `llm_generation_error` - AI question generation failed
- `no_questions_generated` - No questions could be generated
- `canvas_export_error` - Failed to export to Canvas
- `network_error` - Network connectivity issues
- `validation_error` - Data validation failed

### Status Light Color System
- 🔴 **Red**: `failed` - Any process failed
- 🟠 **Orange**: `created`, `extracting_content`, `generating_questions` - Processing
- 🟡 **Yellow**: `exporting_to_canvas` - Exporting to Canvas
- 🟣 **Purple**: `ready_for_review` - Ready for user review
- 🟢 **Green**: `published` - Successfully completed

## Important Conventions

### Backend

- Use SQLModel for database models (combines SQLAlchemy + Pydantic)
- All API endpoints return consistent response formats
- Canvas tokens are securely stored and refreshed automatically
- Database migrations managed with Alembic
- Comprehensive test coverage required
- Use consolidated status system for all quiz state management

### Frontend

- File-based routing with TanStack Router
- Auto-generated API client from backend OpenAPI spec
- Chakra UI for consistent component styling with custom design system
- TypeScript strict mode enabled with 100% type coverage
- Canvas authentication state managed globally
- Custom hooks system for reusable logic and API operations
- Component patterns documented in `/docs/frontend/` for consistency
- JSDoc comments on all component props and custom hooks
- StatusLight component with 4-color system based on consolidated status
- Smart polling system with dynamic intervals based on quiz status
- QuizPhaseProgress component for detailed three-phase status display

### Testing

- Backend: Pytest with coverage reporting
- Frontend: Playwright for end-to-end testing
- All tests must pass before deployment
- Pre-commit hooks enforce code quality

## Canvas Integration

The application integrates deeply with Canvas LMS:

- OAuth 2.0 flow for secure authentication
- Course and module content fetching
- Direct quiz/exam creation in Canvas
- Token refresh handling for long-term access

## Environment Setup

Development uses Docker Compose with service-specific overrides. The stack includes:

- Backend API (FastAPI)
- Frontend (React dev server)
- PostgreSQL database
- Adminer (database admin)
- Traefik (reverse proxy)
- MailCatcher (email testing)

URLs:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database Admin: http://localhost:8080
