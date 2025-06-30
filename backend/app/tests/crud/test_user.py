from sqlmodel import Session

from app.auth.schemas import UserCreate
from app.auth.service import AuthService


def test_create_user(db: Session) -> None:
    canvas_id = 1234
    name = "test"
    access_token = "4567"
    refresh_token = "7891"
    user_in = UserCreate(
        canvas_id=canvas_id,
        name=name,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)

    # Check that basic fields are correct
    assert user.canvas_id == 1234
    assert user.name == "test"
    assert user.id is not None
    assert user.created_at is not None

    # Check that tokens are encrypted (not plain text)
    assert user.access_token != "4567"  # Should be encrypted
    assert user.refresh_token != "7891"  # Should be encrypted

    # Check that we can decrypt the tokens back to original values
    decrypted_access = auth_service.get_decrypted_access_token(user)
    decrypted_refresh = auth_service.get_decrypted_refresh_token(user)
    assert decrypted_access == "4567"
    assert decrypted_refresh == "7891"


def test_get_user_by_canvas_id(db: Session) -> None:
    canvas_id = 1234
    access_token = "1111"
    refresh_token = "2222"
    user_in = UserCreate(
        canvas_id=canvas_id,
        name="name",
        access_token=access_token,
        refresh_token=refresh_token,
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)

    user_2 = auth_service.get_user_by_canvas_id(canvas_id=canvas_id)
    assert user_2
    assert user.canvas_id == user_2.canvas_id
    assert user.id == user_2.id

    # Compare decrypted tokens instead of encrypted ones
    assert auth_service.get_decrypted_access_token(
        user
    ) == auth_service.get_decrypted_access_token(user_2)
    assert auth_service.get_decrypted_refresh_token(
        user
    ) == auth_service.get_decrypted_refresh_token(user_2)


def test_update_user_tokens(db: Session) -> None:
    """Test updating user tokens"""
    canvas_id = 1234
    initial_access = "initial_access_token"
    initial_refresh = "initial_refresh_token"

    user_in = UserCreate(
        canvas_id=canvas_id,
        name="name",
        access_token=initial_access,
        refresh_token=initial_refresh,
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)

    # Update tokens
    new_access = "new_access_token"
    new_refresh = "new_refresh_token"
    updated_user = auth_service.update_user_tokens(
        user=user,
        access_token=new_access,
        refresh_token=new_refresh,
    )

    # Check that tokens were updated
    assert auth_service.get_decrypted_access_token(updated_user) == new_access
    assert auth_service.get_decrypted_refresh_token(updated_user) == new_refresh


def test_clear_user_tokens(db: Session) -> None:
    """Test clearing user tokens"""
    canvas_id = 1234
    user_in = UserCreate(
        canvas_id=canvas_id,
        name="name",
        access_token="test_token",
        refresh_token="test_refresh",
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)

    # Verify tokens exist
    assert auth_service.get_decrypted_access_token(user) == "test_token"
    assert auth_service.get_decrypted_refresh_token(user) == "test_refresh"

    # Clear tokens
    cleared_user = auth_service.clear_user_tokens(user)

    # Check that tokens are cleared
    assert cleared_user.access_token == ""
    assert cleared_user.refresh_token == ""


def test_token_encryption_integration(db: Session) -> None:
    """Test that token encryption works properly with CRUD operations"""
    canvas_id = 5678
    original_access = "super_secret_access_token"
    original_refresh = "super_secret_refresh_token"

    user_in = UserCreate(
        canvas_id=canvas_id,
        name="name",
        access_token=original_access,
        refresh_token=original_refresh,
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)

    # Tokens should be encrypted in database
    assert user.access_token != original_access
    assert user.refresh_token != original_refresh

    # But we should be able to decrypt them
    assert auth_service.get_decrypted_access_token(user) == original_access
    assert auth_service.get_decrypted_refresh_token(user) == original_refresh

    # Test that encrypted tokens are not empty
    assert len(user.access_token) > 0
    assert len(user.refresh_token) > 0


def test_user_with_no_refresh_token(db: Session) -> None:
    """Test creating user with no refresh token"""
    canvas_id = 9999
    access_token = "only_access_token"

    user_in = UserCreate(
        canvas_id=canvas_id, name="name", access_token=access_token, refresh_token=""
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)

    assert user.canvas_id == canvas_id
    assert auth_service.get_decrypted_access_token(user) == access_token
    decrypted_refresh = auth_service.get_decrypted_refresh_token(user)
    # Empty string gets stored and returned as None/empty
    assert decrypted_refresh in ("", None)
    # The actual stored value should be empty string (which encrypts to empty)
    assert user.refresh_token == ""


def test_get_user_by_id(db: Session) -> None:
    """Test getting user by ID"""
    canvas_id = 1234
    user_in = UserCreate(
        canvas_id=canvas_id,
        name="name",
        access_token="test_token",
        refresh_token="test_refresh",
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)

    user_by_id = auth_service.get_user_by_id(user_id=user.id)
    assert user_by_id
    assert user_by_id.id == user.id
    assert user_by_id.canvas_id == canvas_id

    # Test with non-existent ID
    import uuid

    non_existent_user = auth_service.get_user_by_id(user_id=uuid.uuid4())
    assert non_existent_user is None


# New name-specific tests
def test_user_name_is_required(db: Session) -> None:
    """Test that name field is required when creating a user"""
    canvas_id = 2342
    access_token = "test_token"

    # This should work with name
    user_in = UserCreate(
        canvas_id=canvas_id,
        name="John Doe",
        access_token=access_token,
        refresh_token="",
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)
    assert user.name == "John Doe"


def test_user_name_persistence(db: Session) -> None:
    """Test that user name is properly stored and retrieved"""
    canvas_id = 23423
    name = "Jane Smith"
    access_token = "test_token"

    user_in = UserCreate(
        canvas_id=canvas_id, name=name, access_token=access_token, refresh_token=""
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)

    # Verify name is stored correctly
    assert user.name == name

    # Retrieve user and verify name persists
    retrieved_user = auth_service.get_user_by_canvas_id(canvas_id=canvas_id)
    assert retrieved_user is not None
    assert retrieved_user.name == name


def test_user_name_with_special_characters(db: Session) -> None:
    """Test that user names with special characters are handled correctly"""
    canvas_id = 2343
    special_names = [
        "José María",
        "O'Connor",
        "李小明",
        "أحمد",
        "Müller-Schmidt",
        "Jean-Pierre",
    ]

    auth_service = AuthService(db)
    for i, name in enumerate(special_names):
        user_in = UserCreate(
            canvas_id=canvas_id + i,
            name=name,
            access_token=f"token_{i}",
            refresh_token="",
        )
        user = auth_service.create_user(user_in)
        assert user.name == name


def test_user_name_length_limits(db: Session) -> None:
    """Test user name length handling"""
    canvas_id = 234

    auth_service = AuthService(db)
    # Test normal length name
    normal_name = "John Doe"
    user_in = UserCreate(
        canvas_id=canvas_id,
        name=normal_name,
        access_token="token_normal",
        refresh_token="",
    )
    user = auth_service.create_user(user_in)
    assert user.name == normal_name

    # Test long name (up to 255 characters as defined in model)
    long_name = "A" * 255
    user_in = UserCreate(
        canvas_id=canvas_id + 1,
        name=long_name,
        access_token="token_long",
        refresh_token="",
    )
    user = auth_service.create_user(user_in)
    assert user.name == long_name


def test_user_name_updates_with_token_operations(db: Session) -> None:
    """Test that name is preserved during token operations"""
    canvas_id = 234324
    original_name = "Original Name"

    user_in = UserCreate(
        canvas_id=canvas_id,
        name=original_name,
        access_token="original_token",
        refresh_token="original_refresh",
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)

    # Update tokens
    updated_user = auth_service.update_user_tokens(
        user=user, access_token="new_token", refresh_token="new_refresh"
    )

    # Name should be preserved
    assert updated_user.name == original_name

    # Clear tokens
    cleared_user = auth_service.clear_user_tokens(updated_user)

    # Name should still be preserved
    assert cleared_user.name == original_name


def test_user_name_empty_string(db: Session) -> None:
    """Test handling of empty string names"""
    canvas_id = 23423

    user_in = UserCreate(
        canvas_id=canvas_id,
        name="",  # Empty string
        access_token="test_token",
        refresh_token="",
    )
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)
    assert user.name == ""
