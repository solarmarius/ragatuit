"""Authentication module for Canvas OAuth and user management."""

from .dependencies import CurrentUser, get_current_user
from .models import User
from .router import router, users_router
from .schemas import (
    CanvasAuthRequest,
    CanvasAuthResponse,
    TokenPayload,
    UserCreate,
    UserPublic,
    UserUpdateMe,
)
from .utils import create_access_token

__all__ = [
    "router",
    "users_router",
    "User",
    "UserCreate",
    "UserPublic",
    "UserUpdateMe",
    "TokenPayload",
    "CanvasAuthRequest",
    "CanvasAuthResponse",
    "CurrentUser",
    "get_current_user",
    "create_access_token",
]
