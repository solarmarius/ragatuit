"""Configuration for content extraction domain."""

from pydantic_settings import BaseSettings


class ContentExtractionSettings(BaseSettings):
    """Content extraction processing configuration."""

    # Content size limits
    MAX_CONTENT_SIZE: int = 1024 * 1024  # 1MB per item
    MAX_TOTAL_CONTENT_SIZE: int = 50 * 1024 * 1024  # 50MB total
    MAX_CONTENT_LENGTH: int = 50000  # Max processed text length
    MIN_CONTENT_LENGTH: int = 50  # Min processed text length

    # File processing
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB per file
    SUPPORTED_FORMATS: list[str] = ["html", "pdf", "text"]

    # Processing timeouts
    PROCESSING_TIMEOUT: int = 30

    # Text processing
    MAX_WORDS_PER_CONTENT: int = 10000  # Max words in single content item
    MIN_WORDS_PER_CONTENT: int = 10  # Min words in single content item

    class Config:
        env_prefix = "CONTENT_EXTRACTION_"


# Global settings instance
settings = ContentExtractionSettings()
