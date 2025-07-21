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

    def format_for_export(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format MCQ data for generic export.

        Args:
            data: Validated MCQ data

        Returns:
            Dictionary with MCQ data for export
        """
        if not isinstance(data, MultipleChoiceData):
            raise ValueError("Expected MultipleChoiceData")

        return {
            "question_text": data.question_text,
            "option_a": data.option_a,
            "option_b": data.option_b,
            "option_c": data.option_c,
            "option_d": data.option_d,
            "correct_answer": data.correct_answer,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

    async def evaluate_semantic_similarity_async(
        self,
        question_data: BaseQuestionData,
        semantic_similarity_scorer: Any,
        logger: Any,
    ) -> float:
        """Evaluate semantic similarity for MCQ by comparing answer alternatives."""
        try:
            # Cast to MCQ-specific data model to access options
            if not isinstance(question_data, MultipleChoiceData):
                logger.warning(
                    "MCQ expected MultipleChoiceData, skipping semantic similarity"
                )
                return 1.0

            mcq_data = question_data

            # Extract correct answer and all options
            correct_answer = mcq_data.correct_answer
            if not correct_answer:
                logger.warning(
                    "MCQ missing correct_answer, skipping semantic similarity"
                )
                return 1.0

            # Get correct answer text
            correct_option_key = f"option_{correct_answer.lower()}"
            correct_answer_text = getattr(mcq_data, correct_option_key, "")

            if not correct_answer_text:
                logger.warning(
                    f"MCQ correct answer text not found for {correct_answer}"
                )
                return 1.0

            # Collect all option texts for comparison
            option_keys = ["option_a", "option_b", "option_c", "option_d"]
            options = []
            for key in option_keys:
                option_text = getattr(mcq_data, key, None)
                if option_text and option_text != correct_answer_text:
                    options.append(option_text)

            if len(options) < 1:
                logger.warning(
                    "MCQ has insufficient alternatives for semantic similarity"
                )
                return 1.0

            # For now, return a placeholder score since we don't have RAGAS running yet
            # This will be replaced with actual RAGAS evaluation in later phases
            logger.debug(
                "MCQ semantic similarity evaluation (placeholder implementation)"
            )
            return 0.7  # Placeholder score

        except Exception as e:
            logger.error(f"MCQ semantic similarity evaluation failed: {e}")
            return 0.0  # Fail on error

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
