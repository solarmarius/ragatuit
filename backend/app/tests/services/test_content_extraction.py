from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.content_extraction import ContentExtractionService


@pytest.fixture
def service() -> ContentExtractionService:
    """Create a ContentExtractionService instance for testing"""
    return ContentExtractionService(canvas_token="test_token", course_id=12345)


@pytest.mark.asyncio
async def test_extract_content_for_modules_success(
    service: ContentExtractionService,
) -> None:
    """Test successful content extraction from multiple modules"""
    module_ids = [173467, 173468]

    # Mock module items responses
    mock_module_1_items = [
        {
            "id": 1001,
            "type": "Page",
            "title": "Introduction to AI",
            "page_url": "introduction-to-ai",
        },
        {
            "id": 1002,
            "type": "Assignment",
            "title": "Assignment 1",
            "assignment_id": 5001,
        },
        {
            "id": 1003,
            "type": "Page",
            "title": "Machine Learning Basics",
            "page_url": "ml-basics",
        },
    ]

    mock_module_2_items = [
        {
            "id": 2001,
            "type": "Page",
            "title": "Deep Learning",
            "page_url": "deep-learning",
        },
    ]

    # Mock page content responses
    mock_page_1_content = {
        "title": "Introduction to AI",
        "body": "<h1>Introduction</h1><p>Artificial Intelligence is the simulation of human intelligence in machines.</p>",
        "url": "introduction-to-ai",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-02T12:00:00Z",
    }

    mock_page_2_content = {
        "title": "Machine Learning Basics",
        "body": "<h2>Machine Learning</h2><p>Machine learning is a subset of AI that enables computers to learn.</p>",
        "url": "ml-basics",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-02T12:00:00Z",
    }

    mock_page_3_content = {
        "title": "Deep Learning",
        "body": "<h2>Deep Learning</h2><p>Deep learning uses neural networks with multiple layers.</p>",
        "url": "deep-learning",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-02T12:00:00Z",
    }

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()

        # Mock module items API calls
        def mock_get_side_effect(url: str, **_: Any) -> MagicMock:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None

            if "modules/173467/items" in url:
                mock_response.json.return_value = mock_module_1_items
            elif "modules/173468/items" in url:
                mock_response.json.return_value = mock_module_2_items
            elif "pages/introduction-to-ai" in url:
                mock_response.json.return_value = mock_page_1_content
            elif "pages/ml-basics" in url:
                mock_response.json.return_value = mock_page_2_content
            elif "pages/deep-learning" in url:
                mock_response.json.return_value = mock_page_3_content
            else:
                mock_response.json.return_value = {}

            return mock_response

        mock_client.get.side_effect = mock_get_side_effect
        mock_httpx.return_value.__aenter__.return_value = mock_client

        # Execute test
        result = await service.extract_content_for_modules(module_ids)

        # Verify results
        assert len(result) == 2
        assert "module_173467" in result
        assert "module_173468" in result

        # Module 1 should have 2 pages (excluding assignment)
        module_1_content = result["module_173467"]
        assert len(module_1_content) == 2
        assert module_1_content[0]["title"] == "Introduction to AI"
        assert (
            "Artificial Intelligence is the simulation"
            in module_1_content[0]["content"]
        )
        assert module_1_content[1]["title"] == "Machine Learning Basics"
        assert "Machine learning is a subset" in module_1_content[1]["content"]

        # Module 2 should have 1 page
        module_2_content = result["module_173468"]
        assert len(module_2_content) == 1
        assert module_2_content[0]["title"] == "Deep Learning"
        assert "Deep learning uses neural networks" in module_2_content[0]["content"]

        # Verify API calls were made correctly
        assert mock_client.get.call_count == 5  # 2 module items + 3 pages


@pytest.mark.asyncio
async def test_extract_content_for_modules_empty_modules(
    service: ContentExtractionService,
) -> None:
    """Test content extraction with modules that have no page items"""
    module_ids = [173467]

    # Mock module items response with no Page items
    mock_module_items = [
        {
            "id": 1001,
            "type": "Assignment",
            "title": "Assignment 1",
            "assignment_id": 5001,
        },
        {
            "id": 1002,
            "type": "ExternalTool",
            "title": "External Tool",
            "external_url": "https://example.com",
        },
    ]

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_module_items
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service.extract_content_for_modules(module_ids)

        # Verify results
        assert len(result) == 1
        assert "module_173467" in result
        assert len(result["module_173467"]) == 0


@pytest.mark.asyncio
async def test_extract_content_for_modules_page_extraction_failure(
    service: ContentExtractionService,
) -> None:
    """Test content extraction when some pages fail to extract"""
    module_ids = [173467]

    # Mock module items response
    mock_module_items = [
        {
            "id": 1001,
            "type": "Page",
            "title": "Valid Page",
            "page_url": "valid-page",
        },
        {
            "id": 1002,
            "type": "Page",
            "title": "Invalid Page",
            "page_url": "invalid-page",
        },
    ]

    # Mock page content response
    mock_valid_page_content = {
        "title": "Valid Page",
        "body": "<h1>Valid Content</h1><p>This page has valid content that can be extracted.</p>",
        "url": "valid-page",
    }

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()

        def mock_get_side_effect(url: str, **_: Any) -> MagicMock:
            mock_response = MagicMock()

            if "modules/173467/items" in url:
                mock_response.json.return_value = mock_module_items
                mock_response.raise_for_status.return_value = None
            elif "pages/valid-page" in url:
                mock_response.json.return_value = mock_valid_page_content
                mock_response.raise_for_status.return_value = None
            elif "pages/invalid-page" in url:
                # Simulate API error for invalid page
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Not Found", request=MagicMock(), response=MagicMock()
                )
            else:
                mock_response.json.return_value = {}
                mock_response.raise_for_status.return_value = None

            return mock_response

        mock_client.get.side_effect = mock_get_side_effect
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service.extract_content_for_modules(module_ids)

        # Should continue processing and return valid pages only
        assert len(result) == 1
        assert "module_173467" in result
        assert len(result["module_173467"]) == 1
        assert result["module_173467"][0]["title"] == "Valid Page"


@pytest.mark.asyncio
async def test_extract_content_for_modules_module_failure(
    service: ContentExtractionService,
) -> None:
    """Test content extraction when entire module fails"""
    module_ids = [173467, 173468]

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()

        def mock_get_side_effect(url: str, **_: Any) -> MagicMock:
            mock_response = MagicMock()

            if "modules/173467/items" in url:
                # Simulate API error for first module
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Forbidden", request=MagicMock(), response=MagicMock()
                )
            elif "modules/173468/items" in url:
                # Second module succeeds but has no items
                mock_response.json.return_value = []
                mock_response.raise_for_status.return_value = None
            else:
                mock_response.json.return_value = {}
                mock_response.raise_for_status.return_value = None

            return mock_response

        mock_client.get.side_effect = mock_get_side_effect
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service.extract_content_for_modules(module_ids)

        # Should continue processing and return results for both modules
        assert len(result) == 2
        assert "module_173467" in result
        assert "module_173468" in result
        assert len(result["module_173467"]) == 0  # Failed module returns empty
        assert len(result["module_173468"]) == 0  # Empty module


@pytest.mark.asyncio
async def test_fetch_module_items_success(service: ContentExtractionService) -> None:
    """Test successful module items fetching"""
    module_id = 173467
    mock_items = [
        {"id": 1001, "type": "Page", "title": "Page 1"},
        {"id": 1002, "type": "Assignment", "title": "Assignment 1"},
    ]

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_items
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service._fetch_module_items(module_id)

        assert result == mock_items
        mock_client.get.assert_called_once_with(
            "http://canvas-mock:8001/api/v1/courses/12345/modules/173467/items",
            headers={
                "Authorization": "Bearer test_token",
                "Accept": "application/json",
            },
            timeout=30.0,
        )


@pytest.mark.asyncio
async def test_fetch_module_items_non_list_response(
    service: ContentExtractionService,
) -> None:
    """Test module items fetching with non-list response"""
    module_id = 173467

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid response"}
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service._fetch_module_items(module_id)

        assert result == []


@pytest.mark.asyncio
async def test_extract_page_content_success(service: ContentExtractionService) -> None:
    """Test successful page content extraction"""
    page_item = {
        "id": 1001,
        "type": "Page",
        "title": "Test Page",
        "page_url": "test-page",
    }

    mock_page_data = {
        "title": "Test Page",
        "body": "<h1>Test</h1><p>This is test content for extraction with enough text to pass the minimum length requirement.</p>",
        "url": "test-page",
    }

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_page_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service._extract_page_content(page_item)

        assert result is not None
        assert result["title"] == "Test Page"
        assert (
            "This is test content for extraction with enough text" in result["content"]
        )
        assert "<h1>" not in result["content"]  # HTML should be cleaned


@pytest.mark.asyncio
async def test_extract_page_content_missing_page_url(
    service: ContentExtractionService,
) -> None:
    """Test page content extraction with missing page_url"""
    page_item = {
        "id": 1001,
        "type": "Page",
        "title": "Test Page",
        # Missing page_url
    }

    result = await service._extract_page_content(page_item)
    assert result is None


@pytest.mark.asyncio
async def test_extract_page_content_empty_body(
    service: ContentExtractionService,
) -> None:
    """Test page content extraction with empty body"""
    page_item = {
        "id": 1001,
        "type": "Page",
        "title": "Test Page",
        "page_url": "empty-page",
    }

    mock_page_data = {
        "title": "Empty Page",
        "body": "",
        "url": "empty-page",
    }

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_page_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service._extract_page_content(page_item)
        assert result is None


@pytest.mark.asyncio
async def test_extract_page_content_short_content(
    service: ContentExtractionService,
) -> None:
    """Test page content extraction with content too short after cleaning"""
    page_item = {
        "id": 1001,
        "type": "Page",
        "title": "Test Page",
        "page_url": "short-page",
    }

    mock_page_data = {
        "title": "Short Page",
        "body": "<p>Short</p>",  # Too short after cleaning
        "url": "short-page",
    }

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_page_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service._extract_page_content(page_item)
        assert result is None


@pytest.mark.asyncio
async def test_fetch_page_content_success(service: ContentExtractionService) -> None:
    """Test successful page content fetching"""
    page_url = "test-page"
    mock_page_data = {
        "title": "Test Page",
        "body": "<h1>Content</h1>",
        "url": "test-page",
    }

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_page_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service._fetch_page_content(page_url)

        assert result == mock_page_data
        mock_client.get.assert_called_once_with(
            "http://canvas-mock:8001/api/v1/courses/12345/pages/test-page",
            headers={
                "Authorization": "Bearer test_token",
                "Accept": "application/json",
            },
            timeout=30.0,
        )


@pytest.mark.asyncio
async def test_fetch_page_content_special_characters(
    service: ContentExtractionService,
) -> None:
    """Test page content fetching with special characters in URL"""
    page_url = "test page with spaces & symbols"
    mock_page_data = {"title": "Test Page", "body": "<h1>Content</h1>"}

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_page_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service._fetch_page_content(page_url)

        assert result == mock_page_data
        # Verify URL encoding was applied
        expected_encoded_url = "test%20page%20with%20spaces%20%26%20symbols"
        mock_client.get.assert_called_once_with(
            f"http://canvas-mock:8001/api/v1/courses/12345/pages/{expected_encoded_url}",
            headers={
                "Authorization": "Bearer test_token",
                "Accept": "application/json",
            },
            timeout=30.0,
        )


@pytest.mark.asyncio
async def test_fetch_page_content_non_dict_response(
    service: ContentExtractionService,
) -> None:
    """Test page content fetching with non-dict response"""
    page_url = "test-page"

    with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = "invalid response"
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        result = await service._fetch_page_content(page_url)
        assert result == {}


def test_clean_html_content_comprehensive(service: ContentExtractionService) -> None:
    """Test comprehensive HTML cleaning"""
    html_content = """
    <html>
    <head>
        <title>Page Title</title>
        <style>body { color: red; }</style>
        <script>alert('test');</script>
    </head>
    <body>
        <nav class="ic-app-header">Navigation</nav>
        <div class="breadcrumbs">Home > Course</div>
        <header>Page Header</header>

        <div class="main-content">
            <h1>Main Heading</h1>
            <p>This is the main content that should be extracted.</p>

            <div class="page-toolbar">Toolbar content</div>
            <div class="main-content-area">
                <h2>Subheading</h2>
                <p>More content here.   Multiple   spaces   should   be   normalized.</p>

                <ul>
                    <li>List item 1</li>
                    <li>List item 2</li>
                </ul>
            </div>

            <!-- This is a comment -->
            <div class="ui-widget">UI Widget</div>
        </div>

        <footer>Footer content</footer>
    </body>
    </html>
    """

    result = service._clean_html_content(html_content)

    # Verify content is cleaned
    assert "Main Heading" in result
    assert "This is the main content" in result
    assert "Subheading" in result
    assert "More content here" in result
    assert "List item 1" in result
    assert "List item 2" in result

    # Verify unwanted content is removed
    assert "Navigation" not in result
    assert "Page Header" not in result
    assert "Footer content" not in result
    assert "Toolbar content" not in result
    assert "UI Widget" not in result
    assert "Home > Course" not in result
    assert "alert('test')" not in result
    assert "color: red" not in result
    assert "This is a comment" not in result

    # Verify HTML tags are removed
    assert "<h1>" not in result
    assert "<p>" not in result
    assert "<script>" not in result
    assert "<style>" not in result

    # Verify whitespace is normalized
    assert "Multiple   spaces   should" not in result
    assert "Multiple spaces should" in result


def test_clean_html_content_empty_input(service: ContentExtractionService) -> None:
    """Test HTML cleaning with empty input"""
    assert service._clean_html_content("") == ""
    # Note: _clean_html_content expects str, so we test empty string instead of None


def test_clean_html_content_canvas_elements(
    service: ContentExtractionService,
) -> None:
    """Test HTML cleaning specifically for Canvas elements"""
    html_content = """
    <div class="ic-app-nav-toggle-and-crumbs">Breadcrumbs</div>
    <div class="course-title">Course Title</div>
    <div class="right-side-wrapper">Sidebar</div>
    <div class="actual-content">
        <h1>Actual Content</h1>
        <p>This should be kept.</p>
    </div>
    <div class="mce-content-body">Editor content</div>
    <div role="navigation">Navigation role</div>
    """

    result = service._clean_html_content(html_content)

    # Should keep actual content
    assert "Actual Content" in result
    assert "This should be kept" in result

    # Should remove Canvas-specific elements
    assert "Breadcrumbs" not in result
    assert "Course Title" not in result
    assert "Sidebar" not in result
    assert "Editor content" not in result
    assert "Navigation role" not in result


def test_normalize_text_comprehensive(service: ContentExtractionService) -> None:
    """Test comprehensive text normalization"""
    input_text = """

    This   is   text   with   multiple   spaces.



    This has multiple line breaks.


    This sentence ends.Next sentence starts immediately.

    This has excessive punctuation!!!

    This has many dots......

    Multiple questions???

    """

    result = service._normalize_text(input_text)

    # Verify whitespace normalization
    assert "multiple   spaces" not in result
    assert "multiple spaces" in result

    # Verify line break normalization
    assert "\n\n\n" not in result

    # Verify sentence separation
    assert "ends.Next" not in result
    assert "ends. Next" in result

    # Verify punctuation normalization
    assert "!!!" not in result
    assert "!" in result
    assert "......" not in result
    assert "..." in result
    assert "???" not in result
    assert "?" in result


def test_normalize_text_empty_input(service: ContentExtractionService) -> None:
    """Test text normalization with empty input"""
    assert service._normalize_text("") == ""
    # Note: _normalize_text expects str, so we test empty string instead of None


def test_get_content_summary(service: ContentExtractionService) -> None:
    """Test content summary generation"""
    extracted_content = {
        "module_173467": [
            {
                "title": "Page 1",
                "content": "This is the first page with some content for testing.",
            },
            {
                "title": "Page 2",
                "content": "This is the second page with different content.",
            },
        ],
        "module_173468": [
            {
                "title": "Page 3",
                "content": "This is another page in a different module.",
            },
        ],
    }

    with patch("app.services.content_extraction.datetime") as mock_datetime:
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2023-01-15T12:30:45"
        mock_datetime.now.return_value = mock_now

        summary = service.get_content_summary(extracted_content)

        assert summary["modules_processed"] == 2
        assert summary["total_pages"] == 3
        assert summary["total_word_count"] == 26  # Total words across all pages
        assert summary["average_words_per_page"] == 8  # 26 / 3
        assert summary["extracted_at"] == "2023-01-15T12:30:45"


def test_get_content_summary_empty_content(service: ContentExtractionService) -> None:
    """Test content summary with empty content"""
    extracted_content: dict[str, list[dict[str, str]]] = {}

    summary = service.get_content_summary(extracted_content)

    assert summary["modules_processed"] == 0
    assert summary["total_pages"] == 0
    assert summary["total_word_count"] == 0
    assert summary["average_words_per_page"] == 0
    assert "extracted_at" in summary


def test_get_content_summary_zero_pages(service: ContentExtractionService) -> None:
    """Test content summary with modules but no pages"""
    extracted_content: dict[str, list[dict[str, str]]] = {
        "module_173467": [],
        "module_173468": [],
    }

    summary = service.get_content_summary(extracted_content)

    assert summary["modules_processed"] == 2
    assert summary["total_pages"] == 0
    assert summary["total_word_count"] == 0
    assert summary["average_words_per_page"] == 0
