"""Tests for content extraction orchestration."""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.asyncio
async def test_execute_content_extraction_workflow_canvas_only(caplog):
    """Test content extraction workflow with only Canvas modules."""
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"
    selected_modules = {
        "101": {
            "name": "Module 1",
            "source_type": "canvas",
            "question_batches": [{"question_type": "multiple_choice", "count": 10}],
        },
        "102": {
            "name": "Module 2",
            "source_type": "canvas",
            "question_batches": [{"question_type": "true_false", "count": 5}],
        },
    }

    # Mock content extractor and summarizer
    mock_extractor = AsyncMock()
    mock_extractor.return_value = {
        "101": [{"content": "Canvas content 1", "word_count": 100}],
        "102": [{"content": "Canvas content 2", "word_count": 150}],
    }

    mock_summarizer = Mock()
    mock_summarizer.return_value = {
        "modules_processed": 2,
        "total_pages": 2,
        "total_word_count": 250,
    }

    # Act
    result = await _execute_content_extraction_workflow(
        quiz_id,
        canvas_course_id,
        canvas_token,
        selected_modules,
        mock_extractor,
        mock_summarizer,
    )

    extracted_content, final_status, cleaned_modules = result

    # Assert
    assert final_status == "completed"
    assert extracted_content is not None
    assert "101" in extracted_content
    assert "102" in extracted_content

    # Verify Canvas modules were processed
    mock_extractor.assert_called_once_with(canvas_token, canvas_course_id, [101, 102])
    mock_summarizer.assert_called_once()

    # Verify logging (JSON structured logging)
    assert "content_extraction_workflow_started" in caplog.text
    assert "content_extraction_workflow_completed" in caplog.text


@pytest.mark.asyncio
async def test_execute_content_extraction_workflow_manual_only(caplog):
    """Test content extraction workflow with only manual modules."""
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"
    selected_modules = {
        "manual_1": {
            "name": "Manual Module 1",
            "source_type": "manual",
            "content": "Manual content text here",
            "word_count": 50,
            "content_type": "text",
            "question_batches": [{"question_type": "multiple_choice", "count": 5}],
        },
        "manual_2": {
            "name": "Manual Module 2",
            "source_type": "manual",
            "content": "More manual content",
            "word_count": 30,
            "content_type": "text",
            "question_batches": [{"question_type": "fill_in_blank", "count": 3}],
        },
    }

    # Mock content extractor (should not be called) and summarizer
    mock_extractor = AsyncMock()
    mock_summarizer = Mock()
    mock_summarizer.return_value = {
        "modules_processed": 2,
        "total_pages": 2,
        "total_word_count": 80,
    }

    # Act
    result = await _execute_content_extraction_workflow(
        quiz_id,
        canvas_course_id,
        canvas_token,
        selected_modules,
        mock_extractor,
        mock_summarizer,
    )

    extracted_content, final_status, cleaned_modules = result

    # Assert
    assert final_status == "completed"
    assert extracted_content is not None
    assert "manual_1" in extracted_content
    assert "manual_2" in extracted_content

    # Verify manual content structure
    manual_content_1 = extracted_content["manual_1"][0]
    assert manual_content_1["content"] == "Manual content text here"
    assert manual_content_1["word_count"] == 50
    assert manual_content_1["source_type"] == "manual"
    assert manual_content_1["title"] == "Manual Module 1"

    # Canvas extractor should not be called for manual-only workflow
    mock_extractor.assert_not_called()
    mock_summarizer.assert_called_once()

    # Verify logging
    assert "content_modules_categorized" in caplog.text


@pytest.mark.asyncio
async def test_execute_content_extraction_workflow_mixed_sources(caplog):
    """Test content extraction workflow with both Canvas and manual modules."""
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"
    selected_modules = {
        "101": {
            "name": "Canvas Module",
            "source_type": "canvas",
            "question_batches": [{"question_type": "multiple_choice", "count": 8}],
        },
        "manual_1": {
            "name": "Manual Module",
            "source_type": "manual",
            "content": "Manual text content",
            "word_count": 75,
            "question_batches": [{"question_type": "true_false", "count": 4}],
        },
    }

    # Mock functions
    mock_extractor = AsyncMock()
    mock_extractor.return_value = {
        "101": [{"content": "Canvas content", "word_count": 200}]
    }

    mock_summarizer = Mock()
    mock_summarizer.return_value = {
        "modules_processed": 2,
        "total_pages": 2,
        "total_word_count": 275,
    }

    # Act
    result = await _execute_content_extraction_workflow(
        quiz_id,
        canvas_course_id,
        canvas_token,
        selected_modules,
        mock_extractor,
        mock_summarizer,
    )

    extracted_content, final_status, cleaned_modules = result

    # Assert
    assert final_status == "completed"
    assert extracted_content is not None
    assert "101" in extracted_content  # Canvas content
    assert "manual_1" in extracted_content  # Manual content

    # Verify both processing types occurred
    mock_extractor.assert_called_once_with(canvas_token, canvas_course_id, [101])
    mock_summarizer.assert_called_once()

    # Verify logging shows mixed processing
    assert "content_modules_categorized" in caplog.text


@pytest.mark.asyncio
async def test_execute_content_extraction_workflow_unknown_source_type(caplog):
    """Test handling of unknown source types (should fallback to canvas)."""
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"
    selected_modules = {
        "103": {
            "name": "Unknown Source Module",
            "source_type": "future_type",  # Unknown source type
            "question_batches": [{"question_type": "multiple_choice", "count": 5}],
        }
    }

    mock_extractor = AsyncMock()
    mock_extractor.return_value = {
        "103": [{"content": "Fallback canvas content", "word_count": 100}]
    }

    mock_summarizer = Mock()
    mock_summarizer.return_value = {
        "modules_processed": 1,
        "total_pages": 1,
        "total_word_count": 100,
    }

    # Act
    result = await _execute_content_extraction_workflow(
        quiz_id,
        canvas_course_id,
        canvas_token,
        selected_modules,
        mock_extractor,
        mock_summarizer,
    )

    extracted_content, final_status, cleaned_modules = result

    # Assert
    assert final_status == "completed"
    assert extracted_content is not None

    # Should treat unknown type as canvas module
    mock_extractor.assert_called_once_with(canvas_token, canvas_course_id, [103])

    # Verify warning was logged
    assert "unknown_source_type_encountered" in caplog.text


@pytest.mark.asyncio
async def test_execute_content_extraction_workflow_invalid_module_id_fallback(caplog):
    """Test handling of invalid module ID during canvas fallback."""
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"
    selected_modules = {
        "invalid_id": {  # Cannot convert to int
            "name": "Invalid ID Module",
            "source_type": "unknown_type",
            "question_batches": [{"question_type": "multiple_choice", "count": 5}],
        }
    }

    mock_extractor = AsyncMock()
    mock_extractor.return_value = {}  # No content extracted

    mock_summarizer = Mock()
    mock_summarizer.return_value = {
        "modules_processed": 0,
        "total_pages": 0,
        "total_word_count": 0,
    }

    # Act
    result = await _execute_content_extraction_workflow(
        quiz_id,
        canvas_course_id,
        canvas_token,
        selected_modules,
        mock_extractor,
        mock_summarizer,
    )

    extracted_content, final_status, cleaned_modules = result

    # Assert
    assert final_status == "no_content"  # No content extracted
    assert extracted_content is None

    # Should not call extractor when invalid module ID causes no valid canvas modules
    mock_extractor.assert_not_called()

    # Verify error was logged
    assert "invalid_module_id_for_canvas_fallback" in caplog.text


@pytest.mark.asyncio
async def test_execute_content_extraction_workflow_no_content_found(caplog):
    """Test handling when no meaningful content is extracted."""
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"
    selected_modules = {
        "104": {
            "name": "Empty Module",
            "source_type": "canvas",
            "question_batches": [{"question_type": "multiple_choice", "count": 5}],
        }
    }

    mock_extractor = AsyncMock()
    mock_extractor.return_value = {}  # No content

    mock_summarizer = Mock()
    mock_summarizer.return_value = {
        "modules_processed": 0,
        "total_pages": 0,
        "total_word_count": 0,  # No content
    }

    # Act
    result = await _execute_content_extraction_workflow(
        quiz_id,
        canvas_course_id,
        canvas_token,
        selected_modules,
        mock_extractor,
        mock_summarizer,
    )

    extracted_content, final_status, cleaned_modules = result

    # Assert
    assert final_status == "no_content"
    assert extracted_content is None

    # Verify warning logged
    assert "extraction_completed_but_no_content_found" in caplog.text


@pytest.mark.asyncio
async def test_execute_content_extraction_workflow_exception_handling(caplog):
    """Test exception handling during content extraction."""
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"
    selected_modules = {
        "105": {
            "name": "Problem Module",
            "source_type": "canvas",
            "question_batches": [{"question_type": "multiple_choice", "count": 5}],
        }
    }

    # Mock extractor to raise exception
    mock_extractor = AsyncMock()
    mock_extractor.side_effect = RuntimeError("Canvas API failure")

    mock_summarizer = Mock()

    # Act
    result = await _execute_content_extraction_workflow(
        quiz_id,
        canvas_course_id,
        canvas_token,
        selected_modules,
        mock_extractor,
        mock_summarizer,
    )

    extracted_content, final_status, cleaned_modules = result

    # Assert
    assert final_status == "failed"
    assert extracted_content is None
    assert cleaned_modules == selected_modules  # Original modules returned

    # Summarizer should not be called on exception
    mock_summarizer.assert_not_called()

    # Verify error logging
    assert "content_extraction_workflow_failed" in caplog.text


@pytest.mark.asyncio
async def test_execute_content_extraction_workflow_module_cleaning():
    """Test that selected_modules are cleaned to prevent content duplication."""
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"
    selected_modules = {
        "101": {
            "name": "Test Module",
            "source_type": "canvas",
            "question_batches": [{"question_type": "multiple_choice", "count": 10}],
            "extra_field": "should_be_removed",  # Extra field to test cleaning
            "content": "should_be_removed",  # Content should be removed
            "processing_metadata": {"temp": "data"},  # Should be removed
        }
    }

    mock_extractor = AsyncMock()
    mock_extractor.return_value = {
        "101": [{"content": "Canvas content", "word_count": 100}]
    }

    mock_summarizer = Mock()
    mock_summarizer.return_value = {
        "modules_processed": 1,
        "total_pages": 1,
        "total_word_count": 100,
    }

    # Act
    result = await _execute_content_extraction_workflow(
        quiz_id,
        canvas_course_id,
        canvas_token,
        selected_modules,
        mock_extractor,
        mock_summarizer,
    )

    extracted_content, final_status, cleaned_modules = result

    # Assert
    assert final_status == "completed"
    assert cleaned_modules is not None

    # Verify only essential fields are kept
    cleaned_module = cleaned_modules["101"]
    assert "name" in cleaned_module
    assert "source_type" in cleaned_module
    assert "question_batches" in cleaned_module

    # Verify extra fields are removed
    assert "extra_field" not in cleaned_module
    assert "content" not in cleaned_module
    assert "processing_metadata" not in cleaned_module


@pytest.mark.asyncio
@patch("src.quiz.orchestrator.content_extraction.execute_in_transaction")
@patch("src.quiz.orchestrator.content_extraction._execute_content_extraction_workflow")
async def test_orchestrate_content_extraction_job_reservation_success(
    mock_workflow, mock_execute_transaction, caplog
):
    """Test successful job reservation and content extraction orchestration."""
    from src.quiz.orchestrator.content_extraction import orchestrate_content_extraction

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"

    # Mock job reservation success
    mock_quiz_settings = {
        "selected_modules": {
            "101": {
                "name": "Test Module",
                "source_type": "canvas",
                "question_batches": [{"question_type": "multiple_choice", "count": 5}],
            }
        },
        "target_questions": 10,
        "llm_model": "gpt-4",
        "llm_temperature": 0.7,
    }

    # Mock transaction calls: first for reservation, second for saving result
    mock_execute_transaction.side_effect = [
        mock_quiz_settings,  # Job reservation returns quiz settings
        None,  # Save result succeeds
    ]

    # Mock workflow execution
    mock_workflow.return_value = (
        {"101": [{"content": "Test content", "word_count": 100}]},  # extracted_content
        "completed",  # final_status
        {"101": {"name": "Test Module", "source_type": "canvas"}},  # cleaned_modules
    )

    # Mock content extraction functions (won't be called due to workflow mock)
    mock_extractor = AsyncMock()
    mock_summarizer = Mock()

    # Act
    await orchestrate_content_extraction(
        quiz_id, canvas_course_id, canvas_token, mock_extractor, mock_summarizer
    )

    # Assert
    assert mock_execute_transaction.call_count == 2
    mock_workflow.assert_called_once()

    # Verify logging
    assert "content_extraction_orchestration_started" in caplog.text


@pytest.mark.asyncio
@patch("src.quiz.orchestrator.content_extraction.execute_in_transaction")
async def test_orchestrate_content_extraction_job_already_running(
    mock_execute_transaction, caplog
):
    """Test handling when extraction job is already running or complete."""
    from src.quiz.orchestrator.content_extraction import orchestrate_content_extraction

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_course_id = 12345
    canvas_token = "test_token"

    # Mock job reservation failure (returns None)
    mock_execute_transaction.return_value = None

    mock_extractor = AsyncMock()
    mock_summarizer = Mock()

    # Act
    await orchestrate_content_extraction(
        quiz_id, canvas_course_id, canvas_token, mock_extractor, mock_summarizer
    )

    # Assert
    mock_execute_transaction.assert_called_once()  # Only reservation call

    # Content extraction functions should not be called
    mock_extractor.assert_not_called()
    mock_summarizer.assert_not_called()

    # Verify logging
    assert "extraction_orchestration_skipped" in caplog.text
