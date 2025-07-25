# 7. N+1 Query Patterns

## Priority: Critical

**Estimated Effort**: 2 days
**Python Version**: 3.10+
**Dependencies**: SQLModel, SQLAlchemy 2.0+

## Problem Statement

### Current Situation

The application has inefficient N+1 query patterns in question retrieval, particularly when accessing related entities like `quiz.questions` after fetching quizzes. This results in multiple database round trips that significantly degrade performance.

### Why It's a Problem

- **Performance Degradation**: Each quiz triggers separate queries for its questions
- **Database Load**: Exponential increase in queries with data growth
- **Response Time**: API endpoints become slower with more data
- **Resource Waste**: Unnecessary database connections and network overhead
- **Scalability Issues**: Performance degrades linearly with record count

### Affected Modules

- `app/crud.py` - `get_user_quizzes()` function
- `app/crud.py` - `get_question_counts_by_quiz_id()` function
- `app/api/routes/quiz.py` - Endpoints accessing quiz.questions
- Any code iterating over quizzes and accessing related data

### Technical Debt Assessment

- **Risk Level**: Critical - Major performance impact
- **Impact**: All list operations with relationships
- **Cost of Delay**: Increases exponentially with data volume

## Current Implementation Analysis

```python
# File: app/crud.py (current N+1 problem)
def get_user_quizzes(session: Session, user_id: UUID) -> list[Quiz]:
    """Get all quizzes for a user."""
    statement = select(Quiz).where(Quiz.owner_id == user_id).order_by(desc(Quiz.created_at))
    return list(session.exec(statement).all())

# File: app/api/routes/quiz.py (triggers N+1)
@router.get("/", response_model=list[QuizWithCounts])
def get_user_quizzes_endpoint(current_user: CurrentUser, session: SessionDep):
    quizzes = get_user_quizzes(session, current_user.id)

    # PROBLEM: Each iteration triggers a new query
    quiz_responses = []
    for quiz in quizzes:  # If we have 100 quizzes
        question_count = len(quiz.questions)  # 100 additional queries!
        quiz_responses.append(
            QuizWithCounts(
                **quiz.model_dump(),
                question_count=question_count
            )
        )
    return quiz_responses

# Another N+1 example
def get_question_counts_by_quiz_id(session: Session, quiz_id: UUID) -> dict[str, int]:
    """PROBLEM: Fetches ALL questions just to count them."""
    statement = select(Question).where(Question.quiz_id == quiz_id)
    questions = list(session.exec(statement).all())  # Loads entire objects!

    total_count = len(questions)
    approved_count = sum(1 for q in questions if q.is_approved)

    return {"total": total_count, "approved": approved_count}
```

### Performance Metrics

```python
# Under current implementation:
# - 1 query to fetch 50 quizzes
# - 50 queries to fetch questions for each quiz
# - Total: 51 queries
# - Response time: ~2.5 seconds

# With 1000 quizzes:
# - 1001 queries total
# - Response time: ~45 seconds
```

### Python Anti-patterns Identified

- **Lazy Loading Abuse**: Relying on ORM lazy loading in loops
- **Missing Eager Loading**: Not using SQLAlchemy's relationship loading
- **Object Loading for Counting**: Loading full objects just to count
- **No Query Optimization**: Missing database-level aggregation

## Proposed Solution

### Pythonic Approach

Use SQLAlchemy's eager loading strategies and database-level aggregation to fetch related data efficiently in single queries.

### Implementation Plan

1. Implement eager loading for relationships
2. Use database aggregation for counts
3. Create specialized query methods
4. Add query performance monitoring
5. Update all affected endpoints

### Code Examples

```python
# File: app/crud.py (UPDATED with eager loading)
from sqlmodel import select, func, col
from sqlalchemy.orm import selectinload, joinedload

def get_user_quizzes_with_questions(session: Session, user_id: UUID) -> list[Quiz]:
    """
    Get all quizzes for a user with questions eagerly loaded.

    Uses selectinload for one-to-many relationship to avoid query multiplication.
    """
    statement = (
        select(Quiz)
        .where(Quiz.owner_id == user_id)
        .options(selectinload(Quiz.questions))  # Eager load in 1 additional query
        .order_by(desc(Quiz.created_at))
    )
    return list(session.exec(statement).all())

def get_user_quizzes_with_counts(session: Session, user_id: UUID) -> list[dict]:
    """
    Get quizzes with question counts using database aggregation.

    Returns quiz data with counts in a single query.
    """
    # Subquery for counts
    counts_subquery = (
        select(
            Question.quiz_id,
            func.count(Question.id).label("total_questions"),
            func.sum(func.cast(Question.is_approved, Integer)).label("approved_questions")
        )
        .group_by(Question.quiz_id)
        .subquery()
    )

    # Main query with LEFT JOIN
    statement = (
        select(
            Quiz,
            func.coalesce(counts_subquery.c.total_questions, 0).label("total_questions"),
            func.coalesce(counts_subquery.c.approved_questions, 0).label("approved_questions")
        )
        .outerjoin(counts_subquery, Quiz.id == counts_subquery.c.quiz_id)
        .where(Quiz.owner_id == user_id)
        .order_by(desc(Quiz.created_at))
    )

    results = []
    for quiz, total, approved in session.exec(statement):
        quiz_dict = quiz.model_dump()
        quiz_dict["total_questions"] = total
        quiz_dict["approved_questions"] = approved
        results.append(quiz_dict)

    return results

def get_question_counts_by_quiz_id(session: Session, quiz_id: UUID) -> dict[str, int]:
    """
    Get question counts using database aggregation.

    Optimized to use COUNT and SUM instead of loading objects.
    """
    statement = select(
        func.count(Question.id).label("total"),
        func.sum(func.cast(Question.is_approved, Integer)).label("approved")
    ).where(Question.quiz_id == quiz_id)

    result = session.exec(statement).first()

    return {
        "total": result.total or 0,
        "approved": result.approved or 0
    }

# File: app/models.py (Add relationship configuration)
class Quiz(SQLModel, table=True):
    # ... existing fields ...

    # Configure relationship loading
    questions: list["Question"] = Relationship(
        back_populates="quiz",
        cascade_delete=True,
        sa_relationship_kwargs={
            "lazy": "select",  # Default to lazy loading
            "cascade": "all, delete-orphan"
        }
    )

# File: app/api/routes/quiz.py (UPDATED endpoints)
@router.get("/", response_model=list[QuizWithCounts])
def get_user_quizzes_endpoint(current_user: CurrentUser, session: SessionDep):
    """Get user's quizzes with counts - optimized version."""

    # Single query with aggregation
    quiz_data = get_user_quizzes_with_counts(session, current_user.id)

    return [
        QuizWithCounts(**data) for data in quiz_data
    ]

@router.get("/{quiz_id}/questions", response_model=list[Question])
def get_quiz_questions(
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    approved_only: bool = Query(False),
):
    """Get questions for a quiz with pagination."""

    # Verify ownership
    quiz = session.get(Quiz, quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Build query with filters
    statement = select(Question).where(Question.quiz_id == quiz_id)

    if approved_only:
        statement = statement.where(Question.is_approved == True)

    # Add pagination
    statement = statement.offset(skip).limit(limit)

    return list(session.exec(statement).all())

# File: app/crud.py (Additional optimization methods)
def get_quiz_with_full_data(session: Session, quiz_id: UUID) -> Quiz | None:
    """
    Get a quiz with all related data in minimal queries.

    Uses joinedload for single quiz to minimize queries.
    """
    statement = (
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(
            joinedload(Quiz.owner),  # Join load the owner
            selectinload(Quiz.questions)  # Select load questions
        )
    )
    return session.exec(statement).first()

def get_quizzes_summary(session: Session, user_id: UUID) -> list[dict]:
    """
    Get quiz summary with aggregated stats.

    Single query for dashboard/overview data.
    """
    statement = (
        select(
            Quiz.id,
            Quiz.title,
            Quiz.created_at,
            Quiz.content_extraction_status,
            Quiz.question_generation_status,
            func.count(Question.id).label("question_count"),
            func.sum(func.cast(Question.is_approved, Integer)).label("approved_count"),
            func.max(Question.created_at).label("last_question_at")
        )
        .outerjoin(Question, Quiz.id == Question.quiz_id)
        .where(Quiz.owner_id == user_id)
        .group_by(Quiz.id, Quiz.title, Quiz.created_at,
                 Quiz.content_extraction_status, Quiz.question_generation_status)
        .order_by(desc(Quiz.created_at))
    )

    results = []
    for row in session.exec(statement):
        results.append({
            "id": row.id,
            "title": row.title,
            "created_at": row.created_at,
            "content_extraction_status": row.content_extraction_status,
            "question_generation_status": row.question_generation_status,
            "question_count": row.question_count or 0,
            "approved_count": row.approved_count or 0,
            "last_question_at": row.last_question_at
        })

    return results

# File: app/core/query_utils.py (NEW - Query optimization utilities)
from typing import TypeVar, Type
from sqlmodel import SQLModel

T = TypeVar("T", bound=SQLModel)

class QueryOptimizer:
    """Utilities for query optimization and monitoring."""

    @staticmethod
    def log_query_plan(session: Session, statement):
        """Log query execution plan for analysis."""
        if settings.ENVIRONMENT == "local":
            # Get EXPLAIN ANALYZE output
            explain = session.exec(f"EXPLAIN ANALYZE {statement}")
            logger.debug(
                "query_execution_plan",
                query=str(statement),
                plan=explain.all()
            )

    @staticmethod
    def batch_load_relationships(
        session: Session,
        objects: list[T],
        relationship_name: str
    ) -> None:
        """
        Batch load relationships for a list of objects.

        Useful when objects are already loaded but relationships aren't.
        """
        if not objects:
            return

        # Use identity map to avoid re-querying
        model_class = type(objects[0])
        relationship = getattr(model_class, relationship_name)

        # Force load for all objects in single query
        ids = [obj.id for obj in objects]
        statement = (
            select(model_class)
            .where(model_class.id.in_(ids))
            .options(selectinload(relationship))
        )

        # This refreshes the objects in session with relationships loaded
        list(session.exec(statement).all())
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── crud.py                      # UPDATE: Add eager loading methods
│   ├── models.py                    # UPDATE: Configure relationships
│   ├── api/
│   │   └── routes/
│   │       └── quiz.py              # UPDATE: Use optimized queries
│   ├── core/
│   │   └── query_utils.py           # NEW: Query optimization utilities
│   └── tests/
│       └── performance/
│           └── test_n1_queries.py   # NEW: Performance tests
```

### Dependencies

```toml
# Already included, but ensure versions support features
[project.dependencies]
sqlalchemy = ">=2.0.0"  # For modern loading strategies
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/crud/test_query_optimization.py
import pytest
from sqlalchemy import event
from app.crud import (
    get_user_quizzes_with_questions,
    get_question_counts_by_quiz_id,
    get_quizzes_summary
)

class QueryCounter:
    """Helper to count SQL queries in tests."""

    def __init__(self):
        self.count = 0
        self.queries = []

    def __enter__(self):
        self.count = 0
        self.queries = []
        event.listen(Engine, "before_execute", self.callback)
        return self

    def __exit__(self, *args):
        event.remove(Engine, "before_execute", self.callback)

    def callback(self, conn, clauseelement, multiparams, params):
        self.count += 1
        self.queries.append(str(clauseelement))

def test_get_user_quizzes_with_questions_no_n1(session, test_user, test_quizzes):
    """Test that eager loading prevents N+1 queries."""

    with QueryCounter() as counter:
        quizzes = get_user_quizzes_with_questions(session, test_user.id)

        # Access questions on all quizzes
        for quiz in quizzes:
            _ = len(quiz.questions)  # Should not trigger queries

    # Should be 2 queries: 1 for quizzes, 1 for all questions
    assert counter.count == 2

def test_get_question_counts_aggregation(session, test_quiz_with_questions):
    """Test count aggregation uses single query."""

    with QueryCounter() as counter:
        counts = get_question_counts_by_quiz_id(session, test_quiz_with_questions.id)

    # Should be single aggregation query
    assert counter.count == 1
    assert counts["total"] == 10
    assert counts["approved"] == 5

def test_quizzes_summary_single_query(session, test_user, test_quizzes):
    """Test summary uses single aggregated query."""

    with QueryCounter() as counter:
        summary = get_quizzes_summary(session, test_user.id)

    # Should be single query with all data
    assert counter.count == 1
    assert len(summary) == len(test_quizzes)
    assert all("question_count" in item for item in summary)
```

### Performance Tests

```python
# File: app/tests/performance/test_n1_queries.py
import pytest
import time
from app.tests.factories import QuizFactory, QuestionFactory

@pytest.mark.performance
def test_quiz_list_performance_at_scale(session, test_user):
    """Test query performance with realistic data volume."""

    # Create test data
    quizzes = []
    for i in range(100):
        quiz = QuizFactory(owner_id=test_user.id)
        session.add(quiz)
        session.flush()

        # Add 50 questions per quiz
        for j in range(50):
            question = QuestionFactory(quiz_id=quiz.id)
            session.add(question)

        quizzes.append(quiz)

    session.commit()

    # Test old approach (simulated)
    start = time.time()
    all_quizzes = get_user_quizzes(session, test_user.id)
    for quiz in all_quizzes:
        _ = len(quiz.questions)  # Triggers N+1
    old_duration = time.time() - start

    # Clear session to ensure fresh queries
    session.expire_all()

    # Test new approach
    start = time.time()
    quizzes_with_counts = get_user_quizzes_with_counts(session, test_user.id)
    new_duration = time.time() - start

    # New approach should be significantly faster
    assert new_duration < old_duration * 0.1  # At least 10x faster

    # Verify data correctness
    assert len(quizzes_with_counts) == 100
    assert all(item["total_questions"] == 50 for item in quizzes_with_counts)
```

## Code Quality Improvements

### Query Performance Monitoring

```python
# Add to app/core/monitoring.py
from prometheus_client import Histogram, Counter

query_duration = Histogram(
    'sql_query_duration_seconds',
    'SQL query execution time',
    ['operation', 'table']
)

query_count = Counter(
    'sql_query_total',
    'Total SQL queries executed',
    ['operation', 'table']
)

# Add query monitoring middleware
@event.listens_for(Engine, "before_execute")
def before_execute(conn, clauseelement, multiparams, params):
    conn.info['query_start'] = time.time()

@event.listens_for(Engine, "after_execute")
def after_execute(conn, clauseelement, multiparams, params, result):
    duration = time.time() - conn.info.get('query_start', time.time())

    # Extract operation and table for metrics
    operation = "select"  # Parse from clauseelement
    table = "unknown"  # Parse from clauseelement

    query_duration.labels(operation=operation, table=table).observe(duration)
    query_count.labels(operation=operation, table=table).inc()
```

## Migration Strategy

### Phase 1: Add New Methods
1. Implement new optimized query methods
2. Add performance tests
3. Verify correctness with existing data

### Phase 2: Update Endpoints
1. Update endpoints to use new methods
2. Add feature flags for gradual rollout
3. Monitor query performance metrics

### Phase 3: Remove Old Methods
1. Deprecate old inefficient methods
2. Update all references
3. Remove legacy code

### Rollback Plan

```python
# Feature flag for gradual migration
if settings.USE_OPTIMIZED_QUERIES:
    quizzes = get_user_quizzes_with_counts(session, user_id)
else:
    quizzes = get_user_quizzes(session, user_id)  # Old method
```

## Success Criteria

### Performance Metrics

- **Query Reduction**: 90%+ reduction in number of queries
- **Response Time**: <100ms for 100 quizzes (from >2s)
- **Database Load**: 80%+ reduction in database CPU usage
- **Memory Usage**: Stable memory usage (no object bloat)

### Query Metrics

```sql
-- Monitor slow queries
SELECT
    query,
    calls,
    mean_exec_time,
    total_exec_time
FROM pg_stat_statements
WHERE query LIKE '%quiz%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Check for N+1 patterns
SELECT
    query,
    calls
FROM pg_stat_statements
WHERE calls > 100
    AND query LIKE '%question%quiz_id%'
ORDER BY calls DESC;
```

---
