import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup, Comment

from app.core.logging_config import get_logger

logger = get_logger("content_extraction")

# Content extraction limits for security and performance
MAX_PAGE_CONTENT_SIZE = 1024 * 1024  # 1MB per page
MAX_TOTAL_CONTENT_SIZE = 50 * 1024 * 1024  # 50MB total per quiz
MAX_PAGES_PER_MODULE = 100  # Maximum pages to process per module
MIN_CONTENT_LENGTH = 50  # Minimum content length (configurable)
MAX_CONTENT_LENGTH = 500_000  # Maximum content length per page

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # Start with 1 second
MAX_RETRY_DELAY = 30.0  # Cap at 30 seconds
RETRY_BACKOFF_FACTOR = 2.0  # Exponential backoff


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

    async def _make_request_with_retry(
        self, url: str, headers: dict[str, str], timeout: float = 30.0
    ) -> dict[str, Any]:
        """Make HTTP request with exponential backoff retry logic."""
        import asyncio

        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, timeout=timeout)
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
                    max_retries=MAX_RETRIES,
                )

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(
                    "canvas_api_network_error_retry",
                    url=url,
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=MAX_RETRIES,
                )

            # Calculate exponential backoff delay
            if attempt < MAX_RETRIES - 1:  # Don't sleep on last attempt
                delay = min(
                    INITIAL_RETRY_DELAY * (RETRY_BACKOFF_FACTOR**attempt),
                    MAX_RETRY_DELAY,
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
            total_attempts=MAX_RETRIES,
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
        extracted_content = {}

        for module_id in module_ids:
            logger.info(
                "content_extraction_module_started",
                course_id=self.course_id,
                module_id=module_id,
            )

            try:
                # Get module items
                module_items = await self._fetch_module_items(module_id)

                # Filter for Page type items only and apply limits
                page_items = [
                    item
                    for item in module_items
                    if item.get("type") == "Page" and item.get("page_url")
                ]

                # Limit pages per module for performance
                if len(page_items) > MAX_PAGES_PER_MODULE:
                    logger.warning(
                        "content_extraction_pages_limited",
                        course_id=self.course_id,
                        module_id=module_id,
                        total_pages=len(page_items),
                        limit=MAX_PAGES_PER_MODULE,
                    )
                    page_items = page_items[:MAX_PAGES_PER_MODULE]

                logger.info(
                    "content_extraction_pages_found",
                    course_id=self.course_id,
                    module_id=module_id,
                    total_items=len(module_items),
                    page_items=len(page_items),
                )

                # Extract content from each page
                module_content = []
                for page_item in page_items:
                    try:
                        # Check total content size limit
                        if self.total_content_size > MAX_TOTAL_CONTENT_SIZE:
                            logger.warning(
                                "content_extraction_size_limit_reached",
                                course_id=self.course_id,
                                module_id=module_id,
                                total_size=self.total_content_size,
                                limit=MAX_TOTAL_CONTENT_SIZE,
                            )
                            break

                        page_content = await self._extract_page_content(page_item)
                        if page_content:
                            content_size = len(page_content.get("content", ""))
                            self.total_content_size += content_size
                            module_content.append(page_content)
                    except Exception as e:
                        logger.warning(
                            "content_extraction_page_failed",
                            course_id=self.course_id,
                            module_id=module_id,
                            page_url=page_item.get("page_url"),
                            error=str(e),
                        )
                        # Continue with other pages even if one fails
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
            if content_length < MIN_CONTENT_LENGTH:
                logger.info(
                    "content_extraction_page_too_short",
                    course_id=self.course_id,
                    page_url=page_url,
                    content_length=content_length,
                    min_length=MIN_CONTENT_LENGTH,
                )
                return None

            if content_length > MAX_CONTENT_LENGTH:
                logger.warning(
                    "content_extraction_page_content_too_long",
                    course_id=self.course_id,
                    page_url=page_url,
                    content_length=content_length,
                    max_length=MAX_CONTENT_LENGTH,
                )
                # Truncate content instead of discarding
                cleaned_content = (
                    cleaned_content[:MAX_CONTENT_LENGTH] + "... [truncated]"
                )

            return {
                "title": page_data.get("title", "Untitled Page"),
                "content": cleaned_content,
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
        if len(text) > MAX_CONTENT_LENGTH:
            text = text[:MAX_CONTENT_LENGTH]

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
