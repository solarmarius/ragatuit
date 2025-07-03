"""Domain exceptions for content extraction."""


class ContentExtractionError(Exception):
    """Base content extraction exception."""

    def __init__(self, message: str, content_type: str | None = None):
        super().__init__(message)
        self.content_type = content_type


class UnsupportedFormatError(ContentExtractionError):
    """Content format not supported for processing."""

    def __init__(self, content_type: str):
        super().__init__(
            f"Content type '{content_type}' is not supported", content_type
        )


class ContentTooLargeError(ContentExtractionError):
    """Content exceeds size limits."""

    def __init__(
        self, content_size: int, max_size: int, content_type: str | None = None
    ):
        message = f"Content size {content_size} exceeds maximum {max_size}"
        super().__init__(message, content_type)
        self.content_size = content_size
        self.max_size = max_size


class ProcessingFailedError(ContentExtractionError):
    """Content processing failed due to technical error."""

    def __init__(
        self,
        message: str,
        content_type: str | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(message, content_type)
        self.original_error = original_error


class ValidationError(ContentExtractionError):
    """Content failed validation rules."""

    def __init__(self, message: str, content_type: str | None = None):
        super().__init__(message, content_type)
