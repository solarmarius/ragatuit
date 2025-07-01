"""Question model for quiz questions."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.quiz.models import Quiz


class Question(SQLModel, table=True):
    """Question model representing a quiz question with multiple choice options."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: uuid.UUID = Field(
        foreign_key="quiz.id", nullable=False, ondelete="CASCADE", index=True
    )
    quiz: Optional["Quiz"] = Relationship(back_populates="questions")
    question_text: str = Field(min_length=1, max_length=2000)
    option_a: str = Field(min_length=1, max_length=500)
    option_b: str = Field(min_length=1, max_length=500)
    option_c: str = Field(min_length=1, max_length=500)
    option_d: str = Field(min_length=1, max_length=500)
    correct_answer: str = Field(regex=r"^[ABCD]$", description="Must be A, B, C, or D")
    is_approved: bool = Field(
        default=False, description="Whether question is approved", index=True
    )
    approved_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True),
        default=None,
        description="Timestamp when question was approved",
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
    canvas_item_id: str | None = Field(
        default=None, description="Canvas quiz item ID after export"
    )
