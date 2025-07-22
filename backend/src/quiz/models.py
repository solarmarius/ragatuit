"""Quiz database models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from pydantic import field_validator
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.auth.models import User
    from src.question.models import Question

from src.question.types import QuestionType, QuizLanguage

from .schemas import FailureReason, QuizStatus


class Quiz(SQLModel, table=True):
    """Quiz model representing a quiz with questions generated from Canvas content."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    owner: Optional["User"] = Relationship(back_populates="quizzes")
    canvas_course_id: int = Field(index=True)
    canvas_course_name: str
    selected_modules: dict[str, dict[str, Any]] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, default={})
    )
    title: str = Field(min_length=1)
    question_count: int = Field(default=100, ge=1)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)
    language: QuizLanguage = Field(
        default=QuizLanguage.ENGLISH,
        description="Language for question generation",
    )
    question_type: QuestionType = Field(
        default=QuestionType.MULTIPLE_CHOICE,
        description="Type of questions to generate",
    )
    status: QuizStatus = Field(
        default=QuizStatus.CREATED,
        description="Consolidated quiz status",
        index=True,
    )
    failure_reason: FailureReason | None = Field(
        default=None,
        description="Specific failure reason when status is failed",
        index=True,
    )
    last_status_update: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    extracted_content: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    content_extracted_at: datetime | None = Field(
        default=None,
        description="Timestamp when content extraction was completed",
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
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
    canvas_quiz_id: str | None = Field(
        default=None, description="Canvas quiz assignment ID after export"
    )
    exported_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True),
        default=None,
        description="Timestamp when quiz was exported to Canvas",
    )
    generation_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default={}),
        description="Additional metadata for tracking generation details",
    )
    questions: list["Question"] = Relationship(
        back_populates="quiz", cascade_delete=True
    )
    deleted: bool = Field(
        default=False,
        index=True,
        description="Soft delete flag for data preservation",
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Timestamp when quiz was soft deleted",
    )

    @property
    def module_question_distribution(self) -> dict[str, int]:
        """Get question count per module."""
        return {
            module_id: module_data.get("question_count", 0)
            for module_id, module_data in self.selected_modules.items()
        }

    @property
    def total_questions_from_modules(self) -> int:
        """Calculate total questions from module distribution."""
        return sum(
            module_data.get("question_count", 0)
            for module_data in self.selected_modules.values()
        )

    # Pydantic validators for structure
    @field_validator("selected_modules")
    def validate_selected_modules(cls, v: Any) -> dict[str, dict[str, Any]]:
        """Ensure selected_modules has correct structure."""
        if not isinstance(v, dict):
            raise ValueError("selected_modules must be a dictionary")

        # Validate structure for each module
        for module_id, module_data in v.items():
            if not isinstance(module_data, dict):
                raise ValueError(f"Module {module_id} data must be a dictionary")

            # Check required fields
            if "name" not in module_data:
                raise ValueError(f"Module {module_id} missing required 'name' field")

            if "question_count" not in module_data:
                raise ValueError(
                    f"Module {module_id} missing required 'question_count' field"
                )

            # Validate types
            if not isinstance(module_data["name"], str):
                raise ValueError(f"Module {module_id} name must be string")

            if not isinstance(module_data["question_count"], int):
                raise ValueError(f"Module {module_id} question_count must be integer")

            # Validate question count range
            if not (1 <= module_data["question_count"] <= 20):
                raise ValueError(
                    f"Module {module_id} question_count must be between 1 and 20"
                )

        return v

    @field_validator("extracted_content")
    def validate_extracted_content(cls, v: Any) -> dict[str, Any] | None:
        """Validate extracted content structure."""
        if v is not None and not isinstance(v, dict):
            raise ValueError("extracted_content must be a dictionary")
        return v
