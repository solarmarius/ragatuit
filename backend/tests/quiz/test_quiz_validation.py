"""Quiz validation tests with behavior-focused assertions."""

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from sqlmodel import Session

from tests.conftest import create_user_in_session


def test_validate_quiz_ownership_success(session: Session):
    """Test successful quiz ownership validation behavior."""
    from src.quiz.validators import verify_quiz_ownership

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Test behavior: successful ownership validation
    validated_quiz = verify_quiz_ownership(session, quiz.id, user.id)

    assert validated_quiz is not None
    assert validated_quiz.id == quiz.id
    assert validated_quiz.owner_id == user.id


def test_validate_quiz_ownership_not_owner(session: Session):
    """Test quiz ownership validation behavior when user is not owner."""
    from src.quiz.validators import verify_quiz_ownership

    owner = create_user_in_session(session, canvas_id=1)
    other_user = create_user_in_session(session, canvas_id=2)
    quiz = create_test_quiz(session, owner.id)

    # Test behavior: ownership validation fails for non-owner
    from src.exceptions import ResourceNotFoundError

    with pytest.raises(ResourceNotFoundError):
        verify_quiz_ownership(session, quiz.id, other_user.id)


def test_validate_quiz_ownership_not_found(session: Session):
    """Test quiz ownership validation behavior when quiz doesn't exist."""
    from src.quiz.validators import verify_quiz_ownership

    user = create_user_in_session(session)
    non_existent_id = uuid.uuid4()

    # Test behavior: validation fails for non-existent quiz
    from src.exceptions import ResourceNotFoundError

    with pytest.raises(ResourceNotFoundError):
        verify_quiz_ownership(session, non_existent_id, user.id)


def test_quiz_ready_for_extraction_validation():
    """Test quiz extraction readiness validation behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_ready_for_extraction

    # Test behavior: valid statuses for extraction
    quiz_created = create_mock_quiz(status=QuizStatus.CREATED)
    quiz_failed = create_mock_quiz(status=QuizStatus.FAILED)

    assert is_quiz_ready_for_extraction(quiz_created) is True
    assert is_quiz_ready_for_extraction(quiz_failed) is True

    # Test behavior: invalid statuses for extraction
    quiz_extracting = create_mock_quiz(status=QuizStatus.EXTRACTING_CONTENT)
    quiz_generating = create_mock_quiz(status=QuizStatus.GENERATING_QUESTIONS)
    quiz_published = create_mock_quiz(status=QuizStatus.PUBLISHED)

    assert is_quiz_ready_for_extraction(quiz_extracting) is False
    assert is_quiz_ready_for_extraction(quiz_generating) is False
    assert is_quiz_ready_for_extraction(quiz_published) is False


def test_quiz_ready_for_generation_validation():
    """Test quiz generation readiness validation behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_ready_for_generation

    # Test behavior: valid statuses for generation
    quiz_extracting = create_mock_quiz(status=QuizStatus.EXTRACTING_CONTENT)
    quiz_failed = create_mock_quiz(status=QuizStatus.FAILED)
    quiz_partial = create_mock_quiz(status=QuizStatus.READY_FOR_REVIEW_PARTIAL)

    assert is_quiz_ready_for_generation(quiz_extracting) is True
    assert is_quiz_ready_for_generation(quiz_failed) is True
    assert is_quiz_ready_for_generation(quiz_partial) is True

    # Test behavior: invalid statuses for generation
    quiz_created = create_mock_quiz(status=QuizStatus.CREATED)
    quiz_published = create_mock_quiz(status=QuizStatus.PUBLISHED)

    assert is_quiz_ready_for_generation(quiz_created) is False
    assert is_quiz_ready_for_generation(quiz_published) is False


def test_quiz_ready_for_export_validation():
    """Test quiz export readiness validation behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_ready_for_export

    # Test behavior: valid statuses for export
    quiz_ready = create_mock_quiz(status=QuizStatus.READY_FOR_REVIEW)
    quiz_partial = create_mock_quiz(status=QuizStatus.READY_FOR_REVIEW_PARTIAL)

    assert is_quiz_ready_for_export(quiz_ready) is True
    assert is_quiz_ready_for_export(quiz_partial) is True

    # Test behavior: export retry from failed state with specific failure reason
    quiz_failed_export = create_mock_quiz(
        status=QuizStatus.FAILED, failure_reason="canvas_export_error"
    )
    assert is_quiz_ready_for_export(quiz_failed_export) is True

    # Test behavior: invalid statuses for export
    quiz_created = create_mock_quiz(status=QuizStatus.CREATED)
    quiz_extracting = create_mock_quiz(status=QuizStatus.EXTRACTING_CONTENT)
    quiz_failed_content = create_mock_quiz(
        status=QuizStatus.FAILED, failure_reason="content_extraction_error"
    )

    assert is_quiz_ready_for_export(quiz_created) is False
    assert is_quiz_ready_for_export(quiz_extracting) is False
    assert is_quiz_ready_for_export(quiz_failed_content) is False


def test_quiz_processing_state_validation():
    """Test quiz processing state validation behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_processing

    # Test behavior: processing states
    quiz_extracting = create_mock_quiz(status=QuizStatus.EXTRACTING_CONTENT)
    quiz_generating = create_mock_quiz(status=QuizStatus.GENERATING_QUESTIONS)
    quiz_exporting = create_mock_quiz(status=QuizStatus.EXPORTING_TO_CANVAS)

    assert is_quiz_processing(quiz_extracting) is True
    assert is_quiz_processing(quiz_generating) is True
    assert is_quiz_processing(quiz_exporting) is True

    # Test behavior: non-processing states
    quiz_created = create_mock_quiz(status=QuizStatus.CREATED)
    quiz_ready = create_mock_quiz(status=QuizStatus.READY_FOR_REVIEW)
    quiz_published = create_mock_quiz(status=QuizStatus.PUBLISHED)
    quiz_failed = create_mock_quiz(status=QuizStatus.FAILED)

    assert is_quiz_processing(quiz_created) is False
    assert is_quiz_processing(quiz_ready) is False
    assert is_quiz_processing(quiz_published) is False
    assert is_quiz_processing(quiz_failed) is False


def test_quiz_completion_state_validation():
    """Test quiz completion state validation behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_complete

    # Test behavior: complete states
    quiz_ready = create_mock_quiz(status=QuizStatus.READY_FOR_REVIEW)
    quiz_published = create_mock_quiz(status=QuizStatus.PUBLISHED)

    assert is_quiz_complete(quiz_ready) is True
    assert is_quiz_complete(quiz_published) is True

    # Test behavior: incomplete states
    quiz_created = create_mock_quiz(status=QuizStatus.CREATED)
    quiz_extracting = create_mock_quiz(status=QuizStatus.EXTRACTING_CONTENT)
    quiz_generating = create_mock_quiz(status=QuizStatus.GENERATING_QUESTIONS)
    quiz_failed = create_mock_quiz(status=QuizStatus.FAILED)

    assert is_quiz_complete(quiz_created) is False
    assert is_quiz_complete(quiz_extracting) is False
    assert is_quiz_complete(quiz_generating) is False
    assert is_quiz_complete(quiz_failed) is False


def test_quiz_retry_eligibility_validation():
    """Test quiz retry eligibility validation behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_ready_for_retry

    # Test behavior: retry eligible
    quiz_failed = create_mock_quiz(status=QuizStatus.FAILED)
    assert is_quiz_ready_for_retry(quiz_failed) is True

    # Test behavior: retry not eligible
    quiz_created = create_mock_quiz(status=QuizStatus.CREATED)
    quiz_extracting = create_mock_quiz(status=QuizStatus.EXTRACTING_CONTENT)
    quiz_published = create_mock_quiz(status=QuizStatus.PUBLISHED)

    assert is_quiz_ready_for_retry(quiz_created) is False
    assert is_quiz_ready_for_retry(quiz_extracting) is False
    assert is_quiz_ready_for_retry(quiz_published) is False


def test_quiz_processing_phase_description():
    """Test quiz processing phase description behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import get_quiz_processing_phase

    # Test behavior: phase descriptions match status
    quiz_created = create_mock_quiz(status=QuizStatus.CREATED)
    quiz_extracting = create_mock_quiz(status=QuizStatus.EXTRACTING_CONTENT)
    quiz_generating = create_mock_quiz(status=QuizStatus.GENERATING_QUESTIONS)
    quiz_ready = create_mock_quiz(status=QuizStatus.READY_FOR_REVIEW)
    quiz_exporting = create_mock_quiz(status=QuizStatus.EXPORTING_TO_CANVAS)
    quiz_published = create_mock_quiz(status=QuizStatus.PUBLISHED)
    quiz_failed = create_mock_quiz(status=QuizStatus.FAILED)

    assert get_quiz_processing_phase(quiz_created) == "Ready to start"
    assert (
        get_quiz_processing_phase(quiz_extracting) == "Extracting content from modules"
    )
    assert get_quiz_processing_phase(quiz_generating) == "Generating questions with AI"
    assert get_quiz_processing_phase(quiz_ready) == "Ready for question review"
    assert get_quiz_processing_phase(quiz_exporting) == "Exporting to Canvas"
    assert get_quiz_processing_phase(quiz_published) == "Published to Canvas"
    assert get_quiz_processing_phase(quiz_failed) == "Generation failed"


def test_quiz_validation_for_content_extraction_workflow(session: Session):
    """Test complete content extraction validation workflow."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_quiz_for_content_extraction

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Test behavior: successful validation workflow
    validated_quiz = validate_quiz_for_content_extraction(session, quiz.id, user.id)

    assert validated_quiz is not None
    assert validated_quiz.id == quiz.id
    assert validated_quiz.owner_id == user.id
    assert validated_quiz.status == QuizStatus.CREATED


def test_quiz_validation_for_content_extraction_wrong_status(session: Session):
    """Test content extraction validation with wrong status."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_quiz_for_content_extraction

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to already published (can't extract content)
    quiz.status = QuizStatus.PUBLISHED
    session.add(quiz)
    session.commit()

    # Test behavior: validation fails with wrong status
    with pytest.raises(ValueError, match="Content extraction is already in progress"):
        validate_quiz_for_content_extraction(session, quiz.id, user.id)


def test_quiz_validation_for_question_generation_workflow(session: Session):
    """Test complete question generation validation workflow."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_quiz_for_question_generation

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to have extracted content
    quiz.status = QuizStatus.EXTRACTING_CONTENT
    quiz.extracted_content = {"456": [{"content": "test", "word_count": 100}]}
    session.add(quiz)
    session.commit()

    # Test behavior: successful validation workflow
    validated_quiz = validate_quiz_for_question_generation(session, quiz.id, user.id)

    assert validated_quiz is not None
    assert validated_quiz.id == quiz.id
    assert validated_quiz.extracted_content is not None


def test_quiz_validation_for_question_generation_no_content(session: Session):
    """Test question generation validation without extracted content."""
    from src.quiz.validators import validate_quiz_for_question_generation

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)
    # Quiz in created state (no content)

    # Test behavior: validation fails without content
    with pytest.raises(ValueError, match="Content extraction must be completed"):
        validate_quiz_for_question_generation(session, quiz.id, user.id)


def test_quiz_validation_for_export_workflow(session: Session):
    """Test complete export validation workflow."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_quiz_for_export

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to ready for review
    quiz.status = QuizStatus.READY_FOR_REVIEW
    session.add(quiz)
    session.commit()

    # Test behavior: successful validation workflow
    validated_quiz = validate_quiz_for_export(session, quiz.id, user.id)

    assert validated_quiz is not None
    assert validated_quiz.id == quiz.id
    assert validated_quiz.status == QuizStatus.READY_FOR_REVIEW


def test_quiz_validation_for_export_already_published(session: Session):
    """Test export validation with already published quiz."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_quiz_for_export

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to already published
    quiz.status = QuizStatus.PUBLISHED
    quiz.canvas_quiz_id = "quiz_123"
    session.add(quiz)
    session.commit()

    # Test behavior: validation fails for already published quiz
    with pytest.raises(ValueError, match="Quiz has already been exported to Canvas"):
        validate_quiz_for_export(session, quiz.id, user.id)


def test_quiz_validation_for_export_in_progress(session: Session):
    """Test export validation with export already in progress."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_quiz_for_export

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to exporting
    quiz.status = QuizStatus.EXPORTING_TO_CANVAS
    session.add(quiz)
    session.commit()

    # Test behavior: validation fails for export in progress
    with pytest.raises(ValueError, match="Quiz export is already in progress"):
        validate_quiz_for_export(session, quiz.id, user.id)


def test_validator_factory_functions():
    """Test validator factory function behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import (
        create_export_validator,
        create_extraction_validator,
        create_generation_validator,
    )

    # Test behavior: validator factories create working validators
    extraction_validator = create_extraction_validator()
    generation_validator = create_generation_validator()
    export_validator = create_export_validator()

    quiz_created = create_mock_quiz(status=QuizStatus.CREATED)
    quiz_extracting = create_mock_quiz(status=QuizStatus.EXTRACTING_CONTENT)
    quiz_ready = create_mock_quiz(status=QuizStatus.READY_FOR_REVIEW)

    assert extraction_validator(quiz_created) is True
    assert extraction_validator(quiz_extracting) is False

    assert generation_validator(quiz_extracting) is True
    assert generation_validator(quiz_created) is False

    assert export_validator(quiz_ready) is True
    assert export_validator(quiz_created) is False


# Helper functions for behavior-focused testing


def create_mock_quiz(status=None, failure_reason=None):
    """Create a mock quiz with specified status and failure reason."""
    from src.quiz.schemas import QuizStatus

    mock_quiz = Mock()
    mock_quiz.id = uuid.uuid4()
    mock_quiz.owner_id = uuid.uuid4()
    mock_quiz.status = status or QuizStatus.CREATED
    mock_quiz.failure_reason = failure_reason
    mock_quiz.canvas_quiz_id = None
    mock_quiz.extracted_content = None
    mock_quiz.last_status_update = datetime.now(timezone.utc)

    return mock_quiz


def create_test_quiz(session: Session, owner_id: uuid.UUID, title: str = "Test Quiz"):
    """Helper to create a test quiz for validation tests."""
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
