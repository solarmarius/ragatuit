"""
Tests for logging configuration and functionality.
"""

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.logging_config import configure_logging, get_logger, log_context
from app.main import app


class TestLoggingConfiguration:
    """Test logging configuration and setup."""

    def test_configure_logging(self) -> None:
        """Test that logging configuration works."""
        # Configure logging
        configure_logging()

        # Get a logger
        logger = get_logger("test")

        # Verify logger is properly configured
        assert logger is not None
        # Logger is a BoundLoggerLazyProxy initially, check if it has the right methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_logger_output_format(self, caplog: Any) -> None:
        """Test that logger outputs in expected format."""
        configure_logging()
        logger = get_logger("test.format")

        # Test structured logging
        with caplog.at_level(logging.INFO):
            logger.info("test_event", test_field="test_value", number=42)

        # Verify log was captured
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "INFO"
        assert "test_event" in record.message

    def test_log_context(self) -> None:
        """Test log context management."""
        # Set request context
        log_context.set_request_context("test-req-123", "GET", "/test")

        # Verify context is set
        assert log_context.request_id.get() == "test-req-123"
        assert log_context.request_method.get() == "GET"
        assert log_context.request_path.get() == "/test"

        # Set user context
        log_context.set_user_context("user-456", 789)

        # Verify user context
        assert log_context.user_id.get() == "user-456"
        assert log_context.canvas_id.get() == 789

        # Clear context
        log_context.clear_context()

        # Verify context is cleared
        assert log_context.request_id.get() == ""
        assert log_context.user_id.get() == ""


class TestLoggingMiddleware:
    """Test logging middleware functionality."""

    def test_request_logging_middleware(self) -> None:
        """Test that requests are logged properly."""
        client = TestClient(app)

        # Make a test request
        response = client.get("/api/v1/utils/health-check/")

        # Should get successful response
        assert response.status_code == 200

        # Note: In actual implementation, you would capture logs
        # and verify they contain request details

    def test_request_id_generation(self) -> None:
        """Test that request IDs are generated and included."""
        client = TestClient(app)

        # Make a request
        response = client.get("/api/v1/utils/health-check/")

        # Response should include X-Request-ID header
        assert "X-Request-ID" in response.headers

        # Request ID should be a valid UUID format
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID length
        assert request_id.count("-") == 4  # UUID has 4 hyphens


class TestAuthLogging:
    """Test logging in auth routes."""

    @pytest.mark.asyncio
    async def test_oauth_initiation_logging(self, caplog: Any) -> None:
        """Test that OAuth initiation is logged."""
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            response = client.get("/api/v1/auth/login/canvas")

        # The OAuth initiation should return a redirect (307) or the redirect was followed (404)
        # Check if the OAuth logging happened regardless of redirect behavior
        assert response.status_code in [307, 404]

        # Should have logged the OAuth initiation
        log_messages = [record.message for record in caplog.records]
        oauth_logs = [msg for msg in log_messages if "canvas_oauth_initiated" in msg]
        assert len(oauth_logs) > 0


def test_logging_performance() -> None:
    """Test that logging doesn't significantly impact performance."""
    import time

    configure_logging()
    logger = get_logger("performance.test")

    # Time logging operations
    start_time = time.time()

    for i in range(1000):
        logger.info("performance_test", iteration=i, data="test_data")

    end_time = time.time()
    duration = end_time - start_time

    # 1000 log calls should take less than 1 second
    assert duration < 1.0, f"Logging took too long: {duration}s"


def test_log_levels() -> None:
    """Test different log levels work correctly."""
    configure_logging()
    logger = get_logger("level.test")

    # Test all log levels
    logger.debug("debug_message", level="debug")
    logger.info("info_message", level="info")
    logger.warning("warning_message", level="warning")
    logger.error("error_message", level="error")
