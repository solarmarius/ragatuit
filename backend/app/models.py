import uuid
from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


# Properties to receive via API on creation (Canvas OAuth only)
class UserCreate(SQLModel):
    canvas_user_id: str = Field(description="Canvas user identifier")
    canvas_base_url: str = Field(description="Canvas instance base URL")


# Properties to receive via API
class TokenCreate(SQLModel):
    user_id: uuid.UUID = Field(description="User ID who owns this token")
    access_token: str = Field(description="Canvas access token (will be encrypted)")
    refresh_token: str | None = Field(
        default=None, description="Canvas refresh token (will be encrypted)"
    )
    token_type: str = Field(
        default="Bearer", description="Token type from Canvas OAuth2"
    )
    expires_at: datetime | None = Field(
        default=None, description="Token expiration timestamp"
    )
    scope: str | None = Field(default=None, description="Granted OAuth2 scopes")
    canvas_user_id: str = Field(description="Canvas user identifier")
    canvas_base_url: str = Field(description="Canvas instance base URL")


# Database model, database table inferred from class name
class User(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "canvas_user_id", "canvas_base_url", name="unique_canvas_user"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    canvas_user_id: str = Field(default=None, unique=True, index=True)
    canvas_base_url: str = Field(
        default=None, description="Primary Canvas instance URL"
    )
    canvas_tokens: list["CanvasToken"] = Relationship(back_populates="user")


class CanvasToken(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    access_token: str = Field(description="Encrypted Canvas access token")
    refresh_token: str | None = Field(
        default=None, description="Encrypted Canvas refresh token"
    )
    token_type: str = Field(
        default="Bearer", description="Token type from Canvas OAuth2"
    )
    expires_at: datetime | None = Field(
        default=None, description="Token expiration timestamp"
    )
    scope: str | None = Field(default=None, description="Granted OAuth2 scopes")
    canvas_user_id: str = Field(description="Canvas user identifier", index=True)
    canvas_base_url: str = Field(description="Canvas instance base URL")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user: User = Relationship(back_populates="canvas_tokens")


# Properties to return via API, id is always required
class UserPublic(SQLModel):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=255)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)
