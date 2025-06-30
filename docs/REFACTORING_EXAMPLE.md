# Refactoring Example: Quiz Module Transformation

## Before: Current Monolithic Structure

### Current Files Involved
- `app/models.py` (Quiz model mixed with all others)
- `app/crud.py` (Quiz CRUD mixed with all others)
- `app/api/routes/quiz.py` (Routes only)
- `app/services/content_extraction.py` (Business logic)
- `app/services/mcq_generation.py` (Business logic)

### Example: Current Quiz Implementation

```python
# app/models.py (272 lines total, Quiz portion shown)
class Quiz(SQLModel, table=True):
    __tablename__ = "quizzes"

    id: int = Field(default=None, primary_key=True)
    title: str
    user_id: int = Field(foreign_key="users.id")
    canvas_course_id: str
    canvas_quiz_id: Optional[str] = None
    status: str = Field(default="draft")
    settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships mixed in same file
    user: User = Relationship(back_populates="quizzes")
    questions: List["Question"] = Relationship(back_populates="quiz")

class QuizCreate(BaseModel):
    title: str
    canvas_course_id: str
    settings: Dict[str, Any] = {}

# app/crud.py (537 lines total, Quiz CRUD portion)
def create_quiz(db: Session, quiz: QuizCreate, user_id: int) -> Quiz:
    db_quiz = Quiz(**quiz.dict(), user_id=user_id)
    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)
    return db_quiz

def get_quiz(db: Session, quiz_id: int) -> Optional[Quiz]:
    return db.query(Quiz).filter(Quiz.id == quiz_id).first()

# app/api/routes/quiz.py
@router.post("/", response_model=QuizResponse)
async def create_quiz(
    quiz: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud.create_quiz(db, quiz, current_user.id)
```

## After: Modular Feature-Based Structure

### New File Structure (Following the Guide Exactly)
```
src/
└── quiz/
    ├── router.py      # API endpoints
    ├── schemas.py     # Pydantic models
    ├── models.py      # Database models
    ├── dependencies.py # Route dependencies
    ├── config.py      # Quiz-specific config
    ├── constants.py   # Status enums, limits
    ├── exceptions.py  # Custom exceptions
    ├── service.py     # Business logic
    └── utils.py       # Helper functions
```

### Transformed Implementation

```python
# src/quiz/models.py
from sqlmodel import SQLModel, Field, Relationship, Column, JSONB
from datetime import datetime
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..auth.models import User
    from ..question.models import Question

class Quiz(SQLModel, table=True):
    """Quiz model representing a quiz instance."""
    __tablename__ = "quizzes"

    id: int = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    canvas_course_id: str = Field(index=True)
    canvas_course_name: Optional[str] = None
    canvas_quiz_id: Optional[str] = None
    status: str = Field(default="draft", index=True)
    settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    extracted_content: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="quizzes")
    questions: List["Question"] = Relationship(back_populates="quiz", cascade_delete=True)

# src/quiz/schemas.py
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Dict, Any, List, Optional
from .constants import QuizStatus, MAX_TITLE_LENGTH

class QuizCreate(BaseModel):
    """Schema for creating a new quiz."""
    title: str = Field(..., max_length=MAX_TITLE_LENGTH)
    canvas_course_id: str
    canvas_course_name: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)

    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

class QuizUpdate(BaseModel):
    """Schema for updating quiz details."""
    title: Optional[str] = Field(None, max_length=MAX_TITLE_LENGTH)
    status: Optional[QuizStatus] = None
    settings: Optional[Dict[str, Any]] = None

class QuizResponse(BaseModel):
    """Schema for quiz responses."""
    id: int
    title: str
    user_id: int
    canvas_course_id: str
    canvas_course_name: Optional[str]
    canvas_quiz_id: Optional[str]
    status: str
    settings: Dict[str, Any]
    question_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# src/quiz/constants.py
from enum import Enum

class QuizStatus(str, Enum):
    """Valid quiz statuses."""
    DRAFT = "draft"
    EXTRACTING = "extracting"
    GENERATING = "generating"
    READY = "ready"
    PUBLISHED = "published"
    ERROR = "error"

# Configuration constants
MAX_TITLE_LENGTH = 200
MAX_QUESTIONS_PER_QUIZ = 100
DEFAULT_QUESTION_COUNT = 10
EXTRACTION_TIMEOUT = 300  # seconds
GENERATION_TIMEOUT = 600  # seconds

# src/quiz/exceptions.py
from typing import Optional

class QuizException(Exception):
    """Base exception for quiz-related errors."""
    pass

class QuizNotFound(QuizException):
    """Raised when a quiz is not found."""
    def __init__(self, quiz_id: int):
        self.quiz_id = quiz_id
        super().__init__(f"Quiz with id {quiz_id} not found")

class QuizAccessDenied(QuizException):
    """Raised when user doesn't have access to a quiz."""
    def __init__(self, quiz_id: int, user_id: int):
        self.quiz_id = quiz_id
        self.user_id = user_id
        super().__init__(f"User {user_id} cannot access quiz {quiz_id}")

class QuizStatusError(QuizException):
    """Raised when quiz is in invalid status for operation."""
    def __init__(self, quiz_id: int, current_status: str, required_status: str):
        self.quiz_id = quiz_id
        super().__init__(
            f"Quiz {quiz_id} is in status '{current_status}', "
            f"but '{required_status}' is required"
        )

# src/quiz/service.py
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, func
from datetime import datetime
import asyncio

from .models import Quiz
from .schemas import QuizCreate, QuizUpdate, QuizResponse
from .constants import QuizStatus, MAX_QUESTIONS_PER_QUIZ
from .exceptions import QuizNotFound, QuizAccessDenied, QuizStatusError
from ..auth.models import User
from ..question.models import Question
from ..canvas.service import CanvasService
from ..core.logging import get_logger

logger = get_logger(__name__)

class QuizService:
    """Service layer for quiz operations."""

    def __init__(self, session: Session, canvas_service: Optional[CanvasService] = None):
        self.session = session
        self.canvas_service = canvas_service

    async def create_quiz(self, user: User, quiz_data: QuizCreate) -> Quiz:
        """Create a new quiz for a user."""
        quiz = Quiz(
            **quiz_data.model_dump(),
            user_id=user.id,
            status=QuizStatus.DRAFT
        )
        self.session.add(quiz)
        self.session.commit()
        self.session.refresh(quiz)

        logger.info(f"Created quiz {quiz.id} for user {user.id}")
        return quiz

    async def get_quiz(self, quiz_id: int, user: User) -> Quiz:
        """Get a quiz by ID with access control."""
        quiz = self.session.get(Quiz, quiz_id)

        if not quiz:
            raise QuizNotFound(quiz_id)

        if quiz.user_id != user.id:
            raise QuizAccessDenied(quiz_id, user.id)

        return quiz

    async def list_user_quizzes(
        self,
        user: User,
        skip: int = 0,
        limit: int = 20
    ) -> List[Quiz]:
        """List all quizzes for a user."""
        statement = (
            select(Quiz)
            .where(Quiz.user_id == user.id)
            .order_by(Quiz.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    async def update_quiz(
        self,
        quiz_id: int,
        user: User,
        update_data: QuizUpdate
    ) -> Quiz:
        """Update quiz details."""
        quiz = await self.get_quiz(quiz_id, user)

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(quiz, field, value)

        quiz.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(quiz)

        return quiz

    async def extract_content(self, quiz_id: int, user: User) -> Quiz:
        """Extract content from Canvas for quiz generation."""
        quiz = await self.get_quiz(quiz_id, user)

        if quiz.status != QuizStatus.DRAFT:
            raise QuizStatusError(quiz_id, quiz.status, QuizStatus.DRAFT)

        # Update status
        quiz.status = QuizStatus.EXTRACTING
        self.session.commit()

        try:
            # Extract content using Canvas service
            if self.canvas_service:
                content = await self.canvas_service.extract_course_content(
                    user.canvas_tokens,
                    quiz.canvas_course_id
                )
                quiz.extracted_content = content
                quiz.status = QuizStatus.READY
            else:
                raise ValueError("Canvas service not available")

        except Exception as e:
            logger.error(f"Content extraction failed for quiz {quiz_id}: {e}")
            quiz.status = QuizStatus.ERROR
            raise
        finally:
            self.session.commit()

        return quiz

    async def delete_quiz(self, quiz_id: int, user: User) -> bool:
        """Delete a quiz and all associated questions."""
        quiz = await self.get_quiz(quiz_id, user)

        if quiz.status == QuizStatus.PUBLISHED:
            raise QuizStatusError(
                quiz_id,
                quiz.status,
                "any status except published"
            )

        self.session.delete(quiz)
        self.session.commit()

        logger.info(f"Deleted quiz {quiz_id}")
        return True

    def get_quiz_statistics(self, quiz: Quiz) -> Dict[str, Any]:
        """Get statistics for a quiz."""
        total_questions = len(quiz.questions)
        approved_questions = sum(1 for q in quiz.questions if q.is_approved)

        return {
            "total_questions": total_questions,
            "approved_questions": approved_questions,
            "approval_rate": approved_questions / total_questions if total_questions > 0 else 0,
            "status": quiz.status,
            "created_at": quiz.created_at,
            "updated_at": quiz.updated_at
        }

# src/quiz/dependencies.py
from fastapi import Depends
from sqlmodel import Session
from typing import Annotated

from .service import QuizService
from ..database import get_session
from ..canvas.dependencies import get_canvas_service
from ..canvas.service import CanvasService

def get_quiz_service(
    session: Annotated[Session, Depends(get_session)],
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)]
) -> QuizService:
    """Dependency to get quiz service instance."""
    return QuizService(session, canvas_service)

# src/quiz/router.py
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Annotated

from .schemas import QuizCreate, QuizUpdate, QuizResponse
from .service import QuizService
from .dependencies import get_quiz_service
from .exceptions import QuizNotFound, QuizAccessDenied, QuizStatusError
from ..auth.dependencies import get_current_user
from ..auth.models import User

router = APIRouter(prefix="/quizzes", tags=["quizzes"])

@router.post("/", response_model=QuizResponse)
async def create_quiz(
    quiz_data: QuizCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[QuizService, Depends(get_quiz_service)]
) -> QuizResponse:
    """Create a new quiz."""
    quiz = await service.create_quiz(current_user, quiz_data)
    return QuizResponse.model_validate(quiz)

@router.get("/", response_model=List[QuizResponse])
async def list_quizzes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[QuizService, Depends(get_quiz_service)]
) -> List[QuizResponse]:
    """List user's quizzes."""
    quizzes = await service.list_user_quizzes(current_user, skip, limit)
    return [QuizResponse.model_validate(quiz) for quiz in quizzes]

@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[QuizService, Depends(get_quiz_service)]
) -> QuizResponse:
    """Get a specific quiz."""
    try:
        quiz = await service.get_quiz(quiz_id, current_user)
        response = QuizResponse.model_validate(quiz)
        response.question_count = len(quiz.questions)
        return response
    except QuizNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except QuizAccessDenied as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.patch("/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: int,
    update_data: QuizUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[QuizService, Depends(get_quiz_service)]
) -> QuizResponse:
    """Update quiz details."""
    try:
        quiz = await service.update_quiz(quiz_id, current_user, update_data)
        return QuizResponse.model_validate(quiz)
    except (QuizNotFound, QuizAccessDenied) as e:
        raise HTTPException(
            status_code=404 if isinstance(e, QuizNotFound) else 403,
            detail=str(e)
        )

@router.post("/{quiz_id}/extract-content", response_model=QuizResponse)
async def extract_content(
    quiz_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[QuizService, Depends(get_quiz_service)]
) -> QuizResponse:
    """Extract content from Canvas for the quiz."""
    try:
        quiz = await service.extract_content(quiz_id, current_user)
        return QuizResponse.model_validate(quiz)
    except QuizStatusError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (QuizNotFound, QuizAccessDenied) as e:
        raise HTTPException(
            status_code=404 if isinstance(e, QuizNotFound) else 403,
            detail=str(e)
        )

@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[QuizService, Depends(get_quiz_service)]
) -> dict:
    """Delete a quiz."""
    try:
        await service.delete_quiz(quiz_id, current_user)
        return {"detail": "Quiz deleted successfully"}
    except QuizStatusError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (QuizNotFound, QuizAccessDenied) as e:
        raise HTTPException(
            status_code=404 if isinstance(e, QuizNotFound) else 403,
            detail=str(e)
        )

# src/quiz/utils.py
from typing import Dict, Any, List
import json

def format_quiz_title(course_name: str, topic: str = None) -> str:
    """Generate a formatted quiz title."""
    if topic:
        return f"{course_name} - {topic} Quiz"
    return f"{course_name} Quiz"

def validate_quiz_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize quiz settings."""
    defaults = {
        "time_limit": 60,  # minutes
        "question_count": 10,
        "shuffle_questions": True,
        "shuffle_answers": True,
        "show_correct_answers": False,
        "attempts_allowed": 1
    }

    # Merge with defaults
    validated = {**defaults, **settings}

    # Validate ranges
    validated["time_limit"] = max(1, min(validated["time_limit"], 300))
    validated["question_count"] = max(1, min(validated["question_count"], 100))
    validated["attempts_allowed"] = max(1, min(validated["attempts_allowed"], 10))

    return validated

def calculate_quiz_score(questions: List[Dict[str, Any]]) -> float:
    """Calculate the total possible score for a quiz."""
    return sum(q.get("points", 1.0) for q in questions)

# src/quiz/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class QuizConfig(BaseSettings):
    """Quiz module configuration."""

    # Quiz limits
    max_questions_per_quiz: int = 100
    default_question_count: int = 10
    max_quiz_title_length: int = 200

    # Timeouts
    extraction_timeout_seconds: int = 300
    generation_timeout_seconds: int = 600

    # Canvas integration
    canvas_quiz_type: str = "assignment"
    canvas_default_points: float = 1.0

    class Config:
        env_prefix = "QUIZ_"
```

## Key Transformation Benefits

### 1. **Clear Module Boundaries**
- All quiz-related code in one place
- Easy to understand what belongs to quiz functionality
- Clear dependencies between modules

### 2. **Improved Testability**
- Service layer can be tested in isolation
- Mock dependencies easily
- Clear test structure matching module structure

### 3. **Better Maintainability**
- Changes to quiz logic contained within module
- Easy to find related code
- Consistent patterns across modules

### 4. **Enhanced Developer Experience**
- New developers can understand quiz functionality quickly
- Clear import paths
- Predictable file locations

### 5. **Scalability**
- Easy to add new features to quiz module
- Can split large modules if needed
- Clear extension points

## Migration Steps for This Module

1. **Create directory structure**
   ```bash
   mkdir -p src/quiz
   touch src/quiz/{__init__,router,schemas,models,dependencies,config,constants,exceptions,service,utils}.py
   ```

2. **Extract and move code**
   - Move Quiz model from `models.py`
   - Move quiz schemas from `models.py`
   - Convert CRUD functions to service methods
   - Move routes keeping API compatibility

3. **Update imports across codebase**
   - Search and replace old imports
   - Update test imports
   - Fix circular dependencies

4. **Test thoroughly**
   - Run existing tests
   - Add new tests for service layer
   - Integration testing

5. **Document changes**
   - Update API documentation
   - Add module README
   - Update developer guides
