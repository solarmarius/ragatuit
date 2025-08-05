"""Tests for question edit logging functionality."""

import uuid

import pytest

from tests.test_data import DEFAULT_FILL_IN_BLANK_DATA, DEFAULT_MCQ_DATA


def test_generate_edit_log_entries_with_changes():
    """Test edit log generation with field changes."""
    from src.question.utils import generate_edit_log_entries

    old_data = {
        "question_text": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        "correct_answer": "B",
    }

    new_data = {
        "question_text": "What is 2+2 exactly?",  # Changed
        "option_a": "3",  # Same
        "option_b": "4",  # Same
        "correct_answer": "A",  # Changed
        "explanation": "Basic math",  # New field
    }

    entries = generate_edit_log_entries(old_data, new_data)

    assert len(entries) == 3

    # Check question_text change
    question_text_entry = next(e for e in entries if e["field"] == "question_text")
    assert question_text_entry["old_value"] == "What is 2+2?"
    assert question_text_entry["new_value"] == "What is 2+2 exactly?"

    # Check correct_answer change
    answer_entry = next(e for e in entries if e["field"] == "correct_answer")
    assert answer_entry["old_value"] == "B"
    assert answer_entry["new_value"] == "A"

    # Check new field addition
    explanation_entry = next(e for e in entries if e["field"] == "explanation")
    assert explanation_entry["old_value"] is None
    assert explanation_entry["new_value"] == "Basic math"


def test_generate_edit_log_entries_no_changes():
    """Test edit log generation with no changes."""
    from src.question.utils import generate_edit_log_entries

    data = {
        "question_text": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        "correct_answer": "B",
    }

    entries = generate_edit_log_entries(data, data)
    assert entries == []


def test_generate_edit_log_entries_field_removal():
    """Test edit log generation when fields are removed."""
    from src.question.utils import generate_edit_log_entries

    old_data = {
        "question_text": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        "explanation": "Math question",
    }

    new_data = {
        "question_text": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        # explanation removed
    }

    entries = generate_edit_log_entries(old_data, new_data)

    assert len(entries) == 1
    explanation_entry = entries[0]
    assert explanation_entry["field"] == "explanation"
    assert explanation_entry["old_value"] == "Math question"
    assert explanation_entry["new_value"] is None


def test_generate_edit_log_entries_empty_dictionaries():
    """Test edit log generation with empty dictionaries."""
    from src.question.utils import generate_edit_log_entries

    # Both empty
    entries = generate_edit_log_entries({}, {})
    assert entries == []

    # One empty
    entries = generate_edit_log_entries({}, {"field": "value"})
    assert len(entries) == 1
    assert entries[0]["field"] == "field"
    assert entries[0]["old_value"] is None
    assert entries[0]["new_value"] == "value"


def test_generate_edit_log_entries_nested_values():
    """Test edit log generation with nested dictionary values."""
    from src.question.utils import generate_edit_log_entries

    old_data = {
        "question_text": "Test",
        "metadata": {"difficulty": "easy", "tags": ["math"]},
    }

    new_data = {
        "question_text": "Test",
        "metadata": {"difficulty": "hard", "tags": ["math", "algebra"]},
    }

    entries = generate_edit_log_entries(old_data, new_data)

    assert len(entries) == 1
    metadata_entry = entries[0]
    assert metadata_entry["field"] == "metadata"
    assert metadata_entry["old_value"] == {"difficulty": "easy", "tags": ["math"]}
    assert metadata_entry["new_value"] == {
        "difficulty": "hard",
        "tags": ["math", "algebra"],
    }


@pytest.mark.asyncio
async def test_update_question_logs_question_data_changes(async_session):
    """Test that question_data updates are logged."""
    from src.question.service import update_question
    from tests.conftest import create_quiz_in_async_session

    # Create test quiz and question
    quiz = await create_quiz_in_async_session(async_session)

    # Create a question manually with initial data
    from src.question.models import Question, QuestionType

    initial_question_data = DEFAULT_MCQ_DATA.copy()
    question = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data=initial_question_data,
        edit_log=[],  # Start with empty edit log
    )
    async_session.add(question)
    await async_session.commit()
    await async_session.refresh(question)

    # Update question data
    updated_question_data = initial_question_data.copy()
    updated_question_data["question_text"] = "Updated question text"
    updated_question_data["option_a"] = "Updated option A"

    updates = {"question_data": updated_question_data}

    # Call update function
    result = await update_question(async_session, question.id, updates)

    assert result is not None
    assert result.edit_log is not None
    assert len(result.edit_log) == 2

    # Check logged changes
    logged_fields = {entry["field"] for entry in result.edit_log}
    assert "question_text" in logged_fields
    assert "option_a" in logged_fields

    # Check specific values
    question_text_entry = next(
        e for e in result.edit_log if e["field"] == "question_text"
    )
    assert question_text_entry["old_value"] == DEFAULT_MCQ_DATA["question_text"]
    assert question_text_entry["new_value"] == "Updated question text"


@pytest.mark.asyncio
async def test_update_question_appends_to_existing_edit_log(async_session):
    """Test that new edits are appended to existing edit log."""
    from src.question.service import update_question
    from tests.conftest import create_quiz_in_async_session

    # Create test quiz and question with existing edit log
    quiz = await create_quiz_in_async_session(async_session)

    from src.question.models import Question, QuestionType

    initial_question_data = DEFAULT_MCQ_DATA.copy()
    existing_edit_log = [
        {"field": "previous_field", "old_value": "old", "new_value": "new"}
    ]

    question = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data=initial_question_data,
        edit_log=existing_edit_log,
    )
    async_session.add(question)
    await async_session.commit()
    await async_session.refresh(question)

    # Update question data
    updated_question_data = initial_question_data.copy()
    updated_question_data["question_text"] = "Another update"

    updates = {"question_data": updated_question_data}

    # Call update function
    result = await update_question(async_session, question.id, updates)

    assert result is not None
    assert len(result.edit_log) == 2  # 1 existing + 1 new

    # Check that existing entry is preserved
    assert result.edit_log[0] == existing_edit_log[0]

    # Check new entry
    new_entry = result.edit_log[1]
    assert new_entry["field"] == "question_text"
    assert new_entry["old_value"] == DEFAULT_MCQ_DATA["question_text"]
    assert new_entry["new_value"] == "Another update"


@pytest.mark.asyncio
async def test_update_question_no_question_data_change_no_logging(async_session):
    """Test that non-question_data updates don't trigger edit logging."""
    from src.question.service import update_question
    from tests.conftest import create_quiz_in_async_session

    # Create test quiz and question
    quiz = await create_quiz_in_async_session(async_session)

    from src.question.models import Question, QuestionDifficulty, QuestionType

    question = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data=DEFAULT_MCQ_DATA.copy(),
        difficulty=QuestionDifficulty.EASY,
        edit_log=[],
    )
    async_session.add(question)
    await async_session.commit()
    await async_session.refresh(question)

    # Update only difficulty (not question_data)
    updates = {"difficulty": QuestionDifficulty.HARD}

    # Call update function
    result = await update_question(async_session, question.id, updates)

    assert result is not None
    assert result.difficulty == QuestionDifficulty.HARD
    assert result.edit_log == []  # Should remain empty


@pytest.mark.asyncio
async def test_update_question_no_actual_changes_no_logging(async_session):
    """Test that updates with no actual changes don't add log entries."""
    from src.question.service import update_question
    from tests.conftest import create_quiz_in_async_session

    # Create test quiz and question
    quiz = await create_quiz_in_async_session(async_session)

    from src.question.models import Question, QuestionType

    initial_data = DEFAULT_MCQ_DATA.copy()
    question = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data=initial_data,
        edit_log=[],
    )
    async_session.add(question)
    await async_session.commit()
    await async_session.refresh(question)

    # Update with same data
    updates = {"question_data": initial_data.copy()}

    # Call update function
    result = await update_question(async_session, question.id, updates)

    assert result is not None
    assert result.edit_log == []  # Should remain empty since no changes


@pytest.mark.asyncio
async def test_update_question_handles_null_question_data(async_session):
    """Test that update handles null question_data gracefully."""
    from src.question.service import update_question
    from tests.conftest import create_quiz_in_async_session

    # Create test quiz and question with null question_data
    quiz = await create_quiz_in_async_session(async_session)

    from src.question.models import Question, QuestionType

    question = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data=None,  # Start with null
        edit_log=None,  # Start with null
    )
    async_session.add(question)
    await async_session.commit()
    await async_session.refresh(question)

    # Update with actual data
    new_data = DEFAULT_MCQ_DATA.copy()
    updates = {"question_data": new_data}

    # Call update function
    result = await update_question(async_session, question.id, updates)

    assert result is not None
    assert result.question_data == new_data
    assert result.edit_log is not None

    # Should log all fields as new (old_value = None)
    assert len(result.edit_log) == len(new_data)
    for entry in result.edit_log:
        assert entry["old_value"] is None
        assert entry["field"] in new_data
        assert entry["new_value"] == new_data[entry["field"]]


@pytest.mark.asyncio
async def test_update_question_with_different_question_types(async_session):
    """Test edit logging works with different question types."""
    from src.question.service import update_question
    from tests.conftest import create_quiz_in_async_session

    # Test with Fill-in-Blank question type
    quiz = await create_quiz_in_async_session(async_session)

    from src.question.models import Question, QuestionType

    initial_data = DEFAULT_FILL_IN_BLANK_DATA.copy()
    question = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.FILL_IN_BLANK,
        question_data=initial_data,
        edit_log=[],
    )
    async_session.add(question)
    await async_session.commit()
    await async_session.refresh(question)

    # Update fill-in-blank specific data
    updated_data = initial_data.copy()
    updated_data["question_text"] = "Updated fill-in-blank question"
    updated_data["correct_answers"] = ["updated", "answer"]

    updates = {"question_data": updated_data}

    # Call update function
    result = await update_question(async_session, question.id, updates)

    assert result is not None
    assert len(result.edit_log) == 2

    # Check logged changes specific to fill-in-blank
    logged_fields = {entry["field"] for entry in result.edit_log}
    assert "question_text" in logged_fields
    assert "correct_answers" in logged_fields


@pytest.mark.asyncio
async def test_update_nonexistent_question_returns_none(async_session):
    """Test that updating nonexistent question returns None."""
    from src.question.service import update_question

    nonexistent_id = uuid.uuid4()
    updates = {"question_data": {"test": "data"}}

    result = await update_question(async_session, nonexistent_id, updates)
    assert result is None


@pytest.mark.asyncio
async def test_edit_log_persists_after_question_deletion(async_session):
    """Test that edit logs are preserved when questions are soft deleted."""
    from src.question.service import delete_question, update_question
    from tests.conftest import (
        create_quiz_in_async_session,
        create_user_in_async_session,
    )

    # Create test data
    user = await create_user_in_async_session(async_session)
    quiz = await create_quiz_in_async_session(async_session, owner=user)

    # Store IDs early to avoid session access issues
    user_id = user.id
    quiz_id = quiz.id

    from src.question.models import Question, QuestionType

    question = Question(
        quiz_id=quiz_id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data=DEFAULT_MCQ_DATA.copy(),
        edit_log=[],
    )
    async_session.add(question)
    await async_session.commit()
    await async_session.refresh(question)

    # Store question ID early too
    question_id = question.id

    # Make an edit to generate log entry
    updated_data = DEFAULT_MCQ_DATA.copy()
    updated_data["question_text"] = "Modified before deletion"

    result = await update_question(
        async_session, question_id, {"question_data": updated_data}
    )
    assert result is not None
    assert len(result.edit_log) == 1

    # Soft delete the question
    delete_success = await delete_question(async_session, question_id, user_id)
    assert delete_success is True

    # Verify edit log is preserved in soft-deleted question
    from src.question.service import get_question_by_id

    deleted_question = await get_question_by_id(
        async_session, question_id, include_deleted=True
    )
    assert deleted_question is not None
    assert deleted_question.deleted is True
    assert deleted_question.edit_log is not None
    assert len(deleted_question.edit_log) == 1
    assert deleted_question.edit_log[0]["field"] == "question_text"


@pytest.mark.asyncio
async def test_edit_log_accumulates_over_multiple_updates(async_session):
    """Test that edit log accumulates changes over multiple updates."""
    from src.question.service import update_question
    from tests.conftest import create_quiz_in_async_session

    # Create test quiz and question
    quiz = await create_quiz_in_async_session(async_session)

    from src.question.models import Question, QuestionType

    initial_data = DEFAULT_MCQ_DATA.copy()
    question = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data=initial_data,
        edit_log=[],
    )
    async_session.add(question)
    await async_session.commit()
    await async_session.refresh(question)

    # First update - change question text
    updated_data_1 = initial_data.copy()
    updated_data_1["question_text"] = "First update"

    result_1 = await update_question(
        async_session, question.id, {"question_data": updated_data_1}
    )
    assert len(result_1.edit_log) == 1
    assert result_1.edit_log[0]["field"] == "question_text"

    # Second update - change option_a
    updated_data_2 = updated_data_1.copy()
    updated_data_2["option_a"] = "Updated option A"

    result_2 = await update_question(
        async_session, question.id, {"question_data": updated_data_2}
    )
    assert len(result_2.edit_log) == 2

    # Check both entries are present
    logged_fields = {entry["field"] for entry in result_2.edit_log}
    assert "question_text" in logged_fields
    assert "option_a" in logged_fields

    # Third update - change question text again
    updated_data_3 = updated_data_2.copy()
    updated_data_3["question_text"] = "Second question text update"

    result_3 = await update_question(
        async_session, question.id, {"question_data": updated_data_3}
    )
    assert len(result_3.edit_log) == 3

    # Check that question_text appears twice with different old values
    question_text_changes = [
        entry for entry in result_3.edit_log if entry["field"] == "question_text"
    ]
    assert len(question_text_changes) == 2

    # First change should be from original to "First update"
    first_change = next(
        entry
        for entry in question_text_changes
        if entry["old_value"] == initial_data["question_text"]
    )
    assert first_change["new_value"] == "First update"

    # Second change should be from "First update" to "Second question text update"
    second_change = next(
        entry for entry in question_text_changes if entry["old_value"] == "First update"
    )
    assert second_change["new_value"] == "Second question text update"
