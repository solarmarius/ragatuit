import uuid
from datetime import datetime, timedelta
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
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )
    access_token: str = Field(description="Canvas access token")
    refresh_token: str = Field(description="Canvas refresh token")
    # 1 hour expiration from Canvas
    expires_at: datetime | None = Field(
        default=datetime.now() + timedelta(seconds=3600)
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
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=True
        ),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )


class QuizCreate(SQLModel):
    canvas_course_id: int
    canvas_course_name: str
    selected_modules: list[dict[str, int]]


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
