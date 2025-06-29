import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, Relationship, SQLModel


class UserCreate(SQLModel):
    canvas_id: int = Field()
    name: str = Field()
    access_token: str = Field()
    refresh_token: str = Field()


class TokenUpdate(SQLModel):
    access_token: str = Field(default=None)
    refresh_token: str = Field(default=None)
    expires_at: datetime | None = Field(default=None)


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    canvas_id: int = Field(unique=True, index=True)
    name: str | None = Field(default=None, max_length=255)
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
    access_token: str = Field(description="Canvas access token")
    refresh_token: str = Field(description="Canvas refresh token")
    # 1 hour expiration from Canvas
    expires_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1),
        sa_column=Column(
            DateTime(timezone=True), nullable=True
        ),
    )
    token_type: str = Field(default="Bearer")
    onboarding_completed: bool = Field(
        default=False, description="Whether user has completed onboarding"
    )
    quizzes: list["Quiz"] = Relationship(back_populates="owner", cascade_delete=True)


class Quiz(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="quizzes")
    canvas_course_id: int = Field(index=True)
    canvas_course_name: str
    selected_modules: str = Field(description="JSON array of selected Canvas modules")
    title: str = Field(min_length=1)
    question_count: int = Field(default=100, ge=1, le=200)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)
    content_extraction_status: str = Field(
        default="pending",
        description="Status of content extraction: pending, processing, completed, failed",
    )
    llm_generation_status: str = Field(
        default="pending",
        description="Status of LLM generation: pending, processing, completed, failed",
    )
    extracted_content: str | None = Field(
        default=None, description="JSON string of extracted page content"
    )
    content_extracted_at: datetime | None = Field(
        default=None, description="Timestamp when content extraction was completed",         
        sa_column=Column(
            DateTime(timezone=True), nullable=True
        ),
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
    )
    exported_at: datetime | None = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=True
        ),
        default=None, description="Timestamp when quiz was exported to Canvas"
    )
    questions: list["Question"] = Relationship(
        back_populates="quiz", cascade_delete=True
    )

    # Methods to handle JSON strings for selected_modules field
    @property
    def modules_dict(self) -> dict[int, str]:
        """Get selected_modules as a dictionary."""
        if not self.selected_modules:
            return {}

        try:
            parsed = json.loads(self.selected_modules)
            if isinstance(parsed, dict):
                result = {}
                for k, v in parsed.items():
                    try:
                        # Convert key to int and value to string safely
                        key = int(k)
                        value = str(v) if v is not None else ""
                        result[key] = value
                    except (ValueError, TypeError):
                        # Skip invalid key-value pairs
                        continue
                return result
            return {}
        except (json.JSONDecodeError, TypeError):
            # Return empty dict if JSON is malformed
            return {}

    @modules_dict.setter
    def modules_dict(self, value: dict[int, str]) -> None:
        """Set selected_modules from a dictionary."""
        self.selected_modules = json.dumps(value)

    @property
    def content_dict(self) -> dict[str, Any]:
        """Get extracted_content as a dictionary."""
        if not self.extracted_content:
            return {}

        try:
            result = json.loads(self.extracted_content)
            if isinstance(result, dict):
                return result
            return {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @content_dict.setter
    def content_dict(self, value: dict[str, Any]) -> None:
        """Set extracted_content from a dictionary."""
        self.extracted_content = json.dumps(value) if value else None


class QuizCreate(SQLModel):
    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[int, str]
    title: str = Field(min_length=1, max_length=255)
    question_count: int = Field(default=100, ge=1, le=200)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)


class UserPublic(SQLModel):
    name: str
    onboarding_completed: bool


class UserUpdateMe(SQLModel):
    name: str
    onboarding_completed: bool | None = Field(default=None)


class TokenPayload(SQLModel):
    sub: str | None = None


# Generic message
class Message(SQLModel):
    message: str


# Request/Response Models
class CanvasAuthRequest(SQLModel):
    code: str
    state: str | None = None
    canvas_base_url: str


class CanvasAuthResponse(SQLModel):
    access_token: str
    user: dict[str, Any]


class CanvasConfigResponse(SQLModel):
    authorization_url: str
    client_id: str
    redirect_uri: str
    scope: str


class CanvasCourse(SQLModel):
    id: int
    name: str


class CanvasModule(SQLModel):
    id: int
    name: str


class Question(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: uuid.UUID = Field(
        foreign_key="quiz.id", nullable=False, ondelete="CASCADE"
    )
    quiz: Quiz | None = Relationship(back_populates="questions")
    question_text: str = Field(min_length=1, max_length=2000)
    option_a: str = Field(min_length=1, max_length=500)
    option_b: str = Field(min_length=1, max_length=500)
    option_c: str = Field(min_length=1, max_length=500)
    option_d: str = Field(min_length=1, max_length=500)
    correct_answer: str = Field(regex=r"^[ABCD]$", description="Must be A, B, C, or D")
    is_approved: bool = Field(default=False, description="Whether question is approved")
    approved_at: datetime | None = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=True
        ),
        default=None, description="Timestamp when question was approved"
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
