from typing import Any
from urllib.parse import quote, urlencode, urlparse

from app.logging_config import get_logger

logger = get_logger("url_builder")


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
            logger.warning("canvas_url_not_https", url=url)

        return url.rstrip("/")

    def courses(self, course_id: int) -> str:
        """Build course URL."""
        return f"{self.api_base}/courses/{course_id}"

    def modules(self, course_id: int, module_id: int | None = None) -> str:
        """Build modules URL."""
        base = f"{self.courses(course_id)}/modules"
        return f"{base}/{module_id}" if module_id else base

    def module_items(self, course_id: int, module_id: int) -> str:
        """Build module items URL."""
        return f"{self.modules(course_id, module_id)}/items"

    def pages(self, course_id: int, page_url: str | None = None) -> str:
        """Build pages URL with proper encoding."""
        base = f"{self.courses(course_id)}/pages"
        if page_url:
            encoded_url = quote(page_url.strip(), safe="")
            return f"{base}/{encoded_url}"
        return base

    def files(self, course_id: int, file_id: int | None = None) -> str:
        """Build files URL."""
        base = f"{self.courses(course_id)}/files"
        return f"{base}/{file_id}" if file_id else base

    def build_url(self, *parts: str, params: dict[str, Any] | None = None) -> str:
        """
        Build arbitrary API URL.

        Args:
            *parts: URL path parts
            params: Query parameters

        Returns:
            Complete URL
        """
        # Join parts with /
        path = "/".join(str(p).strip("/") for p in parts)
        url = f"{self.api_base}/{path}"

        # Add query parameters if provided
        if params:
            query_string = urlencode(params)
            url = f"{url}?{query_string}"

        return url

    def oauth_token_url(self) -> str:
        """Build OAuth token exchange URL."""
        return f"{self.base_url}/login/oauth2/token"

    def quiz_api_courses(self, course_id: int) -> str:
        """Build URL for Canvas New Quizzes API courses endpoint."""
        return f"{self.base_url}/api/quiz/v1/courses/{course_id}"

    def quiz_api_quizzes(self, course_id: int, quiz_id: str | None = None) -> str:
        """Build URL for Canvas New Quizzes API quizzes endpoint."""
        base = f"{self.quiz_api_courses(course_id)}/quizzes"
        return f"{base}/{quiz_id}" if quiz_id else base

    def quiz_api_items(
        self, course_id: int, quiz_id: str, item_id: str | None = None
    ) -> str:
        """Build URL for Canvas New Quizzes API items endpoint."""
        base = f"{self.quiz_api_quizzes(course_id, quiz_id)}/items"
        return f"{base}/{item_id}" if item_id else base
