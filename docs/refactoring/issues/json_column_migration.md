# 16. JSON Column Migration

## Priority: Medium

**Estimated Effort**: 2 days
**Python Version**: 3.10+
**Dependencies**: SQLAlchemy 2.0+, PostgreSQL, Alembic

## Problem Statement

### Current Situation

JSON data is stored as strings in database columns, requiring manual parsing and serialization. This approach is inefficient, error-prone, and prevents database-level JSON operations and indexing.

### Why It's a Problem

- **Performance Impact**: String parsing overhead on every access
- **No JSON Validation**: Invalid JSON can be stored
- **Missing Query Capabilities**: Cannot query JSON fields in database
- **Manual Parsing Errors**: JSON decode errors at runtime
- **Storage Inefficiency**: String storage less efficient than JSONB
- **No Indexing**: Cannot index JSON fields for fast lookups

### Affected Modules

- `app/models.py` - Quiz model with `selected_modules` and `extracted_content`
- `app/crud.py` - CRUD operations with manual JSON handling
- All code accessing JSON fields

### Technical Debt Assessment

- **Risk Level**: Medium - Performance and reliability impact
- **Impact**: All JSON data operations
- **Cost of Delay**: Increases with data volume

## Current Implementation Analysis

```python
# File: app/models.py (current string-based JSON storage)
class Quiz(SQLModel, table=True):
    # PROBLEM: JSON stored as string
    selected_modules: str = Field(description="JSON array of selected modules")
    extracted_content: str | None = Field(default=None, description="JSON content")

    @property
    def modules_dict(self) -> dict[int, str]:
        """PROBLEM: Manual parsing with error handling."""
        try:
            return json.loads(self.selected_modules)
        except (json.JSONDecodeError, TypeError):
            return {}

    @property
    def content_dict(self) -> dict[str, Any]:
        """PROBLEM: Another manual parsing property."""
        if not self.extracted_content:
            return {}
        try:
            return json.loads(self.extracted_content)
        except (json.JSONDecodeError, TypeError):
            return {}

# File: app/crud.py (manual JSON handling)
def create_quiz(session: Session, quiz_in: QuizCreate, owner_id: UUID) -> Quiz:
    """PROBLEM: Manual JSON serialization."""
    quiz = Quiz.model_validate(
        quiz_in,
        update={
            "owner_id": owner_id,
            # Manual JSON conversion
            "selected_modules": json.dumps(quiz_in.selected_modules),
            "updated_at": datetime.now(timezone.utc),
        },
    )
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    return quiz

# Usage problems
quiz = get_quiz_by_id(session, quiz_id)
# Every access requires parsing
modules = json.loads(quiz.selected_modules)  # Can fail!
# Cannot query: WHERE selected_modules->>'module_1' = 'Introduction'
```

### Performance Analysis

```python
# Current performance issues:
# 1. Parse JSON on every access: ~1ms per parse
# 2. With 1000 quizzes, each with 10 module accesses: 10 seconds overhead
# 3. No ability to filter/query JSON in database
# 4. Full table scans for JSON field searches

# Example inefficient query
quizzes = session.exec(select(Quiz)).all()
javascript_quizzes = [
    q for q in quizzes
    if "javascript" in json.loads(q.selected_modules).values()
]  # Loads ALL quizzes into memory!
```

### Python Anti-patterns Identified

- **String Type Abuse**: Using strings for structured data
- **Manual Serialization**: Error-prone JSON handling
- **No Type Safety**: JSON structure not validated
- **Property Overhead**: Parsing on every property access
- **Missing Database Features**: Not using native JSON support

## Proposed Solution

### Pythonic Approach

Migrate to PostgreSQL's native JSONB columns with SQLAlchemy's JSON type support, providing automatic serialization, validation, and query capabilities.

### Implementation Plan

1. Add new JSONB columns alongside existing
2. Migrate data with validation
3. Update code to use new columns
4. Remove old string columns
5. Add JSON-specific indexes

### Code Examples

```python
# File: app/models.py (UPDATED with native JSON)
from sqlalchemy import Column, JSON
from sqlalchemy.dialects.postgresql import JSONB
from typing import Dict, Any, Optional
from pydantic import validator

class Quiz(SQLModel, table=True):
    """Quiz model with native JSON support."""

    # Old columns (to be removed after migration)
    selected_modules_old: Optional[str] = Field(
        default=None,
        sa_column=Column("selected_modules", String, nullable=True)
    )
    extracted_content_old: Optional[str] = Field(
        default=None,
        sa_column=Column("extracted_content", String, nullable=True)
    )

    # New JSONB columns
    selected_modules: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(
            "selected_modules_json",
            JSONB,  # PostgreSQL JSONB for efficiency
            nullable=False,
            default={},
            server_default=text("'{}'::jsonb")
        )
    )

    extracted_content: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(
            "extracted_content_json",
            JSONB,
            nullable=True
        )
    )

    # Pydantic validators for structure
    @validator('selected_modules')
    def validate_selected_modules(cls, v):
        """Ensure selected_modules has correct structure."""
        if not isinstance(v, dict):
            raise ValueError("selected_modules must be a dictionary")
        # Validate all keys are strings (module IDs)
        for key, value in v.items():
            if not isinstance(value, str):
                raise ValueError(f"Module name must be string, got {type(value)}")
        return v

    @validator('extracted_content')
    def validate_extracted_content(cls, v):
        """Validate extracted content structure."""
        if v is not None and not isinstance(v, dict):
            raise ValueError("extracted_content must be a dictionary")
        return v

    # Remove old properties - direct access now!
    # No more @property with try/except blocks

# File: app/crud.py (UPDATED - no manual JSON handling)
def create_quiz(session: Session, quiz_in: QuizCreate, owner_id: UUID) -> Quiz:
    """Create quiz with automatic JSON handling."""
    quiz = Quiz(
        **quiz_in.model_dump(),  # Direct assignment - no JSON.dumps!
        owner_id=owner_id,
        updated_at=datetime.utcnow()
    )
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    return quiz

def get_quizzes_by_module_name(
    session: Session,
    module_name: str,
    owner_id: Optional[UUID] = None
) -> list[Quiz]:
    """Query quizzes using JSON operations."""
    # Use PostgreSQL JSON operators
    statement = select(Quiz).where(
        Quiz.selected_modules.op('@>')([module_name])  # JSON contains
    )

    if owner_id:
        statement = statement.where(Quiz.owner_id == owner_id)

    return list(session.exec(statement).all())

def get_quizzes_with_content_type(
    session: Session,
    content_type: str
) -> list[Quiz]:
    """Find quizzes with specific content type using JSON path."""
    # Query nested JSON
    statement = select(Quiz).where(
        Quiz.extracted_content['type'].astext == content_type
    )
    return list(session.exec(statement).all())

# File: app/alembic/versions/xxx_migrate_json_columns.py
"""Migrate string JSON to native JSONB columns

Revision ID: xxx
Revises: yyy
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

def upgrade():
    # Step 1: Add new JSONB columns
    op.add_column(
        'quiz',
        sa.Column(
            'selected_modules_json',
            postgresql.JSONB,
            nullable=True,  # Temporarily nullable
            server_default=sa.text("'{}'::jsonb")
        )
    )

    op.add_column(
        'quiz',
        sa.Column(
            'extracted_content_json',
            postgresql.JSONB,
            nullable=True
        )
    )

    # Step 2: Migrate data with validation
    connection = op.get_bind()

    # Migrate in batches to handle large tables
    batch_size = 1000
    offset = 0

    while True:
        result = connection.execute(
            sa.text(f"""
                SELECT id, selected_modules, extracted_content
                FROM quiz
                WHERE selected_modules_json IS NULL
                LIMIT {batch_size} OFFSET {offset}
            """)
        )

        rows = result.fetchall()
        if not rows:
            break

        for row in rows:
            quiz_id = row.id

            # Migrate selected_modules
            try:
                if row.selected_modules:
                    modules = json.loads(row.selected_modules)
                    if isinstance(modules, dict):
                        connection.execute(
                            sa.text("""
                                UPDATE quiz
                                SET selected_modules_json = :modules::jsonb
                                WHERE id = :id
                            """),
                            {"modules": json.dumps(modules), "id": quiz_id}
                        )
            except json.JSONDecodeError:
                # Log error and use empty dict
                print(f"Invalid JSON in quiz {quiz_id} selected_modules")
                connection.execute(
                    sa.text("""
                        UPDATE quiz
                        SET selected_modules_json = '{}'::jsonb
                        WHERE id = :id
                    """),
                    {"id": quiz_id}
                )

            # Migrate extracted_content
            try:
                if row.extracted_content:
                    content = json.loads(row.extracted_content)
                    if isinstance(content, dict):
                        connection.execute(
                            sa.text("""
                                UPDATE quiz
                                SET extracted_content_json = :content::jsonb
                                WHERE id = :id
                            """),
                            {"content": json.dumps(content), "id": quiz_id}
                        )
            except json.JSONDecodeError:
                print(f"Invalid JSON in quiz {quiz_id} extracted_content")

        offset += batch_size

    # Step 3: Make new columns non-nullable (for selected_modules)
    op.alter_column(
        'quiz',
        'selected_modules_json',
        nullable=False
    )

    # Step 4: Create indexes for JSON queries
    op.create_index(
        'ix_quiz_selected_modules_gin',
        'quiz',
        ['selected_modules_json'],
        postgresql_using='gin'  # GIN index for JSON
    )

    op.create_index(
        'ix_quiz_extracted_content_gin',
        'quiz',
        ['extracted_content_json'],
        postgresql_using='gin',
        postgresql_where=sa.text('extracted_content_json IS NOT NULL')
    )

    # Step 5: Create functional indexes for common queries
    op.execute("""
        CREATE INDEX ix_quiz_module_values ON quiz
        USING gin ((selected_modules_json::jsonb))
    """)

def downgrade():
    # Remove indexes
    op.drop_index('ix_quiz_module_values')
    op.drop_index('ix_quiz_extracted_content_gin')
    op.drop_index('ix_quiz_selected_modules_gin')

    # Drop new columns (data loss warning!)
    op.drop_column('quiz', 'extracted_content_json')
    op.drop_column('quiz', 'selected_modules_json')

# File: app/alembic/versions/xxx2_remove_old_json_columns.py
"""Remove old string JSON columns after migration

Revision ID: xxx2
Revises: xxx
"""

def upgrade():
    # Rename new columns to original names
    op.alter_column('quiz', 'selected_modules_json', new_column_name='selected_modules')
    op.alter_column('quiz', 'extracted_content_json', new_column_name='extracted_content')

    # Drop old columns
    op.drop_column('quiz', 'selected_modules_old')
    op.drop_column('quiz', 'extracted_content_old')

def downgrade():
    # Complex - would need to recreate string columns
    pass

# File: app/api/routes/quiz.py (JSON queries in action)
@router.get("/by-module/{module_name}")
async def get_quizzes_by_module(
    module_name: str,
    current_user: CurrentUser,
    session: SessionDep,
) -> list[Quiz]:
    """Get quizzes containing specific module - uses JSON index!"""

    # Efficient JSON query
    statement = select(Quiz).where(
        Quiz.owner_id == current_user.id,
        Quiz.selected_modules.op('?')(module_name)  # JSON key exists
    )

    return list(session.exec(statement).all())

@router.get("/search")
async def search_quiz_content(
    search_term: str,
    current_user: CurrentUser,
    session: SessionDep,
    limit: int = Query(20, le=100),
) -> list[Quiz]:
    """Search in quiz content using JSON text search."""

    # Full text search in JSON
    statement = select(Quiz).where(
        Quiz.owner_id == current_user.id,
        sa.or_(
            # Search in module names
            sa.func.jsonb_path_exists(
                Quiz.selected_modules,
                f'$.* ? (@ like_regex "{search_term}" flag "i")'
            ),
            # Search in extracted content
            Quiz.extracted_content.op('@@')(
                sa.func.plainto_tsquery('english', search_term)
            )
        )
    ).limit(limit)

    return list(session.exec(statement).all())

# File: app/models.py (JSON-specific query builders)
class Quiz(SQLModel, table=True):
    # ... existing fields ...

    @classmethod
    def with_module(cls, module_id: str):
        """Query builder for module filtering."""
        return select(cls).where(
            cls.selected_modules.op('?')(module_id)
        )

    @classmethod
    def with_content_field(cls, field: str, value: Any):
        """Query builder for content field filtering."""
        return select(cls).where(
            cls.extracted_content[field].astext == str(value)
        )

    def add_module(self, module_id: str, module_name: str) -> None:
        """Add module to selection (demonstrates JSON update)."""
        # SQLAlchemy tracks changes to mutable JSON
        self.selected_modules[module_id] = module_name

    def remove_module(self, module_id: str) -> None:
        """Remove module from selection."""
        self.selected_modules.pop(module_id, None)
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── models.py                    # UPDATE: Add JSONB columns
│   ├── crud.py                      # UPDATE: Remove JSON parsing
│   ├── api/
│   │   └── routes/
│   │       └── quiz.py              # UPDATE: Use JSON queries
│   ├── alembic/
│   │   └── versions/
│   │       ├── xxx_migrate_json.py  # NEW: Migration script
│   │       └── xxx2_cleanup.py      # NEW: Cleanup script
│   └── tests/
│       └── test_json_fields.py      # NEW: JSON-specific tests
```

### Migration Strategy

```python
# Safe migration in phases:

# Phase 1: Add new columns, dual-write
class Quiz(SQLModel, table=True):
    selected_modules_old: str = Field(sa_column_name="selected_modules")
    selected_modules: dict = Field(sa_column_name="selected_modules_json")

    def __init__(self, **data):
        super().__init__(**data)
        # Dual write during migration
        if 'selected_modules' in data:
            self.selected_modules_old = json.dumps(data['selected_modules'])

# Phase 2: Backfill data
# Run migration script

# Phase 3: Switch reads to new column
# Update all code to use new columns

# Phase 4: Stop dual-write
# Remove old column references

# Phase 5: Drop old columns
# Final cleanup migration
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/models/test_json_fields.py
import pytest
from app.models import Quiz

def test_quiz_json_field_validation():
    """Test JSON field validation."""

    # Valid data
    quiz = Quiz(
        title="Test",
        selected_modules={"1": "Module 1", "2": "Module 2"},
        canvas_course_id=123,
        owner_id=uuid.uuid4()
    )
    assert quiz.selected_modules == {"1": "Module 1", "2": "Module 2"}

    # Invalid data should raise
    with pytest.raises(ValueError):
        Quiz(
            title="Test",
            selected_modules="not a dict",  # Should be dict
            canvas_course_id=123,
            owner_id=uuid.uuid4()
        )

def test_json_field_mutations(session):
    """Test JSON field updates are tracked."""

    quiz = create_test_quiz(session)

    # Modify JSON field
    quiz.selected_modules["3"] = "Module 3"
    session.commit()

    # Verify persisted
    session.refresh(quiz)
    assert "3" in quiz.selected_modules
    assert quiz.selected_modules["3"] == "Module 3"

def test_json_queries(session):
    """Test JSON-specific queries."""

    # Create test data
    quiz1 = create_quiz(session, selected_modules={"js": "JavaScript", "py": "Python"})
    quiz2 = create_quiz(session, selected_modules={"rb": "Ruby", "go": "Go"})
    quiz3 = create_quiz(session, selected_modules={"js": "JavaScript", "ts": "TypeScript"})

    # Query by JSON key
    js_quizzes = session.exec(
        select(Quiz).where(Quiz.selected_modules.op('?')('js'))
    ).all()

    assert len(js_quizzes) == 2
    assert quiz1 in js_quizzes
    assert quiz3 in js_quizzes

    # Query by JSON value
    python_quizzes = session.exec(
        select(Quiz).where(
            Quiz.selected_modules.op('@>')('{"py": "Python"}')
        )
    ).all()

    assert len(python_quizzes) == 1
    assert quiz1 in python_quizzes

@pytest.mark.benchmark
def test_json_performance(benchmark, session):
    """Benchmark JSON operations vs string parsing."""

    # Create quiz with JSON data
    quiz = create_quiz_with_content(session, module_count=50)

    def access_json_native():
        # Direct access - no parsing
        return len(quiz.selected_modules)

    def access_json_string():
        # Old way - parse every time
        return len(json.loads(quiz.selected_modules_old))

    # Native should be much faster
    native_time = benchmark(access_json_native)
    string_time = benchmark(access_json_string)

    assert native_time < string_time * 0.1  # 10x faster
```

### Migration Tests

```python
# File: app/tests/test_json_migration.py
def test_migration_data_integrity(migrated_db):
    """Test data integrity after migration."""

    # Check all quizzes migrated correctly
    quizzes = migrated_db.exec(select(Quiz)).all()

    for quiz in quizzes:
        # New columns should have data
        assert isinstance(quiz.selected_modules, dict)

        # Data should match original
        if quiz.selected_modules_old:
            old_data = json.loads(quiz.selected_modules_old)
            assert quiz.selected_modules == old_data

def test_migration_handles_invalid_json(test_db):
    """Test migration handles corrupted JSON."""

    # Insert invalid JSON
    test_db.execute(
        "INSERT INTO quiz (id, selected_modules, ...) "
        "VALUES (:id, :modules, ...)",
        {"id": uuid.uuid4(), "modules": "invalid{json"}
    )

    # Run migration
    run_migration("xxx_migrate_json_columns")

    # Should use empty dict for invalid JSON
    quiz = test_db.exec(
        select(Quiz).where(Quiz.selected_modules_old == "invalid{json")
    ).first()

    assert quiz.selected_modules == {}
```

## Code Quality Improvements

### JSON Schema Validation

```python
# Add JSON schema validation
from jsonschema import validate, ValidationError

SELECTED_MODULES_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "^[0-9]+$": {"type": "string"}
    },
    "additionalProperties": False
}

EXTRACTED_CONTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "modules": {
            "type": "object",
            "patternProperties": {
                "^[0-9]+$": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "array"},
                        "type": {"type": "string"}
                    },
                    "required": ["title", "content"]
                }
            }
        },
        "total_pages": {"type": "integer"},
        "extraction_time": {"type": "string", "format": "date-time"}
    }
}

@validator('selected_modules')
def validate_modules_schema(cls, v):
    try:
        validate(v, SELECTED_MODULES_SCHEMA)
    except ValidationError as e:
        raise ValueError(f"Invalid module structure: {e.message}")
    return v
```

## Migration Verification

### SQL Queries for Validation

```sql
-- Verify migration success
SELECT
    COUNT(*) as total_quizzes,
    COUNT(selected_modules_json) as migrated_modules,
    COUNT(extracted_content_json) as migrated_content
FROM quiz;

-- Check for migration failures
SELECT id, selected_modules
FROM quiz
WHERE selected_modules_json = '{}'::jsonb
    AND selected_modules IS NOT NULL
    AND selected_modules != '{}';

-- Performance comparison
EXPLAIN ANALYZE
SELECT * FROM quiz
WHERE selected_modules_json ? '123';  -- Fast with GIN index

-- vs old approach (if columns still exist)
EXPLAIN ANALYZE
SELECT * FROM quiz
WHERE selected_modules LIKE '%"123"%';  -- Full table scan!
```

## Success Criteria

### Performance Metrics

- **Query Speed**: 90%+ improvement for JSON searches
- **Parse Overhead**: Eliminated (0ms vs 1ms per access)
- **Storage Efficiency**: 20% reduction with JSONB compression
- **Index Performance**: <10ms for JSON key lookups

### Data Quality Metrics

- **Migration Success**: 100% of valid JSON migrated
- **Validation Rate**: 100% of new data validated
- **Query Accuracy**: No false positives in JSON searches

---
