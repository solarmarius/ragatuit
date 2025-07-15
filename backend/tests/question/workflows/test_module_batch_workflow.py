"""Tests for module batch workflow."""

import json
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.question.providers import (
    LLMConfiguration,
    LLMMessage,
    LLMModel,
    LLMProvider,
    LLMResponse,
)
from src.question.providers.base import DEFAULT_TEMPERATURE, BaseLLMProvider
from src.question.templates.manager import TemplateManager
from src.question.types import (
    GenerationParameters,
    Question,
    QuestionType,
    QuizLanguage,
)


class MockLLMProvider(BaseLLMProvider):
    """Mock implementation of LLM provider."""

    def __init__(self, response_content: str = ""):
        config = LLMConfiguration(
            provider=LLMProvider.OPENAI,
            model="test-model",
            temperature=DEFAULT_TEMPERATURE,
        )
        super().__init__(config)
        self.response_content = response_content
        self._models = [
            LLMModel(
                model_id="test-model",
                display_name="Test Model",
                provider=LLMProvider.OPENAI,
                max_tokens=4000,
            )
        ]

    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.OPENAI

    async def initialize(self) -> None:
        self._initialized = True

    async def generate(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            content=self.response_content,
            model="test-model",
            provider=LLMProvider.OPENAI,
            response_time=1.0,
            total_tokens=100,
        )

    async def get_available_models(self) -> list[LLMModel]:
        return self._models

    def validate_configuration(self) -> None:
        pass


class MockTemplateManager(TemplateManager):
    """Mock implementation of template manager."""

    def __init__(self):
        # Don't call super().__init__() to avoid file system operations
        self._template_cache = {}
        self._jinja_cache = {}
        self._initialized = True

    async def create_messages(
        self,
        question_type: QuestionType,
        content: str,
        generation_parameters: GenerationParameters,
        template_name: str | None = None,
        language: QuizLanguage | str | None = None,
        extra_variables: dict[str, Any] | None = None,
    ) -> list[LLMMessage]:
        """Return test messages."""
        return [
            LLMMessage(role="system", content="Test system prompt"),
            LLMMessage(role="user", content=f"Generate questions from: {content}"),
        ]


@pytest.fixture
def test_llm_provider():
    """Create test LLM provider."""
    valid_response = json.dumps(
        [
            {
                "question_text": "What is the capital of France?",
                "option_a": "London",
                "option_b": "Berlin",
                "option_c": "Paris",
                "option_d": "Madrid",
                "correct_answer": "C",
                "explanation": "Paris is the capital of France.",
            }
        ]
    )
    return MockLLMProvider(response_content=valid_response)


@pytest.fixture
def test_template_manager():
    """Create test template manager."""
    return MockTemplateManager()


@pytest.fixture
def valid_mcq_response():
    """Valid MCQ JSON response."""
    return json.dumps(
        [
            {
                "question_text": "What is the capital of France?",
                "option_a": "London",
                "option_b": "Berlin",
                "option_c": "Paris",
                "option_d": "Madrid",
                "correct_answer": "C",
                "explanation": "Paris is the capital of France.",
            },
            {
                "question_text": "What is 2 + 2?",
                "option_a": "3",
                "option_b": "4",
                "option_c": "5",
                "option_d": "6",
                "correct_answer": "B",
                "explanation": "2 + 2 equals 4.",
            },
        ]
    )


# Unit Tests - Core Functionality


def test_workflow_initialization(test_llm_provider, test_template_manager):
    """Test workflow initialization."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        language=QuizLanguage.ENGLISH,
    )

    assert workflow.llm_provider == test_llm_provider
    assert workflow.template_manager == test_template_manager
    assert workflow.language == QuizLanguage.ENGLISH
    assert workflow.graph is not None


def test_parse_batch_response_valid_json(
    test_llm_provider, test_template_manager, valid_mcq_response
):
    """Test parsing valid JSON response."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    result = workflow._parse_batch_response(valid_mcq_response)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["question_text"] == "What is the capital of France?"


def test_parse_batch_response_with_markdown(
    test_llm_provider, test_template_manager, valid_mcq_response
):
    """Test parsing JSON response with markdown code blocks."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    markdown_response = f"```json\n{valid_mcq_response}\n```"
    result = workflow._parse_batch_response(markdown_response)

    assert isinstance(result, list)
    assert len(result) == 2


def test_parse_batch_response_invalid_json(test_llm_provider, test_template_manager):
    """Test parsing invalid JSON response."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    with pytest.raises(ValueError, match="LLM response was not valid JSON"):
        workflow._parse_batch_response("Invalid JSON")


def test_validate_mcq_structure_valid(test_llm_provider, test_template_manager):
    """Test validating valid MCQ structure."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    valid_question = {
        "question_text": "What is 2 + 2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": "B",
    }

    # Should not raise exception
    workflow._validate_mcq_structure(valid_question)


def test_validate_mcq_structure_missing_field(test_llm_provider, test_template_manager):
    """Test validating MCQ structure with missing field."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    invalid_question = {
        "question_text": "What is 2 + 2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        # Missing option_d and correct_answer
    }

    with pytest.raises(ValueError, match="Missing required field"):
        workflow._validate_mcq_structure(invalid_question)


def test_validate_mcq_structure_invalid_answer(
    test_llm_provider, test_template_manager
):
    """Test validating MCQ structure with invalid correct answer."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    invalid_question = {
        "question_text": "What is 2 + 2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": "E",  # Invalid answer
    }

    with pytest.raises(ValueError, match="Invalid correct answer"):
        workflow._validate_mcq_structure(invalid_question)


def test_processor_initialization(test_llm_provider, test_template_manager):
    """Test processor initialization."""
    from src.question.workflows.module_batch_workflow import ParallelModuleProcessor

    processor = ParallelModuleProcessor(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        language=QuizLanguage.ENGLISH,
    )

    assert processor.llm_provider == test_llm_provider
    assert processor.template_manager == test_template_manager
    assert processor.language == QuizLanguage.ENGLISH


# Integration Tests - Workflow Components


@pytest.mark.asyncio
async def test_state_creation_with_valid_providers(
    test_llm_provider, test_template_manager
):
    """Test ModuleBatchState creation with valid providers."""
    from src.question.workflows.module_batch_workflow import ModuleBatchState

    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test-module",
        module_name="Test Module",
        module_content="Test content for generating questions",
        target_question_count=5,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    assert state.module_id == "test-module"
    assert state.module_name == "Test Module"
    assert state.target_question_count == 5
    assert state.language == QuizLanguage.ENGLISH
    assert len(state.generated_questions) == 0
    assert state.retry_count == 0


@pytest.mark.asyncio
async def test_prepare_prompt_workflow_node(test_llm_provider, test_template_manager):
    """Test prepare_prompt workflow node."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test-module",
        module_name="Test Module",
        module_content="Test content for generating questions",
        target_question_count=5,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    result = await workflow.prepare_prompt(state)

    assert result.error_message is None
    assert "Test system prompt" in result.current_prompt
    assert "Generate questions from:" in result.current_prompt


@pytest.mark.asyncio
async def test_generate_batch_workflow_node(test_llm_provider, test_template_manager):
    """Test generate_batch workflow node."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test-module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=5,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        current_prompt="Generate questions about France",
    )

    result = await workflow.generate_batch(state)

    assert result.error_message is None
    assert result.raw_response is not None
    assert "Paris is the capital of France" in result.raw_response


@pytest.mark.asyncio
async def test_validate_batch_workflow_node(
    test_llm_provider, test_template_manager, valid_mcq_response
):
    """Test validate_batch workflow node."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test-module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=5,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        raw_response=valid_mcq_response,
    )

    result = await workflow.validate_batch(state)

    assert result.error_message is None
    assert len(result.generated_questions) == 2

    # Check first question
    q1 = result.generated_questions[0]
    assert isinstance(q1, Question)
    assert q1.question_type == QuestionType.MULTIPLE_CHOICE
    assert q1.question_data["question_text"] == "What is the capital of France?"
    assert q1.question_data["correct_answer"] == "C"


@pytest.mark.asyncio
async def test_validate_batch_invalid_json_workflow_node(
    test_llm_provider, test_template_manager
):
    """Test validate_batch with invalid JSON."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test-module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=5,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        raw_response="Invalid JSON response",
    )

    result = await workflow.validate_batch(state)

    assert result.error_message and "JSON_PARSE_ERROR" in result.error_message
    assert result.parsing_error is True
    assert len(result.generated_questions) == 0


def test_check_json_error_conditions(test_llm_provider, test_template_manager):
    """Test JSON error checking conditions."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    # Needs correction
    state_needs_correction = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        parsing_error=True,
        correction_attempts=0,
        max_corrections=2,
    )

    assert workflow.check_json_error(state_needs_correction) == "needs_correction"

    # Continue (no error)
    state_continue = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        parsing_error=False,
    )

    assert workflow.check_json_error(state_continue) == "continue"


def test_should_retry_conditions(test_llm_provider, test_template_manager):
    """Test should_retry conditions."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    # Complete (enough questions)
    mock_questions = [
        Question(
            quiz_id=uuid4(),
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={
                "question_text": f"Test question {i}",
                "correct_answer": "A",
            },
            is_approved=False,
        )
        for i in range(5)
    ]
    state_complete = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        generated_questions=mock_questions,
    )

    assert workflow.should_retry(state_complete) == "complete"

    # Retry needed
    state_retry = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        generated_questions=[],
        retry_count=1,
        max_retries=3,
    )

    assert workflow.should_retry(state_retry) == "retry"

    # Failed (has error)
    state_failed = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        error_message="Critical error",
    )

    assert workflow.should_retry(state_failed) == "failed"


# End-to-End Tests


@pytest.mark.asyncio
async def test_process_module_success(test_llm_provider, test_template_manager):
    """Test successful module processing end-to-end."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    # Mock database operations
    with patch(
        "src.question.workflows.module_batch_workflow.get_async_session"
    ) as mock_session_factory:
        # Create a mock async context manager for the session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_session

        questions = await workflow.process_module(
            quiz_id=uuid4(),
            module_id="123",
            module_name="Test Module",
            module_content="Test content for question generation",
            question_count=1,  # Should match the single question in test provider
        )

    assert len(questions) == 1
    assert all(isinstance(q, Question) for q in questions)
    assert (
        questions[0].question_data["question_text"] == "What is the capital of France?"
    )


@pytest.mark.asyncio
async def test_process_all_modules_success(test_llm_provider, test_template_manager):
    """Test successful processing of multiple modules."""
    from src.question.workflows.module_batch_workflow import ParallelModuleProcessor

    processor = ParallelModuleProcessor(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    modules_data = {
        "mod1": {"name": "Module 1", "content": "Content 1", "question_count": 1},
        "mod2": {"name": "Module 2", "content": "Content 2", "question_count": 1},
    }

    # Mock database operations
    with patch("src.question.workflows.module_batch_workflow.get_async_session"):
        results = await processor.process_all_modules(
            quiz_id=uuid4(),
            modules_data=modules_data,
        )

    assert len(results) == 2
    assert "mod1" in results
    assert "mod2" in results
    assert len(results["mod1"]) == 1
    assert len(results["mod2"]) == 1


@pytest.mark.asyncio
async def test_process_module_with_retry(test_llm_provider, test_template_manager):
    """Test module processing with retry mechanism."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    # Create provider that returns invalid JSON first, then valid
    class RetryTestProvider(MockLLMProvider):
        def __init__(self):
            super().__init__()
            self.call_count = 0

        async def generate(
            self, messages: list[LLMMessage], **kwargs: Any
        ) -> LLMResponse:
            self.call_count += 1
            if self.call_count == 1:
                # First call returns invalid JSON
                content = "Invalid JSON response"
            else:
                # Second call returns valid JSON
                content = json.dumps(
                    [
                        {
                            "question_text": "What is the capital of France?",
                            "option_a": "London",
                            "option_b": "Berlin",
                            "option_c": "Paris",
                            "option_d": "Madrid",
                            "correct_answer": "C",
                        }
                    ]
                )

            return LLMResponse(
                content=content,
                model="test-model",
                provider=LLMProvider.OPENAI,
                response_time=1.0,
                total_tokens=100,
            )

    retry_provider = RetryTestProvider()
    workflow = ModuleBatchWorkflow(
        llm_provider=retry_provider,
        template_manager=test_template_manager,
    )

    # Mock database operations
    with patch("src.question.workflows.module_batch_workflow.get_async_session"):
        questions = await workflow.process_module(
            quiz_id=uuid4(),
            module_id="123",
            module_name="Test Module",
            module_content="Test content",
            question_count=1,
        )

    assert len(questions) == 1
    assert retry_provider.call_count >= 2  # Should have retried


# Error Handling Tests


@pytest.mark.asyncio
async def test_process_module_handles_exceptions(test_template_manager):
    """Test that module processing handles exceptions gracefully."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    # Create provider that always raises an exception
    class FailingProvider(MockLLMProvider):
        async def generate(
            self, messages: list[LLMMessage], **kwargs: Any
        ) -> LLMResponse:
            raise Exception("API Error")

    failing_provider = FailingProvider()
    workflow = ModuleBatchWorkflow(
        llm_provider=failing_provider,
        template_manager=test_template_manager,
    )

    questions = await workflow.process_module(
        quiz_id=uuid4(),
        module_id="123",
        module_name="Test Module",
        module_content="Test content",
        question_count=5,
    )

    # Should return empty list when all attempts fail
    assert len(questions) == 0


def test_json_parsing_edge_cases():
    """Test JSON parsing handles various edge cases."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=MockLLMProvider(),
        template_manager=MockTemplateManager(),
    )

    # Empty JSON array
    result = workflow._parse_batch_response("[]")
    assert result == []

    # JSON with extra whitespace
    valid_json = '[{"question_text": "Test", "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D", "correct_answer": "A"}]'
    result = workflow._parse_batch_response(f"  \n{valid_json}\n  ")
    assert len(result) == 1

    # JSON with nested markdown (should only clean outer blocks)
    markdown_json = f"```json\n{valid_json}\n```"
    result = workflow._parse_batch_response(markdown_json)
    assert len(result) == 1


def test_mcq_validation_edge_cases():
    """Test MCQ validation handles various edge cases."""
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=MockLLMProvider(),
        template_manager=MockTemplateManager(),
    )

    # Question text too short
    short_question = {
        "question_text": "Test?",  # Too short
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_answer": "A",
    }

    with pytest.raises(ValueError, match="Question text too short"):
        workflow._validate_mcq_structure(short_question)

    # Empty option
    empty_option = {
        "question_text": "What is the capital of France?",
        "option_a": "",  # Empty option
        "option_b": "Berlin",
        "option_c": "Paris",
        "option_d": "Madrid",
        "correct_answer": "C",
    }

    with pytest.raises(ValueError, match="Option option_a is empty"):
        workflow._validate_mcq_structure(empty_option)
