import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError # To catch constraint violations

from backend.api.models import User

def test_create_user(db_session: Session):
    """Test creating a new user and saving to the database."""
    user_data = {
        "canvas_id": "test_canvas_id_1",
        "email": "test1@example.com",
        "name": "Test User One"
    }
    user = User(**user_data)

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.canvas_id == user_data["canvas_id"]
    assert user.email == user_data["email"]
    assert user.name == user_data["name"]
    assert user.created_at is not None
    assert user.updated_at is not None

def test_get_user(db_session: Session):
    """Test retrieving a user from the database."""
    user_data = {
        "canvas_id": "test_canvas_id_2",
        "email": "test2@example.com",
        "name": "Test User Two"
    }
    user_to_create = User(**user_data)
    db_session.add(user_to_create)
    db_session.commit()
    db_session.refresh(user_to_create)

    retrieved_user = db_session.get(User, user_to_create.id) # SQLModel's get by PK

    assert retrieved_user is not None
    assert retrieved_user.id == user_to_create.id
    assert retrieved_user.email == user_data["email"]

def test_user_canvas_id_unique_constraint(db_session: Session):
    """Test that canvas_id must be unique."""
    canvas_id = "unique_canvas_id_3"
    user1_data = {"canvas_id": canvas_id, "email": "user3_1@example.com", "name": "User3_1"}
    user1 = User(**user1_data)
    db_session.add(user1)
    db_session.commit()

    user2_data = {"canvas_id": canvas_id, "email": "user3_2@example.com", "name": "User3_2"}
    user2 = User(**user2_data)
    db_session.add(user2)

    with pytest.raises(IntegrityError): # SQLAlchemy raises IntegrityError for unique constraints
        db_session.commit()

def test_user_email_unique_constraint(db_session: Session):
    """Test that email must be unique."""
    db_session.rollback() # Ensure session is clean if previous test failed mid-commit

    email = "unique_email_4@example.com"
    user1_data = {"canvas_id": "canvas_id_4_1", "email": email, "name": "User4_1"}
    user1 = User(**user1_data)
    db_session.add(user1)
    db_session.commit()

    user2_data = {"canvas_id": "canvas_id_4_2", "email": email, "name": "User4_2"}
    user2 = User(**user2_data)
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        db_session.commit()

def test_user_nullable_fields(db_session: Session):
    """Test that nullable fields can be null, and non-nullable raise errors."""
    # Name is nullable
    user_with_null_name_data = {
        "canvas_id": "canvas_id_5",
        "email": "user5@example.com",
        "name": None
    }
    user = User(**user_with_null_name_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.name is None

    # canvas_id is not nullable
    with pytest.raises(ValueError): # Pydantic/SQLModel raises ValueError for missing required fields on model creation
         User(email="user6_fail@example.com", name="Test Fail")

    # email is not nullable
    with pytest.raises(ValueError):
         User(canvas_id="canvas_id_6_fail", name="Test Fail")

    # Note: SQLModel/Pydantic will raise ValueError before hitting DB if required fields are None.
    # The actual DB non-null constraint (NOT NULL) would also cause IntegrityError if somehow
    # a model with None for a required field made it to the commit stage, but SQLModel validates first.
    # For example, trying to set user.email = None after creation and then committing would hit DB error.
    # user.email = None
    # with pytest.raises(IntegrityError): # This would be DB level
    #     db_session.commit()

    # Let's test that setting a required field to None after creation and trying to commit fails
    user_for_none_test = User(canvas_id="cid_7", email="email7@example.com", name="Name7")
    db_session.add(user_for_none_test)
    db_session.commit()
    db_session.refresh(user_for_none_test)

    user_for_none_test.email = None # type: ignore
    # We use type: ignore as SQLModel model is typed and would show error for assigning None to non-Optional.
    # This tests the database constraint if model validation is bypassed or occurs post-creation.
    # However, SQLModel's design often catches this if you try to re-validate or on next DB interaction.
    # Forcing it through:
    with pytest.raises(IntegrityError): # This should be the database-level NOT NULL constraint
        db_session.flush() # Flush to send to DB before commit
        # Or, if flush() doesn't trigger it due to ORM state, commit() would.
        # db_session.commit() # This might also work depending on ORM behavior.
        # The exact error can depend on when SQLAlchemy/DB driver enforces the constraint.
        # Forcing a re-validation or direct update often shows the error more clearly.
        # For now, the ValueError on creation for missing fields is the primary SQLModel validation.
        # The actual DB constraint is a fallback. The IntegrityError for unique fields is a clear DB error.
        # Testing NOT NULL on existing objects is tricky as SQLModel might prevent it.
        # The ValueError on model instantiation is the most direct test for non-nullable fields in SQLModel.
        # Let's simplify and rely on SQLModel's validation during instantiation for non-nullable fields.
        pass # Keeping the ValueError tests above as the primary check for non-nullable


# To run these tests:
# Ensure you are in the `backend` directory.
# Run `poetry run pytest` or `PYTHONPATH=./src poetry run pytest` if Python can't find `backend` module.
# The conftest.py should handle PYTHONPATH issues for imports within tests if tests are run with pytest from root of `backend`
# Or, if `backend/src/backend` is a package, and tests are in `backend/tests`, pytest should find them.
# The `packages = [{include = "backend", from = "src"}]` in pyproject.toml helps pytest discover the package.
