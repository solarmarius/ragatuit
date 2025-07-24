"""Tests for categorization question type implementation."""

import pytest


def test_category_item_creation():
    """Test creating CategoryItem with valid data."""
    from src.question.types.categorization import CategoryItem

    item = CategoryItem(text="Dolphin")
    assert item.text == "Dolphin"
    assert item.id is not None
    assert len(item.id) > 0


def test_category_item_creation_with_custom_id():
    """Test creating CategoryItem with custom ID."""
    from src.question.types.categorization import CategoryItem

    item = CategoryItem(id="custom_id", text="Elephant")
    assert item.id == "custom_id"
    assert item.text == "Elephant"


def test_category_item_empty_text_validation():
    """Test that empty text fails validation."""
    from pydantic import ValidationError

    from src.question.types.categorization import CategoryItem

    with pytest.raises(ValidationError) as exc_info:
        CategoryItem(text="")
    assert "String should have at least 1 character" in str(exc_info.value)


def test_category_item_whitespace_only_validation():
    """Test that whitespace-only text is allowed at this level."""
    from src.question.types.categorization import CategoryItem

    # CategoryItem only validates min_length=1, whitespace validation is at higher level
    item = CategoryItem(text="   ")
    assert item.text == "   "  # Pydantic allows whitespace-only strings


def test_category_item_text_too_long_validation():
    """Test that text longer than 200 characters fails validation."""
    from pydantic import ValidationError

    from src.question.types.categorization import CategoryItem

    long_text = "x" * 201
    with pytest.raises(ValidationError) as exc_info:
        CategoryItem(text=long_text)
    assert "String should have at most 200 characters" in str(exc_info.value)


def test_category_creation():
    """Test creating Category with valid data."""
    from src.question.types.categorization import Category

    category = Category(name="Mammals", correct_items=["item1", "item2"])
    assert category.name == "Mammals"
    assert category.correct_items == ["item1", "item2"]
    assert category.id is not None


def test_category_creation_with_custom_id():
    """Test creating Category with custom ID."""
    from src.question.types.categorization import Category

    category = Category(id="custom_id", name="Birds", correct_items=["item1"])
    assert category.id == "custom_id"
    assert category.name == "Birds"


def test_category_empty_name_validation():
    """Test that empty name fails validation."""
    from pydantic import ValidationError

    from src.question.types.categorization import Category

    with pytest.raises(ValidationError) as exc_info:
        Category(name="", correct_items=["item1"])
    assert "String should have at least 1 character" in str(exc_info.value)


def test_category_name_too_long_validation():
    """Test that name longer than 100 characters fails validation."""
    from pydantic import ValidationError

    from src.question.types.categorization import Category

    long_name = "x" * 101
    with pytest.raises(ValidationError) as exc_info:
        Category(name=long_name, correct_items=["item1"])
    assert "String should have at most 100 characters" in str(exc_info.value)


def test_category_empty_correct_items_validation():
    """Test that empty correct_items fails validation."""
    from pydantic import ValidationError

    from src.question.types.categorization import Category

    with pytest.raises(ValidationError) as exc_info:
        Category(name="Mammals", correct_items=[])
    assert "List should have at least 1 item" in str(exc_info.value)


def test_category_too_many_correct_items_validation():
    """Test that more than 10 correct items fails validation."""
    from pydantic import ValidationError

    from src.question.types.categorization import Category

    many_items = [f"item{i}" for i in range(11)]
    with pytest.raises(ValidationError) as exc_info:
        Category(name="Mammals", correct_items=many_items)
    assert "List should have at most 10 items" in str(exc_info.value)


def test_categorization_data_creation():
    """Test creating CategorizationData with valid data."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [
        CategoryItem(id="item1", text="Dolphin"),
        CategoryItem(id="item2", text="Elephant"),
        CategoryItem(id="item3", text="Eagle"),
        CategoryItem(id="item4", text="Penguin"),
        CategoryItem(id="item5", text="Shark"),
        CategoryItem(id="item6", text="Octopus"),
    ]

    data = CategorizationData(
        question_text="Categorize these animals", categories=categories, items=items
    )
    assert len(data.categories) == 2
    assert len(data.items) == 6
    assert data.distractors is None


def test_categorization_data_creation_with_distractors():
    """Test creating CategorizationData with distractors."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [
        CategoryItem(id="item1", text="Dolphin"),
        CategoryItem(id="item2", text="Elephant"),
        CategoryItem(id="item3", text="Eagle"),
        CategoryItem(id="item4", text="Penguin"),
        CategoryItem(id="item5", text="Shark"),
        CategoryItem(id="item6", text="Octopus"),
    ]
    distractors = [
        CategoryItem(id="dist1", text="Jellyfish"),
        CategoryItem(id="dist2", text="Coral"),
    ]

    data = CategorizationData(
        question_text="Categorize these animals",
        categories=categories,
        items=items,
        distractors=distractors,
    )
    assert len(data.distractors) == 2


def test_categorization_data_minimum_categories_validation():
    """Test that at least 2 categories are required."""
    from pydantic import ValidationError

    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    single_category = [Category(name="Mammals", correct_items=["item1"])]
    items = [CategoryItem(id="item1", text="Dolphin") for _ in range(6)]

    with pytest.raises(ValidationError) as exc_info:
        CategorizationData(
            question_text="Test", categories=single_category, items=items
        )
    assert "List should have at least 2 items" in str(exc_info.value)


def test_categorization_data_maximum_categories_validation():
    """Test that maximum 8 categories are allowed."""
    from pydantic import ValidationError

    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    many_categories = [
        Category(name=f"Category{i}", correct_items=[f"item{i}"]) for i in range(9)
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(9)]

    with pytest.raises(ValidationError) as exc_info:
        CategorizationData(
            question_text="Test", categories=many_categories, items=items
        )
    assert "List should have at most 8 items" in str(exc_info.value)


def test_categorization_data_minimum_items_validation():
    """Test that at least 6 items are required."""
    from pydantic import ValidationError

    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Category1", correct_items=["item1"]),
        Category(name="Category2", correct_items=["item2"]),
    ]
    few_items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(5)]

    with pytest.raises(ValidationError) as exc_info:
        CategorizationData(question_text="Test", categories=categories, items=few_items)
    assert "List should have at least 6 items" in str(exc_info.value)


def test_categorization_data_maximum_items_validation():
    """Test that maximum 20 items are allowed."""
    from pydantic import ValidationError

    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Category1", correct_items=["item1"]),
        Category(name="Category2", correct_items=["item2"]),
    ]
    many_items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(21)]

    with pytest.raises(ValidationError) as exc_info:
        CategorizationData(
            question_text="Test", categories=categories, items=many_items
        )
    assert "List should have at most 20 items" in str(exc_info.value)


def test_categorization_data_duplicate_category_names_validation():
    """Test that duplicate category names are not allowed."""
    from pydantic import ValidationError

    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    duplicate_categories = [
        Category(name="Mammals", correct_items=["item1"]),
        Category(name="mammals", correct_items=["item2"]),  # Case-insensitive duplicate
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    with pytest.raises(ValidationError) as exc_info:
        CategorizationData(
            question_text="Test", categories=duplicate_categories, items=items
        )
    assert "Duplicate category names are not allowed" in str(exc_info.value)


def test_categorization_data_duplicate_item_texts_validation():
    """Test that duplicate item texts are not allowed."""
    from pydantic import ValidationError

    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1"]),
        Category(name="Birds", correct_items=["item2"]),
    ]
    duplicate_items = [
        CategoryItem(id="item1", text="Dolphin"),
        CategoryItem(id="item2", text="dolphin"),  # Case-insensitive duplicate
        CategoryItem(id="item3", text="Eagle"),
        CategoryItem(id="item4", text="Shark"),
        CategoryItem(id="item5", text="Octopus"),
        CategoryItem(id="item6", text="Coral"),
    ]

    with pytest.raises(ValidationError) as exc_info:
        CategorizationData(
            question_text="Test", categories=categories, items=duplicate_items
        )
    assert "Duplicate item texts are not allowed" in str(exc_info.value)


def test_categorization_data_maximum_distractors_validation():
    """Test that maximum 5 distractors are allowed."""
    from pydantic import ValidationError

    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1"]),
        Category(name="Birds", correct_items=["item2"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]
    many_distractors = [
        CategoryItem(id=f"dist{i}", text=f"Distractor{i}") for i in range(6)
    ]

    with pytest.raises(ValidationError) as exc_info:
        CategorizationData(
            question_text="Test",
            categories=categories,
            items=items,
            distractors=many_distractors,
        )
    assert "List should have at most 5 items" in str(exc_info.value)


def test_categorization_data_duplicate_distractor_texts_validation():
    """Test that duplicate distractor texts are not allowed."""
    from pydantic import ValidationError

    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1"]),
        Category(name="Birds", correct_items=["item2"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]
    duplicate_distractors = [
        CategoryItem(id="dist1", text="Jellyfish"),
        CategoryItem(id="dist2", text="jellyfish"),  # Case-insensitive duplicate
        CategoryItem(id="dist3", text="Coral"),
    ]

    with pytest.raises(ValidationError) as exc_info:
        CategorizationData(
            question_text="Test",
            categories=categories,
            items=items,
            distractors=duplicate_distractors,
        )
    assert "Duplicate distractor texts are not allowed" in str(exc_info.value)


def test_categorization_data_validate_item_assignments_success():
    """Test successful item assignment validation."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
        Category(name="Fish", correct_items=["item5", "item6"]),
    ]
    items = [
        CategoryItem(id="item1", text="Dolphin"),
        CategoryItem(id="item2", text="Elephant"),
        CategoryItem(id="item3", text="Eagle"),
        CategoryItem(id="item4", text="Penguin"),
        CategoryItem(id="item5", text="Shark"),
        CategoryItem(id="item6", text="Salmon"),
    ]

    data = CategorizationData(question_text="Test", categories=categories, items=items)
    # Should not raise any exception
    data.validate_item_assignments()


def test_categorization_data_validate_item_assignments_nonexistent_item():
    """Test validation fails when category references non-existent item."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    bad_categories = [
        Category(name="Mammals", correct_items=["nonexistent_item"]),
        Category(name="Birds", correct_items=["item3"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(
        question_text="Test", categories=bad_categories, items=items
    )

    with pytest.raises(ValueError) as exc_info:
        data.validate_item_assignments()
    assert "references non-existent item ID" in str(exc_info.value)


def test_categorization_data_validate_item_assignments_duplicate_assignment():
    """Test validation fails when item is assigned to multiple categories."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    bad_categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(
            name="Birds", correct_items=["item2", "item3"]
        ),  # item2 assigned twice
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(
        question_text="Test", categories=bad_categories, items=items
    )

    with pytest.raises(ValueError) as exc_info:
        data.validate_item_assignments()
    assert "is assigned to multiple categories" in str(exc_info.value)


def test_categorization_data_validate_item_assignments_unassigned_items():
    """Test validation fails when items are not assigned to any category."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    incomplete_categories = [
        Category(name="Mammals", correct_items=["item1"]),
        Category(name="Birds", correct_items=["item3"]),
        # item2, item4, item5, item6 are unassigned
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(
        question_text="Test", categories=incomplete_categories, items=items
    )

    with pytest.raises(ValueError) as exc_info:
        data.validate_item_assignments()
    assert "Items not assigned to any category" in str(exc_info.value)


def test_categorization_data_get_all_items():
    """Test getting all items including distractors."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]
    distractors = [CategoryItem(id="dist1", text="Jellyfish")]

    data = CategorizationData(
        question_text="Test",
        categories=categories,
        items=items,
        distractors=distractors,
    )

    all_items = data.get_all_items()
    assert len(all_items) == 7  # 6 items + 1 distractor


def test_categorization_data_get_all_items_no_distractors():
    """Test getting all items when no distractors."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(question_text="Test", categories=categories, items=items)

    all_items = data.get_all_items()
    assert len(all_items) == 6


def test_categorization_data_get_category_by_id():
    """Test getting category by ID."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(question_text="Test", categories=categories, items=items)

    category = data.get_category_by_id(categories[0].id)
    assert category is not None
    assert category.name == "Mammals"


def test_categorization_data_get_category_by_id_not_found():
    """Test getting category by non-existent ID."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(question_text="Test", categories=categories, items=items)

    category = data.get_category_by_id("nonexistent")
    assert category is None


def test_categorization_data_get_item_by_id():
    """Test getting item by ID."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [
        CategoryItem(id="item1", text="Dolphin"),
        CategoryItem(id="item2", text="Elephant"),
        CategoryItem(id="item3", text="Eagle"),
        CategoryItem(id="item4", text="Penguin"),
        CategoryItem(id="item5", text="Shark"),
        CategoryItem(id="item6", text="Octopus"),
    ]

    data = CategorizationData(question_text="Test", categories=categories, items=items)

    item = data.get_item_by_id("item1")
    assert item is not None
    assert item.text == "Dolphin"


def test_categorization_data_get_item_by_id_not_found():
    """Test getting item by non-existent ID."""
    from src.question.types.categorization import (
        CategorizationData,
        Category,
        CategoryItem,
    )

    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(question_text="Test", categories=categories, items=items)

    item = data.get_item_by_id("nonexistent")
    assert item is None


def test_categorization_question_type_properties():
    """Test CategorizationQuestionType properties."""
    from src.question.types import QuestionType
    from src.question.types.categorization import (
        CategorizationData,
        CategorizationQuestionType,
    )

    question_type = CategorizationQuestionType()
    assert question_type.question_type == QuestionType.CATEGORIZATION
    assert question_type.data_model == CategorizationData


def test_categorization_question_type_validate_data():
    """Test data validation in CategorizationQuestionType."""
    from src.question.types.categorization import (
        CategorizationData,
        CategorizationQuestionType,
    )

    question_type = CategorizationQuestionType()
    data = {
        "question_text": "Categorize these animals by their biological class",
        "categories": [
            {"name": "Mammals", "correct_items": ["item1", "item2"]},
            {"name": "Birds", "correct_items": ["item3", "item4"]},
            {"name": "Fish", "correct_items": ["item5", "item6"]},
        ],
        "items": [
            {"id": "item1", "text": "Dolphin"},
            {"id": "item2", "text": "Elephant"},
            {"id": "item3", "text": "Eagle"},
            {"id": "item4", "text": "Penguin"},
            {"id": "item5", "text": "Shark"},
            {"id": "item6", "text": "Octopus"},
        ],
        "distractors": [
            {"id": "dist1", "text": "Jellyfish"},
            {"id": "dist2", "text": "Coral"},
        ],
        "explanation": "These categories represent major vertebrate classes.",
    }

    result = question_type.validate_data(data)
    assert isinstance(result, CategorizationData)
    assert len(result.categories) == 3
    assert len(result.items) == 6
    assert len(result.distractors) == 2


def test_categorization_question_type_validate_data_with_item_assignment_error():
    """Test validation fails with item assignment errors."""
    from src.question.types.categorization import CategorizationQuestionType

    question_type = CategorizationQuestionType()
    invalid_data = {
        "question_text": "Test",
        "categories": [
            {"name": "Mammals", "correct_items": ["nonexistent_item"]},
            {"name": "Birds", "correct_items": ["item3"]},
        ],
        "items": [{"id": f"item{i}", "text": f"Item{i}"} for i in range(1, 7)],
    }

    with pytest.raises(ValueError) as exc_info:
        question_type.validate_data(invalid_data)
    assert "references non-existent item ID" in str(exc_info.value)


def test_categorization_question_type_validate_data_wrong_structure():
    """Test validation with wrong data structure."""
    from pydantic import ValidationError

    from src.question.types.categorization import CategorizationQuestionType

    question_type = CategorizationQuestionType()

    with pytest.raises(ValidationError):
        question_type.validate_data({"invalid": "data"})


def test_categorization_question_type_format_for_display():
    """Test formatting for display."""
    from src.question.types.categorization import (
        CategorizationData,
        CategorizationQuestionType,
        Category,
        CategoryItem,
    )

    question_type = CategorizationQuestionType()
    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [
        CategoryItem(id="item1", text="Dolphin"),
        CategoryItem(id="item2", text="Elephant"),
        CategoryItem(id="item3", text="Eagle"),
        CategoryItem(id="item4", text="Penguin"),
        CategoryItem(id="item5", text="Shark"),
        CategoryItem(id="item6", text="Octopus"),
    ]
    distractors = [
        CategoryItem(id="dist1", text="Jellyfish"),
        CategoryItem(id="dist2", text="Coral"),
    ]

    data = CategorizationData(
        question_text="Categorize these animals by their biological class",
        categories=categories,
        items=items,
        distractors=distractors,
        explanation="These categories represent major vertebrate classes.",
    )

    result = question_type.format_for_display(data)

    assert (
        result["question_text"] == "Categorize these animals by their biological class"
    )
    assert len(result["categories"]) == 2
    assert len(result["items"]) == 6
    assert len(result["distractors"]) == 2
    assert result["question_type"] == "categorization"

    # Check category structure
    mammals_category = next(
        cat for cat in result["categories"] if cat["name"] == "Mammals"
    )
    assert mammals_category["correct_items"] == ["item1", "item2"]


def test_categorization_question_type_format_for_display_no_distractors():
    """Test formatting for display without distractors."""
    from src.question.types.categorization import (
        CategorizationData,
        CategorizationQuestionType,
        Category,
        CategoryItem,
    )

    question_type = CategorizationQuestionType()
    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(question_text="Test", categories=categories, items=items)

    result = question_type.format_for_display(data)
    assert "distractors" not in result


def test_categorization_question_type_format_for_display_wrong_type():
    """Test format_for_display with wrong data type."""
    from src.question.types.categorization import CategorizationQuestionType

    question_type = CategorizationQuestionType()

    with pytest.raises(ValueError, match="Expected CategorizationData"):
        question_type.format_for_display("wrong_type")


def test_categorization_question_type_format_for_canvas():
    """Test Canvas export formatting."""
    from src.question.types.categorization import (
        CategorizationData,
        CategorizationQuestionType,
        Category,
        CategoryItem,
    )

    question_type = CategorizationQuestionType()
    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [
        CategoryItem(id="item1", text="Dolphin"),
        CategoryItem(id="item2", text="Elephant"),
        CategoryItem(id="item3", text="Eagle"),
        CategoryItem(id="item4", text="Penguin"),
        CategoryItem(id="item5", text="Shark"),
        CategoryItem(id="item6", text="Octopus"),
    ]
    distractors = [
        CategoryItem(id="dist1", text="Jellyfish"),
        CategoryItem(id="dist2", text="Coral"),
    ]

    data = CategorizationData(
        question_text="Categorize these animals by their biological class",
        categories=categories,
        items=items,
        distractors=distractors,
    )

    result = question_type.format_for_canvas(data)

    # Validate basic structure
    assert "title" in result
    assert (
        result["item_body"]
        == "<p>Categorize these animals by their biological class</p>"
    )
    assert result["calculator_type"] == "none"
    assert result["interaction_type_slug"] == "categorization"
    assert result["scoring_algorithm"] == "Categorization"
    assert result["points_possible"] == 2  # 2 categories

    # Validate interaction_data
    interaction_data = result["interaction_data"]
    assert "categories" in interaction_data
    assert "distractors" in interaction_data
    assert "category_order" in interaction_data

    assert len(interaction_data["categories"]) == 2
    assert len(interaction_data["distractors"]) == 8  # 6 items + 2 distractors
    assert len(interaction_data["category_order"]) == 2

    # Validate scoring_data
    scoring_data = result["scoring_data"]
    assert "value" in scoring_data
    assert "score_method" in scoring_data
    assert scoring_data["score_method"] == "all_or_nothing"
    assert len(scoring_data["value"]) == 2  # 2 categories

    # Check that each category has scoring data
    for category_score in scoring_data["value"]:
        assert "id" in category_score
        assert "scoring_data" in category_score
        assert category_score["scoring_data"]["scoring_algorithm"] == "AllOrNothing"


def test_categorization_question_type_format_for_canvas_no_distractors():
    """Test Canvas export formatting without distractors."""
    from src.question.types.categorization import (
        CategorizationData,
        CategorizationQuestionType,
        Category,
        CategoryItem,
    )

    question_type = CategorizationQuestionType()
    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(question_text="Test", categories=categories, items=items)

    result = question_type.format_for_canvas(data)
    assert (
        len(result["interaction_data"]["distractors"]) == 6
    )  # Only items, no distractors


def test_categorization_question_type_format_for_canvas_wrong_type():
    """Test Canvas formatting with wrong data type."""
    from src.question.types.categorization import CategorizationQuestionType

    question_type = CategorizationQuestionType()

    with pytest.raises(ValueError, match="Expected CategorizationData"):
        question_type.format_for_canvas("wrong_type")


def test_categorization_question_type_format_for_export():
    """Test generic export formatting."""
    from src.question.types.categorization import (
        CategorizationData,
        CategorizationQuestionType,
        Category,
        CategoryItem,
    )

    question_type = CategorizationQuestionType()
    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [
        CategoryItem(id="item1", text="Dolphin"),
        CategoryItem(id="item2", text="Elephant"),
        CategoryItem(id="item3", text="Eagle"),
        CategoryItem(id="item4", text="Penguin"),
        CategoryItem(id="item5", text="Shark"),
        CategoryItem(id="item6", text="Octopus"),
    ]
    distractors = [
        CategoryItem(id="dist1", text="Jellyfish"),
        CategoryItem(id="dist2", text="Coral"),
    ]

    data = CategorizationData(
        question_text="Categorize these animals by their biological class",
        categories=categories,
        items=items,
        distractors=distractors,
        explanation="These categories represent major vertebrate classes.",
    )

    result = question_type.format_for_export(data)

    expected_structure = {
        "question_text": "Categorize these animals by their biological class",
        "question_type": "categorization",
        "explanation": "These categories represent major vertebrate classes.",
    }

    for key, value in expected_structure.items():
        assert result[key] == value

    assert len(result["categories"]) == 2
    assert len(result["items"]) == 6
    assert len(result["distractors"]) == 2


def test_categorization_question_type_format_for_export_no_distractors():
    """Test export formatting without distractors."""
    from src.question.types.categorization import (
        CategorizationData,
        CategorizationQuestionType,
        Category,
        CategoryItem,
    )

    question_type = CategorizationQuestionType()
    categories = [
        Category(name="Mammals", correct_items=["item1", "item2"]),
        Category(name="Birds", correct_items=["item3", "item4"]),
    ]
    items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(1, 7)]

    data = CategorizationData(question_text="Test", categories=categories, items=items)

    result = question_type.format_for_export(data)
    assert "distractors" not in result


def test_categorization_question_type_format_for_export_wrong_type():
    """Test export formatting with wrong data type."""
    from src.question.types.categorization import CategorizationQuestionType

    question_type = CategorizationQuestionType()

    with pytest.raises(ValueError, match="Expected CategorizationData"):
        question_type.format_for_export("wrong_type")


def test_categorization_registry_registration():
    """Test that categorization type is registered."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    assert registry.is_registered(QuestionType.CATEGORIZATION)


def test_categorization_registry_get_question_type():
    """Test getting categorization question type from registry."""
    from src.question.types import QuestionType, get_question_type_registry
    from src.question.types.categorization import CategorizationQuestionType

    registry = get_question_type_registry()
    question_type = registry.get_question_type(QuestionType.CATEGORIZATION)
    assert isinstance(question_type, CategorizationQuestionType)


def test_categorization_registry_available_types():
    """Test that available types includes categorization."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    available_types = registry.get_available_types()
    assert QuestionType.CATEGORIZATION in available_types
    assert QuestionType.MULTIPLE_CHOICE in available_types
    assert QuestionType.FILL_IN_BLANK in available_types
    assert QuestionType.MATCHING in available_types


def test_categorization_end_to_end_workflow():
    """Test complete workflow from raw data to Canvas export."""
    from src.question.types import QuestionType, get_question_type_registry

    # Raw AI response data
    raw_data = {
        "question_text": "Classify these programming concepts by category",
        "categories": [
            {"name": "Data Structures", "correct_items": ["item1", "item2"]},
            {"name": "Algorithms", "correct_items": ["item3", "item4"]},
            {"name": "Programming Paradigms", "correct_items": ["item5", "item6"]},
        ],
        "items": [
            {"id": "item1", "text": "Array"},
            {"id": "item2", "text": "Linked List"},
            {"id": "item3", "text": "Binary Search"},
            {"id": "item4", "text": "Quick Sort"},
            {"id": "item5", "text": "Object-Oriented"},
            {"id": "item6", "text": "Functional"},
        ],
        "distractors": [
            {"id": "dist1", "text": "IDE"},
            {"id": "dist2", "text": "Compiler"},
        ],
        "explanation": "These represent fundamental computer science concepts organized by their primary domain.",
    }

    # Get question type and validate data
    registry = get_question_type_registry()
    categorization_type = registry.get_question_type(QuestionType.CATEGORIZATION)
    validated_data = categorization_type.validate_data(raw_data)

    # Format for different outputs
    display_format = categorization_type.format_for_display(validated_data)
    canvas_format = categorization_type.format_for_canvas(validated_data)
    export_format = categorization_type.format_for_export(validated_data)

    # Validate all formats work
    assert display_format["question_type"] == "categorization"
    assert canvas_format["interaction_type_slug"] == "categorization"
    assert export_format["question_type"] == "categorization"

    # Validate data consistency
    assert len(display_format["categories"]) == 3
    assert len(canvas_format["scoring_data"]["value"]) == 3
    assert len(export_format["categories"]) == 3


def test_categorization_validation_round_trip():
    """Test that data can be validated and re-validated."""
    from src.question.types.categorization import CategorizationQuestionType

    question_type = CategorizationQuestionType()
    original_data = {
        "question_text": "Categorize these chemical elements",
        "categories": [
            {"name": "Noble Gases", "correct_items": ["item1", "item2"]},
            {"name": "Alkali Metals", "correct_items": ["item3", "item4"]},
            {"name": "Non-metals", "correct_items": ["item5", "item6"]},
        ],
        "items": [
            {"id": "item1", "text": "Helium"},
            {"id": "item2", "text": "Neon"},
            {"id": "item3", "text": "Sodium"},
            {"id": "item4", "text": "Potassium"},
            {"id": "item5", "text": "Hydrogen"},
            {"id": "item6", "text": "Oxygen"},
        ],
        "explanation": "Chemical elements classified by their properties.",
    }

    # Validate and export
    validated = question_type.validate_data(original_data)
    exported = question_type.format_for_export(validated)

    # Remove question_type for re-validation since it's not part of the data model
    exported_for_validation = exported.copy()
    exported_for_validation.pop("question_type", None)

    # Re-validate exported data
    re_validated = question_type.validate_data(exported_for_validation)
    re_exported = question_type.format_for_export(re_validated)

    # Should be identical
    assert exported == re_exported


def test_categorization_complex_validation_scenario():
    """Test complex validation with maximum complexity."""
    from src.question.types.categorization import CategorizationQuestionType

    # Test with maximum categories, items, and distractors
    categories_data = [
        {"name": f"Category {i}", "correct_items": [f"item{i*2+1}", f"item{i*2+2}"]}
        for i in range(4)  # 4 categories
    ]

    items_data = [
        {"id": f"item{i}", "text": f"Item {i}"}
        for i in range(1, 9)  # 8 items (2 per category)
    ]

    # Add additional items to reach minimum requirement
    for i in range(9, 13):
        items_data.append({"id": f"item{i}", "text": f"Extra Item {i}"})

    # Assign extra items to categories
    categories_data[0]["correct_items"].extend(["item9", "item10"])
    categories_data[1]["correct_items"].extend(["item11", "item12"])

    distractors_data = [
        {"id": f"dist{i}", "text": f"Distractor {i}"}
        for i in range(1, 4)  # 3 distractors
    ]

    complex_data = {
        "question_text": "Complex categorization with special characters: áéíóú & symbols!",
        "categories": categories_data,
        "items": items_data,
        "distractors": distractors_data,
        "explanation": "This tests maximum complexity with special characters and symbols.",
    }

    categorization_type = CategorizationQuestionType()
    validated_data = categorization_type.validate_data(complex_data)

    # Should validate successfully
    assert len(validated_data.categories) == 4
    assert len(validated_data.items) == 12
    assert len(validated_data.distractors) == 3

    # Canvas export should work
    canvas_format = categorization_type.format_for_canvas(validated_data)
    assert canvas_format["points_possible"] == 4
    assert (
        len(canvas_format["interaction_data"]["distractors"]) == 15
    )  # 12 items + 3 distractors
