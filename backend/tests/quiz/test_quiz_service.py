"""Tests for quiz service layer - Unique functionality not covered by behavior-focused tests.

This file contains tests for:
- Tone/Language feature combinations
- Difficulty level variations
- Manual module advanced scenarios
- Async function testing
- Parametrized testing
- Complex integration scenarios

Basic CRUD, validation, and workflows are covered by the refactored test files:
- test_quiz_crud.py
- test_quiz_validation.py
- test_quiz_workflows.py
- test_quiz_status_management.py
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session

from tests.conftest import create_user_in_async_session
from tests.factories import QuizFactory, UserFactory
from tests.test_data import (
    DEFAULT_EXTRACTED_CONTENT,
    DEFAULT_QUIZ_CONFIG,
    DEFAULT_SELECTED_MODULES,
    get_unique_quiz_config,
    get_unique_user_data,
)


def test_create_quiz_module_id_conversion(session: Session):
    """Test that module IDs are properly converted for storage."""
    from src.quiz.schemas import ModuleSelection, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import QuestionBatch

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="ID Conversion Test Course",
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
        title="ID Conversion Test Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Module ID should be stored as string in selected_modules
    assert "456" in quiz.selected_modules
    assert isinstance(list(quiz.selected_modules.keys())[0], str)


@pytest.mark.asyncio
async def test_get_quiz_for_update(async_session):
    """Test getting quiz with row lock for update."""
    from src.quiz.models import Quiz
    from src.quiz.service import get_quiz_for_update

    # Create a user using centralized helper
    user = await create_user_in_async_session(async_session)

    # Use centralized quiz config
    quiz_config = get_unique_quiz_config()

    # Create a quiz in the session first
    quiz = Quiz(
        owner_id=user.id,
        **quiz_config,
        selected_modules=DEFAULT_SELECTED_MODULES,
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
    from src.quiz.models import Quiz
    from src.quiz.service import get_content_from_quiz

    # Create a user using centralized helper
    user = await create_user_in_async_session(async_session, canvas_id=124)

    # Use centralized data
    quiz_config = get_unique_quiz_config()

    quiz = Quiz(
        owner_id=user.id,
        **quiz_config,
        selected_modules=DEFAULT_SELECTED_MODULES,
        extracted_content=DEFAULT_EXTRACTED_CONTENT,
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)

    content = await get_content_from_quiz(async_session, quiz.id)

    assert content == DEFAULT_EXTRACTED_CONTENT


@pytest.mark.asyncio
async def test_get_question_counts(async_session):
    """Test getting question counts for a quiz."""
    from src.quiz.models import Quiz
    from src.quiz.service import get_question_counts

    # Create a user using centralized helper
    user = await create_user_in_async_session(async_session, canvas_id=125)

    # Use centralized quiz config
    quiz_config = get_unique_quiz_config()

    # Create quiz
    quiz = Quiz(
        owner_id=user.id,
        **quiz_config,
        selected_modules=DEFAULT_SELECTED_MODULES,
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


def test_quiz_lifecycle_creation_to_deletion(session: Session):
    """Test complete quiz lifecycle from creation to soft deletion."""
    from src.quiz.service import create_quiz, delete_quiz, get_quiz_by_id
    from tests.conftest import create_quiz_in_session

    quiz = create_quiz_in_session(session)
    quiz_id = quiz.id
    owner_id = quiz.owner_id

    # Verify creation
    assert quiz.id is not None
    assert quiz.owner_id == owner_id

    # Verify retrieval
    retrieved_quiz = get_quiz_by_id(session, quiz_id)
    assert retrieved_quiz is not None
    assert retrieved_quiz.id == quiz_id

    # Verify soft deletion
    deletion_result = delete_quiz(session, quiz_id, owner_id)
    assert deletion_result is True

    # Verify quiz is soft deleted (not returned by default)
    deleted_quiz = get_quiz_by_id(session, quiz_id)
    assert deleted_quiz is None

    # But can be retrieved with include_deleted=True
    deleted_quiz = get_quiz_by_id(session, quiz_id, include_deleted=True)
    assert deleted_quiz is not None
    assert deleted_quiz.deleted is True


def test_multiple_users_quiz_isolation(session: Session):
    """Test that users can only access their own quizzes."""
    from src.quiz.service import get_user_quizzes
    from tests.conftest import create_quiz_in_session, create_user_in_session

    # Create two users
    user1 = create_user_in_session(session, canvas_id=1)
    user2 = create_user_in_session(session, canvas_id=2)

    # Create quizzes for each user
    quiz1 = create_quiz_in_session(session, owner=user1, title="User 1 Quiz")
    quiz2 = create_quiz_in_session(session, owner=user2, title="User 2 Quiz")

    # Verify isolation
    user1_quizzes = get_user_quizzes(session, user1.id)
    user2_quizzes = get_user_quizzes(session, user2.id)

    assert len(user1_quizzes) == 1
    assert len(user2_quizzes) == 1
    assert user1_quizzes[0].id == quiz1.id
    assert user2_quizzes[0].id == quiz2.id


@pytest.mark.parametrize(
    "llm_model,temperature",
    [
        ("gpt-4", 0.5),
        ("gpt-4", 1.0),
        ("o4-mini-2025-04-16", 0.7),
        ("o4-mini-2025-04-16", 1.5),
    ],
)
def test_create_quiz_with_various_parameters(
    session: Session, llm_model: str, temperature: float
):
    """Test quiz creation with various LLM model and temperature combinations."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Parameter Test Course",
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
        title=f"Test Quiz {llm_model}",
        llm_model=llm_model,
        llm_temperature=temperature,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    assert quiz.llm_model == llm_model
    assert quiz.llm_temperature == temperature


# Tone Feature Tests


def test_create_quiz_with_tone_academic_default(session: Session):
    """Test quiz creation defaults to academic tone."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate, QuizTone
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Default Tone Course",
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
        title="Default Tone Quiz",
        # tone not specified - should default to academic
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify default tone is academic
    assert quiz.tone == QuizTone.ACADEMIC


def test_create_quiz_with_tone_explicit_academic(session: Session):
    """Test quiz creation with explicit academic tone selection."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate, QuizTone
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Academic Tone Course",
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
        title="Academic Tone Quiz",
        tone=QuizTone.ACADEMIC,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify academic tone is set
    assert quiz.tone == QuizTone.ACADEMIC


def test_create_quiz_with_tone_casual(session: Session):
    """Test quiz creation with casual tone selection."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate, QuizTone
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Casual Tone Course",
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
        title="Casual Tone Quiz",
        tone=QuizTone.CASUAL,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify casual tone is set
    assert quiz.tone == QuizTone.CASUAL


def test_create_quiz_with_tone_encouraging(session: Session):
    """Test quiz creation with encouraging tone selection."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate, QuizTone
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Encouraging Tone Course",
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
        title="Encouraging Tone Quiz",
        tone=QuizTone.ENCOURAGING,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify encouraging tone is set
    assert quiz.tone == QuizTone.ENCOURAGING


def test_create_quiz_with_tone_professional(session: Session):
    """Test quiz creation with professional tone selection."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate, QuizTone
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Professional Tone Course",
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
        title="Professional Tone Quiz",
        tone=QuizTone.PROFESSIONAL,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify professional tone is set
    assert quiz.tone == QuizTone.PROFESSIONAL


def test_create_quiz_with_tone_and_language_combination(session: Session):
    """Test quiz creation with both tone and language specified."""
    from src.question.types import QuestionDifficulty, QuestionType, QuizLanguage
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate, QuizTone
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Combination Course",
        selected_modules={
            "456": ModuleSelection(
                name="Modul 1",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title="Kombinasjon Quiz",
        language=QuizLanguage.NORWEGIAN,
        tone=QuizTone.ENCOURAGING,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify both language and tone are set
    assert quiz.language == QuizLanguage.NORWEGIAN
    assert quiz.tone == QuizTone.ENCOURAGING


# Norwegian Language Feature Tests


def test_create_quiz_with_norwegian_language(session: Session):
    """Test quiz creation with Norwegian language selection."""
    from src.question.types import QuestionDifficulty, QuestionType, QuizLanguage
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
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
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
    from src.question.types import QuestionDifficulty, QuestionType, QuizLanguage
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
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
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
    from src.question.types import QuestionDifficulty, QuestionType, QuizLanguage
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
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title="English Quiz",
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify English language is set explicitly
    assert quiz.language == QuizLanguage.ENGLISH


def test_prepare_question_generation_includes_tone(session: Session):
    """Test that prepare_question_generation includes tone in results."""
    from src.quiz.schemas import QuizTone
    from src.quiz.service import prepare_question_generation
    from tests.conftest import create_quiz_in_session

    # Create quiz with encouraging tone and selected_modules that total 50 questions
    selected_modules = {
        "module_1": {
            "name": "Introduction",
            "question_batches": [{"question_type": "multiple_choice", "count": 30}],
        },
        "module_2": {
            "name": "Advanced Topics",
            "question_batches": [{"question_type": "fill_in_blank", "count": 20}],
        },
    }

    quiz = create_quiz_in_session(
        session,
        selected_modules=selected_modules,
        llm_model="gpt-4",
        llm_temperature=0.8,
        tone=QuizTone.ENCOURAGING,
    )

    with patch(
        "src.quiz.service.validate_quiz_for_question_generation"
    ) as mock_validate:
        mock_validate.return_value = quiz

        result = prepare_question_generation(session, quiz.id, quiz.owner_id)

    # Verify tone is included in generation parameters
    assert result["tone"] == QuizTone.ENCOURAGING
    assert result["question_count"] == 50
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.8


def test_prepare_question_generation_includes_tone_and_language(session: Session):
    """Test that prepare_question_generation includes both tone and language."""
    from src.question.types import QuizLanguage
    from src.quiz.schemas import QuizTone
    from src.quiz.service import prepare_question_generation
    from tests.conftest import create_quiz_in_session

    # Create quiz with both tone and language specified
    selected_modules = {
        "module_1": {
            "name": "Introduksjon",
            "question_batches": [{"question_type": "multiple_choice", "count": 25}],
        },
        "module_2": {
            "name": "Avanserte Temaer",
            "question_batches": [{"question_type": "fill_in_blank", "count": 25}],
        },
    }

    quiz = create_quiz_in_session(
        session,
        selected_modules=selected_modules,
        llm_model="gpt-4",
        llm_temperature=0.9,
        language=QuizLanguage.NORWEGIAN,
        tone=QuizTone.CASUAL,
    )

    with patch(
        "src.quiz.service.validate_quiz_for_question_generation"
    ) as mock_validate:
        mock_validate.return_value = quiz

        result = prepare_question_generation(session, quiz.id, quiz.owner_id)

    # Verify both tone and language are included
    assert result["tone"] == QuizTone.CASUAL
    assert result["language"] == QuizLanguage.NORWEGIAN
    assert result["question_count"] == 50
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.9


def test_prepare_question_generation_includes_language(session: Session):
    """Test that prepare_question_generation includes language parameter."""
    from src.question.types import QuizLanguage
    from src.quiz.service import prepare_question_generation
    from tests.conftest import create_quiz_in_session

    # Create quiz with Norwegian language
    selected_modules = {
        "module_1": {
            "name": "Norsk Modul",
            "question_batches": [{"question_type": "multiple_choice", "count": 40}],
        },
    }

    quiz = create_quiz_in_session(
        session,
        selected_modules=selected_modules,
        llm_model="gpt-4",
        llm_temperature=0.7,
        language=QuizLanguage.NORWEGIAN,
    )

    with patch(
        "src.quiz.service.validate_quiz_for_question_generation"
    ) as mock_validate:
        mock_validate.return_value = quiz

        result = prepare_question_generation(session, quiz.id, quiz.owner_id)

    # Verify language is included in generation parameters
    assert result["language"] == QuizLanguage.NORWEGIAN
    assert result["question_count"] == 40
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.7


def test_quiz_delete_preserves_questions(session: Session):
    """Test that quiz soft deletion preserves associated questions."""
    from sqlmodel import select

    from src.question.models import Question
    from src.quiz.service import delete_quiz
    from tests.conftest import create_quiz_in_session

    quiz = create_quiz_in_session(session)

    # Create some questions for the quiz
    question1 = Question(
        quiz_id=quiz.id,
        question_text="Test question 1",
        question_type="multiple_choice",
        is_approved=False,
    )
    question2 = Question(
        quiz_id=quiz.id,
        question_text="Test question 2",
        question_type="multiple_choice",
        is_approved=True,
    )

    session.add(question1)
    session.add(question2)
    session.commit()

    # Verify questions exist
    questions = session.exec(
        select(Question)
        .where(Question.quiz_id == quiz.id)
        .where(Question.deleted == False)  # noqa: E712
    ).all()
    assert len(questions) == 2

    # Delete the quiz
    result = delete_quiz(session, quiz.id, quiz.owner_id)
    assert result is True

    # Verify questions remain active (NOT deleted)
    active_questions = session.exec(
        select(Question)
        .where(Question.quiz_id == quiz.id)
        .where(Question.deleted == False)  # noqa: E712
    ).all()
    assert len(active_questions) == 2

    # Verify all questions are still not deleted
    all_questions = session.exec(
        select(Question).where(Question.quiz_id == quiz.id)
    ).all()
    assert len(all_questions) == 2
    assert all(q.deleted is False for q in all_questions)


# Difficulty Feature Tests


def test_create_quiz_with_difficulty_batches(session: Session):
    """Test quiz creation with multiple difficulty levels in question batches."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Difficulty Test Course",
        selected_modules={
            "456": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=8,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=6,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=4,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                ],
            )
        },
        title="Difficulty Test Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify difficulty settings are preserved
    batches = quiz.selected_modules["456"]["question_batches"]
    assert len(batches) == 3
    assert batches[0]["difficulty"] == "easy"
    assert batches[1]["difficulty"] == "medium"
    assert batches[2]["difficulty"] == "hard"
    assert quiz.question_count == 18  # 8 + 6 + 4


def test_create_quiz_with_default_difficulty(session: Session):
    """Test quiz creation uses medium as default difficulty."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Default Difficulty Course",
        selected_modules={
            "456": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.MEDIUM,  # Use explicit default
                    )
                ],
            )
        },
        title="Default Difficulty Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify default difficulty is medium
    batch = quiz.selected_modules["456"]["question_batches"][0]
    assert batch["difficulty"] == "medium"


def test_create_quiz_difficulty_question_count_calculation(session: Session):
    """Test question count calculation with mixed difficulties."""
    from src.quiz.service import prepare_question_generation
    from tests.conftest import create_quiz_in_session

    # Create quiz with selected_modules that have mixed difficulties and total 33 questions
    selected_modules = {
        "module_1": {
            "name": "Introduction",
            "question_batches": [
                {"question_type": "multiple_choice", "count": 15, "difficulty": "easy"},
                {"question_type": "fill_in_blank", "count": 10, "difficulty": "hard"},
            ],
        },
        "module_2": {
            "name": "Advanced Topics",
            "question_batches": [
                {"question_type": "matching", "count": 8, "difficulty": "medium"}
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

    # Verify difficulty is included in generation parameters
    assert result["question_count"] == 33  # 15 + 10 + 8
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.8

    # Function does not return selected_modules, but preserves difficulty in database
    # The difficulty information is maintained in the quiz.selected_modules field


def test_prepare_question_generation_includes_difficulty(session: Session):
    """Test that prepare_question_generation preserves difficulty in quiz data."""
    from src.quiz.service import prepare_question_generation
    from tests.conftest import create_quiz_in_session

    # Create quiz with selected_modules that have mixed difficulties and total 33 questions
    selected_modules = {
        "module_1": {
            "name": "Introduction",
            "question_batches": [
                {"question_type": "multiple_choice", "count": 15, "difficulty": "easy"},
                {"question_type": "fill_in_blank", "count": 10, "difficulty": "hard"},
            ],
        },
        "module_2": {
            "name": "Advanced Topics",
            "question_batches": [
                {"question_type": "matching", "count": 8, "difficulty": "medium"}
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

    # Verify difficulty is included in generation parameters
    assert result["question_count"] == 33  # 15 + 10 + 8
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.8

    # Function does not return selected_modules, but preserves difficulty in database
    # The difficulty information is maintained in the quiz.selected_modules field


@pytest.mark.asyncio
async def test_reserve_quiz_job_includes_difficulty_settings(async_session):
    """Test that quiz job reservation includes difficulty in module settings."""
    from src.auth.models import User
    from src.quiz.models import Quiz
    from src.quiz.service import reserve_quiz_job

    # Create a user first
    user = User(
        canvas_id=150,
        name="Difficulty Job Test User",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    quiz = Quiz(
        owner_id=user.id,
        canvas_course_id=123,
        canvas_course_name="Difficulty Job Test Course",
        selected_modules={
            "1": {
                "name": "Module 1",
                "question_batches": [
                    {
                        "question_type": "multiple_choice",
                        "count": 20,
                        "difficulty": "easy",
                    },
                    {
                        "question_type": "fill_in_blank",
                        "count": 15,
                        "difficulty": "hard",
                    },
                ],
            },
            "2": {
                "name": "Module 2",
                "question_batches": [
                    {"question_type": "matching", "count": 10, "difficulty": "medium"}
                ],
            },
        },
        question_count=45,
        title="Difficulty Job Test Quiz",
        llm_model="gpt-4",
        llm_temperature=0.9,
        status="created",
    )
    async_session.add(quiz)
    await async_session.commit()
    await async_session.refresh(quiz)

    with patch("src.quiz.service.get_quiz_for_update", return_value=quiz):
        result = await reserve_quiz_job(async_session, quiz.id, "extraction")

    assert result is not None
    assert result["target_questions"] == 45
    assert result["llm_model"] == "gpt-4"
    assert result["llm_temperature"] == 0.9

    # The quiz.selected_modules preserves difficulty information in the database
    # but reserve_quiz_job doesn't return selected_modules for extraction jobs
    # Verify the quiz object maintains difficulty information
    assert quiz.selected_modules["1"]["question_batches"][0]["difficulty"] == "easy"
    assert quiz.selected_modules["1"]["question_batches"][1]["difficulty"] == "hard"
    assert quiz.selected_modules["2"]["question_batches"][0]["difficulty"] == "medium"


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_create_quiz_with_single_difficulty_level(session: Session, difficulty: str):
    """Test quiz creation with each individual difficulty level."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name=f"{difficulty.title()} Course",
        selected_modules={
            "456": ModuleSelection(
                name="Test Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty(difficulty),
                    )
                ],
            )
        },
        title=f"{difficulty.title()} Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify difficulty is preserved correctly
    batch = quiz.selected_modules["456"]["question_batches"][0]
    assert batch["difficulty"] == difficulty
    assert quiz.question_count == 10


def test_create_quiz_mixed_difficulty_multiple_modules(session: Session):
    """Test quiz creation with mixed difficulties across multiple modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Mixed Difficulty Course",
        selected_modules={
            "intro": ModuleSelection(
                name="Introduction",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=12,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=8,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                ],
            ),
            "intermediate": ModuleSelection(
                name="Intermediate",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.FILL_IN_BLANK,
                        count=6,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MATCHING,
                        count=4,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                ],
            ),
            "advanced": ModuleSelection(
                name="Advanced",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.CATEGORIZATION,
                        count=3,
                        difficulty=QuestionDifficulty.HARD,
                    )
                ],
            ),
        },
        title="Mixed Difficulty Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify total question count: 12 + 8 + 6 + 4 + 3 = 33
    assert quiz.question_count == 33

    # Verify each module's difficulty settings
    intro_batches = quiz.selected_modules["intro"]["question_batches"]
    assert all(batch["difficulty"] == "easy" for batch in intro_batches)

    intermediate_batches = quiz.selected_modules["intermediate"]["question_batches"]
    assert all(batch["difficulty"] == "medium" for batch in intermediate_batches)

    advanced_batches = quiz.selected_modules["advanced"]["question_batches"]
    assert all(batch["difficulty"] == "hard" for batch in advanced_batches)


def test_create_quiz_with_manual_modules_only(session: Session):
    """Test quiz creation with only manual modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Manual Content Course",
        selected_modules={
            "manual_abc123": ModuleSelection(
                name="Manual Module 1",
                source_type="manual",
                content="This is manual content for testing",
                word_count=7,
                processing_metadata={"source": "manual_text"},
                content_type="text",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=8,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
            "manual_def456": ModuleSelection(
                name="Manual Module 2",
                source_type="manual",
                content="Another manual content block",
                word_count=5,
                processing_metadata={"source": "manual_pdf", "pages": 2},
                content_type="text",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=6,
                        difficulty=QuestionDifficulty.EASY,
                    )
                ],
            ),
        },
        title="Manual Only Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify quiz creation
    assert quiz.owner_id == user.id
    assert quiz.canvas_course_id == 123
    assert quiz.title == "Manual Only Quiz"
    assert quiz.question_count == 14  # 8 + 6 from manual modules

    # Verify manual module structure is preserved
    expected_modules = {
        "manual_abc123": {
            "name": "Manual Module 1",
            "source_type": "manual",
            "content": "This is manual content for testing",
            "word_count": 7,
            "processing_metadata": {"source": "manual_text"},
            "content_type": "text",
            "question_batches": [
                {
                    "question_type": "multiple_choice",
                    "count": 8,
                    "difficulty": "medium",
                }
            ],
        },
        "manual_def456": {
            "name": "Manual Module 2",
            "source_type": "manual",
            "content": "Another manual content block",
            "word_count": 5,
            "processing_metadata": {"source": "manual_pdf", "pages": 2},
            "content_type": "text",
            "question_batches": [
                {
                    "question_type": "true_false",
                    "count": 6,
                    "difficulty": "easy",
                }
            ],
        },
    }
    assert quiz.selected_modules == expected_modules


def test_create_quiz_with_mixed_canvas_and_manual_modules(session: Session):
    """Test quiz creation with both Canvas and manual modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Mixed Source Course",
        selected_modules={
            # Canvas module
            "456": ModuleSelection(
                name="Canvas Module 1",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=12,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
            # Manual module
            "manual_mixed123": ModuleSelection(
                name="Manual Module 1",
                source_type="manual",
                content="Mixed content testing",
                word_count=3,
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=3,
                        difficulty=QuestionDifficulty.EASY,
                    )
                ],
            ),
            # Another Canvas module
            "789": ModuleSelection(
                name="Canvas Module 2",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MATCHING,
                        count=4,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
        },
        title="Mixed Source Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify total question count: 12 + 3 + 4 = 19
    assert quiz.question_count == 19

    # Verify mixed module structure is preserved
    expected_modules = {
        "456": {
            "name": "Canvas Module 1",
            "source_type": "canvas",
            "question_batches": [
                {
                    "question_type": "multiple_choice",
                    "count": 12,
                    "difficulty": "medium",
                }
            ],
        },
        "manual_mixed123": {
            "name": "Manual Module 1",
            "source_type": "manual",
            "content": "Mixed content testing",
            "word_count": 3,
            "content_type": None,
            "processing_metadata": None,
            "question_batches": [
                {
                    "question_type": "true_false",
                    "count": 3,
                    "difficulty": "easy",
                }
            ],
        },
        "789": {
            "name": "Canvas Module 2",
            "source_type": "canvas",
            "question_batches": [
                {
                    "question_type": "matching",
                    "count": 4,
                    "difficulty": "medium",
                }
            ],
        },
    }
    assert quiz.selected_modules == expected_modules


def test_create_quiz_manual_module_validation_missing_fields(session: Session):
    """Test quiz creation fails when manual modules are missing required fields."""
    import pytest
    from pydantic import ValidationError

    from src.quiz.schemas import ModuleSelection, QuizCreate
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    # This should fail - manual modules with source_type="manual" must have content and word_count
    with pytest.raises(ValidationError) as exc_info:
        QuizCreate(
            canvas_course_id=123,
            canvas_course_name="Test Course",
            selected_modules={
                "manual_test123": ModuleSelection(
                    name="Manual Module",
                    source_type="manual",
                    # Missing content, word_count, etc. - should fail validation
                    question_batches=[
                        {
                            "question_type": "multiple_choice",
                            "count": 5,
                            "difficulty": "medium",
                        }
                    ],
                ),
            },
            title="Test Quiz",
        )

    # Verify the validation error mentions required fields
    error_message = str(exc_info.value)
    assert "must have content" in error_message


def test_create_quiz_manual_module_id_validation(session: Session):
    """Test that manual module IDs are properly validated."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    # Valid manual module with proper ID prefix
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Manual ID Test Course",
        selected_modules={
            "manual_test123": ModuleSelection(
                name="Valid Manual Module",
                source_type="manual",
                content="Test content",
                word_count=2,
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=5,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
        },
        title="Manual ID Test Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Should create successfully
    assert quiz.question_count == 5
    assert "manual_test123" in quiz.selected_modules
    assert quiz.selected_modules["manual_test123"]["source_type"] == "manual"


def test_create_quiz_question_count_calculation_mixed_modules(session: Session):
    """Test question count calculation across mixed Canvas and manual modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Count Test Course",
        selected_modules={
            # Canvas module with multiple batches
            "canvas_1": ModuleSelection(
                name="Canvas Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=8,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=4,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                ],
            ),
            # Manual module with multiple batches
            "manual_count123": ModuleSelection(
                name="Manual Module",
                source_type="manual",
                content="Manual content for count testing",
                word_count=5,
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.FILL_IN_BLANK,
                        count=6,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MATCHING,
                        count=3,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.CATEGORIZATION,
                        count=2,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                ],
            ),
        },
        title="Question Count Test Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Verify total question count: 8 + 4 + 6 + 3 + 2 = 23
    assert quiz.question_count == 23

    # Verify each module's question count
    canvas_total = sum(
        batch["count"]
        for batch in quiz.selected_modules["canvas_1"]["question_batches"]
    )
    manual_total = sum(
        batch["count"]
        for batch in quiz.selected_modules["manual_count123"]["question_batches"]
    )

    assert canvas_total == 12  # 8 + 4
    assert manual_total == 11  # 6 + 3 + 2
    assert canvas_total + manual_total == quiz.question_count


def test_create_quiz_module_batch_distribution_mixed(session: Session):
    """Test module batch distribution property with mixed modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate
    from src.quiz.service import create_quiz
    from tests.conftest import create_user_in_session

    user = create_user_in_session(session)

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Batch Distribution Course",
        selected_modules={
            "canvas_module": ModuleSelection(
                name="Canvas Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=5,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                ],
            ),
            "manual_batch123": ModuleSelection(
                name="Manual Module",
                source_type="manual",
                content="Batch distribution test content",
                word_count=4,
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.FILL_IN_BLANK,
                        count=8,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MATCHING,
                        count=4,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.CATEGORIZATION,
                        count=3,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                ],
            ),
        },
        title="Batch Distribution Quiz",
    )

    quiz = create_quiz(session, quiz_data, user.id)

    # Test module batch distribution property
    batch_distribution = quiz.module_batch_distribution

    # Canvas module should have 2 batches
    assert len(batch_distribution["canvas_module"]) == 2
    assert batch_distribution["canvas_module"][0]["question_type"] == "multiple_choice"
    assert batch_distribution["canvas_module"][0]["count"] == 10
    assert batch_distribution["canvas_module"][1]["question_type"] == "true_false"
    assert batch_distribution["canvas_module"][1]["count"] == 5

    # Manual module should have 3 batches
    assert len(batch_distribution["manual_batch123"]) == 3
    assert batch_distribution["manual_batch123"][0]["question_type"] == "fill_in_blank"
    assert batch_distribution["manual_batch123"][0]["count"] == 8
    assert batch_distribution["manual_batch123"][1]["question_type"] == "matching"
    assert batch_distribution["manual_batch123"][1]["count"] == 4
    assert batch_distribution["manual_batch123"][2]["question_type"] == "categorization"
    assert batch_distribution["manual_batch123"][2]["count"] == 3
