import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

from pydantic import field_validator
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.auth.models import User


# User models moved to app.auth.models and app.auth.schemas


class Quiz(SQLModel, table=True):
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
    extracted_content: Optional[dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    content_extracted_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when content extraction was completed",
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=True
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=func.now(),
            nullable=True,
        ),
    )
    canvas_quiz_id: Optional[str] = Field(
        default=None, description="Canvas quiz assignment ID after export"
    )
    export_status: str = Field(
        default="pending",
        description="Status of Canvas export: pending, processing, completed, failed",
        index=True,
    )
    exported_at: Optional[datetime] = Field(
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
    def validate_extracted_content(cls, v: Any) -> Optional[dict[str, Any]]:
        """Validate extracted content structure."""
        if v is not None and not isinstance(v, dict):
            raise ValueError("extracted_content must be a dictionary")
        return v


class QuizCreate(SQLModel):
    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[int, str]
    title: str = Field(min_length=1, max_length=255)
    question_count: int = Field(default=100, ge=1, le=200)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)


# Auth schemas moved to app.auth.schemas


# Generic message
class Message(SQLModel):
    message: str


# Canvas auth schemas moved to app.auth.schemas


class CanvasConfigResponse(SQLModel):
    authorization_url: str
    client_id: str
    redirect_uri: str
    scope: str


class Question(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: uuid.UUID = Field(
        foreign_key="quiz.id", nullable=False, ondelete="CASCADE", index=True
    )
    quiz: Optional[Quiz] = Relationship(back_populates="questions")
    question_text: str = Field(min_length=1, max_length=2000)
    option_a: str = Field(min_length=1, max_length=500)
    option_b: str = Field(min_length=1, max_length=500)
    option_c: str = Field(min_length=1, max_length=500)
    option_d: str = Field(min_length=1, max_length=500)
    correct_answer: str = Field(regex=r"^[ABCD]$", description="Must be A, B, C, or D")
    is_approved: bool = Field(
        default=False, description="Whether question is approved", index=True
    )
    approved_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True),
        default=None,
        description="Timestamp when question was approved",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=True
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=func.now(),
            nullable=True,
        ),
    )
    canvas_item_id: Optional[str] = Field(
        default=None, description="Canvas quiz item ID after export"
    )


class QuestionCreate(SQLModel):
    quiz_id: uuid.UUID
    question_text: str = Field(min_length=1, max_length=2000)
    option_a: str = Field(min_length=1, max_length=500)
    option_b: str = Field(min_length=1, max_length=500)
    option_c: str = Field(min_length=1, max_length=500)
    option_d: str = Field(min_length=1, max_length=500)
    correct_answer: str = Field(regex=r"^[ABCD]$", description="Must be A, B, C, or D")


class QuestionUpdate(SQLModel):
    question_text: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    option_a: Optional[str] = Field(default=None, min_length=1, max_length=500)
    option_b: Optional[str] = Field(default=None, min_length=1, max_length=500)
    option_c: Optional[str] = Field(default=None, min_length=1, max_length=500)
    option_d: Optional[str] = Field(default=None, min_length=1, max_length=500)
    correct_answer: Optional[str] = Field(
        default=None, regex=r"^[ABCD]$", description="Must be A, B, C, or D"
    )


class QuestionPublic(SQLModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    is_approved: bool
    approved_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    canvas_item_id: Optional[str]
