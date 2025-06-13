import pytest
from fastapi.testclient import TestClient
from httpx import Response # For mocking httpx.Response
from jose import jwt
from urllib.parse import urlparse, parse_qs

from backend.config import Settings # To access settings like CANVAS_DOMAIN, etc.
from backend.api.models import User # To check user details
from backend.auth import settings as auth_settings # To access JWT_SECRET, ALGORITHM

# Use client fixture from conftest.py
# Use db_session fixture from conftest.py if direct DB manipulation is needed for setup/assertion

# Load settings once for use in tests
settings = Settings()

# --- Test /auth/login/canvas ---
def test_login_canvas_redirect(client: TestClient):
    response = client.get("/auth/login/canvas", follow_redirects=False) # Don't follow redirect

    assert response.status_code == 307 # FastAPI uses 307 for temporary redirect by default

    location_header = response.headers.get("location")
    assert location_header is not None

    parsed_url = urlparse(location_header)
    query_params = parse_qs(parsed_url.query)

    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == settings.CANVAS_DOMAIN
    assert parsed_url.path == "/login/oauth2/auth"
    assert query_params["client_id"] == [settings.CANVAS_CLIENT_ID]
    assert query_params["response_type"] == ["code"]
    assert query_params["redirect_uri"] == [settings.CANVAS_REDIRECT_URI]

# --- Test /auth/canvas/callback ---
@pytest.mark.asyncio # If using async httpx client mocks, test needs to be async
async def test_auth_canvas_callback_success(client: TestClient, mocker, db_session): # db_session for checking user
    # Mock httpx.AsyncClient.post for token exchange
    mock_canvas_token_data = {
        "access_token": "fake_canvas_access_token",
        "token_type": "Bearer",
        "user": {"id": "mock_canvas_user_123"},
        "expires_in": 3600
    }
    # Mock httpx.AsyncClient.get for user profile fetch
    mock_canvas_user_profile_data = {
        "id": "mock_canvas_user_123",
        "name": "Mock User",
        "primary_email": "mockuser@example.com",
        "sortable_name": "User, Mock"
    }

    # Use mocker provided by pytest-mock
    mock_async_client_instance = mocker.AsyncMock()

    # Configure different return values for post and get
    # The first call to client.post, then client.get
    mock_async_client_instance.post.return_value = Response(200, json=mock_canvas_token_data)
    mock_async_client_instance.get.return_value = Response(200, json=mock_canvas_user_profile_data)

    # Patch httpx.AsyncClient to return our mock instance
    mocker.patch("httpx.AsyncClient", return_value=mock_async_client_instance)

    # Call the callback endpoint
    response = client.get("/auth/canvas/callback?code=testcode", follow_redirects=False)

    assert response.status_code == 303 # SEE_OTHER for redirect after POST-like logic

    # Check user in database
    user = db_session.query(User).filter(User.canvas_id == "mock_canvas_user_123").first()
    assert user is not None
    assert user.email == "mockuser@example.com"
    assert user.name == "Mock User"

    # Check JWT in redirect URL
    redirect_location = response.headers.get("location")
    assert redirect_location is not None
    parsed_redirect_url = urlparse(redirect_location)
    query_params_redirect = parse_qs(parsed_redirect_url.query)

    assert parsed_redirect_url.path == "/auth/callback" # Frontend callback path
    assert "token" in query_params_redirect

    jwt_token = query_params_redirect["token"][0]
    payload = jwt.decode(jwt_token, auth_settings.JWT_SECRET, algorithms=[auth_settings.ALGORITHM])
    assert payload["user_id"] == user.id # Important: check if internal user_id is in token

@pytest.mark.asyncio
async def test_auth_canvas_callback_token_exchange_fails(client: TestClient, mocker):
    mock_async_client_instance = mocker.AsyncMock()
    mock_async_client_instance.post.return_value = Response(400, json={"error": "invalid_grant"})
    mocker.patch("httpx.AsyncClient", return_value=mock_async_client_instance)

    response = client.get("/auth/canvas/callback?code=badcode", follow_redirects=False)

    # Expecting an HTTPException from our endpoint, which TestClient converts to a response
    assert response.status_code == 502 # BAD_GATEWAY, as per main.py logic
    assert "Failed to exchange code for token" in response.json()["detail"]

@pytest.mark.asyncio
async def test_auth_canvas_callback_profile_fetch_fails(client: TestClient, mocker):
    mock_canvas_token_data = {"access_token": "fake_canvas_access_token", "user": {"id": "123"}}

    mock_async_client_instance = mocker.AsyncMock()
    mock_async_client_instance.post.return_value = Response(200, json=mock_canvas_token_data)
    mock_async_client_instance.get.return_value = Response(500, json={"error": "canvas_internal_error"})
    mocker.patch("httpx.AsyncClient", return_value=mock_async_client_instance)

    response = client.get("/auth/canvas/callback?code=goodcode", follow_redirects=False)

    assert response.status_code == 502 # BAD_GATEWAY
    assert "Failed to fetch user info from Canvas" in response.json()["detail"]


# --- Test /users/me (Protected Endpoint) ---
def test_users_me_no_token(client: TestClient):
    response = client.get("/users/me")
    assert response.status_code == 401 # From OAuth2PasswordBearer / verify_token
    assert "Not authenticated" in response.json()["detail"] # Default detail for OAuth2PasswordBearer

def test_users_me_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer invalidtoken"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 401 # From verify_token due to JWTError
    assert "Could not validate credentials" in response.json()["detail"]

def test_users_me_valid_token(client: TestClient, db_session: Session):
    # 1. Create a user and a token for them
    test_user_data = {"canvas_id": "userme1", "email": "userme1@example.com", "name": "User Me One"}
    user = User(**test_user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.id is not None

    # Use the actual create_access_token from auth module
    from backend.auth import create_access_token
    token_payload = {"user_id": user.id}
    valid_token = create_access_token(data=token_payload)

    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.get("/users/me", headers=headers)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == user.id
    assert response_data["email"] == user.email
    assert response_data["canvas_id"] == user.canvas_id
    assert response_data["name"] == user.name
    # Check that sensitive fields (if any added to model later) are not returned by default
    # (response_model=User in main.py helps with this)
    assert "created_at" in response_data # These are fine
    assert "updated_at" in response_data

def test_users_me_token_for_nonexistent_user(client: TestClient, db_session: Session):
    # User ID that doesn't exist in the DB
    non_existent_user_id = 99999

    from backend.auth import create_access_token
    token_payload = {"user_id": non_existent_user_id}
    token_for_ghost = create_access_token(data=token_payload)

    headers = {"Authorization": f"Bearer {token_for_ghost}"}
    response = client.get("/users/me", headers=headers)

    assert response.status_code == 404 # From get_current_user
    assert "User not found" in response.json()["detail"]
