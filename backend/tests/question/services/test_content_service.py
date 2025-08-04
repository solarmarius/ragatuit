"""Tests for module-based content processing functions."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tests.test_data import (
    DEFAULT_EXTRACTED_CONTENT,
    DEFAULT_PAGE_CONTENT,
    get_sample_module_content,
)


@pytest.fixture
def sample_content_dict():
    """Create sample content dictionary using centralized data."""
    return get_sample_module_content()


@pytest.fixture
def sample_large_content_dict():
    """Create sample content dictionary with large content."""
    return get_sample_module_content(large_content=True)


@pytest.mark.asyncio
async def test_get_content_from_quiz_success():
    """Test successful content retrieval from quiz."""
    from src.question.services.content_service import get_content_from_quiz

    quiz_id = uuid.uuid4()
    mock_content = get_sample_module_content()

    with patch(
        "src.question.services.content_service.get_async_session"
    ) as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        with patch(
            "src.quiz.service.get_content_from_quiz", return_value=mock_content
        ) as mock_get_content:
            result = await get_content_from_quiz(quiz_id)

            assert result == mock_content
            mock_get_content.assert_called_once_with(mock_session, quiz_id)


@pytest.mark.asyncio
async def test_get_content_from_quiz_no_content_found():
    """Test content retrieval when no content is found."""
    from src.question.services.content_service import get_content_from_quiz

    quiz_id = uuid.uuid4()

    with patch(
        "src.question.services.content_service.get_async_session"
    ) as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        with patch("src.quiz.service.get_content_from_quiz", return_value=None):
            with pytest.raises(ValueError, match="No extracted content found"):
                await get_content_from_quiz(quiz_id)


@pytest.mark.asyncio
async def test_get_content_from_quiz_exception_handling():
    """Test exception handling during content retrieval."""
    from src.question.services.content_service import get_content_from_quiz

    quiz_id = uuid.uuid4()

    with patch(
        "src.question.services.content_service.get_async_session"
    ) as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_session

        with patch(
            "src.quiz.service.get_content_from_quiz",
            side_effect=Exception("Database error"),
        ):
            with pytest.raises(Exception, match="Database error"):
                await get_content_from_quiz(quiz_id)


def test_validate_module_content_basic(sample_content_dict):
    """Test basic module content validation."""
    from src.question.services.content_service import validate_module_content

    result = validate_module_content(sample_content_dict)

    assert len(result) == 2  # Two modules should be validated
    assert "module_1" in result
    assert "module_2" in result

    # Check that module content is combined correctly
    module_1_content = result["module_1"]
    assert "## Introduction to Python" in module_1_content
    assert "## Variables and Data Types" in module_1_content
    assert "Python is a high-level programming language" in module_1_content

    module_2_content = result["module_2"]
    assert "## Control Structures" in module_2_content
    assert "Control structures in Python" in module_2_content


def test_validate_module_content_filters_short_content():
    """Test that short content is filtered out."""
    from src.question.services.content_service import validate_module_content

    content_dict = {
        "module_short": [
            {
                "id": "page_short",
                "title": "Short",
                "content": "Too short",  # Less than 100 characters
            }
        ],
        "module_valid": [
            {
                "id": "page_valid",
                "title": "Valid Content",
                "content": "This is a valid content section with enough text to pass validation. "
                * 3,
            }
        ],
    }

    result = validate_module_content(content_dict)

    assert len(result) == 1  # Only one module should pass validation
    assert "module_valid" in result
    assert "module_short" not in result


def test_validate_module_content_invalid_data():
    """Test handling of invalid data structures."""
    from src.question.services.content_service import validate_module_content

    content_dict = {
        "module_invalid": "not a list",  # Invalid format
        "module_empty": [],  # Empty list
        "module_valid": [
            {
                "id": "page_1",
                "title": "Valid",
                "content": "This is valid content with enough text. " * 5,
            }
        ],
    }

    result = validate_module_content(content_dict)

    assert len(result) == 1
    assert "module_valid" in result
    assert "module_invalid" not in result
    assert "module_empty" not in result


@pytest.mark.asyncio
async def test_prepare_content_for_generation_with_quiz_content():
    """Test content preparation using quiz content."""
    from src.question.services.content_service import prepare_content_for_generation

    quiz_id = uuid.uuid4()
    mock_content = get_sample_module_content()

    with patch(
        "src.question.services.content_service.get_content_from_quiz",
        return_value=mock_content,
    ) as mock_get_content:
        result = await prepare_content_for_generation(quiz_id)

        mock_get_content.assert_called_once_with(quiz_id)
        assert "module_1" in result
        assert "## Introduction to Python" in result["module_1"]


@pytest.mark.asyncio
async def test_prepare_content_for_generation_with_custom_content():
    """Test content preparation using custom content."""
    from src.question.services.content_service import prepare_content_for_generation

    quiz_id = uuid.uuid4()
    custom_content = get_sample_module_content(module_suffix="_custom")

    result = await prepare_content_for_generation(quiz_id, custom_content)

    assert "module_1_custom" in result
    assert "## Introduction to Python" in result["module_1_custom"]


@pytest.mark.asyncio
async def test_prepare_and_validate_content_with_quality_filter():
    """Test the convenience function with quality filtering."""
    from src.question.services.content_service import prepare_and_validate_content

    quiz_id = uuid.uuid4()
    # Use centralized content with mixed quality
    mock_content = {
        "module_high_quality": [
            {
                "id": "page_1",
                "title": "High Quality Content",
                "content": "This is comprehensive content with substantial information and detailed explanations. "
                * 50,
            }
        ],
        "module_low_quality": [
            {
                "id": "page_2",
                "title": "Low Quality",
                "content": "Short and low quality content.",
            }
        ],
    }

    with patch(
        "src.question.services.content_service.get_content_from_quiz",
        return_value=mock_content,
    ):
        # With quality filter (default)
        result_filtered = await prepare_and_validate_content(quiz_id)
        assert "module_high_quality" in result_filtered
        # Low quality module may or may not be filtered depending on score

        # Without quality filter
        result_unfiltered = await prepare_and_validate_content(
            quiz_id, quality_filter=False
        )
        assert "module_high_quality" in result_unfiltered
        # All modules with sufficient length should be present


def test_validate_content_quality_filters_low_quality():
    """Test that low-quality module content is filtered out."""
    from src.question.services.content_service import validate_content_quality

    modules_content = {
        "module_high_quality": "This is a comprehensive module with substantial content covering various topics in detail. "
        * 30,
        "module_low_quality": "Short low quality content with too much <markup><tags>[brackets]",
        "module_empty": "",
    }

    result = validate_content_quality(modules_content)

    assert "module_high_quality" in result
    assert "module_low_quality" not in result
    assert "module_empty" not in result


def test_validate_content_quality_empty_input():
    """Test quality validation with empty input."""
    from src.question.services.content_service import validate_content_quality

    result = validate_content_quality({})

    assert result == {}


def test_get_content_statistics_basic():
    """Test basic content statistics calculation."""
    from src.question.services.content_service import get_content_statistics

    modules_content = {
        "module_1": "This is module one content. " * 10,
        "module_2": "This is module two content. " * 15,
    }

    stats = get_content_statistics(modules_content)

    assert stats["total_modules"] == 2
    assert stats["total_characters"] > 0
    assert stats["total_words"] > 0
    assert stats["avg_module_size"] > 0
    assert stats["avg_word_count"] > 0
    assert "module_1" in stats["module_ids"]
    assert "module_2" in stats["module_ids"]


def test_get_content_statistics_empty_modules():
    """Test statistics calculation with empty modules."""
    from src.question.services.content_service import get_content_statistics

    stats = get_content_statistics({})

    assert stats["total_modules"] == 0
    assert stats["total_characters"] == 0
    assert stats["total_words"] == 0
    assert stats["avg_module_size"] == 0
    assert stats["avg_word_count"] == 0
    assert stats["module_ids"] == []


def test_calculate_module_quality_score_high_quality():
    """Test quality score calculation for high-quality content."""
    from src.question.services.content_service import _calculate_module_quality_score

    high_quality_content = (
        "This is a comprehensive educational module covering important concepts in computer science. "
        "The content includes detailed explanations, examples, and practical applications. "
        "Students will learn about algorithms, data structures, and programming paradigms. "
    ) * 10

    score = _calculate_module_quality_score(high_quality_content)

    assert score > 0.5  # Should be high quality


def test_calculate_module_quality_score_low_quality():
    """Test quality score calculation for low-quality content."""
    from src.question.services.content_service import _calculate_module_quality_score

    low_quality_content = "Short content with <lots><of><markup>[tags][everywhere]"

    score = _calculate_module_quality_score(low_quality_content)

    assert score < 0.5  # Should be low quality


def test_calculate_module_quality_score_empty_content():
    """Test quality score calculation for empty content."""
    from src.question.services.content_service import _calculate_module_quality_score

    score = _calculate_module_quality_score("")

    assert score == 0.0


def test_combine_module_pages_success():
    """Test successful combination of module pages."""
    from src.question.services.content_service import _combine_module_pages

    pages = [
        {
            "id": "page_1",
            "title": "First Page",
            "content": "This is the first page content.",
        },
        {
            "id": "page_2",
            "title": "Second Page",
            "content": "This is the second page content.",
        },
    ]

    result = _combine_module_pages("module_1", pages)

    assert "## First Page" in result
    assert "## Second Page" in result
    assert "This is the first page content" in result
    assert "This is the second page content" in result


def test_combine_module_pages_skips_invalid_pages():
    """Test that invalid pages are skipped during combination."""
    from src.question.services.content_service import _combine_module_pages

    pages = [
        "invalid_page_string",  # Invalid format
        {
            "id": "page_valid",
            "title": "Valid Page",
            "content": "This is valid content for the page.",
        },
        {
            "id": "page_no_content",
            "title": "No Content",
            # Missing content field
        },
        {
            "id": "page_short",
            "title": "Short",
            "content": "Short",  # Too short (less than 10 chars)
        },
    ]

    result = _combine_module_pages("module_1", pages)

    assert "## Valid Page" in result
    assert "This is valid content" in result
    assert "Short" not in result  # Short content should be filtered


def test_calculate_total_content_size():
    """Test total content size calculation."""
    from src.question.services.content_service import _calculate_total_content_size

    content_dict = {
        "module_1": [
            {"id": "page_1", "content": "Content one"},
            {"id": "page_2", "content": "Content two"},
        ],
        "module_2": [
            {"id": "page_3", "content": "Content three"},
        ],
    }

    total_size = _calculate_total_content_size(content_dict)

    expected_size = len("Content one") + len("Content two") + len("Content three")
    assert total_size == expected_size


def test_calculate_total_content_size_invalid_data():
    """Test total content size calculation with invalid data."""
    from src.question.services.content_service import _calculate_total_content_size

    content_dict = {
        "module_invalid": "not a list",
        "module_valid": [
            {"id": "page_1", "content": "Valid content"},
        ],
    }

    total_size = _calculate_total_content_size(content_dict)

    assert total_size == len("Valid content")


@pytest.mark.asyncio
async def test_functional_composition_pipeline():
    """Test that functions can be easily composed in a pipeline."""
    from src.question.services.content_service import (
        get_content_statistics,
        prepare_and_validate_content,
        prepare_content_for_generation,
        validate_content_quality,
    )

    quiz_id = uuid.uuid4()
    mock_content = get_sample_module_content()

    with patch(
        "src.question.services.content_service.get_content_from_quiz",
        return_value=mock_content,
    ):
        # Test functional pipeline
        content = await prepare_content_for_generation(quiz_id)
        quality_content = validate_content_quality(content)
        stats = get_content_statistics(quality_content)

        # Verify pipeline results
        assert len(content) >= 1
        assert len(quality_content) >= 1
        assert stats["total_modules"] >= 1
        assert stats["total_characters"] > 0

        # Test convenience function does the same thing
        convenience_result = await prepare_and_validate_content(quiz_id)
        assert convenience_result == quality_content
