"""Question schemas for validation and serialization with polymorphic support."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .types import QuestionDifficulty, QuestionType


class QuestionCreateRequest(BaseModel):
    """Schema for creating a new question."""

    quiz_id: uuid.UUID
    question_type: QuestionType
    question_data: dict[str, Any] = Field(description="Question type-specific data")
    difficulty: QuestionDifficulty | None = None
    tags: list[str] | None = None

    class Config:
        use_enum_values = True


class QuestionUpdateRequest(BaseModel):
    """Schema for updating a question."""

    question_data: dict[str, Any] | None = Field(
        default=None, description="Updated question data"
    )
    difficulty: QuestionDifficulty | None = None
    tags: list[str] | None = None

    class Config:
        use_enum_values = True


class QuestionResponse(BaseModel):
    """Public question schema for API responses."""

    id: uuid.UUID
    quiz_id: uuid.UUID
    question_type: QuestionType
    question_data: dict[str, Any]
    difficulty: QuestionDifficulty | None = None
    tags: list[str] | None = None
    is_approved: bool
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    canvas_item_id: str | None = None

    class Config:
        use_enum_values = True
