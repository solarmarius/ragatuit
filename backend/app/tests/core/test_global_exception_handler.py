"""
Tests for global exception handlers.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)
from app.core.global_exception_handler import (
    general_exception_handler,
    service_error_handler,
)


def create_mock_request(path: str = "/test", method: str = "GET") -> Request:
    """Create a mock Request object for testing."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = path
    mock_request.method = method
    return mock_request


@pytest.mark.asyncio
async def test_service_error_handler_basic() -> None:
    """Test service error handler with basic ServiceError."""
    request = create_mock_request("/api/test", "POST")
    error = ServiceError("Test error message", 500)

    response = await service_error_handler(request, error)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    assert response.body == b'{"error":"Test error message"}'


@pytest.mark.asyncio
async def test_service_error_handler_with_custom_status() -> None:
    """Test service error handler with custom status code."""
    request = create_mock_request()
    error = ServiceError("Custom error", 422)

    response = await service_error_handler(request, error)

    assert response.status_code == 422
    assert response.body == b'{"error":"Custom error"}'


@pytest.mark.asyncio
async def test_service_error_handler_with_validation_error() -> None:
    """Test service error handler with ValidationError."""
    request = create_mock_request()
    error = ValidationError("Invalid input data")

    response = await service_error_handler(request, error)

    assert response.status_code == 400
    expected_message = "Validation error: Invalid input data"
    assert expected_message.encode() in response.body


@pytest.mark.asyncio
async def test_service_error_handler_with_authentication_error() -> None:
    """Test service error handler with AuthenticationError."""
    request = create_mock_request()
    error = AuthenticationError("Token expired")

    response = await service_error_handler(request, error)

    assert response.status_code == 401
    expected_message = "Authentication error: Token expired"
    assert expected_message.encode() in response.body


@pytest.mark.asyncio
async def test_service_error_handler_with_resource_not_found_error() -> None:
    """Test service error handler with ResourceNotFoundError."""
    request = create_mock_request()
    error = ResourceNotFoundError("User with ID 123")

    response = await service_error_handler(request, error)

    assert response.status_code == 404
    expected_message = "User with ID 123 not found"
    assert expected_message.encode() in response.body


@pytest.mark.asyncio
async def test_service_error_handler_with_external_service_error() -> None:
    """Test service error handler with ExternalServiceError."""
    request = create_mock_request()
    error = ExternalServiceError("canvas", "Connection timeout", 503)

    response = await service_error_handler(request, error)

    assert response.status_code == 503
    expected_message = "canvas service error: Connection timeout"
    assert expected_message.encode() in response.body


@pytest.mark.asyncio
async def test_service_error_handler_with_external_service_custom_status() -> None:
    """Test service error handler with ExternalServiceError custom status."""
    request = create_mock_request()
    error = ExternalServiceError("openai", "Rate limited", 429)

    response = await service_error_handler(request, error)

    assert response.status_code == 429
    expected_message = "openai service error: Rate limited"
    assert expected_message.encode() in response.body


@pytest.mark.asyncio
async def test_general_exception_handler_with_value_error() -> None:
    """Test general exception handler with ValueError."""
    request = create_mock_request("/api/test", "POST")
    error = ValueError("Something went wrong")

    response = await general_exception_handler(request, error)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    assert response.body == b'{"error":"Internal server error"}'


@pytest.mark.asyncio
async def test_general_exception_handler_with_runtime_error() -> None:
    """Test general exception handler with RuntimeError."""
    request = create_mock_request()
    error = RuntimeError("System failure")

    response = await general_exception_handler(request, error)

    assert response.status_code == 500
    assert response.body == b'{"error":"Internal server error"}'


@pytest.mark.asyncio
async def test_general_exception_handler_with_key_error() -> None:
    """Test general exception handler with KeyError."""
    request = create_mock_request()
    error = KeyError("missing_key")

    response = await general_exception_handler(request, error)

    assert response.status_code == 500
    assert response.body == b'{"error":"Internal server error"}'


@pytest.mark.asyncio
async def test_general_exception_handler_with_custom_exception() -> None:
    """Test general exception handler with custom exception."""
    request = create_mock_request()

    class CustomException(Exception):
        pass

    error = CustomException("Custom error")

    response = await general_exception_handler(request, error)

    assert response.status_code == 500
    assert response.body == b'{"error":"Internal server error"}'


@pytest.mark.asyncio
async def test_error_handlers_preserve_request_info() -> None:
    """Test error handlers can access request information."""
    # Test with different request paths and methods
    test_cases = [
        ("/api/users", "GET"),
        ("/api/quizzes/123", "PUT"),
        ("/api/auth/login", "POST"),
        ("/api/canvas/courses", "DELETE"),
    ]

    for path, method in test_cases:
        request = create_mock_request(path, method)
        error = ServiceError("Test error")

        response = await service_error_handler(request, error)

        # Should still work regardless of request details
        assert response.status_code == 500
        assert response.body == b'{"error":"Test error"}'


@pytest.mark.asyncio
async def test_service_error_handler_response_format() -> None:
    """Test service error handler response format is correct JSON."""
    request = create_mock_request()
    error = ServiceError("Test message")

    response = await service_error_handler(request, error)

    # Check content type header (if set)
    assert response.status_code == 500

    # Response body should be valid JSON
    import json

    body_bytes = response.body
    if isinstance(body_bytes, memoryview):
        body_bytes = body_bytes.tobytes()
    body_text = body_bytes.decode()
    parsed = json.loads(body_text)

    assert "error" in parsed
    assert parsed["error"] == "Test message"


@pytest.mark.asyncio
async def test_general_exception_handler_response_format() -> None:
    """Test general exception handler response format is correct JSON."""
    request = create_mock_request()
    error = Exception("Test exception")

    response = await general_exception_handler(request, error)

    # Check response format
    assert response.status_code == 500

    # Response body should be valid JSON
    import json

    body_bytes = response.body
    if isinstance(body_bytes, memoryview):
        body_bytes = body_bytes.tobytes()
    body_text = body_bytes.decode()
    parsed = json.loads(body_text)

    assert "error" in parsed
    assert parsed["error"] == "Internal server error"


@pytest.mark.asyncio
async def test_error_handlers_with_empty_message() -> None:
    """Test error handlers handle empty error messages."""
    request = create_mock_request()

    # Test with empty message
    error = ServiceError("")
    response = await service_error_handler(request, error)

    assert response.status_code == 500
    assert response.body == b'{"error":""}'


@pytest.mark.asyncio
async def test_error_handlers_with_special_characters() -> None:
    """Test error handlers handle special characters in messages."""
    request = create_mock_request()

    # Test with special characters
    error = ServiceError('Error with "quotes" and \\ backslashes')
    response = await service_error_handler(request, error)

    assert response.status_code == 500
    # Should still be valid JSON
    import json

    body_bytes = response.body
    if isinstance(body_bytes, memoryview):
        body_bytes = body_bytes.tobytes()
    body_text = body_bytes.decode()
    parsed = json.loads(body_text)
    assert "quotes" in parsed["error"]
    assert "backslashes" in parsed["error"]


@pytest.mark.asyncio
async def test_error_handlers_with_unicode() -> None:
    """Test error handlers handle unicode characters."""
    request = create_mock_request()

    # Test with unicode characters
    error = ServiceError("Error with émojis 🚀 and unicode ñ")
    response = await service_error_handler(request, error)

    assert response.status_code == 500
    # Should handle unicode properly
    import json

    body_bytes = response.body
    if isinstance(body_bytes, memoryview):
        body_bytes = body_bytes.tobytes()
    body_text = body_bytes.decode()
    parsed = json.loads(body_text)
    assert "émojis" in parsed["error"]
    assert "🚀" in parsed["error"]
