"""Tests for Canvas service layer."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from tests.common_mocks import mock_canvas_api
from tests.test_data import (
    DEFAULT_CANVAS_QUIZ_RESPONSE,
    DEFAULT_FILE_CONTENT,
    DEFAULT_FILE_INFO,
    DEFAULT_MODULE_ITEMS,
    DEFAULT_PAGE_CONTENT,
    SAMPLE_QUESTIONS_BATCH,
)


@pytest.mark.asyncio
async def test_fetch_canvas_module_items_success():
    """Test successful module items fetch."""
    from src.canvas.service import fetch_canvas_module_items

    with mock_canvas_api(module_items=DEFAULT_MODULE_ITEMS) as _:
        result = await fetch_canvas_module_items("test_token", 456, 789)

    assert result == DEFAULT_MODULE_ITEMS
    assert len(result) == 3
    assert result[0]["title"] == "Test Item 1"


@pytest.mark.asyncio
async def test_fetch_canvas_module_items_with_data_wrapper():
    """Test module items fetch with wrapped data response."""
    from src.canvas.service import fetch_canvas_module_items

    wrapped_response = {
        "data": [{"id": 1, "title": "Wrapped Item", "type": "Page"}],
        "meta": {"total": 1},
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = wrapped_response
        mock_response.raise_for_status.return_value = None

        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        result = await fetch_canvas_module_items("test_token", 456, 789)

    assert result == wrapped_response["data"]
    assert len(result) == 1


@pytest.mark.asyncio
async def test_fetch_canvas_module_items_404_returns_empty():
    """Test that 404 errors return empty list."""
    from src.canvas.service import fetch_canvas_module_items

    with mock_canvas_api(should_fail=True, status_code=404) as _:
        result = await fetch_canvas_module_items("test_token", 456, 789)

    assert result == []


@pytest.mark.asyncio
async def test_fetch_canvas_module_items_http_error_raises_exception():
    """Test that non-404 HTTP errors raise ExternalServiceError."""
    from src.canvas.service import fetch_canvas_module_items
    from src.exceptions import ExternalServiceError

    with mock_canvas_api(should_fail=True, status_code=500) as _:
        with pytest.raises(ExternalServiceError) as exc_info:
            await fetch_canvas_module_items("test_token", 456, 789)

        assert "Failed to fetch module 789 items" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_canvas_page_content_success():
    """Test successful page content fetch."""
    from src.canvas.service import fetch_canvas_page_content

    with mock_canvas_api(page_content=DEFAULT_PAGE_CONTENT) as _:
        result = await fetch_canvas_page_content("test_token", 456, "test-page")

    assert result == DEFAULT_PAGE_CONTENT
    assert result["title"] == "Test Page"
    assert "comprehensive test page content" in result["body"]


@pytest.mark.asyncio
async def test_fetch_canvas_page_content_404_returns_empty():
    """Test that 404 errors return empty dict."""
    from src.canvas.service import fetch_canvas_page_content

    with mock_canvas_api(should_fail=True, status_code=404) as _:
        result = await fetch_canvas_page_content("test_token", 456, "missing-page")

    assert result == {}


@pytest.mark.asyncio
async def test_fetch_canvas_file_info_success():
    """Test successful file info fetch."""
    from src.canvas.service import fetch_canvas_file_info

    with mock_canvas_api(file_info=DEFAULT_FILE_INFO) as _:
        result = await fetch_canvas_file_info("test_token", 456, 789)

    assert result == DEFAULT_FILE_INFO
    assert result["display_name"] == "test_document.pdf"
    assert result["size"] == 12345


@pytest.mark.asyncio
async def test_download_canvas_file_content_success():
    """Test successful file content download."""
    from src.canvas.service import download_canvas_file_content

    with mock_canvas_api(file_content=DEFAULT_FILE_CONTENT) as _:
        result = await download_canvas_file_content("https://example.com/file.pdf")

    assert result == DEFAULT_FILE_CONTENT


@pytest.mark.asyncio
async def test_download_canvas_file_content_follows_redirects():
    """Test that file download follows redirects."""
    from src.canvas.service import download_canvas_file_content

    mock_content = b"Redirected file content"

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.content = mock_content
        mock_response.raise_for_status.return_value = None

        mock_get = mock_client.return_value.__aenter__.return_value.get
        mock_get.return_value = mock_response

        result = await download_canvas_file_content("https://example.com/file.pdf")

    # Verify follow_redirects=True was called
    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args[1]
    assert call_kwargs["follow_redirects"] is True
    assert call_kwargs["timeout"] == 60.0

    assert result == mock_content


@pytest.mark.asyncio
async def test_create_canvas_quiz_success():
    """Test successful quiz creation."""
    from src.canvas.service import create_canvas_quiz

    with mock_canvas_api(quiz_response=DEFAULT_CANVAS_QUIZ_RESPONSE) as _:
        result = await create_canvas_quiz("test_token", 123, "Test Quiz", 100)

    assert result == DEFAULT_CANVAS_QUIZ_RESPONSE
    assert result["title"] == "Test Quiz"
    assert result["points_possible"] == 100


@pytest.mark.asyncio
async def test_create_canvas_quiz_with_correct_payload():
    """Test that quiz creation sends correct payload."""
    from src.canvas.service import create_canvas_quiz

    mock_quiz_response = {"id": "quiz_123", "title": "Test Quiz"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_quiz_response
        mock_response.raise_for_status.return_value = None

        mock_post = mock_client.return_value.__aenter__.return_value.post
        mock_post.return_value = mock_response

        await create_canvas_quiz("test_token", 123, "Math Quiz", 50)

    # Verify the payload structure
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]

    expected_payload = {
        "quiz": {
            "title": "Math Quiz",
            "points_possible": 50,
            "published": False,
            "quiz_settings": {
                "shuffle_questions": False,
                "shuffle_answers": False,
                "has_time_limit": False,
            },
        }
    }

    assert call_kwargs["json"] == expected_payload


@pytest.mark.asyncio
async def test_create_canvas_quiz_items_success():
    """Test successful quiz items creation."""
    from src.canvas.service import create_canvas_quiz_items

    # Use centralized sample questions
    mock_questions = [
        {
            "id": "q1",
            **SAMPLE_QUESTIONS_BATCH[0],
            "question_type": "multiple_choice",
        },
        {
            "id": "q2",
            **SAMPLE_QUESTIONS_BATCH[1],
            "question_type": "multiple_choice",
        },
    ]

    with mock_canvas_api() as _:
        result = await create_canvas_quiz_items(
            "test_token", 123, "quiz_456", mock_questions
        )

    assert len(result) == 2
    assert all(item["success"] for item in result)
    assert result[0]["question_id"] == "q1"
    assert result[1]["question_id"] == "q2"


def test_convert_question_to_canvas_format_multiple_choice():
    """Test converting multiple choice question to Canvas format."""
    from src.canvas.service import convert_question_to_canvas_format

    question = {
        "id": "test_q1",
        "question_text": "What is the capital of France?",
        "option_a": "London",
        "option_b": "Paris",
        "option_c": "Berlin",
        "option_d": "Madrid",
        "correct_answer": "B",
        "question_type": "multiple_choice",
    }

    result = convert_question_to_canvas_format(question, 1)

    # Verify structure
    assert "item" in result
    item = result["item"]

    assert item["entry_type"] == "Item"
    assert item["position"] == 1
    assert item["points_possible"] == 1

    # Verify entry data
    entry = item["entry"]
    assert entry["interaction_type_slug"] == "choice"
    assert "What is the capital of France?" in entry["item_body"]
    assert entry["scoring_data"]["value"] == "choice_2"  # B = index 1, so choice_2

    # Verify choices
    choices = entry["interaction_data"]["choices"]
    assert len(choices) == 4
    assert choices[0]["item_body"] == "<p>London</p>"
    assert choices[1]["item_body"] == "<p>Paris</p>"


@pytest.mark.parametrize(
    "correct_letter,expected_index",
    [
        ("A", 0),  # A = index 0
        ("B", 1),  # B = index 1
        ("C", 2),  # C = index 2
        ("D", 3),  # D = index 3
        ("X", 0),  # Invalid answer defaults to A = index 0
    ],
)
def test_convert_question_correct_answer_mapping(correct_letter, expected_index):
    """Test correct answer mapping for different options."""
    from src.canvas.service import convert_question_to_canvas_format

    question = {
        "id": "test",
        "question_text": "Test question",
        "option_a": "Option A",
        "option_b": "Option B",
        "option_c": "Option C",
        "option_d": "Option D",
        "correct_answer": correct_letter,
        "question_type": "multiple_choice",
    }

    result = convert_question_to_canvas_format(question, 1)

    # Get the choices and scoring data
    entry = result["item"]["entry"]
    choices = entry["interaction_data"]["choices"]
    scoring_value = entry["scoring_data"]["value"]

    # The scoring value should match the UUID of the choice at the expected index
    expected_choice_id = choices[expected_index]["id"]
    assert scoring_value == expected_choice_id


@pytest.mark.asyncio
async def test_canvas_service_error_handling():
    """Test error handling consistency across different operations."""
    from src.canvas.service import (
        create_canvas_quiz,
        download_canvas_file_content,
        fetch_canvas_file_info,
        fetch_canvas_module_items,
    )
    from src.exceptions import ExternalServiceError

    # Mock time.sleep to avoid actual delays during retries
    with (
        patch("httpx.AsyncClient") as mock_client,
        patch("asyncio.sleep") as mock_sleep,
    ):
        # Simulate network failure
        mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
            "Network down"
        )
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception(
            "Network down"
        )

        # All operations should handle errors gracefully
        module_items = await fetch_canvas_module_items("token", 123, 456)
        assert module_items == []

        file_info = await fetch_canvas_file_info("token", 123, 789)
        assert file_info == {}

        file_content = await download_canvas_file_content("https://example.com/file")
        assert file_content == b""

        # Quiz creation should raise exception after retries
        with pytest.raises(ExternalServiceError):
            await create_canvas_quiz("token", 123, "Test Quiz", 100)


# Fill-in-Blank Canvas Format Conversion Tests


def test_convert_question_to_canvas_format_fill_in_blank_single_blank():
    """Test Canvas format conversion for single blank Fill-in-Blank question."""
    from src.canvas.service import convert_question_to_canvas_format

    question_data = {
        "id": str(uuid.uuid4()),
        "question_text": "The capital of France is [blank_1].",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "Paris",
                "answer_variations": ["paris", "PARIS"],
                "case_sensitive": False,
            }
        ],
        "explanation": "Paris is the capital of France.",
        "question_type": "fill_in_blank",
    }

    result = convert_question_to_canvas_format(question_data, position=1)

    # Check item structure
    assert "item" in result
    item = result["item"]
    assert item["entry_type"] == "Item"
    assert item["points_possible"] == 1
    assert item["position"] == 1

    # Check entry structure
    entry = item["entry"]
    assert entry["interaction_type_slug"] == "rich-fill-blank"
    # Item body should have span tags with UUID instead of placeholder
    assert '<span id="' in entry["item_body"]
    assert entry["scoring_algorithm"] == "MultipleMethods"

    # Check interaction data
    interaction_data = entry["interaction_data"]
    assert "blanks" in interaction_data
    assert len(interaction_data["blanks"]) == 1
    blank = interaction_data["blanks"][0]
    assert blank["answer_type"] == "openEntry"
    assert "id" in blank  # Should have UUID

    # Check scoring data
    scoring_data = entry["scoring_data"]
    assert "value" in scoring_data
    assert len(scoring_data["value"]) == 1  # Main answer + 2 variations
    # Working item body should have the answer filled in
    assert "Paris" in scoring_data["working_item_body"]

    # Check scoring values
    scoring_values = scoring_data["value"]
    answers = [sv["scoring_data"]["value"] for sv in scoring_values]
    assert ["Paris", "paris", "PARIS"] in answers

    # Check scoring algorithm
    for sv in scoring_values:
        assert sv["scoring_algorithm"] == "TextInChoices"


def test_convert_question_to_canvas_format_fill_in_blank_multiple_blanks():
    """Test Canvas format conversion for multiple blank Fill-in-Blank question."""
    from src.canvas.service import convert_question_to_canvas_format

    question_data = {
        "id": str(uuid.uuid4()),
        "question_text": "The capital of [blank_1] is [blank_2] and it is located in [blank_3].",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "France",
                "case_sensitive": False,
            },
            {
                "position": 2,
                "correct_answer": "Paris",
                "answer_variations": ["paris"],
                "case_sensitive": False,
            },
            {
                "position": 3,
                "correct_answer": "Europe",
                "case_sensitive": False,
            },
        ],
        "explanation": "Paris is the capital of France in Europe.",
        "question_type": "fill_in_blank",
    }

    result = convert_question_to_canvas_format(question_data, position=1)

    # Check item structure
    item = result["item"]
    assert item["points_possible"] == 3  # One point per blank

    # Check interaction data
    interaction_data = item["entry"]["interaction_data"]
    assert len(interaction_data["blanks"]) == 3

    # Check scoring data
    scoring_data = item["entry"]["scoring_data"]
    assert len(scoring_data["value"]) == 3  # 3 main answers + 1 variation

    # Verify all blanks have unique UUIDs
    blank_ids = [blank["id"] for blank in interaction_data["blanks"]]
    assert len(set(blank_ids)) == 3  # All unique

    # Verify scoring values contain all expected answers
    answers = [sv["scoring_data"]["value"] for sv in scoring_data["value"]]
    assert ["France"] in answers
    assert ["Paris", "paris"] in answers
    assert ["Europe"] in answers


def test_convert_question_to_canvas_format_fill_in_blank_case_sensitive():
    """Test Canvas format conversion for case-sensitive Fill-in-Blank question."""
    from src.canvas.service import convert_question_to_canvas_format

    question_data = {
        "id": str(uuid.uuid4()),
        "question_text": "The chemical symbol for gold is [blank_1].",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "Au",
                "case_sensitive": True,
            }
        ],
        "question_type": "fill_in_blank",
    }

    result = convert_question_to_canvas_format(question_data, position=1)

    # Check scoring data
    scoring_data = result["item"]["entry"]["scoring_data"]
    assert len(scoring_data["value"]) == 1  # Only main answer

    # Check scoring algorithm
    scoring_value = scoring_data["value"][0]
    assert scoring_value["scoring_algorithm"] == "TextInChoices"
    assert scoring_value["scoring_data"]["value"] == ["Au"]


def test_convert_question_to_canvas_format_fill_in_blank_no_variations():
    """Test Canvas format conversion for Fill-in-Blank question without variations."""
    from src.canvas.service import convert_question_to_canvas_format

    question_data = {
        "id": str(uuid.uuid4()),
        "question_text": "The capital of France is [blank_1].",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "Paris",
                "case_sensitive": False,
            }
        ],
        "question_type": "fill_in_blank",
    }

    result = convert_question_to_canvas_format(question_data, position=1)

    # Check scoring data
    scoring_data = result["item"]["entry"]["scoring_data"]
    assert len(scoring_data["value"]) == 1  # Only main answer

    # Check scoring value
    scoring_value = scoring_data["value"][0]
    assert scoring_value["scoring_data"]["value"] == ["Paris"]
    assert scoring_value["scoring_algorithm"] == "TextInChoices"


def test_convert_question_to_canvas_format_fill_in_blank_with_explanation():
    """Test Canvas format conversion preserves explanation field."""
    from src.canvas.service import convert_question_to_canvas_format

    question_data = {
        "id": str(uuid.uuid4()),
        "question_text": "The capital of France is [blank_1].",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "Paris",
                "case_sensitive": False,
            }
        ],
        "explanation": "Paris is the capital and largest city of France.",
        "question_type": "fill_in_blank",
    }

    result = convert_question_to_canvas_format(question_data, position=1)

    # Canvas format should include the question but explanation handling
    # depends on Canvas New Quiz API capabilities
    # The item_body should have span tags with UUIDs for blanks
    assert '<span id="' in result["item"]["entry"]["item_body"]
    assert "The capital of France" in result["item"]["entry"]["item_body"]


def test_convert_question_to_canvas_format_fill_in_blank_uuid_generation():
    """Test that UUIDs are properly generated for blanks."""
    from src.canvas.service import convert_question_to_canvas_format

    question_data = {
        "id": str(uuid.uuid4()),
        "question_text": "Fill [blank_1] and [blank_2].",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "blank1",
                "case_sensitive": False,
            },
            {
                "position": 2,
                "correct_answer": "blank2",
                "case_sensitive": False,
            },
        ],
        "question_type": "fill_in_blank",
    }

    result = convert_question_to_canvas_format(question_data, position=1)

    # Check that UUIDs are generated
    interaction_data = result["item"]["entry"]["interaction_data"]
    blank_ids = [blank["id"] for blank in interaction_data["blanks"]]

    # All IDs should be valid UUIDs
    for blank_id in blank_ids:
        uuid.UUID(blank_id)  # Will raise ValueError if not valid UUID

    # Check that scoring data uses the same UUIDs
    scoring_data = result["item"]["entry"]["scoring_data"]
    scoring_ids = [sv["id"] for sv in scoring_data["value"]]

    # All scoring IDs should be in the blank IDs
    for scoring_id in scoring_ids:
        assert scoring_id in blank_ids


def test_convert_question_to_canvas_format_multiple_choice():
    """Test Canvas format conversion for Multiple Choice question (regression test)."""
    from src.canvas.service import convert_question_to_canvas_format

    question_data = {
        "id": str(uuid.uuid4()),
        "question_text": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": "B",
        "question_type": "multiple_choice",
    }

    result = convert_question_to_canvas_format(question_data, position=1)

    # Check item structure
    item = result["item"]
    assert item["entry_type"] == "Item"
    assert item["points_possible"] == 1
    assert item["position"] == 1

    # Check entry structure
    entry = item["entry"]
    assert entry["interaction_type_slug"] == "choice"
    assert entry["item_body"] == "<p>What is 2+2?</p>"
    assert entry["scoring_algorithm"] == "Equivalence"

    # Check interaction data
    interaction_data = entry["interaction_data"]
    assert "choices" in interaction_data
    assert len(interaction_data["choices"]) == 4

    # Check scoring data - should be UUID format now
    scoring_data = entry["scoring_data"]
    # The correct answer should correspond to option B (index 1 in choices)
    choices = interaction_data["choices"]
    option_b_id = choices[1]["id"]  # Get the UUID for option B
    assert scoring_data["value"] == option_b_id


def test_convert_question_to_canvas_format_unsupported_type():
    """Test Canvas format conversion with unsupported question type."""
    from src.canvas.service import convert_question_to_canvas_format

    question_data = {
        "id": str(uuid.uuid4()),
        "question_text": "Unsupported question",
        "question_type": "unsupported_type",
    }

    with pytest.raises(ValueError, match="Unsupported question type for Canvas export"):
        convert_question_to_canvas_format(question_data, position=1)


def test_convert_question_to_canvas_format_mixed_case_sensitivity():
    """Test Canvas format conversion with mixed case sensitivity."""
    from src.canvas.service import convert_question_to_canvas_format

    question_data = {
        "id": str(uuid.uuid4()),
        "question_text": "Enter [blank_1] and [blank_2].",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "Paris",
                "case_sensitive": False,
            },
            {
                "position": 2,
                "correct_answer": "Au",
                "case_sensitive": True,
            },
        ],
        "question_type": "fill_in_blank",
    }

    result = convert_question_to_canvas_format(question_data, position=1)

    # Check scoring data
    scoring_data = result["item"]["entry"]["scoring_data"]
    assert len(scoring_data["value"]) == 2  # One for each blank

    # Check scoring algorithms
    scoring_values = scoring_data["value"]
    algorithms = [sv["scoring_algorithm"] for sv in scoring_values]
    # All should use TextContainsAnswer in the new implementation
    for algorithm in algorithms:
        assert algorithm == "TextInChoices"
