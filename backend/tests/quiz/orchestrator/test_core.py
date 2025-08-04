"""Tests for core orchestration utilities."""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tests.common_mocks import (
    mock_database_operations,
)
from tests.test_data import (
    get_unique_course_data,
    get_unique_user_data,
)


@pytest.mark.asyncio
async def test_safe_background_orchestration_successful_execution(caplog):
    """Test successful execution of orchestration operation."""
    from src.quiz.orchestrator.core import safe_background_orchestration

    # Arrange
    mock_operation = AsyncMock()
    quiz_id = uuid.uuid4()
    operation_name = "test_operation"
    test_args = ("arg1", "arg2")
    test_kwargs = {"key1": "value1", "key2": "value2"}

    # Act
    await safe_background_orchestration(
        mock_operation, operation_name, quiz_id, *test_args, **test_kwargs
    )

    # Assert
    mock_operation.assert_called_once_with(*test_args, **test_kwargs)

    # Verify logging
    assert "background_orchestration_started" in caplog.text
    assert "background_orchestration_completed" in caplog.text
    assert str(quiz_id) in caplog.text
    assert operation_name in caplog.text


@pytest.mark.asyncio
@patch("src.quiz.orchestrator.core._handle_orchestration_failure")
async def test_safe_background_orchestration_timeout_error_handling(
    mock_handle_failure, caplog
):
    """Test OrchestrationTimeoutError is properly handled."""
    from src.quiz.exceptions import OrchestrationTimeoutError
    from src.quiz.orchestrator.core import safe_background_orchestration

    # Arrange
    mock_operation = AsyncMock()
    timeout_error = OrchestrationTimeoutError(
        operation="test_op", timeout_seconds=30, quiz_id="test-id"
    )
    mock_operation.side_effect = timeout_error

    quiz_id = uuid.uuid4()
    operation_name = "test_operation"

    # Act
    await safe_background_orchestration(mock_operation, operation_name, quiz_id)

    # Assert
    mock_handle_failure.assert_called_once()
    call_args = mock_handle_failure.call_args[0]
    assert call_args[0] == quiz_id
    assert call_args[1] == operation_name
    assert call_args[2] == timeout_error

    # Verify error logging
    assert "background_orchestration_timeout" in caplog.text
    assert str(quiz_id) in caplog.text
    assert "timeout_seconds" in caplog.text


@pytest.mark.asyncio
@patch("src.quiz.orchestrator.core._handle_orchestration_failure")
async def test_safe_background_orchestration_general_exception_handling(
    mock_handle_failure, caplog
):
    """Test general exceptions are properly handled."""
    from src.quiz.orchestrator.core import safe_background_orchestration

    # Arrange
    mock_operation = AsyncMock()
    test_error = ValueError("Test error message")
    mock_operation.side_effect = test_error

    quiz_id = uuid.uuid4()
    operation_name = "test_operation"

    # Act
    await safe_background_orchestration(mock_operation, operation_name, quiz_id)

    # Assert
    mock_handle_failure.assert_called_once()
    call_args = mock_handle_failure.call_args[0]
    assert call_args[0] == quiz_id
    assert call_args[1] == operation_name
    assert call_args[2] == test_error

    # Verify error logging
    assert "background_orchestration_error" in caplog.text
    assert "ValueError" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_safe_background_orchestration_correlation_id_generation(caplog):
    """Test that correlation IDs are generated and logged consistently."""
    from src.quiz.orchestrator.core import safe_background_orchestration

    # Arrange
    mock_operation = AsyncMock()
    quiz_id = uuid.uuid4()

    # Act
    await safe_background_orchestration(mock_operation, "test_op", quiz_id)

    # Assert - correlation_id should appear in both start and complete logs
    assert "correlation_id" in caplog.text

    # Verify UUID format in logs (basic check)
    import re

    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    assert re.search(uuid_pattern, caplog.text, re.IGNORECASE)


@pytest.mark.asyncio
@patch("src.quiz.orchestrator.core.execute_in_transaction")
async def test_handle_orchestration_failure_successful_status_update(
    mock_execute_transaction, caplog
):
    """Test successful update of quiz status to failed."""
    from src.quiz.orchestrator.core import _handle_orchestration_failure

    # Arrange
    quiz_id = uuid.uuid4()
    operation_name = "content_extraction"
    test_error = ValueError("Test error")
    correlation_id = str(uuid.uuid4())

    # Mock the transaction execution to succeed
    mock_execute_transaction.return_value = None

    # Act
    await _handle_orchestration_failure(
        quiz_id, operation_name, test_error, correlation_id
    )

    # Assert
    mock_execute_transaction.assert_called_once()
    assert "orchestration_failure_status_update_initiated" in caplog.text
    assert "orchestration_failure_status_updated" in caplog.text
    assert str(quiz_id) in caplog.text
    assert correlation_id in caplog.text


@pytest.mark.asyncio
@patch("src.quiz.orchestrator.core.execute_in_transaction")
async def test_handle_orchestration_failure_failed_status_update_logging(
    mock_execute_transaction, caplog
):
    """Test logging when status update fails."""
    from src.quiz.orchestrator.core import _handle_orchestration_failure

    # Arrange
    quiz_id = uuid.uuid4()
    operation_name = "question_generation"
    test_error = ValueError("Original error")
    correlation_id = str(uuid.uuid4())

    # Mock transaction failure
    update_error = RuntimeError("Database connection failed")
    mock_execute_transaction.side_effect = update_error

    # Act
    await _handle_orchestration_failure(
        quiz_id, operation_name, test_error, correlation_id
    )

    # Assert
    assert "orchestration_failure_status_update_failed" in caplog.text
    assert "Database connection failed" in caplog.text
    assert "Original error" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
@patch("src.quiz.orchestrator.core.execute_in_transaction")
async def test_rollback_quiz_to_status_successful_rollback(
    mock_execute_transaction, caplog
):
    """Test successful rollback of quiz to target status."""
    from src.quiz.orchestrator.core import rollback_quiz_to_status
    from src.quiz.schemas import QuizStatus

    # Arrange
    quiz_id = uuid.uuid4()
    target_status = QuizStatus.CREATED
    test_error = ValueError("Test error")
    operation_context = "auto_trigger"
    correlation_id = str(uuid.uuid4())

    # Mock successful transaction
    mock_execute_transaction.return_value = None

    # Act
    await rollback_quiz_to_status(
        quiz_id, target_status, test_error, operation_context, correlation_id
    )

    # Assert
    mock_execute_transaction.assert_called_once()
    assert "quiz_rollback_initiated" in caplog.text
    assert "quiz_rollback_completed" in caplog.text
    assert target_status.value in caplog.text
    assert str(quiz_id) in caplog.text
    assert correlation_id in caplog.text


@pytest.mark.asyncio
@patch("src.quiz.orchestrator.core.execute_in_transaction")
async def test_rollback_quiz_to_status_failure_logging(
    mock_execute_transaction, caplog
):
    """Test logging when rollback operation fails."""
    from src.quiz.orchestrator.core import rollback_quiz_to_status
    from src.quiz.schemas import QuizStatus

    # Arrange
    quiz_id = uuid.uuid4()
    target_status = QuizStatus.READY_FOR_REVIEW
    original_error = ValueError("Original error")

    # Mock rollback failure
    rollback_error = RuntimeError("Rollback failed")
    mock_execute_transaction.side_effect = rollback_error

    # Act
    await rollback_quiz_to_status(quiz_id, target_status, original_error)

    # Assert
    assert "quiz_rollback_failed" in caplog.text
    assert "Rollback failed" in caplog.text
    assert "Original error" in caplog.text
    assert str(quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_rollback_quiz_to_status_correlation_id_auto_generation(caplog):
    """Test automatic correlation ID generation when not provided."""
    from src.quiz.orchestrator.core import rollback_quiz_to_status
    from src.quiz.schemas import QuizStatus

    # Arrange
    quiz_id = uuid.uuid4()
    target_status = QuizStatus.CREATED
    test_error = ValueError("Test error")

    # Mock to prevent actual database operations
    with patch("src.quiz.orchestrator.core.execute_in_transaction"):
        # Act
        await rollback_quiz_to_status(quiz_id, target_status, test_error)

    # Assert - should generate and use correlation ID
    assert "correlation_id" in caplog.text

    # Verify UUID format in logs (basic check)
    import re

    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    assert re.search(uuid_pattern, caplog.text, re.IGNORECASE)


@pytest.mark.asyncio
async def test_timeout_operation_successful_within_timeout():
    """Test operation completes successfully within timeout."""
    from src.quiz.orchestrator.core import timeout_operation

    # Arrange
    @timeout_operation(timeout_seconds=5)
    async def test_operation(result_value):
        await asyncio.sleep(0.1)  # Short delay
        return result_value

    expected_result = "success"

    # Act
    result = await test_operation(expected_result)

    # Assert
    assert result == expected_result


@pytest.mark.asyncio
async def test_timeout_operation_raises_orchestration_error(caplog):
    """Test operation timeout raises OrchestrationTimeoutError."""
    from src.quiz.exceptions import OrchestrationTimeoutError
    from src.quiz.orchestrator.core import timeout_operation

    # Arrange
    @timeout_operation(timeout_seconds=1)
    async def slow_operation():
        await asyncio.sleep(2)  # Longer than timeout
        return "should_not_reach"

    # Act & Assert
    with pytest.raises(OrchestrationTimeoutError) as exc_info:
        await slow_operation()

    error = exc_info.value
    assert error.operation == "slow_operation"
    assert error.timeout_seconds == 1
    assert "orchestration_operation_timeout" in caplog.text


@pytest.mark.asyncio
async def test_timeout_operation_with_quiz_id_in_args(caplog):
    """Test timeout error includes quiz_id when available in args."""
    from src.quiz.exceptions import OrchestrationTimeoutError
    from src.quiz.orchestrator.core import timeout_operation

    # Arrange
    test_quiz_id = uuid.uuid4()

    @timeout_operation(timeout_seconds=1)
    async def operation_with_quiz_id(quiz_id):
        await asyncio.sleep(2)
        return "timeout"

    # Act & Assert
    with pytest.raises(OrchestrationTimeoutError) as exc_info:
        await operation_with_quiz_id(test_quiz_id)

    error = exc_info.value
    assert error.quiz_id == str(test_quiz_id)
    assert str(test_quiz_id) in caplog.text


@pytest.mark.asyncio
async def test_timeout_operation_preserves_function_metadata():
    """Test decorator preserves original function metadata."""
    from src.quiz.orchestrator.core import timeout_operation

    # Arrange
    @timeout_operation(timeout_seconds=5)
    async def documented_function():
        """Test function with documentation."""
        return "result"

    # Assert
    assert documented_function.__name__ == "documented_function"
    assert documented_function.__doc__ is not None
    assert "Test function with documentation" in documented_function.__doc__


@pytest.mark.asyncio
async def test_timeout_operation_with_args_and_kwargs():
    """Test timeout decorator works with various argument patterns."""
    from src.quiz.orchestrator.core import timeout_operation

    # Arrange
    @timeout_operation(timeout_seconds=5)
    async def complex_operation(arg1, arg2, kwarg1=None, kwarg2=None):
        await asyncio.sleep(0.1)
        return f"{arg1}-{arg2}-{kwarg1}-{kwarg2}"

    # Act
    result = await complex_operation("a", "b", kwarg1="c", kwarg2="d")

    # Assert
    assert result == "a-b-c-d"


@pytest.mark.asyncio
async def test_timeout_operation_nested_operations():
    """Test nested timeout operations work correctly."""
    from src.quiz.orchestrator.core import timeout_operation

    # Arrange
    @timeout_operation(timeout_seconds=3)
    async def inner_operation():
        await asyncio.sleep(0.1)
        return "inner"

    @timeout_operation(timeout_seconds=5)
    async def outer_operation():
        result = await inner_operation()
        return f"outer-{result}"

    # Act
    result = await outer_operation()

    # Assert
    assert result == "outer-inner"


def test_type_aliases_exist():
    """Test that type aliases are defined for dependency injection."""
    from src.quiz.orchestrator.core import (
        ContentExtractorFunc,
        ContentSummaryFunc,
        QuestionExporterFunc,
        QuizCreatorFunc,
    )

    # These should be defined and importable
    assert ContentExtractorFunc is not None
    assert ContentSummaryFunc is not None
    assert QuizCreatorFunc is not None
    assert QuestionExporterFunc is not None


@pytest.mark.asyncio
async def test_concurrent_background_orchestrations(caplog):
    """Test multiple concurrent background orchestrations."""
    from src.quiz.orchestrator.core import safe_background_orchestration

    # Arrange
    async def mock_operation(operation_id: str):
        await asyncio.sleep(0.1)
        return f"result-{operation_id}"

    quiz_ids = [uuid.uuid4() for _ in range(3)]
    operations = [
        safe_background_orchestration(
            mock_operation, f"test_op_{i}", quiz_id, f"op_{i}"
        )
        for i, quiz_id in enumerate(quiz_ids)
    ]

    # Act
    await asyncio.gather(*operations)

    # Assert - all operations should have logged completion
    completed_logs = [
        record
        for record in caplog.records
        if "background_orchestration_completed" in record.message
    ]
    assert len(completed_logs) == 3


@pytest.mark.asyncio
async def test_concurrent_rollback_operations():
    """Test concurrent rollback operations don't interfere."""
    from src.quiz.orchestrator.core import rollback_quiz_to_status
    from src.quiz.schemas import QuizStatus

    # Arrange
    quiz_ids = [uuid.uuid4() for _ in range(3)]
    errors = [ValueError(f"Error {i}") for i in range(3)]

    with patch("src.quiz.orchestrator.core.execute_in_transaction") as mock_tx:
        mock_tx.return_value = None

        rollbacks = [
            rollback_quiz_to_status(
                quiz_id, QuizStatus.CREATED, error, f"test_context_{i}"
            )
            for i, (quiz_id, error) in enumerate(zip(quiz_ids, errors))
        ]

        # Act
        await asyncio.gather(*rollbacks)

    # Assert - all rollbacks should have been attempted
    assert mock_tx.call_count == 3
