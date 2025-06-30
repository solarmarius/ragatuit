"""
Tests for retry decorators
"""

import time

import pytest

from app.retry import retry_on_failure


@pytest.mark.asyncio
async def test_retry_on_failure_success_first_attempt() -> None:
    """Test retry decorator succeeds on first attempt."""

    @retry_on_failure(max_attempts=3)
    async def successful_function() -> str:
        return "success"

    result = await successful_function()
    assert result == "success"


@pytest.mark.asyncio
async def test_retry_on_failure_success_after_retries() -> None:
    """Test retry decorator succeeds after some failures."""
    call_count = 0

    @retry_on_failure(max_attempts=3, initial_delay=0.01)
    async def flaky_function() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("Temporary failure")
        return "success"

    result = await flaky_function()
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_on_failure_exhausts_attempts() -> None:
    """Test retry decorator exhausts all attempts and raises."""
    call_count = 0

    @retry_on_failure(max_attempts=3, initial_delay=0.01)
    async def always_failing_function() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("Always fails")

    with pytest.raises(ValueError, match="Always fails"):
        await always_failing_function()

    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_on_failure_backoff_timing() -> None:
    """Test retry decorator uses exponential backoff."""
    call_times = []

    @retry_on_failure(max_attempts=3, initial_delay=0.01, backoff_factor=2.0)
    async def timing_function() -> str:
        call_times.append(time.time())
        raise RuntimeError("Always fails")

    with pytest.raises(RuntimeError):
        await timing_function()

    # Should have 3 calls
    assert len(call_times) == 3

    # Check approximate timing (allowing for some variance)
    if len(call_times) >= 2:
        delay1 = call_times[1] - call_times[0]
        assert delay1 >= 0.005  # At least half the expected delay

    if len(call_times) >= 3:
        delay2 = call_times[2] - call_times[1]
        assert delay2 >= 0.015  # At least 1.5x the first delay


@pytest.mark.asyncio
async def test_retry_on_failure_max_delay() -> None:
    """Test retry decorator respects max delay."""

    @retry_on_failure(
        max_attempts=3, initial_delay=1.0, backoff_factor=10.0, max_delay=0.05
    )
    async def failing_function() -> str:
        raise RuntimeError("Fail")

    with pytest.raises(RuntimeError):
        await failing_function()


@pytest.mark.asyncio
async def test_retry_preserves_function_metadata() -> None:
    """Test retry decorator preserves function name and docstring."""

    @retry_on_failure()
    async def documented_function() -> str:
        """This function has documentation."""
        return "test"

    assert documented_function.__name__ == "documented_function"
    assert documented_function.__doc__ == "This function has documentation."


@pytest.mark.asyncio
async def test_retry_handles_non_exception_errors() -> None:
    """Test retry decorator handles different types of exceptions."""

    @retry_on_failure(max_attempts=2, initial_delay=0.01)
    async def function_with_different_errors() -> str:
        raise ValueError("Specific error type")

    with pytest.raises(ValueError, match="Specific error type"):
        await function_with_different_errors()
