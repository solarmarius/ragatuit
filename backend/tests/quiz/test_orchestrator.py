"""Comprehensive tests for module-based quiz orchestrator functionality."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def sample_quiz_id():
    """Create a sample quiz ID for testing."""
    return uuid.uuid4()


@pytest.fixture
def mock_quiz():
    """Create a mock quiz object."""
    quiz = MagicMock()
    quiz.id = uuid.uuid4()
    quiz.selected_modules = {
        "module_1": {"question_count": 5, "name": "Introduction"},
        "module_2": {"question_count": 3, "name": "Advanced Topics"},
    }
    quiz.language = "en"
    return quiz


@pytest.fixture
def sample_extracted_content():
    """Create sample extracted content for testing."""
    return {
        "module_1": "This is comprehensive content for module 1. " * 20,
        "module_2": "This is detailed content for module 2. " * 15,
    }


@pytest.fixture
def sample_generation_results():
    """Create sample generation results."""
    return {
        "module_1": [
            {"question_text": "Question 1", "correct_answer": "A"},
            {"question_text": "Question 2", "correct_answer": "B"},
            {"question_text": "Question 3", "correct_answer": "C"},
            {"question_text": "Question 4", "correct_answer": "D"},
            {"question_text": "Question 5", "correct_answer": "A"},
        ],
        "module_2": [
            {"question_text": "Question 6", "correct_answer": "B"},
            {"question_text": "Question 7", "correct_answer": "C"},
            {"question_text": "Question 8", "correct_answer": "D"},
        ],
    }


@pytest.mark.asyncio
async def test_execute_generation_workflow_success(
    sample_quiz_id, mock_quiz, sample_extracted_content, sample_generation_results
):
    """Test successful generation workflow execution."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import _execute_generation_workflow

    # Mock the services
    with patch("src.question.services.QuestionGenerationService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_questions_for_quiz.return_value = (
            sample_generation_results
        )

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_content:
            mock_content.return_value = sample_extracted_content

            with patch("src.database.get_async_session") as mock_session_ctx:
                mock_session = AsyncMock()
                mock_session_ctx.return_value.__aenter__.return_value = mock_session
                mock_session.get.return_value = mock_quiz

                # Execute the workflow
                status, error_message, exception = await _execute_generation_workflow(
                    quiz_id=sample_quiz_id,
                    target_question_count=8,
                    _llm_model="gpt-4",
                    _llm_temperature=0.7,
                    language=QuizLanguage.ENGLISH,
                    question_type=QuestionType.MULTIPLE_CHOICE,
                )

                # Verify success
                assert status == "completed"
                assert error_message is None
                assert exception is None

                # Verify service calls
                mock_content.assert_called_once_with(sample_quiz_id)
                mock_service.generate_questions_for_quiz.assert_called_once_with(
                    quiz_id=sample_quiz_id,
                    extracted_content=sample_extracted_content,
                    provider_name="openai",
                )


@pytest.mark.asyncio
async def test_execute_generation_workflow_no_content(sample_quiz_id, mock_quiz):
    """Test generation workflow when no content is found."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import _execute_generation_workflow

    with patch("src.question.services.prepare_and_validate_content") as mock_content:
        mock_content.return_value = {}  # No content

        with patch("src.database.get_async_session") as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_quiz

            # Execute the workflow
            status, error_message, exception = await _execute_generation_workflow(
                quiz_id=sample_quiz_id,
                target_question_count=5,
                _llm_model="gpt-4",
                _llm_temperature=0.7,
                language=QuizLanguage.ENGLISH,
                question_type=QuestionType.MULTIPLE_CHOICE,
            )

            # Verify failure due to no content
            assert status == "failed"
            assert "No valid content found" in error_message
            assert exception is None


@pytest.mark.asyncio
async def test_execute_generation_workflow_partial_failure(
    sample_quiz_id, mock_quiz, sample_extracted_content
):
    """Test generation workflow with partial failure (insufficient questions generated)."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import _execute_generation_workflow

    # Mock partial results (only 2 questions when 8 expected)
    partial_results = {
        "module_1": [
            {"question_text": "Question 1", "correct_answer": "A"},
        ],
        "module_2": [
            {"question_text": "Question 2", "correct_answer": "B"},
        ],
    }

    with patch("src.question.services.QuestionGenerationService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_questions_for_quiz.return_value = partial_results

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_content:
            mock_content.return_value = sample_extracted_content

            with patch("src.database.get_async_session") as mock_session_ctx:
                mock_session = AsyncMock()
                mock_session_ctx.return_value.__aenter__.return_value = mock_session
                mock_session.get.return_value = mock_quiz

                # Execute the workflow
                status, error_message, exception = await _execute_generation_workflow(
                    quiz_id=sample_quiz_id,
                    target_question_count=8,
                    _llm_model="gpt-4",
                    _llm_temperature=0.7,
                    language=QuizLanguage.ENGLISH,
                    question_type=QuestionType.MULTIPLE_CHOICE,
                )

                # Verify partial failure
                assert status == "failed"
                assert "Only generated 2/8 questions" in error_message
                assert exception is None


@pytest.mark.asyncio
async def test_execute_generation_workflow_complete_failure(
    sample_quiz_id, mock_quiz, sample_extracted_content
):
    """Test generation workflow when no questions are generated."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import _execute_generation_workflow

    # Mock complete failure (no questions generated)
    failure_results = {"module_1": [], "module_2": []}

    with patch("src.question.services.QuestionGenerationService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_questions_for_quiz.return_value = failure_results

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_content:
            mock_content.return_value = sample_extracted_content

            with patch("src.database.get_async_session") as mock_session_ctx:
                mock_session = AsyncMock()
                mock_session_ctx.return_value.__aenter__.return_value = mock_session
                mock_session.get.return_value = mock_quiz

                # Execute the workflow
                status, error_message, exception = await _execute_generation_workflow(
                    quiz_id=sample_quiz_id,
                    target_question_count=8,
                    _llm_model="gpt-4",
                    _llm_temperature=0.7,
                    language=QuizLanguage.ENGLISH,
                    question_type=QuestionType.MULTIPLE_CHOICE,
                )

                # Verify complete failure
                assert status == "failed"
                assert "No questions were generated from any module" in error_message
                assert exception is None


@pytest.mark.asyncio
async def test_execute_generation_workflow_exception_handling(
    sample_quiz_id, mock_quiz
):
    """Test generation workflow exception handling."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import _execute_generation_workflow

    with patch("src.question.services.prepare_and_validate_content") as mock_content:
        mock_content.side_effect = Exception("Content service error")

        with patch("src.database.get_async_session") as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_quiz

            # Execute the workflow
            status, error_message, exception = await _execute_generation_workflow(
                quiz_id=sample_quiz_id,
                target_question_count=5,
                _llm_model="gpt-4",
                _llm_temperature=0.7,
                language=QuizLanguage.ENGLISH,
                question_type=QuestionType.MULTIPLE_CHOICE,
            )

            # Verify exception handling
            assert status == "failed"
            assert "Content service error" in error_message
            assert isinstance(exception, Exception)


@pytest.mark.asyncio
async def test_orchestrate_quiz_question_generation_success(
    sample_quiz_id, sample_generation_results
):
    """Test complete orchestration workflow success."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import orchestrate_quiz_question_generation

    with patch("src.database.execute_in_transaction") as mock_transaction:
        # Mock successful job reservation
        mock_transaction.side_effect = [True, None]  # Reserve job, save result

        with patch(
            "src.quiz.orchestrator._execute_generation_workflow"
        ) as mock_workflow:
            mock_workflow.return_value = ("completed", None, None)

            # Execute orchestration
            await orchestrate_quiz_question_generation(
                quiz_id=sample_quiz_id,
                target_question_count=8,
                llm_model="gpt-4",
                llm_temperature=0.7,
                language=QuizLanguage.ENGLISH,
                question_type=QuestionType.MULTIPLE_CHOICE,
            )

            # Verify workflow execution
            mock_workflow.assert_called_once()
            assert mock_transaction.call_count == 2  # Reserve + save


@pytest.mark.asyncio
async def test_orchestrate_quiz_question_generation_job_already_running(sample_quiz_id):
    """Test orchestration when job is already running."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import orchestrate_quiz_question_generation

    with patch("src.database.execute_in_transaction") as mock_transaction:
        # Mock job already running (reservation fails)
        mock_transaction.return_value = False

        with patch(
            "src.quiz.orchestrator._execute_generation_workflow"
        ) as mock_workflow:
            # Execute orchestration
            await orchestrate_quiz_question_generation(
                quiz_id=sample_quiz_id,
                target_question_count=8,
                llm_model="gpt-4",
                llm_temperature=0.7,
                language=QuizLanguage.ENGLISH,
                question_type=QuestionType.MULTIPLE_CHOICE,
            )

            # Verify workflow was not executed
            mock_workflow.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrate_quiz_question_generation_with_injected_service(
    sample_quiz_id, sample_generation_results
):
    """Test orchestration with injected generation service."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import orchestrate_quiz_question_generation

    mock_generation_service = AsyncMock()

    with patch("src.database.execute_in_transaction") as mock_transaction:
        mock_transaction.side_effect = [True, None]

        with patch(
            "src.quiz.orchestrator._execute_generation_workflow"
        ) as mock_workflow:
            mock_workflow.return_value = ("completed", None, None)

            # Execute orchestration with injected service
            await orchestrate_quiz_question_generation(
                quiz_id=sample_quiz_id,
                target_question_count=8,
                llm_model="gpt-4",
                llm_temperature=0.7,
                language=QuizLanguage.ENGLISH,
                question_type=QuestionType.MULTIPLE_CHOICE,
                generation_service=mock_generation_service,
            )

            # Verify injected service was passed to workflow
            mock_workflow.assert_called_once()
            call_args = mock_workflow.call_args[1]
            assert call_args["generation_service"] == mock_generation_service


@pytest.mark.asyncio
async def test_generation_workflow_module_level_logging(
    sample_quiz_id, mock_quiz, sample_extracted_content, sample_generation_results
):
    """Test that module-level results are properly logged."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import _execute_generation_workflow

    with patch("src.question.services.QuestionGenerationService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_questions_for_quiz.return_value = (
            sample_generation_results
        )

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_content:
            mock_content.return_value = sample_extracted_content

            with patch("src.database.get_async_session") as mock_session_ctx:
                mock_session = AsyncMock()
                mock_session_ctx.return_value.__aenter__.return_value = mock_session
                mock_session.get.return_value = mock_quiz

                with patch("src.config.get_logger") as mock_logger:
                    logger_instance = MagicMock()
                    mock_logger.return_value = logger_instance

                    # Execute the workflow
                    await _execute_generation_workflow(
                        quiz_id=sample_quiz_id,
                        target_question_count=8,
                        _llm_model="gpt-4",
                        _llm_temperature=0.7,
                        language=QuizLanguage.ENGLISH,
                        question_type=QuestionType.MULTIPLE_CHOICE,
                    )

                    # Verify module-level logging occurred
                    assert (
                        logger_instance.info.call_count >= 3
                    )  # Start, modules, completion

                    # Check that module-specific logs were called
                    module_log_calls = [
                        call
                        for call in logger_instance.info.call_args_list
                        if len(call[0]) > 0
                        and "module_generation_succeeded" in call[0][0]
                    ]
                    assert len(module_log_calls) == 2  # Two successful modules


@pytest.mark.asyncio
async def test_generation_workflow_with_missing_quiz(sample_quiz_id):
    """Test generation workflow when quiz is not found."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import _execute_generation_workflow

    with patch("src.database.get_async_session") as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_session
        mock_session.get.return_value = None  # Quiz not found

        # Execute the workflow
        status, error_message, exception = await _execute_generation_workflow(
            quiz_id=sample_quiz_id,
            target_question_count=5,
            _llm_model="gpt-4",
            _llm_temperature=0.7,
            language=QuizLanguage.ENGLISH,
            question_type=QuestionType.MULTIPLE_CHOICE,
        )

        # Verify failure due to missing quiz
        assert status == "failed"
        assert f"Quiz {sample_quiz_id} not found" in error_message
        assert isinstance(exception, ValueError)


@pytest.mark.asyncio
async def test_generation_workflow_tolerates_80_percent_success(
    sample_quiz_id, mock_quiz, sample_extracted_content
):
    """Test that 80% success rate is considered acceptable."""
    from src.question.types import QuestionType, QuizLanguage
    from src.quiz.orchestrator import _execute_generation_workflow

    # Mock 80% success (6.4 out of 8, rounded to 6 questions)
    good_results = {
        "module_1": [
            {"question_text": f"Question {i}", "correct_answer": "A"} for i in range(4)
        ],
        "module_2": [
            {"question_text": f"Question {i}", "correct_answer": "B"} for i in range(2)
        ],
    }

    with patch("src.question.services.QuestionGenerationService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_questions_for_quiz.return_value = good_results

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_content:
            mock_content.return_value = sample_extracted_content

            with patch("src.database.get_async_session") as mock_session_ctx:
                mock_session = AsyncMock()
                mock_session_ctx.return_value.__aenter__.return_value = mock_session
                mock_session.get.return_value = mock_quiz

                # Execute the workflow (expecting 8, getting 6 = 75%, should still succeed)
                status, error_message, exception = await _execute_generation_workflow(
                    quiz_id=sample_quiz_id,
                    target_question_count=8,
                    _llm_model="gpt-4",
                    _llm_temperature=0.7,
                    language=QuizLanguage.ENGLISH,
                    question_type=QuestionType.MULTIPLE_CHOICE,
                )

                # Should still fail since 75% < 80%
                assert status == "failed"
                assert "6/8 questions" in error_message
