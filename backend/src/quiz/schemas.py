"""Quiz schemas for validation and serialization."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import Field, SQLModel


class QuizCreate(SQLModel):
    """Schema for creating a new quiz."""

    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[int, str]
    title: str = Field(min_length=1, max_length=255)
    question_count: int = Field(default=100, ge=1, le=200)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)


class QuizUpdate(SQLModel):
    """Schema for updating quiz settings."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    question_count: int | None = Field(default=None, ge=1, le=200)
    llm_model: str | None = None
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class QuizPublic(SQLModel):
    """Public quiz schema for API responses."""

    id: UUID
    owner_id: UUID
    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[str, str]
    title: str
    question_count: int
    llm_model: str
    llm_temperature: float
    content_extraction_status: str
    llm_generation_status: str
    extracted_content: dict[str, Any] | None
    content_extracted_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    canvas_quiz_id: str | None
    export_status: str
    exported_at: datetime | None


class QuizContentUpdate(SQLModel):
    """Schema for updating quiz content extraction results."""

    content_extraction_status: str
    extracted_content: dict[str, Any] | None = None
    content_extracted_at: datetime | None = None


class QuizGenerationUpdate(SQLModel):
    """Schema for updating quiz generation status."""

    llm_generation_status: str


class QuizExportUpdate(SQLModel):
    """Schema for updating quiz export results."""

    export_status: str
    canvas_quiz_id: str | None = None
    exported_at: datetime | None = None
