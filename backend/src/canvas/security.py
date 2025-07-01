from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlmodel import Session

from src.auth.canvas_auth import refresh_canvas_token
from src.auth.models import User
from src.auth.service import AuthService

ALGORITHM = "HS256"


# Note: create_access_token has been moved to app.auth.utils


async def ensure_valid_canvas_token(session: Session, user: User) -> str:
    """
    Ensure Canvas token is valid, refresh if needed.
    Returns a valid Canvas access token.
    """
    # Check if token expires within 5 minutes
    if user.expires_at:
        expires_soon = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Ensure both datetimes are timezone-aware for comparison
        if user.expires_at.tzinfo is None:
            # If stored datetime is naive, assume it's UTC
            user_expires_at = user.expires_at.replace(tzinfo=timezone.utc)
        else:
            user_expires_at = user.expires_at

        if user_expires_at <= expires_soon:
            try:
                await refresh_canvas_token(user, session)
            except HTTPException as e:
                if e.status_code == 401:
                    # Invalid canvas token - clear and force re-login
                    auth_service = AuthService(session)
                    auth_service.clear_user_tokens(user)
                    raise HTTPException(
                        status_code=401,
                        detail="Canvas session expired, Please re-login.",
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Canvas temporarily unavailable. Please try again.",
                    )

    auth_service = AuthService(session)
    return auth_service.get_decrypted_access_token(user)
