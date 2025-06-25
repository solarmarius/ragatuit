import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Form, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from mock_bodys import spatial_filtering_body, what_is_an_image_body
from pydantic import BaseModel

app = FastAPI(title="Mock Canvas Server", version="1.0.0")

# Mock data storage
mock_users = {
    "12345": {
        "id": 12345,
        "name": "Marius Solaas",
        "email": "marius.solaas@example.com",
        "login_id": "jteacher",
        "avatar_url": "https://example.com/avatar.jpg",
    }
}

mock_courses = [
    {
        "id": 37823,
        "name": "FYS-2010 Image Analysis",
        "account_id": 27925,
        "uuid": "hfv2nToY5ae1MbmNWTfNhTpzVbwq9ENcT00yTEiK",
        "start_at": None,
        "grading_standard_id": None,
        "is_public": False,
        "created_at": "2025-03-06T16:18:18Z",
        "course_code": "FYS-2010",
        "default_view": "wiki",
        "root_account_id": 1,
        "enrollment_term_id": 3,
        "license": "private",
        "grade_passback_setting": None,
        "end_at": None,
        "public_syllabus": False,
        "public_syllabus_to_auth": True,
        "storage_quota_mb": 3145,
        "is_public_to_auth_users": True,
        "homeroom_course": False,
        "course_color": None,
        "friendly_name": None,
        "apply_assignment_group_weights": False,
        "calendar": {
            "ics": "https://uit.instructure.com/feeds/calendars/course_hfv2nToY5ae1MbmNWTfNhTpzVbwq9ENcT00yTEiK.ics"
        },
        "time_zone": "Europe/Copenhagen",
        "blueprint": False,
        "template": False,
        "sis_course_id": None,
        "integration_id": None,
        "enrollments": [
            {
                "type": "teacher",
                "role": "TeacherEnrollment",
                "role_id": 4,
                "user_id": 71202,
                "enrollment_state": "active",
                "limit_privileges_to_course_section": False,
            }
        ],
        "hide_final_grades": False,
        "workflow_state": "unpublished",
        "restrict_enrollments_to_course_dates": False,
    },
    {
        "id": 37824,
        "name": "ALI-1111 Episk diktning fra ca 1800 til i dag",
        "account_id": 27925,
        "uuid": "Z7bzNStMko53AmlPm6R7qYPbBlLUWkGobbpBqlJ3",
        "start_at": None,
        "grading_standard_id": None,
        "is_public": False,
        "created_at": "2025-03-06T16:18:29Z",
        "course_code": "ALI-1111",
        "default_view": "wiki",
        "root_account_id": 1,
        "enrollment_term_id": 3,
        "license": "private",
        "grade_passback_setting": None,
        "end_at": None,
        "public_syllabus": False,
        "public_syllabus_to_auth": True,
        "storage_quota_mb": 3145,
        "is_public_to_auth_users": True,
        "homeroom_course": False,
        "course_color": None,
        "friendly_name": None,
        "apply_assignment_group_weights": False,
        "calendar": {
            "ics": "https://uit.instructure.com/feeds/calendars/course_Z7bzNStMko53AmlPm6R7qYPbBlLUWkGobbpBqlJ3.ics"
        },
        "time_zone": "Europe/Copenhagen",
        "blueprint": False,
        "template": False,
        "sis_course_id": None,
        "integration_id": None,
        "enrollments": [
            {
                "type": "teacher",
                "role": "TeacherEnrollment",
                "role_id": 4,
                "user_id": 71202,
                "enrollment_state": "active",
                "limit_privileges_to_course_section": False,
            }
        ],
        "hide_final_grades": False,
        "workflow_state": "unpublished",
        "restrict_enrollments_to_course_dates": False,
    },
]

mock_modules = [
    {
        "id": 173467,
        "name": "Admin infomation",
        "position": 1,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": True,
        "items_count": 0,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173467/items",
    },
    {
        "id": 173574,
        "name": "Image Fundamentals",
        "position": 2,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": False,
        "items_count": 5,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173574/items",
    },
    {
        "id": 173468,
        "name": "Spatial Filtering",
        "position": 3,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": True,
        "items_count": 2,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173468/items",
    },
    {
        "id": 173469,
        "name": "Convolution",
        "position": 4,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": False,
        "items_count": 1,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173469/items",
    },
    {
        "id": 173579,
        "name": "Fourier Transforms",
        "position": 5,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": False,
        "items_count": 1,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173579/items",
    },
    {
        "id": 173577,
        "name": "Computational Tomography",
        "position": 6,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": True,
        "items_count": 3,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173577/items",
    },
]

mock_items = {
    173574: [
        {
            "id": 1188038,
            "title": "what-is-an-image",
            "position": 8,
            "indent": 0,
            "quiz_lti": False,
            "type": "Page",
            "module_id": 173690,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1188038",
            "page_url": "what-is-an-image",
            "publish_at": None,
            "url": "https://uit.instructure.com/api/v1/courses/37823/pages/what-is-an-image",
            "published": True,
            "unpublishable": True,
        },
        {
            "id": 1188039,
            "title": "Week8_color.pdf",
            "position": 9,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 173690,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1188039",
            "content_id": 3612012,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3612012",
            "published": True,
            "unpublishable": False,
        },
    ],
    173468: [
        {
            "id": 1188040,
            "title": "spatial-filtering",
            "position": 10,
            "indent": 0,
            "quiz_lti": False,
            "type": "Page",
            "module_id": 173690,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1188040",
            "page_url": "spatial-filtering",
            "publish_at": None,
            "url": "https://uit.instructure.com/api/v1/courses/37823/pages/spatial-filtering",
            "published": True,
            "unpublishable": True,
        }
    ],
}

mock_pages = {
    "what-is-an-image": {
        "title": "what-is-an-image",
        "created_at": "2025-06-25T07:35:02Z",
        "url": "what-is-an-image",
        "editing_roles": "teachers",
        "page_id": 423573,
        "last_edited_by": {
            "id": 71202,
            "anonymous_id": "1ixu",
            "display_name": "Marius Rungmanee Solaas",
            "avatar_image_url": "https://uit.instructure.com/images/thumbnails/1711458/KP9GqxzKd0VQzE400AHhImiJtv8fzGV1cR5gfYW2",
            "html_url": "https://uit.instructure.com/courses/37823/users/71202",
            "pronouns": None,
        },
        "published": True,
        "hide_from_students": False,
        "front_page": False,
        "html_url": "https://uit.instructure.com/courses/37823/pages/what-is-an-image",
        "todo_date": None,
        "publish_at": None,
        "updated_at": "2025-06-25T07:35:39Z",
        "locked_for_user": False,
        "body": what_is_an_image_body,
    },
    "spatial-filtering": {
        "title": "spatial-filtering",
        "created_at": "2025-06-25T07:40:43Z",
        "url": "spatial-filtering",
        "editing_roles": "teachers",
        "page_id": 423574,
        "last_edited_by": {
            "id": 71202,
            "anonymous_id": "1ixu",
            "display_name": "Marius Rungmanee Solaas",
            "avatar_image_url": "https://uit.instructure.com/images/thumbnails/1711458/KP9GqxzKd0VQzE400AHhImiJtv8fzGV1cR5gfYW2",
            "html_url": "https://uit.instructure.com/courses/37823/users/71202",
            "pronouns": None,
        },
        "published": True,
        "hide_from_students": False,
        "front_page": False,
        "html_url": "https://uit.instructure.com/courses/37823/pages/spatial-filtering",
        "todo_date": None,
        "publish_at": None,
        "updated_at": "2025-06-25T07:40:55Z",
        "locked_for_user": False,
        "body": spatial_filtering_body,
    },
}

mock_files = {
    3612012: {
        "id": 3612012,
        "folder_id": 708060,
        "display_name": "Week8_color.pdf",
        "filename": "Week8_color.pdf",
        "uuid": "mBC1UvEdpKW1icxT4SEcTnMza6Iqk9NqVeXmm0nz",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3612012/download?download_frd=1&verifier=mBC1UvEdpKW1icxT4SEcTnMza6Iqk9NqVeXmm0nz",
        "size": 4733671,
        "created_at": "2025-06-25T07:37:50Z",
        "updated_at": "2025-06-25T07:37:50Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-06-25T07:37:50Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3612012,%22type%22:%22canvadoc%22%7D&hmac=17da101766a54e3ced85255631181dba7ef5b02d",
        "crocodoc_session_url": None,
    }
}


# Store authorization codes and tokens
auth_codes = {}
access_tokens = {}
refresh_tokens = {}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: dict
    expires_in: Optional[int] = 3600


@app.get("/")
async def root():
    return {"message": "Mock Canvas LMS Server", "version": "1.0.0"}


# OAuth2 Authorization endpoint
@app.get("/login/oauth2/auth")
async def authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    state: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
):
    """Mock Canvas authorization endpoint"""

    # Validate basic OAuth2 parameters
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Invalid response_type")

    # Return a simple HTML page that simulates Canvas login
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mock Canvas - Authorize Application</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 500px; margin: 0 auto; }}
            .button {{ background: #008EE2; color: white; padding: 10px 20px; border: None; border-radius: 4px; cursor: pointer; text-decoration: None; display: inline-block; }}
            .button:hover {{ background: #0078c7; }}
            .deny-button {{ background: #d93025; color: white; padding: 10px 20px; border: None; border-radius: 4px; cursor: pointer; text-decoration: None; display: inline-block; margin-left: 10px; }}
            .info {{ background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Mock Canvas LMS</h1>
            <h2>Authorize Application</h2>

            <div class="info">
                <strong>Application Details:</strong><br>
                Client ID: {client_id}<br>
                Redirect URI: {redirect_uri}<br>
                Requested Scope: {scope or 'default'}<br>
                State: {state or 'None'}
            </div>

            <p>This application is requesting access to your Canvas account.</p>
            <p><strong>Mock User:</strong> Marius Solaas (mso270@uit.com)</p>

            <div>
                <a href="/login/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type={response_type}&scope={scope or ''}&state={state or ''}&action=authorize" class="button">Authorize</a>
                <a href="/login/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type={response_type}&scope={scope or ''}&state={state or ''}&action=deny" class="deny-button">Deny</a>
            </div>

            <p><small>This is a mock Canvas server for development purposes.</small></p>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# OAuth2 Authorization action handler
@app.get("/login/oauth2/authorize")
async def handle_authorization(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    action: str = Query(...),
    state: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
):
    """Handle the authorization decision (approve/deny)"""

    if action == "deny":
        # User denied authorization
        error_url = f"{redirect_uri}?error=access_denied&error_description=The+user+denied+the+request"
        if state:
            error_url += f"&state={state}"
        return RedirectResponse(url=error_url)

    elif action == "authorize":
        # User approved authorization - generate auth code and redirect
        auth_code = f"mock_auth_code_{uuid.uuid4().hex[:16]}"

        # Store the auth code with associated data
        auth_codes[auth_code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "user_id": "12345",  # Mock user ID
            "expires_at": datetime.now() + timedelta(minutes=10),
        }

        # Create the redirect URL with auth code
        redirect_url = f"{redirect_uri}?code={auth_code}"
        if state:
            redirect_url += f"&state={state}"

        return RedirectResponse(url=redirect_url)

    else:
        raise HTTPException(status_code=400, detail="Invalid action")


# OAuth2 Token endpoint
@app.post("/login/oauth2/token")
async def get_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    redirect_uri: str = Form(None),
    code: str = Form(None),
    refresh_token: str = Form(None),
):
    """Mock Canvas token exchange endpoint"""

    print(
        f"Token exchange request: grant_type={grant_type}, client_id={client_id}, code={code}, refresh_token={refresh_token}"
    )

    if grant_type == "authorization_code":
        # Original authorization code flow
        if not code or not redirect_uri:
            raise HTTPException(status_code=400, detail="Missing code or redirect_uri")

        # Validate authorization code
        if code not in auth_codes:
            print(f"Available auth codes: {list(auth_codes.keys())}")
            raise HTTPException(status_code=400, detail="Invalid authorization code")

        auth_data = auth_codes[code]

        # Check if code is expired
        if datetime.now() > auth_data["expires_at"]:
            raise HTTPException(status_code=400, detail="Authorization code expired")

        # Validate client_id matches
        if auth_data["client_id"] != client_id:
            raise HTTPException(status_code=400, detail="Invalid client_id")

        # Generate access token and refresh token
        access_token = f"mock_access_token_{uuid.uuid4().hex}"
        new_refresh_token = f"mock_refresh_token_{uuid.uuid4().hex}"
        user_id = auth_data["user_id"]

        # Store access token
        access_tokens[access_token] = {
            "user_id": user_id,
            "client_id": client_id,
            "scope": auth_data["scope"],
            "expires_at": datetime.now() + timedelta(hours=1),
            "refresh_token": new_refresh_token,
        }

        # Store refresh token
        refresh_tokens[new_refresh_token] = {
            "user_id": user_id,
            "client_id": client_id,
            "scope": auth_data["scope"],
            "expires_at": datetime.now()
            + timedelta(days=30),  # Refresh tokens last longer
        }

        # Clean up authorization code
        del auth_codes[code]

        print(f"Generated access token: {access_token}")
        print(f"Generated refresh token: {new_refresh_token}")

        return TokenResponse(
            access_token=access_token,
            user=mock_users[user_id],
            refresh_token=new_refresh_token,
            expires_in=3600,
        )

    elif grant_type == "refresh_token":
        # Refresh token flow
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Missing refresh_token")

        # Validate refresh token
        if refresh_token not in refresh_tokens:
            print(f"Available refresh tokens: {list(refresh_tokens.keys())}")
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        refresh_data = refresh_tokens[refresh_token]

        # Check if refresh token is expired
        if datetime.now() > refresh_data["expires_at"]:
            raise HTTPException(status_code=400, detail="Refresh token expired")

        # Validate client_id matches
        if refresh_data["client_id"] != client_id:
            raise HTTPException(status_code=400, detail="Invalid client_id")

        # Generate new access token and refresh token
        new_access_token = f"mock_access_token_{uuid.uuid4().hex}"
        new_refresh_token = f"mock_refresh_token_{uuid.uuid4().hex}"
        user_id = refresh_data["user_id"]

        # Store new access token
        access_tokens[new_access_token] = {
            "user_id": user_id,
            "client_id": client_id,
            "scope": refresh_data["scope"],
            "expires_at": datetime.now() + timedelta(hours=1),
            "refresh_token": new_refresh_token,
        }

        # Store new refresh token
        refresh_tokens[new_refresh_token] = {
            "user_id": user_id,
            "client_id": client_id,
            "scope": refresh_data["scope"],
            "expires_at": datetime.now() + timedelta(days=30),
        }

        # Clean up old refresh token
        del refresh_tokens[refresh_token]

        print(f"Refreshed access token: {new_access_token}")
        print(f"Generated new refresh token: {new_refresh_token}")

        return TokenResponse(
            access_token=new_access_token,
            user=mock_users[user_id],
            refresh_token=new_refresh_token,
            expires_in=3600,
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid grant_type")


# OAuth2 Token revocation endpoint
@app.delete("/login/oauth2/token")
async def revoke_token(
    authorization: str = Header(None),
    access_token: str = Form(None),
):
    """Mock Canvas token revocation endpoint"""

    token_to_revoke = None

    # Check if token is provided in Authorization header
    if authorization and authorization.startswith("Bearer "):
        token_to_revoke = authorization.replace("Bearer ", "")
    # Check if token is provided as form parameter
    elif access_token:
        token_to_revoke = access_token
    else:
        raise HTTPException(
            status_code=400,
            detail="Access token required in Authorization header or as access_token parameter",
        )

    print(f"Token revocation request for token: {token_to_revoke}")

    # Validate that the token exists
    if token_to_revoke not in access_tokens:
        print(f"Available tokens: {list(access_tokens.keys())}")
        raise HTTPException(status_code=401, detail="Invalid access token")

    token_data = access_tokens[token_to_revoke]

    # Remove the access token
    del access_tokens[token_to_revoke]

    # Also revoke the associated refresh token if it exists
    refresh_token_to_remove = token_data.get("refresh_token")
    if refresh_token_to_remove and refresh_token_to_remove in refresh_tokens:
        del refresh_tokens[refresh_token_to_remove]
        print(f"Also revoked associated refresh token: {refresh_token_to_remove}")

    print(f"Successfully revoked access token: {token_to_revoke}")

    # Return 200 OK with empty response body (Canvas behavior)
    return {}


# Helper function to validate access token
def validate_token(authorization: str) -> str:
    print(f"Validating token: {authorization}")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")

    if token not in access_tokens:
        print(f"Available tokens: {list(access_tokens.keys())}")
        raise HTTPException(status_code=401, detail="Invalid access token")

    token_data = access_tokens[token]

    if datetime.now() > token_data["expires_at"]:
        raise HTTPException(status_code=401, detail="Access token expired")

    return token_data["user_id"]


# Canvas API endpoints - Fixed to use proper HTTP headers
@app.get("/api/v1/users/self/profile")
async def get_user_profile(authorization: str = Header(None)):
    """Mock Canvas user profile endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    user_id = validate_token(authorization)

    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")

    return mock_users[user_id]


@app.get("/api/v1/courses")
async def get_courses(authorization: str = Header(None)):
    """Mock Canvas courses endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    # Return mock courses for the authenticated user
    return mock_courses


@app.get("/api/v1/courses/{course_id}/modules")
async def get_course_modules(course_id: int, authorization: str = Header(None)):
    """Mock Canvas course modules endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Only return modules for course ID 37823, otherwise return unauthorized
    if course_id != 37823:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course modules"
        )

    return mock_modules


@app.get("/api/v1/courses/{course_id}/modules/{module_id}/items")
async def get_module_items(
    course_id: int, module_id: int, authorization: str = Header(None)
):
    """Mock Canvas module items endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Only return items for course ID 37823, otherwise return unauthorized
    if course_id != 37823:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course module items"
        )

    # Return items for the specified module_id from the mock_items dictionary
    if module_id in mock_items:
        return mock_items[module_id]
    else:
        # If no items found for this module, return empty list (not an error)
        return []


@app.get("/api/v1/courses/{course_id}/pages/{page_url}")
async def get_page(course_id: int, page_url: str, authorization: str = Header(None)):
    """Mock Canvas page endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Only return pages for course ID 37823, otherwise return unauthorized
    if course_id != 37823:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course pages"
        )

    # Return items for the specified module_id from the mock_items dictionary
    if page_url in mock_pages:
        return mock_pages[page_url]
    else:
        raise HTTPException(status_code=404, detail="Page not found")


@app.get("/api/v1/courses/{course_id}/files/{file_id}")
async def get_file(course_id: int, file_id: int, authorization: str = Header(None)):
    """Mock Canvas file endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Only return files for course ID 37823, otherwise return unauthorized
    if course_id != 37823:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course files"
        )

    # Check if the requested file_id exists in mock_files
    if file_id in mock_files:
        return mock_files[file_id]
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/api/v1/users/{user_id}/profile")
async def get_user_by_id(user_id: str, authorization: str = Header(None)):
    """Mock Canvas user by ID endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")

    return mock_users[user_id]


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tokens": len(access_tokens),
        "pending_auth_codes": len(auth_codes),
    }


# Debug endpoint to see current state
@app.get("/debug")
async def debug_state():
    return {
        "auth_codes": list(auth_codes.keys()),
        "access_tokens": list(access_tokens.keys()),
        "refresh_tokens": list(refresh_tokens.keys()),
        "mock_users": list(mock_users.keys()),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
