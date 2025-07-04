"""Content type processors for different formats."""

from .constants import MAX_CONTENT_LENGTH
from .models import ProcessedContent, RawContent
from .utils import (
    clean_html_content,
    create_processing_metadata,
    estimate_word_count,
    extract_pdf_text,
    normalize_text,
    truncate_content,
    validate_text_content,
)


def process_html_content(raw_content: RawContent) -> ProcessedContent | None:
    """
    Process HTML content into clean text.

    Processing steps:
    1. Parse HTML with BeautifulSoup
    2. Remove scripts, styles, navigation elements
    3. Remove Canvas-specific UI elements
    4. Extract clean text
    5. Normalize whitespace and formatting
    6. Validate content length

    Args:
        raw_content: RawContent with content_type="html"

    Returns:
        ProcessedContent with cleaned text or None if processing fails
    """
    if not raw_content.content:
        return None

    try:
        # Clean HTML and extract text
        cleaned_text = clean_html_content(raw_content.content)

        # Normalize text formatting
        normalized_text = normalize_text(cleaned_text)

        # Validate result
        if not validate_text_content(normalized_text):
            return None

        # Truncate if necessary
        if len(normalized_text) > MAX_CONTENT_LENGTH:  # Use settings value
            normalized_text = truncate_content(normalized_text, MAX_CONTENT_LENGTH)

        # Create processing metadata
        metadata = create_processing_metadata(
            original_type="html",
            original_size=len(raw_content.content),
            processed_size=len(normalized_text),
            html_tags_removed=True,
            canvas_ui_removed=True,
        )

        return ProcessedContent(
            title=raw_content.title or "Untitled",
            content=normalized_text,
            word_count=estimate_word_count(normalized_text),
            content_type="text",
            processing_metadata=metadata,
        )

    except Exception:
        # Log error but don't raise - return None for graceful handling
        return None


def process_pdf_content(raw_content: RawContent) -> ProcessedContent | None:
    """
    Process PDF content into clean text.

    Processing steps:
    1. Create PDF reader from content bytes
    2. Extract text from all pages
    3. Combine page texts with proper spacing
    4. Clean excessive whitespace
    5. Normalize text formatting
    6. Validate content length

    Args:
        raw_content: RawContent with content_type="pdf"

    Returns:
        ProcessedContent with extracted text or None if extraction fails
    """
    if not raw_content.content:
        return None

    try:
        # Convert string content to bytes if needed
        if isinstance(raw_content.content, str):
            # Assume content is base64 encoded or handle accordingly
            pdf_bytes = raw_content.content.encode("latin-1")
        else:
            pdf_bytes = raw_content.content

        # Extract text from PDF
        extracted_text = extract_pdf_text(pdf_bytes)

        if not extracted_text:
            return None

        # Normalize text
        normalized_text = normalize_text(extracted_text)

        # Validate result
        if not validate_text_content(normalized_text):
            return None

        # Truncate if necessary
        if len(normalized_text) > 50000:  # Use settings value
            normalized_text = truncate_content(normalized_text, 50000)

        # Create processing metadata
        page_count = raw_content.metadata.get("page_count", 0)
        metadata = create_processing_metadata(
            original_type="pdf",
            original_size=len(raw_content.content),
            processed_size=len(normalized_text),
            pages_processed=page_count,
            extraction_method="pypdf",
        )

        return ProcessedContent(
            title=raw_content.title or "Untitled Document",
            content=normalized_text,
            word_count=estimate_word_count(normalized_text),
            content_type="text",
            processing_metadata=metadata,
        )

    except Exception:
        # Log error but don't raise - return None for graceful handling
        return None


def process_text_content(raw_content: RawContent) -> ProcessedContent | None:
    """
    Process plain text content with basic normalization.

    Processing steps:
    1. Normalize whitespace
    2. Remove excessive line breaks
    3. Validate content length

    Args:
        raw_content: RawContent with content_type="text"

    Returns:
        ProcessedContent with normalized text or None if processing fails
    """
    if not raw_content.content:
        return None

    try:
        # Simple normalization for plain text
        normalized_text = normalize_text(raw_content.content)

        # Validate result
        if not validate_text_content(normalized_text):
            return None

        # Truncate if necessary
        if len(normalized_text) > 50000:  # Use settings value
            normalized_text = truncate_content(normalized_text, 50000)

        # Create processing metadata
        metadata = create_processing_metadata(
            original_type="text",
            original_size=len(raw_content.content),
            processed_size=len(normalized_text),
            normalization_applied=True,
        )

        return ProcessedContent(
            title=raw_content.title or "Text Content",
            content=normalized_text,
            word_count=estimate_word_count(normalized_text),
            content_type="text",
            processing_metadata=metadata,
        )

    except Exception:
        # Log error but don't raise - return None for graceful handling
        return None


# Processor mapping for factory pattern
CONTENT_PROCESSORS = {
    "html": process_html_content,
    "pdf": process_pdf_content,
    "text": process_text_content,
}
