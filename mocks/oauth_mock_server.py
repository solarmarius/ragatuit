from typing import Optional

from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

app = FastAPI()


@app.get("/login/oauth2/auth")
async def auth_endpoint(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str = None,
    state: str = None,
):
    """
    Simulates the Canvas authorization endpoint.
    Redirects to the redirect_uri with a mock authorization code.
    """
    # Generate a fake authorization code
    mock_code = "mock_auth_code"

    # Append code to the redirect_uri
    redirect_url = f"{redirect_uri}?code={mock_code}"
    if state:
        redirect_url += f"&state={state}"

    return RedirectResponse(url=redirect_url)


@app.post("/login/oauth2/token")
async def token_endpoint(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    refresh_token: str = Form(None),
):
    # Return a fake access token response regardless of input
    return JSONResponse(
        {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "user": {"id": 42, "name": "Jimi Hendrix"},
        }
    )


@app.get("/api/v1/users/self")
async def user_profile(authorization: Optional[str] = Header(None)):
    """
    Simulates the Canvas user profile endpoint.
    Requires Bearer token authentication.
    """
    # Check for Authorization header
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse Bearer token
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme. Expected Bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token (in real Canvas, this would verify the token)
    if not token or len(token) < 10:  # Simple validation for mock
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Return mock user info
    return JSONResponse(
        {
            "id": 123,
            "name": "Mock User",
            "primary_email": "mockuser@example.com",
            "email": "mockuser@example.com",
            "login_id": "mockuser",
            "avatar_url": "https://example.com/avatar.png",
            "sortable_name": "User, Mock",
        }
    )
