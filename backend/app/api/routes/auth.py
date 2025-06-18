import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.security import create_access_token
from app.models import UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login/canvas")
async def login_canvas():
    """Generate Canvas OAuth2 authorization URL and redirect"""
    # TODO: store state in session/cache for validation!
    try:
        state = secrets.token_urlsafe(32)

        parsed_url = urlparse(str(settings.CANVAS_BASE_URL))
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid Canvas base URL")

        canvas_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        auth_params = {
            "client_id": settings.CANVAS_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.CANVAS_REDIRECT_URI,
            "state": state,
        }

        auth_url = f"{canvas_base_url}/login/oauth2/auth?{urlencode(auth_params)}"
        return RedirectResponse(url=auth_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback/canvas")
async def auth_canvas(session: SessionDep, request: Request):
    try:
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        # ADD THESE DEBUG LINES
        print("=== Canvas Callback Debug ===")
        print(f"Received authorization code: {code}")
        print(f"Received state: {state}")

        if not code:
            raise HTTPException(
                status_code=400, detail="Authorization code not provided"
            )

        # Parse Canvas base URL the same way as in login endpoint
        parsed_url = urlparse(str(settings.CANVAS_BASE_URL))
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid Canvas base URL")
        canvas_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        print(f"Canvas base URL: {canvas_base_url}")

        token_data = {
            "grant_type": "authorization_code",
            "client_id": settings.CANVAS_CLIENT_ID,
            "client_secret": settings.CANVAS_CLIENT_SECRET,
            "redirect_uri": str(settings.CANVAS_REDIRECT_URI),
            "code": code,
        }

        print(f"Token request data: {token_data}")
        print(f"Token URL: {canvas_base_url}/login/oauth2/token")

        async with httpx.AsyncClient(follow_redirects=False) as client:
            try:
                response = await client.post(
                    "http://canvas-mock:8001/login/oauth2/token",
                    data=token_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                print(f"Response status: {response.status_code}")
                print(f"Response text: {response.text}")
                response.raise_for_status()
                token_response = response.json()

                print(f"Token response: {token_response}")
            except httpx.HTTPStatusError as e:
                print(
                    f"HTTP Status Error: {e.response.status_code} - {e.response.text}"
                )
                raise HTTPException(
                    status_code=400, detail=f"Canvas OAUTH error: {e.response.text}"
                )
            except httpx.RequestError as e:
                print(f"Request Error: {str(e)}")
                raise HTTPException(
                    status_code=503, detail=f"Failed to connect to Canvas: {str(e)}"
                )

        canvas_user_id = token_response["user"]["id"]
        canvas_user_name = token_response["user"]["name"]
        print("Now trying to find user")
        print(f"Session: {session}")
        user = crud.get_user_by_canvas_id(session=session, canvas_id=canvas_user_id)

        print(f"Found a user: {user}")

        if not user:
            # Create new user
            user_create = UserCreate(
                canvas_id=canvas_user_id,
                name=canvas_user_name,
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
            )
            user = crud.create_user(session, user_create)
        else:
            # Update existing user tokens
            user = crud.update_user_tokens(
                session=session,
                user=user,
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=token_response["expires_in"]),
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        )

        print("SUCCESS:", access_token)
        redirect_url = f"{settings.FRONTEND_HOST}/login/success?token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        error_message = f"Canvas authentication failed: {str(e)}"
        redirect_url = f"{settings.FRONTEND_HOST}/login?error={error_message}"
        return RedirectResponse(url=redirect_url)


@router.delete("/logout")
async def logout_canvas(current_user: CurrentUser, session: SessionDep):
    crud.clear_user_tokens(session, current_user)
    return {"Message": "Canvas account disconnected successfully"}


@router.post("/refresh")
async def refresh_canvas_token(current_user: CurrentUser, session: SessionDep):
    if not current_user.refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available.")
    try:
        refresh_token = crud.get_decrypted_refresh_token(current_user)
        if not refresh_token:
            raise HTTPException(
                status_code=400, detail="No valid refresh token available"
            )
        token_url = f"{settings.CANVAS_BASE_URL}/login/oauth2/token"

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
            user=current_user,
            access_token=token_response["access_token"],
            expires_at=expires_at,
        )

        return {"message": "Token refreshed successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token refresh failed: {str(e)}",
        )
