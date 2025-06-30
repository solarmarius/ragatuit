"""
Utility functions for Canvas module.
"""

import re
from typing import Any

from bs4 import BeautifulSoup, Comment

from app.logging_config import get_logger

logger = get_logger("canvas_utils")


def clean_html_content(html_content: str, max_length: int | None = None) -> str:
    """
    Clean HTML content and extract text.

    Args:
        html_content: Raw HTML content
        max_length: Maximum length of returned text (None for no limit)

    Returns:
        Cleaned text content
    """
    try:
        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        # Apply length limit if specified
        if max_length and len(text) > max_length:
            text = text[:max_length] + "..."

        return text

    except Exception as e:
        logger.error(f"Error cleaning HTML content: {e}")
        return html_content  # Return original if cleaning fails


def validate_canvas_token(token: str) -> bool:
    """
    Validate Canvas API token format.

    Args:
        token: Canvas API token

    Returns:
        bool: True if token appears valid
    """
    if not token or not isinstance(token, str):
        return False

    # Canvas tokens are typically long alphanumeric strings
    # This is a basic check - actual validation happens when making API calls
    return len(token) > 20 and token.replace("-", "").replace("_", "").isalnum()


def format_canvas_error(response_data: dict[str, Any]) -> str:
    """
    Format Canvas API error response into readable message.

    Args:
        response_data: Canvas API error response

    Returns:
        Formatted error message
    """
    errors = response_data.get("errors", [])
    if isinstance(errors, list) and errors:
        # Handle array of error objects
        error_messages = []
        for error in errors:
            if isinstance(error, dict):
                message = error.get("message", str(error))
                error_messages.append(message)
            else:
                error_messages.append(str(error))
        return "; ".join(error_messages)
    elif isinstance(errors, dict):
        # Handle single error object
        return str(errors.get("message", str(errors)))
    else:
        # Fallback to general message
        return str(response_data.get("message", "Unknown Canvas API error"))


def convert_correct_answer_to_canvas_format(correct_answer: str) -> str:
    """
    Convert letter answer (A, B, C, D) to Canvas choice format.

    Args:
        correct_answer: Letter answer (A, B, C, or D)

    Returns:
        Canvas choice ID (choice_1, choice_2, choice_3, or choice_4)
    """
    answer_map = {
        "A": "choice_1",
        "B": "choice_2",
        "C": "choice_3",
        "D": "choice_4",
    }
    return answer_map.get(correct_answer.upper(), "choice_1")


def sanitize_module_name(module_name: str) -> str:
    """
    Sanitize module name for use as dictionary key.

    Args:
        module_name: Raw module name

    Returns:
        Sanitized module name
    """
    # Remove special characters and limit length
    sanitized = re.sub(r"[^\w\s-]", "", module_name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized[:100]  # Limit to reasonable length
