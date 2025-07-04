"""Multiple Choice Question type implementation."""

from typing import Any

from pydantic import Field, field_validator

from .base import BaseQuestionData, BaseQuestionType, QuestionType


class MultipleChoiceData(BaseQuestionData):
    """Data model for multiple choice questions."""

    option_a: str = Field(min_length=1, max_length=500, description="Option A text")
    option_b: str = Field(min_length=1, max_length=500, description="Option B text")
    option_c: str = Field(min_length=1, max_length=500, description="Option C text")
    option_d: str = Field(min_length=1, max_length=500, description="Option D text")
    correct_answer: str = Field(
        pattern=r"^[ABCD]$", description="Must be A, B, C, or D"
    )

    @field_validator("correct_answer")
    @classmethod
    def validate_correct_answer(cls, v: str) -> str:
        """Validate that correct answer is one of A, B, C, D."""
        if v not in ["A", "B", "C", "D"]:
            raise ValueError("Correct answer must be A, B, C, or D")
        return v

    def get_correct_option_text(self) -> str:
        """Get the text of the correct option."""
        option_map = {
            "A": self.option_a,
            "B": self.option_b,
            "C": self.option_c,
            "D": self.option_d,
        }
        return option_map[self.correct_answer]

    def get_all_options(self) -> dict[str, str]:
        """Get all options as a dictionary."""
        return {
            "A": self.option_a,
            "B": self.option_b,
            "C": self.option_c,
            "D": self.option_d,
        }


class MultipleChoiceQuestionType(BaseQuestionType):
    """Implementation for multiple choice questions."""

    @property
    def question_type(self) -> QuestionType:
        """Return the question type enum."""
        return QuestionType.MULTIPLE_CHOICE

    @property
    def data_model(self) -> type[MultipleChoiceData]:
        """Return the data model class for MCQ."""
        return MultipleChoiceData

    def validate_data(self, data: dict[str, Any]) -> MultipleChoiceData:
        """
        Validate and parse MCQ data.

        Args:
            data: Raw question data dictionary

        Returns:
            Validated MCQ data

        Raises:
            ValidationError: If data is invalid
        """
        return MultipleChoiceData(**data)

    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format MCQ data for API display.

        Args:
            data: Validated MCQ data

        Returns:
            Dictionary formatted for frontend display
        """
        if not isinstance(data, MultipleChoiceData):
            raise ValueError("Expected MultipleChoiceData")

        return {
            "question_text": data.question_text,
            "options": data.get_all_options(),
            "correct_answer": data.correct_answer,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format MCQ data for Canvas LMS export.

        Args:
            data: Validated MCQ data

        Returns:
            Dictionary formatted for Canvas API
        """
        if not isinstance(data, MultipleChoiceData):
            raise ValueError("Expected MultipleChoiceData")

        # Canvas expects answers in a specific format
        answers = []
        options = data.get_all_options()

        for letter, text in options.items():
            answers.append(
                {
                    "answer_text": text,
                    "answer_weight": 100 if letter == data.correct_answer else 0,
                    "answer_comments": data.explanation
                    if letter == data.correct_answer
                    else "",
                }
            )

        return {
            "question_type": "multiple_choice_question",
            "question_text": data.question_text,
            "answers": answers,
            "points_possible": 1,
        }

    def migrate_from_legacy(self, legacy_question: Any) -> MultipleChoiceData:
        """
        Migrate from legacy Question model to new MCQ data format.

        Args:
            legacy_question: Legacy Question model instance

        Returns:
            MCQ data compatible with new system
        """
        return MultipleChoiceData(
            question_text=legacy_question.question_text,
            option_a=legacy_question.option_a,
            option_b=legacy_question.option_b,
            option_c=legacy_question.option_c,
            option_d=legacy_question.option_d,
            correct_answer=legacy_question.correct_answer,
            explanation=None,  # Legacy model doesn't have explanation
        )
