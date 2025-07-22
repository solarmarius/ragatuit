"""Fill-in-Blank Question type implementation."""

import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.canvas.constants import CanvasInteractionType, CanvasScoringAlgorithm

from .base import BaseQuestionData, BaseQuestionType, QuestionType


class BlankData(BaseModel):
    """Data model for a single blank within a fill-in-blank question."""

    position: int = Field(
        ge=1, le=100, description="Position of the blank in the question"
    )
    correct_answer: str = Field(
        min_length=1, max_length=200, description="The correct answer for this blank"
    )
    answer_variations: list[str] | None = Field(
        default=None,
        description="Alternative acceptable answers for this blank",
    )
    case_sensitive: bool = Field(
        default=False, description="Whether answers are case-sensitive"
    )

    @field_validator("answer_variations")
    @classmethod
    def validate_answer_variations(cls, v: list[str] | None) -> list[str] | None:
        """Validate that answer variations are non-empty if provided."""
        if v is None:
            return v

        # Check maximum length
        if len(v) > 10:
            raise ValueError("Maximum 10 answer variations allowed")

        # Filter out empty strings and duplicates
        filtered = [variation.strip() for variation in v if variation.strip()]

        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for variation in filtered:
            if variation not in seen:
                seen.add(variation)
                unique_variations.append(variation)

        return unique_variations if unique_variations else None


class FillInBlankData(BaseQuestionData):
    """Data model for fill-in-blank questions."""

    blanks: list[BlankData] = Field(
        description="List of blanks in the question",
    )

    @field_validator("blanks")
    @classmethod
    def validate_blanks(cls, v: list[BlankData]) -> list[BlankData]:
        """Validate that blanks have unique positions."""
        if not v:
            raise ValueError("At least one blank is required")

        # Check maximum length
        if len(v) > 10:
            raise ValueError("Maximum 10 blanks allowed")

        # Check for unique positions
        positions = [blank.position for blank in v]
        if len(set(positions)) != len(positions):
            raise ValueError("Each blank must have a unique position")

        # Sort blanks by position for consistency
        return sorted(v, key=lambda blank: blank.position)

    def get_blank_by_position(self, position: int) -> BlankData | None:
        """Get a blank by its position."""
        for blank in self.blanks:
            if blank.position == position:
                return blank
        return None

    def get_all_answers(self) -> dict[int, list[str]]:
        """Get all possible answers for each blank position."""
        answers = {}
        for blank in self.blanks:
            all_answers = [blank.correct_answer]
            if blank.answer_variations:
                all_answers.extend(blank.answer_variations)
            answers[blank.position] = all_answers
        return answers


class FillInBlankQuestionType(BaseQuestionType):
    """Implementation for fill-in-blank questions."""

    @property
    def question_type(self) -> QuestionType:
        """Return the question type enum."""
        return QuestionType.FILL_IN_BLANK

    @property
    def data_model(self) -> type[FillInBlankData]:
        """Return the data model class for fill-in-blank."""
        return FillInBlankData

    def validate_data(self, data: dict[str, Any]) -> FillInBlankData:
        """
        Validate and parse fill-in-blank data.

        Args:
            data: Raw question data dictionary

        Returns:
            Validated fill-in-blank data

        Raises:
            ValidationError: If data is invalid
        """
        return FillInBlankData(**data)

    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format fill-in-blank data for API display.

        Args:
            data: Validated fill-in-blank data

        Returns:
            Dictionary formatted for frontend display
        """
        if not isinstance(data, FillInBlankData):
            raise ValueError("Expected FillInBlankData")

        # Convert BlankData objects to dictionaries for frontend
        blanks_dict = []
        for blank in data.blanks:
            blank_dict = {
                "position": blank.position,
                "correct_answer": blank.correct_answer,
                "case_sensitive": blank.case_sensitive,
            }
            if blank.answer_variations:
                blank_dict["answer_variations"] = blank.answer_variations
            blanks_dict.append(blank_dict)

        return {
            "question_text": data.question_text,
            "blanks": blanks_dict,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format fill-in-blank data for Canvas Rich Fill In The Blank export.

        Args:
            data: Validated fill-in-blank data

        Returns:
            Dictionary formatted for Canvas New Quizzes API (Rich Fill In The Blank)
        """
        if not isinstance(data, FillInBlankData):
            raise ValueError("Expected FillInBlankData")

        # Generate UUIDs for each blank
        blank_uuids = {blank.position: str(uuid.uuid4()) for blank in data.blanks}

        # Build the HTML body with span tags for blanks
        # Replace [blank_N] placeholders with <span id="blank_uuid">
        item_body = data.question_text
        for blank in data.blanks:
            placeholder = f"[blank_{blank.position}]"
            span_tag = f'<span id="blank_{blank_uuids[blank.position]}"></span>'
            item_body = item_body.replace(placeholder, span_tag)

        # Wrap in paragraph tag if not already wrapped
        if not item_body.strip().startswith("<p>"):
            item_body = f"<p>{item_body}</p>"

        # Build interaction_data with blanks array
        interaction_blanks = []
        for blank in data.blanks:
            interaction_blanks.append(
                {
                    "id": blank_uuids[blank.position],
                    "answer_type": "openEntry",
                }
            )

        interaction_data = {
            "blanks": interaction_blanks,
        }

        # Build scoring_data with scoring information
        scoring_values = []
        for blank in data.blanks:
            blank_uuid = blank_uuids[blank.position]

            # Primary correct answer
            scoring_values.append(
                {
                    "id": blank_uuid,
                    "scoring_data": {
                        "value": blank.correct_answer,
                        "blank_text": blank.correct_answer,
                    },
                    "scoring_algorithm": CanvasScoringAlgorithm.TEXT_CONTAINS_ANSWER,
                }
            )

            # Add answer variations as additional scoring entries
            if blank.answer_variations:
                for variation in blank.answer_variations:
                    scoring_values.append(
                        {
                            "id": blank_uuid,
                            "scoring_data": {
                                "value": variation,
                                "blank_text": variation,
                            },
                            "scoring_algorithm": CanvasScoringAlgorithm.TEXT_CONTAINS_ANSWER,
                        }
                    )

        # Build working_item_body with answers filled in
        working_item_body = data.question_text
        for blank in data.blanks:
            placeholder = f"[blank_{blank.position}]"
            working_item_body = working_item_body.replace(
                placeholder, blank.correct_answer
            )

        # Wrap in paragraph tag if not already wrapped
        if not working_item_body.strip().startswith("<p>"):
            working_item_body = f"<p>{working_item_body}</p>"

        scoring_data = {
            "value": scoring_values,
            "working_item_body": working_item_body,
        }

        # Build the complete Canvas API structure
        return {
            "title": f"Question {data.question_text[:50]}...",  # Canvas requires a title
            "item_body": item_body,
            "calculator_type": "none",
            "interaction_data": interaction_data,
            "properties": {"shuffle_rules": {"blanks": {}}},
            "scoring_data": scoring_data,
            "answer_feedback": {},
            "scoring_algorithm": CanvasScoringAlgorithm.MULTIPLE_METHODS,
            "interaction_type_slug": CanvasInteractionType.RICH_FILL_BLANK,
            "feedback": {},
            "points_possible": len(
                data.blanks
            ),  # Add points_possible for Canvas service
        }

    def format_for_export(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format fill-in-blank data for generic export.

        Args:
            data: Validated fill-in-blank data

        Returns:
            Dictionary with fill-in-blank data for export
        """
        if not isinstance(data, FillInBlankData):
            raise ValueError("Expected FillInBlankData")

        # Convert blanks to a simple dict format for export
        blanks_data = []
        for blank in data.blanks:
            blank_dict = {
                "position": blank.position,
                "correct_answer": blank.correct_answer,
                "case_sensitive": blank.case_sensitive,
            }
            if blank.answer_variations:
                blank_dict["answer_variations"] = blank.answer_variations
            blanks_data.append(blank_dict)

        return {
            "question_text": data.question_text,
            "blanks": blanks_data,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }
