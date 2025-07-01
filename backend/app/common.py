"""Common schemas used across multiple modules."""

from sqlmodel import SQLModel


class Message(SQLModel):
    """Generic message response."""
    message: str
