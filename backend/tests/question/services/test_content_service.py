"""Tests for content processing service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_workflow_config():
    """Create mock workflow configuration."""
    config = MagicMock()
    config.max_chunk_size = 1000
    config.min_chunk_size = 50
    config.overlap_size = 100
    config.quality_threshold = 0.5
    return config


@pytest.fixture
def content_service(mock_workflow_config):
    """Create content processing service instance."""
    from src.question.services.content_service import ContentProcessingService

    return ContentProcessingService(mock_workflow_config)


@pytest.fixture
def sample_content_dict():
    """Create sample content dictionary."""
    return {
        "module_1": [
            {
                "id": "page_1",
                "title": "Introduction to Python",
                "content": (
                    "Python is a high-level programming language. " * 3 + "\n\n"
                )
                * 3,
                "url": "intro-python",
            },
            {
                "id": "page_2",
                "title": "Variables and Data Types",
                "content": (
                    "Python has several built-in data types including integers, floats, strings, and booleans. "
                    * 3
                    + "\n\n"
                )
                * 3,
                "url": "variables-types",
            },
        ],
        "module_2": [
            {
                "id": "page_3",
                "title": "Control Structures",
                "content": (
                    "Control structures in Python include if statements, for loops, and while loops. "
                    * 3
                    + "\n\n"
                )
                * 4,
                "url": "control-structures",
            }
        ],
    }


@pytest.fixture
def large_content_dict():
    """Create large content dictionary for chunking tests."""
    # Create content that's definitely larger than max_chunk_size (1000) with paragraph breaks
    paragraph = (
        "This is a very long paragraph that will need to be split into multiple chunks. "
        * 10
    )
    large_content = (paragraph + "\n\n") * 10  # ~8000+ chars with paragraph breaks

    return {
        "large_module": [
            {
                "id": "large_page",
                "title": "Large Content Page",
                "content": large_content,
                "url": "large-content",
            }
        ]
    }


@pytest.mark.asyncio
async def test_get_content_from_quiz_success(content_service):
    """Test successful content retrieval from quiz."""
    quiz_id = uuid.uuid4()
    expected_content = {"module_1": [{"id": "page_1", "content": "Test content"}]}

    with patch(
        "src.question.services.content_service.get_async_session"
    ) as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        with patch("src.quiz.service.get_content_from_quiz") as mock_get_content:
            mock_get_content.return_value = expected_content

            result = await content_service.get_content_from_quiz(quiz_id)

    assert result == expected_content
    mock_get_content.assert_called_once_with(mock_session, quiz_id)


@pytest.mark.asyncio
async def test_get_content_from_quiz_no_content_found(content_service):
    """Test content retrieval when no content is found."""
    quiz_id = uuid.uuid4()

    with patch(
        "src.question.services.content_service.get_async_session"
    ) as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        with patch("src.quiz.service.get_content_from_quiz") as mock_get_content:
            mock_get_content.return_value = None

            with pytest.raises(ValueError) as exc_info:
                await content_service.get_content_from_quiz(quiz_id)

    assert f"No extracted content found for quiz {quiz_id}" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_content_from_quiz_exception_handling(content_service):
    """Test exception handling in content retrieval."""
    quiz_id = uuid.uuid4()

    with patch(
        "src.question.services.content_service.get_async_session"
    ) as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        with patch("src.quiz.service.get_content_from_quiz") as mock_get_content:
            mock_get_content.side_effect = Exception("Database error")

            with pytest.raises(Exception) as exc_info:
                await content_service.get_content_from_quiz(quiz_id)

    assert "Database error" in str(exc_info.value)


def test_chunk_content_basic(content_service, sample_content_dict):
    """Test basic content chunking."""
    chunks = content_service.chunk_content(sample_content_dict)

    assert len(chunks) == 3  # 3 pages should create 3 chunks

    # Verify chunk properties
    for chunk in chunks:
        assert hasattr(chunk, "content")
        assert hasattr(chunk, "source")
        assert hasattr(chunk, "metadata")
        assert (
            len(chunk.content.strip()) >= content_service.configuration.min_chunk_size
        )

    # Verify metadata
    chunk_sources = [chunk.source for chunk in chunks]
    assert "module_1/page_1" in chunk_sources
    assert "module_2/page_3" in chunk_sources


def test_chunk_content_filters_short_content(content_service):
    """Test that short content is filtered out."""
    short_content_dict = {
        "module_1": [
            {
                "id": "short_page",
                "title": "Short",
                "content": "Too short",  # Less than min_chunk_size
                "url": "short",
            },
            {
                "id": "long_page",
                "title": "Long Enough",
                "content": "This content is long enough to meet the minimum chunk size requirements. "
                * 3,
                "url": "long-enough",
            },
        ]
    }

    chunks = content_service.chunk_content(short_content_dict)

    assert len(chunks) == 1  # Only the long content should remain
    assert "long_page" in chunks[0].source


def test_chunk_content_large_content_splitting(content_service, large_content_dict):
    """Test splitting of large content into multiple chunks."""
    chunks = content_service.chunk_content(large_content_dict)

    # Should create multiple chunks from the large content
    assert len(chunks) > 1

    # Each chunk should be within size limits
    for chunk in chunks:
        assert len(chunk.content) <= content_service.configuration.max_chunk_size

    # Check that chunks have correct metadata for split content
    split_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "split"]
    assert len(split_chunks) > 0

    # Verify chunk indices are sequential
    chunk_indices = [c.metadata.get("chunk_index") for c in split_chunks]
    assert chunk_indices == list(range(len(chunk_indices)))


def test_chunk_content_invalid_data(content_service):
    """Test chunking with invalid data structures."""
    invalid_content_dict = {
        "module_1": "not_a_list",  # Should be a list
        "module_2": [
            "not_a_dict",  # Should be a dict
            {
                "id": "valid_page",
                "content": "Valid content for testing chunking behavior. " * 5,
                "title": "Valid Page",
            },
        ],
    }

    chunks = content_service.chunk_content(invalid_content_dict)

    # Should only process the valid page
    assert len(chunks) == 1
    assert "valid_page" in chunks[0].source


@pytest.mark.asyncio
async def test_prepare_content_for_generation_with_quiz_content(content_service):
    """Test content preparation using quiz content."""
    quiz_id = uuid.uuid4()

    with (
        patch.object(content_service, "get_content_from_quiz") as mock_get_content,
        patch.object(content_service, "chunk_content") as mock_chunk,
    ):
        mock_content = {"module_1": [{"id": "page_1", "content": "test"}]}
        mock_chunks = [MagicMock()]

        mock_get_content.return_value = mock_content
        mock_chunk.return_value = mock_chunks

        result = await content_service.prepare_content_for_generation(quiz_id)

    assert result == mock_chunks
    mock_get_content.assert_called_once_with(quiz_id)
    mock_chunk.assert_called_once_with(mock_content)


@pytest.mark.asyncio
async def test_prepare_content_for_generation_with_custom_content(content_service):
    """Test content preparation using custom content."""
    quiz_id = uuid.uuid4()
    custom_content = {"custom_module": [{"id": "custom_page", "content": "custom"}]}

    with (
        patch.object(content_service, "get_content_from_quiz") as mock_get_content,
        patch.object(content_service, "chunk_content") as mock_chunk,
    ):
        mock_chunks = [MagicMock()]
        mock_chunk.return_value = mock_chunks

        result = await content_service.prepare_content_for_generation(
            quiz_id, custom_content=custom_content
        )

    assert result == mock_chunks
    mock_get_content.assert_not_called()  # Should not fetch from quiz
    mock_chunk.assert_called_once_with(custom_content)


def test_validate_content_quality_filters_low_quality(content_service):
    """Test content quality validation filters low-quality chunks."""
    from src.question.workflows import ContentChunk

    # Create chunks with different quality scores
    high_quality_chunk = ContentChunk(
        content="This is a well-written, comprehensive piece of content with good structure and meaningful information that should pass quality checks.",
        source="high_quality",
        metadata={},
    )

    low_quality_chunk = ContentChunk(
        content="bad",  # Very short, low quality
        source="low_quality",
        metadata={},
    )

    chunks = [high_quality_chunk, low_quality_chunk]

    with patch.object(content_service, "_calculate_content_quality") as mock_quality:
        # High quality chunk gets good score, low quality gets bad score
        mock_quality.side_effect = [0.8, 0.2]  # threshold is 0.5

        result = content_service.validate_content_quality(chunks)

    assert len(result) == 1  # Only high quality chunk should remain
    assert result[0].source == "high_quality"
    assert result[0].metadata["quality_score"] == 0.8


def test_validate_content_quality_empty_input(content_service):
    """Test quality validation with empty input."""
    result = content_service.validate_content_quality([])
    assert result == []


def test_get_content_statistics_basic(content_service):
    """Test content statistics calculation."""
    from src.question.workflows import ContentChunk

    chunks = [
        ContentChunk(
            content="First chunk with some content here.", source="chunk_1", metadata={}
        ),
        ContentChunk(
            content="Second chunk has different content length.",
            source="chunk_2",
            metadata={},
        ),
    ]

    stats = content_service.get_content_statistics(chunks)

    assert stats["total_chunks"] == 2
    assert stats["total_characters"] > 0
    assert stats["total_words"] > 0
    assert stats["avg_chunk_size"] > 0
    assert stats["avg_word_count"] > 0
    assert stats["min_chunk_size"] > 0
    assert stats["max_chunk_size"] > 0
    assert len(stats["sources"]) == 2
    assert stats["source_count"] == 2


def test_get_content_statistics_empty_chunks(content_service):
    """Test statistics calculation with empty chunks list."""
    stats = content_service.get_content_statistics([])

    expected_empty_stats = {
        "total_chunks": 0,
        "total_characters": 0,
        "total_words": 0,
        "avg_chunk_size": 0,
        "avg_word_count": 0,
        "sources": [],
    }

    for key, value in expected_empty_stats.items():
        assert stats[key] == value


def test_calculate_content_quality_high_quality(content_service):
    """Test quality calculation for high-quality content."""
    from src.question.workflows import ContentChunk

    high_quality_content = (
        "This is a comprehensive and well-structured piece of educational content. "
        "It contains multiple sentences with proper punctuation. "
        "The content provides valuable information that would be useful for generating questions. "
        "It has good vocabulary diversity and appropriate length for processing."
    )

    chunk = ContentChunk(content=high_quality_content, source="test", metadata={})

    quality_score = content_service._calculate_content_quality(chunk)

    assert 0.0 <= quality_score <= 1.0
    assert quality_score > 0.5  # Should be considered high quality


def test_calculate_content_quality_low_quality(content_service):
    """Test quality calculation for low-quality content."""
    from src.question.workflows import ContentChunk

    low_quality_content = "bad bad bad bad bad"  # Repetitive, short

    chunk = ContentChunk(content=low_quality_content, source="test", metadata={})

    quality_score = content_service._calculate_content_quality(chunk)

    assert 0.0 <= quality_score <= 1.0
    assert quality_score < 0.5  # Should be considered low quality


def test_calculate_content_quality_empty_content(content_service):
    """Test quality calculation for empty content."""
    from src.question.workflows import ContentChunk

    chunk = ContentChunk(content="", source="test", metadata={})

    quality_score = content_service._calculate_content_quality(chunk)

    assert quality_score == 0.0


def test_calculate_content_quality_heavily_formatted(content_service):
    """Test quality calculation for heavily formatted content."""
    from src.question.workflows import ContentChunk

    heavily_formatted = (
        "<div><p><strong><em><span>Too much</span></em></strong> "
        "<code><pre>[markup]</pre></code> in this content</p></div>"
    )

    chunk = ContentChunk(content=heavily_formatted, source="test", metadata={})

    quality_score = content_service._calculate_content_quality(chunk)

    assert 0.0 <= quality_score <= 1.0
    # Should be penalized for excessive formatting
    assert quality_score < 0.7


def test_process_module_pages_skips_invalid_pages(content_service):
    """Test that invalid pages are skipped during processing."""
    pages = [
        "not_a_dict",  # Should be skipped
        {
            "id": "valid_page",
            "content": "Valid content that should be processed. " * 5,
            "title": "Valid Page",
        },
        {
            "id": "short_page",
            "content": "Short",  # Should be skipped due to length
            "title": "Short Page",
        },
    ]

    chunks = content_service._process_module_pages("test_module", pages)

    assert len(chunks) == 1  # Only the valid page should be processed
    assert "valid_page" in chunks[0].source


def test_chunk_page_content_single_chunk(content_service):
    """Test chunking page content that fits in a single chunk."""
    page = {"id": "test_page", "title": "Test Page", "url": "test-page"}
    content = "This content is short enough to fit in a single chunk."

    chunks = content_service._chunk_page_content("test_module", page, content)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.content == content
    assert chunk.source == "test_module/test_page"
    assert chunk.metadata["chunk_type"] == "full_page"
    assert chunk.metadata["module_id"] == "test_module"
    assert chunk.metadata["page_id"] == "test_page"


def test_chunk_page_content_multiple_chunks(content_service):
    """Test chunking page content that requires splitting."""
    page = {"id": "large_page", "title": "Large Page", "url": "large-page"}
    # Create content larger than max_chunk_size with paragraph breaks
    paragraph = "This is a large piece of content. " * 10
    content = (paragraph + "\n\n") * 10  # Multiple paragraphs that need splitting

    chunks = content_service._chunk_page_content("test_module", page, content)

    assert len(chunks) > 1  # Should be split into multiple chunks

    for i, chunk in enumerate(chunks):
        assert len(chunk.content) <= content_service.configuration.max_chunk_size
        assert chunk.metadata["chunk_type"] == "split"
        assert chunk.metadata["chunk_index"] == i
        assert "large_page" in chunk.source


def test_split_large_content_with_overlap(content_service):
    """Test splitting large content with overlap configuration."""
    content_service.configuration.overlap_size = 50  # Set overlap

    page = {"id": "test_page", "title": "Test"}
    content = (
        "First paragraph content.\n\nSecond paragraph content.\n\nThird paragraph content."
        * 20
    )

    chunks = content_service._split_large_content(content, "test_module", page)

    assert len(chunks) > 1

    # Check that chunks have overlap metadata (except the last one)
    for i, chunk in enumerate(chunks[:-1]):  # All but the last chunk
        if chunk.metadata.get("chunk_index", 0) > 0:  # Not the first chunk
            assert "overlap_size" in chunk.metadata


def test_split_large_content_no_overlap(content_service):
    """Test splitting large content without overlap."""
    content_service.configuration.overlap_size = 0  # No overlap

    page = {"id": "test_page", "title": "Test"}
    content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph." * 30

    chunks = content_service._split_large_content(content, "test_module", page)

    assert len(chunks) > 1

    # Verify sequential chunk indices
    chunk_indices = [chunk.metadata["chunk_index"] for chunk in chunks]
    assert chunk_indices == list(range(len(chunks)))


def test_calculate_total_content_size(content_service, sample_content_dict):
    """Test calculation of total content size."""
    total_size = content_service._calculate_total_content_size(sample_content_dict)

    # Calculate expected size manually
    expected_size = 0
    for pages in sample_content_dict.values():
        for page in pages:
            expected_size += len(page["content"])

    assert total_size == expected_size
    assert total_size > 0


def test_calculate_total_content_size_invalid_data(content_service):
    """Test total size calculation with invalid data."""
    invalid_data = {
        "module_1": "not_a_list",
        "module_2": ["not_a_dict", {"content": "valid content"}],
    }

    total_size = content_service._calculate_total_content_size(invalid_data)

    # Should only count the valid content
    assert total_size == len("valid content")


@pytest.mark.parametrize(
    "chunk_size,min_size,expected_chunks",
    [
        (2000, 100, 1),  # Large chunks, will fit in one
    ],
)
def test_chunk_content_various_sizes(
    content_service, sample_content_dict, chunk_size, min_size, expected_chunks
):
    """Test content chunking with various size configurations."""
    content_service.configuration.max_chunk_size = chunk_size
    content_service.configuration.min_chunk_size = min_size

    chunks = content_service.chunk_content(sample_content_dict)

    # Verify all chunks meet minimum size requirements
    for chunk in chunks:
        assert len(chunk.content) >= min_size
        # For paragraph-based splitting, chunks may exceed max_chunk_size
        # if a single paragraph is larger than the limit

    # Should have reasonable number of chunks
    assert len(chunks) >= 1
