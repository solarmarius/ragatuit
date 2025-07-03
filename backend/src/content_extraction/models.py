"""Data models for content extraction domain."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawContent:
    """
    Raw content from any source before processing.

    Represents unprocessed content that needs to be cleaned and normalized.
    Can come from HTML pages, PDF files, text files, or any other source.
    """

    content: str  # Raw content (HTML, PDF bytes as str, text)
    content_type: str  # "html", "pdf", "text"
    title: str  # Content title
    metadata: dict[str, Any] = field(default_factory=dict)  # Source-specific metadata


@dataclass
class ProcessedContent:
    """
    Cleaned, processed content ready for consumption.

    Represents content that has been cleaned, normalized, and validated.
    Ready to be used by LLMs, search systems, or other consumers.
    """

    title: str  # Content title
    content: str  # Cleaned text content
    word_count: int  # Estimated word count
    content_type: str  # Always "text" after processing
    processing_metadata: dict[str, Any] = field(
        default_factory=dict
    )  # Processing stats and info


@dataclass
class ProcessingSummary:
    """Summary statistics for a batch processing operation."""

    total_items: int  # Total items processed
    successful_items: int  # Successfully processed items
    failed_items: int  # Failed processing items
    total_word_count: int  # Total words across all content
    processing_time_seconds: float  # Time taken for processing
    content_types_processed: dict[str, int] = field(
        default_factory=dict
    )  # Count by content type
