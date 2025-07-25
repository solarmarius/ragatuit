# 5. Missing Database Indexes

## Priority: Critical

**Estimated Effort**: 1 day
**Python Version**: 3.10+
**Dependencies**: SQLAlchemy 2.0+, Alembic

## Problem Statement

### Current Situation

The database schema lacks critical indexes on frequently queried columns including `quiz.owner_id`, `quiz.canvas_course_id`, `question.quiz_id`, and `question.is_approved`. This causes performance degradation as the dataset grows.

### Why It's a Problem

- **Slow Query Performance**: Full table scans on unindexed columns
- **N+1 Query Issues**: Related data fetching without proper indexing
- **Scalability Problems**: Performance degrades linearly with data growth
- **High Database Load**: Inefficient queries consume excessive resources
- **User Experience**: Slow response times for quiz and question operations

### Affected Modules

- `app/models.py` - Database model definitions
- `app/crud.py` - All CRUD operations on Quiz and Question models
- `app/api/routes/quiz.py` - Quiz listing and filtering
- Database performance for all user operations

### Technical Debt Assessment

- **Risk Level**: Critical - Performance degrades with scale
- **Impact**: All database operations involving quizzes and questions
- **Cost of Delay**: Exponential performance degradation with data growth

## Current Implementation Analysis

```python
# File: app/models.py (current schema)
class Quiz(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id")  # NO INDEX!
    canvas_course_id: int  # NO INDEX!
    title: str
    description: str | None = None
    # ... other fields

class Question(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: UUID = Field(foreign_key="quiz.id")  # NO INDEX!
    is_approved: bool = Field(default=False)  # NO INDEX!
    # ... other fields
```

### Performance Impact Analysis

```sql
-- Current slow queries (without indexes):

-- Get user's quizzes (scans entire quiz table)
EXPLAIN SELECT * FROM quiz WHERE owner_id = 'user-uuid';
-- Result: Seq Scan on quiz (cost=0.00..1234.56 rows=1000 width=1024)

-- Get questions for quiz (scans entire question table)
EXPLAIN SELECT * FROM question WHERE quiz_id = 'quiz-uuid';
-- Result: Seq Scan on question (cost=0.00..2345.67 rows=5000 width=512)

-- Filter approved questions (scans and filters entire table)
EXPLAIN SELECT * FROM question WHERE quiz_id = 'quiz-uuid' AND is_approved = true;
-- Result: Seq Scan on question (cost=0.00..3456.78 rows=2500 width=512)
```

### Python Anti-patterns Identified

- **Missing Index Declarations**: No explicit index definitions in SQLModel
- **Inefficient Queries**: CRUD operations without considering indexing
- **No Query Optimization**: Missing selectinload for related data
- **Composite Query Patterns**: Multiple filters without composite indexes

## Proposed Solution

### Pythonic Approach

Add explicit database indexes using SQLAlchemy's `Index` construct with SQLModel, implement composite indexes for common query patterns, and optimize related data loading.

### Implementation Plan

1. Add individual indexes for foreign keys and filtered columns
2. Create composite indexes for common query patterns
3. Update models with explicit index definitions
4. Create Alembic migration for index creation
5. Optimize CRUD operations with proper eager loading
6. Add query performance monitoring

### Code Examples

```python
# File: app/models.py (UPDATED)
from sqlmodel import SQLModel, Field, Index, Column
from sqlalchemy import String, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from typing import Optional
from datetime import datetime
import uuid

class Quiz(SQLModel, table=True):
    """Quiz model with optimized indexing."""

    id: UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(PostgresUUID(as_uuid=True))
    )
    owner_id: UUID = Field(
        foreign_key="user.id",
        sa_column=Column(PostgresUUID(as_uuid=True), index=True)  # Index for user queries
    )
    canvas_course_id: int = Field(index=True)  # Index for course filtering
    title: str = Field(sa_column=Column(String(255), index=True))  # Index for title searches
    description: str | None = None

    # Status fields with indexes
    content_extraction_status: str = Field(
        default="pending",
        sa_column=Column(String(20), index=True)  # Index for status filtering
    )
    llm_generation_status: str = Field(
        default="not_started",
        sa_column=Column(String(20), index=True)
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, index=True)  # Index for date sorting
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, index=True)
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        # User's quizzes ordered by creation date
        Index("ix_quiz_owner_created", "owner_id", "created_at"),

        # Course quizzes with status filtering
        Index("ix_quiz_course_status", "canvas_course_id", "content_extraction_status"),

        # Active quizzes (for admin/monitoring)
        Index("ix_quiz_active", "content_extraction_status", "llm_generation_status"),

        # Full-text search preparation
        Index("ix_quiz_title_search", text("to_tsvector('english', title)"), postgresql_using="gin"),
    )

class Question(SQLModel, table=True):
    """Question model with optimized indexing."""

    id: UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column=Column(PostgresUUID(as_uuid=True))
    )
    quiz_id: UUID = Field(
        foreign_key="quiz.id",
        sa_column=Column(PostgresUUID(as_uuid=True), index=True)  # Critical for quiz queries
    )

    # Approval workflow fields
    is_approved: bool = Field(
        default=False,
        sa_column=Column(Boolean, index=True)  # Index for approval filtering
    )
    approved_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, index=True)
    )

    # Question content
    question_text: str = Field(sa_column=Column(String(1000)))
    correct_answer: str = Field(sa_column=Column(String(500)))

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, index=True)
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        # Quiz questions with approval status (most common query)
        Index("ix_question_quiz_approved", "quiz_id", "is_approved"),

        # Approved questions by creation date
        Index("ix_question_approved_created", "is_approved", "created_at"),

        # Quiz questions ordered by creation (for pagination)
        Index("ix_question_quiz_created", "quiz_id", "created_at"),

        # Admin queries - questions pending approval
        Index("ix_question_pending_approval", "is_approved", "created_at")
        .where(text("is_approved = false")),
    )

# File: app/crud.py (UPDATED for optimized queries)
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, desc, func

def get_user_quizzes_optimized(
    session: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None
) -> list[Quiz]:
    """
    Get user's quizzes with optimized query and pagination.

    Uses index: ix_quiz_owner_created or ix_quiz_course_status
    """
    query = (
        select(Quiz)
        .where(Quiz.owner_id == user_id)
        .order_by(desc(Quiz.created_at))
        .offset(skip)
        .limit(limit)
    )

    if status_filter:
        query = query.where(Quiz.content_extraction_status == status_filter)

    return list(session.exec(query).all())

def get_quiz_questions_optimized(
    session: Session,
    quiz_id: UUID,
    approved_only: bool = False,
    skip: int = 0,
    limit: int = 50
) -> list[Question]:
    """
    Get quiz questions with optimized query.

    Uses index: ix_question_quiz_approved or ix_question_quiz_created
    """
    query = (
        select(Question)
        .where(Question.quiz_id == quiz_id)
        .order_by(desc(Question.created_at))
        .offset(skip)
        .limit(limit)
    )

    if approved_only:
        query = query.where(Question.is_approved == True)

    return list(session.exec(query).all())

def get_quiz_with_questions_optimized(
    session: Session,
    quiz_id: UUID,
    approved_only: bool = False
) -> Quiz | None:
    """
    Get quiz with questions using optimized eager loading.

    Prevents N+1 queries by using selectinload.
    """
    query = select(Quiz).where(Quiz.id == quiz_id)

    if approved_only:
        # Use selectinload with filtered relationship
        query = query.options(
            selectinload(Quiz.questions).where(Question.is_approved == True)
        )
    else:
        query = query.options(selectinload(Quiz.questions))

    return session.exec(query).first()

def get_questions_by_approval_status(
    session: Session,
    is_approved: bool,
    limit: int = 100
) -> list[Question]:
    """
    Get questions by approval status for admin interface.

    Uses index: ix_question_pending_approval or ix_question_approved_created
    """
    query = (
        select(Question)
        .where(Question.is_approved == is_approved)
        .order_by(desc(Question.created_at))
        .limit(limit)
    )

    return list(session.exec(query).all())

# Bulk operations with optimized queries
def approve_questions_bulk(
    session: Session,
    question_ids: list[UUID]
) -> int:
    """
    Bulk approve questions with optimized update.

    Uses index: primary key for WHERE IN clause
    """
    stmt = (
        update(Question)
        .where(Question.id.in_(question_ids))
        .values(
            is_approved=True,
            approved_at=datetime.utcnow()
        )
    )

    result = session.execute(stmt)
    session.commit()
    return result.rowcount
```

### Database Migration

```python
# File: alembic/versions/add_performance_indexes.py
"""Add performance indexes for Quiz and Question models

Revision ID: 001_add_indexes
Revises: previous_revision
Create Date: 2024-01-01 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001_add_indexes'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade():
    """Add performance indexes."""

    # Individual column indexes
    op.create_index('ix_quiz_owner_id', 'quiz', ['owner_id'])
    op.create_index('ix_quiz_canvas_course_id', 'quiz', ['canvas_course_id'])
    op.create_index('ix_quiz_title', 'quiz', ['title'])
    op.create_index('ix_quiz_content_extraction_status', 'quiz', ['content_extraction_status'])
    op.create_index('ix_quiz_llm_generation_status', 'quiz', ['llm_generation_status'])
    op.create_index('ix_quiz_created_at', 'quiz', ['created_at'])
    op.create_index('ix_quiz_updated_at', 'quiz', ['updated_at'])

    op.create_index('ix_question_quiz_id', 'question', ['quiz_id'])
    op.create_index('ix_question_is_approved', 'question', ['is_approved'])
    op.create_index('ix_question_approved_at', 'question', ['approved_at'])
    op.create_index('ix_question_created_at', 'question', ['created_at'])

    # Composite indexes for common query patterns
    op.create_index('ix_quiz_owner_created', 'quiz', ['owner_id', 'created_at'])
    op.create_index('ix_quiz_course_status', 'quiz', ['canvas_course_id', 'content_extraction_status'])
    op.create_index('ix_quiz_active', 'quiz', ['content_extraction_status', 'llm_generation_status'])

    op.create_index('ix_question_quiz_approved', 'question', ['quiz_id', 'is_approved'])
    op.create_index('ix_question_approved_created', 'question', ['is_approved', 'created_at'])
    op.create_index('ix_question_quiz_created', 'question', ['quiz_id', 'created_at'])

    # Partial index for pending approvals
    op.execute("""
        CREATE INDEX ix_question_pending_approval
        ON question (is_approved, created_at)
        WHERE is_approved = false
    """)

    # Full-text search index for quiz titles
    op.execute("""
        CREATE INDEX ix_quiz_title_search
        ON quiz USING gin(to_tsvector('english', title))
    """)

def downgrade():
    """Remove performance indexes."""

    # Drop all indexes in reverse order
    op.drop_index('ix_quiz_title_search')
    op.drop_index('ix_question_pending_approval')

    op.drop_index('ix_question_quiz_created')
    op.drop_index('ix_question_approved_created')
    op.drop_index('ix_question_quiz_approved')

    op.drop_index('ix_quiz_active')
    op.drop_index('ix_quiz_course_status')
    op.drop_index('ix_quiz_owner_created')

    op.drop_index('ix_question_created_at')
    op.drop_index('ix_question_approved_at')
    op.drop_index('ix_question_is_approved')
    op.drop_index('ix_question_quiz_id')

    op.drop_index('ix_quiz_updated_at')
    op.drop_index('ix_quiz_created_at')
    op.drop_index('ix_quiz_llm_generation_status')
    op.drop_index('ix_quiz_content_extraction_status')
    op.drop_index('ix_quiz_title')
    op.drop_index('ix_quiz_canvas_course_id')
    op.drop_index('ix_quiz_owner_id')
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── models.py                    # UPDATE: Add index definitions
│   ├── crud.py                      # UPDATE: Optimize queries
│   └── api/
│       └── routes/
│           └── quiz.py              # UPDATE: Use optimized CRUD
├── alembic/
│   └── versions/
│       └── add_performance_indexes.py  # NEW: Index migration
└── tests/
    └── performance/
        └── test_database_indexes.py    # NEW: Performance tests
```

### Dependencies

No new dependencies required - uses existing SQLAlchemy and Alembic.

## Testing Requirements

### Performance Tests

```python
# File: app/tests/performance/test_database_indexes.py
import pytest
import time
from sqlalchemy import text
from app.core.db import engine
from app.models import Quiz, Question, User
from app.crud import (
    get_user_quizzes_optimized,
    get_quiz_questions_optimized,
    get_questions_by_approval_status
)

@pytest.mark.performance
def test_user_quizzes_query_performance(db_session, test_user):
    """Test user quiz queries use indexes efficiently."""

    # Create test data
    for i in range(100):
        quiz = Quiz(
            owner_id=test_user.id,
            canvas_course_id=123,
            title=f"Test Quiz {i}",
            content_extraction_status="completed"
        )
        db_session.add(quiz)
    db_session.commit()

    # Test query performance
    start_time = time.time()
    quizzes = get_user_quizzes_optimized(db_session, test_user.id, limit=20)
    query_time = time.time() - start_time

    assert len(quizzes) == 20
    assert query_time < 0.1  # Should be very fast with index

    # Verify index usage with EXPLAIN
    explain_result = db_session.execute(
        text("EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM quiz WHERE owner_id = :user_id ORDER BY created_at DESC LIMIT 20"),
        {"user_id": str(test_user.id)}
    ).fetchall()

    explain_text = "\n".join([row[0] for row in explain_result])
    assert "Index Scan" in explain_text
    assert "ix_quiz_owner_created" in explain_text

@pytest.mark.performance
def test_quiz_questions_query_performance(db_session, test_quiz):
    """Test quiz questions queries use indexes efficiently."""

    # Create test questions
    for i in range(200):
        question = Question(
            quiz_id=test_quiz.id,
            question_text=f"Question {i}",
            correct_answer=f"Answer {i}",
            is_approved=(i % 2 == 0)  # Half approved
        )
        db_session.add(question)
    db_session.commit()

    # Test approved questions query
    start_time = time.time()
    approved_questions = get_quiz_questions_optimized(
        db_session, test_quiz.id, approved_only=True, limit=50
    )
    query_time = time.time() - start_time

    assert len(approved_questions) == 50
    assert query_time < 0.05  # Very fast with composite index

    # Verify composite index usage
    explain_result = db_session.execute(
        text("EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM question WHERE quiz_id = :quiz_id AND is_approved = true ORDER BY created_at DESC LIMIT 50"),
        {"quiz_id": str(test_quiz.id)}
    ).fetchall()

    explain_text = "\n".join([row[0] for row in explain_result])
    assert "Index Scan" in explain_text
    assert "ix_question_quiz_approved" in explain_text

@pytest.mark.performance
def test_n_plus_one_query_prevention(db_session, test_user):
    """Test that eager loading prevents N+1 queries."""

    # Create quiz with questions
    quiz = Quiz(
        owner_id=test_user.id,
        canvas_course_id=123,
        title="Test Quiz"
    )
    db_session.add(quiz)
    db_session.flush()

    for i in range(10):
        question = Question(
            quiz_id=quiz.id,
            question_text=f"Question {i}",
            correct_answer=f"Answer {i}",
            is_approved=True
        )
        db_session.add(question)
    db_session.commit()

    # Enable query logging
    from sqlalchemy import event
    queries = []

    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    # Test optimized query
    quiz_with_questions = get_quiz_with_questions_optimized(
        db_session, quiz.id, approved_only=True
    )

    # Should only execute 2 queries: one for quiz, one for all questions
    assert len([q for q in queries if "SELECT" in q]) <= 2
    assert len(quiz_with_questions.questions) == 10
```

### Unit Tests

```python
# File: app/tests/crud/test_optimized_crud.py
def test_get_user_quizzes_with_status_filter(db_session, test_user):
    """Test status filtering uses appropriate index."""

    # Create quizzes with different statuses
    statuses = ["pending", "processing", "completed", "failed"]
    for status in statuses:
        quiz = Quiz(
            owner_id=test_user.id,
            canvas_course_id=123,
            title=f"Quiz {status}",
            content_extraction_status=status
        )
        db_session.add(quiz)
    db_session.commit()

    # Test filtering
    completed_quizzes = get_user_quizzes_optimized(
        db_session, test_user.id, status_filter="completed"
    )

    assert len(completed_quizzes) == 1
    assert completed_quizzes[0].content_extraction_status == "completed"

def test_bulk_approve_questions(db_session, test_quiz):
    """Test bulk operations are efficient."""

    # Create questions
    question_ids = []
    for i in range(50):
        question = Question(
            quiz_id=test_quiz.id,
            question_text=f"Question {i}",
            correct_answer=f"Answer {i}",
            is_approved=False
        )
        db_session.add(question)
        db_session.flush()
        question_ids.append(question.id)
    db_session.commit()

    # Bulk approve
    updated_count = approve_questions_bulk(db_session, question_ids[:25])

    assert updated_count == 25

    # Verify approval
    approved_questions = get_quiz_questions_optimized(
        db_session, test_quiz.id, approved_only=True
    )
    assert len(approved_questions) == 25
```

## Code Quality Improvements

### Query Analysis Tools

```python
# File: app/utils/query_analyzer.py
from sqlalchemy import event, text
from app.core.db import engine
from app.core.logging_config import get_logger
import time

logger = get_logger("query_analyzer")

class QueryAnalyzer:
    """Analyze query performance and index usage."""

    def __init__(self):
        self.slow_queries = []
        self.query_counts = {}

    def start_monitoring(self):
        """Start monitoring SQL queries."""

        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()

        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - context._query_start_time

            # Log slow queries
            if total > 0.1:  # Queries taking more than 100ms
                self.slow_queries.append({
                    "query": statement,
                    "duration": total,
                    "parameters": parameters
                })

                logger.warning(
                    "slow_query_detected",
                    duration=total,
                    query=statement[:200]  # Truncate for logging
                )

            # Count query types
            query_type = statement.strip().split()[0].upper()
            self.query_counts[query_type] = self.query_counts.get(query_type, 0) + 1

    def get_index_usage_stats(self, session):
        """Get index usage statistics."""
        result = session.execute(text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            ORDER BY idx_scan DESC
        """))

        return [dict(row) for row in result]
```

## Migration Strategy

### Pre-Migration Performance Baseline

```sql
-- Capture current performance metrics
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch
FROM pg_stat_user_tables
WHERE schemaname = 'public';
```

### Migration Steps

1. **Create indexes in maintenance window**
2. **Update application code** with optimized queries
3. **Monitor performance improvements**
4. **Validate index usage** with pg_stat_user_indexes

### Rollback Plan

```sql
-- Emergency rollback script
DROP INDEX CONCURRENTLY IF EXISTS ix_quiz_owner_created;
DROP INDEX CONCURRENTLY IF EXISTS ix_question_quiz_approved;
-- ... other indexes
```

## Success Criteria

### Performance Metrics

- **User quiz queries**: <50ms (currently 500ms+)
- **Question queries**: <25ms (currently 200ms+)
- **Bulk operations**: <100ms for 100 records
- **Index usage**: >90% of queries use indexes

### Monitoring Queries

```sql
-- Check slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY mean_time DESC;

-- Index usage verification
SELECT
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexname LIKE 'ix_%'
ORDER BY idx_scan DESC;
```

---
