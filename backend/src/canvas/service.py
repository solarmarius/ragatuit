"""
Canvas services for content extraction and quiz export.
"""

from typing import Any

import httpx

from src.config import get_logger, settings
from src.exceptions import ExternalServiceError
from src.retry import retry_on_failure

# Import services from local module
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
        logger.warning(
            "canvas_module_items_fetch_failed",
            course_id=course_id,
            module_id=module_id,
            error=str(e),
        )
        return []  # Return empty list on network/connection errors


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


# Quiz Export Canvas API Functions


@retry_on_failure(max_attempts=3, initial_delay=2.0)
async def create_canvas_quiz(
    canvas_token: str, course_id: int, title: str, total_points: int
) -> dict[str, Any]:
    """
    Create a new quiz in Canvas using the New Quizzes API.

    Pure function for Canvas API interaction.

    Args:
        canvas_token: Canvas API authentication token
        course_id: Canvas course ID
        title: Quiz title
        total_points: Total points for the quiz

    Returns:
        Canvas quiz object with assignment_id

    Raises:
        ExternalServiceError: If Canvas API call fails
    """
    logger.info(
        "canvas_quiz_creation_started",
        course_id=course_id,
        title=title,
        total_points=total_points,
    )

    url_builder = _get_canvas_url_builder()
    headers = _get_canvas_headers(canvas_token)
    headers["Content-Type"] = "application/json"

    quiz_data = {
        "quiz": {
            "title": title,
            "points_possible": total_points,
            "quiz_settings": {
                "shuffle_questions": False,
                "shuffle_answers": False,
                "has_time_limit": False,
            },
        }
    }

    try:
        async with httpx.AsyncClient(timeout=settings.CANVAS_API_TIMEOUT) as client:
            response = await client.post(
                url_builder.quiz_api_quizzes(course_id),
                headers=headers,
                json=quiz_data,
            )
            response.raise_for_status()
            canvas_quiz: dict[str, Any] = response.json()

            logger.info(
                "canvas_quiz_creation_completed",
                course_id=course_id,
                title=title,
                canvas_quiz_id=canvas_quiz.get("id"),
            )

            return canvas_quiz

    except httpx.HTTPStatusError as e:
        logger.error(
            "canvas_quiz_creation_failed",
            course_id=course_id,
            title=title,
            status_code=e.response.status_code,
            response_text=e.response.text,
        )
        raise ExternalServiceError(
            "canvas",
            f"Failed to create Canvas quiz: {title}",
            e.response.status_code,
        )
    except Exception as e:
        logger.error(
            "canvas_quiz_creation_error",
            course_id=course_id,
            title=title,
            error=str(e),
        )
        raise ExternalServiceError(
            "canvas",
            f"Failed to create Canvas quiz: {title} - {str(e)}",
        )


async def create_canvas_quiz_items(
    canvas_token: str, course_id: int, quiz_id: str, questions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Create quiz items (questions) in Canvas for the given quiz.

    Pure function for Canvas API batch operations.

    Args:
        canvas_token: Canvas API authentication token
        course_id: Canvas course ID
        quiz_id: Canvas quiz assignment ID
        questions: List of question dictionaries to create

    Returns:
        List of results for each question creation attempt
    """
    logger.info(
        "canvas_quiz_items_creation_started",
        course_id=course_id,
        canvas_quiz_id=quiz_id,
        questions_count=len(questions),
    )

    url_builder = _get_canvas_url_builder()
    headers = _get_canvas_headers(canvas_token)
    headers["Content-Type"] = "application/json"

    results = []

    async with httpx.AsyncClient(timeout=settings.CANVAS_API_TIMEOUT) as client:
        for i, question in enumerate(questions):
            try:
                # Convert question to Canvas New Quiz item format
                item_data = convert_question_to_canvas_format(question, i + 1)

                response = await client.post(
                    url_builder.quiz_api_items(course_id, quiz_id),
                    headers=headers,
                    json=item_data,
                )
                response.raise_for_status()
                item_response = response.json()

                results.append(
                    {
                        "success": True,
                        "question_id": question["id"],
                        "item_id": item_response.get("id"),
                        "position": i + 1,
                    }
                )

                logger.info(
                    "canvas_quiz_item_created",
                    course_id=course_id,
                    canvas_quiz_id=quiz_id,
                    question_id=str(question["id"]),
                    canvas_item_id=item_response.get("id"),
                    position=i + 1,
                )

            except httpx.HTTPStatusError as e:
                logger.error(
                    "canvas_quiz_item_creation_failed",
                    course_id=course_id,
                    canvas_quiz_id=quiz_id,
                    question_id=str(question["id"]),
                    position=i + 1,
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                )
                # Continue with other questions even if one fails
                results.append(
                    {
                        "success": False,
                        "question_id": question["id"],
                        "error": f"Canvas API error: {e.response.status_code}",
                        "position": i + 1,
                    }
                )

            except Exception as e:
                logger.error(
                    "canvas_quiz_item_creation_error",
                    course_id=course_id,
                    canvas_quiz_id=quiz_id,
                    question_id=str(question["id"]),
                    position=i + 1,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                results.append(
                    {
                        "success": False,
                        "question_id": question["id"],
                        "error": str(e),
                        "position": i + 1,
                    }
                )

    successful_items = len([r for r in results if r["success"]])
    logger.info(
        "canvas_quiz_items_creation_completed",
        course_id=course_id,
        canvas_quiz_id=quiz_id,
        total_questions=len(questions),
        successful_items=successful_items,
        failed_items=len(questions) - successful_items,
    )

    return results


def convert_question_to_canvas_format(
    question: dict[str, Any], position: int
) -> dict[str, Any]:
    """
    Convert a question dictionary to Canvas New Quiz item format.

    Pure function for data transformation.

    Args:
        question: Question dictionary with question data
        position: Position of the question in the quiz

    Returns:
        Canvas quiz item data structure
    """
    from src.question.types.base import QuestionType
    from src.question.types.registry import get_question_type_registry

    question_type_str = question.get("question_type", "multiple_choice")

    # Map string to QuestionType enum
    question_type_map = {
        "multiple_choice": QuestionType.MULTIPLE_CHOICE,
        "fill_in_blank": QuestionType.FILL_IN_BLANK,
    }

    question_type_enum = question_type_map.get(question_type_str)
    if not question_type_enum:
        from src.config import get_logger

        logger = get_logger("canvas_service")
        logger.error(
            "unsupported_question_type_for_canvas_conversion",
            question_id=question.get("id"),
            question_type=question_type_str,
        )
        raise ValueError(
            f"Unsupported question type for Canvas export: {question_type_str}"
        )

    # Get the question type implementation from registry
    registry = get_question_type_registry()
    question_type_impl = registry.get_question_type(question_type_enum)

    # Convert question dict to the appropriate data model
    # Filter out fields that aren't part of the data model
    data_for_validation = {
        k: v for k, v in question.items() if k not in ["id", "question_type"]
    }

    # For multiple choice, normalize invalid correct_answer to "A" (for backward compatibility)
    if question_type_enum == QuestionType.MULTIPLE_CHOICE:
        if data_for_validation.get("correct_answer") not in ["A", "B", "C", "D"]:
            data_for_validation["correct_answer"] = "A"

    question_data = question_type_impl.validate_data(data_for_validation)

    # Use the question type's format_for_canvas method
    canvas_format = question_type_impl.format_for_canvas(question_data)

    # Wrap in the Canvas API structure expected by the API
    return {
        "item": {
            "entry_type": "Item",
            "points_possible": canvas_format.get("points_possible", 1),
            "position": position,
            "entry": canvas_format,
        }
    }


@retry_on_failure(max_attempts=2, initial_delay=1.0)
async def delete_canvas_quiz(canvas_token: str, course_id: int, quiz_id: str) -> bool:
    """
    Delete a Canvas quiz by ID.

    Pure function for Canvas API quiz deletion, used for rollback scenarios
    when question export fails.

    Args:
        canvas_token: Canvas API authentication token
        course_id: Canvas course ID
        quiz_id: Canvas quiz ID to delete

    Returns:
        True if deletion succeeded, False otherwise

    Raises:
        ExternalServiceError: If Canvas API call fails with non-404 error
    """
    logger.info(
        "canvas_quiz_deletion_started",
        course_id=course_id,
        canvas_quiz_id=quiz_id,
    )

    url_builder = _get_canvas_url_builder()
    headers = _get_canvas_headers(canvas_token)

    try:
        async with httpx.AsyncClient(timeout=settings.CANVAS_API_TIMEOUT) as client:
            response = await client.delete(
                url_builder.quiz_api_quizzes(course_id, quiz_id),
                headers=headers,
            )
            response.raise_for_status()

            logger.info(
                "canvas_quiz_deletion_completed",
                course_id=course_id,
                canvas_quiz_id=quiz_id,
            )

            return True

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Quiz already deleted or doesn't exist
            logger.warning(
                "canvas_quiz_already_deleted",
                course_id=course_id,
                canvas_quiz_id=quiz_id,
            )
            return True  # Consider this successful
        else:
            logger.error(
                "canvas_quiz_deletion_failed",
                course_id=course_id,
                canvas_quiz_id=quiz_id,
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise ExternalServiceError(
                "canvas",
                f"Failed to delete Canvas quiz: {quiz_id}",
                e.response.status_code,
            )
    except Exception as e:
        logger.error(
            "canvas_quiz_deletion_error",
            course_id=course_id,
            canvas_quiz_id=quiz_id,
            error=str(e),
        )
        raise ExternalServiceError(
            "canvas",
            f"Failed to delete Canvas quiz: {quiz_id} - {str(e)}",
        )


# Re-export for public API
__all__ = [
    "fetch_canvas_module_items",
    "fetch_canvas_page_content",
    "fetch_canvas_file_info",
    "download_canvas_file_content",
    "create_canvas_quiz",
    "create_canvas_quiz_items",
    "convert_question_to_canvas_format",
    "delete_canvas_quiz",
]
