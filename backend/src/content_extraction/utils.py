"""Text processing utilities for content extraction."""

import io
import re
from typing import Any

import pypdf
from bs4 import BeautifulSoup, Comment

from .config import settings
from .constants import CANVAS_UI_SELECTORS, HTML_ELEMENTS_TO_REMOVE


def clean_html_content(html_content: str) -> str:
    """
    Clean HTML content and extract readable text.

    Removes:
    - HTML tags and attributes
    - Scripts and styles
    - Comments
    - Navigation elements
    - Canvas-specific UI elements
    - Excessive whitespace

    Returns clean text suitable for LLM processing.

    Args:
        html_content: Raw HTML content to clean

    Returns:
        Cleaned text content
    """
    if not html_content:
        return ""

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for element in soup(HTML_ELEMENTS_TO_REMOVE):
        element.decompose()

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove Canvas-specific elements
    for selector in CANVAS_UI_SELECTORS:
        for element in soup.select(selector):
            element.decompose()

    # Get text content
    text = soup.get_text()

    # Clean up whitespace and formatting
    text = normalize_text(text)

    return text


def normalize_text(text: str) -> str:
    """
    Normalize text by cleaning whitespace and formatting.

    Args:
        text: Raw text to normalize

    Returns:
        Normalized text with cleaned formatting
    """
    if not text:
        return ""

    # Limit text size to prevent ReDoS attacks
    if len(text) > settings.MAX_CONTENT_LENGTH:
        text = text[: settings.MAX_CONTENT_LENGTH]

    # Replace multiple whitespace characters with single spaces (safe regex)
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    # Remove empty lines and excessive line breaks
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text = "\n".join(lines)

    # Ensure sentences are properly separated (safer regex with word boundary)
    text = re.sub(r"\.([A-Z]\w)", r". \1", text)

    # Remove excessive punctuation (limited quantifiers to prevent ReDoS)
    text = re.sub(r"\.{3,10}", "...", text)  # Limit to 10 dots max
    text = re.sub(r"!{2,5}", "!", text)  # Limit to 5 exclamations max
    text = re.sub(r"\?{2,5}", "?", text)  # Limit to 5 questions max

    return text


def extract_pdf_text(pdf_content: bytes) -> str:
    """
    Extract text from PDF bytes using pypdf.

    Args:
        pdf_content: PDF file content as bytes

    Returns:
        Extracted text content or empty string if extraction fails
    """
    if not pdf_content:
        return ""

    pdf_buffer = None
    try:
        # Create PDF reader from bytes
        pdf_buffer = io.BytesIO(pdf_content)
        reader = pypdf.PdfReader(pdf_buffer)
        text_parts = []

        for _page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception:
                # Continue with other pages if one fails
                continue

        # Join all page texts with newlines
        full_text = "\n\n".join(text_parts)

        # Clean up excessive whitespace
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)
        full_text = re.sub(r" {2,}", " ", full_text)

        return full_text.strip()

    except Exception:
        return ""
    finally:
        # Always clean up the buffer to free memory
        if pdf_buffer:
            pdf_buffer.close()


def estimate_word_count(text: str) -> int:
    """
    Estimate word count in text using simple split method.

    Args:
        text: Text to count words in

    Returns:
        Estimated number of words
    """
    if not text:
        return 0
    return len(text.split())


def truncate_content(
    content: str, max_length: int, suffix: str = "... [truncated]"
) -> str:
    """
    Truncate content to maximum length with suffix.

    Args:
        content: Content to truncate
        max_length: Maximum allowed length
        suffix: Suffix to add when truncating

    Returns:
        Truncated content with suffix if needed
    """
    if len(content) <= max_length:
        return content

    truncate_at = max_length - len(suffix)
    return content[:truncate_at] + suffix


def validate_text_content(text: str) -> bool:
    """
    Validate that text content meets basic requirements.

    Args:
        text: Text to validate

    Returns:
        True if text is valid, False otherwise
    """
    if not text or not text.strip():
        return False

    text_length = len(text.strip())
    return settings.MIN_CONTENT_LENGTH <= text_length <= settings.MAX_CONTENT_LENGTH


def create_processing_metadata(
    original_type: str, original_size: int, processed_size: int, **kwargs: Any
) -> dict[str, Any]:
    """
    Create metadata dict for processed content.

    Args:
        original_type: Original content type
        original_size: Size before processing
        processed_size: Size after processing
        **kwargs: Additional metadata fields

    Returns:
        Metadata dictionary
    """
    metadata = {
        "original_type": original_type,
        "original_size": original_size,
        "processed_size": processed_size,
        "compression_ratio": processed_size / original_size if original_size > 0 else 0,
    }
    metadata.update(kwargs)
    return metadata
