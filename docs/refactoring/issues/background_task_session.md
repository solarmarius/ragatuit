# 4. Background Task Session Management

## Priority: Critical

**Estimated Effort**: 2 days
**Python Version**: 3.10+
**Dependencies**: SQLAlchemy 2.0+, asyncio

## Problem Statement

### Current Situation

Background tasks in `quiz.py` create new database sessions using `with Session(engine)` without proper connection management, transaction boundaries, or error recovery. This can lead to connection leaks and inconsistent data states.

### Why It's a Problem

- **Connection Leaks**: Sessions may not be properly closed on errors
- **Transaction Issues**: No proper transaction isolation for concurrent updates
- **Race Conditions**: Multiple tasks can update same quiz simultaneously
- **Resource Exhaustion**: Each task creates new connection without pooling
- **Data Inconsistency**: Partial updates on failures

### Affected Modules

- `app/api/routes/quiz.py` (lines 281-398, 400-500)
- All background tasks
- Database connection pool
- Quiz state management

### Technical Debt Assessment

- **Risk Level**: Critical - Can cause data corruption
- **Impact**: All asynchronous operations
- **Cost of Delay**: Increases with concurrent users

## Current Implementation Analysis

```python
# File: app/api/routes/quiz.py (lines 281-300)
async def extract_content_for_quiz(
    quiz_id: UUID, course_id: int, module_ids: list[int], canvas_token: str
) -> None:
    """Background task to extract content from Canvas modules for a quiz."""
    logger.info("content_extraction_started", quiz_id=str(quiz_id))

    # PROBLEM: Creating new session without proper management
    with Session(engine) as session:
        try:
            # PROBLEM: No transaction isolation
            stmt = select(Quiz).where(Quiz.id == quiz_id).with_for_update()
            quiz = session.exec(stmt).first()

            # ... processing ...

            # PROBLEM: Multiple commits without transaction boundary
            quiz.content_extraction_status = "processing"
            session.add(quiz)
            session.commit()

        except Exception as e:
            # PROBLEM: Session might not rollback properly
            logger.error("content_extraction_failed", error=str(e))
```

### Python Anti-patterns Identified

- **Resource Management**: No context manager for async operations
- **Transaction Boundaries**: Multiple commits in single operation
- **Error Handling**: Incomplete rollback on failures
- **Concurrency**: No protection against race conditions
- **Async/Sync Mixing**: Using sync Session in async function

## Proposed Solution

### Pythonic Approach

Implement proper async session management with transaction boundaries, optimistic locking, and the Unit of Work pattern for background tasks.

### Design Patterns

- **Unit of Work**: Transaction boundary management
- **Repository Pattern**: Abstract database operations
- **Saga Pattern**: For multi-step operations
- **Circuit Breaker**: For external service calls

### Code Examples

```python
# File: app/core/async_db.py (NEW)
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, TypeVar, Callable
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
import asyncio
from datetime import datetime
import uuid

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("async_database")

T = TypeVar('T')

# Create async engine
async_engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI.replace(
        "postgresql://", "postgresql+asyncpg://"
    ),
    pool_size=10,  # Smaller pool for background tasks
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.ENVIRONMENT == "local"
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

class AsyncDatabaseSession:
    """
    Async context manager for database sessions with proper transaction handling.
    """

    def __init__(self, isolation_level: Optional[str] = None):
        self.isolation_level = isolation_level
        self.session: Optional[AsyncSession] = None
        self.transaction_id = str(uuid.uuid4())

    async def __aenter__(self) -> AsyncSession:
        """Create and configure session."""
        self.session = AsyncSessionLocal()

        if self.isolation_level:
            await self.session.execute(
                f"SET TRANSACTION ISOLATION LEVEL {self.isolation_level}"
            )

        logger.debug(
            "async_session_started",
            transaction_id=self.transaction_id,
            isolation_level=self.isolation_level
        )

        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Handle session cleanup and commit/rollback."""
        if not self.session:
            return

        try:
            if exc_type is None:
                await self.session.commit()
                logger.debug(
                    "async_session_committed",
                    transaction_id=self.transaction_id
                )
            else:
                await self.session.rollback()
                logger.warning(
                    "async_session_rollback",
                    transaction_id=self.transaction_id,
                    error_type=exc_type.__name__,
                    error=str(exc_val)
                )
        finally:
            await self.session.close()
            logger.debug(
                "async_session_closed",
                transaction_id=self.transaction_id
            )

class BackgroundTaskManager:
    """
    Manager for background task execution with proper resource management.
    """

    def __init__(self):
        self.active_tasks: dict[str, asyncio.Task] = {}
        self.task_results: dict[str, Any] = {}

    async def execute_with_transaction(
        self,
        task_id: str,
        operation: Callable[[AsyncSession], Awaitable[T]],
        isolation_level: str = "READ COMMITTED"
    ) -> T:
        """
        Execute operation within a transaction.

        Args:
            task_id: Unique task identifier
            operation: Async function to execute
            isolation_level: Transaction isolation level

        Returns:
            Operation result
        """
        logger.info(
            "background_task_started",
            task_id=task_id
        )

        try:
            async with AsyncDatabaseSession(isolation_level) as session:
                result = await operation(session)
                self.task_results[task_id] = {
                    "status": "completed",
                    "result": result,
                    "completed_at": datetime.utcnow()
                }
                return result

        except Exception as e:
            logger.error(
                "background_task_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True
            )
            self.task_results[task_id] = {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow()
            }
            raise

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get task execution status."""
        return self.task_results.get(task_id)

# Global instance
background_task_manager = BackgroundTaskManager()

# File: app/services/background/quiz_tasks.py (NEW)
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import StaleDataError
from typing import Optional
import asyncio

from app.core.async_db import AsyncDatabaseSession
from app.core.logging_config import get_logger
from app.models import Quiz
from app.services.content_extraction import ContentExtractionService

logger = get_logger("quiz_background_tasks")

class QuizBackgroundTasks:
    """
    Background tasks for quiz operations with proper transaction management.
    """

    @staticmethod
    async def extract_content_with_transaction(
        quiz_id: UUID,
        course_id: int,
        module_ids: list[int],
        canvas_token: str
    ) -> dict[str, Any]:
        """
        Extract content with proper transaction and state management.
        """
        async with AsyncDatabaseSession("REPEATABLE READ") as session:
            # Get quiz with lock to prevent concurrent updates
            result = await session.execute(
                select(Quiz)
                .where(Quiz.id == quiz_id)
                .with_for_update(skip_locked=True)
            )
            quiz = result.scalar_one_or_none()

            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found or locked")

            # Check if already processing
            if quiz.content_extraction_status == "processing":
                logger.warning(
                    "quiz_already_processing",
                    quiz_id=str(quiz_id)
                )
                return {"status": "already_processing"}

            # Update status atomically
            quiz.content_extraction_status = "processing"
            quiz.updated_at = datetime.utcnow()
            await session.commit()

        # Perform extraction outside transaction
        try:
            extraction_service = ContentExtractionService(
                canvas_token,
                course_id
            )
            extracted_content = await extraction_service.extract_content_for_modules(
                module_ids
            )

            # Update quiz with results in new transaction
            async with AsyncDatabaseSession() as session:
                # Re-fetch quiz to avoid stale data
                result = await session.execute(
                    select(Quiz).where(Quiz.id == quiz_id)
                )
                quiz = result.scalar_one()

                quiz.content_dict = extracted_content
                quiz.content_extraction_status = "completed"
                quiz.content_extracted_at = datetime.utcnow()
                quiz.updated_at = datetime.utcnow()

                await session.commit()

                return {
                    "status": "completed",
                    "modules_processed": len(extracted_content),
                    "quiz_id": str(quiz_id)
                }

        except Exception as e:
            # Update status on failure
            async with AsyncDatabaseSession() as session:
                await session.execute(
                    update(Quiz)
                    .where(Quiz.id == quiz_id)
                    .values(
                        content_extraction_status="failed",
                        updated_at=datetime.utcnow()
                    )
                )
                await session.commit()
            raise

class TaskOrchestrator:
    """
    Orchestrates complex multi-step background operations.
    """

    def __init__(self):
        self.steps_completed = {}

    async def run_quiz_generation_pipeline(
        self,
        quiz_id: UUID,
        canvas_token: str
    ) -> dict[str, Any]:
        """
        Run complete quiz generation pipeline with compensation.
        """
        pipeline_id = f"pipeline_{quiz_id}"
        self.steps_completed[pipeline_id] = []

        try:
            # Step 1: Load quiz data
            quiz_data = await self._load_quiz_data(quiz_id)
            self.steps_completed[pipeline_id].append("load_quiz")

            # Step 2: Extract content
            if quiz_data["content_extraction_status"] != "completed":
                await QuizBackgroundTasks.extract_content_with_transaction(
                    quiz_id,
                    quiz_data["canvas_course_id"],
                    quiz_data["module_ids"],
                    canvas_token
                )
                self.steps_completed[pipeline_id].append("extract_content")

            # Step 3: Generate questions
            await self._generate_questions(quiz_id)
            self.steps_completed[pipeline_id].append("generate_questions")

            return {
                "status": "completed",
                "steps": self.steps_completed[pipeline_id]
            }

        except Exception as e:
            # Compensate completed steps
            await self._compensate_pipeline(pipeline_id, quiz_id)
            raise

    async def _compensate_pipeline(
        self,
        pipeline_id: str,
        quiz_id: UUID
    ):
        """Rollback completed steps on failure."""
        completed = self.steps_completed.get(pipeline_id, [])

        if "generate_questions" in completed:
            # Delete generated questions
            async with AsyncDatabaseSession() as session:
                await session.execute(
                    "DELETE FROM question WHERE quiz_id = :quiz_id",
                    {"quiz_id": quiz_id}
                )
                await session.commit()

        # Reset quiz status
        async with AsyncDatabaseSession() as session:
            await session.execute(
                update(Quiz)
                .where(Quiz.id == quiz_id)
                .values(
                    content_extraction_status="failed",
                    llm_generation_status="failed"
                )
            )
            await session.commit()

# File: app/api/routes/quiz.py (UPDATED)
from app.services.background.quiz_tasks import QuizBackgroundTasks
from app.core.async_db import background_task_manager

@router.post("/", response_model=Quiz)
async def create_new_quiz(
    quiz_data: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> Quiz:
    """Create a new quiz with proper background task management."""
    try:
        quiz = create_quiz(session, quiz_data, current_user.id)

        # Create task ID for tracking
        task_id = f"extract_content_{quiz.id}"

        # Schedule background task with proper management
        background_tasks.add_task(
            background_task_manager.execute_with_transaction,
            task_id,
            lambda session: QuizBackgroundTasks.extract_content_with_transaction(
                quiz.id,
                quiz_data.canvas_course_id,
                list(quiz_data.selected_modules.keys()),
                canvas_token
            )
        )

        logger.info(
            "quiz_creation_completed",
            quiz_id=str(quiz.id),
            task_id=task_id
        )

        return quiz

    except Exception as e:
        logger.error(
            "quiz_creation_failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to create quiz"
        )

# New endpoint for task status
@router.get("/{quiz_id}/task-status/{task_id}")
async def get_task_status(
    quiz_id: UUID,
    task_id: str,
    current_user: CurrentUser,
    session: SessionDep
) -> dict[str, Any]:
    """Get status of background task."""
    # Verify quiz ownership
    quiz = get_quiz_by_id(session, quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(404, "Quiz not found")

    status = background_task_manager.get_task_status(task_id)
    if not status:
        raise HTTPException(404, "Task not found")

    return status
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   ├── async_db.py             # NEW: Async session management
│   │   └── db.py                   # UPDATE: Add async engine
│   ├── services/
│   │   └── background/
│   │       ├── __init__.py         # NEW
│   │       ├── quiz_tasks.py       # NEW: Quiz background tasks
│   │       └── task_orchestrator.py # NEW: Multi-step operations
│   ├── api/
│   │   └── routes/
│   │       └── quiz.py             # UPDATE: Use new task system
│   └── tests/
│       └── background/
│           └── test_quiz_tasks.py   # NEW: Background task tests
```

### Database Changes

```sql
-- Add version column for optimistic locking
ALTER TABLE quiz ADD COLUMN version INTEGER DEFAULT 0;

-- Add index for background task queries
CREATE INDEX idx_quiz_extraction_status ON quiz(content_extraction_status)
WHERE content_extraction_status IN ('pending', 'processing');
```

### Dependencies

```toml
# pyproject.toml
[project.dependencies]
asyncpg = ">=0.29.0"
sqlalchemy = {version = ">=2.0.0", extras = ["asyncio"]}
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/background/test_quiz_tasks.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from uuid import uuid4

from app.services.background.quiz_tasks import QuizBackgroundTasks
from app.core.async_db import AsyncDatabaseSession

@pytest.mark.asyncio
async def test_extract_content_with_transaction_success():
    """Test successful content extraction with transaction."""
    quiz_id = uuid4()

    # Mock quiz
    mock_quiz = Mock()
    mock_quiz.id = quiz_id
    mock_quiz.content_extraction_status = "pending"

    # Mock session
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_quiz
    mock_session.execute.return_value = mock_result

    with patch('app.services.background.quiz_tasks.AsyncDatabaseSession') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_session

        # Mock extraction service
        with patch('app.services.background.quiz_tasks.ContentExtractionService') as mock_service:
            mock_extraction = AsyncMock()
            mock_extraction.extract_content_for_modules.return_value = {"module_1": []}
            mock_service.return_value = mock_extraction

            result = await QuizBackgroundTasks.extract_content_with_transaction(
                quiz_id, 123, [1, 2], "token"
            )

            assert result["status"] == "completed"
            assert mock_quiz.content_extraction_status == "processing"
            assert mock_session.commit.called

@pytest.mark.asyncio
async def test_extract_content_handles_concurrent_access():
    """Test handling of concurrent extraction attempts."""
    quiz_id = uuid4()

    # Simulate locked quiz
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None  # Locked
    mock_session.execute.return_value = mock_result

    with patch('app.services.background.quiz_tasks.AsyncDatabaseSession') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_session

        with pytest.raises(ValueError, match="not found or locked"):
            await QuizBackgroundTasks.extract_content_with_transaction(
                quiz_id, 123, [1, 2], "token"
            )

@pytest.mark.asyncio
async def test_task_orchestrator_compensation():
    """Test pipeline compensation on failure."""
    orchestrator = TaskOrchestrator()
    quiz_id = uuid4()

    # Set up completed steps
    pipeline_id = f"pipeline_{quiz_id}"
    orchestrator.steps_completed[pipeline_id] = [
        "load_quiz",
        "extract_content",
        "generate_questions"
    ]

    # Mock database operations
    mock_session = AsyncMock()

    with patch('app.services.background.quiz_tasks.AsyncDatabaseSession') as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_session

        await orchestrator._compensate_pipeline(pipeline_id, quiz_id)

        # Verify cleanup operations
        assert mock_session.execute.call_count >= 2  # Delete + update
```

### Integration Tests

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_background_pipeline(db_session, canvas_mock):
    """Test complete background task pipeline."""
    # Create quiz
    quiz = create_test_quiz(db_session)

    # Run extraction
    result = await QuizBackgroundTasks.extract_content_with_transaction(
        quiz.id,
        quiz.canvas_course_id,
        [123, 456],
        "test_token"
    )

    assert result["status"] == "completed"

    # Verify database state
    async with AsyncDatabaseSession() as session:
        updated_quiz = await session.get(Quiz, quiz.id)
        assert updated_quiz.content_extraction_status == "completed"
        assert updated_quiz.extracted_content is not None
```

## Code Quality Improvements

### Monitoring

```python
# Add metrics for background tasks
from prometheus_client import Counter, Histogram, Gauge

task_started = Counter('background_task_started', 'Background tasks started', ['task_type'])
task_completed = Counter('background_task_completed', 'Background tasks completed', ['task_type'])
task_failed = Counter('background_task_failed', 'Background tasks failed', ['task_type'])
task_duration = Histogram('background_task_duration', 'Task execution time', ['task_type'])
active_tasks = Gauge('background_tasks_active', 'Currently active tasks')

# Decorate task methods
def monitored_task(task_type: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            task_started.labels(task_type=task_type).inc()
            active_tasks.inc()

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                task_completed.labels(task_type=task_type).inc()
                return result
            except Exception as e:
                task_failed.labels(task_type=task_type).inc()
                raise
            finally:
                active_tasks.dec()
                task_duration.labels(task_type=task_type).observe(
                    time.time() - start_time
                )
        return wrapper
    return decorator
```

## Migration Strategy

### Phased Rollout

1. **Phase 1**: Deploy new async session management
2. **Phase 2**: Migrate one background task at a time
3. **Phase 3**: Add monitoring and alerting
4. **Phase 4**: Remove old implementation

### Feature Flags

```python
if settings.USE_ASYNC_BACKGROUND_TASKS:
    await QuizBackgroundTasks.extract_content_with_transaction(...)
else:
    # Legacy synchronous implementation
    extract_content_for_quiz(...)
```

## Success Criteria

### Performance Metrics

- **Task Success Rate**: >99%
- **Average Task Duration**: <30s for content extraction
- **Connection Pool Usage**: <50% under normal load
- **Concurrent Task Handling**: Support 100+ concurrent tasks

### Monitoring Queries

```sql
-- Check for stuck tasks
SELECT id, content_extraction_status, updated_at
FROM quiz
WHERE content_extraction_status = 'processing'
AND updated_at < NOW() - INTERVAL '1 hour';

-- Task completion stats
SELECT
    content_extraction_status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (content_extracted_at - created_at))) as avg_duration_seconds
FROM quiz
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY content_extraction_status;
```
