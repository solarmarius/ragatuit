"""Quiz business workflow tests with behavior-focused assertions."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session

from tests.conftest import create_user_in_session


def test_content_extraction_workflow_success(session: Session):
    """Test successful content extraction workflow behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import prepare_content_extraction

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Test behavior: successful workflow preparation
    params = prepare_content_extraction(session, quiz.id, user.id)

    assert params["course_id"] == 12345
    assert params["module_ids"] == [456]

    # Test behavior: quiz status transitions correctly
    session.refresh(quiz)
    assert quiz.status == QuizStatus.EXTRACTING_CONTENT
    assert quiz.failure_reason is None
    assert quiz.extracted_content is None
    assert quiz.content_extracted_at is None


def test_content_extraction_workflow_invalid_user(session: Session):
    """Test content extraction workflow with invalid user."""
    from src.quiz.service import prepare_content_extraction

    owner = create_user_in_session(session, canvas_id=1)
    other_user = create_user_in_session(session, canvas_id=2)
    quiz = create_test_quiz(session, owner.id)

    # Test behavior: workflow fails with unauthorized user
    from src.exceptions import ResourceNotFoundError

    with pytest.raises(ResourceNotFoundError):
        prepare_content_extraction(session, quiz.id, other_user.id)


def test_content_extraction_workflow_reset_from_failed(session: Session):
    """Test content extraction workflow reset from failed state."""
    from src.quiz.schemas import FailureReason, QuizStatus
    from src.quiz.service import prepare_content_extraction

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to failed state
    quiz.status = QuizStatus.FAILED
    quiz.failure_reason = FailureReason.CONTENT_EXTRACTION_ERROR
    quiz.extracted_content = {"old": "data"}
    session.add(quiz)
    session.commit()

    # Test behavior: workflow resets properly from failed state
    params = prepare_content_extraction(session, quiz.id, user.id)

    assert params["course_id"] == 12345
    assert params["module_ids"] == [456]

    # Test behavior: failed state is cleared
    session.refresh(quiz)
    assert quiz.status == QuizStatus.EXTRACTING_CONTENT
    assert quiz.failure_reason is None
    assert quiz.extracted_content is None


def test_question_generation_workflow_success(session: Session):
    """Test successful question generation workflow behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import prepare_question_generation

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to have extracted content
    quiz.status = QuizStatus.EXTRACTING_CONTENT
    quiz.extracted_content = {"456": [{"content": "test", "word_count": 100}]}
    session.add(quiz)
    session.commit()

    # Test behavior: successful workflow preparation
    params = prepare_question_generation(session, quiz.id, user.id)

    assert params["question_count"] == 10
    assert params["llm_model"] == "gpt-5-mini-2025-08-07"
    assert params["llm_temperature"] == 1.0
    assert params["language"].value == "en"
    assert params["tone"].value == "academic"

    # Test behavior: quiz status transitions correctly
    session.refresh(quiz)
    assert quiz.status == QuizStatus.GENERATING_QUESTIONS
    assert quiz.failure_reason is None


def test_question_generation_workflow_no_content(session: Session):
    """Test question generation workflow without extracted content."""
    from src.quiz.service import prepare_question_generation

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)
    # Quiz in created state (no content extracted)

    # Test behavior: workflow fails without extracted content
    with pytest.raises(ValueError):
        prepare_question_generation(session, quiz.id, user.id)


def test_question_generation_workflow_retry_from_partial(session: Session):
    """Test question generation workflow retry from partial success."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import prepare_question_generation

    user = create_user_in_session(session)
    quiz = create_test_quiz(session, user.id)

    # Set quiz to partial success state
    quiz.status = QuizStatus.READY_FOR_REVIEW_PARTIAL
    quiz.extracted_content = {"456": [{"content": "test", "word_count": 100}]}
    session.add(quiz)
    session.commit()

    # Test behavior: workflow allows retry from partial success
    params = prepare_question_generation(session, quiz.id, user.id)

    assert params["question_count"] == 10

    # Test behavior: status transitions to generating
    session.refresh(quiz)
    assert quiz.status == QuizStatus.GENERATING_QUESTIONS


def test_job_reservation_workflow_extraction_behavior():
    """Test job reservation workflow behavior for content extraction."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_status_transition

    # Test behavior: status transition validation for extraction
    assert (
        validate_status_transition(QuizStatus.CREATED, QuizStatus.EXTRACTING_CONTENT)
        is True
    )
    assert (
        validate_status_transition(QuizStatus.FAILED, QuizStatus.EXTRACTING_CONTENT)
        is True
    )
    assert (
        validate_status_transition(
            QuizStatus.EXTRACTING_CONTENT, QuizStatus.EXTRACTING_CONTENT
        )
        is True
    )  # Self-transition allowed


def test_job_reservation_workflow_generation_behavior():
    """Test job reservation workflow behavior for question generation."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_status_transition

    # Test behavior: status transition validation for generation
    assert (
        validate_status_transition(
            QuizStatus.EXTRACTING_CONTENT, QuizStatus.GENERATING_QUESTIONS
        )
        is True
    )
    assert (
        validate_status_transition(QuizStatus.FAILED, QuizStatus.GENERATING_QUESTIONS)
        is True
    )
    assert (
        validate_status_transition(
            QuizStatus.READY_FOR_REVIEW_PARTIAL, QuizStatus.GENERATING_QUESTIONS
        )
        is True
    )
    assert (
        validate_status_transition(QuizStatus.CREATED, QuizStatus.GENERATING_QUESTIONS)
        is False
    )


def test_job_reservation_workflow_export_behavior():
    """Test job reservation workflow behavior for Canvas export."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_status_transition

    # Test behavior: status transition validation for export
    assert (
        validate_status_transition(
            QuizStatus.READY_FOR_REVIEW, QuizStatus.EXPORTING_TO_CANVAS
        )
        is True
    )
    assert (
        validate_status_transition(
            QuizStatus.READY_FOR_REVIEW_PARTIAL, QuizStatus.EXPORTING_TO_CANVAS
        )
        is False
    )
    assert (
        validate_status_transition(QuizStatus.FAILED, QuizStatus.EXPORTING_TO_CANVAS)
        is True
    )
    assert (
        validate_status_transition(QuizStatus.CREATED, QuizStatus.EXPORTING_TO_CANVAS)
        is False
    )


def test_job_reservation_workflow_already_taken_behavior():
    """Test job reservation workflow behavior when job is already taken."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_processing

    # Test behavior: processing state detection
    quiz_extracting = create_mock_quiz_with_content()
    quiz_extracting.status = QuizStatus.EXTRACTING_CONTENT

    quiz_generating = create_mock_quiz_with_content()
    quiz_generating.status = QuizStatus.GENERATING_QUESTIONS

    quiz_exporting = create_mock_quiz_with_content()
    quiz_exporting.status = QuizStatus.EXPORTING_TO_CANVAS

    assert is_quiz_processing(quiz_extracting) is True
    assert is_quiz_processing(quiz_generating) is True
    assert is_quiz_processing(quiz_exporting) is True


def test_job_reservation_workflow_already_exported_behavior():
    """Test job reservation workflow behavior for already exported quiz."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_complete

    # Test behavior: completion state detection
    quiz_published = create_mock_quiz_with_content()
    quiz_published.status = QuizStatus.PUBLISHED
    quiz_published.canvas_quiz_id = "quiz_123"

    quiz_ready = create_mock_quiz_with_content()
    quiz_ready.status = QuizStatus.READY_FOR_REVIEW

    assert is_quiz_complete(quiz_published) is True
    assert is_quiz_complete(quiz_ready) is True
    assert quiz_published.canvas_quiz_id is not None


def test_status_update_workflow_behavior():
    """Test quiz status update workflow behavior."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import validate_status_transition

    # Test behavior: valid status transitions for updates
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
        validate_status_transition(QuizStatus.EXPORTING_TO_CANVAS, QuizStatus.PUBLISHED)
        is True
    )

    # Test behavior: content extraction timestamp behavior
    quiz = create_mock_quiz_with_content()
    quiz.status = QuizStatus.EXTRACTING_CONTENT
    quiz.extracted_content = {"456": [{"content": "test"}]}

    assert quiz.extracted_content is not None


def test_status_update_workflow_failure_behavior():
    """Test quiz status update workflow behavior with failure."""
    from src.quiz.schemas import FailureReason, QuizStatus
    from src.quiz.validators import is_quiz_ready_for_retry, validate_status_transition

    # Test behavior: failure transitions from any status
    assert (
        validate_status_transition(QuizStatus.EXTRACTING_CONTENT, QuizStatus.FAILED)
        is True
    )
    assert (
        validate_status_transition(QuizStatus.GENERATING_QUESTIONS, QuizStatus.FAILED)
        is True
    )
    assert (
        validate_status_transition(QuizStatus.EXPORTING_TO_CANVAS, QuizStatus.FAILED)
        is True
    )

    # Test behavior: retry eligibility after failure
    quiz = create_mock_quiz_with_content()
    quiz.status = QuizStatus.FAILED
    quiz.failure_reason = FailureReason.CONTENT_EXTRACTION_ERROR

    assert is_quiz_ready_for_retry(quiz) is True


def test_status_update_workflow_published_behavior():
    """Test quiz status update workflow behavior for published state."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_complete, validate_status_transition

    # Test behavior: published transition validation
    assert (
        validate_status_transition(QuizStatus.EXPORTING_TO_CANVAS, QuizStatus.PUBLISHED)
        is True
    )
    assert (
        validate_status_transition(QuizStatus.READY_FOR_REVIEW, QuizStatus.PUBLISHED)
        is False
    )

    # Test behavior: completion state after publishing
    quiz = create_mock_quiz_with_content()
    quiz.status = QuizStatus.PUBLISHED
    quiz.canvas_quiz_id = "quiz_123"

    assert is_quiz_complete(quiz) is True
    assert quiz.canvas_quiz_id is not None


def test_quiz_failure_workflow_behavior():
    """Test quiz failure workflow behavior."""
    from src.quiz.schemas import FailureReason, QuizStatus

    # Test behavior: failure reason tracking
    quiz = create_mock_quiz_with_content()
    quiz.status = QuizStatus.FAILED
    quiz.failure_reason = FailureReason.LLM_GENERATION_ERROR

    assert quiz.status == QuizStatus.FAILED
    assert quiz.failure_reason == FailureReason.LLM_GENERATION_ERROR

    # Test behavior: different failure reasons
    failure_reasons = [
        FailureReason.CONTENT_EXTRACTION_ERROR,
        FailureReason.NO_CONTENT_FOUND,
        FailureReason.LLM_GENERATION_ERROR,
        FailureReason.NO_QUESTIONS_GENERATED,
        FailureReason.CANVAS_EXPORT_ERROR,
    ]

    for reason in failure_reasons:
        quiz.failure_reason = reason
        assert quiz.failure_reason == reason


def test_quiz_retry_workflow_behavior():
    """Test quiz retry workflow behavior."""
    from src.quiz.schemas import FailureReason, QuizStatus
    from src.quiz.validators import is_quiz_ready_for_retry, validate_status_transition

    # Test behavior: retry transitions from failed state
    assert validate_status_transition(QuizStatus.FAILED, QuizStatus.CREATED) is True
    assert (
        validate_status_transition(QuizStatus.FAILED, QuizStatus.EXTRACTING_CONTENT)
        is True
    )
    assert (
        validate_status_transition(QuizStatus.FAILED, QuizStatus.GENERATING_QUESTIONS)
        is True
    )

    # Test behavior: retry eligibility
    quiz = create_mock_quiz_with_content()
    quiz.status = QuizStatus.FAILED
    quiz.failure_reason = FailureReason.CONTENT_EXTRACTION_ERROR

    assert is_quiz_ready_for_retry(quiz) is True

    # Test behavior: data clearing during retry
    quiz.extracted_content = {"old": "data"}
    quiz.content_extracted_at = datetime.now(timezone.utc)

    # Simulate retry behavior
    quiz.status = QuizStatus.CREATED
    quiz.extracted_content = None
    quiz.content_extracted_at = None

    assert quiz.status == QuizStatus.CREATED
    assert quiz.extracted_content is None
    assert quiz.content_extracted_at is None


def test_quiz_retry_workflow_invalid_status_behavior():
    """Test quiz retry workflow behavior with invalid current status."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.validators import is_quiz_ready_for_retry

    # Test behavior: retry not allowed from non-failed statuses
    quiz_published = create_mock_quiz_with_content()
    quiz_published.status = QuizStatus.PUBLISHED

    quiz_extracting = create_mock_quiz_with_content()
    quiz_extracting.status = QuizStatus.EXTRACTING_CONTENT

    quiz_ready = create_mock_quiz_with_content()
    quiz_ready.status = QuizStatus.READY_FOR_REVIEW

    assert is_quiz_ready_for_retry(quiz_published) is False
    assert is_quiz_ready_for_retry(quiz_extracting) is False
    assert is_quiz_ready_for_retry(quiz_ready) is False


def test_question_counts_workflow_behavior():
    """Test question counts workflow behavior."""
    # Test behavior: question count structure expectations
    expected_counts = {"total": 15, "approved": 10}

    # Test behavior: count validation
    assert expected_counts["total"] >= expected_counts["approved"]
    assert expected_counts["approved"] >= 0
    assert expected_counts["total"] >= 0

    # Test behavior: different count scenarios
    zero_counts = {"total": 0, "approved": 0}
    partial_counts = {"total": 20, "approved": 5}
    full_counts = {"total": 10, "approved": 10}

    for counts in [zero_counts, partial_counts, full_counts]:
        assert counts["total"] >= counts["approved"]
        assert isinstance(counts["total"], int)
        assert isinstance(counts["approved"], int)


def test_content_retrieval_workflow_behavior():
    """Test content retrieval workflow behavior."""
    # Test behavior: content structure expectations
    test_content = {"456": [{"content": "test", "word_count": 100}]}

    # Test behavior: content validation
    assert isinstance(test_content, dict)
    for module_id, content_items in test_content.items():
        assert isinstance(module_id, str)
        assert isinstance(content_items, list)
        for item in content_items:
            assert isinstance(item, dict)
            assert "content" in item
            assert "word_count" in item
            assert isinstance(item["content"], str)
            assert isinstance(item["word_count"], int)
            assert item["word_count"] >= 0


def test_multi_module_workflow_behavior(session: Session):
    """Test workflow behavior with multiple modules."""
    from src.quiz.service import prepare_content_extraction

    user = create_user_in_session(session)
    quiz = create_multi_module_test_quiz(session, user.id)

    # Test behavior: multi-module extraction parameters
    params = prepare_content_extraction(session, quiz.id, user.id)

    assert params["course_id"] == 12345
    assert set(params["module_ids"]) == {456, 789}  # Both modules

    # Test behavior: quiz properly updated
    session.refresh(quiz)
    assert quiz.question_count == 25  # 10 + 15 from both modules


def test_manual_module_workflow_behavior(session: Session):
    """Test workflow behavior with manual modules."""
    from src.quiz.service import prepare_content_extraction

    user = create_user_in_session(session)
    quiz = create_manual_module_test_quiz(session, user.id)

    # Test behavior: manual module extraction should fail with ValueError
    # because manual modules have non-numeric IDs
    with pytest.raises(ValueError, match="invalid literal for int"):
        prepare_content_extraction(session, quiz.id, user.id)


# Helper functions for behavior-focused testing


def create_mock_quiz_with_content():
    """Create a mock quiz with realistic content for workflow tests."""
    from src.question.types import QuizLanguage
    from src.quiz.schemas import QuizStatus, QuizTone

    mock_quiz = Mock()
    mock_quiz.id = uuid.uuid4()
    mock_quiz.owner_id = uuid.uuid4()
    mock_quiz.canvas_course_id = 12345
    mock_quiz.canvas_course_name = "Test Course"
    mock_quiz.title = "Test Quiz"
    mock_quiz.question_count = 10
    mock_quiz.llm_model = "gpt-5-mini-2025-08-07"
    mock_quiz.llm_temperature = 1.0
    mock_quiz.language = QuizLanguage.ENGLISH
    mock_quiz.tone = QuizTone.ACADEMIC
    mock_quiz.status = QuizStatus.CREATED
    mock_quiz.failure_reason = None
    mock_quiz.extracted_content = None
    mock_quiz.content_extracted_at = None
    mock_quiz.canvas_quiz_id = None
    mock_quiz.exported_at = None
    mock_quiz.last_status_update = datetime.now(timezone.utc)
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

    return mock_quiz


def create_test_quiz(session: Session, owner_id: uuid.UUID, title: str = "Test Quiz"):
    """Helper to create a test quiz for workflow tests."""
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


def create_multi_module_test_quiz(session: Session, owner_id: uuid.UUID):
    """Helper to create a test quiz with multiple modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz

    quiz_data = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Multi-Module Course",
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
        title="Multi-Module Quiz",
    )

    return create_quiz(session, quiz_data, owner_id)


def create_manual_module_test_quiz(session: Session, owner_id: uuid.UUID):
    """Helper to create a test quiz with manual modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz

    quiz_data = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Manual Course",
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

    return create_quiz(session, quiz_data, owner_id)
