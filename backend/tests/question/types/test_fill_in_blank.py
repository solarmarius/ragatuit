"""Tests for Fill-in-Blank question type implementation."""

import pytest


def test_blank_data_creation():
    """Test creating BlankData with valid data."""
    from src.question.types.fill_in_blank import BlankData

    blank = BlankData(
        position=1,
        correct_answer="Paris",
        answer_variations=["paris", "PARIS"],
        case_sensitive=False,
    )
    assert blank.position == 1
    assert blank.correct_answer == "Paris"
    assert blank.answer_variations == ["paris", "PARIS"]
    assert blank.case_sensitive is False


def test_blank_data_minimal():
    """Test BlankData with minimal required fields."""
    from src.question.types.fill_in_blank import BlankData

    blank = BlankData(position=1, correct_answer="Paris")
    assert blank.position == 1
    assert blank.correct_answer == "Paris"
    assert blank.answer_variations is None
    assert blank.case_sensitive is False


def test_blank_data_position_validation():
    """Test position validation for BlankData."""
    from pydantic import ValidationError

    from src.question.types.fill_in_blank import BlankData

    # Valid positions
    BlankData(position=1, correct_answer="test")
    BlankData(position=100, correct_answer="test")

    # Invalid positions
    with pytest.raises(ValidationError) as exc_info:
        BlankData(position=0, correct_answer="test")
    assert "Input should be greater than or equal to 1" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        BlankData(position=101, correct_answer="test")
    assert "Input should be less than or equal to 100" in str(exc_info.value)


def test_blank_data_answer_validation():
    """Test answer validation for BlankData."""
    from pydantic import ValidationError

    from src.question.types.fill_in_blank import BlankData

    # Valid answers
    BlankData(position=1, correct_answer="Paris")
    BlankData(position=1, correct_answer="A" * 200)

    # Invalid answers
    with pytest.raises(ValidationError) as exc_info:
        BlankData(position=1, correct_answer="")
    assert "String should have at least 1 character" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        BlankData(position=1, correct_answer="A" * 201)
    assert "String should have at most 200 characters" in str(exc_info.value)


def test_answer_variations_validation():
    """Test answer variations validation and cleaning."""
    from pydantic import ValidationError

    from src.question.types.fill_in_blank import BlankData

    # Valid variations with exact duplicates
    blank = BlankData(
        position=1,
        correct_answer="Paris",
        answer_variations=["paris", "PARIS", "paris"],  # "paris" appears twice
    )
    # Should remove exact duplicates
    assert len(blank.answer_variations) == 2  # "paris" and "PARIS"
    assert "paris" in blank.answer_variations
    assert "PARIS" in blank.answer_variations

    # Empty variations should be filtered
    blank = BlankData(
        position=1,
        correct_answer="Paris",
        answer_variations=["paris", "", "  ", "PARIS"],
    )
    assert blank.answer_variations == ["paris", "PARIS"]

    # All empty variations should result in None
    blank = BlankData(
        position=1,
        correct_answer="Paris",
        answer_variations=["", "  ", "   "],
    )
    assert blank.answer_variations is None

    # Too many variations
    with pytest.raises(ValidationError) as exc_info:
        BlankData(
            position=1,
            correct_answer="Paris",
            answer_variations=[f"variation{i}" for i in range(11)],
        )
    assert "Maximum 10 answer variations allowed" in str(exc_info.value)


def test_fill_in_blank_data_creation():
    """Test creating FillInBlankData with valid data."""
    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    blanks = [
        BlankData(position=1, correct_answer="Paris"),
        BlankData(position=2, correct_answer="2.2 million"),
    ]
    data = FillInBlankData(
        question_text="The capital of France is _____ with _____ residents.",
        blanks=blanks,
        explanation="Paris is the capital of France.",
    )
    assert data.question_text == "The capital of France is _____ with _____ residents."
    assert len(data.blanks) == 2
    assert data.blanks[0].position == 1
    assert data.blanks[1].position == 2
    assert data.explanation == "Paris is the capital of France."


def test_fill_in_blank_data_blanks_sorted():
    """Test that blanks are sorted by position."""
    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    blanks = [
        BlankData(position=3, correct_answer="Third"),
        BlankData(position=1, correct_answer="First"),
        BlankData(position=2, correct_answer="Second"),
    ]
    data = FillInBlankData(
        question_text="Test question",
        blanks=blanks,
    )
    assert data.blanks[0].position == 1
    assert data.blanks[1].position == 2
    assert data.blanks[2].position == 3


def test_fill_in_blank_data_empty_blanks():
    """Test validation of empty blanks."""
    from pydantic import ValidationError

    from src.question.types.fill_in_blank import FillInBlankData

    with pytest.raises(ValidationError) as exc_info:
        FillInBlankData(
            question_text="Test question",
            blanks=[],
        )
    assert "At least one blank is required" in str(exc_info.value)


def test_fill_in_blank_data_too_many_blanks():
    """Test validation of too many blanks."""
    from pydantic import ValidationError

    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    blanks = [BlankData(position=i, correct_answer=f"Answer{i}") for i in range(1, 12)]
    with pytest.raises(ValidationError) as exc_info:
        FillInBlankData(
            question_text="Test question",
            blanks=blanks,
        )
    assert "Maximum 10 blanks allowed" in str(exc_info.value)


def test_fill_in_blank_data_duplicate_positions():
    """Test validation of duplicate positions."""
    from pydantic import ValidationError

    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    blanks = [
        BlankData(position=1, correct_answer="First"),
        BlankData(position=1, correct_answer="Duplicate"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        FillInBlankData(
            question_text="Test question",
            blanks=blanks,
        )
    assert "Each blank must have a unique position" in str(exc_info.value)


def test_fill_in_blank_data_get_blank_by_position():
    """Test getting blank by position."""
    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    blanks = [
        BlankData(position=1, correct_answer="First"),
        BlankData(position=3, correct_answer="Third"),
    ]
    data = FillInBlankData(
        question_text="Test question",
        blanks=blanks,
    )

    blank1 = data.get_blank_by_position(1)
    assert blank1 is not None
    assert blank1.correct_answer == "First"

    blank3 = data.get_blank_by_position(3)
    assert blank3 is not None
    assert blank3.correct_answer == "Third"

    blank2 = data.get_blank_by_position(2)
    assert blank2 is None


def test_fill_in_blank_data_get_all_answers():
    """Test getting all possible answers."""
    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    blanks = [
        BlankData(
            position=1,
            correct_answer="Paris",
            answer_variations=["paris", "PARIS"],
        ),
        BlankData(position=2, correct_answer="France"),
    ]
    data = FillInBlankData(
        question_text="Test question",
        blanks=blanks,
    )

    all_answers = data.get_all_answers()
    assert all_answers[1] == ["Paris", "paris", "PARIS"]
    assert all_answers[2] == ["France"]


def test_fill_in_blank_question_type_properties():
    """Test FillInBlankQuestionType properties."""
    from src.question.types import QuestionType
    from src.question.types.fill_in_blank import (
        FillInBlankData,
        FillInBlankQuestionType,
    )

    question_type = FillInBlankQuestionType()
    assert question_type.question_type == QuestionType.FILL_IN_BLANK
    assert question_type.data_model == FillInBlankData


def test_fill_in_blank_question_type_validate_data():
    """Test data validation in FillInBlankQuestionType."""
    from src.question.types.fill_in_blank import (
        FillInBlankData,
        FillInBlankQuestionType,
    )

    question_type = FillInBlankQuestionType()
    data = {
        "question_text": "The capital of France is _____.",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "Paris",
                "answer_variations": ["paris"],
                "case_sensitive": False,
            }
        ],
        "explanation": "Paris is the capital of France.",
    }

    result = question_type.validate_data(data)
    assert isinstance(result, FillInBlankData)
    assert result.question_text == "The capital of France is _____."
    assert len(result.blanks) == 1
    assert result.blanks[0].correct_answer == "Paris"


def test_fill_in_blank_question_type_validate_invalid_data():
    """Test validation of invalid data."""
    from pydantic import ValidationError

    from src.question.types.fill_in_blank import FillInBlankQuestionType

    question_type = FillInBlankQuestionType()
    data = {
        "question_text": "Test question",
        "blanks": [],  # Empty blanks should fail
    }

    with pytest.raises(ValidationError):
        question_type.validate_data(data)


def test_fill_in_blank_question_type_format_for_display():
    """Test formatting for display."""
    from src.question.types.fill_in_blank import (
        BlankData,
        FillInBlankData,
        FillInBlankQuestionType,
    )

    question_type = FillInBlankQuestionType()
    data = FillInBlankData(
        question_text="The capital of France is [blank_1].",
        blanks=[
            BlankData(
                position=1,
                correct_answer="Paris",
                answer_variations=["paris"],
                case_sensitive=False,
            )
        ],
        explanation="Paris is the capital of France.",
    )

    result = question_type.format_for_display(data)
    assert result["question_text"] == "The capital of France is [blank_1]."
    assert result["question_type"] == "fill_in_blank"
    assert result["explanation"] == "Paris is the capital of France."
    assert len(result["blanks"]) == 1
    assert result["blanks"][0]["position"] == 1
    assert result["blanks"][0]["correct_answer"] == "Paris"
    assert result["blanks"][0]["answer_variations"] == ["paris"]
    assert result["blanks"][0]["case_sensitive"] is False


def test_fill_in_blank_question_type_format_for_display_wrong_type():
    """Test formatting for display with wrong data type."""
    from src.question.types.fill_in_blank import FillInBlankQuestionType

    question_type = FillInBlankQuestionType()

    with pytest.raises(ValueError, match="Expected FillInBlankData"):
        question_type.format_for_display("wrong_type")


def test_fill_in_blank_question_type_format_for_canvas():
    """Test formatting for Canvas Rich Fill In The Blank."""
    from src.question.types.fill_in_blank import (
        BlankData,
        FillInBlankData,
        FillInBlankQuestionType,
    )

    question_type = FillInBlankQuestionType()
    data = FillInBlankData(
        question_text="The capital of France is [blank_1].",
        blanks=[
            BlankData(
                position=1,
                correct_answer="Paris",
                answer_variations=["paris"],
                case_sensitive=False,
            )
        ],
    )

    result = question_type.format_for_canvas(data)
    assert result["interaction_type_slug"] == "rich-fill-blank"
    assert result["points_possible"] == 1

    # Check interaction_data
    assert "interaction_data" in result
    assert len(result["interaction_data"]["blanks"]) == 1
    assert result["interaction_data"]["blanks"][0]["answer_type"] == "openEntry"
    assert "id" in result["interaction_data"]["blanks"][0]

    # Check scoring_data
    assert "scoring_data" in result
    # Working item body should have the answer filled in
    assert "Paris" in result["scoring_data"]["working_item_body"]
    assert len(result["scoring_data"]["value"]) == 2  # Main answer + variation

    # Check scoring algorithms
    scoring_values = result["scoring_data"]["value"]
    assert scoring_values[0]["scoring_data"]["value"] == "Paris"
    assert scoring_values[0]["scoring_algorithm"] == "TextContainsAnswer"
    assert scoring_values[1]["scoring_data"]["value"] == "paris"


def test_fill_in_blank_question_type_format_for_canvas_case_sensitive():
    """Test Canvas formatting with case-sensitive answers."""
    from src.question.types.fill_in_blank import (
        BlankData,
        FillInBlankData,
        FillInBlankQuestionType,
    )

    question_type = FillInBlankQuestionType()
    data = FillInBlankData(
        question_text="The capital of France is [blank_1].",
        blanks=[
            BlankData(
                position=1,
                correct_answer="Paris",
                case_sensitive=True,
            )
        ],
    )

    result = question_type.format_for_canvas(data)
    scoring_values = result["scoring_data"]["value"]
    assert scoring_values[0]["scoring_algorithm"] == "TextContainsAnswer"


def test_fill_in_blank_question_type_format_for_canvas_multiple_blanks():
    """Test Canvas formatting with multiple blanks."""
    from src.question.types.fill_in_blank import (
        BlankData,
        FillInBlankData,
        FillInBlankQuestionType,
    )

    question_type = FillInBlankQuestionType()
    data = FillInBlankData(
        question_text="The capital of _____ is _____.",
        blanks=[
            BlankData(position=1, correct_answer="France"),
            BlankData(position=2, correct_answer="Paris"),
        ],
    )

    result = question_type.format_for_canvas(data)
    assert result["points_possible"] == 2
    assert len(result["interaction_data"]["blanks"]) == 2
    assert len(result["scoring_data"]["value"]) == 2


def test_fill_in_blank_question_type_format_for_canvas_wrong_type():
    """Test Canvas formatting with wrong data type."""
    from src.question.types.fill_in_blank import FillInBlankQuestionType

    question_type = FillInBlankQuestionType()

    with pytest.raises(ValueError, match="Expected FillInBlankData"):
        question_type.format_for_canvas("wrong_type")


def test_fill_in_blank_registry_registration():
    """Test that fill-in-blank type is registered."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    assert registry.is_registered(QuestionType.FILL_IN_BLANK)


def test_fill_in_blank_registry_get_question_type():
    """Test getting fill-in-blank question type from registry."""
    from src.question.types import QuestionType, get_question_type_registry
    from src.question.types.fill_in_blank import FillInBlankQuestionType

    registry = get_question_type_registry()
    question_type = registry.get_question_type(QuestionType.FILL_IN_BLANK)
    assert isinstance(question_type, FillInBlankQuestionType)


def test_fill_in_blank_registry_available_types():
    """Test that available types includes fill-in-blank."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    available_types = registry.get_available_types()
    assert QuestionType.FILL_IN_BLANK in available_types
    assert QuestionType.MULTIPLE_CHOICE in available_types


def test_fill_in_blank_end_to_end_workflow():
    """Test complete workflow from data creation to Canvas export."""
    from src.question.types import QuestionType, get_question_type_registry
    from src.question.types.fill_in_blank import BlankData, FillInBlankData

    # Create question data
    data = FillInBlankData(
        question_text="The capital of France is _____ and it is located in _____.",
        blanks=[
            BlankData(
                position=1,
                correct_answer="Paris",
                answer_variations=["paris", "PARIS"],
                case_sensitive=False,
            ),
            BlankData(
                position=2,
                correct_answer="Europe",
                case_sensitive=False,
            ),
        ],
        explanation="Paris is the capital of France and is located in Europe.",
    )

    # Get question type from registry
    registry = get_question_type_registry()
    question_type = registry.get_question_type(QuestionType.FILL_IN_BLANK)

    # Test display formatting
    display_format = question_type.format_for_display(data)
    assert display_format["question_type"] == "fill_in_blank"
    assert len(display_format["blanks"]) == 2

    # Test Canvas formatting
    canvas_format = question_type.format_for_canvas(data)
    assert canvas_format["interaction_type_slug"] == "rich-fill-blank"
    assert canvas_format["points_possible"] == 2
    assert len(canvas_format["interaction_data"]["blanks"]) == 2
    # 2 blanks + 2 answer variations for first blank = 4 scoring entries
    assert len(canvas_format["scoring_data"]["value"]) == 4
    assert canvas_format["scoring_algorithm"] == "MultipleMethods"


def test_fill_in_blank_validation_round_trip():
    """Test that data can be validated and re-validated."""
    from src.question.types.fill_in_blank import FillInBlankQuestionType

    question_type = FillInBlankQuestionType()
    original_data = {
        "question_text": "The capital of France is _____.",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "Paris",
                "answer_variations": ["paris"],
                "case_sensitive": False,
            }
        ],
        "explanation": "Paris is the capital of France.",
    }

    # Validate data
    validated_data = question_type.validate_data(original_data)

    # Format for display
    display_data = question_type.format_for_display(validated_data)

    # Validate display data (should work)
    revalidated_data = question_type.validate_data(
        {
            "question_text": display_data["question_text"],
            "blanks": display_data["blanks"],
            "explanation": display_data["explanation"],
        }
    )

    assert revalidated_data.question_text == validated_data.question_text
    assert len(revalidated_data.blanks) == len(validated_data.blanks)
    assert revalidated_data.explanation == validated_data.explanation
