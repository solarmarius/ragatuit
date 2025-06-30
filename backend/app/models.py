import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.quiz.models import Quiz


# User models moved to app.auth.models and app.auth.schemas


# Quiz model and schemas moved to app.quiz.models and app.quiz.schemas


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


class QuestionCreate(SQLModel):
    quiz_id: uuid.UUID
    question_text: str = Field(min_length=1, max_length=2000)
    option_a: str = Field(min_length=1, max_length=500)
    option_b: str = Field(min_length=1, max_length=500)
    option_c: str = Field(min_length=1, max_length=500)
    option_d: str = Field(min_length=1, max_length=500)
    correct_answer: str = Field(regex=r"^[ABCD]$", description="Must be A, B, C, or D")


class QuestionUpdate(SQLModel):
    question_text: str | None = Field(default=None, min_length=1, max_length=2000)
    option_a: str | None = Field(default=None, min_length=1, max_length=500)
    option_b: str | None = Field(default=None, min_length=1, max_length=500)
    option_c: str | None = Field(default=None, min_length=1, max_length=500)
    option_d: str | None = Field(default=None, min_length=1, max_length=500)
    correct_answer: str | None = Field(
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
    approved_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    canvas_item_id: str | None
