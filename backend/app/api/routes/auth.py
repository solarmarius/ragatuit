import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
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
async def login_canvas() -> RedirectResponse:
    """
    Initiate Canvas OAuth2 authentication flow.

    Generates a Canvas OAuth2 authorization URL with a secure state parameter
    and redirects the user to Canvas for authentication.

    **Flow:**
    1. Generates a secure random state parameter for CSRF protection
    2. Validates the Canvas base URL configuration
    3. Constructs OAuth2 authorization URL with required parameters
    4. Redirects user to Canvas login page

    **Returns:**
        RedirectResponse: 307 redirect to Canvas OAuth2 authorization endpoint

    **Raises:**
        HTTPException: 400 if Canvas base URL is invalid or malformed

    **Example:**
        GET /api/v1/auth/login/canvas
        -> Redirects to: https://canvas.example.com/login/oauth2/auth?client_id=...&state=...
    """
    # TODO: Store state in session/cache for CSRF validation
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
async def auth_canvas(session: SessionDep, request: Request) -> RedirectResponse:
    """
    Handle Canvas OAuth2 callback and complete authentication.

    Processes the OAuth2 authorization code returned by Canvas, exchanges it
    for access/refresh tokens, and creates or updates the user account.

    **Parameters:**
        session (SessionDep): Database session for user operations
        request (Request): HTTP request containing OAuth2 callback parameters

    **Query Parameters:**
        code (str): Authorization code from Canvas OAuth2 flow
        state (str): State parameter for CSRF protection (currently not validated)

    **Flow:**
    1. Extracts authorization code from callback URL
    2. Exchanges code for Canvas access/refresh tokens
    3. Retrieves Canvas user information
    4. Creates new user or updates existing user tokens
    5. Generates JWT session token for the application
    6. Redirects to frontend with success token

    **Returns:**
        RedirectResponse: Redirect to frontend login success page with JWT token

    **Raises:**
        HTTPException: 400 if authorization code missing or Canvas returns error
        HTTPException: 503 if unable to connect to Canvas

    **Example:**
        GET /api/v1/auth/callback/canvas?code=abc123&state=xyz789
        -> Redirects to: http://localhost:5173/login/success?token=jwt_token

    **Error Handling:**
        On any error, redirects to frontend login page with error message
    """
    try:
        code = request.query_params.get("code")
        # state = request.query_params.get("state")

        if not code:
            raise HTTPException(
                status_code=400, detail="Authorization code not provided"
            )

        # Parse Canvas base URL the same way as in login endpoint
        # parsed_url = urlparse(str(settings.CANVAS_BASE_URL))
        # if not parsed_url.scheme or not parsed_url.netloc:
        #     raise ValueError("Invalid Canvas base URL")
        # canvas_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        token_data = {
            "grant_type": "authorization_code",
            "client_id": settings.CANVAS_CLIENT_ID,
            "client_secret": settings.CANVAS_CLIENT_SECRET,
            "redirect_uri": str(settings.CANVAS_REDIRECT_URI),
            "code": code,
        }

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
                response.raise_for_status()
                token_response = response.json()

            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=400, detail=f"Canvas OAUTH error: {e.response.text}"
                )
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=503, detail=f"Failed to connect to Canvas: {str(e)}"
                )

        # Validate Canvas response has required fields
        if "access_token" not in token_response:
            raise HTTPException(
                status_code=400, detail="Canvas did not return access_token"
            )
        if "refresh_token" not in token_response:
            raise HTTPException(
                status_code=400, detail="Canvas did not return refresh_token"
            )
        if "user" not in token_response or "id" not in token_response["user"]:
            raise HTTPException(
                status_code=400, detail="Canvas did not return user information"
            )

        canvas_user_id = token_response["user"]["id"]
        canvas_user_name = token_response["user"]["name"]

        user = crud.get_user_by_canvas_id(session=session, canvas_id=canvas_user_id)

        if not user:
            # Create new user
            user_create = UserCreate(
                canvas_id=canvas_user_id,
                name=canvas_user_name,
                access_token=token_response["access_token"],
                refresh_token=token_response["refresh_token"],
            )
            user = crud.create_user(session, user_create)
        else:
            # Update existing user tokens
            user = crud.update_user_tokens(
                session=session,
                user=user,
                access_token=token_response["access_token"],
                refresh_token=token_response["refresh_token"],
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=token_response["expires_in"]),
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        )

        redirect_url = f"{settings.FRONTEND_HOST}/login/success?token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        error_message = f"Canvas authentication failed: {str(e)}"
        redirect_url = f"{settings.FRONTEND_HOST}/login?error={error_message}"
        return RedirectResponse(url=redirect_url)


@router.delete("/logout")
async def logout_canvas(
    current_user: CurrentUser, session: SessionDep
) -> dict[str, str]:
    """
    Logout user and revoke Canvas tokens.

    Safely logs out the authenticated user by revoking their Canvas access token
    and clearing all stored authentication data from the database.

    **Parameters:**
        current_user (CurrentUser): Authenticated user from JWT token
        session (SessionDep): Database session for token cleanup

    **Flow:**
    1. Retrieves and decrypts user's Canvas access token
    2. Attempts to revoke token on Canvas side (gracefully handles failures)
    3. Clears all user tokens from database
    4. Returns success confirmation

    **Returns:**
        dict: Success message confirming logout completion

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Error Handling:**
        - Canvas token revocation failures are logged but don't prevent logout
        - Network errors to Canvas are handled gracefully
        - Database token cleanup always proceeds regardless of Canvas API status

    **Example:**
        DELETE /api/v1/auth/logout
        Authorization: Bearer jwt_token
        -> {"message": "Canvas account disconnected successfully"}
    """
    # Get Canvas access token before clearing it
    try:
        canvas_access_token = crud.get_decrypted_access_token(current_user)

        # Revoke token on Canvas side first
        if canvas_access_token:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.delete(
                        "http://canvas-mock:8001/login/oauth2/token",
                        headers={"Authorization": f"Bearer {canvas_access_token}"},
                    )
                    # Canvas returns 200 on successful revocation
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    # Log error but don't fail logout if Canvas revocation fails
                    print(
                        f"Warning: Failed to revoke Canvas token: {e.response.status_code} - {e.response.text}"
                    )
                except httpx.RequestError as e:
                    # Log network error but don't fail logout
                    print(
                        f"Warning: Network error during Canvas token revocation: {str(e)}"
                    )

    except Exception as e:
        # If we can't get the token, still proceed with logout
        print(f"Warning: Could not retrieve Canvas token for revocation: {str(e)}")

    # Clear tokens from our database
    crud.clear_user_tokens(session, current_user)
    return {"message": "Canvas account disconnected successfully"}


@router.post("/refresh")
async def refresh_canvas_token(
    current_user: CurrentUser, session: SessionDep
) -> dict[str, str]:
    """
    Refresh Canvas access token using stored refresh token.

    Exchanges the user's stored Canvas refresh token for a new access token,
    ensuring continued access to Canvas APIs without requiring re-authentication.

    **Parameters:**
        current_user (CurrentUser): Authenticated user from JWT token
        session (SessionDep): Database session for token updates

    **Flow:**
    1. Validates user has a stored refresh token
    2. Decrypts the refresh token from database
    3. Calls Canvas token refresh endpoint
    4. Updates user's access token and expiration in database
    5. Returns success confirmation

    **Returns:**
        dict: Success message confirming token refresh

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 401 if no refresh token available or decryption fails
        HTTPException: 400 if Canvas token refresh fails or returns error

    **Example:**
        POST /api/v1/auth/refresh
        Authorization: Bearer jwt_token
        -> {"message": "Token refreshed successfully"}

    **Note:**
        This endpoint is automatically called by the token validation middleware
        when Canvas tokens are near expiration, but can also be called manually.
    """
    if not current_user.refresh_token:
        raise HTTPException(
            status_code=401,
            detail="No refresh token found. Please re-login via /auth/login/canvas",
        )
    try:
        refresh_token = crud.get_decrypted_refresh_token(current_user)
        if not refresh_token:
            raise HTTPException(
                status_code=401,
                detail="Refresh token decryption failed. Please re-login via /auth/login/canvas",
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
