from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException, status
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import User
from app.services.url_builder import CanvasURLBuilder

logger = get_logger("canvas_auth_service")


async def refresh_canvas_token(user: User, session: Session) -> None:
    """
    Refresh Canvas OAuth token for a user.

    Args:
        user: User with expired/expiring token
        session: Database session

    Raises:
        HTTPException: If refresh fails
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
        raise HTTPException(
            status_code=401,
            detail="No refresh token found. Please re-login via /auth/login/canvas",
        )

    try:
        refresh_token = crud.get_decrypted_refresh_token(user)
        if not refresh_token:
            logger.error(
                "token_refresh_failed_decryption_error",
                user_id=str(user.id),
                canvas_id=user.canvas_id,
            )
            raise HTTPException(
                status_code=401,
                detail="Refresh token decryption failed. Please re-login via /auth/login/canvas",
            )

        # Initialize URL builder
        base_url = str(settings.CANVAS_BASE_URL)
        if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
            base_url = str(settings.CANVAS_MOCK_URL)
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
                raise HTTPException(
                    status_code=400,
                    detail=f"Canvas token refresh error: {e.response.text}",
                )

        expires_at = None
        if "expires_in" in token_response:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_response["expires_in"]
            )

        crud.update_user_tokens(
            session=session,
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

    except Exception as e:
        logger.error(
            "token_refresh_failed",
            user_id=str(user.id),
            canvas_id=user.canvas_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token refresh failed: {str(e)}",
        )
