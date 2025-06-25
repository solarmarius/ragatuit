import io
import re
from datetime import datetime
from typing import Any

import httpx
import pypdf
from bs4 import BeautifulSoup, Comment

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("content_extraction")

# Content extraction limits for security and performance
MAX_PAGE_CONTENT_SIZE = 1024 * 1024  # 1MB per page
SUPPORTED_FILE_TYPES = ["application/pdf", "pdf"]  # Supported file content types


class ContentExtractionService:
    """
    Service for extracting and cleaning content from Canvas pages.

    This service handles fetching module items, extracting page content,
    and cleaning HTML to produce text suitable for LLM consumption.
    """

    def __init__(self, canvas_token: str, course_id: int):
        self.canvas_token = canvas_token
        self.course_id = course_id
        self.canvas_base_url = "http://canvas-mock:8001/api/v1"
        self.total_content_size = 0  # Track total content size for limits

        # Load configuration settings
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

    async def _make_request_with_retry(
        self, url: str, headers: dict[str, str], timeout: float = 30.0
    ) -> dict[str, Any]:
        """Make HTTP request with exponential backoff retry logic."""
        import asyncio

        last_exception: Exception | None = None

        # Use configured timeout or default
        request_timeout = timeout or self.api_timeout

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url, headers=headers, timeout=request_timeout
                    )
                    response.raise_for_status()
                    result = response.json()

                    # Validate response type
                    if isinstance(result, dict | list):
                        return result if isinstance(result, dict) else {"data": result}

                    logger.warning(
                        "canvas_api_invalid_response_type",
                        url=url,
                        response_type=type(result).__name__,
                        attempt=attempt + 1,
                    )
                    return {}

            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    logger.error(
                        "canvas_api_client_error_no_retry",
                        url=url,
                        status_code=e.response.status_code,
                        attempt=attempt + 1,
                    )
                    raise

                last_exception = e
                logger.warning(
                    "canvas_api_server_error_retry",
                    url=url,
                    status_code=e.response.status_code,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                )

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(
                    "canvas_api_network_error_retry",
                    url=url,
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                )

            # Calculate exponential backoff delay
            if attempt < self.max_retries - 1:  # Don't sleep on last attempt
                delay = min(
                    self.initial_retry_delay * (self.retry_backoff_factor**attempt),
                    self.max_retry_delay,
                )
                logger.info(
                    "canvas_api_retry_delay",
                    url=url,
                    delay=delay,
                    next_attempt=attempt + 2,
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        logger.error(
            "canvas_api_all_retries_exhausted",
            url=url,
            total_attempts=self.max_retries,
            final_error=str(last_exception),
        )

        if last_exception:
            raise last_exception

        raise httpx.RequestError("All retries exhausted")

    async def extract_content_for_modules(
        self, module_ids: list[int]
    ) -> dict[str, list[dict[str, str]]]:
        """
        Extract content from all pages in the specified modules.

        Args:
            module_ids: List of Canvas module IDs to extract content from

        Returns:
            Dict mapping module_id to list of extracted page content:
            {
                "module_123": [
                    {"title": "Page Title", "content": "cleaned text content"},
                    ...
                ]
            }
        """
        extracted_content: dict[str, list[dict[str, str]]] = {}

        for module_id in module_ids:
            logger.info(
                "content_extraction_module_started",
                course_id=self.course_id,
                module_id=module_id,
            )

            try:
                # Get module items
                module_items = await self._fetch_module_items(module_id)

                # Filter for Page and File type items and apply limits
                content_items = [
                    item
                    for item in module_items
                    if (item.get("type") == "Page" and item.get("page_url"))
                    or (item.get("type") == "File" and item.get("content_id"))
                ]

                # Limit content items per module for performance
                if len(content_items) > self.max_pages_per_module:
                    logger.warning(
                        "content_extraction_items_limited",
                        course_id=self.course_id,
                        module_id=module_id,
                        total_items=len(content_items),
                        limit=self.max_pages_per_module,
                    )
                    content_items = content_items[: self.max_pages_per_module]

                logger.info(
                    "content_extraction_items_found",
                    course_id=self.course_id,
                    module_id=module_id,
                    total_items=len(module_items),
                    content_items=len(content_items),
                    page_items=len(
                        [i for i in content_items if i.get("type") == "Page"]
                    ),
                    file_items=len(
                        [i for i in content_items if i.get("type") == "File"]
                    ),
                )

                # Extract content from each item (page or file)
                module_content = []
                for content_item in content_items:
                    try:
                        # Check total content size limit
                        if self.total_content_size > self.max_total_content_size:
                            logger.warning(
                                "content_extraction_size_limit_reached",
                                course_id=self.course_id,
                                module_id=module_id,
                                total_size=self.total_content_size,
                                limit=self.max_total_content_size,
                            )
                            break

                        # Extract content based on item type
                        item_content: dict[str, str] | None = None
                        if content_item.get("type") == "Page":
                            item_content = await self._extract_page_content(
                                content_item
                            )
                        elif content_item.get("type") == "File":
                            item_content = await self._extract_file_content(
                                content_item
                            )

                        if item_content:
                            content_size = len(item_content.get("content", ""))
                            self.total_content_size += content_size
                            module_content.append(item_content)
                    except Exception as e:
                        logger.warning(
                            "content_extraction_item_failed",
                            course_id=self.course_id,
                            module_id=module_id,
                            item_type=content_item.get("type"),
                            item_title=content_item.get("title"),
                            error=str(e),
                        )
                        # Continue with other items even if one fails
                        continue

                extracted_content[f"module_{module_id}"] = module_content

                logger.info(
                    "content_extraction_module_completed",
                    course_id=self.course_id,
                    module_id=module_id,
                    extracted_pages=len(module_content),
                )

            except Exception as e:
                logger.error(
                    "content_extraction_module_failed",
                    course_id=self.course_id,
                    module_id=module_id,
                    error=str(e),
                    exc_info=True,
                )
                # Continue with other modules even if one fails
                extracted_content[f"module_{module_id}"] = []
                continue

        return extracted_content

    async def _fetch_module_items(self, module_id: int) -> list[dict[str, Any]]:
        """Fetch items from a Canvas module."""
        url = (
            f"{self.canvas_base_url}/courses/{self.course_id}/modules/{module_id}/items"
        )
        headers = {
            "Authorization": f"Bearer {self.canvas_token}",
            "Accept": "application/json",
        }

        try:
            result = await self._make_request_with_retry(url, headers)
            # Handle both dict response and list response
            if isinstance(result, dict) and "data" in result:
                data = result["data"]
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            logger.error(
                "fetch_module_items_failed",
                course_id=self.course_id,
                module_id=module_id,
                error=str(e),
            )
            return []

    async def _extract_page_content(
        self, page_item: dict[str, Any]
    ) -> dict[str, str] | None:
        """Extract and clean content from a Canvas page."""
        page_url = page_item.get("page_url")
        if not page_url:
            return None

        try:
            # Fetch page content
            page_data = await self._fetch_page_content(page_url)
            if not page_data or not page_data.get("body"):
                logger.info(
                    "content_extraction_page_empty",
                    course_id=self.course_id,
                    page_url=page_url,
                )
                return None

            # Check raw content size before processing
            raw_body = page_data.get("body", "")
            if len(raw_body) > MAX_PAGE_CONTENT_SIZE:
                logger.warning(
                    "content_extraction_page_too_large",
                    course_id=self.course_id,
                    page_url=page_url,
                    content_size=len(raw_body),
                    limit=MAX_PAGE_CONTENT_SIZE,
                )
                return None

            # Clean and extract text
            cleaned_content = self._clean_html_content(raw_body)

            # Validate content length after cleaning
            content_length = len(cleaned_content.strip())
            if content_length < self.min_content_length:
                logger.info(
                    "content_extraction_page_too_short",
                    course_id=self.course_id,
                    page_url=page_url,
                    content_length=content_length,
                    min_length=self.min_content_length,
                )
                return None

            if content_length > self.max_content_length:
                logger.warning(
                    "content_extraction_page_content_too_long",
                    course_id=self.course_id,
                    page_url=page_url,
                    content_length=content_length,
                    max_length=self.max_content_length,
                )
                # Truncate content instead of discarding
                cleaned_content = (
                    cleaned_content[: self.max_content_length] + "... [truncated]"
                )

            return {
                "title": page_data.get("title", "Untitled Page"),
                "content": cleaned_content,
                "type": "page",
            }

        except Exception as e:
            logger.warning(
                "content_extraction_page_error",
                course_id=self.course_id,
                page_url=page_url,
                error=str(e),
            )
            return None

    async def _fetch_page_content(self, page_url: str) -> dict[str, Any]:
        """Fetch content of a specific Canvas page."""
        from urllib.parse import quote

        encoded_page_url = quote(page_url.strip(), safe="")
        url = (
            f"{self.canvas_base_url}/courses/{self.course_id}/pages/{encoded_page_url}"
        )
        headers = {
            "Authorization": f"Bearer {self.canvas_token}",
            "Accept": "application/json",
        }

        try:
            result = await self._make_request_with_retry(url, headers)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error(
                "fetch_page_content_failed",
                course_id=self.course_id,
                page_url=page_url,
                error=str(e),
            )
            return {}

    async def _extract_file_content(
        self, file_item: dict[str, Any]
    ) -> dict[str, str] | None:
        """
        Extract text content from a Canvas file item.

        Currently supports PDF files only.
        Returns None if file is not supported or extraction fails.
        """
        try:
            file_id = file_item.get("content_id")
            if not file_id:
                logger.warning(
                    "file_extraction_no_content_id",
                    course_id=self.course_id,
                    file_title=file_item.get("title"),
                )
                return None

            # Get file metadata from Canvas API endpoint
            file_info = await self._fetch_file_info(file_id)
            if not file_info:
                return None

            # Check if file is supported (PDF only for now)
            content_type = file_info.get("content-type", "")
            mime_class = file_info.get("mime_class", "")

            if (
                content_type not in SUPPORTED_FILE_TYPES
                and mime_class not in SUPPORTED_FILE_TYPES
            ):
                logger.info(
                    "file_extraction_unsupported_type",
                    course_id=self.course_id,
                    file_id=file_id,
                    content_type=content_type,
                    mime_class=mime_class,
                )
                return None

            # Check file size
            file_size = file_info.get("size", 0)
            if file_size > self.max_file_size:
                logger.warning(
                    "file_extraction_size_limit",
                    course_id=self.course_id,
                    file_id=file_id,
                    file_size=file_size,
                    limit=self.max_file_size,
                )
                return None

            # Download and extract PDF content
            download_url = file_info.get("url")
            if not download_url:
                logger.error(
                    "file_extraction_no_download_url",
                    course_id=self.course_id,
                    file_id=file_id,
                )
                return None

            text_content = await self._download_and_extract_pdf(file_id, download_url)

            if text_content and len(text_content) >= self.min_content_length:
                # Truncate if too long
                if len(text_content) > self.max_content_length:
                    logger.warning(
                        "file_extraction_content_truncated",
                        course_id=self.course_id,
                        file_id=file_id,
                        original_length=len(text_content),
                        max_length=self.max_content_length,
                    )
                    text_content = text_content[: self.max_content_length]

                return {
                    "title": file_info.get(
                        "display_name", file_item.get("title", "Untitled")
                    ),
                    "content": text_content,
                    "type": "file",
                    "content_type": content_type,
                }

            return None

        except Exception as e:
            logger.error(
                "file_extraction_failed",
                course_id=self.course_id,
                file_id=file_item.get("content_id"),
                error=str(e),
                exc_info=True,
            )
            return None

    async def _fetch_file_info(self, file_id: int) -> dict[str, Any]:
        """
        Fetch metadata for a Canvas file using the Canvas API.

        This calls the same Canvas API endpoint that our canvas.py router uses,
        ensuring consistent behavior and avoiding code duplication.
        """
        url = f"{self.canvas_base_url}/courses/{self.course_id}/files/{file_id}"
        headers = {
            "Authorization": f"Bearer {self.canvas_token}",
            "Accept": "application/json",
        }

        try:
            result = await self._make_request_with_retry(url, headers)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error(
                "fetch_file_info_failed",
                course_id=self.course_id,
                file_id=file_id,
                error=str(e),
            )
            return {}

    async def _download_and_extract_pdf(
        self, file_id: int, download_url: str
    ) -> str | None:
        """
        Download PDF file and extract text content.

        Uses in-memory processing with proper cleanup to avoid memory leaks.
        Returns extracted text or None if extraction fails.
        """
        pdf_buffer = None
        try:
            # Download PDF to memory buffer
            pdf_buffer = io.BytesIO()

            async with httpx.AsyncClient() as client:
                # Canvas file URLs may redirect, so follow redirects
                response = await client.get(
                    download_url,
                    follow_redirects=True,
                    timeout=60.0,  # 60 second timeout for file downloads
                )
                response.raise_for_status()

                # Write content to buffer
                pdf_buffer.write(response.content)

            # Reset buffer position for reading
            pdf_buffer.seek(0)

            # Extract text from PDF
            try:
                reader = pypdf.PdfReader(pdf_buffer)
                text_parts = []

                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as e:
                        logger.warning(
                            "pdf_page_extraction_failed",
                            course_id=self.course_id,
                            file_id=file_id,
                            page_num=page_num,
                            error=str(e),
                        )
                        # Continue with other pages
                        continue

                # Join all page texts with newlines
                full_text = "\n\n".join(text_parts)

                # Clean up excessive whitespace
                full_text = re.sub(r"\n{3,}", "\n\n", full_text)
                full_text = re.sub(r" {2,}", " ", full_text)

                return full_text.strip()

            except Exception as e:
                logger.error(
                    "pdf_extraction_failed",
                    course_id=self.course_id,
                    file_id=file_id,
                    error=str(e),
                    exc_info=True,
                )
                return None

        except httpx.HTTPStatusError as e:
            logger.error(
                "pdf_download_http_error",
                course_id=self.course_id,
                file_id=file_id,
                status_code=e.response.status_code,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "pdf_download_failed",
                course_id=self.course_id,
                file_id=file_id,
                error=str(e),
                exc_info=True,
            )
            return None
        finally:
            # CRITICAL: Always clean up the buffer to free memory
            if pdf_buffer:
                pdf_buffer.close()
                del pdf_buffer

    def _clean_html_content(self, html_content: str) -> str:
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
        """
        if not html_content:
            return ""

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove Canvas-specific elements (common class names and IDs)
        canvas_selectors = [
            # Canvas UI elements
            ".ic-app-header",
            ".ic-app-nav-toggle-and-crumbs",
            ".ic-app-crumbs",
            ".breadcrumbs",
            ".course-title",
            ".right-side-wrapper",
            # Canvas page elements
            ".page-toolbar",
            ".show-content",
            ".user_content_iframe",
            ".canvas_user_content",
            ".mce-content-body",
            # Navigation and UI
            '[role="navigation"]',
            '[data-component="Navigation"]',
            ".ui-widget",
            ".ui-state-default",
        ]

        for selector in canvas_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Get text content
        text = soup.get_text()

        # Clean up whitespace and formatting
        text = self._normalize_text(text)

        return text

    def _normalize_text(self, text: str) -> str:
        """Normalize text by cleaning whitespace and formatting."""
        if not text:
            return ""

        # Limit text size to prevent ReDoS attacks
        if len(text) > self.max_content_length:
            text = text[: self.max_content_length]

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

    def get_content_summary(
        self, extracted_content: dict[str, list[dict[str, str]]]
    ) -> dict[str, Any]:
        """
        Generate a summary of extracted content.

        Returns statistics about the extracted content for logging and UI display.
        """
        total_pages = 0
        total_word_count = 0
        modules_processed = len(extracted_content)

        for _module_id, pages in extracted_content.items():
            total_pages += len(pages)
            for page in pages:
                # Rough word count estimation
                word_count = len(page.get("content", "").split())
                total_word_count += word_count

        return {
            "modules_processed": modules_processed,
            "total_pages": total_pages,
            "total_word_count": total_word_count,
            "average_words_per_page": (
                total_word_count // total_pages if total_pages > 0 else 0
            ),
            "extracted_at": datetime.now().isoformat(),
        }
