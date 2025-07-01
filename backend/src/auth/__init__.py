"""Authentication module for Canvas OAuth and user management."""

from .dependencies import CurrentUser, get_auth_service, get_current_user
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
from .service import AuthService, refresh_canvas_token
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
    "AuthService",
    "CurrentUser",
    "get_current_user",
    "get_auth_service",
    "create_access_token",
    "refresh_canvas_token",
]
