"""
Pydantic schemas for authentication module.
"""

from datetime import datetime
from typing import Any, Optional

from sqlmodel import Field, SQLModel


# User schemas
class UserCreate(SQLModel):
    """Schema for creating a new user."""

    canvas_id: int = Field()
    name: str = Field()
    access_token: str = Field()
    refresh_token: str = Field()


class UserPublic(SQLModel):
    """Public user information schema."""

    name: str
    onboarding_completed: bool


class UserUpdateMe(SQLModel):
    """Schema for user self-update."""

    name: str
    onboarding_completed: Optional[bool] = Field(default=None)


# Token schemas
class TokenUpdate(SQLModel):
    """Schema for updating Canvas tokens."""

    access_token: str = Field(default=None)
    refresh_token: str = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)


class TokenPayload(SQLModel):
    """JWT token payload schema."""

    sub: Optional[str] = None


# Canvas OAuth schemas
class CanvasAuthRequest(SQLModel):
    """Schema for Canvas OAuth callback request."""

    code: str
    state: Optional[str] = None
    canvas_base_url: str


class CanvasAuthResponse(SQLModel):
    """Schema for Canvas OAuth response."""

    access_token: str
    user: dict[str, Any]
