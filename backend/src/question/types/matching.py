"""Matching Question type implementation."""

import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.canvas.constants import CanvasInteractionType, CanvasScoringAlgorithm

from .base import (
    BaseQuestionData,
    BaseQuestionType,
    QuestionType,
    generate_canvas_title,
)


class MatchingPair(BaseModel):
    """Data model for a single question-answer pair in a matching question."""

    question: str = Field(
        min_length=1, description="The question/left side item to match"
    )
    answer: str = Field(min_length=1, description="The correct answer/right side item")

    @field_validator("question", "answer")
    @classmethod
    def validate_not_whitespace_only(cls, v: str) -> str:
        """Ensure question and answer are not whitespace-only."""
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only")
        return v


class MatchingData(BaseQuestionData):
    """Data model for matching questions."""

    pairs: list[MatchingPair] = Field(
        min_length=3,
        max_length=10,
        description="List of question-answer pairs (3-10 pairs)",
    )
    distractors: list[str] | None = Field(
        default=None,
        max_length=5,
        description="Optional distractor answers that don't match any question",
    )

    @field_validator("pairs")
    @classmethod
    def validate_pairs(cls, v: list[MatchingPair]) -> list[MatchingPair]:
        """Validate that pairs have no duplicate questions or answers."""
        if len(v) < 3:
            raise ValueError("At least 3 pairs are required")
        if len(v) > 10:
            raise ValueError("Maximum 10 pairs allowed")

        # Check for duplicate questions
        questions = [pair.question.strip().lower() for pair in v]
        if len(set(questions)) != len(questions):
            raise ValueError("Duplicate questions are not allowed")

        # Check for duplicate answers
        answers = [pair.answer.strip().lower() for pair in v]
        if len(set(answers)) != len(answers):
            raise ValueError("Duplicate answers are not allowed")

        return v

    @field_validator("distractors")
    @classmethod
    def validate_distractors(cls, v: list[str] | None) -> list[str] | None:
        """Validate distractors and ensure no duplicates."""
        if v is None:
            return v

        if len(v) > 5:
            raise ValueError("Maximum 5 distractors allowed")

        # Filter out empty strings and duplicates
        filtered = [d.strip() for d in v if d.strip()]

        # Remove duplicates while preserving order
        seen = set()
        unique_distractors = []
        for distractor in filtered:
            distractor_lower = distractor.lower()
            if distractor_lower not in seen:
                seen.add(distractor_lower)
                unique_distractors.append(distractor)

        return unique_distractors if unique_distractors else None

    def validate_no_distractor_matches(self) -> None:
        """Ensure distractors don't accidentally match any question answers."""
        if not self.distractors:
            return

        correct_answers = {pair.answer.strip().lower() for pair in self.pairs}
        for distractor in self.distractors:
            if distractor.strip().lower() in correct_answers:
                raise ValueError(f"Distractor '{distractor}' matches a correct answer")

    def get_all_answers(self) -> list[str]:
        """Get all possible answers (correct + distractors) for display."""
        answers = [pair.answer for pair in self.pairs]
        if self.distractors:
            answers.extend(self.distractors)
        return answers


class MatchingQuestionType(BaseQuestionType):
    """Implementation for matching questions."""

    @property
    def question_type(self) -> QuestionType:
        """Return the question type enum."""
        return QuestionType.MATCHING

    @property
    def data_model(self) -> type[MatchingData]:
        """Return the data model class for matching."""
        return MatchingData

    def validate_data(self, data: dict[str, Any]) -> MatchingData:
        """
        Validate and parse matching data.

        Args:
            data: Raw question data dictionary

        Returns:
            Validated matching data

        Raises:
            ValidationError: If data is invalid
        """
        matching_data = MatchingData(**data)
        # Additional validation
        matching_data.validate_no_distractor_matches()
        return matching_data

    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format matching data for API display.

        Args:
            data: Validated matching data

        Returns:
            Dictionary formatted for frontend display
        """
        if not isinstance(data, MatchingData):
            raise ValueError("Expected MatchingData")

        # Convert MatchingPair objects to dictionaries for frontend
        pairs_dict = [
            {"question": pair.question, "answer": pair.answer} for pair in data.pairs
        ]

        result = {
            "question_text": data.question_text,
            "pairs": pairs_dict,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

        if data.distractors:
            result["distractors"] = data.distractors

        return result

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format matching data for Canvas New Quizzes export.

        Args:
            data: Validated matching data

        Returns:
            Dictionary formatted for Canvas New Quizzes API
        """
        if not isinstance(data, MatchingData):
            raise ValueError("Expected MatchingData")

        # Generate unique IDs for Canvas questions
        question_ids = {pair.question: str(uuid.uuid4()) for pair in data.pairs}

        # Build answers list (correct answers + distractors)
        answers = [pair.answer for pair in data.pairs]
        if data.distractors:
            answers.extend(data.distractors)

        # Build questions array for Canvas
        canvas_questions = [
            {"id": question_ids[pair.question], "item_body": pair.question}
            for pair in data.pairs
        ]

        # Build scoring value mapping (question_id -> correct_answer)
        scoring_value = {
            question_ids[pair.question]: pair.answer for pair in data.pairs
        }

        # Build matches for edit_data
        matches = [
            {
                "answer_body": pair.answer,
                "question_id": question_ids[pair.question],
                "question_body": pair.question,
            }
            for pair in data.pairs
        ]

        # Wrap question text in paragraph tag if not already wrapped
        item_body = data.question_text
        if not item_body.strip().startswith("<p>"):
            item_body = f"<p>{item_body}</p>"

        return {
            "title": generate_canvas_title(data.question_text),
            "item_body": item_body,
            "calculator_type": "none",
            "interaction_data": {
                "answers": answers,
                "questions": canvas_questions,
            },
            "properties": {
                "shuffle_rules": {
                    "questions": {"shuffled": False},
                    "answers": {"shuffled": True},
                }
            },
            "scoring_data": {
                "value": scoring_value,
                "edit_data": {
                    "matches": matches,
                    "distractors": data.distractors or [],
                },
            },
            "answer_feedback": {},
            "scoring_algorithm": CanvasScoringAlgorithm.PARTIAL_DEEP,
            "interaction_type_slug": CanvasInteractionType.MATCHING,
            "feedback": {},
            "points_possible": len(data.pairs),
        }

    def format_for_export(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format matching data for generic export.

        Args:
            data: Validated matching data

        Returns:
            Dictionary with matching data for export
        """
        if not isinstance(data, MatchingData):
            raise ValueError("Expected MatchingData")

        # Convert pairs to simple dict format
        pairs_data = [
            {"question": pair.question, "answer": pair.answer} for pair in data.pairs
        ]

        result = {
            "question_text": data.question_text,
            "pairs": pairs_data,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

        if data.distractors:
            result["distractors"] = data.distractors

        return result

    def format_for_pdf(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format matching for PDF export (student version - no answer pairings).

        Args:
            data: Validated matching data

        Returns:
            Dictionary formatted for PDF generation without answers
        """
        if not isinstance(data, MatchingData):
            raise ValueError("Expected MatchingData")

        # Extract left and right items for PDF display
        left_items = [pair.question for pair in data.pairs]
        right_items = [pair.answer for pair in data.pairs]

        # Add distractors to right items if present
        if data.distractors:
            right_items.extend(data.distractors)

        return {
            "type": "matching",
            "question_text": data.question_text,
            "left_items": left_items,
            "right_items": right_items,
            # No correct matches for student version
        }

    def format_for_qti(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format matching for QTI XML export (with answers for LMS import).

        Args:
            data: Validated matching data

        Returns:
            Dictionary formatted for QTI XML generation with answers
        """
        if not isinstance(data, MatchingData):
            raise ValueError("Expected MatchingData")

        # Extract items and create correct matches
        left_items = [pair.question for pair in data.pairs]
        right_items = [pair.answer for pair in data.pairs]
        correct_matches = [
            {"left": pair.question, "right": pair.answer} for pair in data.pairs
        ]

        # Add distractors if present
        if data.distractors:
            right_items.extend(data.distractors)

        return {
            "type": "matching",
            "question_text": data.question_text,
            "left_items": left_items,
            "right_items": right_items,
            "correct_matches": correct_matches,
            # Additional QTI-specific metadata
            "interaction_type": "associate",
            "max_associations": len(data.pairs),
        }
