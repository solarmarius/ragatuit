# 15. Transaction Management in Background Tasks

## Priority: Critical

**Estimated Effort**: 2 days
**Python Version**: 3.10+
**Dependencies**: SQLAlchemy, SQLModel, asyncio

## Problem Statement

### Current Situation

Background tasks create new database sessions without proper transaction management, leading to potential data inconsistencies, connection leaks, and race conditions. The current implementation lacks proper transaction boundaries and error handling.

### Why It's a Problem

- **Data Inconsistency**: Partial updates when tasks fail mid-execution
- **Connection Leaks**: Sessions not properly closed on errors
- **Race Conditions**: Concurrent updates without proper locking
- **Resource Exhaustion**: Connection pool depletion
- **Debugging Difficulty**: Transaction state unclear in logs
- **Rollback Issues**: Cannot undo partial changes on failure

### Affected Modules

- `app/api/routes/quiz.py` - Background task implementations
- `app/services/mcq_generation.py` - Service-level database operations
- `app/core/db.py` - Database session management
- All background tasks accessing the database

### Technical Debt Assessment

- **Risk Level**: Critical - Can cause data corruption
- **Impact**: All background operations
- **Cost of Delay**: Increases with data volume

## Current Implementation Analysis

```python
# File: app/api/routes/quiz.py (current problematic pattern)
async def extract_content_for_quiz(
    quiz_id: UUID, course_id: int, module_ids: list[int], canvas_token: str
) -> None:
    """PROBLEM: Poor transaction management."""
    logger.info("content_extraction_started", quiz_id=str(quiz_id))

    # PROBLEM: New session without proper lifecycle management
    with Session(engine) as session:
        quiz = session.get(Quiz, quiz_id)
        if not quiz:
            return

        # PROBLEM: No transaction boundary defined
        quiz.content_extraction_status = "processing"
        session.commit()  # Commit 1

        try:
            # Extract content...
            service = ContentExtractionService(canvas_token, course_id)
            content = await service.extract_and_clean_content(module_ids)

            # PROBLEM: Long operation, holding connection
            quiz.extracted_content = json.dumps(content)
            quiz.content_extraction_status = "completed"
            session.commit()  # Commit 2 - What if this fails?

        except Exception as e:
            # PROBLEM: Status update might fail, leaving inconsistent state
            quiz.content_extraction_status = "failed"
            session.commit()  # Commit 3 - Might fail too!
            raise

# File: app/services/mcq_generation.py (transaction issues)
async def save_questions_to_database(self, state: MCQGenerationState):
    """PROBLEM: No proper transaction management."""
    quiz_id = UUID(state["quiz_id"])
    questions = state["generated_questions"]

    # PROBLEM: Each service creating its own session
    with Session(engine) as session:
        # PROBLEM: No isolation level specified
        for question_data in questions:
            question = Question(
                quiz_id=quiz_id,
                **question_data
            )
            session.add(question)

        # PROBLEM: Single commit for bulk operation
        # If it fails, all questions lost
        session.commit()
```

### Current Failure Scenarios

```python
# Scenario 1: Connection leak on error
async def bad_background_task(quiz_id: UUID):
    with Session(engine) as session:  # Opens connection
        quiz = session.get(Quiz, quiz_id)
        quiz.status = "processing"
        session.commit()

        # PROBLEM: If this fails, session might not close properly
        result = await external_api_call()  # Throws exception

        # Never reached, session cleanup uncertain
        quiz.status = "completed"
        session.commit()

# Scenario 2: Partial state updates
async def partial_update_task(quiz_id: UUID):
    with Session(engine) as session:
        quiz = session.get(Quiz, quiz_id)
        quiz.field1 = "updated"
        session.commit()  # Success

        # Some processing...

        quiz.field2 = "updated"
        session.commit()  # Fails - now field1 and field2 inconsistent

# Scenario 3: Race condition
# Task 1 and Task 2 both update same quiz
# No locking = last write wins, data loss
```

### Python Anti-patterns Identified

- **No Transaction Boundaries**: Multiple commits in single operation
- **Missing Context Managers**: Manual session management
- **No Isolation Levels**: Default isolation may be insufficient
- **Lack of Idempotency**: Tasks can't be safely retried
- **No Deadlock Handling**: Concurrent updates can deadlock

## Proposed Solution

### Pythonic Approach

Implement proper transaction management using context managers, async-compatible session handling, proper isolation levels, and idempotent task design with comprehensive error handling.

### Design Patterns

- **Unit of Work**: Single transaction per logical operation
- **Repository Pattern**: Centralized transaction management
- **Saga Pattern**: Compensating transactions for distributed operations
- **Retry Pattern**: Idempotent operations with backoff

### Code Examples

```python
# File: app/core/db.py (ENHANCED transaction management)
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import text
import structlog

logger = structlog.get_logger()

class TransactionManager:
    """Centralized transaction management with proper error handling."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self._session_factory = sessionmaker(
            bind=engine,
            expire_on_commit=False  # Prevent lazy loading issues
        )

    @contextmanager
    def transaction(
        self,
        isolation_level: Optional[str] = None,
        readonly: bool = False,
        retries: int = 3
    ) -> Generator[Session, None, None]:
        """
        Create a transactional session with proper management.

        Args:
            isolation_level: Transaction isolation level
            readonly: Whether this is a read-only transaction
            retries: Number of retries for deadlocks

        Yields:
            Session: Database session with transaction
        """
        attempt = 0
        while attempt <= retries:
            session = self._session_factory()

            try:
                # Set isolation level if specified
                if isolation_level:
                    session.connection().execution_options(
                        isolation_level=isolation_level
                    )

                # Set read-only if specified
                if readonly:
                    session.execute(text("SET TRANSACTION READ ONLY"))

                # Log transaction start
                logger.info(
                    "transaction_started",
                    isolation_level=isolation_level,
                    readonly=readonly,
                    attempt=attempt
                )

                yield session

                # Commit transaction
                session.commit()
                logger.info("transaction_committed")
                break

            except Exception as e:
                session.rollback()
                logger.error(
                    "transaction_failed",
                    error=str(e),
                    attempt=attempt,
                    exc_info=True
                )

                # Check if we should retry
                if attempt < retries and self._is_retryable_error(e):
                    attempt += 1
                    logger.info("transaction_retry", attempt=attempt)
                    continue

                raise

            finally:
                session.close()

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is retryable (deadlock, serialization failure)."""
        error_msg = str(error).lower()
        return any(term in error_msg for term in [
            "deadlock",
            "serialization failure",
            "concurrent update",
            "lock timeout"
        ])

# Async version
class AsyncTransactionManager:
    """Async-compatible transaction management."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._session_factory = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: Optional[str] = None,
        readonly: bool = False,
        retries: int = 3
    ) -> AsyncGenerator[AsyncSession, None]:
        """Async transaction context manager."""
        attempt = 0
        while attempt <= retries:
            async with self._session_factory() as session:
                try:
                    # Set transaction properties
                    if isolation_level or readonly:
                        await session.execute(
                            text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level or 'READ COMMITTED'}"
                                 + (" READ ONLY" if readonly else ""))
                        )

                    logger.info("async_transaction_started")

                    yield session

                    await session.commit()
                    logger.info("async_transaction_committed")
                    break

                except Exception as e:
                    await session.rollback()
                    logger.error(
                        "async_transaction_failed",
                        error=str(e),
                        attempt=attempt
                    )

                    if attempt < retries and self._is_retryable_error(e):
                        attempt += 1
                        continue

                    raise

# Global transaction managers
transaction_manager = TransactionManager(engine)
async_transaction_manager = AsyncTransactionManager(async_engine)

# File: app/services/background_tasks.py (NEW)
from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime
import hashlib
import json

@dataclass
class TaskContext:
    """Context for background task execution."""
    task_id: str
    task_name: str
    parameters: Dict[str, Any]
    attempt: int = 0
    max_attempts: int = 3
    idempotency_key: Optional[str] = None

class BackgroundTaskService:
    """Service for managing background tasks with transactions."""

    def __init__(self, transaction_manager: AsyncTransactionManager):
        self.tm = transaction_manager

    async def execute_with_transaction(
        self,
        context: TaskContext,
        task_func,
        isolation_level: str = "READ COMMITTED"
    ):
        """Execute background task with proper transaction management."""

        # Generate idempotency key if not provided
        if not context.idempotency_key:
            context.idempotency_key = self._generate_idempotency_key(context)

        logger.info(
            "background_task_started",
            task_id=context.task_id,
            task_name=context.task_name,
            attempt=context.attempt,
            idempotency_key=context.idempotency_key
        )

        try:
            async with self.tm.transaction(
                isolation_level=isolation_level,
                retries=context.max_attempts - context.attempt
            ) as session:
                # Check if task already completed (idempotency)
                if await self._is_task_completed(session, context.idempotency_key):
                    logger.info(
                        "background_task_already_completed",
                        idempotency_key=context.idempotency_key
                    )
                    return

                # Execute task function
                result = await task_func(session, context)

                # Mark task as completed
                await self._mark_task_completed(session, context, result)

                logger.info(
                    "background_task_completed",
                    task_id=context.task_id,
                    result=result
                )

                return result

        except Exception as e:
            logger.error(
                "background_task_failed",
                task_id=context.task_id,
                error=str(e),
                exc_info=True
            )

            # Record failure
            await self._record_task_failure(context, e)

            # Retry if attempts remaining
            if context.attempt < context.max_attempts:
                context.attempt += 1
                return await self.execute_with_transaction(context, task_func, isolation_level)

            raise

    def _generate_idempotency_key(self, context: TaskContext) -> str:
        """Generate deterministic idempotency key."""
        key_data = f"{context.task_name}:{json.dumps(context.parameters, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def _is_task_completed(self, session: AsyncSession, idempotency_key: str) -> bool:
        """Check if task already completed."""
        result = await session.execute(
            select(TaskExecution).where(
                TaskExecution.idempotency_key == idempotency_key,
                TaskExecution.status == "completed"
            )
        )
        return result.scalar_one_or_none() is not None

    async def _mark_task_completed(
        self,
        session: AsyncSession,
        context: TaskContext,
        result: Any
    ):
        """Mark task as completed."""
        execution = TaskExecution(
            task_id=context.task_id,
            task_name=context.task_name,
            idempotency_key=context.idempotency_key,
            status="completed",
            result=json.dumps(result) if result else None,
            completed_at=datetime.utcnow()
        )
        session.add(execution)

    async def _record_task_failure(self, context: TaskContext, error: Exception):
        """Record task failure for monitoring."""
        async with self.tm.transaction() as session:
            execution = TaskExecution(
                task_id=context.task_id,
                task_name=context.task_name,
                idempotency_key=context.idempotency_key,
                status="failed",
                error_message=str(error),
                attempt=context.attempt,
                failed_at=datetime.utcnow()
            )
            session.add(execution)

# File: app/api/routes/quiz.py (UPDATED with proper transactions)
from app.services.background_tasks import BackgroundTaskService, TaskContext

background_service = BackgroundTaskService(async_transaction_manager)

async def extract_content_for_quiz(
    quiz_id: UUID,
    course_id: int,
    module_ids: list[int],
    canvas_token: str,
    request_id: Optional[str] = None
) -> None:
    """Extract content with proper transaction management."""

    context = TaskContext(
        task_id=f"extract_{quiz_id}_{datetime.utcnow().timestamp()}",
        task_name="extract_content",
        parameters={
            "quiz_id": str(quiz_id),
            "course_id": course_id,
            "module_ids": module_ids
        }
    )

    async def task_implementation(session: AsyncSession, ctx: TaskContext):
        # Get quiz with row lock to prevent concurrent updates
        result = await session.execute(
            select(Quiz)
            .where(Quiz.id == quiz_id)
            .with_for_update()
        )
        quiz = result.scalar_one_or_none()

        if not quiz:
            raise ValueError(f"Quiz {quiz_id} not found")

        # Update status atomically
        quiz.content_extraction_status = "processing"
        await session.flush()  # Flush but don't commit yet

        # Extract content (outside transaction if possible)
        service = ContentExtractionService(canvas_token, course_id)
        content = await service.extract_and_clean_content(module_ids)

        # Update quiz with results
        quiz.extracted_content = json.dumps(content)
        quiz.content_extraction_status = "completed"
        quiz.content_extracted_at = datetime.utcnow()

        # All changes committed together
        return {"status": "completed", "content_size": len(content)}

    try:
        await background_service.execute_with_transaction(
            context,
            task_implementation,
            isolation_level="REPEATABLE READ"  # Prevent phantom reads
        )
    except Exception as e:
        # Handle failure with compensating transaction
        await mark_quiz_extraction_failed(quiz_id, str(e))

async def mark_quiz_extraction_failed(quiz_id: UUID, error: str):
    """Compensating transaction for failed extraction."""
    async with async_transaction_manager.transaction() as session:
        result = await session.execute(
            select(Quiz).where(Quiz.id == quiz_id).with_for_update()
        )
        quiz = result.scalar_one_or_none()

        if quiz:
            quiz.content_extraction_status = "failed"
            quiz.error_message = error
            quiz.failed_at = datetime.utcnow()

# File: app/services/mcq_generation.py (UPDATED)
class MCQGenerationService:
    def __init__(self, transaction_manager: AsyncTransactionManager):
        self.tm = transaction_manager

    async def save_questions_to_database(
        self,
        state: MCQGenerationState
    ) -> MCQGenerationState:
        """Save questions with proper transaction management."""

        quiz_id = UUID(state["quiz_id"])
        questions = state["generated_questions"]

        async with self.tm.transaction(isolation_level="SERIALIZABLE") as session:
            # Verify quiz exists and lock it
            result = await session.execute(
                select(Quiz)
                .where(Quiz.id == quiz_id)
                .with_for_update()
            )
            quiz = result.scalar_one_or_none()

            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found")

            # Bulk insert questions efficiently
            question_objects = []
            for idx, question_data in enumerate(questions):
                question = Question(
                    quiz_id=quiz_id,
                    question_text=question_data["question"],
                    correct_answer=question_data["correct_answer"],
                    incorrect_answers=question_data["incorrect_answers"],
                    explanation=question_data.get("explanation"),
                    order=idx,
                    generated_at=datetime.utcnow()
                )
                question_objects.append(question)

            # Use bulk insert for efficiency
            session.add_all(question_objects)

            # Update quiz statistics
            quiz.question_generation_status = "completed"
            quiz.questions_generated = len(questions)
            quiz.generation_completed_at = datetime.utcnow()

            # Single commit for entire operation
            logger.info(
                "questions_saved",
                quiz_id=str(quiz_id),
                count=len(questions)
            )

        state["save_status"] = "completed"
        return state

# File: app/models.py (ADD task execution tracking)
class TaskExecution(SQLModel, table=True):
    """Track background task executions for idempotency."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_id: str = Field(index=True)
    task_name: str = Field(index=True)
    idempotency_key: str = Field(unique=True, index=True)
    status: str  # pending, running, completed, failed
    result: Optional[str] = None
    error_message: Optional[str] = None
    attempt: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

# File: app/core/db.py (Connection pool monitoring)
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Monitor connection creation."""
    logger.info(
        "db_connection_created",
        connection_id=id(dbapi_connection)
    )

@event.listens_for(engine, "close")
def receive_close(dbapi_connection, connection_record):
    """Monitor connection closure."""
    logger.info(
        "db_connection_closed",
        connection_id=id(dbapi_connection)
    )

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Monitor connection checkout."""
    logger.debug(
        "db_connection_checkout",
        connection_id=id(dbapi_connection),
        pool_size=engine.pool.size(),
        checked_out=engine.pool.checkedout()
    )
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   └── db.py                    # UPDATE: Transaction managers
│   ├── services/
│   │   ├── background_tasks.py      # NEW: Task management service
│   │   └── mcq_generation.py        # UPDATE: Use transactions
│   ├── api/
│   │   └── routes/
│   │       └── quiz.py              # UPDATE: Background tasks
│   ├── models.py                    # ADD: TaskExecution model
│   ├── alembic/
│   │   └── versions/
│   │       └── xxx_task_execution.py # NEW: Migration
│   └── tests/
│       └── test_transactions.py     # NEW: Transaction tests
```

### Database Migration

```python
# alembic/versions/xxx_add_task_execution.py
"""Add task execution tracking

Revision ID: xxx
Revises: yyy
"""

def upgrade():
    op.create_table(
        'taskexecution',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('task_name', sa.String(), nullable=False),
        sa.Column('idempotency_key', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_taskexecution_task_id', 'taskexecution', ['task_id'])
    op.create_index('ix_taskexecution_task_name', 'taskexecution', ['task_name'])
    op.create_unique_constraint('uq_taskexecution_idempotency_key', 'taskexecution', ['idempotency_key'])

def downgrade():
    op.drop_table('taskexecution')
```

### Configuration

```python
# app/core/config.py additions
class Settings(BaseSettings):
    # Transaction settings
    DEFAULT_ISOLATION_LEVEL: str = "READ COMMITTED"
    BACKGROUND_TASK_ISOLATION: str = "REPEATABLE READ"
    TRANSACTION_TIMEOUT: int = 30  # seconds
    MAX_TRANSACTION_RETRIES: int = 3
    ENABLE_TRANSACTION_MONITORING: bool = True
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/core/test_transactions.py
import pytest
from sqlalchemy.exc import OperationalError
from app.core.db import transaction_manager, async_transaction_manager

def test_transaction_commit(session):
    """Test successful transaction commit."""
    with transaction_manager.transaction() as txn_session:
        user = User(name="Test User")
        txn_session.add(user)
        # Commit happens automatically

    # Verify committed
    assert session.query(User).filter_by(name="Test User").first() is not None

def test_transaction_rollback_on_error(session):
    """Test automatic rollback on error."""
    with pytest.raises(ValueError):
        with transaction_manager.transaction() as txn_session:
            user = User(name="Test User")
            txn_session.add(user)
            raise ValueError("Test error")

    # Verify rolled back
    assert session.query(User).filter_by(name="Test User").first() is None

@pytest.mark.asyncio
async def test_async_transaction_isolation():
    """Test transaction isolation levels."""
    async with async_transaction_manager.transaction(
        isolation_level="SERIALIZABLE"
    ) as session:
        # Should prevent phantom reads
        result = await session.execute(
            select(Quiz).where(Quiz.id == test_quiz_id)
        )
        quiz = result.scalar_one()

        # Another transaction shouldn't see uncommitted changes
        quiz.title = "Updated Title"
        await session.flush()

def test_transaction_retry_on_deadlock(monkeypatch):
    """Test retry logic for deadlocks."""
    attempt_count = 0

    def mock_commit(self):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise OperationalError("Deadlock detected", None, None)
        # Success on third attempt

    with transaction_manager.transaction(retries=3) as session:
        monkeypatch.setattr(session, "commit", mock_commit)
        # Should succeed after retries

    assert attempt_count == 3

@pytest.mark.asyncio
async def test_idempotent_task_execution():
    """Test idempotent background task execution."""
    service = BackgroundTaskService(async_transaction_manager)

    executed_count = 0

    async def test_task(session, context):
        nonlocal executed_count
        executed_count += 1
        return {"result": "success"}

    context = TaskContext(
        task_id="test-123",
        task_name="test_task",
        parameters={"param": "value"},
        idempotency_key="test-key-123"
    )

    # Execute twice with same idempotency key
    await service.execute_with_transaction(context, test_task)
    await service.execute_with_transaction(context, test_task)

    # Should only execute once
    assert executed_count == 1
```

### Integration Tests

```python
# File: app/tests/integration/test_background_transactions.py
@pytest.mark.asyncio
async def test_quiz_content_extraction_transaction(
    test_quiz,
    mock_canvas_api
):
    """Test content extraction with proper transactions."""

    # Run extraction task
    await extract_content_for_quiz(
        test_quiz.id,
        course_id=123,
        module_ids=[1, 2, 3],
        canvas_token="test-token"
    )

    # Verify atomic update
    async with async_transaction_manager.transaction(readonly=True) as session:
        result = await session.execute(
            select(Quiz).where(Quiz.id == test_quiz.id)
        )
        quiz = result.scalar_one()

        assert quiz.content_extraction_status == "completed"
        assert quiz.extracted_content is not None
        assert quiz.content_extracted_at is not None

@pytest.mark.asyncio
async def test_concurrent_quiz_updates():
    """Test handling of concurrent updates."""

    async def update_quiz_1(quiz_id):
        async with async_transaction_manager.transaction() as session:
            result = await session.execute(
                select(Quiz).where(Quiz.id == quiz_id).with_for_update()
            )
            quiz = result.scalar_one()
            await asyncio.sleep(0.1)  # Simulate work
            quiz.field1 = "updated_by_1"

    async def update_quiz_2(quiz_id):
        async with async_transaction_manager.transaction() as session:
            result = await session.execute(
                select(Quiz).where(Quiz.id == quiz_id).with_for_update()
            )
            quiz = result.scalar_one()
            quiz.field2 = "updated_by_2"

    # Run concurrently - should serialize due to locks
    quiz_id = create_test_quiz()
    await asyncio.gather(
        update_quiz_1(quiz_id),
        update_quiz_2(quiz_id)
    )

    # Both updates should succeed
    async with async_transaction_manager.transaction(readonly=True) as session:
        quiz = await session.get(Quiz, quiz_id)
        assert quiz.field1 == "updated_by_1"
        assert quiz.field2 == "updated_by_2"
```

## Code Quality Improvements

### Monitoring Transactions

```python
# Add transaction monitoring
from prometheus_client import Counter, Histogram, Gauge

transaction_duration = Histogram(
    'db_transaction_duration_seconds',
    'Database transaction duration',
    ['transaction_type', 'isolation_level']
)

transaction_total = Counter(
    'db_transactions_total',
    'Total database transactions',
    ['status', 'transaction_type']
)

active_transactions = Gauge(
    'db_active_transactions',
    'Currently active transactions'
)

transaction_retries = Counter(
    'db_transaction_retries_total',
    'Transaction retry attempts',
    ['reason']
)
```

## Migration Strategy

### Phase 1: Add Infrastructure
1. Implement transaction managers
2. Add TaskExecution model
3. Create monitoring

### Phase 2: Update Services
1. Update background tasks one by one
2. Add idempotency checks
3. Test retry logic

### Phase 3: Monitor and Optimize
1. Monitor transaction metrics
2. Tune isolation levels
3. Optimize long transactions

### Rollback Plan

```python
# Feature flag for new transaction management
if settings.USE_ENHANCED_TRANSACTIONS:
    manager = TransactionManager(engine)
else:
    # Use simple session context
    @contextmanager
    def get_session():
        session = Session(engine)
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
```

## Success Criteria

### Data Integrity Metrics

- **Transaction Success Rate**: >99.9%
- **Deadlock Rate**: <0.1% of transactions
- **Connection Leak Rate**: 0 leaks per day
- **Rollback Effectiveness**: 100% clean rollback

### Performance Metrics

- **Transaction Overhead**: <5ms per transaction
- **Retry Success Rate**: >95% within 3 attempts
- **Connection Pool Utilization**: <80% under normal load

### Monitoring Queries

```sql
-- Monitor long-running transactions
SELECT
    pid,
    age(clock_timestamp(), xact_start) AS duration,
    state,
    query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY duration DESC;

-- Check for lock contention
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- Transaction statistics
SELECT
    datname,
    xact_commit,
    xact_rollback,
    xact_rollback::float / (xact_commit + xact_rollback) AS rollback_ratio,
    deadlocks
FROM pg_stat_database
WHERE datname = current_database();
```

---
