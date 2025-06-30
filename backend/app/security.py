from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from jose import jwt
from sqlmodel import Session

from app import crud
from app.auth.models import User
from app.config import settings
from app.encryption import token_encryption
from app.services.canvas_auth import refresh_canvas_token

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
                    crud.clear_user_tokens(session, user)
                    raise HTTPException(
                        status_code=401,
                        detail="Canvas session expired, Please re-login.",
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Canvas temporarily unavailable. Please try again.",
                    )

    return crud.get_decrypted_access_token(user)
