"""Abstract base classes for question types and question generation."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.quiz.models import Quiz

    from .registry import QuestionTypeRegistry

# Type variable for question type implementations
T = TypeVar("T", bound="BaseQuestionType")


class QuestionType(str, Enum):
    """
    Enumeration of supported question types.

    To add a new question type:
    1. Add enum value here
    2. Create implementation in types/{type_name}.py
    3. Register in registry.py
    4. Add templates in templates/files/
    See ADDING_NEW_TYPES.md for detailed instructions.
    """

    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"


class QuestionDifficulty(str, Enum):
    """Question difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuizLanguage(str, Enum):
    """Supported languages for quiz question generation."""

    ENGLISH = "en"
    NORWEGIAN = "no"


class BaseQuestionData(BaseModel):
    """Base class for question type-specific data."""

    question_text: str = Field(min_length=1, max_length=2000)
    explanation: str | None = Field(default=None, max_length=1000)

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class BaseQuestionType(ABC):
    """Abstract base class for question type implementations."""

    @property
    @abstractmethod
    def question_type(self) -> QuestionType:
        """Return the question type enum."""
        pass

    @property
    @abstractmethod
    def data_model(self) -> type[BaseQuestionData]:
        """Return the data model class for this question type."""
        pass

    @abstractmethod
    def validate_data(self, data: dict[str, Any]) -> BaseQuestionData:
        """Validate and parse question data."""
        pass

    @abstractmethod
    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """Format question data for API display."""
        pass

    @abstractmethod
    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """Format question data for Canvas LMS export."""
        pass

    @abstractmethod
    def format_for_export(self, data: BaseQuestionData) -> dict[str, Any]:
        """Format question data for generic export."""
        pass


def generate_canvas_title(question_text: str, max_length: int = 50) -> str:
    """Generate a Canvas-compatible title from question text.

    Args:
        question_text: The question text to generate title from
        max_length: Maximum length for the title (default: 50)

    Returns:
        Title formatted as "Question {truncated_text}..."
    """
    if len(question_text) <= max_length:
        return f"Question {question_text}"
    else:
        return f"Question {question_text[:max_length]}..."


class Question(SQLModel, table=True):
    """
    Polymorphic question model supporting multiple question types.

    This model uses a discriminator field to support different question types
    while maintaining referential integrity and performance.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: uuid.UUID = Field(
        foreign_key="quiz.id", nullable=False, ondelete="CASCADE", index=True
    )
    quiz: "Quiz" = Relationship(back_populates="questions")

    # Question type discrimination
    question_type: QuestionType = Field(index=True, description="Type of question")

    # Flexible question data storage
    question_data: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default={}),
        description="Question type-specific data",
    )

    # Question metadata
    difficulty: QuestionDifficulty | None = Field(default=None, index=True)
    tags: list[str] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))

    # Approval workflow
    is_approved: bool = Field(
        default=False, description="Whether question is approved", index=True
    )
    approved_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True),
        default=None,
        description="Timestamp when question was approved",
    )

    # Audit fields
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=True
        ),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=func.now(),
            nullable=True,
        ),
    )

    # Canvas integration
    canvas_item_id: str | None = Field(
        default=None, description="Canvas quiz item ID after export"
    )

    def get_typed_data(
        self, question_registry: "QuestionTypeRegistry"
    ) -> BaseQuestionData:
        """Get strongly-typed question data using the question registry."""
        question_impl = question_registry.get_question_type(self.question_type)
        return question_impl.validate_data(self.question_data)


class GenerationParameters(BaseModel):
    """Base parameters for question generation."""

    target_count: int = Field(
        ge=1, le=100, description="Number of questions to generate"
    )
    difficulty: QuestionDifficulty | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    custom_instructions: str | None = Field(default=None, max_length=500)
    language: QuizLanguage = Field(
        default=QuizLanguage.ENGLISH, description="Language for question generation"
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class GenerationResult(BaseModel):
    """Result of question generation process."""

    success: bool
    questions_generated: int
    target_questions: int
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now())
