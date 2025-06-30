import pytest

from app.canvas.url_builder import CanvasURLBuilder


@pytest.fixture
def builder() -> CanvasURLBuilder:
    """Create a CanvasURLBuilder instance for testing."""
    return CanvasURLBuilder("https://canvas.test.com")


@pytest.fixture
def mock_builder() -> CanvasURLBuilder:
    """Create a CanvasURLBuilder instance with mock URL for testing."""
    return CanvasURLBuilder("http://canvas-mock:8001")


def test_init_valid_url() -> None:
    """Test initialization with valid URL."""
    builder = CanvasURLBuilder("https://canvas.test.com")
    assert builder.base_url == "https://canvas.test.com"
    assert builder.api_base == "https://canvas.test.com/api/v1"


def test_init_valid_url_with_trailing_slash() -> None:
    """Test initialization with valid URL that has trailing slash."""
    builder = CanvasURLBuilder("https://canvas.test.com/")
    assert builder.base_url == "https://canvas.test.com"
    assert builder.api_base == "https://canvas.test.com/api/v1"


def test_init_with_custom_api_version() -> None:
    """Test initialization with custom API version."""
    builder = CanvasURLBuilder("https://canvas.test.com", api_version="v2")
    assert builder.api_version == "v2"
    assert builder.api_base == "https://canvas.test.com/api/v2"


def test_init_invalid_url() -> None:
    """Test initialization with invalid URL."""
    with pytest.raises(ValueError, match="Invalid URL"):
        CanvasURLBuilder("not-a-url")


def test_init_empty_url() -> None:
    """Test initialization with empty URL."""
    with pytest.raises(ValueError, match="Base URL cannot be empty"):
        CanvasURLBuilder("")


def test_init_url_without_scheme() -> None:
    """Test initialization with URL missing scheme."""
    with pytest.raises(ValueError, match="Invalid URL"):
        CanvasURLBuilder("canvas.test.com")


def test_courses_url(builder: CanvasURLBuilder) -> None:
    """Test course URL generation."""
    assert builder.courses(123) == "https://canvas.test.com/api/v1/courses/123"


def test_modules_url_without_module_id(builder: CanvasURLBuilder) -> None:
    """Test modules URL generation without module ID."""
    assert builder.modules(123) == "https://canvas.test.com/api/v1/courses/123/modules"


def test_modules_url_with_module_id(builder: CanvasURLBuilder) -> None:
    """Test modules URL generation with module ID."""
    assert (
        builder.modules(123, 456)
        == "https://canvas.test.com/api/v1/courses/123/modules/456"
    )


def test_module_items_url(builder: CanvasURLBuilder) -> None:
    """Test module items URL generation."""
    assert (
        builder.module_items(123, 456)
        == "https://canvas.test.com/api/v1/courses/123/modules/456/items"
    )


def test_pages_url_without_page_url(builder: CanvasURLBuilder) -> None:
    """Test pages URL generation without page URL."""
    assert builder.pages(123) == "https://canvas.test.com/api/v1/courses/123/pages"


def test_pages_url_with_simple_page_url(builder: CanvasURLBuilder) -> None:
    """Test pages URL generation with simple page URL."""
    assert (
        builder.pages(123, "introduction")
        == "https://canvas.test.com/api/v1/courses/123/pages/introduction"
    )


def test_pages_url_encoding(builder: CanvasURLBuilder) -> None:
    """Test page URL with special characters."""
    page_url = "page with spaces & special"
    expected = "https://canvas.test.com/api/v1/courses/123/pages/page%20with%20spaces%20%26%20special"
    assert builder.pages(123, page_url) == expected


def test_pages_url_with_complex_encoding(builder: CanvasURLBuilder) -> None:
    """Test page URL with various special characters."""
    page_url = "page/with/slashes?and=query&params"
    expected = "https://canvas.test.com/api/v1/courses/123/pages/page%2Fwith%2Fslashes%3Fand%3Dquery%26params"
    assert builder.pages(123, page_url) == expected


def test_files_url_without_file_id(builder: CanvasURLBuilder) -> None:
    """Test files URL generation without file ID."""
    assert builder.files(123) == "https://canvas.test.com/api/v1/courses/123/files"


def test_files_url_with_file_id(builder: CanvasURLBuilder) -> None:
    """Test files URL generation with file ID."""
    assert (
        builder.files(123, 789)
        == "https://canvas.test.com/api/v1/courses/123/files/789"
    )


def test_build_url_simple(builder: CanvasURLBuilder) -> None:
    """Test arbitrary URL building with simple path."""
    url = builder.build_url("custom", "path")
    assert url == "https://canvas.test.com/api/v1/custom/path"


def test_build_url_with_params(builder: CanvasURLBuilder) -> None:
    """Test arbitrary URL building with parameters."""
    url = builder.build_url("custom", "path", params={"per_page": 50, "page": 2})
    assert url == "https://canvas.test.com/api/v1/custom/path?per_page=50&page=2"


def test_build_url_strips_slashes(builder: CanvasURLBuilder) -> None:
    """Test that build_url properly strips slashes from parts."""
    url = builder.build_url("/custom/", "/path/")
    assert url == "https://canvas.test.com/api/v1/custom/path"


def test_oauth_token_url(builder: CanvasURLBuilder) -> None:
    """Test OAuth token URL generation."""
    assert builder.oauth_token_url() == "https://canvas.test.com/login/oauth2/token"


def test_http_url_with_localhost() -> None:
    """Test that HTTP is allowed for localhost."""
    builder = CanvasURLBuilder("http://localhost:8001")
    assert builder.base_url == "http://localhost:8001"
    assert builder.api_base == "http://localhost:8001/api/v1"


def test_mock_canvas_url(mock_builder: CanvasURLBuilder) -> None:
    """Test with canvas-mock URL."""
    assert mock_builder.base_url == "http://canvas-mock:8001"
    assert mock_builder.api_base == "http://canvas-mock:8001/api/v1"
