"""Validation functions for content extraction."""

from collections.abc import Callable

from .constants import (
    CONTENT_TYPE_MAPPINGS,
    MAX_CONTENT_LENGTH,
    MAX_CONTENT_SIZE,
    MIN_CONTENT_LENGTH,
    SUPPORTED_CONTENT_TYPES,
    SUPPORTED_FORMATS,
)
from .models import RawContent


def is_valid_content_size(raw_content: RawContent) -> bool:
    """
    Check if raw content size is within limits.

    Args:
        raw_content: Content to validate

    Returns:
        True if content size is acceptable
    """
    return len(raw_content.content) <= MAX_CONTENT_SIZE


def is_valid_content_length(text: str) -> bool:
    """
    Check if processed text meets length requirements.

    Args:
        text: Processed text to validate

    Returns:
        True if text length is within acceptable range
    """
    text_length = len(text.strip())
    return MIN_CONTENT_LENGTH <= text_length <= MAX_CONTENT_LENGTH


def is_supported_content_type(content_type: str) -> bool:
    """
    Check if content type is supported for processing.

    Args:
        content_type: Content type to check

    Returns:
        True if content type is supported
    """
    # Normalize content type
    normalized_type = CONTENT_TYPE_MAPPINGS.get(
        content_type.lower(), content_type.lower()
    )
    return (
        content_type.lower() in SUPPORTED_CONTENT_TYPES
        or normalized_type in SUPPORTED_FORMATS
    )


def has_meaningful_content(raw_content: RawContent) -> bool:
    """
    Check if content has meaningful text (not just whitespace).

    Args:
        raw_content: Content to validate

    Returns:
        True if content has meaningful text
    """
    return bool(raw_content.content.strip())


def is_valid_title(title: str) -> bool:
    """
    Check if title is valid (not empty or just whitespace).

    Args:
        title: Title to validate

    Returns:
        True if title is valid
    """
    return bool(title and title.strip())


def create_content_validator() -> Callable[[RawContent], bool]:
    """
    Create a composite validator function that checks all validation rules.

    Returns:
        Function that validates RawContent and returns True if valid
    """

    def validate_content(raw_content: RawContent) -> bool:
        """
        Validate raw content against all rules.

        Args:
            raw_content: Content to validate

        Returns:
            True if content passes all validation rules
        """
        return (
            is_supported_content_type(raw_content.content_type)
            and is_valid_content_size(raw_content)
            and has_meaningful_content(raw_content)
            and is_valid_title(raw_content.title)
        )

    return validate_content


def create_text_validator() -> Callable[[str], bool]:
    """
    Create a validator for processed text content.

    Returns:
        Function that validates processed text and returns True if valid
    """

    def validate_text(text: str) -> bool:
        """
        Validate processed text content.

        Args:
            text: Processed text to validate

        Returns:
            True if text is valid
        """
        return bool(text and text.strip()) and is_valid_content_length(text)

    return validate_text
