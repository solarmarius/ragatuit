import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup, Comment

from app.core.logging_config import get_logger

logger = get_logger("content_extraction")


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

                # Filter for Page type items only
                page_items = [
                    item
                    for item in module_items
                    if item.get("type") == "Page" and item.get("page_url")
                ]

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
                        page_content = await self._extract_page_content(page_item)
                        if page_content:
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.canvas_base_url}/courses/{self.course_id}/modules/{module_id}/items",
                headers={
                    "Authorization": f"Bearer {self.canvas_token}",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            if isinstance(result, list):
                return result
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

            # Clean and extract text
            cleaned_content = self._clean_html_content(page_data["body"])

            # Skip if content is too short or empty after cleaning
            if len(cleaned_content.strip()) < 50:
                logger.info(
                    "content_extraction_page_too_short",
                    course_id=self.course_id,
                    page_url=page_url,
                    content_length=len(cleaned_content.strip()),
                )
                return None

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

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.canvas_base_url}/courses/{self.course_id}/pages/{encoded_page_url}",
                headers={
                    "Authorization": f"Bearer {self.canvas_token}",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            if isinstance(result, dict):
                return result
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

        # Replace multiple whitespace characters with single spaces
        text = re.sub(r"\s+", " ", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Remove empty lines and excessive line breaks
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # Ensure sentences are properly separated
        text = re.sub(r"\.([A-Z])", r". \1", text)

        # Remove excessive punctuation
        text = re.sub(r"[.]{3,}", "...", text)
        text = re.sub(r"[!]{2,}", "!", text)
        text = re.sub(r"[?]{2,}", "?", text)

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
            "average_words_per_page": total_word_count // total_pages
            if total_pages > 0
            else 0,
            "extracted_at": datetime.now().isoformat(),
        }
