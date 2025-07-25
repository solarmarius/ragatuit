# 6. Missing Dependency Injection Pattern

## Priority: Critical

**Estimated Effort**: 3 days
**Python Version**: 3.10+
**Dependencies**: FastAPI dependencies system

## Problem Statement

### Current Situation

Services are instantiated as global singletons (`mcq_generation_service = MCQGenerationService()`) without proper dependency injection, making testing difficult and preventing proper lifecycle management.

### Why It's a Problem

- **Testing Difficulties**: Cannot mock services properly for unit tests
- **Global State Issues**: Services maintain state across requests
- **No Lifecycle Management**: Services created at import time, not per-request
- **Tight Coupling**: Components depend on concrete implementations
- **Configuration Coupling**: Services hardcode configuration values
- **Memory Leaks**: Services hold references indefinitely

### Affected Modules

- `app/services/mcq_generation.py` - Global service instance
- `app/api/routes/quiz.py` - Direct service usage
- All service modules with singleton pattern
- Testing infrastructure

### Technical Debt Assessment

- **Risk Level**: Critical - Blocks proper testing and scalability
- **Impact**: All service layer operations
- **Cost of Delay**: Increases with each new service

## Current Implementation Analysis

```python
# File: app/services/mcq_generation.py (current problematic pattern)
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("mcq_generation")

# PROBLEM: Global singleton instantiation
mcq_generation_service = MCQGenerationService()

class MCQGenerationService:
    def __init__(self):
        # PROBLEM: Configuration hardcoded at import time
        self.max_questions_per_module = settings.MAX_QUESTIONS_PER_MODULE
        self.target_difficulty = "medium"
        # PROBLEM: Global state that persists across requests
        self.generation_cache = {}

# File: app/api/routes/quiz.py (current usage)
from app.services.mcq_generation import mcq_generation_service  # Global import!

@router.post("/{quiz_id}/generate-questions")
async def generate_questions_endpoint(
    quiz_id: UUID,
    generation_request: MCQGenerationRequest,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    # PROBLEM: Using global service instance
    result = await mcq_generation_service.generate_mcqs_for_quiz(
        quiz_id=quiz_id,
        target_count=generation_request.target_question_count,
        model=generation_request.model,
        temperature=generation_request.temperature,
    )
```

### Testing Problems

```python
# Current testing difficulties
def test_mcq_generation():
    # PROBLEM: Cannot mock the global service
    # Global state affects other tests
    # No way to inject test configuration

    # This doesn't work reliably:
    with patch('app.services.mcq_generation.mcq_generation_service'):
        # Test code...
```

### Python Anti-patterns Identified

- **Global State**: Services maintain state across requests
- **Import-Time Configuration**: Settings loaded at module import
- **Singleton Abuse**: Global instances prevent proper testing
- **Tight Coupling**: Direct imports instead of dependency injection
- **No Interface Segregation**: Services expose all methods publicly

## Proposed Solution

### Pythonic Approach

Implement proper dependency injection using FastAPI's dependency system with Protocol-based interfaces, factory functions, and proper service lifecycle management.

### Design Patterns

- **Dependency Injection**: FastAPI's `Depends()` system
- **Protocol Pattern**: Type-safe interface definitions
- **Factory Pattern**: Service creation with configuration
- **Repository Pattern**: Data access abstraction

### Code Examples

```python
# File: app/core/protocols.py (NEW)
from typing import Protocol, Any, Dict, List
from uuid import UUID
from sqlmodel import Session

class MCQGenerationServiceProtocol(Protocol):
    """Protocol for MCQ generation services."""

    async def generate_mcqs_for_quiz(
        self,
        quiz_id: UUID,
        target_count: int,
        model: str,
        temperature: float,
        session: Session
    ) -> Dict[str, Any]: ...

class ContentExtractionServiceProtocol(Protocol):
    """Protocol for content extraction services."""

    async def extract_content_for_modules(
        self,
        module_ids: List[int]
    ) -> Dict[str, Any]: ...

class QuizExportServiceProtocol(Protocol):
    """Protocol for quiz export services."""

    async def export_to_canvas(
        self,
        quiz_id: UUID,
        canvas_quiz_data: Dict[str, Any],
        session: Session
    ) -> Dict[str, Any]: ...

# File: app/services/dependencies.py (NEW)
from functools import lru_cache
from typing import Annotated, Optional
from fastapi import Depends
from sqlmodel import Session

from app.core.config import settings
from app.core.db import get_session
from app.services.mcq_generation import MCQGenerationService
from app.services.content_extraction import ContentExtractionService
from app.services.canvas_quiz_export import CanvasQuizExportService

# Service factory functions with configuration injection
@lru_cache()
def get_mcq_generation_service() -> MCQGenerationService:
    """
    Create MCQ generation service with configuration.

    Uses lru_cache to ensure singleton behavior per application lifecycle,
    but allows dependency injection for testing.
    """
    return MCQGenerationService(
        max_questions_per_module=settings.MAX_QUESTIONS_PER_MODULE,
        target_difficulty=settings.DEFAULT_DIFFICULTY,
        model_temperature=settings.DEFAULT_TEMPERATURE,
        enable_caching=settings.ENABLE_SERVICE_CACHING
    )

def get_content_extraction_service(
    canvas_token: str,
    course_id: int,
    canvas_base_url: Optional[str] = None
) -> ContentExtractionService:
    """
    Create content extraction service with dynamic configuration.

    Args:
        canvas_token: Canvas API token
        course_id: Canvas course ID
        canvas_base_url: Optional Canvas base URL override

    Returns:
        Configured ContentExtractionService
    """
    base_url = canvas_base_url or str(settings.CANVAS_BASE_URL)

    return ContentExtractionService(
        canvas_token=canvas_token,
        course_id=course_id,
        canvas_base_url=base_url,
        api_timeout=settings.CANVAS_API_TIMEOUT,
        max_retries=settings.MAX_RETRIES
    )

@lru_cache()
def get_quiz_export_service() -> CanvasQuizExportService:
    """Create quiz export service."""
    return CanvasQuizExportService(
        canvas_base_url=str(settings.CANVAS_BASE_URL),
        api_timeout=settings.CANVAS_API_TIMEOUT
    )

# Dependency type aliases for clean injection
MCQServiceDep = Annotated[MCQGenerationService, Depends(get_mcq_generation_service)]
QuizExportServiceDep = Annotated[CanvasQuizExportService, Depends(get_quiz_export_service)]

# Factory function for content extraction (requires runtime parameters)
def create_content_extraction_service_factory(
    canvas_token: str,
    course_id: int
):
    """
    Factory function that returns a dependency function.

    This allows us to create a service with runtime parameters
    while still using FastAPI's dependency injection.
    """
    def _get_content_service() -> ContentExtractionService:
        return get_content_extraction_service(canvas_token, course_id)

    return _get_content_service

# File: app/services/mcq_generation.py (UPDATED)
from typing import Optional, Dict, Any
from uuid import UUID
from sqlmodel import Session
from datetime import datetime

from app.core.logging_config import get_logger
from app.core.config import settings

logger = get_logger("mcq_generation")

class MCQGenerationService:
    """
    Service for generating multiple-choice questions using LangGraph.

    This service is now properly injectable and testable.
    """

    def __init__(
        self,
        max_questions_per_module: int = 10,
        target_difficulty: str = "medium",
        model_temperature: float = 0.7,
        enable_caching: bool = True
    ):
        """
        Initialize MCQ generation service with configuration.

        Args:
            max_questions_per_module: Maximum questions per module
            target_difficulty: Target difficulty level
            model_temperature: LLM temperature setting
            enable_caching: Whether to enable generation caching
        """
        self.max_questions_per_module = max_questions_per_module
        self.target_difficulty = target_difficulty
        self.model_temperature = model_temperature
        self.enable_caching = enable_caching

        # Instance-specific cache (not global)
        self._generation_cache: Dict[str, Any] = {} if enable_caching else None

        logger.info(
            "mcq_generation_service_initialized",
            max_questions=max_questions_per_module,
            difficulty=target_difficulty,
            temperature=model_temperature,
            caching_enabled=enable_caching
        )

    async def generate_mcqs_for_quiz(
        self,
        quiz_id: UUID,
        target_count: int,
        model: str,
        temperature: float,
        session: Session
    ) -> Dict[str, Any]:
        """
        Generate MCQs for a quiz using LangGraph workflow.

        Args:
            quiz_id: Quiz identifier
            target_count: Number of questions to generate
            model: LLM model to use
            temperature: Generation temperature
            session: Database session (injected)

        Returns:
            Generation results
        """
        # Check cache if enabled
        if self._generation_cache is not None:
            cache_key = f"{quiz_id}_{target_count}_{model}_{temperature}"
            if cache_key in self._generation_cache:
                logger.info(
                    "mcq_generation_cache_hit",
                    quiz_id=str(quiz_id),
                    cache_key=cache_key
                )
                return self._generation_cache[cache_key]

        # Implementation continues...
        result = await self._execute_generation_workflow(
            quiz_id, target_count, model, temperature, session
        )

        # Cache result if enabled
        if self._generation_cache is not None:
            self._generation_cache[cache_key] = result

        return result

    async def _execute_generation_workflow(
        self,
        quiz_id: UUID,
        target_count: int,
        model: str,
        temperature: float,
        session: Session
    ) -> Dict[str, Any]:
        """Execute the actual LangGraph workflow."""
        # Workflow implementation...
        pass

# File: app/api/routes/quiz.py (UPDATED)
from typing import Annotated
from fastapi import Depends

from app.services.dependencies import (
    MCQServiceDep,
    QuizExportServiceDep,
    create_content_extraction_service_factory
)
from app.api.deps import CurrentUser, SessionDep, CanvasToken

@router.post("/{quiz_id}/generate-questions")
async def generate_questions_endpoint(
    quiz_id: UUID,
    generation_request: MCQGenerationRequest,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
    # SOLUTION: Proper dependency injection
    mcq_service: MCQServiceDep,
) -> dict[str, str]:
    """Generate questions for a quiz using injected service."""

    # Verify quiz ownership
    quiz = get_quiz_by_id(session, quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Use injected service
    result = await mcq_service.generate_mcqs_for_quiz(
        quiz_id=quiz_id,
        target_count=generation_request.target_question_count,
        model=generation_request.model,
        temperature=generation_request.temperature,
        session=session  # Pass session to service
    )

    return {"message": "Question generation started", "task_id": result["task_id"]}

@router.post("/", response_model=Quiz)
async def create_new_quiz(
    quiz_data: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> Quiz:
    """Create a new quiz with proper service injection."""

    quiz = create_quiz(session, quiz_data, current_user.id)

    # Create content extraction service with runtime parameters
    content_service_factory = create_content_extraction_service_factory(
        canvas_token, quiz_data.canvas_course_id
    )
    content_service = content_service_factory()

    # Schedule background task with injected service
    background_tasks.add_task(
        extract_content_for_quiz_with_service,
        quiz.id,
        list(quiz_data.selected_modules.keys()),
        content_service
    )

    return quiz

# Background task with injected service
async def extract_content_for_quiz_with_service(
    quiz_id: UUID,
    module_ids: List[int],
    content_service: ContentExtractionService
) -> None:
    """Background task using injected service."""

    try:
        with get_session() as session:
            # Update quiz status
            quiz = session.get(Quiz, quiz_id)
            if quiz:
                quiz.content_extraction_status = "processing"
                session.commit()

            # Use injected service
            extracted_content = await content_service.extract_content_for_modules(module_ids)

            # Update quiz with results
            if quiz:
                quiz.content_dict = extracted_content
                quiz.content_extraction_status = "completed"
                quiz.content_extracted_at = datetime.utcnow()
                session.commit()

    except Exception as e:
        logger.error(
            "content_extraction_failed",
            quiz_id=str(quiz_id),
            error=str(e)
        )

        # Update failure status
        with get_session() as session:
            quiz = session.get(Quiz, quiz_id)
            if quiz:
                quiz.content_extraction_status = "failed"
                session.commit()

# File: app/services/content_extraction.py (UPDATED)
class ContentExtractionService:
    """Content extraction service with proper configuration injection."""

    def __init__(
        self,
        canvas_token: str,
        course_id: int,
        canvas_base_url: str,
        api_timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize service with injected configuration.

        Args:
            canvas_token: Canvas API token
            course_id: Canvas course ID
            canvas_base_url: Canvas base URL
            api_timeout: API request timeout
            max_retries: Maximum retry attempts
        """
        self.canvas_token = canvas_token
        self.course_id = course_id
        self.canvas_base_url = canvas_base_url
        self.api_timeout = api_timeout
        self.max_retries = max_retries

        # Remove hardcoded configuration
        # Configuration now injected from settings

        logger.info(
            "content_extraction_service_initialized",
            course_id=course_id,
            base_url=canvas_base_url,
            timeout=api_timeout
        )
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   └── protocols.py              # NEW: Service protocols
│   ├── services/
│   │   ├── dependencies.py           # NEW: DI configuration
│   │   ├── mcq_generation.py         # UPDATE: Remove global instance
│   │   ├── content_extraction.py     # UPDATE: Constructor injection
│   │   └── canvas_quiz_export.py     # UPDATE: Constructor injection
│   ├── api/
│   │   ├── deps.py                   # UPDATE: Add service dependencies
│   │   └── routes/
│   │       └── quiz.py               # UPDATE: Use injected services
│   └── tests/
│       ├── conftest.py               # UPDATE: Service mocking
│       └── services/
│           └── test_dependencies.py   # NEW: DI tests
```

### Configuration Changes

```python
# app/core/config.py additions
class Settings(BaseSettings):
    # Service configuration
    ENABLE_SERVICE_CACHING: bool = True
    DEFAULT_DIFFICULTY: str = "medium"
    DEFAULT_TEMPERATURE: float = 0.7
```

## Testing Requirements

### Unit Tests with Dependency Injection

```python
# File: app/tests/conftest.py (UPDATED)
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.dependencies import (
    get_mcq_generation_service,
    get_quiz_export_service
)

@pytest.fixture
def mock_mcq_service():
    """Mock MCQ generation service."""
    service = Mock()
    service.generate_mcqs_for_quiz = AsyncMock(
        return_value={"task_id": "test-task-123", "status": "started"}
    )
    return service

@pytest.fixture
def mock_content_service():
    """Mock content extraction service."""
    service = Mock()
    service.extract_content_for_modules = AsyncMock(
        return_value={"module_1": ["content1", "content2"]}
    )
    return service

@pytest.fixture
def client_with_mocked_services(mock_mcq_service, mock_quiz_export_service):
    """Test client with mocked services."""

    # Override dependencies
    app.dependency_overrides[get_mcq_generation_service] = lambda: mock_mcq_service
    app.dependency_overrides[get_quiz_export_service] = lambda: mock_quiz_export_service

    client = TestClient(app)
    yield client

    # Clean up overrides
    app.dependency_overrides.clear()

# File: app/tests/api/test_quiz_routes.py
@pytest.mark.asyncio
async def test_generate_questions_with_mocked_service(
    client_with_mocked_services,
    test_user,
    test_quiz
):
    """Test question generation with mocked service."""

    response = client_with_mocked_services.post(
        f"/api/quiz/{test_quiz.id}/generate-questions",
        json={
            "target_question_count": 10,
            "model": "gpt-4",
            "temperature": 0.7
        },
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Question generation started"
    assert "task_id" in data

# File: app/tests/services/test_dependencies.py
def test_mcq_service_factory():
    """Test MCQ service factory configuration."""

    service = get_mcq_generation_service()

    assert isinstance(service, MCQGenerationService)
    assert service.max_questions_per_module > 0
    assert service.target_difficulty in ["easy", "medium", "hard"]

def test_mcq_service_singleton_behavior():
    """Test that service factory returns same instance."""

    service1 = get_mcq_generation_service()
    service2 = get_mcq_generation_service()

    assert service1 is service2  # Same instance due to lru_cache

def test_content_service_factory_with_parameters():
    """Test content service factory with parameters."""

    service = get_content_extraction_service(
        canvas_token="test-token",
        course_id=123,
        canvas_base_url="https://test.canvas.com"
    )

    assert service.canvas_token == "test-token"
    assert service.course_id == 123
    assert "test.canvas.com" in service.canvas_base_url

# File: app/tests/services/test_mcq_generation.py (UPDATED)
@pytest.mark.asyncio
async def test_mcq_generation_service_with_configuration():
    """Test service with different configurations."""

    # Test with caching enabled
    service_with_cache = MCQGenerationService(
        max_questions_per_module=5,
        enable_caching=True
    )

    # Test with caching disabled
    service_without_cache = MCQGenerationService(
        max_questions_per_module=10,
        enable_caching=False
    )

    assert service_with_cache.max_questions_per_module == 5
    assert service_without_cache.max_questions_per_module == 10
    assert service_with_cache._generation_cache is not None
    assert service_without_cache._generation_cache is None

@pytest.mark.asyncio
async def test_mcq_service_caching_behavior(db_session, test_quiz):
    """Test service caching behavior."""

    service = MCQGenerationService(enable_caching=True)

    # Mock the workflow execution
    with patch.object(service, '_execute_generation_workflow') as mock_workflow:
        mock_workflow.return_value = {"questions": [], "status": "completed"}

        # First call should execute workflow
        result1 = await service.generate_mcqs_for_quiz(
            test_quiz.id, 10, "gpt-4", 0.7, db_session
        )

        # Second call with same parameters should use cache
        result2 = await service.generate_mcqs_for_quiz(
            test_quiz.id, 10, "gpt-4", 0.7, db_session
        )

        # Workflow should only be called once
        assert mock_workflow.call_count == 1
        assert result1 == result2
```

### Integration Tests

```python
# File: app/tests/integration/test_service_integration.py
@pytest.mark.asyncio
async def test_full_quiz_generation_flow_with_di(
    client,
    test_user,
    mock_canvas_api
):
    """Test complete quiz generation flow with dependency injection."""

    # Create quiz
    quiz_data = {
        "title": "Test Quiz",
        "description": "Integration test quiz",
        "canvas_course_id": 123,
        "selected_modules": {"456": "Test Module"}
    }

    response = client.post(
        "/api/quiz/",
        json=quiz_data,
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )

    assert response.status_code == 200
    quiz = response.json()

    # Generate questions
    generation_request = {
        "target_question_count": 5,
        "model": "gpt-4",
        "temperature": 0.7
    }

    response = client.post(
        f"/api/quiz/{quiz['id']}/generate-questions",
        json=generation_request,
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )

    assert response.status_code == 200
    assert "task_id" in response.json()
```

## Code Quality Improvements

### Type Safety with Protocols

```python
# Enhanced type checking for dependency injection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.protocols import MCQGenerationServiceProtocol

def use_mcq_service(service: "MCQGenerationServiceProtocol") -> None:
    """Function that accepts any MCQ service implementation."""
    # Type checker ensures service has required methods
    pass
```

### Service Health Checks

```python
# File: app/api/routes/health.py
@router.get("/services")
async def check_services_health(
    mcq_service: MCQServiceDep,
    quiz_export_service: QuizExportServiceDep
) -> Dict[str, str]:
    """Check health of injected services."""

    health_status = {}

    # Check MCQ service
    try:
        # Basic health check
        health_status["mcq_generation"] = "healthy"
    except Exception as e:
        health_status["mcq_generation"] = f"unhealthy: {str(e)}"

    # Check export service
    try:
        health_status["quiz_export"] = "healthy"
    except Exception as e:
        health_status["quiz_export"] = f"unhealthy: {str(e)}"

    return health_status
```

## Migration Strategy

### Phase 1: Add DI Infrastructure (Day 1)

1. Create `protocols.py` and `dependencies.py`
2. Add service factory functions
3. Update existing services to accept configuration

### Phase 2: Update Routes (Day 2)

1. Update quiz routes to use dependency injection
2. Update background tasks to accept service instances
3. Add service override mechanism for testing

### Phase 3: Testing & Validation (Day 3)

1. Update all tests to use mocked services
2. Add integration tests with real services
3. Validate performance and behavior

### Rollback Plan

```python
# Feature flag for gradual migration
if settings.USE_DEPENDENCY_INJECTION:
    mcq_service: MCQServiceDep = Depends(get_mcq_generation_service)
else:
    # Fallback to global service
    from app.services.mcq_generation import mcq_generation_service
    mcq_service = mcq_generation_service
```

## Success Criteria

### Code Quality Metrics

- **Test Coverage**: >95% for service layer
- **Type Coverage**: 100% for service interfaces
- **Mocking Success**: All services mockable in tests
- **Dependency Count**: Zero global service instances

### Performance Metrics

- No performance regression from DI overhead
- Service initialization < 10ms
- Memory usage stable (no leaks from service instances)

---
