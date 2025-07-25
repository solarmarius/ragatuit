# 3. Hardcoded API URLs in Content Extraction

## Priority: High

**Estimated Effort**: 1 day
**Python Version**: 3.10+
**Dependencies**: None

## Problem Statement

### Current Situation

The `ContentExtractionService` contains a hardcoded Canvas API URL (`http://canvas-mock:8001/api/v1`) on line 31, making the service environment-specific and untestable in different environments.

### Why It's a Problem

- **Environment Coupling**: Service only works with mock Canvas
- **Testing Difficulties**: Cannot test against different endpoints
- **Deployment Issues**: Requires code changes for different environments
- **Security**: Hardcoded URLs can expose internal infrastructure
- **Maintainability**: URL changes require code modifications

### Affected Modules

- `app/services/content_extraction.py` (line 31)
- All content extraction operations
- Canvas API interactions
- Testing infrastructure

### Technical Debt Assessment

- **Risk Level**: High - Blocks production deployment
- **Impact**: All Canvas content operations
- **Cost of Delay**: Increases with each environment

## Current Implementation Analysis

```python
# File: app/services/content_extraction.py (lines 20-35)
class ContentExtractionService:
    """
    Service for extracting and cleaning content from Canvas pages.
    """

    def __init__(self, canvas_token: str, course_id: int):
        self.canvas_token = canvas_token
        self.course_id = course_id
        # PROBLEM: Hardcoded URL!
        self.canvas_base_url = "http://canvas-mock:8001/api/v1"
        self.total_content_size = 0

        # Load configuration settings
        self.max_file_size = settings.MAX_FILE_SIZE
        # ... more settings
```

### Python Anti-patterns Identified

- **Hardcoded Values**: Environment-specific URL in code
- **Missing Abstraction**: No configuration injection
- **Tight Coupling**: Service tied to specific environment
- **No URL Validation**: Accepts any string without validation

## Proposed Solution

### Pythonic Approach

Use dependency injection with URL validation, environment-based configuration, and proper URL construction utilities.

### Design Patterns

- **Dependency Injection**: Inject configuration
- **Builder Pattern**: For URL construction
- **Strategy Pattern**: For environment-specific behavior

### Code Examples

```python
# File: app/core/config.py (UPDATE)
from pydantic import HttpUrl, validator
from typing import Optional

class Settings(BaseSettings):
    # ... existing settings ...

    # Canvas API configuration
    CANVAS_BASE_URL: HttpUrl
    CANVAS_API_VERSION: str = "v1"

    # Mock Canvas URL for testing
    CANVAS_MOCK_URL: Optional[HttpUrl] = None
    USE_CANVAS_MOCK: bool = False

    @validator('CANVAS_BASE_URL')
    def validate_canvas_url(cls, v: HttpUrl) -> HttpUrl:
        """Ensure Canvas URL doesn't include API path."""
        url_str = str(v)
        if '/api' in url_str:
            raise ValueError("CANVAS_BASE_URL should not include /api path")
        return v

    @computed_field
    @property
    def canvas_api_url(self) -> str:
        """Get full Canvas API URL."""
        base = str(self.CANVAS_MOCK_URL if self.USE_CANVAS_MOCK and self.CANVAS_MOCK_URL else self.CANVAS_BASE_URL)
        return f"{base.rstrip('/')}/api/{self.CANVAS_API_VERSION}"

# File: app/services/url_builder.py (NEW)
from urllib.parse import urljoin, urlparse, quote
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class CanvasURLBuilder:
    """
    Builder for Canvas API URLs with proper encoding and validation.
    """

    def __init__(self, base_url: str, api_version: str = "v1"):
        """
        Initialize URL builder.

        Args:
            base_url: Canvas instance base URL
            api_version: API version (default: v1)

        Raises:
            ValueError: If base_url is invalid
        """
        self.base_url = self._validate_url(base_url)
        self.api_version = api_version
        self.api_base = f"{self.base_url}/api/{api_version}"

    def _validate_url(self, url: str) -> str:
        """Validate and normalize URL."""
        if not url:
            raise ValueError("Base URL cannot be empty")

        # Parse URL to ensure it's valid
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        # Ensure HTTPS in production
        if parsed.scheme != "https" and "localhost" not in parsed.netloc:
            logger.warning(
                "canvas_url_not_https",
                url=url
            )

        return url.rstrip('/')

    def courses(self, course_id: int) -> str:
        """Build course URL."""
        return f"{self.api_base}/courses/{course_id}"

    def modules(self, course_id: int, module_id: Optional[int] = None) -> str:
        """Build modules URL."""
        base = f"{self.courses(course_id)}/modules"
        return f"{base}/{module_id}" if module_id else base

    def module_items(self, course_id: int, module_id: int) -> str:
        """Build module items URL."""
        return f"{self.modules(course_id, module_id)}/items"

    def pages(self, course_id: int, page_url: Optional[str] = None) -> str:
        """Build pages URL with proper encoding."""
        base = f"{self.courses(course_id)}/pages"
        if page_url:
            encoded_url = quote(page_url.strip(), safe='')
            return f"{base}/{encoded_url}"
        return base

    def files(self, course_id: int, file_id: Optional[int] = None) -> str:
        """Build files URL."""
        base = f"{self.courses(course_id)}/files"
        return f"{base}/{file_id}" if file_id else base

    def build_url(self, *parts: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Build arbitrary API URL.

        Args:
            *parts: URL path parts
            params: Query parameters

        Returns:
            Complete URL
        """
        # Join parts with /
        path = '/'.join(str(p).strip('/') for p in parts)
        url = f"{self.api_base}/{path}"

        # Add query parameters if provided
        if params:
            from urllib.parse import urlencode
            query_string = urlencode(params)
            url = f"{url}?{query_string}"

        return url

# File: app/services/content_extraction.py (UPDATED)
from typing import Optional
from app.services.url_builder import CanvasURLBuilder
from app.core.config import settings

class ContentExtractionService:
    """
    Service for extracting and cleaning content from Canvas pages.

    This service handles fetching module items, extracting page content,
    and cleaning HTML to produce text suitable for LLM consumption.
    """

    def __init__(
        self,
        canvas_token: str,
        course_id: int,
        canvas_base_url: Optional[str] = None,
        api_version: str = "v1"
    ):
        """
        Initialize content extraction service.

        Args:
            canvas_token: Canvas API access token
            course_id: Canvas course ID
            canvas_base_url: Optional Canvas base URL (defaults to settings)
            api_version: Canvas API version (default: v1)
        """
        self.canvas_token = canvas_token
        self.course_id = course_id
        self.total_content_size = 0

        # Initialize URL builder with proper configuration
        base_url = canvas_base_url or settings.canvas_api_url.replace(f'/api/{settings.CANVAS_API_VERSION}', '')
        self.url_builder = CanvasURLBuilder(base_url, api_version)

        # Log configuration for debugging
        logger.info(
            "content_extraction_service_initialized",
            course_id=course_id,
            base_url=base_url,
            api_version=api_version
        )

        # Load configuration settings
        self._load_settings()

    def _load_settings(self):
        """Load configuration settings."""
        self.max_file_size = settings.MAX_FILE_SIZE
        self.max_total_content_size = settings.MAX_TOTAL_CONTENT_SIZE
        self.max_pages_per_module = settings.MAX_PAGES_PER_MODULE
        self.max_content_length = settings.MAX_CONTENT_LENGTH
        self.min_content_length = settings.MIN_CONTENT_LENGTH
        self.api_timeout = settings.CANVAS_API_TIMEOUT
        self.max_retries = settings.MAX_RETRIES
        self.initial_retry_delay = settings.INITIAL_RETRY_DELAY
        self.max_retry_delay = settings.MAX_RETRY_DELAY
        self.retry_backoff_factor = settings.RETRY_BACKOFF_FACTOR

    async def _fetch_module_items(self, module_id: int) -> list[dict[str, Any]]:
        """Fetch items from a Canvas module."""
        url = self.url_builder.module_items(self.course_id, module_id)
        headers = {
            "Authorization": f"Bearer {self.canvas_token}",
            "Accept": "application/json",
        }

        try:
            result = await self._make_request_with_retry(url, headers)
            # Handle response...

    async def _fetch_page_content(self, page_url: str) -> dict[str, Any]:
        """Fetch content of a specific Canvas page."""
        url = self.url_builder.pages(self.course_id, page_url)
        # ... rest of implementation

# File: app/services/canvas_factory.py (NEW)
from typing import Optional
from app.core.config import settings
from app.services.content_extraction import ContentExtractionService
from app.services.canvas_quiz_export import CanvasQuizExportService

class CanvasServiceFactory:
    """
    Factory for creating Canvas services with proper configuration.
    """

    @staticmethod
    def create_content_extraction_service(
        canvas_token: str,
        course_id: int,
        use_mock: Optional[bool] = None
    ) -> ContentExtractionService:
        """
        Create content extraction service.

        Args:
            canvas_token: Canvas API token
            course_id: Course ID
            use_mock: Override mock setting (for testing)

        Returns:
            Configured ContentExtractionService
        """
        # Determine which URL to use
        if use_mock is None:
            use_mock = settings.USE_CANVAS_MOCK

        if use_mock and settings.CANVAS_MOCK_URL:
            base_url = str(settings.CANVAS_MOCK_URL)
        else:
            base_url = str(settings.CANVAS_BASE_URL)

        return ContentExtractionService(
            canvas_token=canvas_token,
            course_id=course_id,
            canvas_base_url=base_url
        )

    @staticmethod
    def create_quiz_export_service(
        canvas_token: str,
        use_mock: Optional[bool] = None
    ) -> CanvasQuizExportService:
        """Create quiz export service with proper URL."""
        # Similar implementation...
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   └── config.py                # UPDATE: Add Canvas URLs
│   ├── services/
│   │   ├── url_builder.py          # NEW: URL construction
│   │   ├── content_extraction.py   # UPDATE: Remove hardcoded URL
│   │   ├── canvas_quiz_export.py   # UPDATE: Use URL builder
│   │   └── canvas_factory.py       # NEW: Service factory
│   ├── api/
│   │   └── routes/
│   │       └── quiz.py             # UPDATE: Use factory
│   └── tests/
│       └── services/
│           └── test_url_builder.py  # NEW: URL builder tests
```

### Configuration Changes

```bash
# .env updates
CANVAS_BASE_URL=https://canvas.institution.edu
CANVAS_API_VERSION=v1
CANVAS_MOCK_URL=http://localhost:8001
USE_CANVAS_MOCK=false  # true for local development
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/services/test_url_builder.py
import pytest
from app.services.url_builder import CanvasURLBuilder

class TestCanvasURLBuilder:
    def test_init_valid_url(self):
        """Test initialization with valid URL."""
        builder = CanvasURLBuilder("https://canvas.test.com")
        assert builder.base_url == "https://canvas.test.com"
        assert builder.api_base == "https://canvas.test.com/api/v1"

    def test_init_invalid_url(self):
        """Test initialization with invalid URL."""
        with pytest.raises(ValueError, match="Invalid URL"):
            CanvasURLBuilder("not-a-url")

    def test_init_empty_url(self):
        """Test initialization with empty URL."""
        with pytest.raises(ValueError, match="Base URL cannot be empty"):
            CanvasURLBuilder("")

    def test_courses_url(self):
        """Test course URL generation."""
        builder = CanvasURLBuilder("https://canvas.test.com")
        assert builder.courses(123) == "https://canvas.test.com/api/v1/courses/123"

    def test_pages_url_encoding(self):
        """Test page URL with special characters."""
        builder = CanvasURLBuilder("https://canvas.test.com")
        page_url = "page with spaces & special"
        expected = "https://canvas.test.com/api/v1/courses/123/pages/page%20with%20spaces%20%26%20special"
        assert builder.pages(123, page_url) == expected

    def test_build_url_with_params(self):
        """Test arbitrary URL building with parameters."""
        builder = CanvasURLBuilder("https://canvas.test.com")
        url = builder.build_url("custom", "path", params={"per_page": 50, "page": 2})
        assert url == "https://canvas.test.com/api/v1/custom/path?per_page=50&page=2"

# File: app/tests/services/test_content_extraction.py
@pytest.fixture
def mock_canvas_service(monkeypatch):
    """Mock Canvas service with test URL."""
    monkeypatch.setenv("CANVAS_BASE_URL", "https://test.canvas.com")
    monkeypatch.setenv("USE_CANVAS_MOCK", "true")
    monkeypatch.setenv("CANVAS_MOCK_URL", "http://mock.canvas.local")

def test_content_extraction_service_init_default():
    """Test service initialization with default settings."""
    service = ContentExtractionService("token", 123)
    assert service.course_id == 123
    assert service.canvas_token == "token"
    # URL builder should use settings

def test_content_extraction_service_init_custom_url():
    """Test service initialization with custom URL."""
    service = ContentExtractionService(
        "token",
        123,
        canvas_base_url="https://custom.canvas.com"
    )
    assert "custom.canvas.com" in service.url_builder.base_url

# File: app/tests/integration/test_canvas_services.py
@pytest.mark.integration
async def test_canvas_factory_mock_mode():
    """Test factory creates services in mock mode."""
    with patch.dict(os.environ, {"USE_CANVAS_MOCK": "true"}):
        service = CanvasServiceFactory.create_content_extraction_service(
            "token", 123
        )
        # Should use mock URL
        assert "mock" in service.url_builder.base_url
```

### Integration Tests

```python
# Test against real Canvas API (in staging)
@pytest.mark.skipif(
    not os.getenv("CANVAS_TEST_TOKEN"),
    reason="Canvas test token not available"
)
async def test_real_canvas_api():
    """Test against real Canvas API."""
    service = ContentExtractionService(
        os.getenv("CANVAS_TEST_TOKEN"),
        int(os.getenv("CANVAS_TEST_COURSE_ID")),
        canvas_base_url=os.getenv("CANVAS_TEST_URL")
    )

    # Test actual API call
    modules = await service.extract_content_for_modules([123])
    assert isinstance(modules, dict)
```

## Code Quality Improvements

### Type Safety

```python
# Add type stubs for URL builder
from typing import Protocol

class URLBuilderProtocol(Protocol):
    """Protocol for URL builders."""
    def courses(self, course_id: int) -> str: ...
    def modules(self, course_id: int, module_id: Optional[int] = None) -> str: ...
    def pages(self, course_id: int, page_url: Optional[str] = None) -> str: ...
```

### Configuration Validation

```python
# Startup validation
@app.on_event("startup")
async def validate_canvas_config():
    """Validate Canvas configuration on startup."""
    try:
        # Test URL construction
        builder = CanvasURLBuilder(settings.CANVAS_BASE_URL)
        test_url = builder.courses(1)
        logger.info("canvas_config_valid", test_url=test_url)
    except Exception as e:
        logger.error("canvas_config_invalid", error=str(e))
        raise
```

## Migration Strategy

### Environment-Specific Configuration

```python
# config/environments/development.py
CANVAS_BASE_URL = "http://localhost:8001"
USE_CANVAS_MOCK = True

# config/environments/production.py
CANVAS_BASE_URL = "https://canvas.institution.edu"
USE_CANVAS_MOCK = False
```

### Feature Flag for Gradual Rollout

```python
if settings.USE_NEW_CANVAS_URL_BUILDER:
    service = ContentExtractionService(token, course_id)
else:
    # Legacy with hardcoded URL
    service = LegacyContentExtractionService(token, course_id)
```

## Success Criteria

### Verification Steps

1. All tests pass with mock Canvas URL
2. Integration tests pass with real Canvas API
3. No hardcoded URLs in codebase (`grep -r "canvas-mock" app/`)
4. Service works in all environments

### Performance Metrics

- No performance regression
- URL construction < 1ms
- Same API response times

---
