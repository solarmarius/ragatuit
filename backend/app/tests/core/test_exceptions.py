"""
Tests for custom exception hierarchy.
"""

import pytest

from app.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)


def test_service_error_default_status_code() -> None:
    """Test ServiceError with default status code."""
    error = ServiceError("Test error")
    assert error.message == "Test error"
    assert error.status_code == 500
    assert str(error) == "Test error"


def test_service_error_custom_status_code() -> None:
    """Test ServiceError with custom status code."""
    error = ServiceError("Custom error", 400)
    assert error.message == "Custom error"
    assert error.status_code == 400
    assert str(error) == "Custom error"


def test_service_error_inheritance() -> None:
    """Test ServiceError inherits from Exception."""
    error = ServiceError("Test error")
    assert isinstance(error, Exception)
    assert isinstance(error, ServiceError)


def test_external_service_error_default_status_code() -> None:
    """Test ExternalServiceError with default status code."""
    error = ExternalServiceError("canvas", "API timeout")
    assert error.service == "canvas"
    assert error.status_code == 503
    assert "canvas service error: API timeout" in str(error)


def test_external_service_error_custom_status_code() -> None:
    """Test ExternalServiceError with custom status code."""
    error = ExternalServiceError("openai", "Rate limited", 429)
    assert error.service == "openai"
    assert error.status_code == 429
    assert "openai service error: Rate limited" in str(error)


def test_external_service_error_inheritance() -> None:
    """Test ExternalServiceError inherits from ServiceError."""
    error = ExternalServiceError("canvas", "Test error")
    assert isinstance(error, ServiceError)
    assert isinstance(error, ExternalServiceError)


def test_external_service_error_message_format() -> None:
    """Test ExternalServiceError message formatting."""
    error = ExternalServiceError("test-service", "Connection failed")
    expected_message = "test-service service error: Connection failed"
    assert error.message == expected_message
    assert str(error) == expected_message


def test_validation_error_status_code() -> None:
    """Test ValidationError has correct status code."""
    error = ValidationError("Invalid input")
    assert error.status_code == 400
    assert "Validation error: Invalid input" in str(error)


def test_validation_error_inheritance() -> None:
    """Test ValidationError inherits from ServiceError."""
    error = ValidationError("Test error")
    assert isinstance(error, ServiceError)
    assert isinstance(error, ValidationError)


def test_validation_error_message_format() -> None:
    """Test ValidationError message formatting."""
    error = ValidationError("Email format is invalid")
    expected_message = "Validation error: Email format is invalid"
    assert error.message == expected_message
    assert str(error) == expected_message


def test_authentication_error_status_code() -> None:
    """Test AuthenticationError has correct status code."""
    error = AuthenticationError("Invalid token")
    assert error.status_code == 401
    assert "Authentication error: Invalid token" in str(error)


def test_authentication_error_inheritance() -> None:
    """Test AuthenticationError inherits from ServiceError."""
    error = AuthenticationError("Test error")
    assert isinstance(error, ServiceError)
    assert isinstance(error, AuthenticationError)


def test_authentication_error_message_format() -> None:
    """Test AuthenticationError message formatting."""
    error = AuthenticationError("Token expired")
    expected_message = "Authentication error: Token expired"
    assert error.message == expected_message
    assert str(error) == expected_message


def test_resource_not_found_error_status_code() -> None:
    """Test ResourceNotFoundError has correct status code."""
    error = ResourceNotFoundError("User")
    assert error.status_code == 404
    assert "User not found" in str(error)


def test_resource_not_found_error_inheritance() -> None:
    """Test ResourceNotFoundError inherits from ServiceError."""
    error = ResourceNotFoundError("Quiz")
    assert isinstance(error, ServiceError)
    assert isinstance(error, ResourceNotFoundError)


def test_resource_not_found_error_message_format() -> None:
    """Test ResourceNotFoundError message formatting."""
    error = ResourceNotFoundError("Quiz with ID 123")
    expected_message = "Quiz with ID 123 not found"
    assert error.message == expected_message
    assert str(error) == expected_message


def test_resource_not_found_error_with_uuid() -> None:
    """Test ResourceNotFoundError with UUID resource."""
    uuid_str = "123e4567-e89b-12d3-a456-426614174000"
    error = ResourceNotFoundError(f"Quiz {uuid_str}")
    assert "Quiz 123e4567-e89b-12d3-a456-426614174000 not found" in str(error)


def test_all_custom_exceptions_inherit_from_service_error() -> None:
    """Test all custom exceptions inherit from ServiceError."""
    exceptions = [
        ExternalServiceError("test", "message"),
        ValidationError("message"),
        AuthenticationError("message"),
        ResourceNotFoundError("resource"),
    ]

    for exc in exceptions:
        assert isinstance(exc, ServiceError)
        assert isinstance(exc, Exception)


def test_exception_status_codes_are_correct() -> None:
    """Test all exceptions have correct HTTP status codes."""
    test_cases = [
        (ServiceError("test"), 500),
        (ExternalServiceError("service", "test"), 503),
        (ValidationError("test"), 400),
        (AuthenticationError("test"), 401),
        (ResourceNotFoundError("test"), 404),
    ]

    for exc, expected_code in test_cases:
        assert exc.status_code == expected_code


def test_exception_messages_are_accessible() -> None:
    """Test all exceptions have accessible message attribute."""
    exceptions = [
        ServiceError("service message"),
        ExternalServiceError("canvas", "external message"),
        ValidationError("validation message"),
        AuthenticationError("auth message"),
        ResourceNotFoundError("resource"),
    ]

    for exc in exceptions:
        assert hasattr(exc, "message")
        assert exc.message is not None
        assert len(exc.message) > 0


def test_exception_string_representation() -> None:
    """Test string representation of exceptions."""
    error = ServiceError("Test message")
    assert str(error) == "Test message"

    external_error = ExternalServiceError("canvas", "API error")
    assert "canvas service error: API error" in str(external_error)

    validation_error = ValidationError("Invalid data")
    assert "Validation error: Invalid data" in str(validation_error)


def test_exceptions_can_be_raised_and_caught() -> None:
    """Test exceptions can be properly raised and caught."""
    # Test ServiceError
    with pytest.raises(ServiceError) as exc_info:
        raise ServiceError("Test error")
    assert exc_info.value.message == "Test error"

    # Test ExternalServiceError
    with pytest.raises(ExternalServiceError) as exc_info:
        raise ExternalServiceError("canvas", "Connection failed")
    assert exc_info.value.service == "canvas"

    # Test ValidationError
    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError("Invalid input")
    assert exc_info.value.status_code == 400

    # Test AuthenticationError
    with pytest.raises(AuthenticationError) as exc_info:
        raise AuthenticationError("Unauthorized")
    assert exc_info.value.status_code == 401

    # Test ResourceNotFoundError
    with pytest.raises(ResourceNotFoundError) as exc_info:
        raise ResourceNotFoundError("User")
    assert exc_info.value.status_code == 404


def test_exceptions_can_be_caught_as_base_class() -> None:
    """Test custom exceptions can be caught as ServiceError."""
    exceptions_to_test = [
        ExternalServiceError("canvas", "error"),
        ValidationError("error"),
        AuthenticationError("error"),
        ResourceNotFoundError("error"),
    ]

    for exception in exceptions_to_test:
        with pytest.raises(ServiceError):
            raise exception
