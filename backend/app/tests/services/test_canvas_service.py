import pytest
import httpx
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.services.canvas_service import CanvasService
from app.core.config import settings # To access settings.CANVAS_API_URL

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def canvas_service() -> CanvasService:
    """Fixture to provide a CanvasService instance with a dummy token."""
    return CanvasService(canvas_token="test_token")

MOCK_CANVAS_API_URL = "http://mock-canvas-api"

async def test_create_canvas_quiz_success(canvas_service: CanvasService):
    """Test successful quiz creation in Canvas."""
    course_id = 123
    quiz_title = "Test Quiz"
    quiz_settings = {"description": "A test quiz", "points_possible": 10}
    expected_payload = {
        "title": quiz_title,
        "description": "A test quiz",
        "points_possible": 10,
    }
    mock_response_data = {"id": "q1", "assignment_id": "a1", "title": quiz_title}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response

        response = await canvas_service.create_canvas_quiz(course_id, quiz_title, quiz_settings)

        mock_request.assert_called_once_with(
            "POST",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes",
            headers=canvas_service.headers,
            json=expected_payload,
        )
        assert response == mock_response_data

async def test_create_canvas_quiz_includes_default_points_possible(canvas_service: CanvasService):
    """Test that points_possible defaults to 0 if not in quiz_settings."""
    course_id = 123
    quiz_title = "Test Quiz No Points"
    quiz_settings = {"description": "A test quiz"} # No points_possible
    expected_payload = {
        "title": quiz_title,
        "description": "A test quiz",
        "points_possible": 0, # Should be defaulted
    }
    mock_response_data = {"id": "q2", "assignment_id": "a2", "title": quiz_title}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response

        await canvas_service.create_canvas_quiz(course_id, quiz_title, quiz_settings)

        mock_request.assert_called_once_with(
            "POST",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes",
            headers=canvas_service.headers,
            json=expected_payload,
        )

async def test_add_question_to_canvas_quiz_success(canvas_service: CanvasService):
    """Test successfully adding a question to a Canvas quiz."""
    course_id = 123
    canvas_assignment_id = "a1"
    question_data = {
        "entry_type": "Item",
        "item_body": "<p>What is ...?</p>",
    }
    mock_response_data = {"id": "item1", "item_body": "<p>What is ...?</p>"}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response

        response = await canvas_service.add_question_to_canvas_quiz(
            course_id, canvas_assignment_id, question_data
        )

        mock_request.assert_called_once_with(
            "POST",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes/{canvas_assignment_id}/items",
            headers=canvas_service.headers,
            json=question_data,
        )
        assert response == mock_response_data

async def test_canvas_service_http_status_error(canvas_service: CanvasService):
    """Test handling of HTTPStatusError from Canvas API."""
    course_id = 123
    quiz_title = "Error Quiz"
    quiz_settings = {}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:

        mock_http_error_response = AsyncMock(spec=httpx.Response)
        mock_http_error_response.status_code = 400
        mock_http_error_response.text = "Bad Request from Canvas"

        mock_request.return_value = mock_http_error_response # This is the response object itself
        # Configure raise_for_status on this response object to raise the error
        mock_http_error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Bad Request", request=AsyncMock(), response=mock_http_error_response
        )

        with pytest.raises(HTTPException) as exc_info:
            await canvas_service.create_canvas_quiz(course_id, quiz_title, quiz_settings)

        assert exc_info.value.status_code == 400
        assert "Canvas API error: Bad Request from Canvas" in exc_info.value.detail

async def test_canvas_service_request_error(canvas_service: CanvasService):
    """Test handling of httpx.RequestError (e.g., network issue)."""
    course_id = 123
    quiz_title = "Network Error Quiz"
    quiz_settings = {}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:

        mock_request.side_effect = httpx.RequestError("Network connection failed", request=AsyncMock())

        with pytest.raises(HTTPException) as exc_info:
            await canvas_service.create_canvas_quiz(course_id, quiz_title, quiz_settings)

        assert exc_info.value.status_code == 503 # Service Unavailable
        assert "Error connecting to Canvas API: Network connection failed" in exc_info.value.detail

# --- Tests for additional CanvasService methods ---

async def test_get_canvas_quiz_details_success(canvas_service: CanvasService):
    course_id = 123
    assignment_id = "a1"
    mock_response_data = {"id": "q1", "assignment_id": assignment_id, "title": "Details Quiz"}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response

        response = await canvas_service.get_canvas_quiz_details(course_id, assignment_id)
        mock_request.assert_called_once_with(
            "GET",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}",
            headers=canvas_service.headers,
            json=None,
        )
        assert response == mock_response_data

async def test_update_canvas_quiz_success(canvas_service: CanvasService):
    course_id = 123
    assignment_id = "a1"
    update_data = {"title": "Updated Title"}
    mock_response_data = {"id": "q1", "assignment_id": assignment_id, "title": "Updated Title"}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response

        response = await canvas_service.update_canvas_quiz(course_id, assignment_id, update_data)
        mock_request.assert_called_once_with(
            "PATCH",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}",
            headers=canvas_service.headers,
            json=update_data,
        )
        assert response == mock_response_data

async def test_publish_canvas_quiz_success(canvas_service: CanvasService):
    course_id = 123
    assignment_id = "a1"
    expected_payload = {"published": True}
    mock_response_data = {"id": "q1", "assignment_id": assignment_id, "published": True}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request: # Patch update_canvas_quiz
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response

        response = await canvas_service.publish_canvas_quiz(course_id, assignment_id, True)

        mock_request.assert_called_once_with(
            "PATCH", # publish calls update_canvas_quiz which uses PATCH
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}",
            headers=canvas_service.headers,
            json=expected_payload,
        )
        assert response == mock_response_data


async def test_delete_canvas_quiz_success(canvas_service: CanvasService):
    course_id = 123
    assignment_id = "a1"

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 204 # No content for delete
        mock_response.json.return_value = {} # Should not be called if 204
        mock_request.return_value = mock_response

        await canvas_service.delete_canvas_quiz(course_id, assignment_id)
        mock_request.assert_called_once_with(
            "DELETE",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}",
            headers=canvas_service.headers,
            json=None,
        )

async def test_list_canvas_quiz_items_success(canvas_service: CanvasService):
    course_id = 123
    assignment_id = "a1"
    mock_items_list = [{"id": "item1"}, {"id": "item2"}]
    # Assuming API returns {"quiz_items": [...]} or just [...]
    mock_response_data_dict = {"quiz_items": mock_items_list}
    mock_response_data_list = mock_items_list

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:

        # Test with dict response
        mock_response_dict = AsyncMock(spec=httpx.Response)
        mock_response_dict.status_code = 200
        mock_response_dict.json.return_value = mock_response_data_dict
        mock_request.return_value = mock_response_dict

        response = await canvas_service.list_canvas_quiz_items(course_id, assignment_id)
        assert response == mock_items_list
        mock_request.assert_called_with( # called_with because we call it again
            "GET",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items",
            headers=canvas_service.headers,
            json=None,
        )

        # Test with list response
        mock_response_list_obj = AsyncMock(spec=httpx.Response)
        mock_response_list_obj.status_code = 200
        mock_response_list_obj.json.return_value = mock_response_data_list
        mock_request.return_value = mock_response_list_obj

        response = await canvas_service.list_canvas_quiz_items(course_id, assignment_id)
        assert response == mock_items_list

        # Test with unexpected format
        mock_response_unexpected = AsyncMock(spec=httpx.Response)
        mock_response_unexpected.status_code = 200
        mock_response_unexpected.json.return_value = {"message": "unexpected"} # Not a list
        mock_request.return_value = mock_response_unexpected

        response = await canvas_service.list_canvas_quiz_items(course_id, assignment_id)
        assert response == [] # Should return empty list on unexpected format

async def test_get_canvas_quiz_item_details_success(canvas_service: CanvasService):
    course_id = 123
    assignment_id = "a1"
    item_id = "item1"
    mock_response_data = {"id": item_id, "text": "details"}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response

        response = await canvas_service.get_canvas_quiz_item_details(course_id, assignment_id, item_id)
        mock_request.assert_called_once_with(
            "GET",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items/{item_id}",
            headers=canvas_service.headers,
            json=None,
        )
        assert response == mock_response_data

async def test_update_canvas_quiz_item_success(canvas_service: CanvasService):
    course_id = 123
    assignment_id = "a1"
    item_id = "item1"
    update_data = {"text": "updated text"}
    mock_response_data = {"id": item_id, "text": "updated text"}

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response

        response = await canvas_service.update_canvas_quiz_item(course_id, assignment_id, item_id, update_data)
        mock_request.assert_called_once_with(
            "PATCH",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items/{item_id}",
            headers=canvas_service.headers,
            json=update_data,
        )
        assert response == mock_response_data

async def test_delete_canvas_quiz_item_success(canvas_service: CanvasService):
    course_id = 123
    assignment_id = "a1"
    item_id = "item1"

    with patch("app.services.canvas_service.settings.CANVAS_API_URL", MOCK_CANVAS_API_URL), \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        await canvas_service.delete_canvas_quiz_item(course_id, assignment_id, item_id)
        mock_request.assert_called_once_with(
            "DELETE",
            f"{MOCK_CANVAS_API_URL}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items/{item_id}",
            headers=canvas_service.headers,
            json=None,
        )

# Ensure __init__.py exists in backend/app/tests/services/
# (This is usually handled by file structure, but good to note)
