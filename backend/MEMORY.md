# Claude Code Session Memory

## Task Overview
Refactoring the monolithic `ContentExtractionService` (748 lines) into a functional, domain-driven architecture using pure functions instead of classes.

## Completed Work

### 1. ✅ Content Extraction Domain Created (Root Level)
Successfully created a new root-level domain `src/content_extraction/` with functional architecture:

**Files Created:**
- `__init__.py` - Domain exports (RawContent, ProcessedContent, get_content_processor, etc.)
- `models.py` - Immutable dataclasses (RawContent, ProcessedContent, ProcessingSummary)
- `config.py` - Domain configuration (ContentExtractionSettings with size limits, timeouts)
- `constants.py` - Content types, processing status, Canvas UI selectors, HTML elements
- `exceptions.py` - Domain exceptions (ContentExtractionError, UnsupportedFormatError, etc.)
- `utils.py` - **Pure utility functions** extracted from original service:
  - `clean_html_content()` - HTML cleaning with BeautifulSoup
  - `normalize_text()` - Text normalization and formatting
  - `extract_pdf_text()` - PDF text extraction using pypdf
  - `estimate_word_count()`, `truncate_content()`, `validate_text_content()`
- `validators.py` - **Pure validation functions**:
  - `is_valid_content_size()`, `is_valid_content_length()`, `is_supported_content_type()`
  - `create_content_validator()` - Factory function for composite validation
- `processors.py` - **Content type processors as pure functions**:
  - `process_html_content()` - HTML → clean text
  - `process_pdf_content()` - PDF → clean text
  - `process_text_content()` - Text normalization
  - `CONTENT_PROCESSORS` - Mapping for factory pattern
- `service.py` - **Main service functions**:
  - `process_content()` - Single content processing with validation
  - `process_content_batch()` - Batch processing with error handling
  - `create_processor_selector()` - Factory for processor selection
- `dependencies.py` - **Function composition**:
  - `get_content_processor()` - Configured batch processor
  - `get_single_content_processor()` - Single item processor

### 2. ✅ Canvas API Service Refactored (Functional)
Refactored Canvas API operations to use pure functions in `src/canvas/service.py`:

**Functions Created:**
- `_get_canvas_url_builder()` - Helper for URL building
- `_get_canvas_headers()` - Helper for request headers
- `fetch_canvas_module_items()` - Fetch Canvas module items with @retry_on_failure
- `fetch_canvas_page_content()` - Fetch Canvas page content with @retry_on_failure
- `fetch_canvas_file_info()` - Fetch Canvas file metadata with @retry_on_failure
- `download_canvas_file_content()` - Download file content with @retry_on_failure

**Key Changes:**
- Removed class-based `CanvasAPIService` → Pure functions
- Removed manual `_make_request_with_retry()` → Used `@retry_on_failure` decorator
- All functions are stateless and take parameters explicitly
- Each function handles its own error cases and logging

### 3. ✅ Architecture Principles Achieved
- **Pure Functions Only** - No classes for business logic, stateless operations
- **Separation of Concerns** - Canvas fetches data, content_extraction processes it
- **Immutable Data Flow** - RawContent → processors → ProcessedContent
- **Function Composition** - Higher-order functions for configuration
- **Domain Independence** - Content processing works with any data source

## Data Flow Design
```
[Canvas API] → [Canvas Functions] → [RawContent] → [Content Extraction Functions] → [ProcessedContent]
     ↓              ↓                    ↓                     ↓                           ↓
  Canvas API    Canvas-specific      Generic data         Pure processing            Clean text
   requests      data fetching        transfer             functions                 ready for LLM
```

## Current State

### ✅ Completed
1. **Content extraction domain** - Fully functional with pure functions
2. **Canvas API functions** - Refactored to pure functions with retry decorators
3. **Data models** - Immutable dataclasses for data transfer
4. **Validation & processing** - Pure functions for all content types
5. **Function composition** - Dependency injection through parameters

### 🚧 In Progress
**Next Step: Refactor `ContentExtractionService` class to use new domain**

The original `ContentExtractionService` class (748 lines) in `src/canvas/content_extraction_service.py` needs to be refactored to:
1. Use the new Canvas API functions from `canvas/service.py`
2. Use the new content extraction domain functions
3. Maintain the same public API: `extract_content_for_modules(module_ids) -> dict[str, list[dict]]`

### Key Integration Points
1. **Canvas Functions to Use:**
   - `fetch_canvas_module_items(canvas_token, course_id, module_id)`
   - `fetch_canvas_page_content(canvas_token, course_id, page_url)`
   - `fetch_canvas_file_info(canvas_token, course_id, file_id)`
   - `download_canvas_file_content(download_url)`

2. **Content Extraction Functions to Use:**
   - `get_content_processor()` - Returns batch processing function
   - Create `RawContent` objects from Canvas data
   - Process with content extraction domain
   - Convert `ProcessedContent` back to legacy dict format

## Implementation Strategy for Next Steps

### Refactor ContentExtractionService Class
1. **Replace internal methods** with calls to new functions
2. **Maintain API compatibility** - Same method signature and return format
3. **Data conversion flow:**
   ```python
   # Canvas fetching
   canvas_items = await fetch_canvas_module_items(token, course_id, module_id)

   # Convert to RawContent
   raw_contents = []
   for item in canvas_items:
       if item["type"] == "Page":
           page_data = await fetch_canvas_page_content(token, course_id, item["page_url"])
           raw_contents.append(RawContent(
               content=page_data.get("body", ""),
               content_type="html",
               title=page_data.get("title", ""),
               metadata={"source": "canvas_page"}
           ))

   # Process with content extraction domain
   process_contents = get_content_processor()
   processed_contents = await process_contents(raw_contents)

   # Convert back to legacy format
   return [
       {
           "title": content.title,
           "content": content.content,
           "type": content.processing_metadata.get("original_type", "text")
       }
       for content in processed_contents
   ]
   ```

## Testing Status
- ✅ Content extraction domain imports work
- ✅ Basic RawContent creation works
- ⏳ Need to test full integration after ContentExtractionService refactor

## Files to Update Next
1. `src/canvas/content_extraction_service.py` - Main refactoring target
2. Update `__all__` exports in `src/canvas/service.py` (remove CanvasAPIService reference)
3. Test integration and ensure API compatibility

## Benefits Achieved So Far
- **748-line monolith** → **Multiple focused modules** (30-150 lines each)
- **Class-based** → **Pure functional** approach
- **Platform-specific** → **Platform-agnostic** content processing
- **Hard to test** → **Easily testable** pure functions
- **Tightly coupled** → **Composable** function architecture

The refactoring is ~85% complete. The core functional architecture is in place and working. Only the integration layer (ContentExtractionService) needs to be updated to use the new functions.
