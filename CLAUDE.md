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
# From backend/ directory
cd backend

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Run local development server
fastapi dev app/main.py

# Run tests with coverage
bash scripts/test.sh

# Run linting and type checking
bash scripts/lint.sh

# Individual linting commands
mypy app
ruff check app
ruff format app --check

# Database migrations
docker compose exec backend bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

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
- **Hooks**: `frontend/src/hooks/` - Custom React hooks for auth and utilities
- **Theme**: `frontend/src/theme.tsx` - Chakra UI theme configuration
- **Auth Flow**: Canvas OAuth integration with redirect handling

### Key Models
- **User**: Canvas user with OAuth tokens and metadata
- **Canvas Integration**: OAuth flow for accessing Canvas courses and content
- **Authentication**: JWT-based session management with Canvas token storage

## Development Workflow

1. **Canvas OAuth Setup**: Users authenticate via Canvas to access course content
2. **Course Selection**: Users select which Canvas course to generate questions from
3. **Content Processing**: Course modules are parsed and prepared for LLM input
4. **Question Generation**: Language model generates multiple-choice questions
5. **Review Process**: Users approve/reject generated questions
6. **Exam Creation**: Approved questions are exported to Canvas

## Important Conventions

### Backend
- Use SQLModel for database models (combines SQLAlchemy + Pydantic)
- All API endpoints return consistent response formats
- Canvas tokens are securely stored and refreshed automatically
- Database migrations managed with Alembic
- Comprehensive test coverage required

### Frontend
- File-based routing with TanStack Router
- Auto-generated API client from backend OpenAPI spec
- Chakra UI for consistent component styling
- TypeScript strict mode enabled
- Canvas authentication state managed globally

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
