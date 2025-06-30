"""
Database models for authentication module.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models import Quiz


class User(SQLModel, table=True):
    """User model representing authenticated Canvas users."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    canvas_id: int = Field(unique=True, index=True)
    name: Optional[str] = Field(default=None, max_length=255)
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
    access_token: str = Field(description="Canvas access token")
    refresh_token: str = Field(description="Canvas refresh token")
    # 1 hour expiration from Canvas
    expires_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1),
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    token_type: str = Field(default="Bearer")
    onboarding_completed: bool = Field(
        default=False, description="Whether user has completed onboarding"
    )
    quizzes: list["Quiz"] = Relationship(back_populates="owner", cascade_delete=True)
