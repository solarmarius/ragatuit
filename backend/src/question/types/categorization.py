"""Categorization Question type implementation."""

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


class CategoryItem(BaseModel):
    """Data model for a single item that can be categorized."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the item",
    )
    text: str = Field(
        min_length=1,
        max_length=200,
        description="The text content of the item to be categorized",
    )


class Category(BaseModel):
    """Data model for a category that items can be placed into."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the category",
    )
    name: str = Field(
        min_length=1, max_length=100, description="The name/label of the category"
    )
    correct_items: list[str] = Field(
        min_length=1,
        max_length=20,
        description="List of item IDs that belong in this category",
    )

    @field_validator("correct_items")
    @classmethod
    def validate_correct_items(cls, v: list[str]) -> list[str]:
        """Validate that correct_items is not empty."""
        if not v:
            raise ValueError("Each category must have at least one correct item")
        return v


class CategorizationData(BaseQuestionData):
    """Data model for categorization questions."""

    categories: list[Category] = Field(
        min_length=2, max_length=8, description="List of categories (2-8 categories)"
    )
    items: list[CategoryItem] = Field(
        min_length=4,
        max_length=20,
        description="List of items to be categorized (4-20 items)",
    )
    distractors: list[CategoryItem] | None = Field(
        default=None,
        max_length=5,
        description="Optional distractor items that don't belong in any category",
    )

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[Category]) -> list[Category]:
        """Validate categories have unique names and IDs."""
        if len(v) < 2:
            raise ValueError("At least 2 categories are required")
        if len(v) > 8:
            raise ValueError("Maximum 8 categories allowed")

        # Check for duplicate category names (case-insensitive)
        names_lower = {cat.name.strip().lower() for cat in v}
        if len(names_lower) != len(v):
            raise ValueError("Duplicate category names are not allowed")

        # Check for duplicate category IDs
        category_ids = {cat.id for cat in v}
        if len(category_ids) != len(v):
            raise ValueError("Duplicate category IDs are not allowed")

        return v

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: list[CategoryItem]) -> list[CategoryItem]:
        """Validate items have unique texts and IDs."""
        if len(v) < 4:
            raise ValueError("At least 4 items are required")
        if len(v) > 20:
            raise ValueError("Maximum 20 items allowed")

        # Check for duplicate item texts (case-insensitive)
        texts_lower = {item.text.strip().lower() for item in v}
        if len(texts_lower) != len(v):
            raise ValueError("Duplicate item texts are not allowed")

        # Check for duplicate item IDs
        item_ids = {item.id for item in v}
        if len(item_ids) != len(v):
            raise ValueError("Duplicate item IDs are not allowed")

        return v

    @field_validator("distractors")
    @classmethod
    def validate_distractors(
        cls, v: list[CategoryItem] | None
    ) -> list[CategoryItem] | None:
        """Validate distractors and ensure no duplicates."""
        if v is None:
            return v

        if len(v) > 5:
            raise ValueError("Maximum 5 distractors allowed")

        # Check for duplicate distractor texts (case-insensitive)
        distractor_texts = {item.text.strip().lower() for item in v}
        if len(distractor_texts) != len(v):
            raise ValueError("Duplicate distractor texts are not allowed")

        # Check for duplicate distractor IDs
        distractor_ids = {item.id for item in v}
        if len(distractor_ids) != len(v):
            raise ValueError("Duplicate distractor IDs are not allowed")

        return v

    def clean_distractor_duplicates(self) -> None:
        """Remove any items from the items list that also appear in distractors.

        This handles cases where the LLM incorrectly places distractor items
        in both the items and distractors arrays. Items should only appear
        in one array - distractors belong only in the distractors array.
        """
        if not self.distractors:
            return

        # Get set of distractor IDs for fast lookup
        distractor_ids = {distractor.id for distractor in self.distractors}

        # Remove any items that are also distractors
        self.items = [item for item in self.items if item.id not in distractor_ids]

    def validate_item_assignments(self) -> None:
        """Validate that all referenced items exist and assignments are valid."""
        # Get all item IDs
        all_item_ids = {item.id for item in self.items}
        if self.distractors:
            all_item_ids.update(item.id for item in self.distractors)

        # Check that all correct_items references exist
        for category in self.categories:
            for item_id in category.correct_items:
                if item_id not in all_item_ids:
                    raise ValueError(
                        f"Category '{category.name}' references non-existent item ID: {item_id}"
                    )

        # Check that each item is assigned to exactly one category
        assigned_items = set()
        for category in self.categories:
            for item_id in category.correct_items:
                if item_id in assigned_items:
                    raise ValueError(
                        f"Item ID {item_id} is assigned to multiple categories"
                    )
                assigned_items.add(item_id)

        # Ensure all non-distractor items are assigned to a category
        main_item_ids = {item.id for item in self.items}
        unassigned_items = main_item_ids - assigned_items
        if unassigned_items:
            raise ValueError(
                f"Items not assigned to any category: {list(unassigned_items)}"
            )

    def get_all_items(self) -> list[CategoryItem]:
        """Get all items including distractors for display."""
        all_items = self.items.copy()
        if self.distractors:
            all_items.extend(self.distractors)
        return all_items

    def get_category_by_id(self, category_id: str) -> Category | None:
        """Get a category by its ID."""
        for category in self.categories:
            if category.id == category_id:
                return category
        return None

    def get_item_by_id(self, item_id: str) -> CategoryItem | None:
        """Get an item by its ID (including distractors)."""
        all_items = self.get_all_items()
        for item in all_items:
            if item.id == item_id:
                return item
        return None


class CategorizationQuestionType(BaseQuestionType):
    """Implementation for categorization questions."""

    @property
    def question_type(self) -> QuestionType:
        """Return the question type enum."""
        return QuestionType.CATEGORIZATION

    @property
    def data_model(self) -> type[CategorizationData]:
        """Return the data model class for categorization."""
        return CategorizationData

    def validate_data(self, data: dict[str, Any]) -> CategorizationData:
        """
        Validate and parse categorization data.

        Args:
            data: Raw question data dictionary

        Returns:
            Validated categorization data

        Raises:
            ValidationError: If data is invalid
        """
        categorization_data = CategorizationData(**data)
        # Clean up LLM data inconsistencies (distractors in items array)
        categorization_data.clean_distractor_duplicates()
        # Additional validation for business logic
        categorization_data.validate_item_assignments()
        return categorization_data

    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format categorization data for API display.

        Args:
            data: Validated categorization data

        Returns:
            Dictionary formatted for frontend display
        """
        if not isinstance(data, CategorizationData):
            raise ValueError("Expected CategorizationData")

        # Convert Category and CategoryItem objects to dictionaries for frontend
        categories_dict = [
            {
                "id": cat.id,
                "name": cat.name,
                "correct_items": cat.correct_items,
            }
            for cat in data.categories
        ]

        items_dict = [{"id": item.id, "text": item.text} for item in data.items]

        result = {
            "question_text": data.question_text,
            "categories": categories_dict,
            "items": items_dict,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

        if data.distractors:
            result["distractors"] = [
                {"id": item.id, "text": item.text} for item in data.distractors
            ]

        return result

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format categorization data for Canvas New Quizzes export.

        Args:
            data: Validated categorization data

        Returns:
            Dictionary formatted for Canvas New Quizzes API
        """
        if not isinstance(data, CategorizationData):
            raise ValueError("Expected CategorizationData")

        # Build categories dictionary for Canvas
        canvas_categories = {}
        for category in data.categories:
            canvas_categories[category.id] = {
                "id": category.id,
                "item_body": category.name,
            }

        # Canvas expects all items (including correct ones) in the distractors field
        # The scoring_data determines which items belong to which categories
        canvas_distractors = {}
        all_items = data.get_all_items()

        for item in all_items:
            canvas_distractors[item.id] = {
                "id": item.id,
                "item_body": item.text,
            }

        # Build category order (for consistent display)
        category_order = [cat.id for cat in data.categories]

        # Build scoring data (which items belong to which categories)
        scoring_value = []
        for category in data.categories:
            scoring_value.append(
                {
                    "id": category.id,
                    "scoring_data": {
                        "value": category.correct_items,
                    },
                    "scoring_algorithm": CanvasScoringAlgorithm.ALL_OR_NOTHING,
                }
            )

        # Wrap question text in paragraph tag if not already wrapped
        item_body = data.question_text
        if not item_body.strip().startswith("<p>"):
            item_body = f"<p>{item_body}</p>"

        # Calculate points (typically 1 point per category)
        points_possible = len(data.categories)

        return {
            "title": generate_canvas_title(data.question_text),
            "item_body": item_body,
            "calculator_type": "none",
            "interaction_data": {
                "categories": canvas_categories,
                "distractors": canvas_distractors,
                "category_order": category_order,
            },
            "properties": {"shuffle_rules": {"questions": {"shuffled": False}}},
            "scoring_data": {
                "value": scoring_value,
                "score_method": "all_or_nothing",
            },
            "answer_feedback": {},
            "scoring_algorithm": CanvasScoringAlgorithm.CATEGORIZATION,
            "interaction_type_slug": CanvasInteractionType.CATEGORIZATION,
            "feedback": {},
            "points_possible": points_possible,
        }

    def format_for_export(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format categorization data for generic export.

        Args:
            data: Validated categorization data

        Returns:
            Dictionary with categorization data for export
        """
        if not isinstance(data, CategorizationData):
            raise ValueError("Expected CategorizationData")

        # Convert to simple dict format for export
        categories_data = [
            {
                "id": cat.id,
                "name": cat.name,
                "correct_items": cat.correct_items,
            }
            for cat in data.categories
        ]

        items_data = [{"id": item.id, "text": item.text} for item in data.items]

        result = {
            "question_text": data.question_text,
            "categories": categories_data,
            "items": items_data,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

        if data.distractors:
            result["distractors"] = [
                {"id": item.id, "text": item.text} for item in data.distractors
            ]

        return result
