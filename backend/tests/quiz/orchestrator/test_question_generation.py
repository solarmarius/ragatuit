"""Tests for question generation orchestration."""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.asyncio
async def test_orchestrate_question_generation_success(caplog):
    """Test successful question generation workflow with complete batch success."""
    from src.question.types import QuizLanguage
    from src.quiz.orchestrator.question_generation import (
        orchestrate_quiz_question_generation,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    target_questions = 10
    llm_model = "gpt-4"
    llm_temperature = 0.7
    language = QuizLanguage.ENGLISH

    # Mock generation service
    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )

    # Mock batch results - all batches successful
    mock_batch_results = {
        "module_1": ["question1", "question2", "question3"],
        "module_2": ["question4", "question5"],
    }
    mock_batch_status = {
        "successful_batches": ["module_1_multiple_choice", "module_2_true_false"],
        "failed_batches": [],
    }
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.return_value = (
        mock_batch_results,
        mock_batch_status,
    )

    # Mock transaction functions
    with patch(
        "src.quiz.orchestrator.question_generation.execute_in_transaction"
    ) as mock_execute_transaction:
        # Mock job reservation success and save result success
        mock_execute_transaction.side_effect = [True, None]

        # Mock content preparation
        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_prepare_content:
            mock_prepare_content.return_value = {
                "module_1": [{"content": "Module 1 content", "word_count": 100}],
                "module_2": [{"content": "Module 2 content", "word_count": 150}],
            }

            # Mock quiz model for batch status checking
            with patch("src.database.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_quiz = Mock()
                mock_quiz.selected_modules = {
                    "module_1": {
                        "question_batches": [
                            {"question_type": "multiple_choice", "count": 3}
                        ]
                    },
                    "module_2": {
                        "question_batches": [
                            {"question_type": "true_false", "count": 2}
                        ]
                    },
                }
                mock_quiz.generation_metadata = {
                    "successful_batches": [],
                    "failed_batches": [],
                }
                mock_session.get = AsyncMock(return_value=mock_quiz)
                mock_session.refresh = AsyncMock()
                mock_get_session.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

                # Act
                await orchestrate_quiz_question_generation(
                    quiz_id,
                    target_questions,
                    llm_model,
                    llm_temperature,
                    language,
                    mock_generation_service,
                )

    # Assert
    assert mock_execute_transaction.call_count == 2  # Job reservation + save result
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.assert_called_once()

    # Verify logging
    assert "quiz_question_generation_orchestration_started" in caplog.text
    assert str(quiz_id) in caplog.text
    assert "generation_workflow_complete_success" in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_question_generation_llm_failure(caplog):
    """Test handling of LLM provider failures during question generation."""
    from src.question.types import QuizLanguage
    from src.quiz.orchestrator.question_generation import (
        orchestrate_quiz_question_generation,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    language = QuizLanguage.ENGLISH

    # Mock generation service that raises LLM failure
    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.side_effect = RuntimeError(
        "LLM API failure"
    )

    with patch(
        "src.quiz.orchestrator.question_generation.execute_in_transaction"
    ) as mock_execute_transaction:
        # Mock job reservation success
        mock_execute_transaction.side_effect = [True, None]

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_prepare_content:
            mock_prepare_content.return_value = {
                "module_1": [{"content": "Content", "word_count": 100}]
            }

            # Act
            await orchestrate_quiz_question_generation(
                quiz_id, 10, "gpt-4", 0.7, language, mock_generation_service
            )

    # Assert
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.assert_called_once()

    # Verify error logging and status update to failed
    assert "generation_workflow_failed" in caplog.text
    assert "LLM API failure" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_question_generation_validation_retry(caplog):
    """Test partial success scenario with failed validation requiring retry."""
    from src.question.types import QuizLanguage
    from src.quiz.orchestrator.question_generation import (
        orchestrate_quiz_question_generation,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    language = QuizLanguage.ENGLISH

    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )

    # Mock partial success - some batches failed validation
    mock_batch_results = {
        "module_1": ["question1", "question2"],  # Success
        "module_2": [],  # Failed
    }
    mock_batch_status = {
        "successful_batches": ["module_1_multiple_choice"],
        "failed_batches": ["module_2_true_false"],  # Failed validation
    }
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.return_value = (
        mock_batch_results,
        mock_batch_status,
    )

    with patch(
        "src.quiz.orchestrator.question_generation.execute_in_transaction"
    ) as mock_execute_transaction:
        mock_execute_transaction.side_effect = [True, None]

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_prepare_content:
            mock_prepare_content.return_value = {
                "module_1": [{"content": "Module 1", "word_count": 100}],
                "module_2": [{"content": "Module 2", "word_count": 150}],
            }

            # Mock quiz for batch status checking - expect 2 batches total
            with patch("src.database.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_quiz = Mock()
                mock_quiz.selected_modules = {
                    "module_1": {
                        "question_batches": [
                            {"question_type": "multiple_choice", "count": 2}
                        ]
                    },
                    "module_2": {
                        "question_batches": [
                            {"question_type": "true_false", "count": 3}
                        ]
                    },
                }
                mock_quiz.generation_metadata = {
                    "successful_batches": [],
                    "failed_batches": [],
                }
                mock_session.get = AsyncMock(return_value=mock_quiz)
                mock_session.refresh = AsyncMock()
                mock_get_session.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

                # Act
                await orchestrate_quiz_question_generation(
                    quiz_id, 10, "gpt-4", 0.7, language, mock_generation_service
                )

    # Assert
    assert "generation_workflow_partial_success" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_question_generation_mixed_types(caplog):
    """Test question generation with mixed question types per module."""
    from src.question.types import QuizLanguage
    from src.quiz.orchestrator.question_generation import (
        orchestrate_quiz_question_generation,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    language = QuizLanguage.NORWEGIAN

    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )

    # Mock results for multiple question types per module
    mock_batch_results = {
        "module_1": ["q1", "q2", "q3", "q4", "q5"],  # Multiple types
        "module_2": ["q6", "q7"],
    }
    mock_batch_status = {
        "successful_batches": [
            "module_1_multiple_choice",
            "module_1_true_false",
            "module_1_fill_in_blank",
            "module_2_multiple_choice",
        ],
        "failed_batches": [],
    }
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.return_value = (
        mock_batch_results,
        mock_batch_status,
    )

    with patch(
        "src.quiz.orchestrator.question_generation.execute_in_transaction"
    ) as mock_execute_transaction:
        mock_execute_transaction.side_effect = [True, None]

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_prepare_content:
            mock_prepare_content.return_value = {
                "module_1": [{"content": "Rich content", "word_count": 300}],
                "module_2": [{"content": "Simple content", "word_count": 100}],
            }

            # Mock quiz with mixed question types
            with patch("src.database.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_quiz = Mock()
                mock_quiz.selected_modules = {
                    "module_1": {
                        "question_batches": [
                            {"question_type": "multiple_choice", "count": 2},
                            {"question_type": "true_false", "count": 2},
                            {"question_type": "fill_in_blank", "count": 1},
                        ]
                    },
                    "module_2": {
                        "question_batches": [
                            {"question_type": "multiple_choice", "count": 2}
                        ]
                    },
                }
                mock_quiz.generation_metadata = {
                    "successful_batches": [],
                    "failed_batches": [],
                }
                mock_session.get = AsyncMock(return_value=mock_quiz)
                mock_session.refresh = AsyncMock()
                mock_get_session.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

                # Act
                await orchestrate_quiz_question_generation(
                    quiz_id, 15, "gpt-4", 0.7, language, mock_generation_service
                )

    # Assert
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.assert_called_once()

    # Verify Norwegian language and mixed types processing
    assert "generation_workflow_complete_success" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_question_generation_timeout(caplog):
    """Test timeout handling during question generation."""
    from src.question.types import QuizLanguage
    from src.quiz.exceptions import OrchestrationTimeoutError
    from src.quiz.orchestrator.question_generation import (
        orchestrate_quiz_question_generation,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    language = QuizLanguage.ENGLISH

    # Mock generation service that times out
    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )
    timeout_error = OrchestrationTimeoutError(
        operation="question_generation", timeout_seconds=300, quiz_id=str(quiz_id)
    )
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.side_effect = timeout_error

    with patch(
        "src.quiz.orchestrator.question_generation.execute_in_transaction"
    ) as mock_execute_transaction:
        mock_execute_transaction.side_effect = [True, None]

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_prepare_content:
            mock_prepare_content.return_value = {
                "module_1": [{"content": "Content", "word_count": 100}]
            }

            # Act
            await orchestrate_quiz_question_generation(
                quiz_id, 10, "gpt-4", 0.7, language, mock_generation_service
            )

    # Assert
    assert "generation_workflow_failed" in caplog.text
    assert "OrchestrationTimeoutError" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_question_generation_batch_coordination(caplog):
    """Test batch processing coordination with metadata updates."""
    from src.question.types import QuizLanguage
    from src.quiz.orchestrator.question_generation import (
        orchestrate_quiz_question_generation,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    language = QuizLanguage.ENGLISH

    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )

    # Mock complex batch coordination scenario
    mock_batch_results = {"module_1": ["q1", "q2"], "module_2": ["q3"]}
    mock_batch_status = {
        "successful_batches": ["module_1_multiple_choice", "module_2_true_false"],
        "failed_batches": ["module_1_fill_in_blank"],  # One batch failed
    }
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.return_value = (
        mock_batch_results,
        mock_batch_status,
    )

    with patch(
        "src.quiz.orchestrator.question_generation.execute_in_transaction"
    ) as mock_execute_transaction:
        mock_execute_transaction.side_effect = [True, None]

        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_prepare_content:
            mock_prepare_content.return_value = {
                "module_1": [{"content": "Module 1", "word_count": 200}],
                "module_2": [{"content": "Module 2", "word_count": 150}],
            }

            # Mock quiz with previous generation metadata
            with patch("src.database.get_async_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_quiz = Mock()
                mock_quiz.selected_modules = {
                    "module_1": {
                        "question_batches": [
                            {"question_type": "multiple_choice", "count": 2},
                            {"question_type": "fill_in_blank", "count": 1},
                        ]
                    },
                    "module_2": {
                        "question_batches": [
                            {"question_type": "true_false", "count": 1}
                        ]
                    },
                }
                # Previous metadata shows some historical batches but not enough for complete success
                mock_quiz.generation_metadata = {
                    "successful_batches": [],  # No previous successes to ensure partial success
                    "failed_batches": [],
                }
                mock_session.get = AsyncMock(return_value=mock_quiz)
                mock_session.refresh = AsyncMock()
                mock_get_session.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

                # Act
                await orchestrate_quiz_question_generation(
                    quiz_id, 10, "gpt-4", 0.7, language, mock_generation_service
                )

    # Assert
    assert "generation_workflow_batch_status_check" in caplog.text
    assert "generation_workflow_partial_success" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_question_generation_job_already_running(caplog):
    """Test handling when generation job is already running or complete."""
    from src.question.types import QuizLanguage
    from src.quiz.orchestrator.question_generation import (
        orchestrate_quiz_question_generation,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    language = QuizLanguage.ENGLISH

    mock_generation_service = Mock()

    with patch(
        "src.quiz.orchestrator.question_generation.execute_in_transaction"
    ) as mock_execute_transaction:
        # Mock job reservation failure (returns False)
        mock_execute_transaction.return_value = False

        # Act
        await orchestrate_quiz_question_generation(
            quiz_id, 10, "gpt-4", 0.7, language, mock_generation_service
        )

    # Assert
    mock_execute_transaction.assert_called_once()  # Only reservation call

    # Generation service should not be called
    assert (
        not hasattr(
            mock_generation_service, "generate_questions_for_quiz_with_batch_tracking"
        )
        or not mock_generation_service.generate_questions_for_quiz_with_batch_tracking.called
    )

    # Verify logging
    assert "generation_orchestration_skipped" in caplog.text
    assert "job_already_running_or_complete" in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_question_generation_no_content_found(caplog):
    """Test handling when no content is found for question generation."""
    from src.question.types import QuizLanguage
    from src.quiz.orchestrator.question_generation import (
        orchestrate_quiz_question_generation,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    language = QuizLanguage.ENGLISH

    mock_generation_service = Mock()

    with patch(
        "src.quiz.orchestrator.question_generation.execute_in_transaction"
    ) as mock_execute_transaction:
        mock_execute_transaction.side_effect = [True, None]  # Job reservation success

        # Mock no content found
        with patch(
            "src.question.services.prepare_and_validate_content"
        ) as mock_prepare_content:
            mock_prepare_content.return_value = {}  # No content

            # Act
            await orchestrate_quiz_question_generation(
                quiz_id, 10, "gpt-4", 0.7, language, mock_generation_service
            )

    # Assert
    assert mock_execute_transaction.call_count == 2  # Reservation + save result

    # Verify error logging
    assert "generation_workflow_no_content_found" in caplog.text
    assert str(quiz_id) in caplog.text
