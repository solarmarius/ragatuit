"""
Simple retry decorators and utilities for handling transient failures.
"""

import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from src.logging_config import get_logger

logger = get_logger("retry")

T = TypeVar("T")


def retry_on_failure(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator for adding retry logic to functions.

    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_factor: Exponential backoff multiplier
        max_delay: Maximum delay between retries (seconds)
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Don't retry on the last attempt
                    if attempt == max_attempts - 1:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=max_attempts,
                            error=str(e),
                        )
                        raise e

                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (backoff_factor**attempt), max_delay)

                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e),
                    )

                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError("No exception to re-raise")

        return wrapper

    return decorator
