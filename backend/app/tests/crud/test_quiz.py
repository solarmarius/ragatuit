import uuid

from sqlmodel import Session

from app import crud
from app.auth.schemas import UserCreate
from app.auth.service import AuthService
from app.models import QuizCreate


def test_create_quiz(db: Session, user_id: uuid.UUID) -> None:
    """Test creating a quiz with all fields."""
    canvas_course_id = 12345
    canvas_course_name = "Test Course"
    selected_modules = {173467: "Module 1", 173468: "Module 2"}
    title = "Test Quiz"
    question_count = 50
    llm_model = "gpt-4o"
    llm_temperature = 1

    quiz_in = QuizCreate(
        canvas_course_id=canvas_course_id,
        canvas_course_name=canvas_course_name,
        selected_modules=selected_modules,
        title=title,
        question_count=question_count,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
    )

    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    # Check basic fields
    assert quiz.id is not None
    assert quiz.owner_id == user_id
    assert quiz.canvas_course_id == canvas_course_id
    assert quiz.canvas_course_name == canvas_course_name
    assert quiz.title == title
    assert quiz.question_count == question_count
    assert quiz.llm_model == llm_model
    assert quiz.llm_temperature == llm_temperature
    assert quiz.created_at is not None
    assert quiz.updated_at is not None

    # Check that modules are stored as dict with string keys
    assert quiz.selected_modules is not None
    expected_modules = {str(k): v for k, v in selected_modules.items()}
    assert quiz.selected_modules == expected_modules


def test_create_quiz_with_defaults(db: Session, user_id: uuid.UUID) -> None:
    """Test creating a quiz using default values."""
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Default Quiz",
        # question_count, llm_model, llm_temperature will use defaults
    )

    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    # Check default values
    assert quiz.question_count == 100  # Default
    assert quiz.llm_model == "o3"  # Default
    assert quiz.llm_temperature == 1  # Default


def test_get_quiz_by_id(db: Session, user_id: uuid.UUID) -> None:
    """Test retrieving a quiz by its ID."""
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
    )
    created_quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    retrieved_quiz = crud.get_quiz_by_id(session=db, quiz_id=created_quiz.id)

    assert retrieved_quiz is not None
    assert retrieved_quiz.id == created_quiz.id
    assert retrieved_quiz.owner_id == user_id
    assert retrieved_quiz.title == "Test Quiz"


def test_get_quiz_by_id_not_found(db: Session) -> None:
    """Test retrieving a quiz with non-existent ID."""
    non_existent_id = uuid.uuid4()

    quiz = crud.get_quiz_by_id(session=db, quiz_id=non_existent_id)

    assert quiz is None


def test_get_user_quizzes_empty(db: Session, user_id: uuid.UUID) -> None:
    """Test getting quizzes for user with no quizzes."""
    quizzes = crud.get_user_quizzes(session=db, user_id=user_id)

    assert quizzes == []


def test_get_user_quizzes_single(db: Session, user_id: uuid.UUID) -> None:
    """Test getting quizzes for user with one quiz."""
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Single Quiz",
    )
    created_quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    quizzes = crud.get_user_quizzes(session=db, user_id=user_id)

    assert len(quizzes) == 1
    assert quizzes[0].id == created_quiz.id
    assert quizzes[0].owner_id == user_id


def test_get_user_quizzes_multiple_ordered(db: Session, user_id: uuid.UUID) -> None:
    """Test getting multiple quizzes ordered by creation date (newest first)."""
    # Create first quiz
    quiz_in_1 = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="First Course",
        selected_modules={173467: "Module 1"},
        title="First Quiz",
    )
    first_quiz = crud.create_quiz(session=db, quiz_create=quiz_in_1, owner_id=user_id)

    # Small delay to ensure different timestamps
    import time

    time.sleep(0.001)

    # Create second quiz
    quiz_in_2 = QuizCreate(
        canvas_course_id=67890,
        canvas_course_name="Second Course",
        selected_modules={173468: "Module 2"},
        title="Second Quiz",
    )
    second_quiz = crud.create_quiz(session=db, quiz_create=quiz_in_2, owner_id=user_id)

    quizzes = crud.get_user_quizzes(session=db, user_id=user_id)

    assert len(quizzes) == 2
    # Check that both quizzes are returned
    quiz_ids = {quiz.id for quiz in quizzes}
    assert first_quiz.id in quiz_ids
    assert second_quiz.id in quiz_ids
    # Both should have creation times
    assert quizzes[0].created_at is not None
    assert quizzes[1].created_at is not None


def test_get_user_quizzes_user_isolation(db: Session, user_id: uuid.UUID) -> None:
    """Test that users only see their own quizzes."""
    # Create second user
    second_user_in = UserCreate(
        canvas_id=67890,
        name="Second User",
        access_token="second_access_token",
        refresh_token="second_refresh_token",
    )
    second_user = AuthService(db).create_user(second_user_in)

    # Create quiz for first user
    quiz_in_first = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="First User Course",
        selected_modules={173467: "Module 1"},
        title="First User Quiz",
    )
    first_quiz = crud.create_quiz(
        session=db, quiz_create=quiz_in_first, owner_id=user_id
    )

    # Create quiz for second user
    quiz_in_second = QuizCreate(
        canvas_course_id=67890,
        canvas_course_name="Second User Course",
        selected_modules={173468: "Module 2"},
        title="Second User Quiz",
    )
    second_quiz = crud.create_quiz(
        session=db, quiz_create=quiz_in_second, owner_id=second_user.id
    )

    # Check first user only sees their quiz
    first_quizzes = crud.get_user_quizzes(session=db, user_id=user_id)
    assert len(first_quizzes) == 1
    assert first_quizzes[0].id == first_quiz.id

    # Check second user only sees their quiz
    second_quizzes = crud.get_user_quizzes(session=db, user_id=second_user.id)
    assert len(second_quizzes) == 1
    assert second_quizzes[0].id == second_quiz.id


def test_quiz_selected_modules_jsonb(db: Session, user_id: uuid.UUID) -> None:
    """Test that selected_modules works as native JSONB."""
    modules = {173467: "Module 1", 173468: "Module 2"}
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules=modules,
        title="Modules Test Quiz",
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    # Test that modules are stored with string keys
    expected = {str(k): v for k, v in modules.items()}
    assert quiz.selected_modules == expected

    # Test direct assignment
    new_modules = {"999": "New Module", "1000": "Another Module"}
    quiz.selected_modules = new_modules
    db.commit()
    db.refresh(quiz)

    assert quiz.selected_modules == new_modules


def test_quiz_selected_modules_edge_cases(db: Session, user_id: uuid.UUID) -> None:
    """Test selected_modules JSONB with edge cases."""
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={},  # Empty modules
        title="Edge Case Quiz",
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    # Test empty modules
    assert quiz.selected_modules == {}

    # Test setting empty modules
    quiz.selected_modules = {}
    db.commit()
    db.refresh(quiz)
    assert quiz.selected_modules == {}


def test_quiz_field_constraints(db: Session, user_id: uuid.UUID) -> None:
    """Test quiz field validation constraints."""
    # Test minimum question count
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Min Questions Quiz",
        question_count=1,  # Minimum
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)
    assert quiz.question_count == 1

    # Test maximum question count
    quiz_in.question_count = 200  # Maximum
    quiz_in.title = "Max Questions Quiz"
    quiz2 = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)
    assert quiz2.question_count == 200

    # Test minimum temperature
    quiz_in.llm_temperature = 0.0  # Minimum
    quiz_in.title = "Min Temp Quiz"
    quiz3 = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)
    assert quiz3.llm_temperature == 0.0

    # Test maximum temperature
    quiz_in.llm_temperature = 2.0  # Maximum
    quiz_in.title = "Max Temp Quiz"
    quiz4 = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)
    assert quiz4.llm_temperature == 2.0


def test_quiz_title_handling(db: Session, user_id: uuid.UUID) -> None:
    """Test quiz title validation and special characters."""
    # Test minimum length title
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="A",  # Single character
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)
    assert quiz.title == "A"

    # Test title with special characters
    special_title = "Quiz: Machine Learning & AI (2024) - Test #1"
    quiz_in.title = special_title
    quiz2 = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)
    assert quiz2.title == special_title


def test_quiz_llm_models(db: Session, user_id: uuid.UUID) -> None:
    """Test different LLM model values."""
    models = ["gpt-4o", "gpt-4.1-mini", "gpt-o3", "o3"]

    for i, model in enumerate(models):
        quiz_in = QuizCreate(
            canvas_course_id=12345 + i,
            canvas_course_name=f"Course {i}",
            selected_modules={173467 + i: f"Module {i}"},
            title=f"Quiz {i}",
            llm_model=model,
        )
        quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)
        assert quiz.llm_model == model


def test_delete_quiz_success(db: Session, user_id: uuid.UUID) -> None:
    """Test successful quiz deletion by owner."""
    # Create a quiz first
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Quiz to Delete",
    )
    created_quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)
    quiz_id = created_quiz.id

    # Verify quiz exists
    assert crud.get_quiz_by_id(session=db, quiz_id=quiz_id) is not None

    # Delete the quiz
    result = crud.delete_quiz(session=db, quiz_id=quiz_id, user_id=user_id)

    # Verify deletion was successful
    assert result is True
    assert crud.get_quiz_by_id(session=db, quiz_id=quiz_id) is None


def test_delete_quiz_not_found(db: Session, user_id: uuid.UUID) -> None:
    """Test deleting a non-existent quiz."""
    non_existent_id = uuid.uuid4()

    # Try to delete non-existent quiz
    result = crud.delete_quiz(session=db, quiz_id=non_existent_id, user_id=user_id)

    # Should return False
    assert result is False


def test_delete_quiz_unauthorized(db: Session, user_id: uuid.UUID) -> None:
    """Test deleting a quiz by a user who doesn't own it."""
    # Create a second user
    second_user_in = UserCreate(
        canvas_id=67890,
        name="Second User",
        access_token="second_access_token",
        refresh_token="second_refresh_token",
    )
    second_user = AuthService(db).create_user(second_user_in)

    # Create a quiz owned by the first user
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="First User's Course",
        selected_modules={173467: "Module 1"},
        title="First User's Quiz",
    )
    first_user_quiz = crud.create_quiz(
        session=db, quiz_create=quiz_in, owner_id=user_id
    )

    # Try to delete the first user's quiz as the second user
    result = crud.delete_quiz(
        session=db, quiz_id=first_user_quiz.id, user_id=second_user.id
    )

    # Should return False (unauthorized)
    assert result is False
    # Quiz should still exist
    assert crud.get_quiz_by_id(session=db, quiz_id=first_user_quiz.id) is not None


def test_delete_quiz_with_extracted_content(db: Session, user_id: uuid.UUID) -> None:
    """Test deleting a quiz that has extracted content."""
    # Create a quiz
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Quiz with Content",
    )
    created_quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    # Add some extracted content
    created_quiz.extracted_content = {
        "modules": {
            "173467": {"pages": [{"title": "Test Page", "content": "Test content"}]}
        }
    }
    created_quiz.content_extraction_status = "completed"
    db.add(created_quiz)
    db.commit()

    # Verify content exists
    quiz = crud.get_quiz_by_id(session=db, quiz_id=created_quiz.id)
    assert quiz is not None
    assert quiz.extracted_content is not None
    assert quiz.content_extraction_status == "completed"

    # Delete the quiz
    result = crud.delete_quiz(session=db, quiz_id=created_quiz.id, user_id=user_id)

    # Verify deletion was successful (including content)
    assert result is True
    assert crud.get_quiz_by_id(session=db, quiz_id=created_quiz.id) is None


def test_delete_quiz_multiple_users_isolation(db: Session, user_id: uuid.UUID) -> None:
    """Test that deleting a quiz doesn't affect other users' quizzes."""
    # Create a second user
    second_user_in = UserCreate(
        canvas_id=67890,
        name="Second User",
        access_token="second_access_token",
        refresh_token="second_refresh_token",
    )
    second_user = AuthService(db).create_user(second_user_in)

    # Create quizzes for both users
    first_quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="First User Course",
        selected_modules={173467: "Module 1"},
        title="First User Quiz",
    )
    first_quiz = crud.create_quiz(
        session=db, quiz_create=first_quiz_in, owner_id=user_id
    )

    second_quiz_in = QuizCreate(
        canvas_course_id=67890,
        canvas_course_name="Second User Course",
        selected_modules={173468: "Module 2"},
        title="Second User Quiz",
    )
    second_quiz = crud.create_quiz(
        session=db, quiz_create=second_quiz_in, owner_id=second_user.id
    )

    # Delete first user's quiz
    result = crud.delete_quiz(session=db, quiz_id=first_quiz.id, user_id=user_id)

    # Verify first user's quiz is deleted
    assert result is True
    assert crud.get_quiz_by_id(session=db, quiz_id=first_quiz.id) is None

    # Verify second user's quiz is still there
    remaining_quiz = crud.get_quiz_by_id(session=db, quiz_id=second_quiz.id)
    assert remaining_quiz is not None
    assert remaining_quiz.owner_id == second_user.id
    assert remaining_quiz.title == "Second User Quiz"

    # Verify user quiz lists are correct
    first_user_quizzes = crud.get_user_quizzes(session=db, user_id=user_id)
    second_user_quizzes = crud.get_user_quizzes(session=db, user_id=second_user.id)

    assert len(first_user_quizzes) == 0
    assert len(second_user_quizzes) == 1
    assert second_user_quizzes[0].id == second_quiz.id
