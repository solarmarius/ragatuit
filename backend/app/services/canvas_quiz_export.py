from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx

from app.core.config import settings
from app.core.db import get_async_session
from app.core.exceptions import (
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)
from app.core.logging_config import get_logger
from app.core.retry import retry_on_failure
from app.crud import get_approved_questions_by_quiz_id_async, get_quiz_for_update
from app.models import Question
from app.services.url_builder import CanvasURLBuilder

logger = get_logger("canvas_quiz_export")


class CanvasQuizExportService:
    """
    Service for exporting quizzes and questions to Canvas LMS.

    This service handles the complete workflow of creating quizzes in Canvas
    and adding approved questions as quiz items using the Canvas New Quizzes API.
    """

    def __init__(self, canvas_token: str):
        self.canvas_token = canvas_token
        self.api_timeout = settings.CANVAS_API_TIMEOUT

        # Initialize URL builder with settings
        base_url = str(settings.CANVAS_BASE_URL)
        if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
            base_url = str(settings.CANVAS_MOCK_URL)
        self.url_builder = CanvasURLBuilder(base_url, settings.CANVAS_API_VERSION)

    async def export_quiz_to_canvas(self, quiz_id: UUID) -> dict[str, Any]:
        """
        Main orchestration function to export a quiz to Canvas.

        Args:
            quiz_id: UUID of the quiz to export

        Returns:
            dict: Export result with success status and Canvas quiz information

        Raises:
            ValueError: If quiz not found or has no approved questions
            HTTPException: If Canvas API calls fail
        """
        logger.info(
            "canvas_quiz_export_started",
            quiz_id=str(quiz_id),
        )

        try:
            async with get_async_session() as session:
                quiz = await get_quiz_for_update(session, quiz_id)

                if not quiz:
                    logger.error(
                        "canvas_quiz_export_quiz_not_found",
                        quiz_id=str(quiz_id),
                    )
                    raise ResourceNotFoundError(f"Quiz {quiz_id}")

                if quiz.export_status == "completed" and quiz.canvas_quiz_id:
                    logger.warning(
                        "canvas_quiz_export_already_exported",
                        quiz_id=str(quiz_id),
                        canvas_quiz_id=quiz.canvas_quiz_id,
                    )
                    return {
                        "success": True,
                        "canvas_quiz_id": quiz.canvas_quiz_id,
                        "exported_questions": 0,
                        "message": "Quiz already exported to Canvas",
                        "already_exported": True,
                    }

                if quiz.export_status == "processing":
                    logger.warning(
                        "canvas_quiz_export_already_processing",
                        quiz_id=str(quiz_id),
                        current_status=quiz.export_status,
                    )
                    return {
                        "success": False,
                        "message": "Quiz export is already in progress",
                        "export_in_progress": True,
                    }

                approved_questions = await get_approved_questions_by_quiz_id_async(
                    session, quiz_id
                )

                if not approved_questions:
                    logger.error(
                        "canvas_quiz_export_no_approved_questions",
                        quiz_id=str(quiz_id),
                    )
                    raise ValidationError("Quiz has no approved questions to export")

                question_data = [
                    {
                        "id": question.id,
                        "question_text": question.question_text,
                        "option_a": question.option_a,
                        "option_b": question.option_b,
                        "option_c": question.option_c,
                        "option_d": question.option_d,
                        "correct_answer": question.correct_answer,
                    }
                    for question in approved_questions
                ]

                quiz_course_id = quiz.canvas_course_id
                quiz_title = quiz.title

                quiz.export_status = "processing"
                await session.commit()

                logger.info(
                    "canvas_quiz_export_processing",
                    quiz_id=str(quiz_id),
                    course_id=quiz_course_id,
                    approved_questions_count=len(question_data),
                )

            canvas_quiz = await self.create_canvas_quiz(
                course_id=quiz_course_id,
                title=quiz_title,
                total_points=len(question_data),
            )

            canvas_quiz_id = canvas_quiz["id"]
            logger.info(
                "canvas_quiz_created",
                quiz_id=str(quiz_id),
                canvas_quiz_id=canvas_quiz_id,
            )

            exported_items = await self.create_quiz_items(
                course_id=quiz_course_id,
                quiz_id=canvas_quiz_id,
                questions=question_data,
            )

            async with get_async_session() as session:
                quiz = await get_quiz_for_update(session, quiz_id)

                if quiz:
                    quiz.canvas_quiz_id = canvas_quiz_id
                    quiz.export_status = "completed"
                    quiz.exported_at = datetime.now(timezone.utc)

                    for question_dict, item_result in zip(
                        question_data, exported_items, strict=False
                    ):
                        if item_result["success"]:
                            question_obj = await session.get(
                                Question, question_dict["id"]
                            )
                            if question_obj:
                                question_obj.canvas_item_id = item_result["item_id"]

                    await session.commit()

            logger.info(
                "canvas_quiz_export_completed",
                quiz_id=str(quiz_id),
                canvas_quiz_id=canvas_quiz_id,
                exported_questions=len([r for r in exported_items if r["success"]]),
            )

            return {
                "success": True,
                "canvas_quiz_id": canvas_quiz_id,
                "exported_questions": len([r for r in exported_items if r["success"]]),
                "message": "Quiz successfully exported to Canvas",
            }

        except Exception as e:
            try:
                async with get_async_session() as error_session:
                    quiz = await get_quiz_for_update(error_session, quiz_id)
                    if quiz:
                        quiz.export_status = "failed"
                        await error_session.commit()
            except Exception as update_error:
                logger.error(
                    "canvas_quiz_export_status_update_failed",
                    quiz_id=str(quiz_id),
                    error=str(update_error),
                )

            logger.error(
                "canvas_quiz_export_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    @retry_on_failure(max_attempts=3, initial_delay=2.0)
    async def create_canvas_quiz(
        self, course_id: int, title: str, total_points: int
    ) -> dict[str, Any]:
        """
        Create a new quiz in Canvas using the New Quizzes API.

        Args:
            course_id: Canvas course ID
            title: Quiz title
            total_points: Total points for the quiz

        Returns:
            dict: Canvas quiz object with assignment_id

        Raises:
            httpx.HTTPStatusError: If Canvas API call fails
        """
        logger.info(
            "canvas_quiz_creation_started",
            course_id=course_id,
            title=title,
            total_points=total_points,
        )

        quiz_data = {
            "title": title,
            "points_possible": total_points,
            "quiz_settings": {
                "shuffle_questions": True,
                "shuffle_answers": True,
                "time_limit": 60,  # 60 minutes default
                "multiple_attempts": False,
                "scoring_policy": "keep_highest",
            },
        }

        async with httpx.AsyncClient(timeout=self.api_timeout) as client:
            try:
                response = await client.post(
                    self.url_builder.quiz_api_quizzes(course_id),
                    headers={
                        "Authorization": f"Bearer {self.canvas_token}",
                        "Content-Type": "application/json",
                    },
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

    async def create_quiz_items(
        self, course_id: int, quiz_id: str, questions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Create quiz items (questions) in Canvas for the given quiz.

        Args:
            course_id: Canvas course ID
            quiz_id: Canvas quiz assignment ID
            questions: List of question dictionaries to create

        Returns:
            list: Results for each question creation attempt
        """
        logger.info(
            "canvas_quiz_items_creation_started",
            course_id=course_id,
            canvas_quiz_id=quiz_id,
            questions_count=len(questions),
        )

        results = []

        async with httpx.AsyncClient(timeout=self.api_timeout) as client:
            for i, question in enumerate(questions):
                try:
                    # Convert question to Canvas New Quiz item format
                    item_data = self._convert_question_to_canvas_item(question, i + 1)

                    response = await client.post(
                        self.url_builder.quiz_api_items(course_id, quiz_id),
                        headers={
                            "Authorization": f"Bearer {self.canvas_token}",
                            "Content-Type": "application/json",
                        },
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

    def _convert_question_to_canvas_item(
        self, question: dict[str, Any], position: int
    ) -> dict[str, Any]:
        """
        Convert a question dictionary to Canvas New Quiz item format.

        Args:
            question: Question dictionary with question data
            position: Position of the question in the quiz

        Returns:
            dict: Canvas quiz item data structure
        """
        # Map correct answer letter to choice index
        correct_answer_map = {"A": 0, "B": 1, "C": 2, "D": 3}
        correct_index = correct_answer_map.get(question["correct_answer"], 0)

        choices = [
            {
                "id": f"choice_{i + 1}",
                "position": i + 1,
                "item_body": f"<p>{choice}</p>",
            }
            for i, choice in enumerate(
                [
                    question["option_a"],
                    question["option_b"],
                    question["option_c"],
                    question["option_d"],
                ]
            )
        ]

        item_id = f"item_{question['id']}"

        return {
            "item": {
                "id": item_id,
                "entry_type": "Item",
                "entry_id": item_id,
                "position": position,
                "item_type": "Question",
                "properties": {"shuffle_answers": True},
                "points_possible": 1,  # 1 point per question
                "entry": {
                    "interaction_type_slug": "choice",
                    "item_body": f"<p>{question['question_text']}</p>",
                    "interaction_data": {"choices": choices},
                    "scoring_algorithm": "Equivalence",
                    "scoring_data": {"value": f"choice_{correct_index + 1}"},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        }
