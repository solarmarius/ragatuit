import logging
from http import HTTPStatus
from typing import Optional

import httpx
from app.core.config import Settings
from app.core.oauth import create_access_token, get_current_user
from app.db.database import engine, get_session
from app.models.user import User
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, SQLModel, select

# import jwt # No longer needed for placeholder JWT, using python-jose via auth.py


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQLModel.metadata.create_all(bind=engine)

settings = Settings()

app = FastAPI()
auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.get("/login/canvas")
async def login_canvas():
    """
    Redirects the user to the Canvas authorization URL.
    """
    authorization_url = (
        f"http://{settings.CANVAS_DOMAIN}/login/oauth2/auth"
        f"?client_id={settings.CANVAS_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={settings.CANVAS_REDIRECT_URI}"
    )
    return RedirectResponse(authorization_url)


@auth_router.get("/callback")
async def auth_canvas_callback(
    code: str,
    request: Request,  # state: Optional[str] = None, # If using state
    db: Session = Depends(get_session),
):
    """
    Handles the callback from Canvas after user authorization.
    Exchanges the authorization code for an access token, fetches user info,
    creates or updates the user in the database, and returns a JWT.
    """
    # Token Exchange
    token_url = f"http://host.docker.internal:9000/login/oauth2/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.CANVAS_CLIENT_ID,
        "client_secret": settings.CANVAS_CLIENT_SECRET,
        "redirect_uri": settings.CANVAS_REDIRECT_URI,
        "code": code,
    }
    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(token_url, data=payload)
            token_response.raise_for_status()  # Raise an exception for bad status codes
            token_data = token_response.json()
            logger.info(token_data)
            access_token = token_data.get("access_token")
            canvas_user_id_from_token = token_data.get("user", {}).get(
                "id"
            )  # Canvas often returns user id in token response

            if not access_token or not canvas_user_id_from_token:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Failed to retrieve access token or user ID from Canvas.",
                )

        except httpx.HTTPStatusError as e:
            # Log the error details from e.response.text
            raise HTTPException(
                status_code=HTTPStatus.BAD_GATEWAY,
                detail=f"Failed to exchange code for token with Canvas: {e.response.text}",
            )
        except Exception as e:  # Catch other potential errors like network issues
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=f"Error during token exchange: {str(e)}",
            )

        # Fetch User Info from Canvas
        # Note: Some Canvas instances might require "Bearer" prefix, some might not for user_id in token
        # For /api/v1/users/self/profile, Bearer token is standard.
        user_info_url = f"http://host.docker.internal:9000/api/v1/users/self"  # Using /users/self is more common
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            user_response = await client.get(user_info_url, headers=headers)
            user_response.raise_for_status()
            user_data = user_response.json()
        except httpx.HTTPStatusError as e:
            # Log the error details from e.response.text
            raise HTTPException(
                status_code=HTTPStatus.BAD_GATEWAY,
                detail=f"Failed to fetch user info from Canvas: {e.response.text}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=f"Error fetching user info: {str(e)}",
            )

    # User Handling
    canvas_id_str = str(
        user_data.get("id")
    )  # Ensure it's a string for consistency with model
    user_email = user_data.get("primary_email") or user_data.get(
        "email"
    )  # primary_email is common
    user_name = user_data.get("name") or user_data.get("sortable_name")

    if not canvas_id_str or not user_email:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Required user information (Canvas ID, email) not found in Canvas profile.",
        )

    statement = select(User).where(User.canvas_id == canvas_id_str)
    db_user = db.exec(statement).first()

    if db_user:
        # Update existing user if necessary
        db_user.email = user_email
        db_user.name = user_name
        # Potentially update access_token and refresh_token if you store them
        # db_user.access_token = access_token
        # db_user.refresh_token = token_data.get("refresh_token")
    else:
        # Create new user
        db_user = User(
            canvas_id=canvas_id_str,
            email=user_email,
            name=user_name,
            # access_token=access_token, # If storing
            # refresh_token=token_data.get("refresh_token") # If storing
        )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Generate actual JWT token
    # The payload for the token should be {"user_id": db_user.id}
    # to match what verify_token and TokenData expect.
    if db_user.id is None:
        # This should not happen if user is committed and refreshed
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="User ID is null after creation/update",
        )

    access_token_payload = {"user_id": db_user.id}
    jwt_token = create_access_token(data=access_token_payload)

    # Redirect user to frontend with the token in query parameter
    frontend_callback_url = f"http://localhost:5173/auth/callback?token={jwt_token}"
    return RedirectResponse(url=frontend_callback_url, status_code=HTTPStatus.SEE_OTHER)


app.include_router(auth_router)


# Protected endpoint example
@app.get(
    "/users/me", response_model=User
)  # response_model ensures only User fields are returned
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Fetch the current authenticated user.
    """
    return current_user


@app.get("/")
async def root():
    return {"message": "Hello World"}
