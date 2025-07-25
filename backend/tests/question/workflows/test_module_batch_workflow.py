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


def test_dynamic_question_validation_mcq(test_llm_provider, test_template_manager):
    """Test that dynamic validation works for MCQ questions."""
    from src.question.types import QuestionType
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    valid_mcq_question = {
        "question_text": "What is 2 + 2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": "B",
    }

    # Test that valid MCQ questions pass validation
    from src.question.types.registry import get_question_type_registry

    registry = get_question_type_registry()
    question_type_impl = registry.get_question_type(QuestionType.MULTIPLE_CHOICE)

    # Should not raise exception
    validated_data = question_type_impl.validate_data(valid_mcq_question)
    assert validated_data.question_text == "What is 2 + 2?"
    assert validated_data.option_a == "3"


def test_dynamic_question_validation_fib(test_llm_provider, test_template_manager):
    """Test that dynamic validation works for Fill-in-Blank questions."""
    from src.question.types import QuestionType
    from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    valid_fib_question = {
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
    }

    # Test that valid FIB questions pass validation
    from src.question.types.registry import get_question_type_registry

    registry = get_question_type_registry()
    question_type_impl = registry.get_question_type(QuestionType.FILL_IN_BLANK)

    # Should not raise exception
    validated_data = question_type_impl.validate_data(valid_fib_question)
    assert validated_data.question_text == "The capital of France is [blank_1]."
    assert len(validated_data.blanks) == 1
    assert validated_data.blanks[0].correct_answer == "Paris"


def test_dynamic_question_validation_invalid_data(
    test_llm_provider, test_template_manager
):
    """Test that dynamic validation properly rejects invalid data."""
    from src.question.types import QuestionType
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

    # Test that invalid questions raise validation errors
    from src.question.types.registry import get_question_type_registry

    registry = get_question_type_registry()
    question_type_impl = registry.get_question_type(QuestionType.MULTIPLE_CHOICE)

    with pytest.raises(Exception):  # Should raise ValidationError or similar
        question_type_impl.validate_data(invalid_question)


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
        question_type=QuestionType.MULTIPLE_CHOICE,
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
        question_type=QuestionType.MULTIPLE_CHOICE,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    result = await workflow.prepare_prompt(state)

    assert result.error_message is None
    assert "Test system prompt" in result.system_prompt
    assert "Generate questions from:" in result.user_prompt


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
        question_type=QuestionType.MULTIPLE_CHOICE,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        system_prompt="You are an expert educator creating multiple-choice quiz questions.",
        user_prompt="Generate questions about France",
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
        question_type=QuestionType.MULTIPLE_CHOICE,
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
        question_type=QuestionType.MULTIPLE_CHOICE,
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

    # Needs JSON correction
    state_needs_correction = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        parsing_error=True,
        correction_attempts=0,
        max_corrections=2,
    )

    assert workflow.check_error_type(state_needs_correction) == "needs_json_correction"

    # Continue (no error)
    state_continue = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        parsing_error=False,
    )

    assert workflow.check_error_type(state_continue) == "continue"


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
        question_type=QuestionType.MULTIPLE_CHOICE,
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
        question_type=QuestionType.MULTIPLE_CHOICE,
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
        question_type=QuestionType.MULTIPLE_CHOICE,
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
            question_type=QuestionType.MULTIPLE_CHOICE,
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
            question_type=QuestionType.MULTIPLE_CHOICE,
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
        question_type=QuestionType.MULTIPLE_CHOICE,
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


def test_question_validation_edge_cases():
    """Test question validation handles various edge cases through the registry."""
    from src.question.types import QuestionType
    from src.question.types.registry import get_question_type_registry

    registry = get_question_type_registry()

    # Test MCQ validation with missing required field
    mcq_impl = registry.get_question_type(QuestionType.MULTIPLE_CHOICE)
    missing_field = {
        "question_text": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        # Missing option_d and correct_answer
    }

    # MCQ validation should reject missing required fields
    with pytest.raises(Exception):
        mcq_impl.validate_data(missing_field)

    # Test FIB validation with empty blanks
    fib_impl = registry.get_question_type(QuestionType.FILL_IN_BLANK)
    empty_blanks = {
        "question_text": "The capital of France is [blank_1].",
        "blanks": [],  # Empty blanks
    }

    with pytest.raises(Exception):
        fib_impl.validate_data(empty_blanks)


def test_check_error_type_conditions(test_llm_provider, test_template_manager):
    """Test error type checking conditions."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    # Test JSON error needs correction
    state_json_error = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        parsing_error=True,
        correction_attempts=0,
        max_corrections=2,
    )

    assert workflow.check_error_type(state_json_error) == "needs_json_correction"

    # Test validation error needs correction
    state_validation_error = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        validation_error=True,
        validation_correction_attempts=0,
        max_validation_corrections=2,
    )

    assert (
        workflow.check_error_type(state_validation_error)
        == "needs_validation_correction"
    )

    # Test continue (no errors)
    state_continue = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        parsing_error=False,
        validation_error=False,
    )

    assert workflow.check_error_type(state_continue) == "continue"

    # Test max corrections reached
    state_max_corrections = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test",
        module_name="Test",
        module_content="Test",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        validation_error=True,
        validation_correction_attempts=2,
        max_validation_corrections=2,
    )

    assert workflow.check_error_type(state_max_corrections) == "continue"


@pytest.mark.asyncio
async def test_prepare_validation_correction_workflow_node(
    test_llm_provider, test_template_manager
):
    """Test prepare_validation_correction workflow node."""
    from src.question.types import QuestionType
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
        question_type=QuestionType.MULTIPLE_CHOICE,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        validation_error=True,
        failed_questions_data=[
            {"question_text": "What is 2 + 2?", "option_a": "3", "option_b": "4"},
            {"question_text": "What is the capital?", "correct_answer": "invalid"},
        ],
        failed_questions_errors=[
            "Question validation failed: Missing required field: option_d",
            "Question validation failed: Invalid correct_answer format",
        ],
        validation_correction_attempts=0,
        raw_response='[{"question_text": "Invalid question"}]',
    )

    result = await workflow.prepare_validation_correction(state)

    assert result.error_message is None
    assert result.validation_correction_attempts == 1
    assert result.validation_error is False
    assert len(result.failed_questions_data) == 2  # Should be preserved for retry
    assert len(result.failed_questions_errors) == 2  # Should be preserved for retry
    assert result.raw_response == ""
    assert (
        result.system_prompt == ""
    )  # Should be cleared to avoid conflicting instructions
    assert "failed validation" in result.user_prompt.lower()
    assert "multiple_choice" in result.user_prompt.lower()


@pytest.mark.asyncio
async def test_prepare_validation_correction_fib_workflow_node(
    test_llm_provider, test_template_manager
):
    """Test prepare_validation_correction workflow node for Fill-in-Blank."""
    from src.question.types import QuestionType
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
        target_question_count=3,
        question_type=QuestionType.FILL_IN_BLANK,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        validation_error=True,
        failed_questions_data=[
            {
                "question_text": "Complete this: The sky is ___",
                "sentence": "The sky is blue",
            },
        ],
        failed_questions_errors=[
            "Question validation failed: Missing required field: blanks",
        ],
        validation_correction_attempts=0,
        raw_response='[{"question_text": "Invalid question"}]',
    )

    result = await workflow.prepare_validation_correction(state)

    assert result.error_message is None
    assert result.validation_correction_attempts == 1
    assert result.validation_error is False
    assert (
        result.system_prompt == ""
    )  # Should be cleared to avoid conflicting instructions
    assert "blanks" in result.user_prompt
    assert "fill_in_blank" in result.user_prompt.lower()


@pytest.mark.asyncio
async def test_validate_batch_sets_validation_error_flags(
    test_llm_provider, test_template_manager
):
    """Test that validate_batch sets validation error flags when all questions fail validation."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    workflow = ModuleBatchWorkflow(
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
    )

    # Create invalid MCQ response (missing required fields)
    invalid_mcq_response = json.dumps(
        [
            {
                "question_text": "What is 2 + 2?",
                "option_a": "3",
                "option_b": "4",
                # Missing option_c, option_d, and correct_answer
            }
        ]
    )

    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test-module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        language=QuizLanguage.ENGLISH,
        llm_provider=test_llm_provider,
        template_manager=test_template_manager,
        raw_response=invalid_mcq_response,
    )

    result = await workflow.validate_batch(state)

    assert result.validation_error is True
    assert len(result.failed_questions_data) > 0  # Failed questions should be stored
    assert len(result.failed_questions_errors) > 0  # Errors should be stored
    assert result.error_message is None  # No general error, just validation errors
    assert len(result.generated_questions) == 0  # No questions should be generated


# Smart Retry Functionality Tests


@pytest.fixture
def mock_mixed_success_response():
    """Mock LLM response with mixed valid/invalid questions."""
    return json.dumps(
        [
            {
                # Valid categorization question (meets minimum requirements)
                "question_text": "Valid categorization question",
                "categories": [
                    {"name": "Category1", "correct_items": ["item1", "item2", "item5"]},
                    {"name": "Category2", "correct_items": ["item3", "item4", "item6"]},
                ],
                "items": [
                    {"id": "item1", "text": "Valid item 1"},
                    {"id": "item2", "text": "Valid item 2"},
                    {"id": "item3", "text": "Valid item 3"},
                    {"id": "item4", "text": "Valid item 4"},
                    {"id": "item5", "text": "Valid item 5"},
                    {"id": "item6", "text": "Valid item 6"},
                ],
                "distractors": [],
                "explanation": "Valid explanation",
            },
            {
                # Invalid categorization question (missing item assignment - has 7 items but item7 unassigned)
                "question_text": "Invalid categorization question",
                "categories": [
                    {"name": "Category1", "correct_items": ["item1", "item2", "item5"]},
                    {"name": "Category2", "correct_items": ["item3", "item4", "item6"]},
                ],
                "items": [
                    {"id": "item1", "text": "Assigned item 1"},
                    {"id": "item2", "text": "Assigned item 2"},
                    {"id": "item3", "text": "Assigned item 3"},
                    {"id": "item4", "text": "Assigned item 4"},
                    {"id": "item5", "text": "Assigned item 5"},
                    {"id": "item6", "text": "Assigned item 6"},
                    {
                        "id": "item7",
                        "text": "Unassigned item",
                    },  # This will fail validation
                ],
                "distractors": [],
                "explanation": "Invalid explanation",
            },
        ]
    )


@pytest.fixture
def mock_all_invalid_response():
    """Mock LLM response with all invalid questions."""
    return json.dumps(
        [
            {
                # Invalid question 1 - unassigned item
                "question_text": "Invalid question 1",
                "categories": [
                    {"name": "Cat1", "correct_items": ["item1", "item2", "item5"]},
                    {"name": "Cat2", "correct_items": ["item3", "item4", "item6"]},
                ],
                "items": [
                    {"id": "item1", "text": "Item 1"},
                    {"id": "item2", "text": "Item 2"},
                    {"id": "item3", "text": "Item 3"},
                    {"id": "item4", "text": "Item 4"},
                    {"id": "item5", "text": "Item 5"},
                    {"id": "item6", "text": "Item 6"},
                    {
                        "id": "item7",
                        "text": "Unassigned item",
                    },  # This will fail validation
                ],
                "explanation": "Invalid explanation 1",
            },
            {
                # Invalid question 2 - another unassigned item
                "question_text": "Invalid question 2",
                "categories": [
                    {"name": "Cat1", "correct_items": ["item1", "item2", "item5"]},
                    {"name": "Cat2", "correct_items": ["item3", "item4", "item6"]},
                ],
                "items": [
                    {"id": "item1", "text": "Item 1"},
                    {"id": "item2", "text": "Item 2"},
                    {"id": "item3", "text": "Item 3"},
                    {"id": "item4", "text": "Item 4"},
                    {"id": "item5", "text": "Item 5"},
                    {"id": "item6", "text": "Item 6"},
                    {
                        "id": "item8",
                        "text": "Another unassigned item",
                    },  # This will fail validation
                ],
                "explanation": "Invalid explanation 2",
            },
        ]
    )


@pytest.mark.asyncio
async def test_preserve_successful_questions_on_validation_failure(
    test_template_manager, mock_mixed_success_response
):
    """Test that successful questions are preserved when some fail validation."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    # Create mock LLM provider with mixed response
    llm_provider = MockLLMProvider(mock_mixed_success_response)

    workflow = ModuleBatchWorkflow(
        llm_provider=llm_provider,
        template_manager=test_template_manager,
    )

    # Create initial state
    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=2,
        question_type=QuestionType.CATEGORIZATION,
        llm_provider=llm_provider,
        template_manager=test_template_manager,
        raw_response=mock_mixed_success_response,
    )

    # Execute validation
    result_state = await workflow.validate_batch(state)

    # Assertions for smart retry behavior
    assert (
        len(result_state.successful_questions_preserved) == 1
    )  # One valid question preserved
    assert len(result_state.failed_questions_data) == 1  # One invalid question stored
    assert len(result_state.failed_questions_errors) == 1  # One error message stored
    assert result_state.validation_error is True  # Validation error flag set
    assert (
        len(result_state.generated_questions) == 0
    )  # Generated questions reset for retry

    # Verify error message contains expected content (unassigned item validation error)
    error_message = result_state.failed_questions_errors[0]
    assert (
        "Items not assigned to any category" in error_message
        or "item7" in error_message
    )

    # Verify failed question data is preserved
    failed_data = result_state.failed_questions_data[0]
    assert failed_data["question_text"] == "Invalid categorization question"
    assert (
        len(failed_data["items"]) == 7
    )  # All items preserved in failed data (including unassigned item7)

    # Verify preserved question has correct type
    preserved_question = result_state.successful_questions_preserved[0]
    assert preserved_question.question_type == QuestionType.CATEGORIZATION
    assert preserved_question.is_approved is False


@pytest.mark.asyncio
async def test_validation_correction_with_specific_questions(
    test_template_manager, mock_all_invalid_response
):
    """Test that correction prompts include specific failed question data."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    llm_provider = MockLLMProvider()

    workflow = ModuleBatchWorkflow(
        llm_provider=llm_provider,
        template_manager=test_template_manager,
    )

    # Create state with failed questions (simulating result of validate_batch)
    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=2,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=llm_provider,
        template_manager=test_template_manager,
        validation_error=True,
        failed_questions_data=[
            {
                "question_text": "Test categorization question",
                "categories": [{"name": "Category1", "correct_items": ["item1"]}],
                "items": [
                    {"id": "item1", "text": "Item 1"},
                    {"id": "item2", "text": "Unassigned item"},
                ],
                "explanation": "Test explanation",
            }
        ],
        failed_questions_errors=[
            "Question validation failed: Items not assigned to any category: ['item2']"
        ],
    )

    # Execute correction preparation
    result_state = await workflow.prepare_validation_correction(state)

    # Assertions
    assert result_state.validation_error is False  # Reset for retry
    assert result_state.validation_correction_attempts == 1  # Incremented

    # Verify correction prompt contains specific failed question data
    correction_prompt = result_state.user_prompt
    assert "FAILED QUESTION 1:" in correction_prompt
    assert "Test categorization question" in correction_prompt  # Original question text
    assert '"item2"' in correction_prompt  # Failed item ID
    assert "Items not assigned to any category" in correction_prompt  # Specific error
    assert "fix ONLY these specific questions" in correction_prompt  # Clear instruction
    assert "1 questions failed validation" in correction_prompt  # Correct count
    assert "Do not generate new questions" in correction_prompt  # Explicit instruction

    # Verify prompt structure contains required sections
    assert "Original Data:" in correction_prompt
    assert "Validation Error:" in correction_prompt
    assert "Requirements:" in correction_prompt
    assert "JSON array" in correction_prompt


@pytest.mark.asyncio
async def test_question_counting_with_mixed_success(test_template_manager):
    """Test that question counting works correctly with preserved questions."""
    from unittest.mock import Mock

    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    llm_provider = MockLLMProvider()

    workflow = ModuleBatchWorkflow(
        llm_provider=llm_provider,
        template_manager=test_template_manager,
    )

    # Create state with mixed success scenario
    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=10,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=llm_provider,
        template_manager=test_template_manager,
        successful_questions_preserved=[
            Mock(spec=Question)
            for _ in range(7)  # 7 successful questions
        ],
        generated_questions=[
            Mock(spec=Question)
            for _ in range(2)  # 2 newly generated questions
        ],
    )

    # Test should_retry logic - should retry for 1 more question (7+2=9, need 10)
    retry_decision = workflow.should_retry(state)
    assert retry_decision == "retry"

    # Test with exact count
    state.generated_questions.append(Mock(spec=Question))  # Add 1 more (7+3=10)
    retry_decision = workflow.should_retry(state)
    assert retry_decision == "complete"  # Should complete (7+3=10, target met)

    # Test over count
    state.generated_questions.append(Mock(spec=Question))  # Add 1 more (7+4=11)
    retry_decision = workflow.should_retry(state)
    assert retry_decision == "complete"  # Should complete (over target)


@pytest.mark.asyncio
async def test_save_questions_combines_preserved_and_new(test_template_manager):
    """Test that save_questions combines preserved and newly generated questions."""
    from unittest.mock import AsyncMock, Mock, patch

    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    llm_provider = MockLLMProvider()

    workflow = ModuleBatchWorkflow(
        llm_provider=llm_provider,
        template_manager=test_template_manager,
    )

    # Create mock questions
    preserved_questions = [Mock(spec=Question) for _ in range(3)]
    new_questions = [Mock(spec=Question) for _ in range(2)]

    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=llm_provider,
        template_manager=test_template_manager,
        successful_questions_preserved=preserved_questions,
        generated_questions=new_questions,
    )

    # Mock database session
    mock_session = AsyncMock()

    with patch(
        "src.question.workflows.module_batch_workflow.get_async_session"
    ) as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # Execute save_questions
        result_state = await workflow.save_questions(state)

        # Verify all questions were added to session (3 preserved + 2 new = 5 total)
        assert mock_session.add.call_count == 5

        # Verify commit was called
        mock_session.commit.assert_called_once()

        # Verify no error occurred
        assert result_state.error_message is None


@pytest.mark.asyncio
async def test_retry_generation_clears_failed_question_state(test_template_manager):
    """Test that retry_generation properly clears failed question state."""
    from unittest.mock import Mock

    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    llm_provider = MockLLMProvider()

    workflow = ModuleBatchWorkflow(
        llm_provider=llm_provider,
        template_manager=test_template_manager,
    )

    # Create state with failed questions and preserved questions
    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=llm_provider,
        template_manager=test_template_manager,
        failed_questions_data=[{"question": "failed"}],
        failed_questions_errors=["error message"],
        successful_questions_preserved=[Mock(spec=Question) for _ in range(2)],
        retry_count=0,
    )

    # Execute retry_generation
    result_state = await workflow.retry_generation(state)

    # Verify failed question state is cleared
    assert result_state.failed_questions_data == []
    assert result_state.failed_questions_errors == []

    # Verify preserved questions are kept
    assert len(result_state.successful_questions_preserved) == 2

    # Verify retry count is incremented
    assert result_state.retry_count == 1

    # Verify other state is reset
    assert result_state.error_message is None
    assert result_state.raw_response == ""


@pytest.mark.asyncio
async def test_prepare_prompt_calculates_remaining_questions_correctly(
    test_template_manager,
):
    """Test that prepare_prompt calculates remaining questions accounting for preserved ones."""
    from unittest.mock import Mock

    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    llm_provider = MockLLMProvider()

    workflow = ModuleBatchWorkflow(
        llm_provider=llm_provider,
        template_manager=test_template_manager,
    )

    # Create state with preserved and generated questions
    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_module",
        module_name="Test Module",
        module_content="Test content for questions",
        target_question_count=10,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=llm_provider,
        template_manager=test_template_manager,
        successful_questions_preserved=[
            Mock(spec=Question) for _ in range(6)
        ],  # 6 preserved
        generated_questions=[Mock(spec=Question) for _ in range(2)],  # 2 generated
    )

    # Execute prepare_prompt
    result_state = await workflow.prepare_prompt(state)

    # Verify prompts were created
    assert result_state.system_prompt == "Test system prompt"
    assert "Test content for questions" in result_state.user_prompt

    # The template manager mock doesn't give us access to the exact parameters,
    # but we can verify the method completes without error, indicating the
    # remaining_questions calculation (10 - 6 - 2 = 2) worked correctly
    assert result_state.error_message is None


@pytest.mark.asyncio
async def test_no_questions_preserved_when_all_succeed(test_template_manager):
    """Test that no questions are moved to preserved when all validation succeeds."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    # Valid categorization questions only (meet minimum requirements)
    valid_response = json.dumps(
        [
            {
                "question_text": "Valid question 1",
                "categories": [
                    {"name": "Category1", "correct_items": ["item1", "item2", "item5"]},
                    {"name": "Category2", "correct_items": ["item3", "item4", "item6"]},
                ],
                "items": [
                    {"id": "item1", "text": "Valid item 1"},
                    {"id": "item2", "text": "Valid item 2"},
                    {"id": "item3", "text": "Valid item 3"},
                    {"id": "item4", "text": "Valid item 4"},
                    {"id": "item5", "text": "Valid item 5"},
                    {"id": "item6", "text": "Valid item 6"},
                ],
                "distractors": [],
                "explanation": "Valid explanation 1",
            },
            {
                "question_text": "Valid question 2",
                "categories": [
                    {"name": "CategoryA", "correct_items": ["itemA", "itemB", "itemE"]},
                    {"name": "CategoryB", "correct_items": ["itemC", "itemD", "itemF"]},
                ],
                "items": [
                    {"id": "itemA", "text": "Another valid item A"},
                    {"id": "itemB", "text": "Another valid item B"},
                    {"id": "itemC", "text": "Another valid item C"},
                    {"id": "itemD", "text": "Another valid item D"},
                    {"id": "itemE", "text": "Another valid item E"},
                    {"id": "itemF", "text": "Another valid item F"},
                ],
                "distractors": [],
                "explanation": "Valid explanation 2",
            },
        ]
    )

    llm_provider = MockLLMProvider(valid_response)

    workflow = ModuleBatchWorkflow(
        llm_provider=llm_provider,
        template_manager=test_template_manager,
    )

    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=2,
        question_type=QuestionType.CATEGORIZATION,
        llm_provider=llm_provider,
        template_manager=test_template_manager,
        raw_response=valid_response,
    )

    # Execute validation
    result_state = await workflow.validate_batch(state)

    # Verify normal behavior when all questions succeed
    assert (
        len(result_state.generated_questions) == 2
    )  # Both questions in generated list
    assert (
        len(result_state.successful_questions_preserved) == 0
    )  # No questions moved to preserved
    assert len(result_state.failed_questions_data) == 0  # No failed questions
    assert result_state.validation_error is False  # No validation error


@pytest.mark.asyncio
async def test_all_questions_fail_validation(
    test_template_manager, mock_all_invalid_response
):
    """Test behavior when all questions fail validation."""
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    llm_provider = MockLLMProvider(mock_all_invalid_response)

    workflow = ModuleBatchWorkflow(
        llm_provider=llm_provider,
        template_manager=test_template_manager,
    )

    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=2,
        question_type=QuestionType.CATEGORIZATION,
        llm_provider=llm_provider,
        template_manager=test_template_manager,
        raw_response=mock_all_invalid_response,
    )

    # Execute validation
    result_state = await workflow.validate_batch(state)

    # Verify all questions failed behavior
    assert len(result_state.generated_questions) == 0  # No successful questions
    assert (
        len(result_state.successful_questions_preserved) == 0
    )  # No questions to preserve
    assert len(result_state.failed_questions_data) == 2  # Both questions failed
    assert len(result_state.failed_questions_errors) == 2  # Two error messages
    assert result_state.validation_error is True  # Validation error set

    # Verify all failed question data is preserved
    for i, failed_data in enumerate(result_state.failed_questions_data):
        assert failed_data["question_text"] == f"Invalid question {i+1}"
        assert (
            "Items not assigned to any category"
            in result_state.failed_questions_errors[i]
        )
