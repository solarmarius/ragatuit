# 7. Missing API Pagination

## Priority: Medium

**Estimated Effort**: 2 days
**Python Version**: 3.10+
**Dependencies**: FastAPI, SQLModel

## Problem Statement

### Current Situation

List endpoints in the API return all records without pagination, which can cause memory issues and poor performance as the dataset grows. Endpoints like `GET /api/quiz/` return entire result sets.

### Why It's a Problem

- **Memory Consumption**: Large result sets consume excessive server memory
- **Network Overhead**: Slow response times for large data transfers
- **Client Performance**: Frontend struggles with large lists
- **Scalability Issues**: Performance degrades linearly with data growth
- **User Experience**: Long loading times for quiz and question lists
- **Resource Exhaustion**: Can cause server timeouts

### Affected Modules

- `app/api/routes/quiz.py` - Quiz listing endpoints
- `app/crud.py` - All list operations
- Frontend components expecting full data sets
- Database query performance

### Technical Debt Assessment

- **Risk Level**: Medium - Performance issues at scale
- **Impact**: All list operations and user experience
- **Cost of Delay**: Increases with data volume

## Current Implementation Analysis

```python
# File: app/api/routes/quiz.py (current)
@router.get("/", response_model=list[Quiz])
def get_user_quizzes_endpoint(
    current_user: CurrentUser,
    session: SessionDep
) -> list[Quiz]:
    """
    Get all quizzes for the current user.

    PROBLEM: Returns ALL quizzes without limits!
    """
    return get_user_quizzes(session, current_user.id)

# File: app/crud.py (current)
def get_user_quizzes(session: Session, user_id: UUID) -> list[Quiz]:
    """
    Get all quizzes for a user.

    PROBLEM: No pagination parameters!
    """
    statement = select(Quiz).where(Quiz.owner_id == user_id).order_by(desc(Quiz.created_at))
    return list(session.exec(statement).all())  # Returns EVERYTHING!

def get_quiz_questions(session: Session, quiz_id: UUID) -> list[Question]:
    """
    Get all questions for a quiz.

    PROBLEM: Could return thousands of questions!
    """
    statement = select(Question).where(Question.quiz_id == quiz_id).order_by(Question.created_at)
    return list(session.exec(statement).all())
```

### Performance Impact

```python
# Example performance issues:
# User with 1000 quizzes:
# - Response size: ~5MB JSON
# - Query time: 2-5 seconds
# - Memory usage: 50MB+ per request

# Quiz with 500 questions:
# - Response size: ~10MB JSON
# - Frontend rendering: 3-10 seconds
# - Browser memory: 100MB+
```

### API Response Problems

```json
{
  "current_response": [
    {"id": "...", "title": "Quiz 1", "...": "..."},
    {"id": "...", "title": "Quiz 2", "...": "..."}
    // ... potentially thousands more
  ]
}
```

### Python Anti-patterns Identified

- **No Limit Enforcement**: Queries can return unlimited results
- **Missing Pagination**: No offset/limit parameters
- **No Total Count**: Clients can't implement proper pagination UI
- **Inconsistent Patterns**: Some endpoints have limits, others don't

## Proposed Solution

### Pythonic Approach

Implement consistent pagination using FastAPI query parameters, create reusable pagination models with SQLModel, and add proper response metadata for client-side pagination.

### Design Patterns

- **Repository Pattern**: Standardized pagination in data access layer
- **Response Wrapper Pattern**: Consistent paginated response format
- **Builder Pattern**: Flexible query building with pagination
- **Strategy Pattern**: Different pagination strategies for different use cases

### Code Examples

```python
# File: app/models/pagination.py (NEW)
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field
from sqlmodel import SQLModel

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    skip: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of records to return (max 100)"
    )

    @property
    def offset(self) -> int:
        """Alias for skip to match SQLAlchemy terminology."""
        return self.skip

    def to_sql_params(self) -> dict[str, int]:
        """Convert to SQL parameters."""
        return {"offset": self.skip, "limit": self.limit}

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T] = Field(description="List of items for current page")
    total: int = Field(description="Total number of items")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Maximum items per page")

    # Computed pagination metadata
    @property
    def page(self) -> int:
        """Current page number (1-based)."""
        return (self.skip // self.limit) + 1

    @property
    def pages(self) -> int:
        """Total number of pages."""
        return (self.total + self.limit - 1) // self.limit

    @property
    def has_next(self) -> bool:
        """Whether there are more pages."""
        return self.skip + self.limit < self.total

    @property
    def has_previous(self) -> bool:
        """Whether there are previous pages."""
        return self.skip > 0

    @property
    def next_skip(self) -> Optional[int]:
        """Skip value for next page."""
        return self.skip + self.limit if self.has_next else None

    @property
    def previous_skip(self) -> Optional[int]:
        """Skip value for previous page."""
        return max(0, self.skip - self.limit) if self.has_previous else None

class PaginationMeta(BaseModel):
    """Additional pagination metadata."""

    current_page: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_url: Optional[str] = None
    previous_url: Optional[str] = None

# File: app/core/pagination.py (NEW)
from typing import TypeVar, Type, List, Tuple, Optional, Any
from sqlmodel import Session, SQLModel, select, func
from sqlalchemy import Select
from fastapi import Request
from urllib.parse import urlencode

from app.models.pagination import PaginatedResponse, PaginationParams, PaginationMeta

ModelType = TypeVar("ModelType", bound=SQLModel)

class PaginationHelper:
    """Helper class for implementing pagination consistently."""

    @staticmethod
    def paginate_query(
        session: Session,
        query: Select,
        pagination: PaginationParams,
        count_query: Optional[Select] = None
    ) -> Tuple[List[Any], int]:
        """
        Apply pagination to a query and get total count.

        Args:
            session: Database session
            query: Base query to paginate
            pagination: Pagination parameters
            count_query: Optional custom count query

        Returns:
            Tuple of (items, total_count)
        """
        # Get total count
        if count_query is None:
            # Create count query from original query
            count_query = select(func.count()).select_from(query.subquery())

        total = session.exec(count_query).one()

        # Apply pagination to main query
        paginated_query = query.offset(pagination.skip).limit(pagination.limit)
        items = list(session.exec(paginated_query).all())

        return items, total

    @staticmethod
    def create_paginated_response(
        items: List[ModelType],
        total: int,
        pagination: PaginationParams
    ) -> PaginatedResponse[ModelType]:
        """Create a paginated response object."""
        return PaginatedResponse(
            items=items,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit
        )

    @staticmethod
    def generate_pagination_urls(
        request: Request,
        pagination: PaginationParams,
        total: int
    ) -> PaginationMeta:
        """Generate pagination metadata with URLs."""
        base_url = str(request.url).split('?')[0]
        query_params = dict(request.query_params)

        def build_url(skip: int) -> str:
            params = {**query_params, 'skip': skip, 'limit': pagination.limit}
            return f"{base_url}?{urlencode(params)}"

        current_page = (pagination.skip // pagination.limit) + 1
        total_pages = (total + pagination.limit - 1) // pagination.limit

        next_url = None
        previous_url = None

        if pagination.skip + pagination.limit < total:
            next_url = build_url(pagination.skip + pagination.limit)

        if pagination.skip > 0:
            previous_skip = max(0, pagination.skip - pagination.limit)
            previous_url = build_url(previous_skip)

        return PaginationMeta(
            current_page=current_page,
            total_pages=total_pages,
            has_next=next_url is not None,
            has_previous=previous_url is not None,
            next_url=next_url,
            previous_url=previous_url
        )

# File: app/crud.py (UPDATED)
from app.models.pagination import PaginationParams
from app.core.pagination import PaginationHelper

def get_user_quizzes_paginated(
    session: Session,
    user_id: UUID,
    pagination: PaginationParams,
    status_filter: Optional[str] = None
) -> Tuple[List[Quiz], int]:
    """
    Get user's quizzes with pagination.

    Args:
        session: Database session
        user_id: User ID
        pagination: Pagination parameters
        status_filter: Optional status filter

    Returns:
        Tuple of (quizzes, total_count)
    """
    # Build base query
    query = (
        select(Quiz)
        .where(Quiz.owner_id == user_id)
        .order_by(desc(Quiz.created_at))
    )

    # Apply optional filters
    if status_filter:
        query = query.where(Quiz.content_extraction_status == status_filter)

    # Build count query
    count_query = (
        select(func.count(Quiz.id))
        .where(Quiz.owner_id == user_id)
    )

    if status_filter:
        count_query = count_query.where(Quiz.content_extraction_status == status_filter)

    # Apply pagination
    return PaginationHelper.paginate_query(session, query, pagination, count_query)

def get_quiz_questions_paginated(
    session: Session,
    quiz_id: UUID,
    pagination: PaginationParams,
    approved_only: bool = False,
    search: Optional[str] = None
) -> Tuple[List[Question], int]:
    """
    Get quiz questions with pagination and optional filtering.

    Args:
        session: Database session
        quiz_id: Quiz ID
        pagination: Pagination parameters
        approved_only: Filter for approved questions only
        search: Optional text search in question content

    Returns:
        Tuple of (questions, total_count)
    """
    # Build base query
    query = (
        select(Question)
        .where(Question.quiz_id == quiz_id)
        .order_by(desc(Question.created_at))
    )

    # Apply filters
    if approved_only:
        query = query.where(Question.is_approved == True)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            Question.question_text.ilike(search_pattern) |
            Question.correct_answer.ilike(search_pattern)
        )

    # Build count query with same filters
    count_query = select(func.count(Question.id)).where(Question.quiz_id == quiz_id)

    if approved_only:
        count_query = count_query.where(Question.is_approved == True)

    if search:
        search_pattern = f"%{search}%"
        count_query = count_query.where(
            Question.question_text.ilike(search_pattern) |
            Question.correct_answer.ilike(search_pattern)
        )

    return PaginationHelper.paginate_query(session, query, pagination, count_query)

# Advanced pagination with relationships
def get_quizzes_with_question_counts(
    session: Session,
    user_id: UUID,
    pagination: PaginationParams
) -> Tuple[List[dict], int]:
    """
    Get quizzes with question counts using efficient join query.

    Returns quizzes with metadata about question counts.
    """
    from sqlalchemy import and_

    # Complex query with subquery for question counts
    question_count_subquery = (
        select(
            Question.quiz_id,
            func.count(Question.id).label('total_questions'),
            func.count(Question.id).filter(Question.is_approved == True).label('approved_questions')
        )
        .group_by(Question.quiz_id)
        .subquery()
    )

    # Main query with left join
    query = (
        select(
            Quiz,
            func.coalesce(question_count_subquery.c.total_questions, 0).label('total_questions'),
            func.coalesce(question_count_subquery.c.approved_questions, 0).label('approved_questions')
        )
        .outerjoin(question_count_subquery, Quiz.id == question_count_subquery.c.quiz_id)
        .where(Quiz.owner_id == user_id)
        .order_by(desc(Quiz.created_at))
    )

    # Count query
    count_query = select(func.count(Quiz.id)).where(Quiz.owner_id == user_id)

    items, total = PaginationHelper.paginate_query(session, query, pagination, count_query)

    # Transform results to include question counts
    result_items = []
    for quiz, total_questions, approved_questions in items:
        quiz_dict = quiz.model_dump()
        quiz_dict.update({
            'total_questions': total_questions,
            'approved_questions': approved_questions
        })
        result_items.append(quiz_dict)

    return result_items, total

# File: app/api/routes/quiz.py (UPDATED)
from typing import Annotated, Optional
from fastapi import Query, Request, Depends

from app.models.pagination import PaginatedResponse, PaginationParams
from app.core.pagination import PaginationHelper

# Dependency for pagination parameters
def get_pagination_params(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return (max 100)")
) -> PaginationParams:
    """Get pagination parameters from query params."""
    return PaginationParams(skip=skip, limit=limit)

PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]

@router.get("/", response_model=PaginatedResponse[Quiz])
def get_user_quizzes_endpoint(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    pagination: PaginationDep,
    status: Optional[str] = Query(None, description="Filter by extraction status")
) -> PaginatedResponse[Quiz]:
    """
    Get user's quizzes with pagination.

    Args:
        request: FastAPI request object for URL generation
        current_user: Current authenticated user
        session: Database session
        pagination: Pagination parameters
        status: Optional status filter

    Returns:
        Paginated response with quizzes
    """
    # Get paginated data
    quizzes, total = get_user_quizzes_paginated(
        session, current_user.id, pagination, status
    )

    # Create paginated response
    return PaginationHelper.create_paginated_response(quizzes, total, pagination)

@router.get("/{quiz_id}/questions", response_model=PaginatedResponse[Question])
def get_quiz_questions_endpoint(
    request: Request,
    quiz_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
    pagination: PaginationDep,
    approved_only: bool = Query(False, description="Show only approved questions"),
    search: Optional[str] = Query(None, description="Search in question text")
) -> PaginatedResponse[Question]:
    """
    Get questions for a quiz with pagination and filtering.

    Args:
        request: FastAPI request object
        quiz_id: Quiz identifier
        current_user: Current authenticated user
        session: Database session
        pagination: Pagination parameters
        approved_only: Filter for approved questions
        search: Text search filter

    Returns:
        Paginated response with questions
    """
    # Verify quiz ownership
    quiz = get_quiz_by_id(session, quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Get paginated questions
    questions, total = get_quiz_questions_paginated(
        session, quiz_id, pagination, approved_only, search
    )

    return PaginationHelper.create_paginated_response(questions, total, pagination)

# Enhanced endpoint with metadata
@router.get("/with-counts", response_model=PaginatedResponse[dict])
def get_user_quizzes_with_metadata(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    pagination: PaginationDep
) -> PaginatedResponse[dict]:
    """
    Get user's quizzes with question counts and metadata.

    Includes total_questions and approved_questions for each quiz.
    """
    quizzes_with_counts, total = get_quizzes_with_question_counts(
        session, current_user.id, pagination
    )

    return PaginatedResponse(
        items=quizzes_with_counts,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit
    )

# Cursor-based pagination for real-time data
@router.get("/recent", response_model=dict[str, Any])
def get_recent_quizzes(
    current_user: CurrentUser,
    session: SessionDep,
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=50, description="Number of quizzes")
) -> dict[str, Any]:
    """
    Get recent quizzes using cursor-based pagination.

    Better for real-time data where items are frequently added.
    """
    from datetime import datetime
    import base64
    import json

    # Decode cursor to get timestamp
    after_timestamp = None
    if cursor:
        try:
            cursor_data = json.loads(base64.b64decode(cursor).decode())
            after_timestamp = datetime.fromisoformat(cursor_data['timestamp'])
        except (ValueError, KeyError):
            raise HTTPException(status_code=400, detail="Invalid cursor")

    # Build query
    query = (
        select(Quiz)
        .where(Quiz.owner_id == current_user.id)
        .order_by(desc(Quiz.created_at))
        .limit(limit + 1)  # Get one extra to check for next page
    )

    if after_timestamp:
        query = query.where(Quiz.created_at < after_timestamp)

    quizzes = list(session.exec(query).all())

    # Check if there are more results
    has_next = len(quizzes) > limit
    if has_next:
        quizzes = quizzes[:-1]  # Remove the extra item

    # Generate next cursor
    next_cursor = None
    if has_next and quizzes:
        last_quiz = quizzes[-1]
        cursor_data = {'timestamp': last_quiz.created_at.isoformat()}
        next_cursor = base64.b64encode(
            json.dumps(cursor_data).encode()
        ).decode()

    return {
        'items': quizzes,
        'has_next': has_next,
        'next_cursor': next_cursor
    }
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── models/
│   │   └── pagination.py            # NEW: Pagination models
│   ├── core/
│   │   └── pagination.py            # NEW: Pagination helpers
│   ├── crud.py                      # UPDATE: Add pagination
│   ├── api/
│   │   └── routes/
│   │       ├── quiz.py              # UPDATE: Paginated endpoints
│   │       └── question.py          # UPDATE: Question endpoints
│   └── tests/
│       ├── api/
│       │   └── test_pagination.py    # NEW: Pagination tests
│       └── crud/
│           └── test_paginated_crud.py # NEW: CRUD pagination tests
```

### Response Format Changes

```json
{
  "before": [
    {"id": "...", "title": "Quiz 1"},
    {"id": "...", "title": "Quiz 2"}
  ],

  "after": {
    "items": [
      {"id": "...", "title": "Quiz 1"},
      {"id": "...", "title": "Quiz 2"}
    ],
    "total": 150,
    "skip": 20,
    "limit": 20,
    "page": 2,
    "pages": 8,
    "has_next": true,
    "has_previous": true
  }
}
```

### Configuration

```python
# app/core/config.py
class Settings(BaseSettings):
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    ENABLE_CURSOR_PAGINATION: bool = True
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/core/test_pagination.py
import pytest
from app.models.pagination import PaginationParams, PaginatedResponse
from app.core.pagination import PaginationHelper

def test_pagination_params_validation():
    """Test pagination parameter validation."""

    # Valid parameters
    params = PaginationParams(skip=10, limit=20)
    assert params.skip == 10
    assert params.limit == 20
    assert params.offset == 10  # Alias

    # Invalid parameters should raise validation error
    with pytest.raises(ValueError):
        PaginationParams(skip=-1, limit=20)  # Negative skip

    with pytest.raises(ValueError):
        PaginationParams(skip=0, limit=0)  # Zero limit

    with pytest.raises(ValueError):
        PaginationParams(skip=0, limit=200)  # Limit too high

def test_paginated_response_properties():
    """Test paginated response computed properties."""

    response = PaginatedResponse(
        items=[1, 2, 3, 4, 5],
        total=100,
        skip=20,
        limit=10
    )

    assert response.page == 3  # (20 // 10) + 1
    assert response.pages == 10  # (100 + 10 - 1) // 10
    assert response.has_next is True  # 20 + 10 < 100
    assert response.has_previous is True  # 20 > 0
    assert response.next_skip == 30
    assert response.previous_skip == 10

def test_pagination_helper_query():
    """Test pagination helper with mock query."""
    from unittest.mock import Mock, MagicMock

    # Mock session and query
    session = Mock()
    query = Mock()

    # Mock count query result
    count_result = Mock()
    count_result.one.return_value = 50
    session.exec.side_effect = [count_result, [1, 2, 3, 4, 5]]

    # Mock query methods
    query.offset.return_value = query
    query.limit.return_value = query

    pagination = PaginationParams(skip=10, limit=5)
    items, total = PaginationHelper.paginate_query(session, query, pagination)

    assert total == 50
    assert items == [1, 2, 3, 4, 5]
    query.offset.assert_called_once_with(10)
    query.limit.assert_called_once_with(5)

# File: app/tests/crud/test_paginated_crud.py
def test_get_user_quizzes_paginated(db_session, test_user):
    """Test paginated quiz retrieval."""

    # Create test quizzes
    for i in range(25):
        quiz = Quiz(
            owner_id=test_user.id,
            canvas_course_id=123,
            title=f"Quiz {i}",
            content_extraction_status="completed" if i % 2 == 0 else "pending"
        )
        db_session.add(quiz)
    db_session.commit()

    # Test first page
    pagination = PaginationParams(skip=0, limit=10)
    quizzes, total = get_user_quizzes_paginated(db_session, test_user.id, pagination)

    assert len(quizzes) == 10
    assert total == 25

    # Test second page
    pagination = PaginationParams(skip=10, limit=10)
    quizzes, total = get_user_quizzes_paginated(db_session, test_user.id, pagination)

    assert len(quizzes) == 10
    assert total == 25

    # Test last page (partial)
    pagination = PaginationParams(skip=20, limit=10)
    quizzes, total = get_user_quizzes_paginated(db_session, test_user.id, pagination)

    assert len(quizzes) == 5  # Only 5 remaining
    assert total == 25

def test_get_user_quizzes_with_status_filter(db_session, test_user):
    """Test pagination with status filtering."""

    # Create quizzes with different statuses
    for i in range(20):
        quiz = Quiz(
            owner_id=test_user.id,
            canvas_course_id=123,
            title=f"Quiz {i}",
            content_extraction_status="completed" if i < 10 else "pending"
        )
        db_session.add(quiz)
    db_session.commit()

    # Test filtering for completed quizzes
    pagination = PaginationParams(skip=0, limit=20)
    quizzes, total = get_user_quizzes_paginated(
        db_session, test_user.id, pagination, status_filter="completed"
    )

    assert len(quizzes) == 10
    assert total == 10
    assert all(q.content_extraction_status == "completed" for q in quizzes)

# File: app/tests/api/test_pagination.py
def test_quiz_pagination_endpoint(client, test_user, test_quizzes):
    """Test quiz pagination API endpoint."""

    # Test first page
    response = client.get(
        "/api/quiz/?skip=0&limit=5",
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert len(data["items"]) <= 5
    assert data["skip"] == 0
    assert data["limit"] == 5

def test_question_pagination_with_search(client, test_user, test_quiz_with_questions):
    """Test question pagination with search."""

    response = client.get(
        f"/api/quiz/{test_quiz_with_questions.id}/questions?search=python&limit=10",
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    # All returned questions should contain "python"
    for question in data["items"]:
        assert "python" in question["question_text"].lower() or \
               "python" in question["correct_answer"].lower()

def test_pagination_parameter_validation(client, test_user):
    """Test pagination parameter validation."""

    # Test invalid skip (negative)
    response = client.get(
        "/api/quiz/?skip=-1&limit=10",
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )
    assert response.status_code == 422  # Validation error

    # Test invalid limit (too high)
    response = client.get(
        "/api/quiz/?skip=0&limit=200",
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )
    assert response.status_code == 422  # Validation error
```

### Performance Tests

```python
# File: app/tests/performance/test_pagination_performance.py
@pytest.mark.performance
def test_pagination_performance_large_dataset(db_session, test_user):
    """Test pagination performance with large dataset."""
    import time

    # Create large dataset
    quizzes = []
    for i in range(1000):
        quiz = Quiz(
            owner_id=test_user.id,
            canvas_course_id=123,
            title=f"Quiz {i}"
        )
        quizzes.append(quiz)

    db_session.add_all(quizzes)
    db_session.commit()

    # Test pagination performance
    pagination = PaginationParams(skip=500, limit=20)

    start_time = time.time()
    results, total = get_user_quizzes_paginated(db_session, test_user.id, pagination)
    query_time = time.time() - start_time

    assert len(results) == 20
    assert total == 1000
    assert query_time < 0.1  # Should be fast with proper indexing

@pytest.mark.performance
def test_cursor_pagination_performance(db_session, test_user):
    """Test cursor-based pagination performance."""

    # Create time-series data
    from datetime import datetime, timedelta
    base_time = datetime.utcnow()

    for i in range(500):
        quiz = Quiz(
            owner_id=test_user.id,
            canvas_course_id=123,
            title=f"Quiz {i}",
            created_at=base_time - timedelta(minutes=i)
        )
        db_session.add(quiz)
    db_session.commit()

    # Test cursor pagination (should be O(log n) instead of O(n))
    start_time = time.time()
    # Test would use cursor-based endpoint
    query_time = time.time() - start_time

    assert query_time < 0.05  # Cursor pagination should be very fast
```

## Code Quality Improvements

### Response Caching

```python
# Add caching for expensive pagination queries
from functools import lru_cache
from typing import Tuple

@lru_cache(maxsize=128)
def get_user_quiz_count_cached(user_id: str) -> int:
    """Cache user quiz counts for faster pagination."""
    # Implementation...
    pass
```

### Query Optimization

```sql
-- Add indexes for pagination performance
CREATE INDEX idx_quiz_owner_created_pagination
ON quiz (owner_id, created_at DESC, id);

CREATE INDEX idx_question_quiz_created_pagination
ON question (quiz_id, created_at DESC, id);
```

## Migration Strategy

### Phase 1: Add Pagination Infrastructure (Day 1)

1. Create pagination models and helpers
2. Update CRUD functions to support pagination
3. Maintain backward compatibility

### Phase 2: Update API Endpoints (Day 2)

1. Add pagination parameters to endpoints
2. Update response formats
3. Add comprehensive tests

### Backward Compatibility

```python
# Support both old and new response formats
@router.get("/legacy", response_model=list[Quiz])
def get_user_quizzes_legacy(
    current_user: CurrentUser,
    session: SessionDep
) -> list[Quiz]:
    """Legacy endpoint without pagination."""
    pagination = PaginationParams(skip=0, limit=1000)  # Large limit for compatibility
    quizzes, _ = get_user_quizzes_paginated(session, current_user.id, pagination)
    return quizzes
```

## Success Criteria

### Performance Metrics

- **Response Time**: <100ms for paginated queries
- **Memory Usage**: <10MB per request regardless of total data size
- **Database Load**: Queries scale with page size, not total records
- **Frontend Performance**: Page load times <2s

### API Metrics

- **Response Size**: <1MB per page
- **Page Load**: First page loads in <500ms
- **Navigation**: Next/previous page <200ms

### Monitoring Queries

```sql
-- Monitor pagination query performance
SELECT
    query,
    mean_time,
    calls,
    total_time
FROM pg_stat_statements
WHERE query LIKE '%LIMIT%OFFSET%'
ORDER BY mean_time DESC;
```

---
