import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


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


class UserPublic(SQLModel):
    name: str


class UserUpdateMe(SQLModel):
    name: str


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
