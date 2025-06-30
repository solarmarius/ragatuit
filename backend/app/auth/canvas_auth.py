from datetime import datetime, timedelta, timezone

import httpx
from sqlmodel import Session

from app.auth.models import User
from app.auth.service import AuthService
from app.config import settings
from app.exceptions import AuthenticationError, ExternalServiceError
from app.logging_config import get_logger
from app.retry import retry_on_failure

logger = get_logger("canvas_auth_service")


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
        auth_service = AuthService(session)
        refresh_token = auth_service.get_decrypted_refresh_token(user)
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
        from app.canvas.url_builder import CanvasURLBuilder

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

        auth_service.update_user_tokens(
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
