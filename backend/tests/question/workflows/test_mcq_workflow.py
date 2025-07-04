"""Tests for MCQ workflow implementation."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class MockLLMProvider:
    """Simple mock LLM provider for testing."""

    def __init__(self):
        self.generate_with_retry = AsyncMock()

    async def generate(self, messages):
        return await self.generate_with_retry(messages)


@pytest.fixture
def workflow():
    """Create MCQ workflow instance."""
    from src.question.types import QuestionType
    from src.question.workflows.base import WorkflowConfiguration
    from src.question.workflows.mcq_workflow import MCQWorkflow

    config = WorkflowConfiguration()
    return MCQWorkflow(QuestionType.MULTIPLE_CHOICE, config)


@pytest.fixture
def generation_params():
    """Create test generation parameters."""
    from src.question.types import GenerationParameters, QuestionDifficulty

    return GenerationParameters(
        target_count=5,
        difficulty=QuestionDifficulty.MEDIUM,
        tags=["python", "programming"],
        custom_instructions="Focus on basic concepts",
    )


@pytest.fixture
def sample_content():
    """Create sample content for generation."""
    return {
        "modules": [
            {
                "id": "module_1",
                "name": "Introduction to Python",
                "content": "Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
            },
            {
                "id": "module_2",
                "name": "Data Types",
                "content": "Python has several built-in data types including integers, floats, strings, lists, tuples, and dictionaries. Each type has specific methods and operations.",
            },
        ],
        "total_content_length": 500,
    }


@pytest.fixture
def initial_state(generation_params, sample_content):
    """Create initial workflow state."""
    from src.question.types import QuestionType

    return {
        "quiz_id": uuid.uuid4(),
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "target_question_count": generation_params.target_count,
        "content_chunks": ["sample content chunk"],
        "generation_parameters": generation_params,
        "llm_provider": MockLLMProvider(),
        "current_chunk_index": 0,
        "questions_generated": 0,
        "generated_questions": [],
        "error_message": None,
        "workflow_metadata": {
            "workflow_name": "mcq_generation_workflow",
            "started_at": "2024-01-01T00:00:00Z",
        },
    }


def test_workflow_name(workflow):
    """Test workflow name property."""
    assert workflow.workflow_name == "mcq_generation_workflow"


def test_build_workflow_structure(workflow):
    """Test that workflow is built with correct structure."""
    graph = workflow.build_workflow()

    # Verify nodes exist
    assert "prepare_content" in graph.nodes
    assert "generate_question" in graph.nodes
    assert "validate_question" in graph.nodes
    assert "save_questions" in graph.nodes

    # Note: We can't easily test edges without running the workflow,
    # but we can verify the graph was created
    assert graph is not None


@pytest.mark.asyncio
async def test_prepare_content(workflow, initial_state):
    """Test content preparation step."""
    with patch("src.quiz.service.get_content_from_quiz") as mock_get_content:
        mock_get_content.return_value = {
            "module_1": [
                {
                    "id": "page_1",
                    "title": "Test Page",
                    "content": "This is test content for chunking" * 10,
                }
            ]
        }

        state = await workflow.prepare_content(initial_state)

    assert state["quiz_id"] == initial_state["quiz_id"]
    assert state["target_question_count"] == initial_state["target_question_count"]
    assert state["generation_parameters"] == initial_state["generation_parameters"]
    assert "content_chunks" in state
    assert state["questions_generated"] == 0
    assert state["generated_questions"] == []


@pytest.mark.asyncio
async def test_generate_question_success(workflow, initial_state):
    """Test successful question generation."""
    mock_llm_response = json.dumps(
        {
            "question_text": "What is Python?",
            "option_a": "A snake",
            "option_b": "A programming language",
            "option_c": "A type of coffee",
            "option_d": "A web browser",
            "correct_answer": "B",
            "explanation": "Python is a high-level programming language.",
        }
    )

    # Set up state with content chunks
    initial_state["content_chunks"] = ["Python is a programming language"]
    initial_state["current_chunk_index"] = 0

    mock_response = MagicMock()
    mock_response.content = mock_llm_response
    mock_response.response_time = 1.5
    mock_response.total_tokens = 100
    mock_response.model = "gpt-4"

    initial_state["llm_provider"].generate_with_retry = AsyncMock(
        return_value=mock_response
    )

    state = await workflow.generate_question(initial_state)

    assert len(state["generated_questions"]) == 1
    assert state["generated_questions"][0]["question_text"] == "What is Python?"
    assert state["questions_generated"] == 1
    assert state["current_chunk_index"] == 1


@pytest.mark.asyncio
async def test_generate_question_invalid_json(workflow, initial_state):
    """Test question generation with invalid JSON response."""
    mock_invalid_response = "This is not valid JSON"

    # Set up state with content chunks
    initial_state["content_chunks"] = ["Python is a programming language"]
    initial_state["current_chunk_index"] = 0

    mock_response = MagicMock()
    mock_response.content = mock_invalid_response
    mock_response.response_time = 1.5
    mock_response.total_tokens = 100
    mock_response.model = "gpt-4"

    initial_state["llm_provider"].generate_with_retry = AsyncMock(
        return_value=mock_response
    )

    state = await workflow.generate_question(initial_state)

    # The workflow should move to next chunk index even on error
    assert len(state["generated_questions"]) == 0
    assert state["current_chunk_index"] == 1


@pytest.mark.asyncio
async def test_generate_question_missing_required_fields(workflow, initial_state):
    """Test question generation with missing required fields in response."""
    mock_response_missing_fields = json.dumps(
        {
            "question_text": "What is Python?",
            "option_a": "A snake",
            # Missing other required fields
        }
    )

    # Set up state with content chunks
    initial_state["content_chunks"] = ["Python is a programming language"]
    initial_state["current_chunk_index"] = 0

    mock_response = MagicMock()
    mock_response.content = mock_response_missing_fields
    mock_response.response_time = 1.5
    mock_response.total_tokens = 100
    mock_response.model = "gpt-4"

    initial_state["llm_provider"].generate_with_retry = AsyncMock(
        return_value=mock_response
    )

    state = await workflow.generate_question(initial_state)

    # The workflow should move to next chunk index even on error
    assert len(state["generated_questions"]) == 0
    assert state["current_chunk_index"] == 1


@pytest.mark.asyncio
async def test_validate_question_success(workflow, initial_state):
    """Test successful question validation."""
    # Set up state with valid questions
    initial_state["generated_questions"] = [
        {
            "question_text": "What is Python?",
            "option_a": "A snake",
            "option_b": "A programming language",
            "option_c": "A type of coffee",
            "option_d": "A web browser",
            "correct_answer": "B",
            "explanation": "Python is a programming language.",
        }
    ]

    state = await workflow.validate_question(initial_state)

    # Validation passes through the questions
    assert len(state["generated_questions"]) == 1
    assert state["generated_questions"][0]["question_text"] == "What is Python?"


@pytest.mark.asyncio
async def test_validate_question_with_valid_questions(workflow, initial_state):
    """Test question validation with valid questions."""
    # Set up state with valid questions
    initial_state["generated_questions"] = [
        {
            "question_text": "Valid question?",
            "option_a": "Yes",
            "option_b": "No",
            "option_c": "Maybe",
            "option_d": "Absolutely",
            "correct_answer": "A",
            "explanation": "This is valid.",
        }
    ]

    state = await workflow.validate_question(initial_state)

    # Validation should pass through questions unchanged
    assert len(state["generated_questions"]) == 1
    assert state["generated_questions"][0]["question_text"] == "Valid question?"


def test_should_continue_generation_needs_more_questions(workflow, initial_state):
    """Test continuation decision when more questions are needed."""
    # Set up state with fewer questions than target
    initial_state["questions_generated"] = 2
    initial_state["target_question_count"] = 5
    initial_state["content_chunks"] = ["chunk1", "chunk2", "chunk3"]
    initial_state["current_chunk_index"] = 2
    initial_state["error_message"] = None

    result = workflow.should_continue_generation(initial_state)

    assert result == "generate_question"


def test_should_continue_generation_target_reached(workflow, initial_state):
    """Test continuation decision when target is reached."""
    # Set up state with target number of questions
    initial_state["questions_generated"] = 5
    initial_state["target_question_count"] = 5
    initial_state["content_chunks"] = ["chunk1", "chunk2", "chunk3"]
    initial_state["current_chunk_index"] = 2
    initial_state["error_message"] = None

    result = workflow.should_continue_generation(initial_state)

    assert result == "save_questions"


def test_should_continue_generation_chunks_exhausted(workflow, initial_state):
    """Test continuation decision when content chunks are exhausted."""
    # Set up state with exhausted chunks but not enough questions
    initial_state["questions_generated"] = 1
    initial_state["target_question_count"] = 5
    initial_state["content_chunks"] = ["chunk1", "chunk2"]
    initial_state["current_chunk_index"] = 2  # Beyond available chunks
    initial_state["error_message"] = None

    result = workflow.should_continue_generation(initial_state)

    # Should stop even if target not reached
    assert result == "save_questions"


@pytest.mark.asyncio
async def test_save_questions_to_database_success(workflow, initial_state):
    """Test successful saving of questions to database."""
    # Set up state with questions to save
    initial_state["generated_questions"] = [
        {
            "question_text": "What is Python?",
            "option_a": "A snake",
            "option_b": "A programming language",
            "option_c": "A type of coffee",
            "option_d": "A web browser",
            "correct_answer": "B",
            "explanation": "Python is a programming language.",
        }
    ]

    with patch("src.question.workflows.mcq_workflow.transaction") as mock_transaction:
        # Mock transaction context manager
        mock_session = AsyncMock()
        mock_session.add_all = MagicMock()
        mock_transaction.return_value.__aenter__.return_value = mock_session

        state = await workflow.save_questions_to_database(initial_state)

    assert state["error_message"] is None
    assert "questions_saved" in state["workflow_metadata"]


@pytest.mark.asyncio
async def test_save_questions_to_database_failure(workflow, initial_state):
    """Test saving of questions to database with failures."""
    initial_state["generated_questions"] = [
        {"question_text": "Invalid question"}  # Missing required fields
    ]

    with patch("src.question.workflows.mcq_workflow.transaction") as mock_transaction:
        mock_session = AsyncMock()
        mock_session.add_all = MagicMock()
        mock_transaction.return_value.__aenter__.return_value = mock_session

        state = await workflow.save_questions_to_database(initial_state)

    # Should handle validation errors gracefully
    assert "questions_saved" in state["workflow_metadata"]
    assert state["workflow_metadata"]["questions_saved"] == 0


def test_validate_question_structure_valid(workflow):
    """Test question structure validation with valid question."""
    valid_question = {
        "question_text": "What is Python?",
        "option_a": "A snake",
        "option_b": "A programming language",
        "option_c": "A type of coffee",
        "option_d": "A web browser",
        "correct_answer": "B",
        "explanation": "Python is a programming language.",
    }

    # Should not raise an exception for valid question
    try:
        workflow._validate_mcq_structure(valid_question)
        result = True
    except ValueError:
        result = False

    assert result is True


def test_validate_question_structure_missing_fields(workflow):
    """Test question structure validation with missing fields."""
    invalid_questions = [
        {"question_text": "What is Python?"},  # Missing options
        {
            "question_text": "What is Python?",
            "option_a": "A snake",
            "option_b": "A language",
            # Missing option_c, option_d, correct_answer
        },
        {
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "option_d": "D",
            "correct_answer": "A",
            # Missing question_text
        },
    ]

    for invalid_question in invalid_questions:
        with pytest.raises(ValueError):
            workflow._validate_mcq_structure(invalid_question)


def test_validate_question_structure_invalid_correct_answer(workflow):
    """Test question structure validation with invalid correct answer."""
    invalid_question = {
        "question_text": "What is Python?",
        "option_a": "A snake",
        "option_b": "A programming language",
        "option_c": "A type of coffee",
        "option_d": "A web browser",
        "correct_answer": "E",  # Invalid - should be A, B, C, or D
        "explanation": "Python is a programming language.",
    }

    with pytest.raises(ValueError):
        workflow._validate_mcq_structure(invalid_question)


@pytest.mark.asyncio
async def test_full_workflow_execution(workflow, initial_state):
    """Test full workflow execution from start to finish."""
    # Mock all external dependencies
    mock_llm_response = json.dumps(
        {
            "question_text": "What is Python?",
            "option_a": "A snake",
            "option_b": "A programming language",
            "option_c": "A type of coffee",
            "option_d": "A web browser",
            "correct_answer": "B",
            "explanation": "Python is a programming language.",
        }
    )

    with (
        patch("src.quiz.service.get_content_from_quiz") as mock_get_content,
        patch("src.question.workflows.mcq_workflow.transaction") as mock_transaction,
    ):
        # Mock content service
        mock_get_content.return_value = {
            "module_1": [
                {
                    "id": "page_1",
                    "title": "Test Page",
                    "content": "This is test content for chunking" * 10,
                }
            ]
        }

        # Mock LLM provider response
        mock_response = MagicMock()
        mock_response.content = mock_llm_response
        mock_response.response_time = 1.5
        mock_response.total_tokens = 100
        mock_response.model = "gpt-4"

        initial_state["llm_provider"].generate_with_retry = AsyncMock(
            return_value=mock_response
        )

        # Mock database transaction
        mock_session = AsyncMock()
        mock_session.add_all = MagicMock()
        mock_transaction.return_value.__aenter__.return_value = mock_session

        # Test each step manually
        state = await workflow.prepare_content(initial_state)
        assert "content_chunks" in state

        state = await workflow.generate_question(state)
        assert state["questions_generated"] == 1

        state = await workflow.validate_question(state)
        assert len(state["generated_questions"]) == 1

        # Set target count to 1 so it goes to save
        state["target_question_count"] = 1

        state = await workflow.save_questions_to_database(state)

    assert state["error_message"] is None
    assert len(state["generated_questions"]) == 1
    assert "questions_saved" in state["workflow_metadata"]


@pytest.mark.parametrize(
    "target_count,questions_generated,current_chunk,total_chunks,expected_action",
    [
        (5, 1, 1, 3, "generate_question"),  # Need more questions, have chunks
        (5, 5, 2, 3, "save_questions"),  # Target reached
        (2, 1, 1, 3, "generate_question"),  # Need more questions
        (10, 5, 3, 3, "save_questions"),  # Chunks exhausted
        (1, 0, 0, 3, "generate_question"),  # Just starting
    ],
)
def test_should_continue_generation_various_scenarios(
    workflow,
    initial_state,
    target_count,
    questions_generated,
    current_chunk,
    total_chunks,
    expected_action,
):
    """Test continuation decision with various scenarios."""
    initial_state["target_question_count"] = target_count
    initial_state["questions_generated"] = questions_generated
    initial_state["current_chunk_index"] = current_chunk
    initial_state["content_chunks"] = [f"chunk_{i}" for i in range(total_chunks)]
    initial_state["error_message"] = None

    result = workflow.should_continue_generation(initial_state)
    assert result == expected_action
