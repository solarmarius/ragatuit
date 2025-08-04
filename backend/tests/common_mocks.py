"""Centralized mock utilities for test infrastructure.

This module provides reusable mock contexts and utilities to reduce duplication
across test files and standardize external service mocking.
"""

from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch


@contextmanager
def mock_canvas_api(
    courses: Optional[List[Dict[str, Any]]] = None,
    modules: Optional[List[Dict[str, Any]]] = None,
    module_items: Optional[List[Dict[str, Any]]] = None,
    page_content: Optional[Dict[str, Any]] = None,
    file_info: Optional[Dict[str, Any]] = None,
    file_content: Optional[bytes] = None,
    quiz_response: Optional[Dict[str, Any]] = None,
    quiz_items_response: Optional[List[Dict[str, Any]]] = None,
    should_fail: bool = False,
    status_code: int = 200,
) -> Generator[MagicMock, None, None]:
    """Mock Canvas API with standard responses.

    Args:
        courses: List of course data dicts
        modules: List of module data dicts
        module_items: List of module item data dicts
        page_content: Page content dict
        file_info: File info dict
        file_content: File content bytes
        quiz_response: Quiz creation response
        quiz_items_response: Quiz items creation response
        should_fail: Whether API calls should fail
        status_code: HTTP status code for failures
    """
    # Default responses
    if courses is None:
        courses = [
            {
                "id": 123,
                "name": "Test Course",
                "course_code": "TEST101",
                "enrollment_term_id": 1,
                "workflow_state": "available",
            }
        ]

    if modules is None:
        modules = [
            {
                "id": 456,
                "name": "Module 1",
                "position": 1,
                "workflow_state": "active",
                "items_count": 5,
            }
        ]

    if module_items is None:
        module_items = [
            {"id": 123, "title": "Test Item 1", "type": "Page", "url": "test-page-1"},
            {"id": 124, "title": "Test Item 2", "type": "File", "url": "test-file-1"},
        ]

    if page_content is None:
        page_content = {
            "title": "Test Page",
            "body": "<p>This is test page content</p>",
            "url": "test-page",
            "created_at": "2024-01-01T00:00:00Z",
        }

    if file_info is None:
        file_info = {
            "id": 789,
            "display_name": "test_file.pdf",
            "filename": "test_file.pdf",
            "content-type": "application/pdf",
            "size": 12345,
            "url": "https://canvas.example.com/files/789/download",
        }

    if file_content is None:
        file_content = b"This is test file content"

    if quiz_response is None:
        quiz_response = {
            "id": "quiz_123",
            "title": "Test Quiz",
            "points_possible": 100,
            "assignment_id": "assignment_456",
        }

    if quiz_items_response is None:
        quiz_items_response = [
            {"success": True, "canvas_id": 8001, "question_id": "q1"},
            {"success": True, "canvas_id": 8002, "question_id": "q2"},
        ]

    mock_client = MagicMock()

    if should_fail:
        # Configure mock to simulate failures
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = status_code
        error = httpx.HTTPStatusError(
            f"HTTP {status_code} error", request=MagicMock(), response=mock_response
        )

        mock_client.return_value.__aenter__.return_value.get.side_effect = error
        mock_client.return_value.__aenter__.return_value.post.side_effect = error
    else:
        # Configure successful responses
        def mock_get_response(url, **kwargs):
            mock_response = MagicMock()

            # More specific URL matching - order matters!
            if "modules" in url and "items" in url:
                mock_response.json.return_value = module_items
            elif "modules" in url:
                mock_response.json.return_value = modules
            elif "pages" in url:
                mock_response.json.return_value = page_content
            elif "files" in url:
                if "download" in url:
                    mock_response.content = file_content
                else:
                    mock_response.json.return_value = file_info
            elif "courses" in url:
                mock_response.json.return_value = courses
            elif (
                url.endswith((".pdf", ".docx", ".txt", ".pptx"))
                or "file" in url.lower()
            ):
                # Handle direct file downloads (like example.com/file.pdf)
                mock_response.content = file_content
            else:
                mock_response.json.return_value = {}

            mock_response.raise_for_status.return_value = None
            return mock_response

        def mock_post_response(url, **kwargs):
            mock_response = MagicMock()

            if "quizzes" in url and "items" in url:
                mock_response.json.return_value = {"id": "item_123"}
            elif "quizzes" in url:
                mock_response.json.return_value = quiz_response
            else:
                mock_response.json.return_value = {}

            mock_response.raise_for_status.return_value = None
            return mock_response

        mock_client.return_value.__aenter__.return_value.get.side_effect = (
            mock_get_response
        )
        mock_client.return_value.__aenter__.return_value.post.side_effect = (
            mock_post_response
        )

    with patch("httpx.AsyncClient", mock_client):
        yield mock_client


@contextmanager
def mock_openai_api(
    response_content: Optional[str] = None,
    usage: Optional[Dict[str, int]] = None,
    should_fail: bool = False,
    error_type: str = "generic",
) -> Generator[MagicMock, None, None]:
    """Mock OpenAI API with standard responses.

    Args:
        response_content: JSON content to return
        usage: Token usage dict
        should_fail: Whether API calls should fail
        error_type: Type of error to simulate (generic, auth, rate_limit)
    """
    if response_content is None:
        response_content = '{"questions": [{"question_text": "What is 2+2?", "options": [{"text": "4", "is_correct": true}, {"text": "5", "is_correct": false}], "explanation": "Basic arithmetic."}]}'

    if usage is None:
        usage = {
            "prompt_tokens": 20,
            "completion_tokens": 50,
            "total_tokens": 70,
        }

    mock_response = MagicMock()
    mock_response.content = response_content
    mock_response.usage = usage

    mock_client = AsyncMock()

    if should_fail:
        if error_type == "auth":
            mock_client.ainvoke.side_effect = Exception("authentication failed")
        elif error_type == "rate_limit":
            mock_client.ainvoke.side_effect = Exception("Rate limit exceeded")
        else:
            mock_client.ainvoke.side_effect = Exception("Generic OpenAI error")
    else:
        mock_client.ainvoke.return_value = mock_response

    mock_chat_openai = MagicMock()
    mock_chat_openai.return_value = mock_client

    with patch("src.question.providers.openai_provider.ChatOpenAI", mock_chat_openai):
        yield mock_chat_openai


@contextmanager
def mock_auth_tokens(
    encrypt_pattern: str = "encrypted_{token}",
    decrypt_pattern: str = "decrypted_{token}",
) -> Generator[tuple, None, None]:
    """Mock token encryption/decryption functions.

    Args:
        encrypt_pattern: Format string for encrypted tokens
        decrypt_pattern: Format string for decrypted tokens
    """

    def mock_encrypt(token: str) -> str:
        return encrypt_pattern.format(token=token)

    def mock_decrypt(token: str) -> str:
        # Extract original token from encrypted format
        if encrypt_pattern.format(token="") in token:
            original = token.replace(encrypt_pattern.format(token=""), "")
            return decrypt_pattern.format(token=original)
        return decrypt_pattern.format(token=token)

    with (
        patch("src.auth.service.encrypt_token", side_effect=mock_encrypt) as mock_enc,
        patch("src.auth.service.decrypt_token", side_effect=mock_decrypt) as mock_dec,
    ):
        yield (mock_enc, mock_dec)


@contextmanager
def mock_time(
    start_time: float = 1000.0,
    end_time: float = 1002.5,
    fixed_time: Optional[float] = None,
) -> Generator[MagicMock, None, None]:
    """Mock time.time() for consistent timing tests.

    Args:
        start_time: Starting timestamp
        end_time: Ending timestamp
        fixed_time: Fixed timestamp (overrides start/end)
    """
    mock_time_module = MagicMock()

    if fixed_time is not None:
        mock_time_module.time.return_value = fixed_time
    else:
        mock_time_module.time.side_effect = [start_time, end_time]

    with (
        patch("time.time", mock_time_module.time),
        patch("src.question.providers.openai_provider.time", mock_time_module),
    ):
        yield mock_time_module


@contextmanager
def mock_database_operations(
    query_results: Optional[List[Any]] = None,
    scalar_result: Optional[Any] = None,
    execute_result: Optional[Any] = None,
) -> Generator[MagicMock, None, None]:
    """Mock database session operations.

    Args:
        query_results: List of results for .all() queries
        scalar_result: Result for .scalar_one_or_none() queries
        execute_result: Custom execute result mock
    """
    mock_session = AsyncMock()

    if execute_result:
        mock_session.execute.return_value = execute_result
    else:
        mock_result = MagicMock()

        if query_results is not None:
            mock_result.scalars.return_value.all.return_value = query_results
        else:
            mock_result.scalars.return_value.all.return_value = []

        if scalar_result is not None:
            mock_result.scalar_one_or_none.return_value = scalar_result
        else:
            mock_result.scalar_one_or_none.return_value = None

        mock_session.execute.return_value = mock_result

    mock_session.get.return_value = scalar_result
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    yield mock_session


@contextmanager
def mock_content_extraction(
    extracted_content: Optional[Dict[str, Any]] = None,
    should_fail: bool = False,
) -> Generator[tuple, None, None]:
    """Mock content extraction workflow components.

    Args:
        extracted_content: Content extraction result
        should_fail: Whether extraction should fail
    """
    if extracted_content is None:
        extracted_content = {
            "101": [
                {"content": "Module 1 test content", "word_count": 100},
            ],
            "102": [
                {"content": "Module 2 test content", "word_count": 150},
            ],
        }

    mock_extractor = AsyncMock()
    mock_summarizer = MagicMock()

    if should_fail:
        mock_extractor.side_effect = RuntimeError("Content extraction failed")
    else:
        mock_extractor.return_value = extracted_content
        mock_summarizer.return_value = {
            "modules_processed": len(extracted_content),
            "total_pages": sum(len(content) for content in extracted_content.values()),
            "total_word_count": sum(
                item["word_count"]
                for content in extracted_content.values()
                for item in content
            ),
        }

    yield (mock_extractor, mock_summarizer)


@contextmanager
def mock_question_generation(
    generated_questions: Optional[Dict[str, List[str]]] = None,
    batch_status: Optional[Dict[str, List[str]]] = None,
    should_fail: bool = False,
) -> Generator[MagicMock, None, None]:
    """Mock question generation service.

    Args:
        generated_questions: Questions by module
        batch_status: Batch success/failure tracking
        should_fail: Whether generation should fail
    """
    if generated_questions is None:
        generated_questions = {
            "101": ["Generated question 1", "Generated question 2"],
            "102": ["Generated question 3"],
        }

    if batch_status is None:
        batch_status = {
            "successful_batches": ["101_multiple_choice", "102_true_false"],
            "failed_batches": [],
        }

    mock_service = MagicMock()
    mock_service.generate_questions_for_quiz_with_batch_tracking = AsyncMock()

    if should_fail:
        mock_service.generate_questions_for_quiz_with_batch_tracking.side_effect = (
            Exception("Generation failed")
        )
    else:
        mock_service.generate_questions_for_quiz_with_batch_tracking.return_value = (
            generated_questions,
            batch_status,
        )

    yield mock_service


# Utility functions for common mock configurations


def create_mock_quiz_response(
    quiz_id: str = "quiz_123", title: str = "Test Quiz"
) -> Dict[str, Any]:
    """Create a standard Canvas quiz response."""
    return {
        "id": quiz_id,
        "title": title,
        "points_possible": 100,
        "assignment_id": f"assignment_{quiz_id}",
    }


def create_mock_user_response(
    canvas_id: int = 12345, name: str = "Test User"
) -> Dict[str, Any]:
    """Create a standard Canvas user response."""
    return {
        "id": canvas_id,
        "name": name,
        "email": f"test{canvas_id}@example.com",
        "login_id": f"user{canvas_id}",
    }


def create_mock_course_response(
    course_id: int = 123, name: str = "Test Course"
) -> Dict[str, Any]:
    """Create a standard Canvas course response."""
    return {
        "id": course_id,
        "name": name,
        "course_code": f"TEST{course_id}",
        "enrollment_term_id": 1,
        "workflow_state": "available",
    }


def create_mock_module_response(
    module_id: int = 456, name: str = "Test Module"
) -> Dict[str, Any]:
    """Create a standard Canvas module response."""
    return {
        "id": module_id,
        "name": name,
        "position": 1,
        "workflow_state": "active",
        "items_count": 5,
    }
