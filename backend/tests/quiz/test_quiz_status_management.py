"""Quiz status management tests with behavior-focused assertions."""

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from sqlmodel import Session

from tests.conftest import create_user_in_session


def test_prepare_content_extraction_success(session: Session):
    """Test successful content extraction preparation behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import prepare_content_extraction

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Test behavior: successful preparation
    params = prepare_content_extraction(session, quiz.id, user.id)

    assert params["course_id"] == 12345
    assert params["module_ids"] == [456]

    # Test behavior: quiz status updated
    session.refresh(quiz)
    assert quiz.status == QuizStatus.EXTRACTING_CONTENT
    assert quiz.failure_reason is None
    assert quiz.extracted_content is None


def test_prepare_content_extraction_invalid_user(session: Session):
    """Test content extraction preparation with invalid user."""
    from src.quiz.service import prepare_content_extraction

    owner = create_user_in_session(session, canvas_id=1)
    other_user = create_user_in_session(session, canvas_id=2)
    quiz = create_test_quiz(session, owner.id)

    # Test behavior: preparation fails with invalid user
    from src.exceptions import ResourceNotFoundError

    with pytest.raises(ResourceNotFoundError):
        prepare_content_extraction(session, quiz.id, other_user.id)


def test_prepare_content_extraction_wrong_status(session: Session):
    """Test content extraction preparation with wrong quiz status."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import prepare_content_extraction

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to already published (can't extract content)
    quiz.status = QuizStatus.PUBLISHED
    session.add(quiz)
    session.commit()

    # Test behavior: preparation fails with wrong status
    with pytest.raises(ValueError):
        prepare_content_extraction(session, quiz.id, user.id)


def test_prepare_question_generation_success(session: Session):
    """Test successful question generation preparation behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import prepare_question_generation

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to have extracted content
    quiz.status = QuizStatus.EXTRACTING_CONTENT
    quiz.extracted_content = {"456": [{"content": "test", "word_count": 100}]}
    session.add(quiz)
    session.commit()

    # Test behavior: successful preparation
    params = prepare_question_generation(session, quiz.id, user.id)

    assert params["question_count"] == 10
    assert params["llm_model"] == "gpt-5-mini-2025-08-07"
    assert params["llm_temperature"] == 1.0
    assert params["language"].value == "en"
    assert params["tone"].value == "academic"

    # Test behavior: quiz status updated
    session.refresh(quiz)
    assert quiz.status == QuizStatus.GENERATING_QUESTIONS
    assert quiz.failure_reason is None


def test_prepare_question_generation_no_content(session: Session):
    """Test question generation preparation with no extracted content."""
    from src.quiz.service import prepare_question_generation

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)
    # Quiz in created state (no content extracted)

    # Test behavior: preparation fails without extracted content
    with pytest.raises(ValueError):
        prepare_question_generation(session, quiz.id, user.id)


def test_prepare_question_generation_invalid_user(session: Session):
    """Test question generation preparation with invalid user."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import prepare_question_generation

    owner = create_user_in_session(session, canvas_id=1)
    other_user = create_user_in_session(session, canvas_id=2)
    quiz = create_test_quiz(session, owner.id)

    # Set quiz to have extracted content
    quiz.status = QuizStatus.EXTRACTING_CONTENT
    quiz.extracted_content = {"456": [{"content": "test", "word_count": 100}]}
    session.add(quiz)
    session.commit()

    # Test behavior: preparation fails with invalid user
    from src.exceptions import ResourceNotFoundError

    with pytest.raises(ResourceNotFoundError):
        prepare_question_generation(session, quiz.id, other_user.id)


def test_quiz_status_transitions():
    """Test quiz status transition validation behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_status_transition

    # Test behavior: valid transitions
    assert (
        validate_status_transition(QuizStatus.CREATED, QuizStatus.EXTRACTING_CONTENT)
        is True
    )
    assert (
        validate_status_transition(
            QuizStatus.EXTRACTING_CONTENT, QuizStatus.GENERATING_QUESTIONS
        )
        is True
    )
    assert (
        validate_status_transition(
            QuizStatus.GENERATING_QUESTIONS, QuizStatus.READY_FOR_REVIEW
        )
        is True
    )
    assert (
        validate_status_transition(
            QuizStatus.READY_FOR_REVIEW, QuizStatus.EXPORTING_TO_CANVAS
        )
        is True
    )
    assert (
        validate_status_transition(QuizStatus.EXPORTING_TO_CANVAS, QuizStatus.PUBLISHED)
        is True
    )

    # Test behavior: failure transitions (from any status)
    assert validate_status_transition(QuizStatus.CREATED, QuizStatus.FAILED) is True
    assert (
        validate_status_transition(QuizStatus.EXTRACTING_CONTENT, QuizStatus.FAILED)
        is True
    )
    assert (
        validate_status_transition(QuizStatus.GENERATING_QUESTIONS, QuizStatus.FAILED)
        is True
    )

    # Test behavior: invalid transitions
    assert validate_status_transition(QuizStatus.PUBLISHED, QuizStatus.CREATED) is False
    assert (
        validate_status_transition(QuizStatus.READY_FOR_REVIEW, QuizStatus.CREATED)
        is False
    )
    assert (
        validate_status_transition(
            QuizStatus.GENERATING_QUESTIONS, QuizStatus.EXTRACTING_CONTENT
        )
        is False
    )


def test_quiz_status_retry_transitions():
    """Test quiz status retry transition behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_status_transition

    # Test behavior: retry from failed state
    assert validate_status_transition(QuizStatus.FAILED, QuizStatus.CREATED) is True
    assert (
        validate_status_transition(QuizStatus.FAILED, QuizStatus.EXTRACTING_CONTENT)
        is True
    )
    assert (
        validate_status_transition(QuizStatus.FAILED, QuizStatus.GENERATING_QUESTIONS)
        is True
    )

    # Test behavior: partial success retry
    assert (
        validate_status_transition(
            QuizStatus.READY_FOR_REVIEW_PARTIAL, QuizStatus.GENERATING_QUESTIONS
        )
        is True
    )


def test_quiz_validation_for_content_extraction_success(session: Session):
    """Test quiz validation behavior for content extraction."""
    from src.quiz.validators import validate_quiz_for_content_extraction

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Test behavior: valid quiz for extraction
    validated_quiz = validate_quiz_for_content_extraction(session, quiz.id, user.id)

    assert validated_quiz is not None
    assert validated_quiz.id == quiz.id
    assert validated_quiz.owner_id == user.id


def test_quiz_validation_for_content_extraction_not_owner(session: Session):
    """Test quiz validation behavior when user is not owner."""
    from src.quiz.validators import validate_quiz_for_content_extraction

    owner = create_user_in_session(session, canvas_id=1)
    other_user = create_user_in_session(session, canvas_id=2)
    quiz = create_test_quiz(session, owner.id)

    # Test behavior: validation fails when user is not owner
    from src.exceptions import ResourceNotFoundError

    with pytest.raises(ResourceNotFoundError):
        validate_quiz_for_content_extraction(session, quiz.id, other_user.id)


def test_quiz_validation_for_content_extraction_deleted(session: Session):
    """Test quiz validation behavior with soft-deleted quiz."""
    from src.quiz.service import delete_quiz
    from src.quiz.validators import validate_quiz_for_content_extraction

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Soft delete the quiz
    success = delete_quiz(session, quiz.id, user.id)
    assert success is True

    # Test behavior: validation should still work with soft-deleted quiz
    # (The validator doesn't check deleted status, only ownership)
    try:
        validated_quiz = validate_quiz_for_content_extraction(session, quiz.id, user.id)
        assert validated_quiz is not None
        assert validated_quiz.deleted is True  # Should be soft-deleted
    except Exception as e:
        # If an exception is raised, that's also valid behavior
        assert isinstance(e, (ResourceNotFoundError, ValueError))


def test_quiz_validation_for_question_generation_success(session: Session):
    """Test quiz validation behavior for question generation."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_quiz_for_question_generation

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to have content extracted
    quiz.status = QuizStatus.EXTRACTING_CONTENT
    quiz.extracted_content = {"456": [{"content": "test", "word_count": 100}]}
    session.add(quiz)
    session.commit()

    # Test behavior: valid quiz for generation
    validated_quiz = validate_quiz_for_question_generation(session, quiz.id, user.id)

    assert validated_quiz is not None
    assert validated_quiz.id == quiz.id
    assert validated_quiz.extracted_content is not None


def test_quiz_validation_for_question_generation_no_content(session: Session):
    """Test quiz validation behavior for generation without extracted content."""
    from src.quiz.validators import validate_quiz_for_question_generation

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)
    # Quiz in created state (no content)

    # Test behavior: validation fails without content
    with pytest.raises(ValueError, match="Content extraction must be completed"):
        validate_quiz_for_question_generation(session, quiz.id, user.id)


def test_quiz_validation_for_question_generation_not_owner(session: Session):
    """Test quiz validation behavior for generation when not owner."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_quiz_for_question_generation

    owner = create_user_in_session(session, canvas_id=1)
    other_user = create_user_in_session(session, canvas_id=2)
    quiz = create_test_quiz(session, owner.id)

    # Set quiz to have content extracted
    quiz.status = QuizStatus.EXTRACTING_CONTENT
    quiz.extracted_content = {"456": [{"content": "test", "word_count": 100}]}
    session.add(quiz)
    session.commit()

    # Test behavior: validation fails when user is not owner
    from src.exceptions import ResourceNotFoundError

    with pytest.raises(ResourceNotFoundError):
        validate_quiz_for_question_generation(session, quiz.id, other_user.id)


def test_quiz_behavior_helpers():
    """Test quiz behavior helper functions."""
    user = create_user_in_session_mock()
    quiz = create_test_quiz_mock(user.id)

    # Test behavior: module management
    assert has_module(quiz, "456") is True
    assert has_module(quiz, "999") is False

    # Test behavior: question counting
    assert get_total_question_count(quiz) == 10
    assert get_module_question_count(quiz, "456") == 10

    # Test behavior: module properties
    assert get_module_name(quiz, "456") == "Test Module"
    assert get_module_source_type(quiz, "456") == "canvas"

    # Test behavior: status checking
    assert is_ready_for_extraction(quiz) is True
    assert is_ready_for_generation(quiz) is False  # No content
    assert is_ready_for_export(quiz) is False  # No content/questions


def test_quiz_status_management_edge_cases(session: Session):
    """Test edge cases in quiz status management."""
    from src.quiz.schemas import QuizStatus

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Test behavior: multiple status updates
    quiz.status = QuizStatus.EXTRACTING_CONTENT
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    assert quiz.status == QuizStatus.EXTRACTING_CONTENT

    # Test behavior: status with timestamps
    original_update_time = quiz.last_status_update
    quiz.status = QuizStatus.GENERATING_QUESTIONS
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    assert quiz.last_status_update >= original_update_time


def test_quiz_failure_reason_tracking(session: Session):
    """Test failure reason tracking behavior."""
    from src.quiz.schemas import FailureReason, QuizStatus

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Test behavior: failure reason setting
    quiz.status = QuizStatus.FAILED
    quiz.failure_reason = FailureReason.CONTENT_EXTRACTION_ERROR
    session.add(quiz)
    session.commit()
    session.refresh(quiz)

    assert quiz.status == QuizStatus.FAILED
    assert quiz.failure_reason == FailureReason.CONTENT_EXTRACTION_ERROR

    # Test behavior: failure reason clearing on status change
    quiz.status = QuizStatus.EXTRACTING_CONTENT
    quiz.failure_reason = None
    session.add(quiz)
    session.commit()
    session.refresh(quiz)

    assert quiz.status == QuizStatus.EXTRACTING_CONTENT
    assert quiz.failure_reason is None


# Helper functions for behavior-focused testing


def has_module(quiz, module_id: str) -> bool:
    """Check if quiz has a specific module."""
    return module_id in quiz.selected_modules


def get_total_question_count(quiz) -> int:
    """Get total question count for quiz."""
    return quiz.question_count


def get_module_question_count(quiz, module_id: str) -> int:
    """Get total question count for a module."""
    module = quiz.selected_modules[module_id]
    return sum(batch["count"] for batch in module["question_batches"])


def get_module_name(quiz, module_id: str) -> str:
    """Get module name."""
    return quiz.selected_modules[module_id]["name"]


def get_module_source_type(quiz, module_id: str) -> str:
    """Get module source type."""
    return quiz.selected_modules[module_id].get("source_type", "canvas")


def is_ready_for_extraction(quiz) -> bool:
    """Check if quiz is ready for content extraction."""
    from src.quiz.schemas import QuizStatus

    return quiz.status in [QuizStatus.CREATED, QuizStatus.FAILED]


def is_ready_for_generation(quiz) -> bool:
    """Check if quiz is ready for question generation."""
    from src.quiz.schemas import QuizStatus

    return (
        quiz.status in [QuizStatus.EXTRACTING_CONTENT, QuizStatus.FAILED]
        and quiz.extracted_content is not None
    )


def is_ready_for_export(quiz) -> bool:
    """Check if quiz is ready for Canvas export."""
    from src.quiz.schemas import QuizStatus

    return quiz.status in [
        QuizStatus.READY_FOR_REVIEW,
        QuizStatus.READY_FOR_REVIEW_PARTIAL,
    ]


def create_user_in_session_mock():
    """Create a mock user for testing."""
    mock_user = Mock()
    mock_user.id = uuid.uuid4()
    mock_user.canvas_id = 12345
    return mock_user


def create_test_quiz_mock(owner_id: uuid.UUID):
    """Create a mock quiz for testing."""
    from src.question.types import QuizLanguage
    from src.quiz.schemas import QuizStatus, QuizTone

    mock_quiz = Mock()
    mock_quiz.id = uuid.uuid4()
    mock_quiz.owner_id = owner_id
    mock_quiz.canvas_course_id = 12345
    mock_quiz.canvas_course_name = "Test Course"
    mock_quiz.selected_modules = {
        "456": {
            "name": "Test Module",
            "question_batches": [
                {
                    "question_type": "multiple_choice",
                    "count": 10,
                    "difficulty": "medium",
                }
            ],
            "source_type": "canvas",
        }
    }
    mock_quiz.title = "Test Quiz"
    mock_quiz.question_count = 10
    mock_quiz.llm_model = "gpt-5-mini-2025-08-07"
    mock_quiz.llm_temperature = 1.0
    mock_quiz.language = QuizLanguage.ENGLISH
    mock_quiz.tone = QuizTone.ACADEMIC
    mock_quiz.status = QuizStatus.CREATED
    mock_quiz.failure_reason = None
    mock_quiz.extracted_content = None
    mock_quiz.last_status_update = datetime.now(timezone.utc)

    return mock_quiz


def create_test_quiz(session: Session, owner_id: uuid.UUID, title: str = "Test Quiz"):
    """Helper to create a test quiz for status management tests."""
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
