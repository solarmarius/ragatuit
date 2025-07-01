"""
Canvas services for content extraction and quiz export.
"""

from typing import Any

import httpx

from src.config import settings
from src.exceptions import ExternalServiceError
from src.logging_config import get_logger
from src.retry import retry_on_failure

# Import services from local module
from .quiz_export_service import CanvasQuizExportService
from .url_builder import CanvasURLBuilder

logger = get_logger("canvas_service")


def _get_canvas_url_builder() -> CanvasURLBuilder:
    """Get configured Canvas URL builder."""
    base_url = str(settings.CANVAS_BASE_URL)
    if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
        base_url = str(settings.CANVAS_MOCK_URL)
    return CanvasURLBuilder(base_url, settings.CANVAS_API_VERSION)


def _get_canvas_headers(canvas_token: str) -> dict[str, str]:
    """Get standard Canvas API headers."""
    return {
        "Authorization": f"Bearer {canvas_token}",
        "Accept": "application/json",
    }


@retry_on_failure(max_attempts=3, initial_delay=1.0)
async def fetch_canvas_module_items(
    canvas_token: str, course_id: int, module_id: int
) -> list[dict[str, Any]]:
    """
    Fetch items from a Canvas module.

    Args:
        canvas_token: Canvas API token
        course_id: Canvas course ID
        module_id: Canvas module ID

    Returns:
        List of module items with metadata
    """
    url_builder = _get_canvas_url_builder()
    url = url_builder.module_items(course_id, module_id)
    headers = _get_canvas_headers(canvas_token)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, timeout=settings.CANVAS_API_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()

            # Handle both dict response and list response
            if isinstance(result, dict) and "data" in result:
                data = result["data"]
                return data if isinstance(data, list) else []
            elif isinstance(result, list):
                return result
            return []

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(
                "module_not_found",
                course_id=course_id,
                module_id=module_id,
            )
            return []  # Empty list for missing modules
        else:
            raise ExternalServiceError(
                "canvas",
                f"Failed to fetch module {module_id} items",
                e.response.status_code,
            )
    except Exception as e:
        raise ExternalServiceError(
            "canvas", f"Failed to fetch module {module_id} items: {str(e)}"
        )


@retry_on_failure(max_attempts=2, initial_delay=0.5)
async def fetch_canvas_page_content(
    canvas_token: str, course_id: int, page_url: str
) -> dict[str, Any]:
    """
    Fetch content of a specific Canvas page.

    Args:
        canvas_token: Canvas API token
        course_id: Canvas course ID
        page_url: Canvas page URL identifier

    Returns:
        Page data with body content and metadata
    """
    url_builder = _get_canvas_url_builder()
    url = url_builder.pages(course_id, page_url)
    headers = _get_canvas_headers(canvas_token)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, timeout=settings.CANVAS_API_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            return result if isinstance(result, dict) else {}

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(
                "page_not_found",
                course_id=course_id,
                page_url=page_url,
            )
            return {}  # Empty dict for missing pages
        else:
            raise ExternalServiceError(
                "canvas",
                f"Failed to fetch page content: {page_url}",
                e.response.status_code,
            )
    except Exception as e:
        raise ExternalServiceError("canvas", f"Failed to fetch page content: {str(e)}")


@retry_on_failure(max_attempts=2, initial_delay=0.5)
async def fetch_canvas_file_info(
    canvas_token: str, course_id: int, file_id: int
) -> dict[str, Any]:
    """
    Fetch metadata for a Canvas file.

    Args:
        canvas_token: Canvas API token
        course_id: Canvas course ID
        file_id: Canvas file ID

    Returns:
        File metadata including download URL and content type
    """
    url_builder = _get_canvas_url_builder()
    url = url_builder.files(course_id, file_id)
    headers = _get_canvas_headers(canvas_token)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, timeout=settings.CANVAS_API_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            return result if isinstance(result, dict) else {}

    except Exception as e:
        logger.error(
            "fetch_file_info_failed",
            course_id=course_id,
            file_id=file_id,
            error=str(e),
        )
        return {}


@retry_on_failure(max_attempts=2, initial_delay=1.0)
async def download_canvas_file_content(download_url: str) -> bytes:
    """
    Download file content from Canvas.

    Args:
        download_url: URL to download file from

    Returns:
        File content as bytes
    """
    try:
        async with httpx.AsyncClient() as client:
            # Canvas file URLs may redirect, so follow redirects
            response = await client.get(
                download_url,
                follow_redirects=True,
                timeout=60.0,  # 60 second timeout for file downloads
            )
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(
            "file_download_failed",
            download_url=download_url,
            error=str(e),
        )
        return b""


# Re-export for public API
__all__ = [
    "CanvasQuizExportService",
    "fetch_canvas_module_items",
    "fetch_canvas_page_content",
    "fetch_canvas_file_info",
    "download_canvas_file_content",
]
