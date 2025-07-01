"""Question schemas for validation and serialization."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class QuestionCreate(SQLModel):
    """Schema for creating a new question."""

    quiz_id: uuid.UUID
    question_text: str = Field(min_length=1, max_length=2000)
    option_a: str = Field(min_length=1, max_length=500)
    option_b: str = Field(min_length=1, max_length=500)
    option_c: str = Field(min_length=1, max_length=500)
    option_d: str = Field(min_length=1, max_length=500)
    correct_answer: str = Field(regex=r"^[ABCD]$", description="Must be A, B, C, or D")


class QuestionUpdate(SQLModel):
    """Schema for updating a question."""

    question_text: str | None = Field(default=None, min_length=1, max_length=2000)
    option_a: str | None = Field(default=None, min_length=1, max_length=500)
    option_b: str | None = Field(default=None, min_length=1, max_length=500)
    option_c: str | None = Field(default=None, min_length=1, max_length=500)
    option_d: str | None = Field(default=None, min_length=1, max_length=500)
    correct_answer: str | None = Field(
        default=None, regex=r"^[ABCD]$", description="Must be A, B, C, or D"
    )


class QuestionPublic(SQLModel):
    """Public question schema for API responses."""

    id: uuid.UUID
    quiz_id: uuid.UUID
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    is_approved: bool
    approved_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    canvas_item_id: str | None
