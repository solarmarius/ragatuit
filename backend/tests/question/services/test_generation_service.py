"""Tests for generation orchestration service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def generation_service():
    """Create generation orchestration service instance."""
    from unittest.mock import MagicMock, patch

    from src.question.services.generation_service import GenerationOrchestrationService

    with (
        patch(
            "src.question.services.generation_service.get_configuration_service"
        ) as mock_config_service,
        patch(
            "src.question.services.generation_service.get_llm_provider_registry"
        ) as mock_provider_registry,
        patch(
            "src.question.services.generation_service.get_workflow_registry"
        ) as mock_workflow_registry,
        patch(
            "src.question.services.generation_service.get_template_manager"
        ) as mock_template_manager,
    ):
        service = GenerationOrchestrationService()

        # Replace the actual instances with mocks
        service.config_service = mock_config_service.return_value
        service.provider_registry = mock_provider_registry.return_value
        service.workflow_registry = mock_workflow_registry.return_value
        service.template_manager = mock_template_manager.return_value

        yield service


@pytest.fixture
def generation_parameters():
    """Create test generation parameters."""
    from src.question.types import GenerationParameters, QuestionDifficulty

    return GenerationParameters(
        target_count=5,
        difficulty=QuestionDifficulty.MEDIUM,
        tags=["python", "programming"],
        custom_instructions="Focus on basic concepts",
    )


@pytest.fixture
def mock_generation_result():
    """Create mock generation result."""
    from src.question.types import GenerationResult

    return GenerationResult(
        success=True,
        questions_generated=5,
        target_questions=5,
        error_message=None,
        metadata={
            "quiz_id": str(uuid.uuid4()),
            "question_type": "multiple_choice",
            "provider": "openai",
            "workflow": "mcq_workflow",
        },
    )


@pytest.fixture
def mock_content_chunks():
    """Create mock content chunks."""
    from src.question.workflows import ContentChunk

    return [
        ContentChunk(
            content="Python is a programming language.",
            source="module_1/page_1",
            metadata={"module_id": "module_1", "page_id": "page_1"},
        ),
        ContentChunk(
            content="Variables store data values.",
            source="module_1/page_2",
            metadata={"module_id": "module_1", "page_id": "page_2"},
        ),
    ]


def test_generation_service_initialization(generation_service):
    """Test generation service initialization."""
    assert generation_service.config_service is not None
    assert generation_service.provider_registry is not None
    assert generation_service.workflow_registry is not None
    assert generation_service.template_manager is not None


@pytest.mark.asyncio
async def test_generate_questions_success(
    generation_service,
    generation_parameters,
    mock_generation_result,
    mock_content_chunks,
):
    """Test successful question generation."""
    from src.question.types import QuestionType

    quiz_id = uuid.uuid4()
    question_type = QuestionType.MULTIPLE_CHOICE

    with (
        patch.object(
            generation_service, "_validate_generation_request"
        ) as mock_validate,
        patch.object(
            generation_service.config_service, "get_config"
        ) as mock_get_config,
        patch.object(
            generation_service.config_service, "get_provider_config"
        ) as mock_get_provider_config,
        patch.object(
            generation_service.config_service, "get_workflow_config"
        ) as mock_get_workflow_config,
        patch(
            "src.question.services.generation_service.ContentProcessingService"
        ) as mock_content_service_class,
    ):
        # Mock configuration
        mock_config = MagicMock()
        mock_config.enable_duplicate_detection = False
        mock_get_config.return_value = mock_config

        mock_provider_config = MagicMock()
        mock_provider_config.provider = MagicMock()
        mock_provider_config.model = "gpt-4"
        mock_provider_config.temperature = 0.7
        mock_provider_config.max_retries = 3
        mock_get_provider_config.return_value = mock_provider_config

        mock_workflow_config = MagicMock()
        mock_workflow_config.max_chunk_size = 1000
        mock_workflow_config.quality_threshold = 0.5
        mock_get_workflow_config.return_value = mock_workflow_config

        # Mock content service
        mock_content_service = MagicMock()
        mock_content_service.prepare_content_for_generation = AsyncMock(
            return_value=mock_content_chunks
        )
        mock_content_service.get_content_statistics.return_value = {
            "total_characters": 500,
            "avg_chunk_size": 250,
        }
        mock_content_service_class.return_value = mock_content_service

        # Mock provider registry
        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider
        generation_service.provider_registry.get_available_providers.return_value = [
            MagicMock()
        ]

        # Mock workflow registry
        mock_workflow = MagicMock()
        mock_workflow.workflow_name = "mcq_workflow"
        mock_workflow.execute = AsyncMock(return_value=mock_generation_result)
        generation_service.workflow_registry.get_workflow.return_value = mock_workflow

        result = await generation_service.generate_questions(
            quiz_id=quiz_id,
            question_type=question_type,
            generation_parameters=generation_parameters,
        )

    assert result.success is True
    assert result.questions_generated == 5
    assert result.target_questions == 5
    mock_validate.assert_called_once_with(question_type, generation_parameters)
    mock_workflow.execute.assert_called_once()


@pytest.mark.asyncio
async def test_generate_questions_no_content_chunks(
    generation_service, generation_parameters
):
    """Test question generation when no content chunks are found."""
    from src.question.types import QuestionType

    quiz_id = uuid.uuid4()
    question_type = QuestionType.MULTIPLE_CHOICE

    with (
        patch.object(generation_service, "_validate_generation_request"),
        patch.object(
            generation_service.config_service, "get_config"
        ) as mock_get_config,
        patch.object(generation_service.config_service, "get_provider_config"),
        patch.object(generation_service.config_service, "get_workflow_config"),
        patch(
            "src.question.services.generation_service.ContentProcessingService"
        ) as mock_content_service_class,
    ):
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Mock content service returns empty chunks
        mock_content_service = MagicMock()
        mock_content_service.prepare_content_for_generation = AsyncMock(return_value=[])
        mock_content_service_class.return_value = mock_content_service

        generation_service.provider_registry.get_available_providers.return_value = [
            MagicMock()
        ]

        result = await generation_service.generate_questions(
            quiz_id=quiz_id,
            question_type=question_type,
            generation_parameters=generation_parameters,
        )

    assert result.success is False
    assert result.questions_generated == 0
    assert "No valid content chunks found" in result.error_message


@pytest.mark.asyncio
async def test_generate_questions_with_quality_filtering(
    generation_service, generation_parameters, mock_content_chunks
):
    """Test question generation with quality filtering enabled."""
    from src.question.types import QuestionType

    quiz_id = uuid.uuid4()
    question_type = QuestionType.MULTIPLE_CHOICE

    with (
        patch.object(generation_service, "_validate_generation_request"),
        patch.object(
            generation_service.config_service, "get_config"
        ) as mock_get_config,
        patch.object(generation_service.config_service, "get_provider_config"),
        patch.object(generation_service.config_service, "get_workflow_config"),
        patch(
            "src.question.services.generation_service.ContentProcessingService"
        ) as mock_content_service_class,
    ):
        # Enable quality filtering
        mock_config = MagicMock()
        mock_config.enable_duplicate_detection = True
        mock_get_config.return_value = mock_config

        # Mock content service
        mock_content_service = MagicMock()
        mock_content_service.prepare_content_for_generation = AsyncMock(
            return_value=mock_content_chunks
        )
        mock_content_service.validate_content_quality.return_value = mock_content_chunks
        mock_content_service.get_content_statistics.return_value = {
            "total_characters": 500
        }
        mock_content_service_class.return_value = mock_content_service

        # Mock other dependencies
        generation_service.provider_registry.get_available_providers.return_value = [
            MagicMock()
        ]
        generation_service.provider_registry.get_provider.return_value = MagicMock()

        mock_workflow = MagicMock()
        mock_workflow.workflow_name = "test_workflow"
        mock_workflow.execute = AsyncMock(
            return_value=MagicMock(success=True, metadata={})
        )
        generation_service.workflow_registry.get_workflow.return_value = mock_workflow

        await generation_service.generate_questions(
            quiz_id=quiz_id,
            question_type=question_type,
            generation_parameters=generation_parameters,
        )

    # Verify quality filtering was called
    mock_content_service.validate_content_quality.assert_called_once_with(
        mock_content_chunks
    )


@pytest.mark.asyncio
async def test_generate_questions_exception_handling(
    generation_service, generation_parameters
):
    """Test exception handling in question generation."""
    from src.question.types import QuestionType

    quiz_id = uuid.uuid4()
    question_type = QuestionType.MULTIPLE_CHOICE

    with patch.object(
        generation_service, "_validate_generation_request"
    ) as mock_validate:
        mock_validate.side_effect = Exception("Validation error")

        result = await generation_service.generate_questions(
            quiz_id=quiz_id,
            question_type=question_type,
            generation_parameters=generation_parameters,
        )

    assert result.success is False
    assert result.questions_generated == 0
    assert "Generation failed: Validation error" in result.error_message
    assert result.metadata["error_type"] == "Exception"


@pytest.mark.asyncio
async def test_batch_generate_questions_success(generation_service):
    """Test successful batch question generation."""
    from src.question.types import GenerationResult

    requests = [
        {
            "quiz_id": str(uuid.uuid4()),
            "question_type": "multiple_choice",
            "generation_parameters": {"target_count": 3, "difficulty": "medium"},
        },
        {
            "quiz_id": str(uuid.uuid4()),
            "question_type": "true_false",
            "generation_parameters": {"target_count": 2, "difficulty": "easy"},
        },
    ]

    mock_result_1 = GenerationResult(
        success=True, questions_generated=3, target_questions=3
    )
    mock_result_2 = GenerationResult(
        success=True, questions_generated=2, target_questions=2
    )

    with patch.object(generation_service, "generate_questions") as mock_generate:
        mock_generate.side_effect = [mock_result_1, mock_result_2]

        results = await generation_service.batch_generate_questions(requests)

    assert len(results) == 2
    assert all(result.success for result in results)
    assert results[0].questions_generated == 3
    assert results[1].questions_generated == 2


@pytest.mark.asyncio
async def test_batch_generate_questions_with_failures(generation_service):
    """Test batch generation with some failures."""
    from src.question.types import GenerationResult

    requests = [
        {
            "quiz_id": str(uuid.uuid4()),
            "question_type": "multiple_choice",
            "generation_parameters": {"target_count": 3, "difficulty": "medium"},
        },
        {
            "quiz_id": "invalid_uuid",  # Invalid UUID
            "question_type": "true_false",
            "generation_parameters": {"target_count": 2, "difficulty": "easy"},
        },
    ]

    mock_success_result = GenerationResult(
        success=True, questions_generated=3, target_questions=3
    )

    with patch.object(generation_service, "generate_questions") as mock_generate:
        mock_generate.return_value = mock_success_result

        results = await generation_service.batch_generate_questions(requests)

    assert len(results) == 2
    assert results[0].success is True  # First request succeeds
    assert results[1].success is False  # Second request fails due to invalid UUID
    assert "Batch request failed" in results[1].error_message


@pytest.mark.asyncio
async def test_batch_generate_questions_empty_list(generation_service):
    """Test batch generation with empty request list."""
    results = await generation_service.batch_generate_questions([])

    assert results == []


def test_get_generation_capabilities(generation_service):
    """Test getting generation capabilities."""
    from src.question.providers import LLMProvider
    from src.question.types import QuestionType

    # Mock registries
    mock_providers = [LLMProvider.OPENAI]
    generation_service.provider_registry.get_available_providers.return_value = (
        mock_providers
    )
    generation_service.provider_registry.is_registered.return_value = True

    mock_question_types = [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]
    generation_service.workflow_registry.get_available_question_types.return_value = (
        mock_question_types
    )
    generation_service.workflow_registry.is_supported.return_value = True

    mock_templates = [
        MagicMock(
            name="mcq_template",
            question_type=QuestionType.MULTIPLE_CHOICE,
            version="1.0",
            description="MCQ template",
        )
    ]
    generation_service.template_manager.list_templates.return_value = mock_templates

    generation_service.config_service.get_configuration_summary.return_value = {
        "version": "1.0"
    }

    capabilities = generation_service.get_generation_capabilities()

    assert "providers" in capabilities
    assert "question_types" in capabilities
    assert "templates" in capabilities
    assert "configuration" in capabilities

    assert len(capabilities["providers"]) == 1
    assert capabilities["providers"][0]["name"] == "openai"
    assert capabilities["providers"][0]["available"] is True


@pytest.mark.asyncio
async def test_validate_generation_setup_all_valid(generation_service):
    """Test generation setup validation when everything is valid."""
    from src.question.types import QuestionType

    question_type = QuestionType.MULTIPLE_CHOICE

    # Mock all validation checks to pass
    generation_service.workflow_registry.is_supported.return_value = True
    generation_service.config_service.get_config.return_value = MagicMock()
    generation_service.config_service.get_provider_config.return_value = MagicMock()
    generation_service.provider_registry.is_registered.return_value = True
    generation_service.provider_registry.health_check = AsyncMock(return_value=True)
    generation_service.template_manager.get_template.return_value = MagicMock()

    result = await generation_service.validate_generation_setup(question_type)

    assert result["overall_status"] == "ready"
    assert result["question_type_supported"] is True
    assert result["provider_available"] is True
    assert result["workflow_available"] is True
    assert result["template_available"] is True
    assert result["provider_health"] is True
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_validate_generation_setup_question_type_not_supported(
    generation_service,
):
    """Test validation when question type is not supported."""
    from src.question.types import QuestionType

    question_type = QuestionType.MULTIPLE_CHOICE

    # Question type not supported
    generation_service.workflow_registry.is_supported.return_value = False

    result = await generation_service.validate_generation_setup(question_type)

    assert result["overall_status"] == "error"
    assert result["question_type_supported"] is False
    assert any("not supported" in error for error in result["errors"])


@pytest.mark.asyncio
async def test_validate_generation_setup_provider_health_failed(generation_service):
    """Test validation when provider health check fails."""
    from src.question.types import QuestionType

    question_type = QuestionType.MULTIPLE_CHOICE

    # Mock setup where provider is available but health check fails
    generation_service.workflow_registry.is_supported.return_value = True
    generation_service.config_service.get_config.return_value = MagicMock()
    generation_service.config_service.get_provider_config.return_value = MagicMock()
    generation_service.provider_registry.is_registered.return_value = True
    generation_service.provider_registry.health_check = AsyncMock(return_value=False)
    generation_service.template_manager.get_template.return_value = MagicMock()

    result = await generation_service.validate_generation_setup(question_type)

    assert result["overall_status"] == "error"
    assert result["provider_available"] is True
    assert result["provider_health"] is False
    assert any("health check failed" in error for error in result["errors"])


@pytest.mark.asyncio
async def test_validate_generation_setup_template_not_available(generation_service):
    """Test validation when template is not available."""
    from src.question.types import QuestionType

    question_type = QuestionType.MULTIPLE_CHOICE

    # Mock setup where template is not available
    generation_service.workflow_registry.is_supported.return_value = True
    generation_service.config_service.get_config.return_value = MagicMock()
    generation_service.config_service.get_provider_config.return_value = MagicMock()
    generation_service.provider_registry.is_registered.return_value = True
    generation_service.provider_registry.health_check = AsyncMock(return_value=True)
    generation_service.template_manager.get_template.side_effect = ValueError(
        "Template not found"
    )

    result = await generation_service.validate_generation_setup(question_type)

    assert result["overall_status"] == "error"
    assert result["template_available"] is False
    assert any("No template available" in error for error in result["errors"])


@pytest.mark.asyncio
async def test_validate_generation_setup_exception_handling(generation_service):
    """Test validation exception handling."""
    from src.question.types import QuestionType

    question_type = QuestionType.MULTIPLE_CHOICE

    # Mock an exception during validation
    generation_service.workflow_registry.is_supported.side_effect = Exception(
        "Registry error"
    )

    result = await generation_service.validate_generation_setup(question_type)

    assert result["overall_status"] == "error"
    assert any(
        "Validation failed: Registry error" in error for error in result["errors"]
    )


def test_validate_generation_request_valid(generation_service, generation_parameters):
    """Test validation of valid generation request."""
    from src.question.types import QuestionType

    question_type = QuestionType.MULTIPLE_CHOICE

    # Mock workflow registry to support the question type
    generation_service.workflow_registry.is_supported.return_value = True

    # Mock config service
    mock_config = MagicMock()
    mock_config.max_concurrent_generations = 10
    generation_service.config_service.get_config.return_value = mock_config

    # Should not raise any exception
    generation_service._validate_generation_request(
        question_type, generation_parameters
    )


def test_validate_generation_request_unsupported_question_type(
    generation_service, generation_parameters
):
    """Test validation with unsupported question type."""
    from src.question.types import QuestionType

    question_type = QuestionType.MULTIPLE_CHOICE

    # Mock workflow registry to not support the question type
    generation_service.workflow_registry.is_supported.return_value = False

    with pytest.raises(ValueError) as exc_info:
        generation_service._validate_generation_request(
            question_type, generation_parameters
        )

    assert "not supported" in str(exc_info.value)


def test_validate_generation_request_invalid_target_count(generation_service):
    """Test validation with invalid target count."""
    from pydantic import ValidationError

    from src.question.types import (
        GenerationParameters,
        QuestionDifficulty,
        QuestionType,
    )

    question_type = QuestionType.MULTIPLE_CHOICE
    generation_service.workflow_registry.is_supported.return_value = True

    # Test zero target count - should fail at Pydantic level
    with pytest.raises(ValidationError) as exc_info:
        GenerationParameters(target_count=0, difficulty=QuestionDifficulty.MEDIUM)

    assert "greater_than_equal" in str(exc_info.value)


def test_validate_generation_request_excessive_target_count(generation_service):
    """Test validation with excessive target count."""
    from pydantic import ValidationError

    from src.question.types import (
        GenerationParameters,
        QuestionDifficulty,
        QuestionType,
    )

    question_type = QuestionType.MULTIPLE_CHOICE
    generation_service.workflow_registry.is_supported.return_value = True

    # Test excessive target count - should fail at Pydantic level
    with pytest.raises(ValidationError) as exc_info:
        GenerationParameters(
            target_count=150,  # > 100
            difficulty=QuestionDifficulty.MEDIUM,
        )

    assert "less_than_equal" in str(exc_info.value)


def test_validate_generation_request_system_limits(generation_service):
    """Test validation against system limits."""
    from src.question.types import (
        GenerationParameters,
        QuestionDifficulty,
        QuestionType,
    )

    question_type = QuestionType.MULTIPLE_CHOICE
    generation_service.workflow_registry.is_supported.return_value = True

    # Mock config with low limits
    mock_config = MagicMock()
    mock_config.max_concurrent_generations = 1  # Very low limit
    generation_service.config_service.get_config.return_value = mock_config

    excessive_params = GenerationParameters(
        target_count=50,  # > 1 * 10
        difficulty=QuestionDifficulty.MEDIUM,
    )

    with pytest.raises(ValueError) as exc_info:
        generation_service._validate_generation_request(question_type, excessive_params)

    assert "exceeds system limits" in str(exc_info.value)


@pytest.mark.parametrize(
    "provider_name,workflow_name,template_name",
    [
        (None, None, None),  # All defaults
        ("openai", None, None),  # Specific provider
        (None, "mcq_workflow", None),  # Specific workflow
        (None, None, "mcq_template"),  # Specific template
        ("openai", "mcq_workflow", "mcq_template"),  # All specified
    ],
)
@pytest.mark.asyncio
async def test_generate_questions_with_optional_parameters(
    generation_service,
    generation_parameters,
    mock_content_chunks,
    provider_name,
    workflow_name,
    template_name,
):
    """Test question generation with various optional parameters."""
    from src.question.types import QuestionType

    quiz_id = uuid.uuid4()
    question_type = QuestionType.MULTIPLE_CHOICE

    with (
        patch.object(generation_service, "_validate_generation_request"),
        patch.object(
            generation_service.config_service, "get_config"
        ) as mock_get_config,
        patch.object(generation_service.config_service, "get_provider_config"),
        patch.object(generation_service.config_service, "get_workflow_config"),
        patch(
            "src.question.services.generation_service.ContentProcessingService"
        ) as mock_content_service_class,
    ):
        mock_config = MagicMock()
        mock_config.enable_duplicate_detection = False
        mock_get_config.return_value = mock_config

        # Mock content service
        mock_content_service = MagicMock()
        mock_content_service.prepare_content_for_generation = AsyncMock(
            return_value=mock_content_chunks
        )
        mock_content_service.get_content_statistics.return_value = {
            "total_characters": 500
        }
        mock_content_service_class.return_value = mock_content_service

        # Mock provider and workflow
        generation_service.provider_registry.get_available_providers.return_value = [
            MagicMock()
        ]
        generation_service.provider_registry.get_provider.return_value = MagicMock()

        mock_workflow = MagicMock()
        mock_workflow.workflow_name = workflow_name or "default_workflow"
        mock_workflow.execute = AsyncMock(
            return_value=MagicMock(success=True, metadata={})
        )
        generation_service.workflow_registry.get_workflow.return_value = mock_workflow

        result = await generation_service.generate_questions(
            quiz_id=quiz_id,
            question_type=question_type,
            generation_parameters=generation_parameters,
            provider_name=provider_name,
            workflow_name=workflow_name,
            template_name=template_name,
        )

    # Should complete successfully regardless of optional parameters
    assert hasattr(result, "success")
    assert hasattr(result, "metadata")
