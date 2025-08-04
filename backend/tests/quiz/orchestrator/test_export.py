"""Tests for Canvas export orchestration."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_orchestrate_export_canvas_success(caplog):
    """Test successful Canvas quiz export workflow."""
    from src.quiz.orchestrator.export import orchestrate_quiz_export_to_canvas

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_token = "test_canvas_token"

    # Mock Canvas functions
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {"id": 12345, "title": "Test Quiz"}

    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = [
        {"success": True, "canvas_id": 1001, "question_id": "q1"},
        {"success": True, "canvas_id": 1002, "question_id": "q2"},
        {"success": True, "canvas_id": 1003, "question_id": "q3"},
    ]

    # Mock question data preparation
    mock_question_data = [
        {"id": "q1", "question_text": "Question 1?", "approved": True},
        {"id": "q2", "question_text": "Question 2?", "approved": True},
        {"id": "q3", "question_text": "Question 3?", "approved": True},
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            # Mock transaction calls: validate/reserve + save success results
            mock_export_data = {
                "course_id": 67890,
                "title": "Test Quiz Export",
                "already_exported": False,
                "questions": mock_question_data,
            }

            mock_execute_transaction.side_effect = [
                mock_export_data,  # Validate and reserve
                {  # Save success results
                    "success": True,
                    "canvas_quiz_id": 12345,
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
    assert result["canvas_quiz_id"] == 12345
    assert result["exported_questions"] == 3

    # Verify Canvas operations were called
    mock_quiz_creator.assert_called_once_with(
        canvas_token, 67890, "Test Quiz Export", 3
    )
    mock_question_exporter.assert_called_once_with(
        canvas_token, 67890, 12345, mock_question_data
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

    mock_question_data = [{"id": "q1", "question_text": "Test?", "approved": True}]

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

    # Arrange
    quiz_id = uuid.uuid4()
    canvas_token = "integration_token"
    course_id = 98765

    # Mock Canvas API integration
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {
        "id": 54321,
        "title": "Integration Test Quiz",
        "course_id": course_id,
    }

    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = [
        {"success": True, "canvas_id": 2001, "question_id": "q1"},
        {"success": True, "canvas_id": 2002, "question_id": "q2"},
    ]

    mock_question_data = [
        {"id": "q1", "question_text": "Integration question 1?", "approved": True},
        {"id": "q2", "question_text": "Integration question 2?", "approved": True},
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
                "title": "Integration Test Quiz",
                "already_exported": False,
                "questions": mock_question_data,
            }

            mock_execute_transaction.side_effect = [
                mock_export_data,  # Validate and reserve
                {  # Save success
                    "success": True,
                    "canvas_quiz_id": 54321,
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
        canvas_token, course_id, "Integration Test Quiz", 2
    )
    mock_question_exporter.assert_called_once_with(
        canvas_token, course_id, 54321, mock_question_data
    )

    assert result["canvas_quiz_id"] == 54321
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

    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {"id": 99999, "title": "Format Test"}

    mock_question_exporter = AsyncMock()
    # Mock successful format conversion
    mock_question_exporter.return_value = [
        {
            "success": True,
            "canvas_id": 3001,
            "question_id": "mc1",
            "converted_format": "multiple_choice_question",
        },
        {
            "success": True,
            "canvas_id": 3002,
            "question_id": "tf1",
            "converted_format": "true_false_question",
        },
        {
            "success": True,
            "canvas_id": 3003,
            "question_id": "fib1",
            "converted_format": "fill_in_multiple_blanks_question",
        },
    ]

    # Mock various question types requiring format conversion
    mock_question_data = [
        {
            "id": "mc1",
            "question_type": "multiple_choice",
            "question_text": "MC Question?",
            "approved": True,
        },
        {
            "id": "tf1",
            "question_type": "true_false",
            "question_text": "TF Question?",
            "approved": True,
        },
        {
            "id": "fib1",
            "question_type": "fill_in_blank",
            "question_text": "FIB: ___ is correct",
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
                "course_id": 11111,
                "title": "Format Test Quiz",
                "already_exported": False,
                "questions": mock_question_data,
            }

            mock_execute_transaction.side_effect = [
                mock_export_data,
                {
                    "success": True,
                    "canvas_quiz_id": 99999,
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
        canvas_token, 11111, 99999, mock_question_data
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
    course_id = 22222

    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {"id": 77777, "title": "Failed Export Quiz"}

    # Mock partial failure in question export
    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = [
        {"success": True, "canvas_id": 4001, "question_id": "q1"},
        {
            "success": False,
            "canvas_id": None,
            "question_id": "q2",
            "error": "Format error",
        },
        {
            "success": False,
            "canvas_id": None,
            "question_id": "q3",
            "error": "Validation failed",
        },
    ]

    mock_question_data = [
        {"id": "q1", "question_text": "Good question?", "approved": True},
        {"id": "q2", "question_text": "Bad question?", "approved": True},
        {"id": "q3", "question_text": "Another bad question?", "approved": True},
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
                "title": "Failed Export Quiz",
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
    mock_delete_quiz.assert_called_once_with(canvas_token, course_id, 77777)

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

    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {"id": 55555, "title": "Completion Test"}

    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = [
        {"success": True, "canvas_id": 5001, "question_id": "q1"},
        {"success": True, "canvas_id": 5002, "question_id": "q2"},
    ]

    mock_question_data = [
        {"id": "q1", "question_text": "Completion question 1?", "approved": True},
        {"id": "q2", "question_text": "Completion question 2?", "approved": True},
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            mock_export_data = {
                "course_id": 33333,
                "title": "Completion Test Quiz",
                "already_exported": False,
                "questions": mock_question_data,
            }

            mock_completion_result = {
                "success": True,
                "canvas_quiz_id": 55555,
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
    assert result["canvas_quiz_id"] == 55555
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
        {"id": "q1", "question_text": "Already exported?", "approved": True}
    ]

    with patch(
        "src.question.service.prepare_questions_for_export"
    ) as mock_prepare_questions:
        mock_prepare_questions.return_value = mock_question_data

        with patch(
            "src.quiz.orchestrator.export.execute_in_transaction"
        ) as mock_execute_transaction:
            # Mock already exported scenario
            mock_export_data = {
                "course_id": 44444,
                "title": "Already Exported Quiz",
                "already_exported": True,
                "canvas_quiz_id": 88888,
                "questions": mock_question_data,
            }

            mock_execute_transaction.return_value = mock_export_data

            # Act
            result = await orchestrate_quiz_export_to_canvas(
                quiz_id, canvas_token, mock_quiz_creator, mock_question_exporter
            )

    # Assert
    assert result["success"] is True
    assert result["canvas_quiz_id"] == 88888
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
