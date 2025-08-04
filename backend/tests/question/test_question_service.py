"""Tests for question service layer."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.test_data import (
    DEFAULT_FILL_IN_BLANK_DATA,
    DEFAULT_MCQ_DATA,
    SAMPLE_QUESTIONS_BATCH,
)


@pytest.mark.asyncio
async def test_save_questions_success(async_session):
    """Test successful question saving."""
    from src.question.models import QuestionType
    from src.question.service import save_questions
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id
    question_type = QuestionType.MULTIPLE_CHOICE

    questions_data = [
        {
            **SAMPLE_QUESTIONS_BATCH[0],
            "correct_answer": "B",
            "explanation": SAMPLE_QUESTIONS_BATCH[0]["explanation"],
        },
        {
            **SAMPLE_QUESTIONS_BATCH[1],
            "correct_answer": "C",
            "explanation": SAMPLE_QUESTIONS_BATCH[1]["explanation"],
        },
    ]

    # Mock question registry and validation
    mock_question_data = MagicMock()
    mock_question_data.dict.return_value = {"validated": "data"}

    mock_question_impl = MagicMock()
    mock_question_impl.validate_data.return_value = mock_question_data

    mock_registry = MagicMock()
    mock_registry.get_question_type.return_value = mock_question_impl

    with patch(
        "src.question.service.get_question_type_registry", return_value=mock_registry
    ):
        result = await save_questions(
            async_session, quiz_id, question_type, questions_data
        )

    assert result["success"] is True
    assert result["saved_count"] == 2
    assert result["total_count"] == 2
    assert len(result["question_ids"]) == 2
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_save_questions_with_validation_errors(async_session):
    """Test question saving with validation errors."""
    from src.question.models import QuestionType
    from src.question.service import save_questions
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id
    question_type = QuestionType.MULTIPLE_CHOICE

    questions_data = [{"invalid": "data"}, {"also_invalid": "data"}]

    # Mock question registry to raise validation errors
    mock_question_impl = MagicMock()
    mock_question_impl.validate_data.side_effect = ValueError("Invalid question data")

    mock_registry = MagicMock()
    mock_registry.get_question_type.return_value = mock_question_impl

    with patch(
        "src.question.service.get_question_type_registry", return_value=mock_registry
    ):
        result = await save_questions(
            async_session, quiz_id, question_type, questions_data
        )

    assert result["success"] is False
    assert result["saved_count"] == 0
    assert result["total_count"] == 2
    assert len(result["errors"]) == 2
    assert "Question 1: Invalid question data" in result["errors"]
    assert "Question 2: Invalid question data" in result["errors"]


@pytest.mark.asyncio
async def test_save_questions_partial_success(async_session):
    """Test question saving with partial success."""
    from src.question.models import QuestionType
    from src.question.service import save_questions
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id
    question_type = QuestionType.MULTIPLE_CHOICE

    questions_data = [
        {"valid": "question_1"},
        {"invalid": "question_2"},
        {"valid": "question_3"},
    ]

    # Mock question registry with mixed validation results
    mock_question_data = MagicMock()
    mock_question_data.dict.return_value = {"validated": "data"}

    mock_question_impl = MagicMock()

    def validate_side_effect(data):
        if "invalid" in str(data):
            raise ValueError("Invalid data")
        return mock_question_data

    mock_question_impl.validate_data.side_effect = validate_side_effect

    mock_registry = MagicMock()
    mock_registry.get_question_type.return_value = mock_question_impl

    with patch(
        "src.question.service.get_question_type_registry", return_value=mock_registry
    ):
        result = await save_questions(
            async_session, quiz_id, question_type, questions_data
        )

    # Should fail because ANY validation error causes complete failure
    assert result["success"] is False
    assert result["saved_count"] == 0
    assert len(result["errors"]) == 1


@pytest.mark.asyncio
async def test_save_questions_empty_list(async_session):
    """Test saving empty questions list."""
    from src.question.models import QuestionType
    from src.question.service import save_questions
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id
    question_type = QuestionType.MULTIPLE_CHOICE

    with patch("src.question.service.get_question_type_registry"):
        result = await save_questions(async_session, quiz_id, question_type, [])

    assert result["success"] is True
    assert result["saved_count"] == 0
    assert result["total_count"] == 0
    assert result["question_ids"] == []


@pytest.mark.asyncio
async def test_get_questions_by_quiz_basic(async_session):
    """Test basic question retrieval."""
    from src.question.models import Question, QuestionType
    from src.question.service import get_questions_by_quiz
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id

    # Create mock questions
    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={
                **DEFAULT_MCQ_DATA,
                "question_text": SAMPLE_QUESTIONS_BATCH[0]["question_text"],
            },
            is_approved=False,
        ),
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.FILL_IN_BLANK,
            question_data={**DEFAULT_FILL_IN_BLANK_DATA, "question_text": "Test 2"},
            is_approved=True,
        ),
    ]

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = questions
    async_session.execute = AsyncMock(return_value=mock_result)

    result = await get_questions_by_quiz(async_session, quiz_id)

    assert len(result) == 2
    assert (
        result[0].question_data["question_text"]
        == SAMPLE_QUESTIONS_BATCH[0]["question_text"]
    )
    assert result[1].question_data["question_text"] == "Test 2"


@pytest.mark.asyncio
async def test_get_questions_by_quiz_with_filters(async_session):
    """Test question retrieval with filters."""
    from src.question.models import Question, QuestionType
    from src.question.service import get_questions_by_quiz
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id

    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={"question_text": "MC Question"},
            is_approved=True,
        )
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = questions
    async_session.execute = AsyncMock(return_value=mock_result)

    # Test with question type filter
    result = await get_questions_by_quiz(
        async_session,
        quiz_id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        approved_only=True,
    )

    assert len(result) == 1
    assert result[0].question_type == QuestionType.MULTIPLE_CHOICE
    async_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_questions_by_quiz_with_pagination(async_session):
    """Test question retrieval with pagination."""
    from src.question.models import Question, QuestionType
    from src.question.service import get_questions_by_quiz
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id

    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={"question_text": "Question 1"},
        )
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = questions
    async_session.execute = AsyncMock(return_value=mock_result)

    result = await get_questions_by_quiz(async_session, quiz_id, limit=10, offset=5)

    assert len(result) == 1
    async_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_questions_by_quiz_empty_result(async_session):
    """Test question retrieval with no results."""
    from src.question.service import get_questions_by_quiz
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    async_session.execute = AsyncMock(return_value=mock_result)

    result = await get_questions_by_quiz(async_session, quiz_id)

    assert result == []


@pytest.mark.asyncio
async def test_get_formatted_questions_success(async_session):
    """Test successful formatted question retrieval."""
    from src.question.models import Question, QuestionType
    from src.question.service import get_formatted_questions_by_quiz
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id

    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={"question_text": "Formatted question"},
            is_approved=True,
        )
    ]

    formatted_questions = [
        {
            "id": str(questions[0].id),
            "question_text": "Formatted question",
            "type": "multiple_choice",
            "is_approved": True,
        }
    ]

    with (
        patch("src.question.service.get_questions_by_quiz", return_value=questions),
        patch(
            "src.question.service.format_questions_batch",
            return_value=formatted_questions,
        ),
    ):
        result = await get_formatted_questions_by_quiz(async_session, quiz_id)

    assert len(result) == 1
    assert result[0]["question_text"] == "Formatted question"
    assert result[0]["type"] == "multiple_choice"


@pytest.mark.asyncio
async def test_get_formatted_questions_with_filters(async_session):
    """Test formatted question retrieval with filters."""
    from src.question.models import QuestionType
    from src.question.service import get_formatted_questions_by_quiz
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id

    with (
        patch("src.question.service.get_questions_by_quiz", return_value=[]),
        patch("src.question.service.format_questions_batch", return_value=[]),
    ):
        result = await get_formatted_questions_by_quiz(
            async_session,
            quiz_id,
            question_type=QuestionType.FILL_IN_BLANK,
            approved_only=True,
            limit=5,
            offset=2,
        )

    assert result == []


@pytest.mark.asyncio
async def test_get_question_by_id_success(async_session):
    """Test successful question retrieval by ID."""
    from src.question.models import Question, QuestionType
    from src.question.service import get_question_by_id

    question_id = uuid.uuid4()
    question = Question(
        id=question_id,
        quiz_id=uuid.uuid4(),
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data={"question_text": "Test question"},
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = question
    async_session.execute = AsyncMock(return_value=mock_result)

    result = await get_question_by_id(async_session, question_id)

    assert result == question
    assert result.id == question_id


@pytest.mark.asyncio
async def test_get_question_by_id_not_found(async_session):
    """Test question retrieval when not found."""
    from src.question.service import get_question_by_id

    question_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    async_session.execute = AsyncMock(return_value=mock_result)

    result = await get_question_by_id(async_session, question_id)

    assert result is None


@pytest.mark.asyncio
async def test_approve_question_success(async_session):
    """Test successful question approval."""
    from src.question.service import approve_question
    from tests.conftest import create_question_in_async_session

    # Create a question in the database with proper foreign key relationships
    question = await create_question_in_async_session(
        async_session, is_approved=False, approved_at=None
    )

    result = await approve_question(async_session, question.id)

    assert result is not None
    assert result.id == question.id
    assert result.is_approved is True
    assert result.approved_at is not None
    assert result.updated_at is not None


@pytest.mark.asyncio
async def test_approve_question_not_found(async_session):
    """Test question approval when question not found."""
    from src.question.service import approve_question

    question_id = uuid.uuid4()

    with patch("src.question.service.get_question_by_id", return_value=None):
        result = await approve_question(async_session, question_id)

    assert result is None


@pytest.mark.asyncio
async def test_approve_question_already_approved(async_session):
    """Test approving an already approved question."""
    from src.question.service import approve_question
    from tests.conftest import create_question_in_async_session

    # Create a question in the database that's already approved
    original_approved_at = datetime.now(timezone.utc)
    question = await create_question_in_async_session(
        async_session, is_approved=True, approved_at=original_approved_at
    )

    result = await approve_question(async_session, question.id)

    assert result is not None
    assert result.id == question.id
    assert result.is_approved is True
    # Should update approved_at even if already approved
    assert result.approved_at != original_approved_at


@pytest.mark.asyncio
async def test_update_question_success(async_session):
    """Test successful question update."""
    from src.question.models import QuestionDifficulty
    from src.question.service import update_question
    from tests.conftest import create_question_in_async_session

    # Create a question in the database with proper foreign key relationships
    question = await create_question_in_async_session(
        async_session,
        question_data={"question_text": "Original question"},
        difficulty=QuestionDifficulty.EASY,
    )

    updates = {
        "question_data": {"question_text": "Updated question"},
        "difficulty": QuestionDifficulty.HARD,
    }

    result = await update_question(async_session, question.id, updates)

    assert result is not None
    assert result.id == question.id
    assert result.question_data == {"question_text": "Updated question"}
    assert result.difficulty == QuestionDifficulty.HARD
    assert result.updated_at is not None


@pytest.mark.asyncio
async def test_update_question_not_found(async_session):
    """Test question update when question not found."""
    from src.question.models import QuestionDifficulty
    from src.question.service import update_question

    question_id = uuid.uuid4()
    updates = {"difficulty": QuestionDifficulty.HARD}

    with patch("src.question.service.get_question_by_id", return_value=None):
        result = await update_question(async_session, question_id, updates)

    assert result is None


@pytest.mark.asyncio
async def test_update_question_invalid_field(async_session):
    """Test question update with invalid field."""
    from src.question.service import update_question
    from tests.conftest import create_question_in_async_session

    # Create a question in the database with proper foreign key relationships
    question = await create_question_in_async_session(
        async_session, question_data={"question_text": "Test question"}
    )

    updates = {
        "question_data": {"question_text": "Updated question"},
        "invalid_field": "should_be_ignored",
    }

    result = await update_question(async_session, question.id, updates)

    # Should only update valid fields
    assert result is not None
    assert result.id == question.id
    assert result.question_data == {"question_text": "Updated question"}
    assert not hasattr(result, "invalid_field")


@pytest.mark.asyncio
async def test_delete_question_success(async_session):
    """Test successful question deletion."""
    from src.question.service import delete_question

    question_id = uuid.uuid4()
    quiz_owner_id = uuid.uuid4()

    # Mock a question for the delete query response
    mock_question = MagicMock()
    mock_question.id = question_id
    mock_question.deleted = False  # Not yet soft-deleted

    # Mock the join query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_question
    async_session.execute = AsyncMock(return_value=mock_result)
    async_session.add = MagicMock()  # For soft delete
    async_session.commit = AsyncMock()

    result = await delete_question(async_session, question_id, quiz_owner_id)

    assert result is True
    # Verify soft delete was performed (not hard delete)
    async_session.add.assert_called_once_with(mock_question)
    async_session.commit.assert_called_once()
    # Verify question was marked as deleted
    assert mock_question.deleted is True
    assert mock_question.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_question_not_found_or_unauthorized(async_session):
    """Test question deletion when not found or unauthorized."""
    from src.question.service import delete_question

    question_id = uuid.uuid4()
    quiz_owner_id = uuid.uuid4()

    # Mock empty query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    async_session.execute = AsyncMock(return_value=mock_result)
    async_session.delete = MagicMock()

    result = await delete_question(async_session, question_id, quiz_owner_id)

    assert result is False
    async_session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_prepare_questions_for_export_success():
    """Test successful question export preparation."""
    from src.question.models import Question, QuestionType
    from src.question.service import prepare_questions_for_export

    quiz_id = uuid.uuid4()

    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={
                "question_text": "What is 2+2?",
                "option_a": "3",
                "option_b": "4",
                "option_c": "5",
                "option_d": "6",
                "correct_answer": "B",
            },
            is_approved=True,
        )
    ]

    # Create proper MultipleChoiceData instance
    from src.question.types.mcq import MultipleChoiceData

    mock_mcq_data = MultipleChoiceData(
        question_text="What is 2+2?",
        option_a="3",
        option_b="4",
        option_c="5",
        option_d="6",
        correct_answer="B",
    )

    # Mock question.get_typed_data to return the mock data
    for question in questions:
        object.__setattr__(
            question, "get_typed_data", MagicMock(return_value=mock_mcq_data)
        )

    with (
        patch("src.database.get_async_session") as mock_get_session,
        patch("src.question.service.get_questions_by_quiz", return_value=questions),
        patch("src.question.service.get_question_type_registry"),
    ):
        # Mock the async context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await prepare_questions_for_export(quiz_id)

    assert len(result) == 1
    assert result[0]["question_text"] == "What is 2+2?"
    assert result[0]["option_a"] == "3"
    assert result[0]["option_b"] == "4"
    assert result[0]["correct_answer"] == "B"


@pytest.mark.asyncio
async def test_prepare_questions_for_export_no_approved_questions():
    """Test export preparation with no approved questions."""
    from src.question.service import prepare_questions_for_export

    quiz_id = uuid.uuid4()

    with (
        patch("src.database.get_async_session") as mock_get_session,
        patch("src.question.service.get_questions_by_quiz", return_value=[]),
    ):
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await prepare_questions_for_export(quiz_id)

    assert result == []


@pytest.mark.asyncio
async def test_update_question_canvas_ids_success(async_session):
    """Test successful Canvas ID updates."""
    from src.question.models import Question, QuestionType
    from src.question.service import update_question_canvas_ids

    question_id_1 = uuid.uuid4()
    question_id_2 = uuid.uuid4()

    question_data_list = [{"id": question_id_1}, {"id": question_id_2}]

    export_results = [
        {"success": True, "item_id": "canvas_item_1"},
        {"success": True, "item_id": "canvas_item_2"},
    ]

    # Mock questions as simple objects with just the attributes we need
    question_1 = MagicMock()
    question_1.id = question_id_1
    question_1.canvas_item_id = None

    question_2 = MagicMock()
    question_2.id = question_id_2
    question_2.canvas_item_id = None

    # Mock session.get to return questions
    async_session.get = AsyncMock(side_effect=[question_1, question_2])

    await update_question_canvas_ids(async_session, question_data_list, export_results)

    assert question_1.canvas_item_id == "canvas_item_1"
    assert question_2.canvas_item_id == "canvas_item_2"


@pytest.mark.asyncio
async def test_update_question_canvas_ids_with_failures(async_session):
    """Test Canvas ID updates with some failures."""
    from src.question.models import Question, QuestionType
    from src.question.service import update_question_canvas_ids

    question_id_1 = uuid.uuid4()
    question_id_2 = uuid.uuid4()

    question_data_list = [{"id": question_id_1}, {"id": question_id_2}]

    export_results = [
        {"success": True, "item_id": "canvas_item_1"},
        {"success": False, "error": "Export failed"},
    ]

    # Mock question as simple object with just the attributes we need
    question_1 = MagicMock()
    question_1.id = question_id_1
    question_1.canvas_item_id = None

    # Only first question should be retrieved since second failed
    async_session.get = AsyncMock(return_value=question_1)

    await update_question_canvas_ids(async_session, question_data_list, export_results)

    assert question_1.canvas_item_id == "canvas_item_1"
    # Only one call to session.get for successful export
    async_session.get.assert_called_once_with(Question, question_id_1)


@pytest.mark.asyncio
async def test_update_question_canvas_ids_question_not_found(async_session):
    """Test Canvas ID update when question not found."""
    from src.question.models import Question
    from src.question.service import update_question_canvas_ids

    question_data_list = [{"id": uuid.uuid4()}]
    export_results = [{"success": True, "item_id": "canvas_item_1"}]

    # Mock session.get to return None (question not found)
    async_session.get = AsyncMock(return_value=None)

    # Should handle gracefully without error
    await update_question_canvas_ids(async_session, question_data_list, export_results)

    async_session.get.assert_called_once()


@pytest.mark.asyncio
async def test_question_lifecycle_save_to_export(async_session):
    """Test complete question lifecycle from save to export."""
    from src.question.models import Question, QuestionType
    from src.question.service import (
        approve_question,
        prepare_questions_for_export,
        save_questions,
    )
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id
    question_type = QuestionType.MULTIPLE_CHOICE

    # 1. Save questions
    questions_data = [
        {
            "question_text": "Integration test question",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "correct_answer": "B",
        }
    ]

    # Mock successful save
    with patch("src.question.service.get_question_type_registry") as mock_registry:
        mock_data = MagicMock()
        mock_data.dict.return_value = {"validated": "data"}
        mock_impl = MagicMock()
        mock_impl.validate_data.return_value = mock_data
        mock_registry.return_value.get_question_type.return_value = mock_impl

        save_result = await save_questions(
            async_session, quiz_id, question_type, questions_data
        )

    assert save_result["success"] is True
    assert len(save_result["question_ids"]) > 0

    # 2. Get the actual question from the database
    question_id = uuid.UUID(save_result["question_ids"][0])

    # Get the question from the database for approval
    from src.question.service import get_question_by_id

    question = await get_question_by_id(async_session, question_id)

    # 3. Approve question
    approved_question = await approve_question(async_session, question_id)

    assert approved_question.is_approved is True

    # 4. Prepare for export
    from src.question.types.mcq import MultipleChoiceData

    mock_mcq_data = MultipleChoiceData(
        question_text="Integration test question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="B",
    )
    object.__setattr__(
        approved_question, "get_typed_data", MagicMock(return_value=mock_mcq_data)
    )

    with (
        patch("src.database.get_async_session") as mock_get_session,
        patch(
            "src.question.service.get_questions_by_quiz",
            return_value=[approved_question],
        ),
    ):
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        export_data = await prepare_questions_for_export(quiz_id)

    assert len(export_data) == 1
    assert export_data[0]["question_text"] == "Integration test question"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question_type,approved_only,expected_filter",
    [
        ("MULTIPLE_CHOICE", True, "mc_approved"),
        ("FILL_IN_BLANK", False, "fib_all"),
        (None, True, "all_approved"),
        (None, False, "all_questions"),
    ],
)
async def test_get_questions_with_various_filters(
    async_session, question_type, approved_only, expected_filter
):
    """Test question retrieval with various filter combinations."""
    from src.question.models import Question, QuestionType
    from src.question.service import get_questions_by_quiz

    quiz_id = uuid.uuid4()

    # Mock appropriate questions based on filters
    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=getattr(QuestionType, question_type)
            if question_type
            else QuestionType.MULTIPLE_CHOICE,
            question_data={"question_text": f"Test {expected_filter}"},
            is_approved=approved_only,
        )
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = questions
    async_session.execute = AsyncMock(return_value=mock_result)

    result = await get_questions_by_quiz(
        async_session,
        quiz_id,
        question_type=getattr(QuestionType, question_type) if question_type else None,
        approved_only=approved_only,
    )

    assert len(result) == 1
    assert expected_filter in result[0].question_data["question_text"]


# Norwegian Language Feature Tests for Question Service


@pytest.mark.asyncio
async def test_save_questions_with_norwegian_validation(async_session):
    """Test question saving with Norwegian language-specific validation."""
    from src.question.models import QuestionType
    from src.question.service import save_questions
    from tests.conftest import create_quiz_in_async_session

    # Create a quiz in the session to avoid foreign key constraint violation
    quiz = await create_quiz_in_async_session(async_session)
    quiz_id = quiz.id
    question_type = QuestionType.MULTIPLE_CHOICE

    # Norwegian questions data
    questions_data = [
        {
            "question_text": "Hva er 2+2?",
            "option_a": "3",
            "option_b": "4",
            "option_c": "5",
            "option_d": "6",
            "correct_answer": "B",
            "explanation": "Grunnleggende aritmetikk",
        },
        {
            "question_text": "Hva er hovedstaden i Norge?",
            "option_a": "Bergen",
            "option_b": "Trondheim",
            "option_c": "Oslo",
            "option_d": "Stavanger",
            "correct_answer": "C",
            "explanation": "Oslo er hovedstaden i Norge",
        },
    ]

    # Mock question registry and validation
    mock_question_data = MagicMock()
    mock_question_data.dict.return_value = {"validated": "norwegian_data"}

    mock_question_impl = MagicMock()
    mock_question_impl.validate_data.return_value = mock_question_data

    mock_registry = MagicMock()
    mock_registry.get_question_type.return_value = mock_question_impl

    with patch(
        "src.question.service.get_question_type_registry", return_value=mock_registry
    ):
        result = await save_questions(
            async_session, quiz_id, question_type, questions_data
        )

    assert result["success"] is True
    assert result["saved_count"] == 2
    assert result["total_count"] == 2
    assert len(result["question_ids"]) == 2
    assert result["errors"] == []

    # Verify Norwegian questions were validated
    assert mock_question_impl.validate_data.call_count == 2


@pytest.mark.asyncio
async def test_prepare_questions_for_export_norwegian_content():
    """Test question export preparation with Norwegian content."""
    from src.question.models import Question, QuestionType
    from src.question.service import prepare_questions_for_export

    quiz_id = uuid.uuid4()

    # Norwegian questions
    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={
                "question_text": "Hva er hovedstaden i Norge?",
                "option_a": "Bergen",
                "option_b": "Trondheim",
                "option_c": "Oslo",
                "option_d": "Stavanger",
                "correct_answer": "C",
                "explanation": "Oslo er hovedstaden i Norge",
            },
            is_approved=True,
        )
    ]

    # Create proper MultipleChoiceData instance with Norwegian content
    from src.question.types.mcq import MultipleChoiceData

    mock_norwegian_mcq_data = MultipleChoiceData(
        question_text="Hva er hovedstaden i Norge?",
        option_a="Bergen",
        option_b="Trondheim",
        option_c="Oslo",
        option_d="Stavanger",
        correct_answer="C",
        explanation="Oslo er hovedstaden i Norge",
    )

    # Mock question.get_typed_data to return the Norwegian mock data
    for question in questions:
        object.__setattr__(
            question, "get_typed_data", MagicMock(return_value=mock_norwegian_mcq_data)
        )

    with (
        patch("src.database.get_async_session") as mock_get_session,
        patch("src.question.service.get_questions_by_quiz", return_value=questions),
        patch("src.question.service.get_question_type_registry"),
    ):
        # Mock the async context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await prepare_questions_for_export(quiz_id)

    assert len(result) == 1
    # Verify Norwegian content is preserved in export
    assert result[0]["question_text"] == "Hva er hovedstaden i Norge?"
    assert result[0]["option_a"] == "Bergen"
    assert result[0]["option_c"] == "Oslo"
    assert result[0]["correct_answer"] == "C"


# Fill-in-Blank Export Tests


@pytest.mark.asyncio
async def test_prepare_questions_for_export_fill_in_blank_success():
    """Test successful Fill-in-Blank question export preparation."""
    from src.question.models import Question, QuestionType
    from src.question.service import prepare_questions_for_export

    quiz_id = uuid.uuid4()

    # Create Fill-in-Blank questions
    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.FILL_IN_BLANK,
            question_data={
                "question_text": "The capital of France is [blank_1].",
                "blanks": [
                    {
                        "position": 1,
                        "correct_answer": "Paris",
                        "answer_variations": ["paris", "PARIS"],
                        "case_sensitive": False,
                    }
                ],
                "explanation": "Paris is the capital of France.",
            },
            is_approved=True,
        )
    ]

    # Create proper FillInBlankData instance
    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    mock_fib_data = FillInBlankData(
        question_text="The capital of France is [blank_1].",
        blanks=[
            BlankData(
                position=1,
                correct_answer="Paris",
                answer_variations=["paris", "PARIS"],
                case_sensitive=False,
            )
        ],
        explanation="Paris is the capital of France.",
    )

    # Mock question.get_typed_data to return the mock data
    for question in questions:
        object.__setattr__(
            question, "get_typed_data", MagicMock(return_value=mock_fib_data)
        )

    with (
        patch("src.database.get_async_session") as mock_get_session,
        patch("src.question.service.get_questions_by_quiz", return_value=questions),
        patch("src.question.service.get_question_type_registry"),
    ):
        # Mock the async context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await prepare_questions_for_export(quiz_id)

    assert len(result) == 1
    assert result[0]["question_text"] == "The capital of France is [blank_1]."
    assert result[0]["question_type"] == "fill_in_blank"
    assert len(result[0]["blanks"]) == 1
    assert result[0]["blanks"][0]["position"] == 1
    assert result[0]["blanks"][0]["correct_answer"] == "Paris"
    assert result[0]["blanks"][0]["answer_variations"] == ["paris", "PARIS"]
    assert result[0]["blanks"][0]["case_sensitive"] is False
    assert result[0]["explanation"] == "Paris is the capital of France."


@pytest.mark.asyncio
async def test_prepare_questions_for_export_fill_in_blank_multiple_blanks():
    """Test Fill-in-Blank export with multiple blanks."""
    from src.question.models import Question, QuestionType
    from src.question.service import prepare_questions_for_export

    quiz_id = uuid.uuid4()

    # Create Fill-in-Blank question with multiple blanks
    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.FILL_IN_BLANK,
            question_data={
                "question_text": "The capital of [blank_1] is [blank_2] and it is located in [blank_3].",
                "blanks": [
                    {
                        "position": 1,
                        "correct_answer": "France",
                        "case_sensitive": False,
                    },
                    {
                        "position": 2,
                        "correct_answer": "Paris",
                        "answer_variations": ["paris"],
                        "case_sensitive": False,
                    },
                    {
                        "position": 3,
                        "correct_answer": "Europe",
                        "case_sensitive": False,
                    },
                ],
                "explanation": "Paris is the capital of France in Europe.",
            },
            is_approved=True,
        )
    ]

    # Create proper FillInBlankData instance with multiple blanks
    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    mock_fib_data = FillInBlankData(
        question_text="The capital of [blank_1] is [blank_2] and it is located in [blank_3].",
        blanks=[
            BlankData(
                position=1,
                correct_answer="France",
                case_sensitive=False,
            ),
            BlankData(
                position=2,
                correct_answer="Paris",
                answer_variations=["paris"],
                case_sensitive=False,
            ),
            BlankData(
                position=3,
                correct_answer="Europe",
                case_sensitive=False,
            ),
        ],
        explanation="Paris is the capital of France in Europe.",
    )

    # Mock question.get_typed_data to return the mock data
    for question in questions:
        object.__setattr__(
            question, "get_typed_data", MagicMock(return_value=mock_fib_data)
        )

    with (
        patch("src.database.get_async_session") as mock_get_session,
        patch("src.question.service.get_questions_by_quiz", return_value=questions),
        patch("src.question.service.get_question_type_registry"),
    ):
        # Mock the async context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await prepare_questions_for_export(quiz_id)

    assert len(result) == 1
    assert result[0]["question_type"] == "fill_in_blank"
    assert len(result[0]["blanks"]) == 3

    # Verify all blanks are properly formatted
    blanks = result[0]["blanks"]
    assert blanks[0]["position"] == 1
    assert blanks[0]["correct_answer"] == "France"
    assert blanks[1]["position"] == 2
    assert blanks[1]["correct_answer"] == "Paris"
    assert blanks[1]["answer_variations"] == ["paris"]
    assert blanks[2]["position"] == 3
    assert blanks[2]["correct_answer"] == "Europe"


@pytest.mark.asyncio
async def test_prepare_questions_for_export_fill_in_blank_case_sensitive():
    """Test Fill-in-Blank export with case-sensitive answers."""
    from src.question.models import Question, QuestionType
    from src.question.service import prepare_questions_for_export

    quiz_id = uuid.uuid4()

    # Create Fill-in-Blank question with case-sensitive answers
    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.FILL_IN_BLANK,
            question_data={
                "question_text": "The chemical symbol for gold is [blank_1].",
                "blanks": [
                    {
                        "position": 1,
                        "correct_answer": "Au",
                        "case_sensitive": True,
                    }
                ],
                "explanation": "Au is the chemical symbol for gold.",
            },
            is_approved=True,
        )
    ]

    # Create proper FillInBlankData instance
    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    mock_fib_data = FillInBlankData(
        question_text="The chemical symbol for gold is [blank_1].",
        blanks=[
            BlankData(
                position=1,
                correct_answer="Au",
                case_sensitive=True,
            )
        ],
        explanation="Au is the chemical symbol for gold.",
    )

    # Mock question.get_typed_data to return the mock data
    for question in questions:
        object.__setattr__(
            question, "get_typed_data", MagicMock(return_value=mock_fib_data)
        )

    with (
        patch("src.database.get_async_session") as mock_get_session,
        patch("src.question.service.get_questions_by_quiz", return_value=questions),
        patch("src.question.service.get_question_type_registry"),
    ):
        # Mock the async context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await prepare_questions_for_export(quiz_id)

    assert len(result) == 1
    assert result[0]["question_type"] == "fill_in_blank"
    assert len(result[0]["blanks"]) == 1
    assert result[0]["blanks"][0]["case_sensitive"] is True
    assert result[0]["blanks"][0]["correct_answer"] == "Au"


@pytest.mark.asyncio
async def test_prepare_questions_for_export_mixed_question_types():
    """Test export preparation with mixed MCQ and Fill-in-Blank questions."""
    from src.question.models import Question, QuestionType
    from src.question.service import prepare_questions_for_export

    quiz_id = uuid.uuid4()

    # Create mixed question types
    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={
                "question_text": "What is 2+2?",
                "option_a": "3",
                "option_b": "4",
                "option_c": "5",
                "option_d": "6",
                "correct_answer": "B",
            },
            is_approved=True,
        ),
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.FILL_IN_BLANK,
            question_data={
                "question_text": "The capital of France is [blank_1].",
                "blanks": [
                    {
                        "position": 1,
                        "correct_answer": "Paris",
                        "case_sensitive": False,
                    }
                ],
                "explanation": "Paris is the capital of France.",
            },
            is_approved=True,
        ),
    ]

    # Create proper data instances
    from src.question.types.fill_in_blank import BlankData, FillInBlankData
    from src.question.types.mcq import MultipleChoiceData

    mock_mcq_data = MultipleChoiceData(
        question_text="What is 2+2?",
        option_a="3",
        option_b="4",
        option_c="5",
        option_d="6",
        correct_answer="B",
    )

    mock_fib_data = FillInBlankData(
        question_text="The capital of France is [blank_1].",
        blanks=[
            BlankData(
                position=1,
                correct_answer="Paris",
                case_sensitive=False,
            )
        ],
        explanation="Paris is the capital of France.",
    )

    # Mock question.get_typed_data to return appropriate data
    object.__setattr__(
        questions[0], "get_typed_data", MagicMock(return_value=mock_mcq_data)
    )
    object.__setattr__(
        questions[1], "get_typed_data", MagicMock(return_value=mock_fib_data)
    )

    with (
        patch("src.database.get_async_session") as mock_get_session,
        patch("src.question.service.get_questions_by_quiz", return_value=questions),
        patch("src.question.service.get_question_type_registry"),
    ):
        # Mock the async context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await prepare_questions_for_export(quiz_id)

    assert len(result) == 2

    # Verify MCQ question
    mcq_question = next(q for q in result if q["question_type"] == "multiple_choice")
    assert mcq_question["question_text"] == "What is 2+2?"
    assert mcq_question["option_a"] == "3"
    assert mcq_question["correct_answer"] == "B"

    # Verify Fill-in-Blank question
    fib_question = next(q for q in result if q["question_type"] == "fill_in_blank")
    assert fib_question["question_text"] == "The capital of France is [blank_1]."
    assert len(fib_question["blanks"]) == 1
    assert fib_question["blanks"][0]["correct_answer"] == "Paris"


@pytest.mark.asyncio
async def test_prepare_questions_for_export_fill_in_blank_with_answer_variations():
    """Test Fill-in-Blank export with answer variations."""
    from src.question.models import Question, QuestionType
    from src.question.service import prepare_questions_for_export

    quiz_id = uuid.uuid4()

    # Create Fill-in-Blank question with multiple answer variations
    questions = [
        Question(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_type=QuestionType.FILL_IN_BLANK,
            question_data={
                "question_text": "The capital of France is [blank_1].",
                "blanks": [
                    {
                        "position": 1,
                        "correct_answer": "Paris",
                        "answer_variations": ["paris", "PARIS", "Paříž", "パリ"],
                        "case_sensitive": False,
                    }
                ],
                "explanation": "Paris is the capital of France.",
            },
            is_approved=True,
        )
    ]

    # Create proper FillInBlankData instance
    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    mock_fib_data = FillInBlankData(
        question_text="The capital of France is [blank_1].",
        blanks=[
            BlankData(
                position=1,
                correct_answer="Paris",
                answer_variations=["paris", "PARIS", "Paříž", "パリ"],
                case_sensitive=False,
            )
        ],
        explanation="Paris is the capital of France.",
    )

    # Mock question.get_typed_data to return the mock data
    for question in questions:
        object.__setattr__(
            question, "get_typed_data", MagicMock(return_value=mock_fib_data)
        )

    with (
        patch("src.database.get_async_session") as mock_get_session,
        patch("src.question.service.get_questions_by_quiz", return_value=questions),
        patch("src.question.service.get_question_type_registry"),
    ):
        # Mock the async context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        result = await prepare_questions_for_export(quiz_id)

    assert len(result) == 1
    assert result[0]["question_type"] == "fill_in_blank"
    assert len(result[0]["blanks"]) == 1

    blank = result[0]["blanks"][0]
    assert blank["correct_answer"] == "Paris"
    assert blank["answer_variations"] == ["paris", "PARIS", "Paříž", "パリ"]
    assert blank["case_sensitive"] is False
