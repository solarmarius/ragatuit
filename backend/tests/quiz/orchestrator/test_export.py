"""Tests for Canvas export orchestration."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tests.common_mocks import (
    mock_canvas_api,
    mock_database_operations,
)
from tests.test_data import (
    DEFAULT_CANVAS_QUIZ_RESPONSE,
    DEFAULT_FILL_IN_BLANK_DATA,
    DEFAULT_MCQ_DATA,
    DEFAULT_QUIZ_ITEMS_RESPONSE,
    DEFAULT_TRUE_FALSE_DATA,
    FAILED_QUIZ_ITEMS_RESPONSE,
    SAMPLE_QUESTIONS_BATCH,
    get_unique_course_data,
    get_unique_quiz_config,
)


@pytest.mark.asyncio
async def test_orchestrate_export_canvas_success(caplog):
    """Test successful Canvas quiz export workflow."""
    from src.quiz.orchestrator.export import orchestrate_quiz_export_to_canvas

    # Arrange - Generate consistent test data
    quiz_id = uuid.uuid4()
    canvas_token = "test_canvas_token"
    course_data = get_unique_course_data()
    quiz_config = get_unique_quiz_config()

    # Mock Canvas functions using centralized data
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = DEFAULT_CANVAS_QUIZ_RESPONSE

    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = DEFAULT_QUIZ_ITEMS_RESPONSE

    # Mock question data preparation using centralized data
    mock_question_data = [
        {
            "id": "q1",
            "question_text": SAMPLE_QUESTIONS_BATCH[0]["question_text"],
            "approved": True,
        },
        {
            "id": "q2",
            "question_text": SAMPLE_QUESTIONS_BATCH[1]["question_text"],
            "approved": True,
        },
        {"id": "q3", "question_text": "What is Python?", "approved": True},
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            # Mock transaction calls using generated data
            mock_export_data = {
                "course_id": course_data["id"],
                "title": quiz_config["title"],
                "already_exported": False,
                "questions": mock_question_data,
            }

            mock_execute_transaction.side_effect = [
                mock_export_data,  # Validate and reserve
                {  # Save success results
                    "success": True,
                    "canvas_quiz_id": DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
                    "exported_questions": 3,
                    "message": "Quiz successfully exported to Canvas",
                },
            ]

            # Act
            result = await orchestrate_quiz_export_to_canvas(
                quiz_id, canvas_token, mock_quiz_creator, mock_question_exporter
            )

    # Assert
    assert result["success"] is True
    assert result["canvas_quiz_id"] == DEFAULT_CANVAS_QUIZ_RESPONSE["id"]
    assert result["exported_questions"] == 3

    # Verify Canvas operations were called
    mock_quiz_creator.assert_called_once_with(
        canvas_token, course_data["id"], quiz_config["title"], 3
    )
    mock_question_exporter.assert_called_once_with(
        canvas_token,
        course_data["id"],
        DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
        mock_question_data,
    )

    # Verify logging
    assert "quiz_export_orchestration_started" in caplog.text
    assert "canvas_export_complete_success" in caplog.text
    assert "quiz_export_orchestration_completed_success" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_export_job_reservation(caplog):
    """Test export job reservation and concurrency handling."""
    from src.quiz.orchestrator.export import orchestrate_quiz_export_to_canvas

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_token = "test_token"

    mock_quiz_creator = AsyncMock()
    mock_question_exporter = AsyncMock()

    mock_question_data = [
        {
            "id": "q1",
            "question_text": DEFAULT_MCQ_DATA["question_text"],
            "approved": True,
        }
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            # Mock job reservation failure (already running)
            mock_execute_transaction.return_value = None

            # Act & Assert
            with pytest.raises(
                RuntimeError, match="Failed to validate quiz for export"
            ):
                await orchestrate_quiz_export_to_canvas(
                    quiz_id, canvas_token, mock_quiz_creator, mock_question_exporter
                )

    # Assert
    mock_execute_transaction.assert_called_once()  # Only reservation call

    # Canvas operations should not be called
    mock_quiz_creator.assert_not_called()
    mock_question_exporter.assert_not_called()

    # Verify logging
    assert "quiz_export_orchestration_started" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_export_canvas_api_integration(caplog):
    """Test Canvas API integration for quiz creation and question export."""
    from src.quiz.orchestrator.export import orchestrate_quiz_export_to_canvas

    # Arrange - Generate consistent test data
    quiz_id = uuid.uuid4()
    canvas_token = "integration_token"
    course_data = get_unique_course_data()
    course_id = course_data["id"]
    quiz_config = get_unique_quiz_config()

    # Mock Canvas API integration using centralized data
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {
        "id": DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
        "title": quiz_config["title"],
        "course_id": course_id,
    }

    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = DEFAULT_QUIZ_ITEMS_RESPONSE[:2]

    mock_question_data = [
        {
            "id": "q1",
            "question_text": SAMPLE_QUESTIONS_BATCH[0]["question_text"],
            "approved": True,
        },
        {
            "id": "q2",
            "question_text": SAMPLE_QUESTIONS_BATCH[1]["question_text"],
            "approved": True,
        },
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            mock_export_data = {
                "course_id": course_id,
                "title": quiz_config["title"],
                "already_exported": False,
                "questions": mock_question_data,
            }

            mock_execute_transaction.side_effect = [
                mock_export_data,  # Validate and reserve
                {  # Save success
                    "success": True,
                    "canvas_quiz_id": DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
                    "exported_questions": 2,
                    "message": "Quiz successfully exported to Canvas",
                },
            ]

            # Act
            result = await orchestrate_quiz_export_to_canvas(
                quiz_id, canvas_token, mock_quiz_creator, mock_question_exporter
            )

    # Assert Canvas API integration
    mock_quiz_creator.assert_called_once_with(
        canvas_token, course_id, quiz_config["title"], 2
    )
    mock_question_exporter.assert_called_once_with(
        canvas_token, course_id, DEFAULT_CANVAS_QUIZ_RESPONSE["id"], mock_question_data
    )

    assert result["canvas_quiz_id"] == DEFAULT_CANVAS_QUIZ_RESPONSE["id"]
    assert result["exported_questions"] == 2

    # Verify integration logging
    assert "canvas_quiz_created_for_export" in caplog.text
    assert "canvas_export_results_analyzed" in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_export_question_format_conversion(caplog):
    """Test question format conversion during export process."""
    from src.quiz.orchestrator.export import orchestrate_quiz_export_to_canvas

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_token = "format_token"

    quiz_config = get_unique_quiz_config()
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {
        "id": DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
        "title": quiz_config["title"],
    }

    mock_question_exporter = AsyncMock()
    # Mock successful format conversion
    mock_question_exporter.return_value = [
        {
            "success": True,
            "canvas_id": DEFAULT_QUIZ_ITEMS_RESPONSE[0]["canvas_id"],
            "question_id": "mc1",
            "converted_format": "multiple_choice_question",
        },
        {
            "success": True,
            "canvas_id": DEFAULT_QUIZ_ITEMS_RESPONSE[1]["canvas_id"],
            "question_id": "tf1",
            "converted_format": "true_false_question",
        },
        {
            "success": True,
            "canvas_id": DEFAULT_QUIZ_ITEMS_RESPONSE[2]["canvas_id"],
            "question_id": "fib1",
            "converted_format": "fill_in_multiple_blanks_question",
        },
    ]

    # Mock various question types using centralized data
    mock_question_data = [
        {
            "id": "mc1",
            "question_type": "multiple_choice",
            "question_text": DEFAULT_MCQ_DATA["question_text"],
            "approved": True,
        },
        {
            "id": "tf1",
            "question_type": "true_false",
            "question_text": DEFAULT_TRUE_FALSE_DATA["question_text"],
            "approved": True,
        },
        {
            "id": "fib1",
            "question_type": "fill_in_blank",
            "question_text": DEFAULT_FILL_IN_BLANK_DATA["question_text"],
            "approved": True,
        },
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            course_data = get_unique_course_data()
            mock_export_data = {
                "course_id": course_data["id"],
                "title": quiz_config["title"],
                "already_exported": False,
                "questions": mock_question_data,
            }

            mock_execute_transaction.side_effect = [
                mock_export_data,
                {
                    "success": True,
                    "canvas_quiz_id": DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
                    "exported_questions": 3,
                    "message": "Quiz successfully exported to Canvas",
                },
            ]

            # Act
            result = await orchestrate_quiz_export_to_canvas(
                quiz_id, canvas_token, mock_quiz_creator, mock_question_exporter
            )

    # Assert
    assert result["success"] is True
    assert result["exported_questions"] == 3

    # Verify all question types were processed
    mock_question_exporter.assert_called_once_with(
        canvas_token,
        course_data["id"],
        DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
        mock_question_data,
    )

    # Verify format conversion logging
    assert "canvas_export_results_analyzed" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_export_failure_rollback(caplog):
    """Test export failure handling and Canvas quiz rollback."""
    from src.quiz.orchestrator.export import orchestrate_quiz_export_to_canvas

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_token = "rollback_token"
    course_data = get_unique_course_data()
    course_id = course_data["id"]
    quiz_config = get_unique_quiz_config()

    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {
        "id": DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
        "title": quiz_config["title"],
    }

    # Mock partial failure in question export using centralized data
    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = FAILED_QUIZ_ITEMS_RESPONSE

    mock_question_data = [
        {
            "id": "q1",
            "question_text": SAMPLE_QUESTIONS_BATCH[0]["question_text"],
            "approved": True,
        },
        {
            "id": "q2",
            "question_text": SAMPLE_QUESTIONS_BATCH[1]["question_text"],
            "approved": True,
        },
        {
            "id": "q3",
            "question_text": DEFAULT_MCQ_DATA["question_text"],
            "approved": True,
        },
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            mock_export_data = {
                "course_id": course_id,
                "title": quiz_config["title"],
                "already_exported": False,
                "questions": mock_question_data,
            }

            # Mock: validate/reserve succeeds, but failure status update also succeeds
            mock_execute_transaction.side_effect = [
                mock_export_data,  # Validate and reserve
                None,  # Mark as failed
            ]

            # Mock Canvas quiz deletion during rollback
            with patch("src.canvas.service.delete_canvas_quiz") as mock_delete_quiz:
                mock_delete_quiz.return_value = True  # Rollback succeeds

                # Act & Assert
                with pytest.raises(Exception):  # CanvasQuizExportError
                    await orchestrate_quiz_export_to_canvas(
                        quiz_id, canvas_token, mock_quiz_creator, mock_question_exporter
                    )

    # Assert rollback was attempted
    mock_delete_quiz.assert_called_once_with(
        canvas_token, course_id, DEFAULT_CANVAS_QUIZ_RESPONSE["id"]
    )

    # Verify failure and rollback logging
    assert "canvas_export_failure_rollback_needed" in caplog.text
    assert "quiz_export_initiating_rollback" in caplog.text
    assert "quiz_export_rollback_completed" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_export_completion_status(caplog):
    """Test export completion and status updates."""
    from src.quiz.orchestrator.export import orchestrate_quiz_export_to_canvas

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_token = "completion_token"

    quiz_config = get_unique_quiz_config()
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {
        "id": DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
        "title": quiz_config["title"],
    }

    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = DEFAULT_QUIZ_ITEMS_RESPONSE[:2]

    mock_question_data = [
        {
            "id": "q1",
            "question_text": SAMPLE_QUESTIONS_BATCH[0]["question_text"],
            "approved": True,
        },
        {
            "id": "q2",
            "question_text": SAMPLE_QUESTIONS_BATCH[1]["question_text"],
            "approved": True,
        },
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            course_data = get_unique_course_data()
            mock_export_data = {
                "course_id": course_data["id"],
                "title": quiz_config["title"],
                "already_exported": False,
                "questions": mock_question_data,
            }

            mock_completion_result = {
                "success": True,
                "canvas_quiz_id": DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
                "exported_questions": 2,
                "message": "Quiz successfully exported to Canvas",
            }

            mock_execute_transaction.side_effect = [
                mock_export_data,  # Validate and reserve
                mock_completion_result,  # Save success results
            ]

            # Act
            result = await orchestrate_quiz_export_to_canvas(
                quiz_id, canvas_token, mock_quiz_creator, mock_question_exporter
            )

    # Assert completion status
    assert result == mock_completion_result
    assert result["success"] is True
    assert result["canvas_quiz_id"] == DEFAULT_CANVAS_QUIZ_RESPONSE["id"]
    assert result["exported_questions"] == 2

    # Verify status update transactions
    assert mock_execute_transaction.call_count == 2

    # Verify completion logging
    assert "quiz_export_orchestration_completed_success" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_orchestrate_export_already_exported_quiz(caplog):
    """Test handling of quiz that has already been exported."""
    from src.quiz.orchestrator.export import orchestrate_quiz_export_to_canvas

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_token = "already_token"

    mock_quiz_creator = AsyncMock()
    mock_question_exporter = AsyncMock()

    mock_question_data = [
        {
            "id": "q1",
            "question_text": DEFAULT_MCQ_DATA["question_text"],
            "approved": True,
        }
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            # Mock already exported scenario using centralized data
            course_data = get_unique_course_data()
            quiz_config = get_unique_quiz_config()
            mock_export_data = {
                "course_id": course_data["id"],
                "title": quiz_config["title"],
                "already_exported": True,
                "canvas_quiz_id": DEFAULT_CANVAS_QUIZ_RESPONSE["id"],
                "questions": mock_question_data,
            }

            mock_execute_transaction.return_value = mock_export_data

            # Act
            result = await orchestrate_quiz_export_to_canvas(
                quiz_id, canvas_token, mock_quiz_creator, mock_question_exporter
            )

    # Assert
    assert result["success"] is True
    assert result["canvas_quiz_id"] == DEFAULT_CANVAS_QUIZ_RESPONSE["id"]
    assert result["exported_questions"] == 0
    assert result["message"] == "Quiz already exported to Canvas"
    assert result["already_exported"] is True

    # Canvas operations should not be called for already exported quiz
    mock_quiz_creator.assert_not_called()
    mock_question_exporter.assert_not_called()

    # Only one transaction call (validation)
    assert mock_execute_transaction.call_count == 1


@pytest.mark.asyncio
async def test_orchestrate_export_no_approved_questions(caplog):
    """Test handling when no approved questions are found for export."""
    from src.quiz.orchestrator.export import orchestrate_quiz_export_to_canvas

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_token = "no_questions_token"

    mock_quiz_creator = AsyncMock()
    mock_question_exporter = AsyncMock()

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        # Mock no approved questions found
        mock_prepare_questions.return_value = None

        # Act & Assert
        with pytest.raises(
            RuntimeError, match="No approved questions found for export"
        ):
            await orchestrate_quiz_export_to_canvas(
                quiz_id, canvas_token, mock_quiz_creator, mock_question_exporter
            )

    # Assert
    mock_prepare_questions.assert_called_once_with(quiz_id)

    # No further operations should occur
    mock_quiz_creator.assert_not_called()
    mock_question_exporter.assert_not_called()

    # Verify logging
    assert "quiz_export_orchestration_started" in caplog.text
    assert str(quiz_id) in caplog.text
