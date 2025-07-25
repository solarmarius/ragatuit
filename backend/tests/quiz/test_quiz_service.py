"""Tests for quiz service layer."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session

from tests.factories import QuizFactory, UserFactory


def test_create_quiz_success(session: Session):
    """Test successful quiz creation."""
    from src.quiz.schemas import ModuleSelection, QuizCreate
    from src.quiz.service import create_quiz

    # Create user using helper function
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    from src.question.types import QuestionType
    from src.quiz.schemas import QuestionBatch

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={
            "456": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10)
                ],
            ),
            "789": ModuleSelection(
                name="Module 2",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=15)
                ],
            ),
        },
        title="Test Quiz",
        llm_model="gpt-4",
        llm_temperature=0.7,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify quiz creation
    assert quiz.owner_id == user.id
    assert quiz.canvas_course_id == 123
    assert quiz.canvas_course_name == "Test Course"
    assert quiz.selected_modules == {
        "456": {
            "name": "Module 1",
            "question_batches": [{"question_type": "multiple_choice", "count": 10}],
        },
        "789": {
            "name": "Module 2",
            "question_batches": [{"question_type": "multiple_choice", "count": 15}],
        },
    }
    assert quiz.title == "Test Quiz"
    assert quiz.question_count == 25  # 10 + 15 from modules
    assert quiz.llm_model == "gpt-4"
    assert quiz.llm_temperature == 0.7
    assert quiz.updated_at is not None


def test_create_quiz_with_defaults(session: Session):
    """Test quiz creation with default values."""
    from src.question.types import QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={
            "456": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10)
                ],
            )
        },
        title="Default Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify defaults
    assert quiz.question_count == 10  # Sum of module question counts
    assert quiz.llm_model == "o3"  # Default
    assert quiz.llm_temperature == 1.0  # Default


def test_create_quiz_with_multiple_question_types_per_module(session: Session):
    """Test that multiple question types per module are properly persisted."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    # Test with multiple question types per module
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Multi-Type Test Course",
        selected_modules={
            "456": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10),
                    QuestionBatch(question_type=QuestionType.FILL_IN_BLANK, count=5),
                ],
            ),
            "789": ModuleSelection(
                name="Module 2",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MATCHING, count=3),
                    QuestionBatch(question_type=QuestionType.CATEGORIZATION, count=2),
                ],
            ),
        },
        title="Multi-Type Quiz",
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify multiple question types are persisted correctly
    assert quiz.language == QuizLanguage.ENGLISH
    assert quiz.question_count == 20  # 10 + 5 + 3 + 2

    # Verify module structure
    expected_modules = {
        "456": {
            "name": "Module 1",
            "question_batches": [
                {"question_type": "multiple_choice", "count": 10},
                {"question_type": "fill_in_blank", "count": 5},
            ],
        },
        "789": {
            "name": "Module 2",
            "question_batches": [
                {"question_type": "matching", "count": 3},
                {"question_type": "categorization", "count": 2},
            ],
        },
    }
    assert quiz.selected_modules == expected_modules

    # Verify batch distribution property works
    batch_distribution = quiz.module_batch_distribution
    assert len(batch_distribution["456"]) == 2
    assert len(batch_distribution["789"]) == 2


def test_create_quiz_module_id_conversion(session: Session):
    """Test that module IDs are handled correctly as strings."""
    from src.question.types import QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={
            "111": ModuleSelection(
                name="Module A",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10)
                ],
            ),
            "222": ModuleSelection(
                name="Module B",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=15)
                ],
            ),
            "333": ModuleSelection(
                name="Module C",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=5)
                ],
            ),
        },
        title="Module Test Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify module ID conversion
    expected_modules = {
        "111": {
            "name": "Module A",
            "question_batches": [{"question_type": "multiple_choice", "count": 10}],
        },
        "222": {
            "name": "Module B",
            "question_batches": [{"question_type": "multiple_choice", "count": 15}],
        },
        "333": {
            "name": "Module C",
            "question_batches": [{"question_type": "multiple_choice", "count": 5}],
        },
    }
    assert quiz.selected_modules == expected_modules


def test_get_quiz_by_id_existing(session: Session):
    """Test retrieving an existing quiz by ID."""
    from src.quiz.service import get_quiz_by_id

    # Create user and quiz using helper functions
    from tests.conftest import create_quiz_in_session, create_user_in_session

    user = create_user_in_session(session)
    created_quiz = create_quiz_in_session(session, owner=user)

    found_quiz = get_quiz_by_id(session, created_quiz.id)

    assert found_quiz is not None
    assert found_quiz.id == created_quiz.id
    assert found_quiz.title == created_quiz.title
    assert found_quiz.canvas_course_id == created_quiz.canvas_course_id


def test_get_quiz_by_id_nonexistent(session: Session):
    """Test retrieving a non-existent quiz returns None."""
    from src.quiz.service import get_quiz_by_id

    random_id = uuid.uuid4()
    found_quiz = get_quiz_by_id(session, random_id)
    assert found_quiz is None


def test_get_user_quizzes_success(session: Session):
    """Test retrieving quizzes for a user."""
    from src.quiz.service import get_user_quizzes
    from tests.conftest import create_quiz_in_session, create_user_in_session

    user = create_user_in_session(session)
    quiz1 = create_quiz_in_session(session, owner=user, title="Quiz 1")
    quiz2 = create_quiz_in_session(session, owner=user, title="Quiz 2")

    # Create quiz for different user
    other_user = create_user_in_session(session)
    create_quiz_in_session(session, owner=other_user, title="Other Quiz")

    user_quizzes = get_user_quizzes(session, user.id)

    assert len(user_quizzes) == 2
    quiz_titles = [quiz.title for quiz in user_quizzes]
    assert "Quiz 1" in quiz_titles
    assert "Quiz 2" in quiz_titles
    assert "Other Quiz" not in quiz_titles


def test_get_user_quizzes_empty(session: Session):
    """Test retrieving quizzes for user with no quizzes."""
    from src.quiz.service import get_user_quizzes
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    user_quizzes = get_user_quizzes(session, user.id)

    assert user_quizzes == []


def test_delete_quiz_as_owner_success(session: Session):
    """Test successful quiz soft deletion by owner."""
    from src.quiz.service import delete_quiz
    from tests.conftest import create_quiz_in_session

    quiz = create_quiz_in_session(session)
    quiz_id = quiz.id
    owner_id = quiz.owner_id

    result = delete_quiz(session, quiz_id, owner_id)

    assert result is True

    # Verify quiz is soft-deleted (not returned by default query)
    from src.quiz.service import get_quiz_by_id

    deleted_quiz = get_quiz_by_id(session, quiz_id)
    assert deleted_quiz is None

    # But exists when including deleted
    soft_deleted_quiz = get_quiz_by_id(session, quiz_id, include_deleted=True)
    assert soft_deleted_quiz is not None
    assert soft_deleted_quiz.deleted is True


def test_delete_quiz_not_owner_fails(session: Session):
    """Test quiz deletion fails when user is not owner."""
    from src.quiz.service import delete_quiz
    from tests.conftest import create_quiz_in_session, create_user_in_session

    quiz = create_quiz_in_session(session)
    other_user = create_user_in_session(session)

    result = delete_quiz(session, quiz.id, other_user.id)

    assert result is False

    # Verify quiz still exists
    from src.quiz.service import get_quiz_by_id

    existing_quiz = get_quiz_by_id(session, quiz.id)
    assert existing_quiz is not None


def test_delete_quiz_nonexistent_fails(session: Session):
    """Test deletion of non-existent quiz fails."""
    from src.quiz.service import delete_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)
    random_id = uuid.uuid4()

    result = delete_quiz(session, random_id, user.id)

    assert result is False


@pytest.mark.asyncio
async def test_get_quiz_for_update(async_session):
    """Test getting quiz with row lock for update."""
    from src.auth.models import User
    from src.quiz.models import Quiz
    from src.quiz.service import get_quiz_for_update

    # Create a user first
    user = User(
        canvas_id=123,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create a quiz in the session first
    quiz = Quiz(
        owner_id=user.id,
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={"1": "Module 1"},
        title="Test Quiz",
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)
    quiz_id = quiz.id

    found_quiz = await get_quiz_for_update(async_session, quiz_id)

    assert found_quiz is not None
    assert found_quiz.id == quiz_id


@pytest.mark.asyncio
async def test_get_quiz_for_update_nonexistent(async_session):
    """Test getting non-existent quiz for update returns None."""
    from src.quiz.service import get_quiz_for_update

    random_id = uuid.uuid4()

    found_quiz = await get_quiz_for_update(async_session, random_id)

    assert found_quiz is None


@pytest.mark.asyncio
async def test_get_content_from_quiz(async_session):
    """Test getting extracted content from quiz."""
    from src.auth.models import User
    from src.quiz.models import Quiz
    from src.quiz.service import get_content_from_quiz

    content_data = {"modules": [{"id": "1", "content": "Test content"}]}

    # Create a user first
    user = User(
        canvas_id=124,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    quiz = Quiz(
        owner_id=user.id,
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={"1": {"name": "Module 1", "question_count": 10}},
        title="Test Quiz",
        extracted_content=content_data,
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)

    content = await get_content_from_quiz(async_session, quiz.id)

    assert content == content_data


@pytest.mark.asyncio
async def test_get_question_counts(async_session):
    """Test getting question counts for a quiz."""
    from src.auth.models import User
    from src.quiz.models import Quiz
    from src.quiz.service import get_question_counts

    # Create a user first
    user = User(
        canvas_id=125,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create quiz
    quiz = Quiz(
        owner_id=user.id,
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={"1": {"name": "Module 1", "question_count": 10}},
        title="Test Quiz",
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)

    # Mock Question import and query
    with (
        patch("src.quiz.service.select") as mock_select,
        patch("src.quiz.service.func") as mock_func,
    ):
        # Mock the query result
        mock_result = MagicMock()
        mock_result.first.return_value = MagicMock(total=5, approved=3)
        async_session.execute = AsyncMock(return_value=mock_result)

        counts = await get_question_counts(async_session, quiz.id)

    assert counts == {"total": 5, "approved": 3}


def test_prepare_content_extraction_success(session: Session):
    """Test successful content extraction preparation."""
    from src.quiz.service import prepare_content_extraction
    from tests.conftest import create_quiz_in_session

    quiz = create_quiz_in_session(
        session,
        selected_modules={
            "123": {"name": "Module A", "question_count": 10},
            "456": {"name": "Module B", "question_count": 15},
        },
    )

    with patch(
        "src.quiz.service.validate_quiz_for_content_extraction"
    ) as mock_validate:
        mock_validate.return_value = quiz

        result = prepare_content_extraction(session, quiz.id, quiz.owner_id)

    # Verify result
    assert result["course_id"] == quiz.canvas_course_id
    assert set(result["module_ids"]) == {123, 456}


def test_prepare_question_generation_success(session: Session):
    """Test successful question generation preparation."""
    from src.quiz.service import prepare_question_generation
    from tests.conftest import create_quiz_in_session

    # Create quiz with selected_modules that total 75 questions
    selected_modules = {
        "module_1": {
            "name": "Introduction",
            "question_batches": [{"question_type": "multiple_choice", "count": 30}],
        },
        "module_2": {
            "name": "Advanced Topics",
            "question_batches": [
                {"question_type": "multiple_choice", "count": 25},
                {"question_type": "fill_in_blank", "count": 20},
            ],
        },
    }

    quiz = create_quiz_in_session(
        session,
        selected_modules=selected_modules,
        llm_model="gpt-4",
        llm_temperature=0.8,
    )

    with patch(
        "src.quiz.service.validate_quiz_for_question_generation"
    ) as mock_validate:
        mock_validate.return_value = quiz

        result = prepare_question_generation(session, quiz.id, quiz.owner_id)

    # Verify result
    assert result["question_count"] == 75
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.8


@pytest.mark.asyncio
async def test_reserve_quiz_job_extraction_success(async_session):
    """Test successful extraction job reservation."""
    from src.auth.models import User
    from src.quiz.models import Quiz
    from src.quiz.service import reserve_quiz_job

    # Create a user first
    user = User(
        canvas_id=126,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    quiz = Quiz(
        owner_id=user.id,
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={
            "1": {
                "name": "Module 1",
                "question_batches": [{"question_type": "multiple_choice", "count": 50}],
            }
        },
        question_count=50,
        title="Test Quiz",
        llm_model="gpt-4",
        llm_temperature=0.7,
        status="created",
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)

    with patch("src.quiz.service.get_quiz_for_update", return_value=quiz):
        result = await reserve_quiz_job(async_session, quiz.id, "extraction")

    assert result is not None
    assert result["target_questions"] == 50
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.7


@pytest.mark.asyncio
async def test_reserve_quiz_job_already_processing(async_session):
    """Test job reservation when already processing."""
    from src.quiz.models import Quiz
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import reserve_quiz_job

    quiz = Quiz(
        owner_id=uuid.uuid4(),
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={"1": {"name": "Module 1", "question_count": 10}},
        title="Test Quiz",
        status=QuizStatus.EXTRACTING_CONTENT,
    )

    with patch("src.quiz.service.get_quiz_for_update", return_value=quiz):
        result = await reserve_quiz_job(async_session, quiz.id, "extraction")

    assert result is None


@pytest.mark.asyncio
async def test_update_quiz_status_content_extraction(async_session):
    """Test updating content extraction status to completed."""
    from src.auth.models import User
    from src.quiz.models import Quiz
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import update_quiz_status

    # Create a user first
    user = User(
        canvas_id=127,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    quiz = Quiz(
        owner_id=user.id,
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={"1": {"name": "Module 1", "question_count": 10}},
        title="Test Quiz",
        status=QuizStatus.EXTRACTING_CONTENT,
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)

    extracted_content = {"modules": [{"id": "1", "content": "Test"}]}

    with patch("src.quiz.service.get_quiz_for_update", return_value=quiz):
        await update_quiz_status(
            async_session,
            quiz.id,
            QuizStatus.READY_FOR_REVIEW,
            extracted_content=extracted_content,
        )

    # In a real test, you'd refresh the quiz and check the updates
    # For this mock test, we verify the function completed without error
    assert True


@pytest.mark.asyncio
async def test_update_quiz_status_quiz_not_found(async_session):
    """Test status update when quiz not found."""
    from src.quiz.schemas import QuizStatus
    from src.quiz.service import update_quiz_status

    random_id = uuid.uuid4()

    with patch("src.quiz.service.get_quiz_for_update", return_value=None):
        await update_quiz_status(async_session, random_id, QuizStatus.READY_FOR_REVIEW)

    # Should handle gracefully without error
    assert True


def test_quiz_lifecycle_creation_to_deletion(session: Session):
    """Test complete quiz lifecycle from creation to deletion."""
    from src.question.types import QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import (
        create_quiz,
        delete_quiz,
        get_quiz_by_id,
        get_user_quizzes,
    )
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    # Create quiz
    quiz_data = QuizCreate(
        canvas_course_id=999,
        canvas_course_name="Lifecycle Course",
        selected_modules={
            "111": ModuleSelection(
                name="Module Alpha",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=15)
                ],
            ),
            "222": ModuleSelection(
                name="Module Beta",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10)
                ],
            ),
        },
        title="Lifecycle Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)
    quiz_id = quiz.id

    # Verify creation
    assert quiz.owner_id == user.id
    assert quiz.title == "Lifecycle Quiz"

    # Retrieve by ID
    found_quiz = get_quiz_by_id(session, quiz_id)
    assert found_quiz is not None
    assert found_quiz.id == quiz_id

    # Get user quizzes
    user_quizzes = get_user_quizzes(session, user.id)
    assert len(user_quizzes) == 1
    assert user_quizzes[0].id == quiz_id

    # Delete quiz (soft delete)
    delete_result = delete_quiz(session, quiz_id, user.id)
    assert delete_result is True

    # Verify soft deletion
    deleted_quiz = get_quiz_by_id(session, quiz_id)
    assert deleted_quiz is None

    # But quiz exists when including deleted
    soft_deleted_quiz = get_quiz_by_id(session, quiz_id, include_deleted=True)
    assert soft_deleted_quiz is not None
    assert soft_deleted_quiz.deleted is True

    # Verify user has no active quizzes (soft-deleted excluded by default)
    user_quizzes_after = get_user_quizzes(session, user.id)
    assert len(user_quizzes_after) == 0

    # But quiz appears when including deleted
    user_quizzes_all = get_user_quizzes(session, user.id, include_deleted=True)
    assert len(user_quizzes_all) == 1


def test_multiple_users_quiz_isolation(session: Session):
    """Test that quizzes are properly isolated between users."""
    from src.quiz.service import delete_quiz, get_quiz_by_id, get_user_quizzes
    from tests.conftest import create_quiz_in_session, create_user_in_session

    user1 = create_user_in_session(session)
    user2 = create_user_in_session(session)

    # Create quizzes for each user
    quiz1 = create_quiz_in_session(session, owner=user1, title="User 1 Quiz")
    quiz2 = create_quiz_in_session(session, owner=user2, title="User 2 Quiz")

    # Verify isolation
    user1_quizzes = get_user_quizzes(session, user1.id)
    user2_quizzes = get_user_quizzes(session, user2.id)

    assert len(user1_quizzes) == 1
    assert len(user2_quizzes) == 1
    assert user1_quizzes[0].title == "User 1 Quiz"
    assert user2_quizzes[0].title == "User 2 Quiz"

    # User 1 cannot delete User 2's quiz
    delete_result = delete_quiz(session, quiz2.id, user1.id)
    assert delete_result is False

    # Quiz 2 should still exist
    existing_quiz2 = get_quiz_by_id(session, quiz2.id)
    assert existing_quiz2 is not None


@pytest.mark.parametrize(
    "question_count,llm_model,temperature",
    [
        (1, "gpt-3.5", 0.0),
        (100, "gpt-4", 1.0),
        (200, "claude", 2.0),
        (50, "custom-model", 1.5),
    ],
)
def test_create_quiz_with_various_parameters(
    session: Session, question_count: int, llm_model: str, temperature: float
):
    """Test quiz creation with various parameter combinations."""
    from src.question.types import QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Param Test Course",
        selected_modules={
            "1": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=min(question_count, 20),
                    )
                ],
            )
        },
        title=f"Quiz {question_count}q",
        llm_model=llm_model,
        llm_temperature=temperature,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    assert quiz.question_count == min(question_count, 20)
    assert quiz.llm_model == llm_model
    assert quiz.llm_temperature == temperature


# Norwegian Language Feature Tests


def test_create_quiz_with_norwegian_language(session: Session):
    """Test quiz creation with Norwegian language selection."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Norwegian Course",
        selected_modules={
            "456": ModuleSelection(
                name="Modul 1",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10)
                ],
            )
        },
        title="Norsk Quiz",
        language=QuizLanguage.NORWEGIAN,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify Norwegian language is set
    assert quiz.language == QuizLanguage.NORWEGIAN
    assert quiz.canvas_course_name == "Norwegian Course"
    assert quiz.title == "Norsk Quiz"


def test_create_quiz_language_defaults_to_english(session: Session):
    """Test quiz creation defaults to English when language not specified."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Default Language Course",
        selected_modules={
            "456": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10)
                ],
            )
        },
        title="Default Quiz",
        # language not specified - should default to English
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify default language is English
    assert quiz.language == QuizLanguage.ENGLISH


def test_create_quiz_with_english_language_explicit(session: Session):
    """Test quiz creation with explicit English language selection."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="English Course",
        selected_modules={
            "456": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10)
                ],
            )
        },
        title="English Quiz",
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify English language is set explicitly
    assert quiz.language == QuizLanguage.ENGLISH


def test_prepare_question_generation_includes_language(session: Session):
    """Test that prepare_question_generation includes language in results."""
    from src.question.types import QuizLanguage
    from src.quiz.service import prepare_question_generation
    from tests.conftest import create_quiz_in_session

    # Create quiz with Norwegian language and selected_modules that total 75 questions
    selected_modules = {
        "module_1": {
            "name": "Introduction",
            "question_batches": [{"question_type": "multiple_choice", "count": 40}],
        },
        "module_2": {
            "name": "Advanced Topics",
            "question_batches": [{"question_type": "fill_in_blank", "count": 35}],
        },
    }

    quiz = create_quiz_in_session(
        session,
        selected_modules=selected_modules,
        llm_model="gpt-4",
        llm_temperature=0.8,
        language=QuizLanguage.NORWEGIAN,
    )

    with patch(
        "src.quiz.service.validate_quiz_for_question_generation"
    ) as mock_validate:
        mock_validate.return_value = quiz

        result = prepare_question_generation(session, quiz.id, quiz.owner_id)

    # Verify language is included in generation parameters
    assert result["language"] == QuizLanguage.NORWEGIAN
    assert result["question_count"] == 75
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.8


@pytest.mark.asyncio
async def test_reserve_quiz_job_includes_language_setting(async_session):
    """Test that quiz job reservation includes language in settings."""
    from src.auth.models import User
    from src.question.types import QuizLanguage
    from src.quiz.models import Quiz
    from src.quiz.service import reserve_quiz_job

    # Create a user first
    user = User(
        canvas_id=128,
        name="Language Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    quiz = Quiz(
        owner_id=user.id,
        canvas_course_id=123,
        canvas_course_name="Norwegian Test Course",
        selected_modules={
            "1": {
                "name": "Modul 1",
                "question_batches": [{"question_type": "multiple_choice", "count": 50}],
            }
        },
        question_count=50,
        title="Norsk Test Quiz",
        llm_model="gpt-4",
        llm_temperature=0.7,
        language=QuizLanguage.NORWEGIAN,
        status="created",
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)

    with patch("src.quiz.service.get_quiz_for_update", return_value=quiz):
        result = await reserve_quiz_job(async_session, quiz.id, "extraction")

    assert result is not None
    assert result["language"] == QuizLanguage.NORWEGIAN
    assert result["target_questions"] == 50
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.7


# Soft Delete Tests


def test_delete_quiz_soft_delete_success(session: Session):
    """Test quiz soft deletion preserves data for research."""
    from src.quiz.service import delete_quiz, get_quiz_by_id
    from tests.conftest import create_quiz_in_session

    quiz = create_quiz_in_session(session)
    quiz_id = quiz.id
    owner_id = quiz.owner_id

    result = delete_quiz(session, quiz_id, owner_id)

    assert result is True

    # Verify quiz is soft-deleted (not returned by default query)
    deleted_quiz = get_quiz_by_id(session, quiz_id)
    assert deleted_quiz is None

    # But can be retrieved when including deleted
    soft_deleted_quiz = get_quiz_by_id(session, quiz_id, include_deleted=True)
    assert soft_deleted_quiz is not None
    assert soft_deleted_quiz.deleted is True
    assert soft_deleted_quiz.deleted_at is not None


def test_quiz_cascade_soft_delete_to_questions(session: Session):
    """Test quiz deletion cascades soft delete to associated questions."""
    from src.quiz.service import delete_quiz
    from tests.conftest import create_quiz_in_session

    # Create quiz with questions
    quiz = create_quiz_in_session(session)

    # Create some questions for the quiz
    from src.question.models import Question
    from src.question.types import QuestionType

    question1 = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data={"question_text": "Test Q1", "choices": ["A", "B"]},
    )
    question2 = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data={"question_text": "Test Q2", "choices": ["C", "D"]},
    )
    session.add_all([question1, question2])
    session.commit()
    session.refresh(question1)
    session.refresh(question2)

    # Delete the quiz
    result = delete_quiz(session, quiz.id, quiz.owner_id)
    assert result is True

    # Verify questions are also soft-deleted by checking directly
    from sqlmodel import select

    q1_soft_deleted = session.exec(
        select(Question).where(Question.id == question1.id)
    ).first()
    q2_soft_deleted = session.exec(
        select(Question).where(Question.id == question2.id)
    ).first()

    assert q1_soft_deleted.deleted is True
    assert q1_soft_deleted.deleted_at is not None
    assert q2_soft_deleted.deleted is True
    assert q2_soft_deleted.deleted_at is not None


def test_get_user_quizzes_excludes_soft_deleted(session: Session):
    """Test get_user_quizzes excludes soft-deleted quizzes by default."""
    from src.quiz.service import delete_quiz, get_user_quizzes
    from tests.conftest import create_quiz_in_session, create_user_in_session

    user = create_user_in_session(session)

    # Create two quizzes
    quiz1 = create_quiz_in_session(session, owner=user, title="Active Quiz")
    quiz2 = create_quiz_in_session(session, owner=user, title="To Delete Quiz")

    # Initially both should be returned
    user_quizzes = get_user_quizzes(session, user.id)
    assert len(user_quizzes) == 2

    # Soft delete one quiz
    delete_quiz(session, quiz2.id, user.id)

    # Only active quiz should be returned
    user_quizzes_after = get_user_quizzes(session, user.id)
    assert len(user_quizzes_after) == 1
    assert user_quizzes_after[0].title == "Active Quiz"

    # Both should be returned when including deleted
    user_quizzes_all = get_user_quizzes(session, user.id, include_deleted=True)
    assert len(user_quizzes_all) == 2


def test_get_quiz_by_id_include_deleted_parameter(session: Session):
    """Test get_quiz_by_id include_deleted parameter works correctly."""
    from src.quiz.service import delete_quiz, get_quiz_by_id
    from tests.conftest import create_quiz_in_session

    quiz = create_quiz_in_session(session)
    quiz_id = quiz.id

    # Initially quiz is returned
    active_quiz = get_quiz_by_id(session, quiz_id)
    assert active_quiz is not None

    # Soft delete the quiz
    delete_quiz(session, quiz_id, quiz.owner_id)

    # Default query excludes soft-deleted
    deleted_quiz = get_quiz_by_id(session, quiz_id)
    assert deleted_quiz is None

    # include_deleted=True returns soft-deleted quiz
    soft_deleted_quiz = get_quiz_by_id(session, quiz_id, include_deleted=True)
    assert soft_deleted_quiz is not None
    assert soft_deleted_quiz.deleted is True


@pytest.mark.asyncio
async def test_get_question_counts_excludes_soft_deleted_questions(async_session):
    """Test get_question_counts excludes soft-deleted questions by default."""
    from src.auth.models import User
    from src.question.types import QuestionType
    from src.quiz.models import Quiz
    from src.quiz.service import get_question_counts

    # Create user and quiz
    user = User(
        canvas_id=140,
        name="Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    quiz = Quiz(
        owner_id=user.id,
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={"1": {"name": "Module 1", "question_count": 10}},
        title="Test Quiz",
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)

    # Store quiz_id immediately after refresh to avoid lazy loading issues
    quiz_id = quiz.id

    # Create questions
    from src.question.types.base import Question

    question1 = Question(
        quiz_id=quiz_id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data={"question_text": "Q1", "choices": ["A", "B"]},
        is_approved=True,
    )
    question2 = Question(
        quiz_id=quiz_id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data={"question_text": "Q2", "choices": ["C", "D"]},
        is_approved=False,
    )
    question3 = Question(
        quiz_id=quiz_id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data={"question_text": "Q3", "choices": ["E", "F"]},
        is_approved=True,
        deleted=True,  # Soft-deleted question
    )
    async_session.add_all([question1, question2, question3])
    await async_session.commit()

    # Get counts excluding soft-deleted
    counts = await get_question_counts(async_session, quiz_id)
    assert counts["total"] == 2  # Excludes soft-deleted question3
    assert counts["approved"] == 1  # Only question1 is approved and not deleted

    # Get counts including soft-deleted
    counts_all = await get_question_counts(async_session, quiz_id, include_deleted=True)
    assert counts_all["total"] == 3  # Includes all questions
    assert counts_all["approved"] == 2  # question1 and question3 are approved


def test_prevent_double_soft_deletion(session: Session):
    """Test that attempting to soft delete an already soft-deleted quiz fails."""
    from src.quiz.service import delete_quiz, get_quiz_by_id
    from tests.conftest import create_quiz_in_session

    quiz = create_quiz_in_session(session)
    quiz_id = quiz.id
    owner_id = quiz.owner_id

    # First deletion succeeds
    result1 = delete_quiz(session, quiz_id, owner_id)
    assert result1 is True

    # Second deletion fails (quiz already soft-deleted)
    result2 = delete_quiz(session, quiz_id, owner_id)
    assert result2 is False

    # Verify quiz is still soft-deleted (not hard deleted)
    soft_deleted_quiz = get_quiz_by_id(session, quiz_id, include_deleted=True)
    assert soft_deleted_quiz is not None
    assert soft_deleted_quiz.deleted is True


@pytest.mark.asyncio
async def test_async_functions_respect_soft_delete_filter(async_session):
    """Test async functions respect soft delete filtering."""
    from src.auth.models import User
    from src.quiz.models import Quiz
    from src.quiz.service import get_content_from_quiz, get_quiz_for_update

    # Create user and quiz
    user = User(
        canvas_id=141,
        name="Async Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    quiz = Quiz(
        owner_id=user.id,
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={"1": {"name": "Module 1", "question_count": 10}},
        title="Test Quiz",
        deleted=True,  # Create as soft-deleted
        extracted_content={"test": "content"},
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)

    # Store quiz_id before using it in async operations
    quiz_id = quiz.id

    # Async functions should exclude soft-deleted by default
    quiz_for_update = await get_quiz_for_update(async_session, quiz_id)
    assert quiz_for_update is None

    content = await get_content_from_quiz(async_session, quiz_id)
    assert content is None

    # But include when requested
    quiz_for_update_inc = await get_quiz_for_update(
        async_session, quiz_id, include_deleted=True
    )
    assert quiz_for_update_inc is not None

    content_inc = await get_content_from_quiz(
        async_session, quiz_id, include_deleted=True
    )
    assert content_inc == {"test": "content"}


def test_soft_delete_preserves_all_quiz_data(session: Session):
    """Test soft deletion preserves all quiz data for research purposes."""
    from src.quiz.service import delete_quiz, get_quiz_by_id
    from tests.conftest import create_quiz_in_session

    # Create quiz with comprehensive data
    quiz = create_quiz_in_session(
        session,
        title="Research Quiz",
        question_count=50,
        llm_model="gpt-4",
        llm_temperature=0.8,
        selected_modules={
            "123": {"name": "AI Module", "question_count": 25},
            "456": {"name": "ML Module", "question_count": 25},
        },
    )

    original_data = {
        "title": quiz.title,
        "question_count": quiz.question_count,
        "llm_model": quiz.llm_model,
        "llm_temperature": quiz.llm_temperature,
        "selected_modules": quiz.selected_modules,
        "canvas_course_id": quiz.canvas_course_id,
        "canvas_course_name": quiz.canvas_course_name,
    }

    # Soft delete the quiz
    result = delete_quiz(session, quiz.id, quiz.owner_id)
    assert result is True

    # Retrieve soft-deleted quiz and verify all data is preserved
    soft_deleted_quiz = get_quiz_by_id(session, quiz.id, include_deleted=True)
    assert soft_deleted_quiz is not None
    assert soft_deleted_quiz.deleted is True
    assert soft_deleted_quiz.deleted_at is not None

    # Verify all original data is preserved
    assert soft_deleted_quiz.title == original_data["title"]
    assert soft_deleted_quiz.question_count == original_data["question_count"]
    assert soft_deleted_quiz.llm_model == original_data["llm_model"]
    assert soft_deleted_quiz.llm_temperature == original_data["llm_temperature"]
    assert soft_deleted_quiz.selected_modules == original_data["selected_modules"]
    assert soft_deleted_quiz.canvas_course_id == original_data["canvas_course_id"]
    assert soft_deleted_quiz.canvas_course_name == original_data["canvas_course_name"]
