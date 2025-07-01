# Content Extraction Domain Specification

## Overview

This specification outlines the refactoring of the monolithic `ContentExtractionService` into a functional, domain-driven architecture. The goal is to separate Canvas-specific data fetching from generic content processing, using pure functions instead of classes.

## Current State Analysis

### Problems with Existing Implementation
- **God Class**: `ContentExtractionService` (748 lines) handles too many responsibilities
- **Tight Coupling**: Canvas API logic mixed with content processing
- **Hard to Test**: Complex dependencies and side effects
- **Not Reusable**: Content processing tied to Canvas platform
- **Mixed Abstraction Levels**: HTTP requests mixed with text processing

### Current File Structure
```
src/canvas/content_extraction_service.py  # 748 lines - monolithic class
```

## Target Architecture

### Design Principles
1. **Pure Functions Only** - No classes for business logic, stateless operations
2. **Separation of Concerns** - Canvas fetching vs content processing
3. **Functional Composition** - Higher-order functions for configuration
4. **Immutable Data** - Dataclasses for data transfer
5. **Dependency Injection** - Functions passed as parameters
6. **Platform Agnostic** - Content processing independent of source

### Responsibility Split

**Canvas Module** (`src/canvas/`):
- Canvas API authentication and requests
- Fetching modules, pages, files from Canvas
- Canvas URL building and error handling
- **Provides raw content** to content extraction domain

**Content Extraction Domain** (`src/content_extraction/`):
- HTML cleaning and text extraction
- PDF text extraction
- Content validation and filtering
- Text normalization
- **Processes content** from any source

## Target File Structure

```
src/
├── content_extraction/              # New root-level domain
│   ├── __init__.py                 # Function exports
│   ├── models.py                   # Immutable dataclasses
│   ├── schemas.py                  # Pydantic request/response models
│   ├── config.py                   # Processing configuration
│   ├── constants.py                # Content types, limits
│   ├── exceptions.py               # Domain exceptions
│   ├── service.py                  # Main processing functions
│   ├── processors.py               # Content type processors
│   ├── validators.py               # Validation functions
│   ├── utils.py                    # Text processing utilities
│   └── dependencies.py             # Function composition
└── canvas/
    ├── content_extraction_service.py  # Simplified orchestrator
    └── service.py                     # Canvas API operations
```

## Data Models

### Core Data Transfer Objects

```python
@dataclass
class RawContent:
    """Raw content from any source before processing"""
    content: str                    # Raw content (HTML, PDF bytes, text)
    content_type: str              # "html", "pdf", "text"
    title: str                     # Content title
    metadata: dict = field(default_factory=dict)  # Source-specific metadata

@dataclass
class ProcessedContent:
    """Cleaned, processed content ready for consumption"""
    title: str                     # Content title
    content: str                   # Cleaned text content
    word_count: int               # Estimated word count
    content_type: str             # Always "text" after processing
    processing_metadata: dict     # Processing stats and info
```

### Pydantic Schemas

```python
class ContentProcessingRequest(BaseModel):
    """Request for content processing"""
    raw_contents: list[RawContent]
    options: ProcessingOptions = ProcessingOptions()

class ProcessingOptions(BaseModel):
    """Processing configuration options"""
    max_content_length: int = 50000
    min_content_length: int = 50
    include_metadata: bool = True

class ContentProcessingResponse(BaseModel):
    """Response from content processing"""
    processed_contents: list[ProcessedContent]
    summary: ProcessingSummary
    errors: list[str]
```

## Core Functions Specification

### Main Processing Functions (`service.py`)

```python
async def process_content(
    raw_content: RawContent,
    processor_func: ProcessorFunc,
    validator_func: ValidatorFunc | None = None
) -> ProcessedContent | None:
    """
    Process a single content item using provided functions.

    Args:
        raw_content: Content to process
        processor_func: Function to process the content
        validator_func: Optional validation function

    Returns:
        Processed content or None if processing fails

    Properties:
        - Pure function (no side effects)
        - Same input always produces same output
        - Error handling returns None rather than raising
    """

async def process_content_batch(
    raw_contents: list[RawContent],
    get_processor: Callable[[str], ProcessorFunc],
    validator_func: ValidatorFunc | None = None
) -> list[ProcessedContent]:
    """
    Process multiple content items using appropriate processors.

    Args:
        raw_contents: List of content to process
        get_processor: Function that returns processor for content type
        validator_func: Optional validation function

    Returns:
        List of successfully processed content

    Properties:
        - Processes items independently
        - Failures don't affect other items
        - Uses appropriate processor for each content type
    """

def create_processor_selector() -> Callable[[str], ProcessorFunc]:
    """
    Factory function that returns a processor selector.

    Returns:
        Function that maps content types to processor functions

    Properties:
        - Creates mapping of content_type -> processor function
        - Raises UnsupportedFormatError for unknown types
        - Configurable processor mapping
    """
```

### Content Processors (`processors.py`)

```python
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
        ProcessedContent with cleaned text or None if invalid
    """

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
        ProcessedContent with normalized text or None if invalid
    """
```

### Validation Functions (`validators.py`)

```python
def is_valid_content_size(raw_content: RawContent) -> bool:
    """Check if raw content size is within limits."""

def is_valid_content_length(text: str) -> bool:
    """Check if processed text meets length requirements."""

def is_supported_content_type(content_type: str) -> bool:
    """Check if content type is supported for processing."""

def create_content_validator() -> Callable[[RawContent], bool]:
    """Create a composite validator function with all validation rules."""
```

### Utility Functions (`utils.py`)

```python
def clean_html_content(html: str) -> str:
    """
    Clean HTML content and extract readable text.

    Removes:
    - HTML tags and attributes
    - Scripts and styles
    - Comments and navigation elements
    - Canvas-specific UI elements
    - Excessive whitespace

    Returns clean text suitable for LLM processing.
    """

def normalize_text(text: str) -> str:
    """
    Normalize text formatting and whitespace.

    Operations:
    - Replace multiple whitespace with single spaces
    - Remove leading/trailing whitespace
    - Remove empty lines
    - Ensure proper sentence separation
    - Limit excessive punctuation
    """

def estimate_word_count(text: str) -> int:
    """Estimate word count in text using simple split method."""

def extract_pdf_text(pdf_content: bytes) -> str:
    """
    Extract text from PDF bytes using pypdf.

    Operations:
    - Create PDF reader from bytes
    - Extract text from all pages
    - Handle page extraction errors gracefully
    - Join pages with proper spacing
    - Clean excessive whitespace
    """
```

## Configuration and Constants

### Configuration (`config.py`)

```python
class ContentExtractionSettings(BaseSettings):
    """Content extraction processing configuration."""

    # Content size limits
    MAX_CONTENT_SIZE: int = 1024 * 1024  # 1MB per item
    MAX_TOTAL_CONTENT_SIZE: int = 50 * 1024 * 1024  # 50MB total
    MAX_CONTENT_LENGTH: int = 50000  # Max processed text length
    MIN_CONTENT_LENGTH: int = 50     # Min processed text length

    # File processing
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB per file
    SUPPORTED_FORMATS: list[str] = ["html", "pdf", "text"]

    # Processing timeouts
    PROCESSING_TIMEOUT: int = 30

    class Config:
        env_prefix = "CONTENT_EXTRACTION_"
```

### Constants (`constants.py`)

```python
# Supported content types
SUPPORTED_CONTENT_TYPES = [
    "text/html",
    "application/pdf",
    "text/plain"
]

# Processing status
class ProcessingStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Content type mappings
CONTENT_TYPE_MAPPINGS = {
    "text/html": "html",
    "application/pdf": "pdf",
    "text/plain": "text",
    "pdf": "pdf"  # Alternative format
}

# Size limits
MAX_PAGE_CONTENT_SIZE = 1024 * 1024  # 1MB
MAX_TOTAL_CONTENT_SIZE = 50 * 1024 * 1024  # 50MB
```

## Canvas Integration

### Simplified Canvas Service (`canvas/content_extraction_service.py`)

```python
class ContentExtractionService:
    """Canvas-specific content extraction orchestrator."""

    def __init__(self, canvas_token: str, course_id: int):
        self.canvas_service = CanvasService(canvas_token, course_id)
        self.process_contents = get_content_processor()  # Function from content_extraction

    async def extract_content_for_modules(self, module_ids: list[int]) -> dict[str, list[ProcessedContent]]:
        """
        Main orchestration: Canvas fetching + content processing.

        Flow:
        1. Fetch module items from Canvas API
        2. Convert Canvas data to RawContent objects
        3. Delegate processing to content_extraction domain
        4. Return processed results
        """
```

### Canvas API Service (`canvas/service.py`)

```python
class CanvasService:
    """Pure Canvas API operations."""

    async def fetch_module_items(self, module_id: int) -> list[dict]:
        """Fetch Canvas module items with retry logic."""

    async def fetch_page_content(self, page_url: str) -> dict:
        """Fetch Canvas page content."""

    async def fetch_file_content(self, file_id: int) -> FileData:
        """Fetch Canvas file content and metadata."""
```

## Function Composition (`dependencies.py`)

```python
def get_content_processor() -> Callable:
    """
    Create configured content processor function.

    Returns:
        Async function that processes list[RawContent] -> list[ProcessedContent]
    """

def get_single_content_processor() -> Callable:
    """
    Create single content processor function.

    Returns:
        Async function that processes RawContent -> ProcessedContent | None
    """
```

## Error Handling

### Exception Hierarchy

```python
class ContentExtractionError(Exception):
    """Base content extraction exception."""

class UnsupportedFormatError(ContentExtractionError):
    """Content format not supported for processing."""

class ContentTooLargeError(ContentExtractionError):
    """Content exceeds size limits."""

class ProcessingFailedError(ContentExtractionError):
    """Content processing failed due to technical error."""

class ValidationError(ContentExtractionError):
    """Content failed validation rules."""
```

### Error Handling Strategy

1. **Graceful Degradation** - Process what you can, skip failures
2. **No Exceptions in Processing** - Return None for failures
3. **Comprehensive Logging** - Log all errors with context
4. **Preserve Partial Results** - Don't fail entire batch for single item failure

## Migration Strategy

### Phase 1: Create Domain Structure
1. Create `src/content_extraction/` directory
2. Set up all module files with basic structure
3. Define data models and schemas
4. Create configuration and constants

### Phase 2: Extract Utility Functions
1. Move HTML cleaning logic from current service to `utils.py`
2. Move PDF extraction logic to `utils.py`
3. Move text normalization to `utils.py`
4. Create pure functions with no dependencies

### Phase 3: Create Processing Functions
1. Implement content processors in `processors.py`
2. Implement validation functions in `validators.py`
3. Create main service functions in `service.py`
4. Set up function composition in `dependencies.py`

### Phase 4: Refactor Canvas Integration
1. Extract Canvas API operations to `canvas/service.py`
2. Simplify `canvas/content_extraction_service.py` to orchestrator
3. Update Canvas service to use content_extraction functions
4. Ensure API compatibility

### Phase 5: Testing and Validation
1. Create comprehensive unit tests for pure functions
2. Integration tests for Canvas orchestration
3. Performance testing for batch processing
4. Validate API compatibility

### Phase 6: Cleanup
1. Remove old monolithic content extraction code
2. Update imports throughout codebase
3. Update documentation
4. Remove unused dependencies

## Testing Strategy

### Unit Testing Pure Functions

```python
def test_process_html_content():
    """Test HTML content processing."""
    raw = RawContent(
        content="<p>Hello <b>world</b></p>",
        content_type="html",
        title="Test"
    )
    result = process_html_content(raw)

    assert result is not None
    assert result.content == "Hello world"
    assert result.word_count == 2
    assert result.content_type == "text"

def test_clean_html_content():
    """Test HTML cleaning utility."""
    html = "<p>Hello</p><script>alert('hi')</script>"
    result = clean_html_content(html)
    assert result == "Hello"
    assert "script" not in result
```

### Integration Testing

```python
async def test_canvas_content_extraction_integration():
    """Test full Canvas content extraction flow."""
    service = ContentExtractionService(token, course_id)
    result = await service.extract_content_for_modules([123])

    assert isinstance(result, dict)
    assert "module_123" in result
    assert all(isinstance(item, ProcessedContent) for item in result["module_123"])
```

## Performance Considerations

### Memory Management
- Process content in batches to limit memory usage
- Use generators for large content sets
- Proper cleanup of PDF readers and HTML parsers

### Concurrency
- Functions are pure and thread-safe
- Can process multiple items concurrently
- Async/await for I/O operations

### Caching
- Results can be cached since functions are pure
- Content fingerprinting for cache keys
- TTL-based cache expiration

## Security Considerations

### Content Validation
- Size limits to prevent memory exhaustion
- Content type validation
- Input sanitization for HTML processing

### Resource Limits
- Processing timeouts
- Memory usage limits
- File size restrictions

## Success Criteria

1. **Functional Implementation** - All processing uses pure functions
2. **Platform Independence** - Content processing works with any data source
3. **API Compatibility** - Existing Canvas endpoints continue working
4. **Performance** - No degradation in processing speed
5. **Testability** - 100% unit test coverage for pure functions
6. **Maintainability** - Code is easier to understand and modify
7. **Extensibility** - Easy to add new content types and processors

## Future Enhancements

### Additional Content Types
- Image text extraction (OCR)
- Video transcript extraction
- Audio transcript processing
- Microsoft Office documents

### Additional Data Sources
- Direct file uploads
- Web scraping
- Google Drive integration
- Other LMS platforms (Moodle, Blackboard)

### Advanced Processing
- Content deduplication
- Language detection
- Content summarization
- Semantic chunking for LLMs

This specification provides a comprehensive guide for implementing the functional content extraction domain while maintaining clean architecture principles and ensuring robust, testable code.
