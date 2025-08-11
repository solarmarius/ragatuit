"""True/False Question type implementation."""

from typing import Any

from pydantic import Field

from src.canvas.constants import CanvasInteractionType, CanvasScoringAlgorithm

from .base import (
    BaseQuestionData,
    BaseQuestionType,
    QuestionType,
    generate_canvas_title,
)


class TrueFalseData(BaseQuestionData):
    """Data model for true/false questions."""

    correct_answer: bool = Field(
        description="Whether the statement is true (True) or false (False)"
    )


class TrueFalseQuestionType(BaseQuestionType):
    """Implementation for true/false questions."""

    @property
    def question_type(self) -> QuestionType:
        """Return the question type enum."""
        return QuestionType.TRUE_FALSE

    @property
    def data_model(self) -> type[TrueFalseData]:
        """Return the data model class for True/False."""
        return TrueFalseData

    def validate_data(self, data: dict[str, Any]) -> TrueFalseData:
        """
        Validate and parse True/False data.

        Args:
            data: Raw question data dictionary

        Returns:
            Validated True/False data

        Raises:
            ValidationError: If data is invalid
        """
        return TrueFalseData(**data)

    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format True/False data for API display.

        Args:
            data: Validated True/False data

        Returns:
            Dictionary formatted for frontend display
        """
        if not isinstance(data, TrueFalseData):
            raise ValueError("Expected TrueFalseData")

        return {
            "question_text": data.question_text,
            "correct_answer": data.correct_answer,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format True/False data for Canvas New Quizzes export.

        Args:
            data: Validated True/False data

        Returns:
            Dictionary formatted for Canvas New Quizzes API
        """
        if not isinstance(data, TrueFalseData):
            raise ValueError("Expected TrueFalseData")

        # Wrap question text in paragraph tag if not already wrapped
        item_body = data.question_text
        if not item_body.strip().startswith("<p>"):
            item_body = f"<p>{item_body}</p>"

        return {
            "title": generate_canvas_title(data.question_text),
            "item_body": item_body,
            "calculator_type": "none",
            "interaction_data": {
                "true_choice": "True",
                "false_choice": "False",
            },
            "properties": {},
            "scoring_data": {"value": data.correct_answer},
            "scoring_algorithm": CanvasScoringAlgorithm.EQUIVALENCE,
            "interaction_type_slug": CanvasInteractionType.TRUE_FALSE,
            "feedback": {"neutral": data.explanation} if data.explanation else {},
            "points_possible": 1,
        }

    def format_for_export(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format True/False data for generic export.

        Args:
            data: Validated True/False data

        Returns:
            Dictionary with True/False data for export
        """
        if not isinstance(data, TrueFalseData):
            raise ValueError("Expected TrueFalseData")

        return {
            "question_text": data.question_text,
            "correct_answer": data.correct_answer,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }
