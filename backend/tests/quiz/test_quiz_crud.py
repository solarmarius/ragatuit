"""Quiz CRUD operations tests with behavior-focused assertions."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from tests.conftest import create_user_in_session
from tests.test_data import (
    DEFAULT_QUIZ_CONFIG,
    DEFAULT_SELECTED_MODULES,
    MIXED_QUESTION_TYPES_MODULES,
    get_unique_quiz_config,
    get_unique_user_data,
)


def test_create_quiz_success(session: Session):
    """Test successful quiz creation with behavior-focused assertions."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz

    user = create_user_in_session(session)

    # Use centralized quiz configuration
    quiz_config = get_unique_quiz_config()

    quiz_data = QuizCreate(
        **quiz_config,
        selected_modules={
            "456": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
            "789": ModuleSelection(
                name="Module 2",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=15,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
        },
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Behavior-focused assertions
    assert quiz.owner_id == user.id
    assert quiz.canvas_course_id == quiz_config["canvas_course_id"]
    assert quiz.canvas_course_name == quiz_config["canvas_course_name"]
    assert quiz.title == quiz_config["title"]

    # Test behavior: total question calculation
    assert quiz.question_count == 25  # 10 + 15 from modules

    # Test behavior: module management
    assert has_module(quiz, "456")
    assert has_module(quiz, "789")
    assert not has_module(quiz, "999")

    # Test behavior: question type configuration
    assert get_module_question_count(quiz, "456") == 10
    assert get_module_question_count(quiz, "789") == 15
    assert get_module_name(quiz, "456") == "Module 1"
    assert get_module_name(quiz, "789") == "Module 2"

    # LLM configuration from centralized config
    assert quiz.llm_model == quiz_config["llm_model"]
    assert quiz.llm_temperature == quiz_config["llm_temperature"]

    # Metadata
    assert quiz.updated_at is not None
    assert quiz.id is not None


def test_create_quiz_with_defaults(session: Session):
    """Test quiz creation with default values."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz

    user = create_user_in_session(session)

    # Use centralized configuration for defaults test
    quiz_config = DEFAULT_QUIZ_CONFIG.copy()
    quiz_config["title"] = "Default Quiz"

    quiz_data = QuizCreate(
        **quiz_config,
        selected_modules={
            "456": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Test default behavior
    assert quiz.question_count == 10
    assert quiz.llm_model == DEFAULT_QUIZ_CONFIG["llm_model"]  # Default
    assert quiz.llm_temperature == DEFAULT_QUIZ_CONFIG["llm_temperature"]  # Default


def test_create_quiz_with_multiple_question_types_per_module(session: Session):
    """Test behavior with multiple question types per module."""
    from src.question.types import QuestionDifficulty, QuestionType, QuizLanguage
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz

    user = create_user_in_session(session)

    # Use centralized mixed question types configuration
    quiz_config = get_unique_quiz_config()
    quiz_config["canvas_course_name"] = "Multi-Type Test Course"

    # Convert centralized mixed modules to schema format
    mixed_modules = {}
    for module_id, module_data in MIXED_QUESTION_TYPES_MODULES.items():
        batches = []
        for batch in module_data["question_batches"]:
            batches.append(
                QuestionBatch(
                    question_type=QuestionType[batch["question_type"].upper()],
                    count=batch["count"],
                    difficulty=QuestionDifficulty[batch["difficulty"].upper()],
                )
            )
        mixed_modules[module_id] = ModuleSelection(
            name=module_data["name"],
            question_batches=batches,
        )

    quiz_data = QuizCreate(
        **quiz_config,
        selected_modules=mixed_modules,
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Test behavior: complex question counting based on centralized data
    assert quiz.language == QuizLanguage.ENGLISH
    # MIXED_QUESTION_TYPES_MODULES has: 10 MC + 5 FIB + 3 TF = 18 total
    assert quiz.question_count == 18  # From centralized mixed module data

    # Test behavior: module question type diversity
    assert (
        get_module_question_count(quiz, "456") == 18
    )  # All questions from mixed module

    # Test behavior: question type validation
    assert has_question_type(quiz, "456", "multiple_choice")
    assert has_question_type(quiz, "456", "fill_in_blank")
    assert has_question_type(quiz, "456", "true_false")
    assert not has_question_type(quiz, "456", "matching")
    assert not has_question_type(quiz, "456", "categorization")


def test_create_quiz_with_manual_modules(session: Session):
    """Test quiz creation behavior with manual modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Manual Test Course",
        selected_modules={
            "manual_123": ModuleSelection(
                name="Manual Module",
                source_type="manual",
                content="Test manual content",
                word_count=50,
                content_type="text",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=5,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title="Manual Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Test behavior: manual module handling
    assert has_module(quiz, "manual_123")
    assert get_module_source_type(quiz, "manual_123") == "manual"
    assert get_module_content(quiz, "manual_123") == "Test manual content"
    assert get_module_word_count(quiz, "manual_123") == 50
    assert get_module_content_type(quiz, "manual_123") == "text"
    assert quiz.question_count == 5


def test_get_quiz_by_id_success(session: Session):
    """Test successful quiz retrieval."""
    from src.quiz.service import get_quiz_by_id

    # Create a quiz first
    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Test behavior: successful retrieval
    retrieved_quiz = get_quiz_by_id(session, quiz.id)

    assert retrieved_quiz is not None
    assert retrieved_quiz.id == quiz.id
    assert retrieved_quiz.owner_id == user.id


def test_get_quiz_by_id_not_found(session: Session):
    """Test quiz retrieval behavior when quiz doesn't exist."""
    from src.quiz.service import get_quiz_by_id

    non_existent_id = uuid.uuid4()

    # Test behavior: graceful handling of non-existent quiz
    retrieved_quiz = get_quiz_by_id(session, non_existent_id)

    assert retrieved_quiz is None


def test_get_quiz_by_id_soft_deleted(session: Session):
    """Test quiz retrieval behavior with soft-deleted quizzes."""
    from src.quiz.service import delete_quiz, get_quiz_by_id

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Soft delete the quiz
    success = delete_quiz(session, quiz.id, user.id)
    assert success is True

    # Test behavior: soft-deleted quiz not returned by default
    retrieved_quiz = get_quiz_by_id(session, quiz.id)
    assert retrieved_quiz is None

    # Test behavior: soft-deleted quiz returned when requested
    retrieved_quiz = get_quiz_by_id(session, quiz.id, include_deleted=True)
    assert retrieved_quiz is not None
    assert retrieved_quiz.id == quiz.id
    assert retrieved_quiz.deleted is True


def test_get_user_quizzes_success(session: Session):
    """Test successful user quiz retrieval."""
    from src.quiz.service import get_user_quizzes

    user = create_user_in_session(session)

    # Create multiple quizzes
    quiz1 = create_test_quiz(session, user.id, title="Quiz 1")
    quiz2 = create_test_quiz(session, user.id, title="Quiz 2")

    # Test behavior: user quiz listing
    user_quizzes = get_user_quizzes(session, user.id)

    assert len(user_quizzes) == 2
    quiz_ids = [q.id for q in user_quizzes]
    assert quiz1.id in quiz_ids
    assert quiz2.id in quiz_ids


def test_get_user_quizzes_empty(session: Session):
    """Test user quiz retrieval behavior when user has no quizzes."""
    from src.quiz.service import get_user_quizzes

    user = create_user_in_session(session)

    # Test behavior: empty quiz list
    user_quizzes = get_user_quizzes(session, user.id)

    assert len(user_quizzes) == 0
    assert user_quizzes == []


def test_get_user_quizzes_ordering(session: Session):
    """Test quiz ordering behavior (most recent first)."""
    from src.quiz.service import get_user_quizzes

    user = create_user_in_session(session)

    # Create quizzes
    quiz1 = create_test_quiz(session, user.id, title="First Quiz")
    quiz2 = create_test_quiz(session, user.id, title="Second Quiz")

    # Test behavior: quiz list contains both quizzes
    user_quizzes = get_user_quizzes(session, user.id)

    assert len(user_quizzes) == 2
    quiz_ids = [q.id for q in user_quizzes]
    assert quiz1.id in quiz_ids
    assert quiz2.id in quiz_ids

    # Test behavior: ordered by created_at descending
    assert all(
        user_quizzes[i].created_at >= user_quizzes[i + 1].created_at
        for i in range(len(user_quizzes) - 1)
    )


def test_delete_quiz_success(session: Session):
    """Test successful quiz deletion behavior."""
    from src.quiz.service import delete_quiz

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Test behavior: successful deletion
    success = delete_quiz(session, quiz.id, user.id)

    assert success is True

    # Test behavior: quiz is soft-deleted, not physically removed
    from src.quiz.service import get_quiz_by_id

    deleted_quiz = get_quiz_by_id(session, quiz.id, include_deleted=True)
    assert deleted_quiz is not None
    assert deleted_quiz.deleted is True
    assert deleted_quiz.deleted_at is not None


def test_delete_quiz_not_owner(session: Session):
    """Test quiz deletion behavior when user is not owner."""
    from src.quiz.service import delete_quiz

    owner = create_user_in_session(session, canvas_id=1)
    other_user = create_user_in_session(session, canvas_id=2)
    quiz = create_test_quiz(session, owner.id)

    # Test behavior: unauthorized deletion fails
    success = delete_quiz(session, quiz.id, other_user.id)

    assert success is False

    # Test behavior: quiz remains undeleted
    from src.quiz.service import get_quiz_by_id

    quiz_check = get_quiz_by_id(session, quiz.id)
    assert quiz_check is not None
    assert quiz_check.deleted is False


def test_delete_quiz_not_found(session: Session):
    """Test quiz deletion behavior when quiz doesn't exist."""
    from src.quiz.service import delete_quiz

    user = create_user_in_session(session)
    non_existent_id = uuid.uuid4()

    # Test behavior: graceful handling of non-existent quiz
    success = delete_quiz(session, non_existent_id, user.id)

    assert success is False


def test_delete_quiz_already_deleted(session: Session):
    """Test quiz deletion behavior when quiz is already soft-deleted."""
    from src.quiz.service import delete_quiz

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # First deletion
    success1 = delete_quiz(session, quiz.id, user.id)
    assert success1 is True

    # Test behavior: second deletion fails gracefully
    success2 = delete_quiz(session, quiz.id, user.id)
    assert success2 is False


# Helper functions for behavior-focused testing


def has_module(quiz, module_id: str) -> bool:
    """Check if quiz has a specific module."""
    return module_id in quiz.selected_modules


def get_module_name(quiz, module_id: str) -> str:
    """Get module name."""
    return quiz.selected_modules[module_id]["name"]


def get_module_question_count(quiz, module_id: str) -> int:
    """Get total question count for a module."""
    module = quiz.selected_modules[module_id]
    return sum(batch["count"] for batch in module["question_batches"])


def get_module_source_type(quiz, module_id: str) -> str:
    """Get module source type."""
    return quiz.selected_modules[module_id].get("source_type", "canvas")


def get_module_content(quiz, module_id: str) -> str:
    """Get module content (for manual modules)."""
    return quiz.selected_modules[module_id].get("content", "")


def get_module_word_count(quiz, module_id: str) -> int:
    """Get module word count (for manual modules)."""
    return quiz.selected_modules[module_id].get("word_count", 0)


def get_module_content_type(quiz, module_id: str) -> str:
    """Get module content type (for manual modules)."""
    return quiz.selected_modules[module_id].get("content_type", "text")


def has_question_type(quiz, module_id: str, question_type: str) -> bool:
    """Check if module has a specific question type."""
    module = quiz.selected_modules[module_id]
    return any(
        batch["question_type"] == question_type for batch in module["question_batches"]
    )


def create_test_quiz(session: Session, owner_id: uuid.UUID, title: str = "Test Quiz"):
    """Helper to create a test quiz."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz

    quiz_data = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={
            "456": ModuleSelection(
                name="Test Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title=title,
    )

    return create_quiz(session, quiz_data, owner_id)
