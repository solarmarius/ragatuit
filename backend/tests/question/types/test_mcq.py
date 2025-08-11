"""Tests for Multiple Choice Question type implementation."""

import re
import uuid

import pytest


def test_multiple_choice_data_creation():
    """Test creating MultipleChoiceData with valid data."""
    from src.question.types.mcq import MultipleChoiceData

    data = MultipleChoiceData(
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
        explanation="Paris is the capital of France.",
    )
    assert data.question_text == "What is the capital of France?"
    assert data.option_a == "Paris"
    assert data.option_b == "London"
    assert data.option_c == "Berlin"
    assert data.option_d == "Madrid"
    assert data.correct_answer == "A"
    assert data.explanation == "Paris is the capital of France."


def test_multiple_choice_data_minimal():
    """Test MultipleChoiceData with minimal required fields."""
    from src.question.types.mcq import MultipleChoiceData

    data = MultipleChoiceData(
        question_text="What is 2+2?",
        option_a="3",
        option_b="4",
        option_c="5",
        option_d="6",
        correct_answer="B",
    )
    assert data.explanation is None
    assert data.correct_answer == "B"


def test_multiple_choice_data_question_text_validation():
    """Test question text validation."""
    from pydantic import ValidationError

    from src.question.types.mcq import MultipleChoiceData

    # Valid question text
    MultipleChoiceData(
        question_text="Valid question?",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )

    # Empty question text
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
        )
    assert "String should have at least 1 character" in str(exc_info.value)

    # Question text too long
    long_text = "x" * 2001
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text=long_text,
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
        )
    assert "String should have at most 2000 characters" in str(exc_info.value)


def test_multiple_choice_data_option_validation():
    """Test option validation for all options."""
    from pydantic import ValidationError

    from src.question.types.mcq import MultipleChoiceData

    # Valid options
    MultipleChoiceData(
        question_text="Test?",
        option_a="Option A",
        option_b="Option B",
        option_c="Option C",
        option_d="Option D",
        correct_answer="A",
    )

    # Empty option A
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="Test?",
            option_a="",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
        )
    assert "String should have at least 1 character" in str(exc_info.value)

    # Empty option B
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="Test?",
            option_a="A",
            option_b="",
            option_c="C",
            option_d="D",
            correct_answer="A",
        )
    assert "String should have at least 1 character" in str(exc_info.value)

    # Empty option C
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="Test?",
            option_a="A",
            option_b="B",
            option_c="",
            option_d="D",
            correct_answer="A",
        )
    assert "String should have at least 1 character" in str(exc_info.value)

    # Empty option D
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="Test?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="",
            correct_answer="A",
        )
    assert "String should have at least 1 character" in str(exc_info.value)


def test_multiple_choice_data_option_length_validation():
    """Test option length validation."""
    from pydantic import ValidationError

    from src.question.types.mcq import MultipleChoiceData

    # Valid max length option
    max_option = "x" * 500
    MultipleChoiceData(
        question_text="Test?",
        option_a=max_option,
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )

    # Option A too long
    long_option = "x" * 501
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="Test?",
            option_a=long_option,
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
        )
    assert "String should have at most 500 characters" in str(exc_info.value)

    # Option B too long
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="Test?",
            option_a="A",
            option_b=long_option,
            option_c="C",
            option_d="D",
            correct_answer="A",
        )
    assert "String should have at most 500 characters" in str(exc_info.value)

    # Option C too long
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="Test?",
            option_a="A",
            option_b="B",
            option_c=long_option,
            option_d="D",
            correct_answer="A",
        )
    assert "String should have at most 500 characters" in str(exc_info.value)

    # Option D too long
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="Test?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d=long_option,
            correct_answer="A",
        )
    assert "String should have at most 500 characters" in str(exc_info.value)


def test_multiple_choice_data_correct_answer_validation():
    """Test correct answer validation."""
    from pydantic import ValidationError

    from src.question.types.mcq import MultipleChoiceData

    # Valid correct answers
    for answer in ["A", "B", "C", "D"]:
        MultipleChoiceData(
            question_text="Test?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer=answer,
        )

    # Invalid correct answers
    invalid_answers = ["E", "1", "a", "b", "", "AB", "INVALID"]
    for invalid_answer in invalid_answers:
        with pytest.raises(ValidationError) as exc_info:
            MultipleChoiceData(
                question_text="Test?",
                option_a="A",
                option_b="B",
                option_c="C",
                option_d="D",
                correct_answer=invalid_answer,
            )
        # Check both validator error and pattern error messages
        error_msg = str(exc_info.value)
        assert (
            "Correct answer must be A, B, C, or D" in error_msg
            or "String should match pattern" in error_msg
        )


def test_multiple_choice_data_explanation_validation():
    """Test explanation validation."""
    from pydantic import ValidationError

    from src.question.types.mcq import MultipleChoiceData

    # Valid explanation
    MultipleChoiceData(
        question_text="Test?",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
        explanation="This is a valid explanation.",
    )

    # No explanation (should be allowed)
    MultipleChoiceData(
        question_text="Test?",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )

    # Explanation too long
    long_explanation = "x" * 1001
    with pytest.raises(ValidationError) as exc_info:
        MultipleChoiceData(
            question_text="Test?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
            explanation=long_explanation,
        )
    assert "String should have at most 1000 characters" in str(exc_info.value)


def test_multiple_choice_data_get_correct_option_text():
    """Test getting correct option text."""
    from src.question.types.mcq import MultipleChoiceData

    data = MultipleChoiceData(
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
    )
    assert data.get_correct_option_text() == "Paris"

    # Test with different correct answers
    data.correct_answer = "B"
    assert data.get_correct_option_text() == "London"

    data.correct_answer = "C"
    assert data.get_correct_option_text() == "Berlin"

    data.correct_answer = "D"
    assert data.get_correct_option_text() == "Madrid"


def test_multiple_choice_data_get_all_options():
    """Test getting all options dictionary."""
    from src.question.types.mcq import MultipleChoiceData

    data = MultipleChoiceData(
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
    )

    expected = {"A": "Paris", "B": "London", "C": "Berlin", "D": "Madrid"}
    assert data.get_all_options() == expected


def test_multiple_choice_question_type_properties():
    """Test MultipleChoiceQuestionType properties."""
    from src.question.types import QuestionType
    from src.question.types.mcq import MultipleChoiceData, MultipleChoiceQuestionType

    question_type = MultipleChoiceQuestionType()
    assert question_type.question_type == QuestionType.MULTIPLE_CHOICE
    assert question_type.data_model == MultipleChoiceData


def test_multiple_choice_question_type_validate_data():
    """Test data validation in MultipleChoiceQuestionType."""
    from src.question.types.mcq import MultipleChoiceData, MultipleChoiceQuestionType

    question_type = MultipleChoiceQuestionType()
    data = {
        "question_text": "What is the capital of France?",
        "option_a": "Paris",
        "option_b": "London",
        "option_c": "Berlin",
        "option_d": "Madrid",
        "correct_answer": "A",
        "explanation": "Paris is the capital of France.",
    }

    result = question_type.validate_data(data)
    assert isinstance(result, MultipleChoiceData)
    assert result.question_text == "What is the capital of France?"
    assert result.option_a == "Paris"
    assert result.correct_answer == "A"
    assert result.explanation == "Paris is the capital of France."


def test_multiple_choice_question_type_validate_invalid_data():
    """Test validation of invalid data."""
    from pydantic import ValidationError

    from src.question.types.mcq import MultipleChoiceQuestionType

    question_type = MultipleChoiceQuestionType()

    # Missing required fields
    with pytest.raises(ValidationError):
        question_type.validate_data({"question_text": "Test?"})

    # Invalid correct answer
    with pytest.raises(ValidationError):
        question_type.validate_data(
            {
                "question_text": "Test?",
                "option_a": "A",
                "option_b": "B",
                "option_c": "C",
                "option_d": "D",
                "correct_answer": "E",
            }
        )


def test_multiple_choice_question_type_format_for_display():
    """Test formatting for display."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    data = MultipleChoiceData(
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
        explanation="Paris is the capital of France.",
    )

    result = question_type.format_for_display(data)
    expected = {
        "question_text": "What is the capital of France?",
        "options": {"A": "Paris", "B": "London", "C": "Berlin", "D": "Madrid"},
        "correct_answer": "A",
        "explanation": "Paris is the capital of France.",
        "question_type": "multiple_choice",
    }
    assert result == expected


def test_multiple_choice_question_type_format_for_display_no_explanation():
    """Test formatting for display without explanation."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    data = MultipleChoiceData(
        question_text="What is 2+2?",
        option_a="3",
        option_b="4",
        option_c="5",
        option_d="6",
        correct_answer="B",
    )

    result = question_type.format_for_display(data)
    assert result["explanation"] is None
    assert result["correct_answer"] == "B"


def test_multiple_choice_question_type_format_for_display_wrong_type():
    """Test formatting for display with wrong data type."""
    from src.question.types.mcq import MultipleChoiceQuestionType

    question_type = MultipleChoiceQuestionType()

    with pytest.raises(ValueError, match="Expected MultipleChoiceData"):
        question_type.format_for_display("wrong_type")


def test_multiple_choice_question_type_format_for_canvas():
    """Test Canvas export formatting."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    data = MultipleChoiceData(
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
    )

    result = question_type.format_for_canvas(data)

    # Validate basic structure
    assert "title" in result
    assert result["item_body"] == "<p>What is the capital of France?</p>"
    assert result["calculator_type"] == "none"
    assert result["interaction_type_slug"] == "choice"
    assert result["scoring_algorithm"] == "Equivalence"
    assert result["points_possible"] == 1

    # Validate interaction_data
    interaction_data = result["interaction_data"]
    assert "choices" in interaction_data
    assert len(interaction_data["choices"]) == 4

    # Check choice structure and validate UUIDs
    choices = interaction_data["choices"]
    uuid_pattern = (
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )

    # Validate first choice
    assert re.match(
        uuid_pattern, choices[0]["id"]
    ), "First choice ID should be a valid UUID"
    assert choices[0]["position"] == 1
    assert choices[0]["item_body"] == "<p>Paris</p>"

    # Validate other choice content (IDs are UUIDs, content should match)
    assert choices[1]["item_body"] == "<p>London</p>"
    assert choices[2]["item_body"] == "<p>Berlin</p>"
    assert choices[3]["item_body"] == "<p>Madrid</p>"

    # Validate all choice IDs are proper UUIDs
    for i, choice in enumerate(choices):
        assert re.match(
            uuid_pattern, choice["id"]
        ), f"Choice {i} ID should be a valid UUID"
        assert choice["position"] == i + 1

    # Validate scoring data uses UUID (A=0, so first choice UUID)
    scoring_value = result["scoring_data"]["value"]
    assert (
        scoring_value == choices[0]["id"]
    ), "Scoring value should be the UUID of the correct choice"
    assert re.match(uuid_pattern, scoring_value)

    # Validate properties
    properties = result["properties"]
    assert properties["shuffle_rules"]["choices"]["shuffled"] is True
    assert properties["vary_points_by_answer"] is False

    # Validate feedback - should be empty when no explanation
    assert result["feedback"] == {}


def test_multiple_choice_question_type_format_for_canvas_uuid_compliance():
    """Test that Canvas formatting uses proper UUIDs as per Canvas New Quizzes API requirements."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    data = MultipleChoiceData(
        question_text="Which language is used for web development?",
        option_a="JavaScript",
        option_b="Python",
        option_c="Java",
        option_d="C++",
        correct_answer="A",
    )

    result = question_type.format_for_canvas(data)

    # Validate that all choice IDs are proper UUIDs (Version 4)
    uuid_pattern = (
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    choices = result["interaction_data"]["choices"]

    assert len(choices) == 4
    choice_ids = []
    for i, choice in enumerate(choices):
        choice_id = choice["id"]
        choice_ids.append(choice_id)
        # Validate UUID format
        assert re.match(
            uuid_pattern, choice_id
        ), f"Choice {i} ID '{choice_id}' is not a valid UUID4"
        # Validate UUID can be parsed
        uuid.UUID(choice_id)  # Should not raise exception
        # Validate position is correct
        assert choice["position"] == i + 1

    # Validate all UUIDs are unique
    assert len(set(choice_ids)) == 4, "All choice UUIDs should be unique"

    # Validate scoring data uses the correct choice UUID (A=0, so first choice)
    scoring_value = result["scoring_data"]["value"]
    assert (
        scoring_value == choice_ids[0]
    ), "Scoring value should be the UUID of the correct choice"
    assert re.match(
        uuid_pattern, scoring_value
    ), "Scoring value should be a valid UUID4"


def test_multiple_choice_question_type_format_for_canvas_different_answers():
    """Test Canvas formatting with different correct answers uses correct UUIDs."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    uuid_pattern = (
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )

    # Test answer B (index 1)
    data_b = MultipleChoiceData(
        question_text="What is 2+2?",
        option_a="3",
        option_b="4",
        option_c="5",
        option_d="6",
        correct_answer="B",
    )
    result_b = question_type.format_for_canvas(data_b)
    choices_b = result_b["interaction_data"]["choices"]
    assert result_b["scoring_data"]["value"] == choices_b[1]["id"]  # Second choice UUID
    assert re.match(uuid_pattern, result_b["scoring_data"]["value"])

    # Test answer C (index 2)
    data_c = MultipleChoiceData(
        question_text="What is 3+3?",
        option_a="5",
        option_b="6",
        option_c="7",
        option_d="8",
        correct_answer="C",
    )
    result_c = question_type.format_for_canvas(data_c)
    choices_c = result_c["interaction_data"]["choices"]
    assert result_c["scoring_data"]["value"] == choices_c[2]["id"]  # Third choice UUID
    assert re.match(uuid_pattern, result_c["scoring_data"]["value"])

    # Test answer D (index 3)
    data_d = MultipleChoiceData(
        question_text="What is 4+4?",
        option_a="6",
        option_b="7",
        option_c="8",
        option_d="9",
        correct_answer="D",
    )
    result_d = question_type.format_for_canvas(data_d)
    choices_d = result_d["interaction_data"]["choices"]
    assert result_d["scoring_data"]["value"] == choices_d[3]["id"]  # Fourth choice UUID
    assert re.match(uuid_pattern, result_d["scoring_data"]["value"])


def test_multiple_choice_question_type_format_for_canvas_html_wrapping():
    """Test Canvas formatting HTML wrapping behavior."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()

    # Question text without HTML tags
    data = MultipleChoiceData(
        question_text="Plain text question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )
    result = question_type.format_for_canvas(data)
    assert result["item_body"] == "<p>Plain text question</p>"

    # Question text already with HTML tags
    data_html = MultipleChoiceData(
        question_text="<p>Already wrapped question</p>",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )
    result_html = question_type.format_for_canvas(data_html)
    assert result_html["item_body"] == "<p>Already wrapped question</p>"


def test_multiple_choice_question_type_format_for_canvas_wrong_type():
    """Test Canvas formatting with wrong data type."""
    from src.question.types.mcq import MultipleChoiceQuestionType

    question_type = MultipleChoiceQuestionType()

    with pytest.raises(ValueError, match="Expected MultipleChoiceData"):
        question_type.format_for_canvas("wrong_type")


def test_multiple_choice_question_type_format_for_canvas_with_explanation():
    """Test Canvas export formatting with explanation."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    data = MultipleChoiceData(
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
        explanation="Paris is the capital city of France and its largest city.",
    )

    result = question_type.format_for_canvas(data)

    # Validate feedback contains explanation
    assert "feedback" in result
    assert "neutral" in result["feedback"]
    assert (
        result["feedback"]["neutral"]
        == "Paris is the capital city of France and its largest city."
    )


def test_multiple_choice_question_type_format_for_canvas_empty_explanation():
    """Test Canvas export formatting with empty string explanation."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    data = MultipleChoiceData(
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
        explanation="",
    )

    result = question_type.format_for_canvas(data)

    # Validate feedback is empty dict when explanation is empty string
    assert result["feedback"] == {}


def test_multiple_choice_question_type_format_for_canvas_max_explanation():
    """Test Canvas export formatting with maximum length explanation."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    max_explanation = "x" * 1000  # Maximum allowed length
    data = MultipleChoiceData(
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
        explanation=max_explanation,
    )

    result = question_type.format_for_canvas(data)

    # Validate feedback contains full explanation
    assert "feedback" in result
    assert "neutral" in result["feedback"]
    assert result["feedback"]["neutral"] == max_explanation
    assert len(result["feedback"]["neutral"]) == 1000


def test_multiple_choice_question_type_format_for_export():
    """Test generic export formatting."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    data = MultipleChoiceData(
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
        explanation="Paris is the capital of France.",
    )

    result = question_type.format_for_export(data)
    expected = {
        "question_text": "What is the capital of France?",
        "option_a": "Paris",
        "option_b": "London",
        "option_c": "Berlin",
        "option_d": "Madrid",
        "correct_answer": "A",
        "explanation": "Paris is the capital of France.",
        "question_type": "multiple_choice",
    }
    assert result == expected


def test_multiple_choice_question_type_format_for_export_no_explanation():
    """Test export formatting without explanation."""
    from src.question.types.mcq import (
        MultipleChoiceData,
        MultipleChoiceQuestionType,
    )

    question_type = MultipleChoiceQuestionType()
    data = MultipleChoiceData(
        question_text="What is 2+2?",
        option_a="3",
        option_b="4",
        option_c="5",
        option_d="6",
        correct_answer="B",
    )

    result = question_type.format_for_export(data)
    assert result["explanation"] is None
    assert result["correct_answer"] == "B"


def test_multiple_choice_question_type_format_for_export_wrong_type():
    """Test export formatting with wrong data type."""
    from src.question.types.mcq import MultipleChoiceQuestionType

    question_type = MultipleChoiceQuestionType()

    with pytest.raises(ValueError, match="Expected MultipleChoiceData"):
        question_type.format_for_export("wrong_type")


def test_multiple_choice_question_type_migrate_from_legacy():
    """Test migration from legacy question format."""
    from src.question.types.mcq import MultipleChoiceQuestionType

    # Mock legacy question object
    class MockLegacyQuestion:
        def __init__(self):
            self.question_text = "Legacy question?"
            self.option_a = "Legacy A"
            self.option_b = "Legacy B"
            self.option_c = "Legacy C"
            self.option_d = "Legacy D"
            self.correct_answer = "B"

    question_type = MultipleChoiceQuestionType()
    legacy_question = MockLegacyQuestion()

    migrated_data = question_type.migrate_from_legacy(legacy_question)

    assert migrated_data.question_text == "Legacy question?"
    assert migrated_data.option_a == "Legacy A"
    assert migrated_data.option_b == "Legacy B"
    assert migrated_data.option_c == "Legacy C"
    assert migrated_data.option_d == "Legacy D"
    assert migrated_data.correct_answer == "B"
    assert migrated_data.explanation is None  # Legacy doesn't have explanation


def test_multiple_choice_registry_registration():
    """Test that multiple choice type is registered."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    assert registry.is_registered(QuestionType.MULTIPLE_CHOICE)


def test_multiple_choice_registry_get_question_type():
    """Test getting multiple choice question type from registry."""
    from src.question.types import QuestionType, get_question_type_registry
    from src.question.types.mcq import MultipleChoiceQuestionType

    registry = get_question_type_registry()
    question_type = registry.get_question_type(QuestionType.MULTIPLE_CHOICE)
    assert isinstance(question_type, MultipleChoiceQuestionType)


def test_multiple_choice_registry_available_types():
    """Test that available types includes multiple choice."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    available_types = registry.get_available_types()
    assert QuestionType.MULTIPLE_CHOICE in available_types


def test_multiple_choice_end_to_end_workflow():
    """Test complete workflow from raw data to Canvas export."""
    from src.question.types import QuestionType, get_question_type_registry

    # Raw AI response data
    raw_data = {
        "question_text": "Which programming language was created by Guido van Rossum?",
        "option_a": "Python",
        "option_b": "Java",
        "option_c": "JavaScript",
        "option_d": "C++",
        "correct_answer": "A",
        "explanation": "Python was created by Guido van Rossum and first released in 1991.",
    }

    # Get question type and validate data
    registry = get_question_type_registry()
    mcq_type = registry.get_question_type(QuestionType.MULTIPLE_CHOICE)
    validated_data = mcq_type.validate_data(raw_data)

    # Format for different outputs
    display_format = mcq_type.format_for_display(validated_data)
    canvas_format = mcq_type.format_for_canvas(validated_data)
    export_format = mcq_type.format_for_export(validated_data)

    # Validate all formats work
    assert display_format["question_type"] == "multiple_choice"
    assert canvas_format["interaction_type_slug"] == "choice"
    assert export_format["question_type"] == "multiple_choice"

    # Validate data consistency
    assert display_format["correct_answer"] == "A"
    # Canvas should use UUID for correct answer (A = index 0 = first choice UUID)
    choices = canvas_format["interaction_data"]["choices"]
    assert canvas_format["scoring_data"]["value"] == choices[0]["id"]
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        canvas_format["scoring_data"]["value"],
    )
    assert export_format["correct_answer"] == "A"

    # Validate question content consistency
    assert display_format["question_text"] == raw_data["question_text"]
    assert export_format["option_a"] == raw_data["option_a"]


def test_multiple_choice_validation_round_trip():
    """Test that data can be validated and re-validated."""
    from src.question.types.mcq import MultipleChoiceQuestionType

    question_type = MultipleChoiceQuestionType()
    original_data = {
        "question_text": "What is the most popular programming language for web development?",
        "option_a": "JavaScript",
        "option_b": "Python",
        "option_c": "Java",
        "option_d": "C#",
        "correct_answer": "A",
        "explanation": "JavaScript is the most widely used language for web development.",
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


def test_multiple_choice_complex_validation_scenario():
    """Test complex validation with edge cases and special characters."""
    from src.question.types.mcq import MultipleChoiceQuestionType

    # Test with special characters, maximum lengths, and edge cases
    complex_data = {
        "question_text": "What is the correct mathematical expression for Euler's identity? (π, e, i)",
        "option_a": "e^(iπ) + 1 = 0",
        "option_b": "e^(iπ) - 1 = 0",
        "option_c": "e^(iπ) = 1",
        "option_d": "e^(iπ) = -1",
        "correct_answer": "A",
        "explanation": "Euler's identity: e^(iπ) + 1 = 0 is considered one of the most beautiful equations in mathematics.",
    }

    mcq_type = MultipleChoiceQuestionType()
    validated_data = mcq_type.validate_data(complex_data)

    # Should validate successfully
    assert validated_data.question_text == complex_data["question_text"]
    assert validated_data.correct_answer == "A"

    # Canvas export should work with special characters
    canvas_format = mcq_type.format_for_canvas(validated_data)
    assert canvas_format["points_possible"] == 1
    assert "π" in canvas_format["item_body"]  # Special characters preserved

    # Display format should work
    display_format = mcq_type.format_for_display(validated_data)
    assert "π" in display_format["options"]["A"]


def test_multiple_choice_maximum_length_content():
    """Test with maximum allowed content lengths."""
    from src.question.types.mcq import MultipleChoiceQuestionType

    # Create data with maximum allowed lengths
    max_question = "x" * 2000
    max_option = "y" * 500
    max_explanation = "z" * 1000

    max_data = {
        "question_text": max_question,
        "option_a": max_option,
        "option_b": "Short B",
        "option_c": "Short C",
        "option_d": "Short D",
        "correct_answer": "A",
        "explanation": max_explanation,
    }

    mcq_type = MultipleChoiceQuestionType()
    validated_data = mcq_type.validate_data(max_data)

    # Should validate successfully
    assert len(validated_data.question_text) == 2000
    assert len(validated_data.option_a) == 500
    assert len(validated_data.explanation) == 1000

    # All formatting methods should work
    display_format = mcq_type.format_for_display(validated_data)
    canvas_format = mcq_type.format_for_canvas(validated_data)
    export_format = mcq_type.format_for_export(validated_data)

    assert len(display_format["question_text"]) == 2000
    assert (
        len(canvas_format["interaction_data"]["choices"][0]["item_body"]) > 500
    )  # Includes HTML
    assert len(export_format["explanation"]) == 1000


def test_multiple_choice_all_answer_options():
    """Test MCQ with each possible correct answer (A, B, C, D)."""
    from src.question.types.mcq import MultipleChoiceQuestionType

    mcq_type = MultipleChoiceQuestionType()
    base_data = {
        "question_text": "Test question",
        "option_a": "Option A",
        "option_b": "Option B",
        "option_c": "Option C",
        "option_d": "Option D",
    }

    # Test each correct answer with UUID validation
    uuid_pattern = (
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    answer_to_index = {"A": 0, "B": 1, "C": 2, "D": 3}

    for correct_answer, expected_index in answer_to_index.items():
        data = {**base_data, "correct_answer": correct_answer}
        validated_data = mcq_type.validate_data(data)

        # Test Canvas format uses UUIDs
        canvas_format = mcq_type.format_for_canvas(validated_data)
        choices = canvas_format["interaction_data"]["choices"]
        scoring_value = canvas_format["scoring_data"]["value"]

        # Validate scoring uses the correct choice UUID
        assert scoring_value == choices[expected_index]["id"]
        assert re.match(uuid_pattern, scoring_value)

        # Test display format
        display_format = mcq_type.format_for_display(validated_data)
        assert display_format["correct_answer"] == correct_answer

        # Test get_correct_option_text method
        assert validated_data.get_correct_option_text() == f"Option {correct_answer}"
