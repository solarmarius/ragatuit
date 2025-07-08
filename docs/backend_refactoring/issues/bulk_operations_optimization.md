# 19. Bulk Operations Optimization

## Priority: Medium

**Estimated Effort**: 2 days
**Python Version**: 3.10+
**Dependencies**: SQLAlchemy 2.0+, PostgreSQL

## Problem Statement

### Current Situation

The application lacks optimized bulk operations for database interactions, particularly in question creation and approval workflows. Current implementations use individual inserts/updates in loops, causing performance bottlenecks.

### Why It's a Problem

- **Performance Degradation**: Individual operations are 10-100x slower
- **Database Load**: Excessive round trips to database
- **Transaction Overhead**: Each operation has transaction cost
- **Resource Usage**: Higher CPU and memory consumption
- **Scalability Issues**: Performance degrades linearly with data volume
- **User Experience**: Long wait times for bulk actions

### Affected Modules

- `app/services/mcq_generation.py` - Question saving
- `app/crud.py` - No bulk operation methods
- `app/api/routes/quiz.py` - Bulk approval endpoint
- All modules performing multiple database operations

### Technical Debt Assessment

- **Risk Level**: Medium - Significant performance impact
- **Impact**: All bulk data operations
- **Cost of Delay**: Increases with data growth

## Current Implementation Analysis

```python
# File: app/services/mcq_generation.py (current inefficient pattern)
async def save_questions_to_database(self, state: MCQGenerationState):
    """PROBLEM: Individual inserts in loop."""
    quiz_id = UUID(state["quiz_id"])
    questions = state["generated_questions"]

    with Session(engine) as session:
        # PROBLEM: N individual INSERT statements
        for question_data in questions:
            question = Question(
                quiz_id=quiz_id,
                question_text=question_data["question"],
                correct_answer=question_data["correct_answer"],
                incorrect_answers=question_data["incorrect_answers"],
            )
            session.add(question)  # Individual insert

        session.commit()  # Still one commit, but N inserts

# File: app/api/routes/quiz.py (bulk approval - inefficient)
@router.put("/{quiz_id}/questions/approve")
async def approve_questions_bulk(
    quiz_id: UUID,
    question_ids: list[UUID],
    session: SessionDep,
) -> dict:
    """PROBLEM: Individual updates."""

    approved_count = 0
    for question_id in question_ids:  # Loop through IDs
        question = session.get(Question, question_id)  # Individual SELECT
        if question and question.quiz_id == quiz_id:
            question.is_approved = True
            question.approved_at = datetime.utcnow()
            approved_count += 1

    session.commit()
    return {"approved": approved_count}

# Performance analysis:
# Saving 50 questions:
# - Current: 50 INSERT statements + 1 COMMIT
# - Time: ~500ms
# - Optimal: 1 bulk INSERT + 1 COMMIT
# - Time: ~50ms (10x faster)

# Approving 100 questions:
# - Current: 100 SELECT + 100 UPDATE + 1 COMMIT
# - Time: ~2000ms
# - Optimal: 1 bulk UPDATE + 1 COMMIT
# - Time: ~100ms (20x faster)
```

### Current Database Logs

```sql
-- Current pattern for saving questions (INEFFICIENT)
BEGIN;
INSERT INTO question (id, quiz_id, question_text, ...) VALUES ($1, $2, $3, ...);
INSERT INTO question (id, quiz_id, question_text, ...) VALUES ($4, $5, $6, ...);
INSERT INTO question (id, quiz_id, question_text, ...) VALUES ($7, $8, $9, ...);
-- ... 47 more individual INSERTs
COMMIT;

-- Current pattern for bulk approval (VERY INEFFICIENT)
BEGIN;
SELECT * FROM question WHERE id = $1;
UPDATE question SET is_approved = true, approved_at = $2 WHERE id = $3;
SELECT * FROM question WHERE id = $4;
UPDATE question SET is_approved = true, approved_at = $5 WHERE id = $6;
-- ... 98 more SELECT/UPDATE pairs
COMMIT;
```

### Python Anti-patterns Identified

- **Loop INSERT/UPDATE**: Database operations in loops
- **Missing Bulk Methods**: No bulk operation utilities
- **ORM Overhead**: Using ORM for bulk operations
- **No Batching**: Processing all items at once
- **Missing Indexes**: May need indexes for bulk filters

## Proposed Solution

### Pythonic Approach

Implement efficient bulk operations using SQLAlchemy's bulk methods, PostgreSQL-specific features, and proper batching strategies for optimal performance.

### Implementation Strategies

1. **Bulk INSERT**: Use `bulk_insert_mappings` or PostgreSQL COPY
2. **Bulk UPDATE**: Use `bulk_update_mappings` or single UPDATE with CASE
3. **Bulk DELETE**: Use single DELETE with IN clause
4. **Batching**: Process large datasets in chunks
5. **Upserts**: Use PostgreSQL ON CONFLICT for insert-or-update

### Code Examples

```python
# File: app/crud/bulk_operations.py (NEW)
from typing import List, Dict, Any, TypeVar, Type
from sqlalchemy import update, delete, select, and_, or_, func, case
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, SQLModel
import uuid
from datetime import datetime

T = TypeVar('T', bound=SQLModel)

class BulkOperations:
    """Optimized bulk database operations."""

    @staticmethod
    def bulk_insert(
        session: Session,
        model: Type[T],
        records: List[Dict[str, Any]],
        batch_size: int = 1000,
        return_ids: bool = False
    ) -> List[uuid.UUID]:
        """
        Efficient bulk insert with batching.

        Args:
            session: Database session
            model: SQLModel class
            records: List of dictionaries with record data
            batch_size: Number of records per batch
            return_ids: Whether to return inserted IDs

        Returns:
            List of inserted IDs if return_ids=True
        """
        if not records:
            return []

        inserted_ids = []

        # Process in batches
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            # Ensure IDs for all records
            for record in batch:
                if 'id' not in record:
                    record['id'] = uuid.uuid4()

            if return_ids:
                # Use ORM for ID tracking
                objects = [model(**record) for record in batch]
                session.add_all(objects)
                session.flush()
                inserted_ids.extend([obj.id for obj in objects])
            else:
                # Use bulk_insert_mappings for speed
                session.bulk_insert_mappings(model, batch)

        return inserted_ids

    @staticmethod
    def bulk_update(
        session: Session,
        model: Type[T],
        records: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """
        Efficient bulk update.

        Args:
            session: Database session
            model: SQLModel class
            records: List of dicts with 'id' and fields to update
            batch_size: Number of records per batch

        Returns:
            Number of records updated
        """
        if not records:
            return 0

        updated_count = 0

        # Process in batches
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            # Use bulk_update_mappings
            session.bulk_update_mappings(model, batch)
            updated_count += len(batch)

        return updated_count

    @staticmethod
    def bulk_update_where(
        session: Session,
        model: Type[T],
        values: Dict[str, Any],
        filter_column: str,
        filter_values: List[Any],
        batch_size: int = 1000
    ) -> int:
        """
        Update multiple records with same values.

        Example: Set is_approved=True for list of IDs
        """
        if not filter_values:
            return 0

        total_updated = 0

        # Process in batches to avoid huge IN clauses
        for i in range(0, len(filter_values), batch_size):
            batch_values = filter_values[i:i + batch_size]

            stmt = (
                update(model)
                .where(getattr(model, filter_column).in_(batch_values))
                .values(**values)
            )

            result = session.execute(stmt)
            total_updated += result.rowcount

        return total_updated

    @staticmethod
    def bulk_upsert(
        session: Session,
        model: Type[T],
        records: List[Dict[str, Any]],
        unique_fields: List[str],
        update_fields: List[str],
        batch_size: int = 1000
    ) -> int:
        """
        PostgreSQL upsert (INSERT ON CONFLICT UPDATE).

        Args:
            unique_fields: Fields that determine uniqueness
            update_fields: Fields to update on conflict
        """
        if not records:
            return 0

        upserted_count = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            # Prepare insert statement
            stmt = insert(model.__table__).values(batch)

            # Add ON CONFLICT clause
            update_dict = {
                field: getattr(stmt.excluded, field)
                for field in update_fields
            }

            stmt = stmt.on_conflict_do_update(
                index_elements=unique_fields,
                set_=update_dict
            )

            result = session.execute(stmt)
            upserted_count += result.rowcount

        return upserted_count

    @staticmethod
    def bulk_delete(
        session: Session,
        model: Type[T],
        filter_column: str,
        filter_values: List[Any],
        batch_size: int = 1000
    ) -> int:
        """Efficient bulk delete."""
        if not filter_values:
            return 0

        total_deleted = 0

        for i in range(0, len(filter_values), batch_size):
            batch_values = filter_values[i:i + batch_size]

            stmt = delete(model).where(
                getattr(model, filter_column).in_(batch_values)
            )

            result = session.execute(stmt)
            total_deleted += result.rowcount

        return total_deleted

# File: app/services/mcq_generation.py (UPDATED with bulk operations)
from app.crud.bulk_operations import BulkOperations

class MCQGenerationService:
    async def save_questions_to_database(
        self,
        state: MCQGenerationState
    ) -> MCQGenerationState:
        """Save questions using bulk operations."""

        quiz_id = UUID(state["quiz_id"])
        questions = state["generated_questions"]

        with Session(engine) as session:
            # Prepare bulk data
            question_records = []
            for idx, question_data in enumerate(questions):
                question_records.append({
                    "id": uuid.uuid4(),
                    "quiz_id": quiz_id,
                    "question_text": question_data["question"],
                    "correct_answer": question_data["correct_answer"],
                    "incorrect_answers": question_data["incorrect_answers"],
                    "explanation": question_data.get("explanation"),
                    "difficulty": question_data.get("difficulty", "medium"),
                    "order": idx,
                    "created_at": datetime.utcnow(),
                    "is_approved": False,
                })

            # Bulk insert all questions
            inserted_ids = BulkOperations.bulk_insert(
                session,
                Question,
                question_records,
                return_ids=True
            )

            # Update quiz stats in single query
            stmt = (
                update(Quiz)
                .where(Quiz.id == quiz_id)
                .values(
                    question_generation_status="completed",
                    questions_generated=len(questions),
                    generation_completed_at=datetime.utcnow()
                )
            )
            session.execute(stmt)

            session.commit()

            logger.info(
                "questions_bulk_saved",
                quiz_id=str(quiz_id),
                count=len(questions),
                method="bulk_insert"
            )

        state["saved_question_ids"] = [str(id) for id in inserted_ids]
        return state

# File: app/api/routes/quiz.py (UPDATED bulk endpoints)
from app.crud.bulk_operations import BulkOperations

@router.put("/{quiz_id}/questions/approve")
async def approve_questions_bulk(
    quiz_id: UUID,
    request: BulkApprovalRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> dict:
    """Approve multiple questions efficiently."""

    # Verify quiz ownership
    quiz = get_quiz_by_id(session, quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Bulk update with ownership check
    values = {
        "is_approved": True,
        "approved_at": datetime.utcnow(),
        "approved_by": current_user.id
    }

    # Use efficient bulk update
    updated_count = BulkOperations.bulk_update_where(
        session,
        Question,
        values,
        filter_column="id",
        filter_values=request.question_ids
    )

    session.commit()

    logger.info(
        "bulk_approval_completed",
        quiz_id=str(quiz_id),
        requested_count=len(request.question_ids),
        updated_count=updated_count
    )

    return {
        "approved": updated_count,
        "requested": len(request.question_ids)
    }

@router.post("/{quiz_id}/questions/bulk-create")
async def create_questions_bulk(
    quiz_id: UUID,
    questions: List[QuestionCreate],
    current_user: CurrentUser,
    session: SessionDep,
) -> dict:
    """Create multiple questions efficiently."""

    # Verify quiz ownership
    quiz = get_quiz_by_id(session, quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Prepare bulk data
    question_records = [
        {
            **question.model_dump(),
            "quiz_id": quiz_id,
            "created_at": datetime.utcnow(),
            "created_by": current_user.id
        }
        for question in questions
    ]

    # Bulk insert
    inserted_ids = BulkOperations.bulk_insert(
        session,
        Question,
        question_records,
        return_ids=True
    )

    session.commit()

    return {
        "created": len(inserted_ids),
        "question_ids": [str(id) for id in inserted_ids]
    }

@router.delete("/{quiz_id}/questions")
async def delete_questions_bulk(
    quiz_id: UUID,
    question_ids: List[UUID],
    current_user: CurrentUser,
    session: SessionDep,
) -> dict:
    """Delete multiple questions efficiently."""

    # Verify quiz ownership
    quiz = get_quiz_by_id(session, quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Bulk delete with ownership check
    deleted_count = BulkOperations.bulk_delete(
        session,
        Question,
        filter_column="id",
        filter_values=question_ids
    )

    session.commit()

    return {"deleted": deleted_count}

# File: app/crud.py (UPDATED with bulk operations)
def create_questions_bulk(
    session: Session,
    quiz_id: UUID,
    questions_data: List[Dict[str, Any]]
) -> List[Question]:
    """Create multiple questions efficiently."""

    records = [
        {
            "quiz_id": quiz_id,
            "created_at": datetime.utcnow(),
            **data
        }
        for data in questions_data
    ]

    ids = BulkOperations.bulk_insert(
        session,
        Question,
        records,
        return_ids=True
    )

    # Return created questions
    return session.exec(
        select(Question).where(Question.id.in_(ids))
    ).all()

def update_questions_bulk(
    session: Session,
    updates: List[Dict[str, Any]]
) -> int:
    """Update multiple questions with different values."""

    # Each dict must have 'id' and fields to update
    return BulkOperations.bulk_update(
        session,
        Question,
        updates
    )

def approve_questions_by_quiz(
    session: Session,
    quiz_id: UUID,
    question_ids: Optional[List[UUID]] = None
) -> int:
    """Approve all or specific questions for a quiz."""

    if question_ids:
        # Approve specific questions
        stmt = (
            update(Question)
            .where(
                and_(
                    Question.quiz_id == quiz_id,
                    Question.id.in_(question_ids)
                )
            )
            .values(
                is_approved=True,
                approved_at=datetime.utcnow()
            )
        )
    else:
        # Approve all questions
        stmt = (
            update(Question)
            .where(Question.quiz_id == quiz_id)
            .values(
                is_approved=True,
                approved_at=datetime.utcnow()
            )
        )

    result = session.execute(stmt)
    return result.rowcount

# File: app/utils/bulk_helpers.py (NEW - Bulk operation utilities)
from typing import List, Dict, Any, Iterator
import pandas as pd
from io import StringIO

class BulkHelpers:
    """Utilities for bulk operations."""

    @staticmethod
    def chunk_list(
        items: List[Any],
        chunk_size: int
    ) -> Iterator[List[Any]]:
        """Split list into chunks."""
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]

    @staticmethod
    def prepare_bulk_data(
        dataframe: pd.DataFrame,
        model_fields: List[str]
    ) -> List[Dict[str, Any]]:
        """Convert DataFrame to bulk insert format."""

        # Filter to only model fields
        df_filtered = dataframe[model_fields]

        # Convert to list of dicts
        return df_filtered.to_dict('records')

    @staticmethod
    def generate_copy_statement(
        table_name: str,
        columns: List[str],
        data: List[List[Any]]
    ) -> tuple[str, str]:
        """
        Generate PostgreSQL COPY statement for ultimate performance.

        Returns:
            Tuple of (COPY statement, CSV data)
        """

        # Create CSV data
        output = StringIO()
        for row in data:
            # Handle None values and escaping
            csv_row = []
            for value in row:
                if value is None:
                    csv_row.append('\\N')
                else:
                    # Escape special characters
                    str_value = str(value).replace('\\', '\\\\').replace('\n', '\\n')
                    csv_row.append(str_value)

            output.write('\t'.join(csv_row) + '\n')

        copy_stmt = f"COPY {table_name} ({','.join(columns)}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')"

        return copy_stmt, output.getvalue()

# Example using COPY for maximum performance
class SuperBulkOperations:
    """Ultra-fast bulk operations using PostgreSQL COPY."""

    @staticmethod
    async def copy_insert(
        session: Session,
        table_name: str,
        columns: List[str],
        data: List[List[Any]]
    ) -> int:
        """
        Use PostgreSQL COPY for fastest possible insert.

        Note: Bypasses ORM validation!
        """

        copy_stmt, csv_data = BulkHelpers.generate_copy_statement(
            table_name, columns, data
        )

        # Use raw connection for COPY
        connection = session.connection()
        cursor = connection.connection.cursor()

        cursor.copy_expert(copy_stmt, StringIO(csv_data))

        return cursor.rowcount
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── crud/
│   │   ├── bulk_operations.py       # NEW: Bulk operations
│   │   └── __init__.py              # UPDATE: Export bulk ops
│   ├── crud.py                      # UPDATE: Add bulk methods
│   ├── services/
│   │   └── mcq_generation.py        # UPDATE: Use bulk insert
│   ├── api/
│   │   └── routes/
│   │       └── quiz.py              # UPDATE: Bulk endpoints
│   ├── utils/
│   │   └── bulk_helpers.py          # NEW: Bulk utilities
│   └── tests/
│       └── test_bulk_operations.py  # NEW: Bulk tests
```

### Database Indexes for Bulk Operations

```sql
-- Ensure indexes for bulk operations
CREATE INDEX IF NOT EXISTS idx_question_quiz_id_id
ON question(quiz_id, id);

CREATE INDEX IF NOT EXISTS idx_question_quiz_id_approved
ON question(quiz_id, is_approved);

-- For bulk updates by multiple fields
CREATE INDEX IF NOT EXISTS idx_question_composite
ON question(quiz_id, is_approved, created_at);
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/crud/test_bulk_operations.py
import pytest
from app.crud.bulk_operations import BulkOperations
from app.models import Question
import time

def test_bulk_insert_performance(session, test_quiz):
    """Test bulk insert is faster than individual."""

    # Prepare test data
    questions_data = [
        {
            "quiz_id": test_quiz.id,
            "question_text": f"Question {i}",
            "correct_answer": f"Answer {i}",
            "incorrect_answers": [f"Wrong {i}.1", f"Wrong {i}.2", f"Wrong {i}.3"]
        }
        for i in range(100)
    ]

    # Time individual inserts
    start = time.time()
    for data in questions_data[:50]:
        q = Question(**data)
        session.add(q)
    session.commit()
    individual_time = time.time() - start

    # Time bulk insert
    start = time.time()
    BulkOperations.bulk_insert(
        session,
        Question,
        questions_data[50:]
    )
    session.commit()
    bulk_time = time.time() - start

    # Bulk should be significantly faster
    assert bulk_time < individual_time * 0.5

    # Verify all inserted
    count = session.query(Question).filter_by(quiz_id=test_quiz.id).count()
    assert count == 100

def test_bulk_update(session, test_questions):
    """Test bulk update functionality."""

    # Prepare updates
    updates = [
        {
            "id": q.id,
            "is_approved": True,
            "difficulty": "hard"
        }
        for q in test_questions[:10]
    ]

    # Perform bulk update
    updated = BulkOperations.bulk_update(
        session,
        Question,
        updates
    )
    session.commit()

    assert updated == 10

    # Verify updates
    for q in test_questions[:10]:
        session.refresh(q)
        assert q.is_approved is True
        assert q.difficulty == "hard"

def test_bulk_upsert(session, test_quiz):
    """Test upsert functionality."""

    # Mix of new and existing records
    records = [
        {
            "quiz_id": test_quiz.id,
            "question_text": "New Question",
            "correct_answer": "New Answer",
            "incorrect_answers": ["W1", "W2", "W3"]
        },
        {
            "id": test_quiz.questions[0].id,  # Existing
            "quiz_id": test_quiz.id,
            "question_text": "Updated Question",
            "correct_answer": "Updated Answer",
            "incorrect_answers": ["U1", "U2", "U3"]
        }
    ]

    upserted = BulkOperations.bulk_upsert(
        session,
        Question,
        records,
        unique_fields=["id"],
        update_fields=["question_text", "correct_answer"]
    )

    session.commit()
    assert upserted == 2

@pytest.mark.benchmark
def test_bulk_operation_scaling(benchmark, session):
    """Test bulk operations scale well."""

    def bulk_insert_1000():
        records = [
            {
                "quiz_id": uuid.uuid4(),
                "question_text": f"Q{i}",
                "correct_answer": f"A{i}",
                "incorrect_answers": ["W1", "W2", "W3"]
            }
            for i in range(1000)
        ]

        BulkOperations.bulk_insert(session, Question, records)
        session.commit()
        session.rollback()  # Don't actually save

    # Should complete in reasonable time
    result = benchmark(bulk_insert_1000)
    assert benchmark.stats['mean'] < 1.0  # Less than 1 second
```

### Performance Tests

```python
# File: app/tests/performance/test_bulk_performance.py
import pytest
from app.crud.bulk_operations import BulkOperations, SuperBulkOperations

@pytest.mark.performance
def test_bulk_methods_comparison(session, test_quiz):
    """Compare different bulk methods."""

    results = {}
    data_sizes = [100, 1000, 5000]

    for size in data_sizes:
        records = generate_test_questions(test_quiz.id, size)

        # Method 1: Individual inserts
        start = time.time()
        for record in records[:size//3]:
            q = Question(**record)
            session.add(q)
        session.commit()
        session.rollback()
        results[f'individual_{size}'] = time.time() - start

        # Method 2: Bulk insert mappings
        start = time.time()
        BulkOperations.bulk_insert(
            session,
            Question,
            records[size//3:2*size//3]
        )
        session.commit()
        session.rollback()
        results[f'bulk_mappings_{size}'] = time.time() - start

        # Method 3: PostgreSQL COPY
        start = time.time()
        data_lists = [
            [r['id'], r['quiz_id'], r['question_text'], ...]
            for r in records[2*size//3:]
        ]
        SuperBulkOperations.copy_insert(
            session,
            'question',
            ['id', 'quiz_id', 'question_text', ...],
            data_lists
        )
        session.commit()
        session.rollback()
        results[f'copy_{size}'] = time.time() - start

    # Verify performance improvements
    for size in data_sizes:
        assert results[f'bulk_mappings_{size}'] < results[f'individual_{size}'] * 0.3
        assert results[f'copy_{size}'] < results[f'bulk_mappings_{size}'] * 0.5
```

## Code Quality Improvements

### Monitoring Bulk Operations

```python
from prometheus_client import Histogram, Counter

bulk_operation_duration = Histogram(
    'bulk_operation_duration_seconds',
    'Time spent in bulk operations',
    ['operation', 'model', 'method']
)

bulk_operation_records = Histogram(
    'bulk_operation_records',
    'Number of records in bulk operation',
    ['operation', 'model'],
    buckets=[10, 50, 100, 500, 1000, 5000, 10000]
)

# Decorate bulk operations
def monitor_bulk_operation(operation: str, model: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)

            duration = time.time() - start
            records = kwargs.get('records', [])

            bulk_operation_duration.labels(
                operation=operation,
                model=model,
                method=func.__name__
            ).observe(duration)

            bulk_operation_records.labels(
                operation=operation,
                model=model
            ).observe(len(records))

            return result
        return wrapper
    return decorator
```

## Migration Strategy

### Phase 1: Add Infrastructure
1. Create BulkOperations class
2. Add bulk helpers
3. Create tests

### Phase 2: Update Services
1. Update MCQGenerationService
2. Update bulk endpoints
3. Add monitoring

### Phase 3: Optimize
1. Add database indexes
2. Tune batch sizes
3. Consider COPY for large operations

### Rollback Plan

```python
# Feature flag for bulk operations
if settings.USE_BULK_OPERATIONS:
    BulkOperations.bulk_insert(session, Question, records)
else:
    # Fall back to individual inserts
    for record in records:
        session.add(Question(**record))
```

## Success Criteria

### Performance Metrics

- **Insert Speed**: 10x improvement for 100+ records
- **Update Speed**: 20x improvement for bulk updates
- **Memory Usage**: Linear scaling with batch size
- **Database Load**: 90% reduction in query count

### Operational Metrics

- **Batch Success Rate**: >99.9%
- **Timeout Rate**: <0.1% with proper batching
- **Error Rate**: No increase from individual operations

### Query Analysis

```sql
-- Monitor bulk operation performance
SELECT
    query,
    calls,
    mean_exec_time,
    total_exec_time,
    rows
FROM pg_stat_statements
WHERE query LIKE '%INSERT INTO question%'
   OR query LIKE '%UPDATE question%'
ORDER BY total_exec_time DESC;

-- Check for lock contention during bulk ops
SELECT
    locktype,
    relation::regclass,
    mode,
    granted,
    COUNT(*)
FROM pg_locks
WHERE relation::regclass::text LIKE '%question%'
GROUP BY locktype, relation, mode, granted;
```

---
