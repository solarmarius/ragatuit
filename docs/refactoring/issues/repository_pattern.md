# 9. Repository Pattern Implementation

## Priority: Medium

**Estimated Effort**: 4 days
**Python Version**: 3.10+
**Dependencies**: SQLModel, SQLAlchemy 2.0+

## Problem Statement

### Current Situation

All CRUD operations are consolidated in a single 500+ line `crud.py` file without proper abstraction, making it difficult to maintain, test, and extend. Database operations are mixed with business logic throughout the codebase.

### Why It's a Problem

- **Monolithic CRUD File**: Single file with 500+ lines is difficult to navigate
- **No Abstraction**: Direct database queries scattered throughout codebase
- **Poor Testability**: Cannot easily mock data access layer
- **Code Duplication**: Similar query patterns repeated across functions
- **No Transaction Management**: Inconsistent transaction boundaries
- **Mixed Responsibilities**: Business logic mixed with data access

### Affected Modules

- `app/crud.py` - Monolithic CRUD operations file
- `app/api/routes/` - Direct CRUD function usage
- `app/services/` - Services calling CRUD directly
- Testing infrastructure lacking proper mocking

### Technical Debt Assessment

- **Risk Level**: Medium - Affects maintainability and testing
- **Impact**: All database operations and testing
- **Cost of Delay**: Increases with each new model and operation

## Current Implementation Analysis

```python
# File: app/crud.py (current monolithic structure)
from sqlmodel import Session, select
from uuid import UUID
from typing import Optional, List

# PROBLEM: All operations in single file, no abstraction
def create_user(session: Session, user_create: UserCreate) -> User:
    """Create user."""
    # Direct database operations
    user = User(**user_create.model_dump())
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def get_user(session: Session, user_id: UUID) -> User | None:
    """Get user by ID."""
    # PROBLEM: Repetitive pattern
    return session.get(User, user_id)

def update_user(session: Session, user: User, user_update: UserUpdate) -> User:
    """Update user."""
    # PROBLEM: No transaction management
    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def delete_user(session: Session, user: User) -> None:
    """Delete user."""
    # PROBLEM: Hard delete, no soft delete option
    session.delete(user)
    session.commit()

# Similar patterns repeated for Quiz, Question, etc.
def create_quiz(session: Session, quiz_create: QuizCreate, owner_id: UUID) -> Quiz:
    """Create quiz."""
    # PROBLEM: Duplicate pattern
    quiz = Quiz(**quiz_create.model_dump(), owner_id=owner_id)
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    return quiz

def get_quiz_by_id(session: Session, quiz_id: UUID) -> Quiz | None:
    """Get quiz by ID."""
    # PROBLEM: No eager loading options
    return session.get(Quiz, quiz_id)

def get_user_quizzes(session: Session, user_id: UUID) -> List[Quiz]:
    """Get all quizzes for user."""
    # PROBLEM: No pagination, filtering, or sorting options
    statement = select(Quiz).where(Quiz.owner_id == user_id)
    return list(session.exec(statement).all())
```

### Problems with Current Approach

```python
# Direct database operations in routes
@router.get("/{quiz_id}")
def get_quiz_endpoint(quiz_id: UUID, session: SessionDep) -> Quiz:
    # PROBLEM: Direct database query in route
    quiz = session.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz not found")
    return quiz

# Testing difficulties
def test_get_quiz():
    # PROBLEM: Cannot easily mock database operations
    # Must use real database or complex mocking
    pass
```

### Python Anti-patterns Identified

- **God Object**: Single file handling all database operations
- **Lack of Abstraction**: No interface between business logic and data access
- **Code Duplication**: Repetitive CRUD patterns
- **Mixed Concerns**: Business logic mixed with data access
- **Poor Encapsulation**: No proper domain object encapsulation

## Proposed Solution

### Pythonic Approach

Implement the Repository Pattern with generic base repository, domain-specific repositories, and proper abstraction using Python's Protocol for type safety and testability.

### Design Patterns

- **Repository Pattern**: Abstract data access layer
- **Unit of Work Pattern**: Manage transaction boundaries
- **Generic Repository**: Reduce code duplication
- **Specification Pattern**: Flexible query building
- **Protocol Pattern**: Type-safe interfaces

### Code Examples

```python
# File: app/repositories/base.py (NEW)
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from uuid import UUID
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, select, update, delete, func
from sqlalchemy import desc, asc
from sqlalchemy.orm import selectinload, joinedload

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class RepositoryProtocol(Protocol[ModelType]):
    """Protocol defining repository interface."""

    def get(self, id: UUID) -> Optional[ModelType]: ...
    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[ModelType]: ...
    def create(self, obj_in: CreateSchemaType) -> ModelType: ...
    def update(self, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType: ...
    def delete(self, id: UUID) -> bool: ...

class BaseRepository(Generic[ModelType], ABC):
    """
    Base repository with common CRUD operations.

    This class provides standard CRUD operations that can be inherited
    by domain-specific repositories.
    """

    def __init__(self, session: Session, model: Type[ModelType]):
        """
        Initialize repository.

        Args:
            session: Database session
            model: SQLModel class
        """
        self.session = session
        self.model = model

    def get(self, id: UUID) -> Optional[ModelType]:
        """
        Get single record by ID.

        Args:
            id: Record identifier

        Returns:
            Model instance or None
        """
        return self.session.get(self.model, id)

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_direction: str = "desc",
        **filters
    ) -> List[ModelType]:
        """
        Get multiple records with filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field to order by
            order_direction: "asc" or "desc"
            **filters: Field filters

        Returns:
            List of model instances
        """
        query = select(self.model)

        # Apply filters
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)

        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_func = desc if order_direction == "desc" else asc
            query = query.order_by(order_func(getattr(self.model, order_by)))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        return list(self.session.exec(query).all())

    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create new record.

        Args:
            obj_in: Data for creating record

        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def update(
        self,
        db_obj: ModelType,
        obj_in: Dict[str, Any],
        exclude_unset: bool = True
    ) -> ModelType:
        """
        Update existing record.

        Args:
            db_obj: Existing model instance
            obj_in: Update data
            exclude_unset: Whether to exclude unset fields

        Returns:
            Updated model instance
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=exclude_unset)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def delete(self, id: UUID) -> bool:
        """
        Delete record by ID.

        Args:
            id: Record identifier

        Returns:
            True if deleted, False if not found
        """
        db_obj = self.get(id)
        if db_obj:
            self.session.delete(db_obj)
            self.session.commit()
            return True
        return False

    def soft_delete(self, id: UUID) -> bool:
        """
        Soft delete record (mark as deleted).

        Args:
            id: Record identifier

        Returns:
            True if deleted, False if not found
        """
        if hasattr(self.model, 'is_deleted'):
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(is_deleted=True)
            )
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount > 0
        else:
            return self.delete(id)

    def count(self, **filters) -> int:
        """
        Count records with optional filtering.

        Args:
            **filters: Field filters

        Returns:
            Count of matching records
        """
        query = select(func.count(self.model.id))

        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)

        return self.session.exec(query).one()

    def exists(self, id: UUID) -> bool:
        """
        Check if record exists.

        Args:
            id: Record identifier

        Returns:
            True if exists, False otherwise
        """
        query = select(func.count(self.model.id)).where(self.model.id == id)
        return self.session.exec(query).one() > 0

    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records efficiently.

        Args:
            objects: List of object data

        Returns:
            List of created model instances
        """
        db_objects = [self.model(**obj_data) for obj_data in objects]
        self.session.add_all(db_objects)
        self.session.commit()

        for obj in db_objects:
            self.session.refresh(obj)

        return db_objects

    def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records efficiently.

        Args:
            updates: List of update data with 'id' field

        Returns:
            Number of updated records
        """
        if not updates:
            return 0

        # Group updates by fields being updated
        update_groups = {}
        for update_data in updates:
            if 'id' not in update_data:
                continue

            # Create key from fields being updated (excluding id)
            fields_key = tuple(sorted(k for k in update_data.keys() if k != 'id'))

            if fields_key not in update_groups:
                update_groups[fields_key] = []

            update_groups[fields_key].append(update_data)

        total_updated = 0

        for fields, group_updates in update_groups.items():
            if not fields:
                continue

            # Prepare bulk update statement
            ids = [update_data['id'] for update_data in group_updates]

            # Create case statements for each field
            case_statements = {}
            for field in fields:
                cases = {
                    update_data['id']: update_data[field]
                    for update_data in group_updates
                    if field in update_data
                }
                if cases:
                    case_statements[field] = cases

            if case_statements:
                stmt = update(self.model).where(self.model.id.in_(ids))

                # Add case statements for each field
                for field, cases in case_statements.items():
                    stmt = stmt.values({
                        field: sqlalchemy.case(
                            cases,
                            value=self.model.id
                        )
                    })

                result = self.session.execute(stmt)
                total_updated += result.rowcount

        self.session.commit()
        return total_updated

# File: app/repositories/user.py (NEW)
from typing import Optional, List
from uuid import UUID

from app.repositories.base import BaseRepository
from app.models import User, UserCreate, UserUpdate

class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User email address

        Returns:
            User instance or None
        """
        stmt = select(User).where(User.email == email)
        return self.session.exec(stmt).first()

    def get_by_canvas_id(self, canvas_id: int) -> Optional[User]:
        """
        Get user by Canvas ID.

        Args:
            canvas_id: Canvas user ID

        Returns:
            User instance or None
        """
        stmt = select(User).where(User.canvas_id == canvas_id)
        return self.session.exec(stmt).first()

    def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get active users (with valid tokens).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of active users
        """
        stmt = (
            select(User)
            .where(User.access_token.isnot(None))
            .where(User.expires_at > func.now())
            .order_by(desc(User.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

    def update_tokens(
        self,
        user: User,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> User:
        """
        Update user authentication tokens.

        Args:
            user: User instance
            access_token: New access token
            refresh_token: Optional refresh token
            expires_at: Token expiration time

        Returns:
            Updated user instance
        """
        user.access_token = access_token
        if refresh_token:
            user.refresh_token = refresh_token
        if expires_at:
            user.expires_at = expires_at

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def search_users(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Search users by name or email.

        Args:
            query: Search query
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of matching users
        """
        search_pattern = f"%{query}%"
        stmt = (
            select(User)
            .where(
                (User.full_name.ilike(search_pattern)) |
                (User.email.ilike(search_pattern))
            )
            .order_by(User.full_name)
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

# File: app/repositories/quiz.py (NEW)
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import selectinload, joinedload

from app.repositories.base import BaseRepository
from app.models import Quiz, Question, QuizCreate, QuizUpdate

class QuizRepository(BaseRepository[Quiz]):
    """Repository for Quiz model operations."""

    def __init__(self, session: Session):
        super().__init__(session, Quiz)

    def get_with_questions(
        self,
        quiz_id: UUID,
        approved_only: bool = False
    ) -> Optional[Quiz]:
        """
        Get quiz with questions using eager loading.

        Args:
            quiz_id: Quiz identifier
            approved_only: Only load approved questions

        Returns:
            Quiz with questions or None
        """
        query = select(Quiz).where(Quiz.id == quiz_id)

        if approved_only:
            # Load only approved questions
            query = query.options(
                selectinload(Quiz.questions).where(Question.is_approved == True)
            )
        else:
            # Load all questions
            query = query.options(selectinload(Quiz.questions))

        return self.session.exec(query).first()

    def get_by_owner(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None,
        course_filter: Optional[int] = None
    ) -> List[Quiz]:
        """
        Get quizzes by owner with optional filtering.

        Args:
            owner_id: Owner user ID
            skip: Number of records to skip
            limit: Maximum number of records
            status_filter: Optional status filter
            course_filter: Optional course ID filter

        Returns:
            List of user's quizzes
        """
        query = (
            select(Quiz)
            .where(Quiz.owner_id == owner_id)
            .order_by(desc(Quiz.created_at))
        )

        if status_filter:
            query = query.where(Quiz.content_extraction_status == status_filter)

        if course_filter:
            query = query.where(Quiz.canvas_course_id == course_filter)

        query = query.offset(skip).limit(limit)
        return list(self.session.exec(query).all())

    def get_with_question_counts(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get quizzes with question counts using efficient query.

        Args:
            owner_id: Owner user ID
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of quiz data with question counts
        """
        # Subquery for question counts
        question_counts_subquery = (
            select(
                Question.quiz_id,
                func.count(Question.id).label('total_questions'),
                func.sum(
                    func.case(
                        (Question.is_approved == True, 1),
                        else_=0
                    )
                ).label('approved_questions')
            )
            .group_by(Question.quiz_id)
            .subquery()
        )

        # Main query with left join
        stmt = (
            select(
                Quiz,
                func.coalesce(question_counts_subquery.c.total_questions, 0).label('total_questions'),
                func.coalesce(question_counts_subquery.c.approved_questions, 0).label('approved_questions')
            )
            .outerjoin(
                question_counts_subquery,
                Quiz.id == question_counts_subquery.c.quiz_id
            )
            .where(Quiz.owner_id == owner_id)
            .order_by(desc(Quiz.created_at))
            .offset(skip)
            .limit(limit)
        )

        results = self.session.exec(stmt).all()

        # Transform results
        quiz_data = []
        for quiz, total_questions, approved_questions in results:
            quiz_dict = quiz.model_dump()
            quiz_dict.update({
                'total_questions': total_questions,
                'approved_questions': approved_questions
            })
            quiz_data.append(quiz_dict)

        return quiz_data

    def get_by_course(
        self,
        course_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Quiz]:
        """
        Get quizzes by Canvas course ID.

        Args:
            course_id: Canvas course ID
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of course quizzes
        """
        stmt = (
            select(Quiz)
            .where(Quiz.canvas_course_id == course_id)
            .order_by(desc(Quiz.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

    def get_pending_extraction(self, limit: int = 50) -> List[Quiz]:
        """
        Get quizzes pending content extraction.

        Args:
            limit: Maximum number of records

        Returns:
            List of quizzes needing content extraction
        """
        stmt = (
            select(Quiz)
            .where(Quiz.content_extraction_status == "pending")
            .order_by(Quiz.created_at)  # Process oldest first
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

    def update_extraction_status(
        self,
        quiz_id: UUID,
        status: str,
        content_data: Optional[Dict[str, Any]] = None,
        extracted_at: Optional[datetime] = None
    ) -> bool:
        """
        Update quiz extraction status efficiently.

        Args:
            quiz_id: Quiz identifier
            status: New extraction status
            content_data: Optional extracted content
            extracted_at: Optional extraction timestamp

        Returns:
            True if updated, False if not found
        """
        update_values = {"content_extraction_status": status}

        if content_data is not None:
            update_values["content_dict"] = content_data

        if extracted_at is not None:
            update_values["content_extracted_at"] = extracted_at

        stmt = (
            update(Quiz)
            .where(Quiz.id == quiz_id)
            .values(**update_values)
        )

        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount > 0

    def search_quizzes(
        self,
        query: str,
        owner_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Quiz]:
        """
        Search quizzes by title or description.

        Args:
            query: Search query
            owner_id: Optional owner filter
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of matching quizzes
        """
        search_pattern = f"%{query}%"
        stmt = (
            select(Quiz)
            .where(
                (Quiz.title.ilike(search_pattern)) |
                (Quiz.description.ilike(search_pattern))
            )
        )

        if owner_id:
            stmt = stmt.where(Quiz.owner_id == owner_id)

        stmt = stmt.order_by(desc(Quiz.created_at)).offset(skip).limit(limit)
        return list(self.session.exec(stmt).all())

# File: app/repositories/question.py (NEW)
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.repositories.base import BaseRepository
from app.models import Question, QuestionCreate, QuestionUpdate

class QuestionRepository(BaseRepository[Question]):
    """Repository for Question model operations."""

    def __init__(self, session: Session):
        super().__init__(session, Question)

    def get_by_quiz(
        self,
        quiz_id: UUID,
        approved_only: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> List[Question]:
        """
        Get questions by quiz ID.

        Args:
            quiz_id: Quiz identifier
            approved_only: Only return approved questions
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of quiz questions
        """
        query = (
            select(Question)
            .where(Question.quiz_id == quiz_id)
            .order_by(desc(Question.created_at))
        )

        if approved_only:
            query = query.where(Question.is_approved == True)

        query = query.offset(skip).limit(limit)
        return list(self.session.exec(query).all())

    def search_questions(
        self,
        quiz_id: UUID,
        search_query: str,
        approved_only: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> List[Question]:
        """
        Search questions within a quiz.

        Args:
            quiz_id: Quiz identifier
            search_query: Text to search for
            approved_only: Only search approved questions
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of matching questions
        """
        search_pattern = f"%{search_query}%"
        query = (
            select(Question)
            .where(Question.quiz_id == quiz_id)
            .where(
                (Question.question_text.ilike(search_pattern)) |
                (Question.correct_answer.ilike(search_pattern))
            )
        )

        if approved_only:
            query = query.where(Question.is_approved == True)

        query = query.order_by(desc(Question.created_at)).offset(skip).limit(limit)
        return list(self.session.exec(query).all())

    def get_pending_approval(
        self,
        quiz_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[Question]:
        """
        Get questions pending approval.

        Args:
            quiz_id: Optional quiz ID filter
            limit: Maximum number of records

        Returns:
            List of questions needing approval
        """
        query = (
            select(Question)
            .where(Question.is_approved == False)
            .order_by(Question.created_at)
        )

        if quiz_id:
            query = query.where(Question.quiz_id == quiz_id)

        query = query.limit(limit)
        return list(self.session.exec(query).all())

    def bulk_approve(self, question_ids: List[UUID]) -> int:
        """
        Approve multiple questions efficiently.

        Args:
            question_ids: List of question IDs to approve

        Returns:
            Number of questions approved
        """
        stmt = (
            update(Question)
            .where(Question.id.in_(question_ids))
            .values(
                is_approved=True,
                approved_at=datetime.utcnow()
            )
        )

        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    def bulk_reject(self, question_ids: List[UUID]) -> int:
        """
        Reject multiple questions efficiently.

        Args:
            question_ids: List of question IDs to reject

        Returns:
            Number of questions rejected
        """
        result = self.session.execute(
            delete(Question).where(Question.id.in_(question_ids))
        )
        self.session.commit()
        return result.rowcount

    def get_statistics(self, quiz_id: UUID) -> Dict[str, int]:
        """
        Get question statistics for a quiz.

        Args:
            quiz_id: Quiz identifier

        Returns:
            Dictionary with question statistics
        """
        stats_query = (
            select(
                func.count(Question.id).label('total'),
                func.sum(
                    func.case(
                        (Question.is_approved == True, 1),
                        else_=0
                    )
                ).label('approved'),
                func.sum(
                    func.case(
                        (Question.is_approved == False, 1),
                        else_=0
                    )
                ).label('pending')
            )
            .where(Question.quiz_id == quiz_id)
        )

        result = self.session.exec(stats_query).first()

        return {
            'total': result.total or 0,
            'approved': result.approved or 0,
            'pending': result.pending or 0
        }

# File: app/repositories/dependencies.py (NEW)
from functools import lru_cache
from typing import Annotated
from fastapi import Depends

from app.core.db import get_session
from app.repositories.user import UserRepository
from app.repositories.quiz import QuizRepository
from app.repositories.question import QuestionRepository

def get_user_repository(session: SessionDep) -> UserRepository:
    """Get user repository instance."""
    return UserRepository(session)

def get_quiz_repository(session: SessionDep) -> QuizRepository:
    """Get quiz repository instance."""
    return QuizRepository(session)

def get_question_repository(session: SessionDep) -> QuestionRepository:
    """Get question repository instance."""
    return QuestionRepository(session)

# Type aliases for dependency injection
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
QuizRepositoryDep = Annotated[QuizRepository, Depends(get_quiz_repository)]
QuestionRepositoryDep = Annotated[QuestionRepository, Depends(get_question_repository)]

# File: app/services/unit_of_work.py (NEW)
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any

from sqlmodel import Session
from app.core.db import engine, get_session
from app.repositories.user import UserRepository
from app.repositories.quiz import QuizRepository
from app.repositories.question import QuestionRepository

class UnitOfWork:
    """
    Unit of Work pattern implementation for managing transactions.

    Provides a single transaction context across multiple repositories.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize Unit of Work.

        Args:
            session: Optional existing session
        """
        self._session = session
        self._own_session = session is None
        self._users: Optional[UserRepository] = None
        self._quizzes: Optional[QuizRepository] = None
        self._questions: Optional[QuestionRepository] = None

    @property
    def session(self) -> Session:
        """Get database session."""
        if not self._session:
            self._session = Session(engine)
        return self._session

    @property
    def users(self) -> UserRepository:
        """Get user repository."""
        if not self._users:
            self._users = UserRepository(self.session)
        return self._users

    @property
    def quizzes(self) -> QuizRepository:
        """Get quiz repository."""
        if not self._quizzes:
            self._quizzes = QuizRepository(self.session)
        return self._quizzes

    @property
    def questions(self) -> QuestionRepository:
        """Get question repository."""
        if not self._questions:
            self._questions = QuestionRepository(self.session)
        return self._questions

    def commit(self) -> None:
        """Commit transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback transaction."""
        self.session.rollback()

    def close(self) -> None:
        """Close session if owned by this unit of work."""
        if self._own_session and self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager with proper cleanup."""
        if exc_type:
            self.rollback()
        else:
            try:
                self.commit()
            except Exception:
                self.rollback()
                raise
        finally:
            self.close()

@contextmanager
def get_unit_of_work() -> Generator[UnitOfWork, None, None]:
    """
    Context manager for Unit of Work.

    Yields:
        UnitOfWork instance with managed transaction
    """
    uow = UnitOfWork()
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()

# File: app/api/routes/quiz.py (UPDATED to use repositories)
from app.repositories.dependencies import QuizRepositoryDep, QuestionRepositoryDep
from app.services.unit_of_work import get_unit_of_work

@router.get("/", response_model=PaginatedResponse[Quiz])
def get_user_quizzes_endpoint(
    current_user: CurrentUser,
    quiz_repo: QuizRepositoryDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    course_id: Optional[int] = Query(None)
) -> PaginatedResponse[Quiz]:
    """Get user's quizzes with pagination and filtering."""

    # Get quizzes using repository
    quizzes = quiz_repo.get_by_owner(
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
        status_filter=status,
        course_filter=course_id
    )

    # Get total count
    total = quiz_repo.count(owner_id=current_user.id)

    return PaginatedResponse(
        items=quizzes,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{quiz_id}/questions", response_model=PaginatedResponse[Question])
def get_quiz_questions_endpoint(
    quiz_id: UUID,
    current_user: CurrentUser,
    quiz_repo: QuizRepositoryDep,
    question_repo: QuestionRepositoryDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    approved_only: bool = Query(False),
    search: Optional[str] = Query(None)
) -> PaginatedResponse[Question]:
    """Get quiz questions with pagination and filtering."""

    # Verify quiz ownership
    quiz = quiz_repo.get(quiz_id)
    if not quiz or quiz.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Get questions using repository
    if search:
        questions = question_repo.search_questions(
            quiz_id=quiz_id,
            search_query=search,
            approved_only=approved_only,
            skip=skip,
            limit=limit
        )
    else:
        questions = question_repo.get_by_quiz(
            quiz_id=quiz_id,
            approved_only=approved_only,
            skip=skip,
            limit=limit
        )

    # Get total count
    total = question_repo.count(quiz_id=quiz_id)
    if approved_only:
        total = question_repo.count(quiz_id=quiz_id, is_approved=True)

    return PaginatedResponse(
        items=questions,
        total=total,
        skip=skip,
        limit=limit
    )

# Complex operation using Unit of Work
@router.post("/{quiz_id}/approve-questions")
def approve_quiz_questions(
    quiz_id: UUID,
    question_ids: List[UUID],
    current_user: CurrentUser
) -> Dict[str, Any]:
    """Approve multiple questions in a single transaction."""

    with get_unit_of_work() as uow:
        # Verify quiz ownership
        quiz = uow.quizzes.get(quiz_id)
        if not quiz or quiz.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Approve questions
        approved_count = uow.questions.bulk_approve(question_ids)

        # Update quiz status if all questions are approved
        stats = uow.questions.get_statistics(quiz_id)
        if stats['pending'] == 0 and stats['approved'] > 0:
            uow.quizzes.update(
                quiz,
                {"llm_generation_status": "completed"}
            )

        # Transaction committed automatically by context manager

        return {
            "message": f"Approved {approved_count} questions",
            "approved_count": approved_count,
            "quiz_status": "completed" if stats['pending'] == 0 else "in_progress"
        }
```

## Implementation Details

### Files to Create/Modify

```
backend/
├── app/
│   ├── repositories/
│   │   ├── __init__.py              # NEW: Package init
│   │   ├── base.py                  # NEW: Base repository
│   │   ├── user.py                  # NEW: User repository
│   │   ├── quiz.py                  # NEW: Quiz repository
│   │   ├── question.py              # NEW: Question repository
│   │   └── dependencies.py          # NEW: Repository dependencies
│   ├── services/
│   │   └── unit_of_work.py          # NEW: Unit of Work pattern
│   ├── crud.py                      # UPDATE: Migrate to repositories
│   ├── api/
│   │   └── routes/
│   │       ├── quiz.py              # UPDATE: Use repositories
│   │       ├── question.py          # UPDATE: Use repositories
│   │       └── user.py              # UPDATE: Use repositories
│   └── tests/
│       ├── repositories/
│       │   ├── test_base.py         # NEW: Base repository tests
│       │   ├── test_user.py         # NEW: User repository tests
│       │   ├── test_quiz.py         # NEW: Quiz repository tests
│       │   └── test_question.py     # NEW: Question repository tests
│       └── services/
│           └── test_unit_of_work.py  # NEW: UoW tests
```

### Migration Strategy

```python
# Phase 1: Create repositories alongside existing CRUD
# Phase 2: Update routes to use repositories gradually
# Phase 3: Remove old CRUD functions

# Backward compatibility during migration
def get_user_quizzes_legacy(session: Session, user_id: UUID) -> List[Quiz]:
    """Legacy function - use QuizRepository.get_by_owner instead."""
    repo = QuizRepository(session)
    return repo.get_by_owner(user_id)
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/repositories/test_base.py
import pytest
from unittest.mock import Mock
from uuid import uuid4

from app.repositories.base import BaseRepository
from app.models import User

class TestBaseRepository:

    @pytest.fixture
    def mock_session(self):
        return Mock()

    @pytest.fixture
    def user_repository(self, mock_session):
        return BaseRepository(mock_session, User)

    def test_get_by_id(self, user_repository, mock_session):
        """Test getting record by ID."""
        user_id = uuid4()
        mock_user = Mock()
        mock_session.get.return_value = mock_user

        result = user_repository.get(user_id)

        assert result == mock_user
        mock_session.get.assert_called_once_with(User, user_id)

    def test_create(self, user_repository, mock_session):
        """Test creating new record."""
        user_data = {"name": "Test User", "email": "test@example.com"}
        mock_user = Mock()

        # Mock the User constructor
        with patch('app.models.User') as mock_user_class:
            mock_user_class.return_value = mock_user

            result = user_repository.create(user_data)

            assert result == mock_user
            mock_session.add.assert_called_once_with(mock_user)
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_user)

# File: app/tests/repositories/test_quiz.py
def test_quiz_repository_get_by_owner(db_session, test_user, test_quizzes):
    """Test getting quizzes by owner."""

    repo = QuizRepository(db_session)

    # Get first page
    quizzes = repo.get_by_owner(test_user.id, skip=0, limit=5)

    assert len(quizzes) == 5
    assert all(quiz.owner_id == test_user.id for quiz in quizzes)

    # Test with status filter
    completed_quizzes = repo.get_by_owner(
        test_user.id,
        status_filter="completed"
    )

    assert all(quiz.content_extraction_status == "completed" for quiz in completed_quizzes)

def test_quiz_repository_get_with_question_counts(db_session, test_user):
    """Test getting quizzes with question counts."""

    # Create quiz with questions
    quiz = Quiz(owner_id=test_user.id, title="Test Quiz", canvas_course_id=123)
    db_session.add(quiz)
    db_session.flush()

    # Add questions
    for i in range(5):
        question = Question(
            quiz_id=quiz.id,
            question_text=f"Question {i}",
            correct_answer=f"Answer {i}",
            is_approved=(i < 3)  # First 3 approved
        )
        db_session.add(question)

    db_session.commit()

    repo = QuizRepository(db_session)
    quiz_data = repo.get_with_question_counts(test_user.id)

    assert len(quiz_data) == 1
    assert quiz_data[0]['total_questions'] == 5
    assert quiz_data[0]['approved_questions'] == 3

# File: app/tests/services/test_unit_of_work.py
def test_unit_of_work_commit(db_session):
    """Test Unit of Work commits successfully."""

    with get_unit_of_work() as uow:
        user_data = {
            "canvas_id": 123,
            "email": "test@example.com",
            "full_name": "Test User"
        }
        user = uow.users.create(user_data)

        quiz_data = {
            "owner_id": user.id,
            "title": "Test Quiz",
            "canvas_course_id": 456
        }
        quiz = uow.quizzes.create(quiz_data)

        # Should be committed automatically

    # Verify data was persisted
    with get_unit_of_work() as uow:
        saved_user = uow.users.get(user.id)
        saved_quiz = uow.quizzes.get(quiz.id)

        assert saved_user is not None
        assert saved_quiz is not None
        assert saved_quiz.owner_id == saved_user.id

def test_unit_of_work_rollback_on_exception(db_session):
    """Test Unit of Work rolls back on exception."""

    user_id = None

    try:
        with get_unit_of_work() as uow:
            user_data = {
                "canvas_id": 123,
                "email": "test@example.com",
                "full_name": "Test User"
            }
            user = uow.users.create(user_data)
            user_id = user.id

            # Force an exception
            raise Exception("Test exception")
    except Exception:
        pass

    # Verify data was not persisted
    with get_unit_of_work() as uow:
        saved_user = uow.users.get(user_id)
        assert saved_user is None
```

### Performance Tests

```python
# File: app/tests/performance/test_repository_performance.py
@pytest.mark.performance
def test_bulk_operations_performance(db_session):
    """Test bulk operations are efficient."""

    repo = QuestionRepository(db_session)

    # Create test data
    quiz_id = uuid4()
    question_data = [
        {
            "quiz_id": quiz_id,
            "question_text": f"Question {i}",
            "correct_answer": f"Answer {i}",
            "is_approved": False
        }
        for i in range(1000)
    ]

    # Test bulk create performance
    start_time = time.time()
    questions = repo.bulk_create(question_data)
    create_time = time.time() - start_time

    assert len(questions) == 1000
    assert create_time < 2.0  # Should complete in under 2 seconds

    # Test bulk approve performance
    question_ids = [q.id for q in questions[:500]]

    start_time = time.time()
    approved_count = repo.bulk_approve(question_ids)
    approve_time = time.time() - start_time

    assert approved_count == 500
    assert approve_time < 1.0  # Should complete in under 1 second
```

## Code Quality Improvements

### Type Safety

```python
# Enhanced type annotations for repositories
from typing import TypeVar, Generic, Protocol, runtime_checkable

@runtime_checkable
class Identifiable(Protocol):
    """Protocol for models with ID field."""
    id: UUID

ModelType = TypeVar("ModelType", bound=Identifiable)

class TypedRepository(Generic[ModelType]):
    """Type-safe repository base class."""
    pass
```

### Query Builder

```python
# File: app/repositories/query_builder.py
class QueryBuilder:
    """Fluent interface for building complex queries."""

    def __init__(self, model_class):
        self.model_class = model_class
        self._query = select(model_class)

    def where(self, condition):
        self._query = self._query.where(condition)
        return self

    def order_by(self, *fields):
        self._query = self._query.order_by(*fields)
        return self

    def limit(self, count):
        self._query = self._query.limit(count)
        return self

    def offset(self, count):
        self._query = self._query.offset(count)
        return self

    def build(self):
        return self._query

# Usage
query = (
    QueryBuilder(Quiz)
    .where(Quiz.owner_id == user_id)
    .where(Quiz.content_extraction_status == "completed")
    .order_by(desc(Quiz.created_at))
    .limit(20)
    .build()
)
```

## Success Criteria

### Code Quality Metrics

- **Reduced File Size**: Main CRUD file reduced from 500+ to <100 lines
- **Test Coverage**: >90% for all repositories
- **Type Coverage**: 100% type annotation coverage
- **Separation of Concerns**: Clear separation between data access and business logic

### Performance Metrics

- **Query Efficiency**: Optimized queries with proper eager loading
- **Bulk Operations**: Efficient bulk insert/update operations
- **Transaction Management**: Proper transaction boundaries

### Maintainability Metrics

- **Code Duplication**: Eliminated duplicate CRUD patterns
- **Modularity**: Each repository handles single domain
- **Testability**: Easy mocking and unit testing

---
