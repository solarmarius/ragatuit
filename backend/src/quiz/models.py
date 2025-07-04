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


class Quiz(SQLModel, table=True):
    """Quiz model representing a quiz with questions generated from Canvas content."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    owner: Optional["User"] = Relationship(back_populates="quizzes")
    canvas_course_id: int = Field(index=True)
    canvas_course_name: str
    selected_modules: dict[str, str] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, default={})
    )
    title: str = Field(min_length=1)
    question_count: int = Field(default=100, ge=1, le=200)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)
    content_extraction_status: str = Field(
        default="pending",
        description="Status of content extraction: pending, processing, completed, failed",
        index=True,
    )
    llm_generation_status: str = Field(
        default="pending",
        description="Status of LLM generation: pending, processing, completed, failed",
        index=True,
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
    export_status: str = Field(
        default="pending",
        description="Status of Canvas export: pending, processing, completed, failed",
        index=True,
    )
    exported_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True),
        default=None,
        description="Timestamp when quiz was exported to Canvas",
    )
    questions: list["Question"] = Relationship(
        back_populates="quiz", cascade_delete=True
    )

    # Pydantic validators for structure
    @field_validator("selected_modules")
    def validate_selected_modules(cls, v: Any) -> dict[str, str]:
        """Ensure selected_modules has correct structure."""
        if not isinstance(v, dict):
            raise ValueError("selected_modules must be a dictionary")
        # Validate all keys are strings (module IDs)
        for _key, value in v.items():
            if not isinstance(value, str):
                raise ValueError(f"Module name must be string, got {type(value)}")
        return v

    @field_validator("extracted_content")
    def validate_extracted_content(cls, v: Any) -> dict[str, Any] | None:
        """Validate extracted content structure."""
        if v is not None and not isinstance(v, dict):
            raise ValueError("extracted_content must be a dictionary")
        return v
