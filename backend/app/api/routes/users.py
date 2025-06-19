from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.models import Message, UserPublic, UserUpdateMe

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user profile information.

    Returns the authenticated user's public profile data including their name
    and Canvas information. This endpoint provides user data for displaying
    in the frontend interface.

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Parameters:**
        current_user (CurrentUser): Authenticated user from JWT token validation

    **Returns:**
        UserPublic: User's public profile information (excludes sensitive data)

    **Response Model:**
        - name (str): User's display name from Canvas
        - Additional public fields as defined in UserPublic schema

    **Usage:**
        GET /api/v1/users/me
        Authorization: Bearer <jwt_token>

    **Example Response:**
        {
            "name": "John Doe"
        }

    **Security:**
    - Only returns public user information (no tokens or sensitive data)
    - Requires valid authentication to access
    - User can only access their own profile information

    **Frontend Integration:**
    Used by frontend to display user information in navigation, profile sections,
    and user settings pages.
    """
    return current_user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update current user's profile information.

    Allows authenticated users to modify their profile data such as display name.
    Only updates fields provided in the request body, leaving other fields unchanged.

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Parameters:**
        session (SessionDep): Database session for the update transaction
        user_in (UserUpdateMe): Updated user data (only provided fields are changed)
        current_user (CurrentUser): Authenticated user from JWT token validation

    **Request Body (UserUpdateMe):**
        - name (str, optional): New display name for the user

    **Returns:**
        UserPublic: Updated user profile with new information

    **Usage:**
        PATCH /api/v1/users/me
        Authorization: Bearer <jwt_token>
        Content-Type: application/json

        {
            "name": "New Display Name"
        }

    **Example Response:**
        {
            "name": "New Display Name"
        }

    **Behavior:**
    - Partial updates: Only provided fields are modified
    - Validation: Input validated against UserUpdateMe schema
    - Database: Changes are committed immediately
    - Response: Returns updated user information

    **Security:**
    - Users can only update their own profile
    - Sensitive fields (tokens, Canvas ID) cannot be modified
    - Input validation prevents malicious data

    **Error Handling:**
    - Validation errors return 422 with details
    - Authentication errors return 401/403
    - Database errors return 500
    """
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Permanently delete current user account and all associated data.

    **⚠️ DESTRUCTIVE OPERATION ⚠️**

    This endpoint permanently removes the user's account from the system,
    including all Canvas OAuth tokens and user data. This action cannot be undone.

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Parameters:**
        session (SessionDep): Database session for the deletion transaction
        current_user (CurrentUser): Authenticated user from JWT token validation

    **Returns:**
        Message: Confirmation message that the account was deleted

    **Usage:**
        DELETE /api/v1/users/me
        Authorization: Bearer <jwt_token>

    **Example Response:**
        {
            "message": "User deleted successfully"
        }

    **Data Removed:**
    - User account record
    - Encrypted Canvas OAuth tokens
    - User profile information
    - All associated user data

    **Side Effects:**
    - All JWT tokens for this user become invalid immediately
    - User must re-authenticate with Canvas to create a new account
    - Canvas connection is severed (tokens are deleted)
    - User loses access to all application features

    **Security:**
    - Users can only delete their own account
    - Requires active authentication (prevents accidental deletion)
    - Immediate token invalidation prevents further access

    **Frontend Integration:**
    - Should show confirmation dialog before calling this endpoint
    - Redirect to login page after successful deletion
    - Clear any stored authentication state

    **Recovery:**
    - No account recovery possible after deletion
    - User can create new account by authenticating with Canvas again
    - Previous data and settings will not be restored

    **Note:**
    This operation is final. Consider implementing account deactivation
    instead of deletion for better user experience.
    """
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")
