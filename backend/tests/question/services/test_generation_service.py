"""Tests for module-based question generation service."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


@pytest.fixture
def generation_service():
    """Create question generation service instance."""
    from unittest.mock import patch

    from src.question.services.generation_service import QuestionGenerationService

    with (
        patch(
            "src.question.services.generation_service.get_llm_provider_registry"
        ) as mock_provider_registry,
        patch(
            "src.question.services.generation_service.get_template_manager"
        ) as mock_template_manager,
    ):
        service = QuestionGenerationService()
        service.provider_registry = mock_provider_registry.return_value
        service.template_manager = mock_template_manager.return_value
        yield service


@pytest.fixture
def mock_quiz():
    """Create mock quiz with module structure."""
    from src.quiz.models import Quiz
    from src.quiz.schemas import QuizStatus, QuizTone

    quiz = MagicMock(spec=Quiz)
    quiz.id = UUID("12345678-1234-5678-1234-567812345678")
    quiz.status = QuizStatus.GENERATING_QUESTIONS
    quiz.language = "en"
    quiz.tone = QuizTone.ACADEMIC  # Default tone
    quiz.selected_modules = {
        "module_1": {
            "name": "Introduction",
            "question_batches": [{"question_type": "multiple_choice", "count": 5}],
        },
        "module_2": {
            "name": "Advanced Topics",
            "question_batches": [{"question_type": "multiple_choice", "count": 10}],
        },
    }
    quiz.question_count = 15
    quiz.generation_metadata = None  # No existing metadata by default
    return quiz


@pytest.fixture
def mock_quiz_with_tone():
    """Create mock quiz with specific tone."""
    from src.quiz.models import Quiz
    from src.quiz.schemas import QuizStatus, QuizTone

    quiz = MagicMock(spec=Quiz)
    quiz.id = UUID("87654321-4321-8765-4321-876543218765")
    quiz.status = QuizStatus.GENERATING_QUESTIONS
    quiz.language = "en"
    quiz.tone = QuizTone.PROFESSIONAL  # Professional tone
    quiz.selected_modules = {
        "module_1": {
            "name": "Business Strategy",
            "question_batches": [{"question_type": "multiple_choice", "count": 8}],
        },
        "module_2": {
            "name": "Leadership",
            "question_batches": [{"question_type": "multiple_choice", "count": 12}],
        },
    }
    quiz.question_count = 20
    quiz.generation_metadata = None
    return quiz


@pytest.fixture
def extracted_content():
    """Create mock extracted content."""
    return {
        "module_1": "This is content from module 1 about introduction topics.",
        "module_2": "This is content from module 2 about advanced topics.",
    }


@pytest.fixture
def mock_questions():
    """Create mock generated questions."""
    from src.question.types import Question, QuestionType

    return [
        Question(
            quiz_id=UUID("12345678-1234-5678-1234-567812345678"),
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={
                "question_text": "What is the main topic?",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "correct_answer": "A",
            },
            is_approved=False,
        ),
        Question(
            quiz_id=UUID("12345678-1234-5678-1234-567812345678"),
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_data={
                "question_text": "What is advanced concept?",
                "option_a": "Advanced A",
                "option_b": "Advanced B",
                "option_c": "Advanced C",
                "option_d": "Advanced D",
                "correct_answer": "B",
            },
            is_approved=False,
        ),
    ]


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_success(
    generation_service, mock_quiz, extracted_content, mock_questions
):
    """Test successful module-based question generation with batch tracking."""
    quiz_id = mock_quiz.id

    with (
        patch(
            "src.question.services.generation_service.get_async_session"
        ) as mock_session_ctx,
        patch(
            "src.question.services.generation_service.ParallelModuleProcessor"
        ) as mock_processor_class,
    ):
        # Mock session and quiz retrieval
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        # Mock provider registry
        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider

        # Mock parallel processor
        mock_processor = MagicMock()
        mock_processor.process_all_modules_with_batches = AsyncMock(
            return_value=(
                {
                    "module_1": [mock_questions[0]],
                    "module_2": [mock_questions[1]],
                },
                {
                    "successful_batches": [
                        "module_1_multiple_choice_5",
                        "module_2_multiple_choice_10",
                    ],
                    "failed_batches": [],
                },
            )
        )
        mock_processor_class.return_value = mock_processor

        (
            result,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id, extracted_content
        )

    assert len(result) == 2
    assert "module_1" in result
    assert "module_2" in result
    assert len(result["module_1"]) == 1
    assert len(result["module_2"]) == 1

    # Check batch status
    assert batch_status["successful_batches"] == [
        "module_1_multiple_choice_5",
        "module_2_multiple_choice_10",
    ]
    assert batch_status["failed_batches"] == []

    # Verify provider was called correctly
    from src.question.providers import LLMProvider

    generation_service.provider_registry.get_provider.assert_called_once_with(
        LLMProvider.OPENAI
    )

    # Verify processor was called correctly
    mock_processor.process_all_modules_with_batches.assert_called_once()
    call_args = mock_processor.process_all_modules_with_batches.call_args
    assert call_args[0][0] == quiz_id  # quiz_id
    assert "module_1" in call_args[0][1]  # modules_data
    assert "module_2" in call_args[0][1]


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_quiz_not_found(
    generation_service,
):
    """Test generation when quiz is not found."""
    quiz_id = UUID("00000000-0000-0000-0000-000000000000")
    extracted_content = {"module_1": "content"}

    with patch(
        "src.question.services.generation_service.get_async_session"
    ) as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session.get.return_value = None  # Quiz not found
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        with pytest.raises(ValueError, match="Quiz .* not found"):
            await generation_service.generate_questions_for_quiz_with_batch_tracking(
                quiz_id, extracted_content
            )


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_no_content(
    generation_service, mock_quiz
):
    """Test generation when no module content is available."""
    quiz_id = mock_quiz.id
    extracted_content = {}  # No content

    with patch(
        "src.question.services.generation_service.get_async_session"
    ) as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        # With batch tracking, empty content should return empty results rather than raise
        (
            result,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id, extracted_content
        )
        assert result == {}
        assert batch_status == {"successful_batches": [], "failed_batches": []}


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_missing_module_content(
    generation_service, mock_quiz, extracted_content
):
    """Test generation when some module content is missing."""
    quiz_id = mock_quiz.id
    # Only provide content for one module
    partial_content = {"module_1": extracted_content["module_1"]}

    with (
        patch(
            "src.question.services.generation_service.get_async_session"
        ) as mock_session_ctx,
        patch(
            "src.question.services.generation_service.ParallelModuleProcessor"
        ) as mock_processor_class,
    ):
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider

        mock_processor = MagicMock()
        mock_processor.process_all_modules_with_batches = AsyncMock(
            return_value=(
                {"module_1": []},
                {
                    "successful_batches": [],
                    "failed_batches": ["module_1_multiple_choice_5"],
                },
            )
        )
        mock_processor_class.return_value = mock_processor

        (
            result,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id, partial_content
        )

        # Should only process the one module with content
        call_args = mock_processor.process_all_modules_with_batches.call_args[0][1]
        assert len(call_args) == 1
        assert "module_1" in call_args
        assert "module_2" not in call_args


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_with_tone(
    generation_service, mock_quiz_with_tone, extracted_content
):
    """Test generation with specific tone."""
    quiz_id = mock_quiz_with_tone.id

    with (
        patch(
            "src.question.services.generation_service.get_async_session"
        ) as mock_session_ctx,
        patch(
            "src.question.services.generation_service.ParallelModuleProcessor"
        ) as mock_processor_class,
    ):
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz_with_tone
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider

        mock_processor = MagicMock()
        mock_processor.process_all_modules_with_batches = AsyncMock(
            return_value=({}, {"successful_batches": [], "failed_batches": []})
        )
        mock_processor_class.return_value = mock_processor

        (
            result,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id, extracted_content
        )

        # Verify processor was created with professional tone
        from src.question.types import QuizLanguage
        from src.quiz.schemas import QuizTone

        mock_processor_class.assert_called_once_with(
            llm_provider=mock_provider,
            template_manager=generation_service.template_manager,
            language=QuizLanguage.ENGLISH,
            tone=QuizTone.PROFESSIONAL.value,
        )


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_tone_extraction(
    generation_service, mock_quiz, extracted_content
):
    """Test that tone is extracted from quiz model correctly."""
    from src.quiz.schemas import QuizTone

    # Set encouraging tone on the quiz
    mock_quiz.tone = QuizTone.ENCOURAGING
    quiz_id = mock_quiz.id

    with (
        patch(
            "src.question.services.generation_service.get_async_session"
        ) as mock_session_ctx,
        patch(
            "src.question.services.generation_service.ParallelModuleProcessor"
        ) as mock_processor_class,
    ):
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider

        mock_processor = MagicMock()
        mock_processor.process_all_modules_with_batches = AsyncMock(
            return_value=({}, {"successful_batches": [], "failed_batches": []})
        )
        mock_processor_class.return_value = mock_processor

        (
            result,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id, extracted_content
        )

        # Verify processor was created with encouraging tone
        from src.question.types import QuizLanguage

        mock_processor_class.assert_called_once_with(
            llm_provider=mock_provider,
            template_manager=generation_service.template_manager,
            language=QuizLanguage.ENGLISH,
            tone=QuizTone.ENCOURAGING.value,
        )


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_tone_and_language(
    generation_service, mock_quiz, extracted_content
):
    """Test generation with both tone and language."""
    from src.question.types import QuizLanguage
    from src.quiz.schemas import QuizTone

    # Set Norwegian language and casual tone
    mock_quiz.language = "no"
    mock_quiz.tone = QuizTone.CASUAL
    quiz_id = mock_quiz.id

    with (
        patch(
            "src.question.services.generation_service.get_async_session"
        ) as mock_session_ctx,
        patch(
            "src.question.services.generation_service.ParallelModuleProcessor"
        ) as mock_processor_class,
    ):
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider

        mock_processor = MagicMock()
        mock_processor.process_all_modules_with_batches = AsyncMock(
            return_value=({}, {"successful_batches": [], "failed_batches": []})
        )
        mock_processor_class.return_value = mock_processor

        (
            result,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id, extracted_content
        )

        # Verify processor was created with both Norwegian language and casual tone
        mock_processor_class.assert_called_once_with(
            llm_provider=mock_provider,
            template_manager=generation_service.template_manager,
            language=QuizLanguage.NORWEGIAN,
            tone=QuizTone.CASUAL.value,
        )


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_norwegian_language(
    generation_service, mock_quiz, extracted_content
):
    """Test generation with Norwegian language."""
    mock_quiz.language = "no"  # Norwegian
    quiz_id = mock_quiz.id

    with (
        patch(
            "src.question.services.generation_service.get_async_session"
        ) as mock_session_ctx,
        patch(
            "src.question.services.generation_service.ParallelModuleProcessor"
        ) as mock_processor_class,
    ):
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider

        mock_processor = MagicMock()
        mock_processor.process_all_modules_with_batches = AsyncMock(
            return_value=({}, {"successful_batches": [], "failed_batches": []})
        )
        mock_processor_class.return_value = mock_processor

        (
            result,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id, extracted_content
        )

        # Verify processor was created with Norwegian language
        from src.question.types import QuizLanguage
        from src.quiz.schemas import QuizTone

        mock_processor_class.assert_called_once_with(
            llm_provider=mock_provider,
            template_manager=generation_service.template_manager,
            language=QuizLanguage.NORWEGIAN,
            tone=QuizTone.ACADEMIC.value,  # Default tone
        )


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_preserves_question_count(
    generation_service, mock_quiz, extracted_content, mock_questions
):
    """Test that quiz question count is preserved after generation."""
    quiz_id = mock_quiz.id

    with (
        patch(
            "src.question.services.generation_service.get_async_session"
        ) as mock_session_ctx,
        patch(
            "src.question.services.generation_service.ParallelModuleProcessor"
        ) as mock_processor_class,
    ):
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider

        mock_processor = MagicMock()
        mock_processor.process_all_modules_with_batches = AsyncMock(
            return_value=(
                {
                    "module_1": [mock_questions[0]],
                    "module_2": [mock_questions[1]],
                },
                {
                    "successful_batches": [
                        "module_1_multiple_choice_5",
                        "module_2_multiple_choice_10",
                    ],
                    "failed_batches": [],
                },
            )
        )
        mock_processor_class.return_value = mock_processor

        (
            result,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id, extracted_content
        )

        # Verify quiz total question count preserves original target (should NOT be updated)
        assert mock_quiz.question_count == 15  # Original value preserved
        mock_session.commit.assert_not_called()  # No database update needed


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_provider_exception(
    generation_service, mock_quiz, extracted_content
):
    """Test handling of provider exceptions."""
    quiz_id = mock_quiz.id

    with (
        patch(
            "src.question.services.generation_service.get_async_session"
        ) as mock_session_ctx,
    ):
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        # Make provider registry raise an exception
        generation_service.provider_registry.get_provider.side_effect = Exception(
            "Provider error"
        )

        with pytest.raises(Exception, match="Provider error"):
            await generation_service.generate_questions_for_quiz_with_batch_tracking(
                quiz_id, extracted_content
            )


@pytest.mark.asyncio
async def test_generate_questions_for_quiz_with_batch_tracking_custom_provider(
    generation_service, mock_quiz, extracted_content
):
    """Test generation with custom provider."""
    quiz_id = mock_quiz.id

    with (
        patch(
            "src.question.services.generation_service.get_async_session"
        ) as mock_session_ctx,
        patch(
            "src.question.services.generation_service.ParallelModuleProcessor"
        ) as mock_processor_class,
    ):
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_quiz
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider

        mock_processor = MagicMock()
        mock_processor.process_all_modules_with_batches = AsyncMock(
            return_value=({}, {"successful_batches": [], "failed_batches": []})
        )
        mock_processor_class.return_value = mock_processor

        (
            result,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id, extracted_content, provider_name="anthropic"
        )

        # Verify correct provider was requested
        from src.question.providers import LLMProvider

        generation_service.provider_registry.get_provider.assert_called_once_with(
            LLMProvider.ANTHROPIC
        )


def test_generation_service_initialization(generation_service):
    """Test generation service initialization."""
    assert generation_service.provider_registry is not None
    assert generation_service.template_manager is not None


@pytest.mark.asyncio
async def test_generate_uses_quiz_question_type(generation_service, mock_quiz):
    """Test that generation uses the quiz's question type."""
    extracted_content = {
        "module_1": "Content for module 1",
        "module_2": "Content for module 2",
    }

    with patch(
        "src.question.services.generation_service.get_async_session"
    ) as mock_session_ctx:
        # Mock session context
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_quiz)
        mock_session.commit = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        # Mock provider
        mock_provider = MagicMock()
        generation_service.provider_registry.get_provider.return_value = mock_provider

        # Mock the ParallelModuleProcessor
        with patch(
            "src.question.services.generation_service.ParallelModuleProcessor"
        ) as MockProcessor:
            mock_processor_instance = MagicMock()
            mock_processor_instance.process_all_modules_with_batches = AsyncMock(
                return_value=(
                    {"module_1": [], "module_2": []},
                    {"successful_batches": [], "failed_batches": []},
                )
            )
            MockProcessor.return_value = mock_processor_instance

            # Call the method
            (
                result,
                batch_status,
            ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
                quiz_id=mock_quiz.id, extracted_content=extracted_content
            )

            # Verify ParallelModuleProcessor was called with correct parameters
            from src.question.types import QuizLanguage
            from src.quiz.schemas import QuizTone

            MockProcessor.assert_called_once_with(
                llm_provider=mock_provider,
                template_manager=generation_service.template_manager,
                language=QuizLanguage.ENGLISH,
                tone=QuizTone.ACADEMIC.value,  # Default tone from mock quiz
            )


@pytest.mark.asyncio
async def test_workflow_uses_correct_template():
    """Test that workflow selects template based on question type."""
    from src.question.providers.base import BaseLLMProvider
    from src.question.templates.manager import TemplateManager
    from src.question.types import QuestionType, QuizLanguage
    from src.question.workflows.module_batch_workflow import (
        ModuleBatchState,
        ModuleBatchWorkflow,
    )

    # Create proper mock instances
    mock_provider = MagicMock(spec=BaseLLMProvider)
    mock_template_manager = MagicMock(spec=TemplateManager)

    workflow = ModuleBatchWorkflow(
        llm_provider=mock_provider,
        template_manager=mock_template_manager,
        language=QuizLanguage.ENGLISH,
    )

    # Mock template manager to verify calls
    mock_template_manager.create_messages = AsyncMock(
        return_value=[
            MagicMock(content="System prompt"),
            MagicMock(content="User prompt"),
        ]
    )

    # Create test state with question type
    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_module",
        module_name="Test Module",
        module_content="Test content",
        target_question_count=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        llm_provider=mock_provider,
        template_manager=mock_template_manager,
    )

    # Execute prepare_prompt
    await workflow.prepare_prompt(state)

    # Verify template manager was called with correct question type
    mock_template_manager.create_messages.assert_called_once()
    call_args = mock_template_manager.create_messages.call_args
    assert call_args[0][0] == QuestionType.MULTIPLE_CHOICE  # First positional arg
    assert call_args[1]["template_name"] is None  # Should let manager auto-select
    assert call_args[1]["language"] == QuizLanguage.ENGLISH
