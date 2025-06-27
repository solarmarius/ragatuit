import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models import Question, Quiz, User
from app.services.canvas_quiz_export import CanvasQuizExportService


@pytest.fixture
def mock_user() -> User:
    """Create a mock user for testing."""
    return User(
        id=uuid.uuid4(),
        canvas_id=12345,
        name="Test User",
        access_token="encrypted_token",
        refresh_token="encrypted_refresh",
    )


@pytest.fixture
def mock_quiz(mock_user: User) -> Quiz:
    """Create a mock quiz for testing."""
    return Quiz(
        id=uuid.uuid4(),
        owner_id=mock_user.id,
        canvas_course_id=37823,
        canvas_course_name="Test Course",
        title="Test Quiz",
        selected_modules='{"173467": "Test Module"}',
        question_count=10,
        export_status="pending",
    )


@pytest.fixture
def mock_questions(mock_quiz: Quiz) -> list[Question]:
    """Create mock approved questions for testing."""
    questions = []
    for i in range(3):
        question = Question(
            id=uuid.uuid4(),
            quiz_id=mock_quiz.id,
            question_text=f"Test question {i + 1}?",
            option_a=f"Option A {i + 1}",
            option_b=f"Option B {i + 1}",
            option_c=f"Option C {i + 1}",
            option_d=f"Option D {i + 1}",
            correct_answer="A",
            is_approved=True,
            approved_at=datetime.now(timezone.utc),
        )
        questions.append(question)
    return questions


@pytest.fixture
def mock_question_data() -> list[dict[str, Any]]:
    """Create mock question dictionaries for testing."""
    question_data = []
    for i in range(3):
        question_data.append(
            {
                "id": uuid.uuid4(),
                "question_text": f"Test question {i + 1}?",
                "option_a": f"Option A {i + 1}",
                "option_b": f"Option B {i + 1}",
                "option_c": f"Option C {i + 1}",
                "option_d": f"Option D {i + 1}",
                "correct_answer": "A",
            }
        )
    return question_data


@pytest.fixture
def export_service() -> CanvasQuizExportService:
    """Create CanvasQuizExportService instance."""
    return CanvasQuizExportService("test_canvas_token")


class TestCanvasQuizExportService:
    """Test cases for CanvasQuizExportService."""

    def test_init(self) -> None:
        """Test service initialization."""
        service = CanvasQuizExportService("test_token")
        assert service.canvas_token == "test_token"
        assert service.canvas_base_url == "http://canvas-mock:8001/api"

    def test_convert_question_to_canvas_item(
        self, export_service: CanvasQuizExportService, mock_quiz: Quiz
    ) -> None:
        """Test question to Canvas item conversion."""
        question_id = uuid.uuid4()
        question = {
            "id": question_id,
            "question_text": "What is 2+2?",
            "option_a": "3",
            "option_b": "4",
            "option_c": "5",
            "option_d": "6",
            "correct_answer": "B",
        }

        result = export_service._convert_question_to_canvas_item(question, 1)

        # Check structure
        assert "item" in result
        item = result["item"]

        assert item["id"] == f"item_{question_id}"
        assert item["entry_type"] == "Item"
        assert item["position"] == 1
        assert item["item_type"] == "Question"
        assert item["points_possible"] == 1
        assert item["properties"]["shuffle_answers"] is True

        # Check entry structure
        entry = item["entry"]
        assert entry["interaction_type_slug"] == "choice"
        assert entry["item_body"] == "<p>What is 2+2?</p>"
        assert entry["scoring_algorithm"] == "Equivalence"
        assert entry["scoring_data"]["value"] == "choice_2"  # B = index 1, so choice_2

        # Check choices
        choices = entry["interaction_data"]["choices"]
        assert len(choices) == 4
        assert choices[0]["id"] == "choice_1"
        assert choices[0]["item_body"] == "<p>3</p>"
        assert choices[1]["id"] == "choice_2"
        assert choices[1]["item_body"] == "<p>4</p>"

    def test_convert_question_correct_answer_mapping(
        self, export_service: CanvasQuizExportService, mock_quiz: Quiz
    ) -> None:
        """Test correct answer mapping for all options."""
        test_cases = [
            ("A", "choice_1"),
            ("B", "choice_2"),
            ("C", "choice_3"),
            ("D", "choice_4"),
        ]

        for correct_answer, expected_choice in test_cases:
            question = {
                "id": uuid.uuid4(),
                "question_text": "Test question?",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "correct_answer": correct_answer,
            }

            result = export_service._convert_question_to_canvas_item(question, 1)
            scoring_data = result["item"]["entry"]["scoring_data"]
            assert scoring_data["value"] == expected_choice

    @pytest.mark.asyncio
    async def test_create_canvas_quiz_success(
        self, export_service: CanvasQuizExportService
    ) -> None:
        """Test successful Canvas quiz creation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "assignment_id": "quiz_12345",
            "title": "Test Quiz",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await export_service.create_canvas_quiz(
                course_id=37823,
                title="Test Quiz",
                total_points=10,
            )

            assert result["assignment_id"] == "quiz_12345"
            assert result["title"] == "Test Quiz"

            # Verify API call
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args

            assert (
                call_args[0][0]
                == "http://canvas-mock:8001/api/quiz/v1/courses/37823/quizzes"
            )
            assert (
                call_args[1]["headers"]["Authorization"] == "Bearer test_canvas_token"
            )

            quiz_data = call_args[1]["json"]
            assert quiz_data["title"] == "Test Quiz"
            assert quiz_data["points_possible"] == 10
            assert quiz_data["quiz_settings"]["shuffle_questions"] is True

    @pytest.mark.asyncio
    async def test_create_canvas_quiz_api_error(
        self, export_service: CanvasQuizExportService
    ) -> None:
        """Test Canvas quiz creation API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await export_service.create_canvas_quiz(
                    course_id=37823,
                    title="Test Quiz",
                    total_points=10,
                )

    @pytest.mark.asyncio
    async def test_create_quiz_items_success(
        self,
        export_service: CanvasQuizExportService,
        mock_question_data: list[dict[str, Any]],
    ) -> None:
        """Test successful Canvas quiz items creation."""
        mock_responses = []
        for i, _question in enumerate(mock_question_data):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": f"item_{i + 1}"}
            mock_response.raise_for_status = MagicMock()
            mock_responses.append(mock_response)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_responses
            )

            results = await export_service.create_quiz_items(
                course_id=37823,
                quiz_id="quiz_12345",
                questions=mock_question_data,
            )

            assert len(results) == 3
            for i, result in enumerate(results):
                assert result["success"] is True
                assert result["item_id"] == f"item_{i + 1}"
                assert result["position"] == i + 1

    @pytest.mark.asyncio
    async def test_create_quiz_items_partial_failure(
        self,
        export_service: CanvasQuizExportService,
        mock_question_data: list[dict[str, Any]],
    ) -> None:
        """Test Canvas quiz items creation with partial failures."""
        # First item succeeds, second fails, third succeeds
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {"id": "item_1"}
        mock_response_1.raise_for_status = MagicMock()

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 400
        mock_response_2.text = "Bad Request"
        mock_response_2.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response_2
        )

        mock_response_3 = MagicMock()
        mock_response_3.status_code = 200
        mock_response_3.json.return_value = {"id": "item_3"}
        mock_response_3.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=[mock_response_1, mock_response_2, mock_response_3]
            )

            results = await export_service.create_quiz_items(
                course_id=37823,
                quiz_id="quiz_12345",
                questions=mock_question_data,
            )

            assert len(results) == 3
            assert results[0]["success"] is True
            assert results[0]["item_id"] == "item_1"

            assert results[1]["success"] is False
            assert "HTTP 400" in results[1]["error"]

            assert results[2]["success"] is True
            assert results[2]["item_id"] == "item_3"

    @pytest.mark.asyncio
    async def test_export_quiz_to_canvas_success(
        self,
        export_service: CanvasQuizExportService,
        mock_quiz: Quiz,
        mock_questions: list[Question],
    ) -> None:
        """Test complete quiz export to Canvas."""
        with (
            patch("app.services.canvas_quiz_export.Session") as mock_session_class,
            patch("app.services.canvas_quiz_export.get_quiz_by_id") as mock_get_quiz,
            patch(
                "app.services.canvas_quiz_export.get_approved_questions_by_quiz_id"
            ) as mock_get_questions,
            patch.object(export_service, "create_canvas_quiz") as mock_create_quiz,
            patch.object(export_service, "create_quiz_items") as mock_create_items,
        ):
            # Setup mocks
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session

            mock_get_quiz.return_value = mock_quiz
            mock_get_questions.return_value = mock_questions

            mock_create_quiz.return_value = {"id": "quiz_12345"}
            mock_create_items.return_value = [
                {"success": True, "question_id": q.id, "item_id": f"item_{i}"}
                for i, q in enumerate(mock_questions)
            ]

            result = await export_service.export_quiz_to_canvas(mock_quiz.id)

            assert result["success"] is True
            assert result["canvas_quiz_id"] == "quiz_12345"
            assert result["exported_questions"] == 3
            assert result["message"] == "Quiz successfully exported to Canvas"

            # Verify quiz status was updated
            assert mock_quiz.export_status == "completed"
            assert mock_quiz.canvas_quiz_id == "quiz_12345"
            assert mock_quiz.exported_at is not None

    @pytest.mark.asyncio
    async def test_export_quiz_already_exported(
        self, export_service: CanvasQuizExportService, mock_quiz: Quiz
    ) -> None:
        """Test export of already exported quiz."""
        mock_quiz.export_status = "completed"
        mock_quiz.canvas_quiz_id = "existing_quiz_123"

        with (
            patch("app.services.canvas_quiz_export.Session") as mock_session_class,
            patch("app.services.canvas_quiz_export.get_quiz_by_id") as mock_get_quiz,
        ):
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_get_quiz.return_value = mock_quiz

            result = await export_service.export_quiz_to_canvas(mock_quiz.id)

            assert result["success"] is True
            assert result["already_exported"] is True
            assert result["canvas_quiz_id"] == "existing_quiz_123"
            assert result["message"] == "Quiz already exported to Canvas"

    @pytest.mark.asyncio
    async def test_export_quiz_already_processing(
        self, export_service: CanvasQuizExportService, mock_quiz: Quiz
    ) -> None:
        """Test export of quiz already being processed."""
        mock_quiz.export_status = "processing"

        with (
            patch("app.services.canvas_quiz_export.Session") as mock_session_class,
            patch("app.services.canvas_quiz_export.get_quiz_by_id") as mock_get_quiz,
        ):
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_get_quiz.return_value = mock_quiz

            result = await export_service.export_quiz_to_canvas(mock_quiz.id)

            assert result["success"] is False
            assert result["export_in_progress"] is True
            assert result["message"] == "Quiz export is already in progress"

    @pytest.mark.asyncio
    async def test_export_quiz_not_found(
        self, export_service: CanvasQuizExportService
    ) -> None:
        """Test export of non-existent quiz."""
        quiz_id = uuid.uuid4()

        with (
            patch("app.services.canvas_quiz_export.Session") as mock_session_class,
            patch("app.services.canvas_quiz_export.get_quiz_by_id") as mock_get_quiz,
        ):
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_get_quiz.return_value = None

            with pytest.raises(ValueError, match=f"Quiz {quiz_id} not found"):
                await export_service.export_quiz_to_canvas(quiz_id)

    @pytest.mark.asyncio
    async def test_export_quiz_no_approved_questions(
        self, export_service: CanvasQuizExportService, mock_quiz: Quiz
    ) -> None:
        """Test export of quiz with no approved questions."""
        with (
            patch("app.services.canvas_quiz_export.Session") as mock_session_class,
            patch("app.services.canvas_quiz_export.get_quiz_by_id") as mock_get_quiz,
            patch(
                "app.services.canvas_quiz_export.get_approved_questions_by_quiz_id"
            ) as mock_get_questions,
        ):
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_get_quiz.return_value = mock_quiz
            mock_get_questions.return_value = []

            with pytest.raises(ValueError, match="has no approved questions to export"):
                await export_service.export_quiz_to_canvas(mock_quiz.id)

    @pytest.mark.asyncio
    async def test_export_quiz_canvas_error_updates_status(
        self,
        export_service: CanvasQuizExportService,
        mock_quiz: Quiz,
        mock_questions: list[Question],
    ) -> None:
        """Test that Canvas API errors update quiz status to failed."""
        with (
            patch("app.services.canvas_quiz_export.Session") as mock_session_class,
            patch("app.services.canvas_quiz_export.get_quiz_by_id") as mock_get_quiz,
            patch(
                "app.services.canvas_quiz_export.get_approved_questions_by_quiz_id"
            ) as mock_get_questions,
            patch.object(export_service, "create_canvas_quiz") as mock_create_quiz,
        ):
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session

            mock_get_quiz.return_value = mock_quiz
            mock_get_questions.return_value = mock_questions
            mock_create_quiz.side_effect = Exception("Canvas API Error")

            with pytest.raises(Exception, match="Canvas API Error"):
                await export_service.export_quiz_to_canvas(mock_quiz.id)

            # Verify status was updated to failed
            assert mock_quiz.export_status == "failed"
