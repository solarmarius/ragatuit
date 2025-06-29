import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.services.mcq_generation import (
    MCQGenerationService,
    MCQGenerationState,
    mcq_generation_service,
)


@pytest.fixture
def sample_quiz_id() -> UUID:
    """Return a sample quiz UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_content_dict() -> dict[str, list[dict[str, str]]]:
    """Return sample extracted content for testing."""
    return {
        "module_1": [
            {
                "title": "Introduction to Machine Learning",
                "content": "Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed. It involves algorithms that can identify patterns in data and make predictions or decisions based on those patterns. There are three main types of machine learning: supervised learning, unsupervised learning, and reinforcement learning. Supervised learning uses labeled data to train models, while unsupervised learning finds patterns in unlabeled data. Reinforcement learning involves agents learning through interaction with an environment.",
            },
            {
                "title": "Neural Networks",
                "content": "Neural networks are computational models inspired by the human brain. They consist of interconnected nodes called neurons arranged in layers. The input layer receives data, hidden layers process the information, and the output layer produces results. Each connection has a weight that determines the strength of the signal. Training involves adjusting these weights through backpropagation to minimize error. Deep neural networks with many hidden layers are called deep learning models and have achieved remarkable success in image recognition, natural language processing, and other domains.",
            },
        ]
    }


@pytest.fixture
def sample_generated_question() -> dict[str, str]:
    """Return a sample generated question for testing."""
    return {
        "question_text": "What are the three main types of machine learning?",
        "option_a": "Supervised, unsupervised, and reinforcement learning",
        "option_b": "Classification, regression, and clustering",
        "option_c": "Linear, non-linear, and deep learning",
        "option_d": "Training, testing, and validation",
        "correct_answer": "A",
    }


def test_chunk_content_basic() -> None:
    """Test basic content chunking functionality."""
    service = MCQGenerationService()
    content_dict = {
        "module_1": [
            {
                "content": "This is a sufficiently long piece of content that should be included in the chunking process because it meets the minimum length requirement of 100 characters or more."
            },
            {
                "content": "This is another sufficiently long piece of content that should also be included in the chunking process since it exceeds 100 chars."
            },
        ]
    }

    chunks = service._chunk_content(content_dict, max_chunk_size=1000)

    assert len(chunks) == 2
    assert "sufficiently long piece of content" in chunks[0]
    assert "another sufficiently long piece" in chunks[1]


def test_chunk_content_long_content() -> None:
    """Test chunking of long content that needs to be split."""
    service = MCQGenerationService()
    # Create content with paragraph breaks to test proper chunking
    paragraph1 = "This is the first paragraph. " * 30  # ~900 chars
    paragraph2 = "This is the second paragraph. " * 30  # ~900 chars
    paragraph3 = "This is the third paragraph. " * 30  # ~900 chars
    long_content = paragraph1 + "\n\n" + paragraph2 + "\n\n" + paragraph3
    content_dict = {"module_1": [{"content": long_content}]}

    chunks = service._chunk_content(content_dict, max_chunk_size=1500)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 1500


def test_chunk_content_filters_short_content() -> None:
    """Test that very short content is filtered out."""
    service = MCQGenerationService()
    content_dict = {
        "module_1": [
            {"content": "Too short"},  # Less than 100 chars
            {
                "content": "This is a much longer piece of content that should be included in the chunking process because it meets the minimum length requirement."
            },
        ]
    }

    chunks = service._chunk_content(content_dict)

    assert len(chunks) == 1
    assert "Too short" not in chunks[0]
    assert "This is a much longer piece" in chunks[0]


def test_chunk_content_handles_invalid_data() -> None:
    """Test that invalid data structures are handled gracefully."""
    service = MCQGenerationService()
    content_dict = {
        "module_1": "not a list",  # Invalid structure
        "module_2": [
            "not a dict",  # Invalid item
            {
                "content": "Valid content that should be included in the final output because it has sufficient length to pass the minimum requirement of 100 characters."
            },
            {"no_content_key": "missing content"},  # Missing content key
        ],
    }

    chunks = service._chunk_content(content_dict)

    assert len(chunks) == 1
    assert "Valid content that should be included" in chunks[0]


@patch("app.services.mcq_generation.get_content_from_quiz")
@pytest.mark.asyncio
async def test_content_preparation_success(
    mock_get_content: MagicMock,
    sample_quiz_id: UUID,
    sample_content_dict: dict[str, list[dict[str, str]]],
) -> None:
    """Test successful content preparation."""
    service = MCQGenerationService()
    mock_get_content.return_value = json.dumps(sample_content_dict)

    state: MCQGenerationState = {
        "quiz_id": sample_quiz_id,
        "content_chunks": [],
        "target_question_count": 10,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": [],
        "current_chunk_index": 0,
        "questions_generated": 0,
        "error_message": None,
    }

    with patch("app.services.mcq_generation.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        result_state = await service.content_preparation(state)

        assert result_state["error_message"] is None
        assert len(result_state["content_chunks"]) > 0
        assert result_state["current_chunk_index"] == 0
        assert result_state["questions_generated"] == 0
        assert result_state["generated_questions"] == []


@patch("app.services.mcq_generation.get_content_from_quiz")
@pytest.mark.asyncio
async def test_content_preparation_no_content(
    mock_get_content: MagicMock, sample_quiz_id: UUID
) -> None:
    """Test content preparation when no content is found."""
    service = MCQGenerationService()
    mock_get_content.return_value = None

    state: MCQGenerationState = {
        "quiz_id": sample_quiz_id,
        "content_chunks": [],
        "target_question_count": 10,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": [],
        "current_chunk_index": 0,
        "questions_generated": 0,
        "error_message": None,
    }

    with patch("app.services.mcq_generation.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        result_state = await service.content_preparation(state)

        assert result_state["error_message"] is not None
        assert "No extracted content found" in result_state["error_message"]


@patch("app.services.mcq_generation.settings")
@patch("app.services.mcq_generation.ChatOpenAI")
@pytest.mark.asyncio
async def test_generate_question_success(
    mock_chat_openai: MagicMock,
    mock_settings: MagicMock,
    sample_quiz_id: UUID,
    sample_generated_question: dict[str, str],
) -> None:
    """Test successful question generation."""
    # Mock settings to have API key
    mock_settings.OPENAI_SECRET_KEY = "test-api-key"
    mock_settings.LLM_API_TIMEOUT = 120.0

    service = MCQGenerationService()

    # Mock LLM response
    mock_llm_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps(sample_generated_question)
    mock_llm_instance.return_value = mock_response
    mock_chat_openai.return_value = mock_llm_instance

    # Create chain mock
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_response

    state: MCQGenerationState = {
        "quiz_id": sample_quiz_id,
        "content_chunks": ["Sample content for question generation"],
        "target_question_count": 10,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": [],
        "current_chunk_index": 0,
        "questions_generated": 0,
        "error_message": None,
    }

    with patch.object(service, "_create_mcq_prompt") as mock_prompt:
        mock_prompt_instance = MagicMock()
        mock_prompt.return_value = mock_prompt_instance
        mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

        result_state = await service.generate_question(state)

        assert result_state["error_message"] is None
        assert result_state["questions_generated"] == 1
        assert result_state["current_chunk_index"] == 1
        assert len(result_state["generated_questions"]) == 1

        generated_question = result_state["generated_questions"][0]
        assert (
            generated_question["question_text"]
            == sample_generated_question["question_text"]
        )
        assert generated_question["quiz_id"] == sample_quiz_id


@patch("app.services.mcq_generation.settings")
@pytest.mark.asyncio
async def test_generate_question_invalid_json(
    mock_settings: MagicMock, sample_quiz_id: UUID
) -> None:
    """Test question generation with invalid JSON response."""
    # Mock settings to have API key
    mock_settings.OPENAI_SECRET_KEY = "test-api-key"
    mock_settings.LLM_API_TIMEOUT = 120.0

    service = MCQGenerationService()

    # Mock LLM response with invalid JSON
    with patch.object(service, "_get_llm") as _mock_get_llm:
        mock_response = MagicMock()
        mock_response.content = "Invalid JSON response"

        mock_chain = MagicMock()
        mock_chain.ainvoke.return_value = mock_response

        with patch.object(service, "_create_mcq_prompt") as mock_prompt:
            mock_prompt_instance = MagicMock()
            mock_prompt.return_value = mock_prompt_instance
            mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

            state: MCQGenerationState = {
                "quiz_id": sample_quiz_id,
                "content_chunks": ["Sample content"],
                "target_question_count": 10,
                "llm_model": "gpt-4o",
                "llm_temperature": 0.3,
                "generated_questions": [],
                "current_chunk_index": 0,
                "questions_generated": 0,
                "error_message": None,
            }

            result_state = await service.generate_question(state)

            # Should move to next chunk despite error (non-critical error)
            assert result_state["current_chunk_index"] == 1
            assert result_state["questions_generated"] == 0


@patch("app.services.mcq_generation.settings")
@pytest.mark.asyncio
async def test_generate_question_missing_fields(
    mock_settings: MagicMock, sample_quiz_id: UUID
) -> None:
    """Test question generation with missing required fields."""
    # Mock settings to have API key
    mock_settings.OPENAI_SECRET_KEY = "test-api-key"
    mock_settings.LLM_API_TIMEOUT = 120.0

    service = MCQGenerationService()

    incomplete_question = {"question_text": "Incomplete question"}

    with patch.object(service, "_get_llm") as _mock_get_llm:
        mock_response = MagicMock()
        mock_response.content = json.dumps(incomplete_question)

        mock_chain = MagicMock()
        mock_chain.ainvoke.return_value = mock_response

        with patch.object(service, "_create_mcq_prompt") as mock_prompt:
            mock_prompt_instance = MagicMock()
            mock_prompt.return_value = mock_prompt_instance
            mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

            state: MCQGenerationState = {
                "quiz_id": sample_quiz_id,
                "content_chunks": ["Sample content"],
                "target_question_count": 10,
                "llm_model": "gpt-4o",
                "llm_temperature": 0.3,
                "generated_questions": [],
                "current_chunk_index": 0,
                "questions_generated": 0,
                "error_message": None,
            }

            result_state = await service.generate_question(state)

            # Should move to next chunk despite validation error
            assert result_state["current_chunk_index"] == 1
            assert result_state["questions_generated"] == 0


def test_should_continue_generation_target_reached(sample_quiz_id: UUID) -> None:
    """Test stopping when target question count is reached."""
    service = MCQGenerationService()

    state: MCQGenerationState = {
        "quiz_id": sample_quiz_id,
        "content_chunks": ["chunk1", "chunk2"],
        "target_question_count": 5,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": [],
        "current_chunk_index": 1,
        "questions_generated": 5,  # Target reached
        "error_message": None,
    }

    result = service.should_continue_generation(state)
    assert result == "save_questions"


def test_should_continue_generation_chunks_exhausted(sample_quiz_id: UUID) -> None:
    """Test stopping when all content chunks are processed."""
    service = MCQGenerationService()

    state: MCQGenerationState = {
        "quiz_id": sample_quiz_id,
        "content_chunks": ["chunk1", "chunk2"],
        "target_question_count": 10,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": [],
        "current_chunk_index": 2,  # All chunks processed
        "questions_generated": 2,
        "error_message": None,
    }

    result = service.should_continue_generation(state)
    assert result == "save_questions"


def test_should_continue_generation_error_occurred(sample_quiz_id: UUID) -> None:
    """Test stopping when there's a critical error."""
    service = MCQGenerationService()

    state: MCQGenerationState = {
        "quiz_id": sample_quiz_id,
        "content_chunks": ["chunk1", "chunk2"],
        "target_question_count": 10,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": [],
        "current_chunk_index": 1,
        "questions_generated": 2,
        "error_message": "Critical error occurred",
    }

    result = service.should_continue_generation(state)
    assert result == "save_questions"


def test_should_continue_generation_continue(sample_quiz_id: UUID) -> None:
    """Test continuing when conditions allow."""
    service = MCQGenerationService()

    state: MCQGenerationState = {
        "quiz_id": sample_quiz_id,
        "content_chunks": ["chunk1", "chunk2", "chunk3"],
        "target_question_count": 10,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": [],
        "current_chunk_index": 1,
        "questions_generated": 3,
        "error_message": None,
    }

    result = service.should_continue_generation(state)
    assert result == "generate_question"


@pytest.mark.asyncio
async def test_save_questions_to_database_success(
    sample_quiz_id: UUID, sample_generated_question: dict[str, str]
) -> None:
    """Test successful saving of questions to database."""
    service = MCQGenerationService()

    questions = [sample_generated_question.copy()]
    questions[0]["quiz_id"] = str(sample_quiz_id)

    state: MCQGenerationState = {
        "quiz_id": sample_quiz_id,
        "content_chunks": [],
        "target_question_count": 1,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": questions,
        "current_chunk_index": 1,
        "questions_generated": 1,
        "error_message": None,
    }

    with patch("app.services.mcq_generation.get_async_session") as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        result_state = await service.save_questions_to_database(state)

        assert result_state["error_message"] is None
        mock_session.add_all.assert_called()
        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_save_questions_to_database_failure(
    sample_quiz_id: UUID, sample_generated_question: dict[str, str]
) -> None:
    """Test handling of database errors when saving questions."""
    service = MCQGenerationService()

    questions = [sample_generated_question.copy()]
    questions[0]["quiz_id"] = str(sample_quiz_id)

    state: MCQGenerationState = {
        "quiz_id": sample_quiz_id,
        "content_chunks": [],
        "target_question_count": 1,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": questions,
        "current_chunk_index": 1,
        "questions_generated": 1,
        "error_message": None,
    }

    with patch("app.services.mcq_generation.get_async_session") as mock_session_class:
        mock_session = AsyncMock()
        mock_session.commit.side_effect = Exception("Database error")
        mock_session_class.return_value.__aenter__.return_value = mock_session

        result_state = await service.save_questions_to_database(state)

        assert result_state["error_message"] is not None
        assert "Failed to save questions" in result_state["error_message"]


def test_build_workflow() -> None:
    """Test workflow construction."""
    service = MCQGenerationService()
    workflow = service.build_workflow()

    assert workflow is not None
    # Check that all nodes are added
    assert "content_preparation" in workflow.nodes
    assert "generate_question" in workflow.nodes
    assert "save_questions" in workflow.nodes


@patch("app.services.mcq_generation.get_content_from_quiz")
@pytest.mark.asyncio
async def test_generate_mcqs_for_quiz_success(
    mock_get_content: MagicMock,
    sample_quiz_id: UUID,
    sample_content_dict: dict[str, list[dict[str, str]]],
    sample_generated_question: dict[str, str],
) -> None:
    """Test the complete MCQ generation workflow."""
    service = MCQGenerationService()
    mock_get_content.return_value = json.dumps(sample_content_dict)

    # Mock the workflow compilation and execution
    final_state = {
        "quiz_id": sample_quiz_id,
        "content_chunks": ["chunk1"],
        "target_question_count": 1,
        "llm_model": "gpt-4o",
        "llm_temperature": 0.3,
        "generated_questions": [sample_generated_question],
        "current_chunk_index": 1,
        "questions_generated": 1,
        "error_message": None,
    }

    # Use AsyncMock for async mock
    mock_app = AsyncMock()
    mock_app.ainvoke.return_value = final_state

    with patch.object(service, "build_workflow") as mock_build:
        mock_workflow = MagicMock()
        mock_workflow.compile.return_value = mock_app
        mock_build.return_value = mock_workflow

        result = await service.generate_mcqs_for_quiz(
            quiz_id=sample_quiz_id,
            target_question_count=1,
            llm_model="gpt-4o",
            llm_temperature=0.3,
        )

        assert result["success"] is True
        assert result["questions_generated"] == 1
        assert result["quiz_id"] == str(sample_quiz_id)
        assert result["error_message"] is None


@pytest.mark.asyncio
async def test_generate_mcqs_for_quiz_failure(sample_quiz_id: UUID) -> None:
    """Test MCQ generation workflow failure handling."""
    service = MCQGenerationService()

    with patch.object(
        service, "build_workflow", side_effect=Exception("Workflow error")
    ):
        result = await service.generate_mcqs_for_quiz(
            quiz_id=sample_quiz_id,
            target_question_count=1,
            llm_model="gpt-4o",
            llm_temperature=0.3,
        )

        assert result["success"] is False
        assert result["questions_generated"] == 0
        assert "Workflow error" in result["error_message"]


def test_global_service_instance_exists() -> None:
    """Test that the global service instance is created."""
    assert mcq_generation_service is not None
    assert isinstance(mcq_generation_service, MCQGenerationService)
