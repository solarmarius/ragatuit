from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlmodel import Session

from src.auth.models import User
from src.auth.service import (
    clear_user_tokens,
    get_decrypted_access_token,
    get_decrypted_refresh_token,
    update_user_tokens,
)
from src.config import get_logger, settings
from src.exceptions import AuthenticationError, ExternalServiceError
from src.retry import retry_on_failure

ALGORITHM = "HS256"
logger = get_logger("canvas_security")


# Note: create_access_token has been moved to app.auth.utils


@retry_on_failure(max_attempts=2, initial_delay=1.0)
async def refresh_canvas_token(user: User, session: Session) -> None:
    """
    Refresh Canvas OAuth token for a user.

    Args:
        user: User with expired/expiring token
        session: Database session

    Raises:
        AuthenticationError: If refresh token is missing or invalid
        ExternalServiceError: If Canvas API call fails
        ConfigurationError: If Canvas configuration is invalid
    """
    logger.info(
        "canvas_token_refresh_initiated",
        user_id=str(user.id),
        canvas_id=user.canvas_id,
    )

    if not user.refresh_token:
        logger.warning(
            "token_refresh_failed_no_refresh_token",
            user_id=str(user.id),
            canvas_id=user.canvas_id,
        )
        raise AuthenticationError(
            "No refresh token found. Please re-login via /auth/login/canvas"
        )

    try:
        refresh_token = get_decrypted_refresh_token(user)
        if not refresh_token:
            logger.error(
                "token_refresh_failed_decryption_error",
                user_id=str(user.id),
                canvas_id=user.canvas_id,
            )
            raise AuthenticationError(
                "Refresh token decryption failed. Please re-login via /auth/login/canvas"
            )

        # Initialize URL builder
        base_url = str(settings.CANVAS_BASE_URL)
        if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
            base_url = str(settings.CANVAS_MOCK_URL)
        from src.canvas.url_builder import CanvasURLBuilder

        url_builder = CanvasURLBuilder(base_url, settings.CANVAS_API_VERSION)

        token_url = url_builder.oauth_token_url()
        token_data = {
            "grant_type": "refresh_token",
            "client_id": settings.CANVAS_CLIENT_ID,
            "client_secret": settings.CANVAS_CLIENT_SECRET,
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=token_data)
                response.raise_for_status()
                token_response = response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise AuthenticationError(
                        "Invalid refresh token. Please re-login via /auth/login/canvas"
                    )
                else:
                    raise ExternalServiceError(
                        "canvas",
                        f"Token refresh failed: {e.response.text}",
                        e.response.status_code,
                    )

        expires_at = None
        if "expires_in" in token_response:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_response["expires_in"]
            )

        update_user_tokens(
            session,
            user=user,
            access_token=token_response["access_token"],
            expires_at=expires_at,
        )

        logger.info(
            "token_refresh_completed_successfully",
            user_id=str(user.id),
            canvas_id=user.canvas_id,
            expires_at=expires_at.isoformat() if expires_at else None,
        )

    except Exception:
        # Let the error handler decorator handle unexpected exceptions
        raise


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
                    clear_user_tokens(session, user)
                    raise HTTPException(
                        status_code=401,
                        detail="Canvas session expired, Please re-login.",
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Canvas temporarily unavailable. Please try again.",
                    )

    return get_decrypted_access_token(user)
