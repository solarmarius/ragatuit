"""Tests for content extraction service layer."""

import time
from unittest.mock import Mock, patch

import pytest


@pytest.mark.asyncio
async def test_process_content_success():
    """Test successful content processing."""
    from src.content_extraction.models import ProcessedContent, RawContent
    from src.content_extraction.service import process_content

    raw_content = RawContent(
        content="<p>Test HTML content</p>",
        content_type="html",
        title="Test Page",
        metadata={"source": "canvas"},
    )

    expected_processed = ProcessedContent(
        title="Test Page",
        content="Test HTML content",
        word_count=3,
        content_type="text",
        processing_metadata={"original_type": "html"},
    )

    # Mock processor function
    processor_func = Mock(return_value=expected_processed)

    result = await process_content(raw_content, processor_func)

    assert result == expected_processed
    processor_func.assert_called_once_with(raw_content)


@pytest.mark.asyncio
async def test_process_content_with_validator_success():
    """Test content processing with successful validation."""
    from src.content_extraction.models import ProcessedContent, RawContent
    from src.content_extraction.service import process_content

    raw_content = RawContent(
        content="Valid content", content_type="text", title="Valid Page"
    )

    processed_content = ProcessedContent(
        title="Valid Page", content="Valid content", word_count=2, content_type="text"
    )

    validator_func = Mock(return_value=True)
    processor_func = Mock(return_value=processed_content)

    result = await process_content(raw_content, processor_func, validator_func)

    assert result == processed_content
    validator_func.assert_called_once_with(raw_content)
    processor_func.assert_called_once_with(raw_content)


@pytest.mark.asyncio
async def test_process_content_with_validator_failure():
    """Test content processing with validation failure."""
    from src.content_extraction.models import RawContent
    from src.content_extraction.service import process_content

    raw_content = RawContent(
        content="Invalid content", content_type="text", title="Invalid Page"
    )

    validator_func = Mock(return_value=False)
    processor_func = Mock()

    result = await process_content(raw_content, processor_func, validator_func)

    assert result is None
    validator_func.assert_called_once_with(raw_content)
    processor_func.assert_not_called()


@pytest.mark.asyncio
async def test_process_content_processor_returns_none():
    """Test handling when processor returns None."""
    from src.content_extraction.models import RawContent
    from src.content_extraction.service import process_content

    raw_content = RawContent(
        content="Empty content", content_type="text", title="Empty Page"
    )

    processor_func = Mock(return_value=None)

    result = await process_content(raw_content, processor_func)

    assert result is None
    processor_func.assert_called_once_with(raw_content)


@pytest.mark.asyncio
async def test_process_content_batch_success():
    """Test successful batch processing."""
    from src.content_extraction.models import ProcessedContent, RawContent
    from src.content_extraction.service import process_content_batch

    raw_contents = [
        RawContent("Content 1", "html", "Page 1"),
        RawContent("Content 2", "text", "Page 2"),
        RawContent("Content 3", "html", "Page 3"),
    ]

    processed_contents = [
        ProcessedContent("Page 1", "Content 1", 2, "text"),
        ProcessedContent("Page 2", "Content 2", 2, "text"),
        ProcessedContent("Page 3", "Content 3", 2, "text"),
    ]

    # Mock get_processor function
    processor_func = Mock()
    processor_func.side_effect = processed_contents

    get_processor = Mock(return_value=processor_func)

    result = await process_content_batch(raw_contents, get_processor)

    assert len(result) == 3
    assert result == processed_contents
    assert get_processor.call_count == 3


@pytest.mark.asyncio
async def test_process_content_batch_with_failures():
    """Test batch processing with some failures."""
    from src.content_extraction.exceptions import UnsupportedFormatError
    from src.content_extraction.models import ProcessedContent, RawContent
    from src.content_extraction.service import process_content_batch

    raw_contents = [
        RawContent("Good content", "html", "Good Page"),
        RawContent("Bad content", "unknown", "Bad Page"),
        RawContent("Another good", "text", "Another Good Page"),
    ]

    # Mock processor that succeeds for known types
    def mock_processor(content: RawContent) -> ProcessedContent:
        if content.content_type in ["html", "text"]:
            return ProcessedContent(
                title=content.title,
                content=content.content,
                word_count=2,
                content_type="text",
            )
        return None

    processor_func = Mock(side_effect=mock_processor)

    # Mock get_processor that raises for unknown types
    def mock_get_processor(content_type: str):
        if content_type == "unknown":
            raise UnsupportedFormatError(content_type)
        return processor_func

    get_processor = Mock(side_effect=mock_get_processor)

    result = await process_content_batch(raw_contents, get_processor)

    # Should have 2 successful items (first and third)
    assert len(result) == 2
    assert result[0].title == "Good Page"
    assert result[1].title == "Another Good Page"


@pytest.mark.asyncio
async def test_process_content_batch_timing():
    """Test that batch processing tracks timing."""
    from src.content_extraction.models import ProcessedContent, RawContent
    from src.content_extraction.service import process_content_batch

    raw_contents = [RawContent("Test", "text", "Test")]

    processed_content = ProcessedContent("Test", "Test", 1, "text")
    processor_func = Mock(return_value=processed_content)
    get_processor = Mock(return_value=processor_func)

    # Mock time.time to control timing
    # We need to provide enough values since logging also calls time.time()
    with patch("src.content_extraction.service.time.time") as mock_time:
        # Return the same start time multiple times, then end time
        mock_time.side_effect = [1000.0] * 10 + [1002.5] * 10  # 2.5 second difference

        result = await process_content_batch(raw_contents, get_processor)

    assert len(result) == 1
    # Verify time.time was called at least for start and end
    assert mock_time.call_count >= 2


def test_create_processor_selector_html():
    """Test processor selector for HTML content."""
    from src.content_extraction.service import create_processor_selector

    get_processor = create_processor_selector()

    # Mock the CONTENT_PROCESSORS registry
    with patch("src.content_extraction.service.CONTENT_PROCESSORS") as mock_processors:
        mock_html_processor = Mock()
        mock_processors.get.return_value = mock_html_processor

        processor = get_processor("html")

        assert processor == mock_html_processor
        mock_processors.get.assert_called_once_with("html")


@pytest.mark.parametrize(
    "input_type,expected_key",
    [
        ("text/html", "html"),
        ("application/pdf", "pdf"),
        ("text/plain", "text"),
        ("HTML", "html"),  # Case insensitive
        ("PDF", "pdf"),
    ],
)
def test_create_processor_selector_mime_type_mapping(input_type, expected_key):
    """Test processor selector with MIME types."""
    from src.content_extraction.service import create_processor_selector

    get_processor = create_processor_selector()

    with patch("src.content_extraction.service.CONTENT_PROCESSORS") as mock_processors:
        mock_processor = Mock()
        mock_processors.get.return_value = mock_processor

        processor = get_processor(input_type)

        assert processor == mock_processor
        # Verify the correct normalized key was used
        mock_processors.get.assert_called_with(expected_key)


def test_create_processor_selector_unsupported_format():
    """Test processor selector with unsupported format."""
    from src.content_extraction.exceptions import UnsupportedFormatError
    from src.content_extraction.service import create_processor_selector

    get_processor = create_processor_selector()

    with patch("src.content_extraction.service.CONTENT_PROCESSORS") as mock_processors:
        mock_processors.get.return_value = None

        with pytest.raises(UnsupportedFormatError) as exc_info:
            get_processor("unsupported_format")

        assert "unsupported_format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_processing_summary_basic():
    """Test basic processing summary creation."""
    from src.content_extraction.models import ProcessedContent, RawContent
    from src.content_extraction.service import create_processing_summary

    raw_contents = [
        RawContent("Content 1", "html", "Page 1"),
        RawContent("Content 2", "pdf", "Page 2"),
        RawContent("Content 3", "text", "Page 3"),
    ]

    processed_contents = [
        ProcessedContent(
            "Page 1",
            "Content 1",
            2,
            "text",
            processing_metadata={"original_type": "html"},
        ),
        ProcessedContent(
            "Page 2",
            "Content 2",
            3,
            "text",
            processing_metadata={"original_type": "pdf"},
        ),
    ]

    summary = await create_processing_summary(raw_contents, processed_contents, 5.5)

    assert summary.total_items == 3
    assert summary.successful_items == 2
    assert summary.failed_items == 1
    assert summary.total_word_count == 5  # 2 + 3
    assert summary.processing_time_seconds == 5.5
    assert summary.content_types_processed == {"html": 1, "pdf": 1}


@pytest.mark.asyncio
async def test_create_processing_summary_empty():
    """Test processing summary with no processed content."""
    from src.content_extraction.models import RawContent
    from src.content_extraction.service import create_processing_summary

    raw_contents = [RawContent("Failed", "unknown", "Failed Page")]
    processed_contents = []

    summary = await create_processing_summary(raw_contents, processed_contents, 1.0)

    assert summary.total_items == 1
    assert summary.successful_items == 0
    assert summary.failed_items == 1
    assert summary.total_word_count == 0
    assert summary.processing_time_seconds == 1.0
    assert summary.content_types_processed == {}


@pytest.mark.asyncio
async def test_full_content_extraction_workflow():
    """Test complete content extraction workflow."""
    from src.content_extraction.models import ProcessedContent, RawContent
    from src.content_extraction.service import (
        create_processing_summary,
        create_processor_selector,
        process_content_batch,
    )

    # Sample raw content
    raw_contents = [
        RawContent(
            content="<html><body><h1>Title</h1><p>Content here</p></body></html>",
            content_type="text/html",
            title="HTML Page",
            metadata={"source": "canvas", "url": "example.com/page1"},
        ),
        RawContent(
            content="Plain text content for testing",
            content_type="text/plain",
            title="Text Document",
            metadata={"source": "upload"},
        ),
    ]

    # Mock processors
    def mock_html_processor(content: RawContent) -> ProcessedContent:
        return ProcessedContent(
            title=content.title,
            content="Title Content here",  # Cleaned HTML
            word_count=3,
            content_type="text",
            processing_metadata={
                "original_type": "html",
                "cleaned": True,
                "html_tags_removed": True,
            },
        )

    def mock_text_processor(content: RawContent) -> ProcessedContent:
        return ProcessedContent(
            title=content.title,
            content=content.content,
            word_count=5,
            content_type="text",
            processing_metadata={"original_type": "text", "cleaned": False},
        )

    # Mock CONTENT_PROCESSORS registry
    with patch("src.content_extraction.service.CONTENT_PROCESSORS") as mock_processors:
        mock_processors.get.side_effect = lambda key: {
            "html": mock_html_processor,
            "text": mock_text_processor,
        }.get(key)

        # Create processor selector
        get_processor = create_processor_selector()

        # Process batch
        start_time = time.time()
        processed_contents = await process_content_batch(raw_contents, get_processor)
        processing_time = time.time() - start_time

        # Create summary
        summary = await create_processing_summary(
            raw_contents, processed_contents, processing_time
        )

    # Verify results
    assert len(processed_contents) == 2

    # HTML content
    html_result = processed_contents[0]
    assert html_result.title == "HTML Page"
    assert html_result.content == "Title Content here"
    assert html_result.word_count == 3
    assert html_result.processing_metadata["original_type"] == "html"

    # Text content
    text_result = processed_contents[1]
    assert text_result.title == "Text Document"
    assert text_result.word_count == 5
    assert text_result.processing_metadata["original_type"] == "text"

    # Summary verification
    assert summary.total_items == 2
    assert summary.successful_items == 2
    assert summary.failed_items == 0
    assert summary.total_word_count == 8  # 3 + 5
    assert summary.content_types_processed == {"html": 1, "text": 1}


@pytest.mark.asyncio
async def test_mixed_success_failure_workflow():
    """Test workflow with mix of successful and failed processing."""
    from src.content_extraction.exceptions import UnsupportedFormatError
    from src.content_extraction.models import ProcessedContent, RawContent
    from src.content_extraction.service import (
        create_processing_summary,
        process_content_batch,
    )

    raw_contents = [
        RawContent("Good HTML", "html", "Good Page"),
        RawContent("Bad content", "unsupported", "Bad Page"),
        RawContent("Good text", "text", "Good Text"),
        RawContent("Error content", "html", "Error Page"),  # Will cause processor error
    ]

    def mock_processor(content: RawContent) -> ProcessedContent:
        if content.title == "Error Page":
            raise Exception("Processor error")
        return ProcessedContent(
            title=content.title,
            content=content.content,
            word_count=2,
            content_type="text",
            processing_metadata={"original_type": content.content_type},
        )

    def mock_get_processor(content_type: str):
        if content_type == "unsupported":
            raise UnsupportedFormatError(content_type)
        return mock_processor

    # Process with errors
    processed_contents = await process_content_batch(raw_contents, mock_get_processor)

    # Should only have 2 successful items
    assert len(processed_contents) == 2
    assert processed_contents[0].title == "Good Page"
    assert processed_contents[1].title == "Good Text"

    # Create summary
    summary = await create_processing_summary(raw_contents, processed_contents, 1.5)

    assert summary.total_items == 4
    assert summary.successful_items == 2
    assert summary.failed_items == 2
    assert summary.content_types_processed == {"html": 1, "text": 1}
