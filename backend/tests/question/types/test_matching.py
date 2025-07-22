"""Tests for matching question type implementation."""

import pytest


def test_matching_pair_creation():
    """Test creating MatchingPair with valid data."""
    from src.question.types.matching import MatchingPair

    pair = MatchingPair(question="France", answer="Paris")
    assert pair.question == "France"
    assert pair.answer == "Paris"


def test_matching_pair_empty_question_validation():
    """Test that empty question fails validation."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingPair

    with pytest.raises(ValidationError) as exc_info:
        MatchingPair(question="", answer="Paris")
    assert "String should have at least 1 character" in str(exc_info.value)


def test_matching_pair_empty_answer_validation():
    """Test that empty answer fails validation."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingPair

    with pytest.raises(ValidationError) as exc_info:
        MatchingPair(question="France", answer="")
    assert "String should have at least 1 character" in str(exc_info.value)


def test_matching_pair_whitespace_only_validation():
    """Test that whitespace-only strings fail validation."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingPair

    with pytest.raises(ValidationError) as exc_info:
        MatchingPair(question="   ", answer="Paris")
    assert "Field cannot be empty or whitespace-only" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        MatchingPair(question="France", answer="   ")
    assert "Field cannot be empty or whitespace-only" in str(exc_info.value)


def test_matching_data_creation():
    """Test creating MatchingData with valid data."""
    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    data = MatchingData(
        question_text="Match countries to capitals",
        pairs=pairs,
        explanation="European countries and their capitals.",
    )
    assert data.question_text == "Match countries to capitals"
    assert len(data.pairs) == 3
    assert data.explanation == "European countries and their capitals."
    assert data.distractors is None


def test_matching_data_with_distractors():
    """Test creating MatchingData with distractors."""
    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    distractors = ["Madrid", "London"]
    data = MatchingData(
        question_text="Match countries to capitals",
        pairs=pairs,
        distractors=distractors,
    )
    assert data.distractors == ["Madrid", "London"]


def test_matching_data_minimum_pairs_validation():
    """Test that at least 3 pairs are required."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        MatchingData(question_text="Test", pairs=pairs)
    assert "List should have at least 3 items" in str(exc_info.value)


def test_matching_data_maximum_pairs_validation():
    """Test that maximum 10 pairs are allowed."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question=f"Country{i}", answer=f"Capital{i}") for i in range(11)
    ]
    with pytest.raises(ValidationError) as exc_info:
        MatchingData(question_text="Test", pairs=pairs)
    assert "List should have at most 10 items" in str(exc_info.value)


def test_matching_data_duplicate_questions_validation():
    """Test that duplicate questions are not allowed."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="France", answer="Lyon"),  # Duplicate question
        MatchingPair(question="Germany", answer="Berlin"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        MatchingData(question_text="Test", pairs=pairs)
    assert "Duplicate questions are not allowed" in str(exc_info.value)


def test_matching_data_duplicate_answers_validation():
    """Test that duplicate answers are not allowed."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Paris"),  # Duplicate answer
        MatchingPair(question="Italy", answer="Rome"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        MatchingData(question_text="Test", pairs=pairs)
    assert "Duplicate answers are not allowed" in str(exc_info.value)


def test_matching_data_case_insensitive_duplicate_detection():
    """Test that duplicate detection is case-insensitive."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="FRANCE", answer="Berlin"),  # Case-insensitive duplicate
        MatchingPair(question="Germany", answer="Rome"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        MatchingData(question_text="Test", pairs=pairs)
    assert "Duplicate questions are not allowed" in str(exc_info.value)


def test_matching_data_maximum_distractors_validation():
    """Test that maximum 5 distractors are allowed."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    distractors = ["Madrid", "London", "Cairo", "Tokyo", "Moscow", "Sydney"]  # 6
    with pytest.raises(ValidationError) as exc_info:
        MatchingData(question_text="Test", pairs=pairs, distractors=distractors)
    assert "List should have at most 5 items" in str(exc_info.value)


def test_matching_data_empty_distractors_filtered():
    """Test that empty distractors are filtered out."""
    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    distractors = ["Madrid", "", "  ", "London", ""]
    data = MatchingData(question_text="Test", pairs=pairs, distractors=distractors)
    assert data.distractors == ["Madrid", "London"]


def test_matching_data_duplicate_distractors_removed():
    """Test that duplicate distractors are removed."""
    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    distractors = ["Madrid", "London", "madrid", "LONDON"]  # Case-insensitive dupes
    data = MatchingData(question_text="Test", pairs=pairs, distractors=distractors)
    assert data.distractors == ["Madrid", "London"]


def test_matching_data_distractor_matches_answer_validation():
    """Test that distractors cannot match correct answers."""
    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    distractors = ["Madrid", "Paris"]  # "Paris" matches a correct answer
    data = MatchingData(question_text="Test", pairs=pairs, distractors=distractors)

    with pytest.raises(ValueError) as exc_info:
        data.validate_no_distractor_matches()
    assert "Distractor 'Paris' matches a correct answer" in str(exc_info.value)


def test_matching_data_get_all_answers():
    """Test getting all answers including distractors."""
    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    distractors = ["Madrid", "London"]
    data = MatchingData(question_text="Test", pairs=pairs, distractors=distractors)

    all_answers = data.get_all_answers()
    expected = ["Paris", "Berlin", "Rome", "Madrid", "London"]
    assert all_answers == expected


def test_matching_data_get_all_answers_no_distractors():
    """Test getting all answers when no distractors."""
    from src.question.types.matching import MatchingData, MatchingPair

    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    data = MatchingData(question_text="Test", pairs=pairs)

    all_answers = data.get_all_answers()
    expected = ["Paris", "Berlin", "Rome"]
    assert all_answers == expected


def test_matching_question_type_properties():
    """Test MatchingQuestionType properties."""
    from src.question.types import QuestionType
    from src.question.types.matching import MatchingData, MatchingQuestionType

    question_type = MatchingQuestionType()
    assert question_type.question_type == QuestionType.MATCHING
    assert question_type.data_model == MatchingData


def test_matching_question_type_validate_data():
    """Test data validation in MatchingQuestionType."""
    from src.question.types.matching import MatchingData, MatchingQuestionType

    question_type = MatchingQuestionType()
    data = {
        "question_text": "Match countries to their capitals",
        "pairs": [
            {"question": "France", "answer": "Paris"},
            {"question": "Germany", "answer": "Berlin"},
            {"question": "Italy", "answer": "Rome"},
        ],
        "distractors": ["Madrid", "London"],
        "explanation": "These are European countries and capitals.",
    }

    result = question_type.validate_data(data)
    assert isinstance(result, MatchingData)
    assert result.question_text == "Match countries to their capitals"
    assert len(result.pairs) == 3
    assert result.distractors == ["Madrid", "London"]


def test_matching_question_type_validate_data_with_distractor_conflict():
    """Test validation fails when distractor matches answer."""
    from src.question.types.matching import MatchingQuestionType

    question_type = MatchingQuestionType()
    data = {
        "question_text": "Match countries to their capitals",
        "pairs": [
            {"question": "France", "answer": "Paris"},
            {"question": "Germany", "answer": "Berlin"},
            {"question": "Italy", "answer": "Rome"},
        ],
        "distractors": ["Madrid", "Paris"],  # Paris is a correct answer
    }

    with pytest.raises(ValueError) as exc_info:
        question_type.validate_data(data)
    assert "Distractor 'Paris' matches a correct answer" in str(exc_info.value)


def test_matching_question_type_validate_invalid_data():
    """Test validation of invalid data."""
    from pydantic import ValidationError

    from src.question.types.matching import MatchingQuestionType

    question_type = MatchingQuestionType()
    data = {"invalid": "data"}

    with pytest.raises(ValidationError):
        question_type.validate_data(data)


def test_matching_question_type_format_for_display():
    """Test formatting for display."""
    from src.question.types.matching import (
        MatchingData,
        MatchingPair,
        MatchingQuestionType,
    )

    question_type = MatchingQuestionType()
    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    data = MatchingData(
        question_text="Match countries to their capitals",
        pairs=pairs,
        distractors=["Madrid", "London"],
        explanation="These are European countries and capitals.",
    )

    result = question_type.format_for_display(data)
    expected = {
        "question_text": "Match countries to their capitals",
        "pairs": [
            {"question": "France", "answer": "Paris"},
            {"question": "Germany", "answer": "Berlin"},
            {"question": "Italy", "answer": "Rome"},
        ],
        "distractors": ["Madrid", "London"],
        "explanation": "These are European countries and capitals.",
        "question_type": "matching",
    }
    assert result == expected


def test_matching_question_type_format_for_display_no_distractors():
    """Test formatting for display without distractors."""
    from src.question.types.matching import (
        MatchingData,
        MatchingPair,
        MatchingQuestionType,
    )

    question_type = MatchingQuestionType()
    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    data = MatchingData(question_text="Match countries to capitals", pairs=pairs)

    result = question_type.format_for_display(data)
    assert "distractors" not in result


def test_matching_question_type_format_for_display_wrong_type():
    """Test formatting for display with wrong data type."""
    from src.question.types.matching import MatchingQuestionType

    question_type = MatchingQuestionType()

    with pytest.raises(ValueError, match="Expected MatchingData"):
        question_type.format_for_display("wrong_type")


def test_matching_question_type_format_for_canvas():
    """Test Canvas export formatting."""
    from src.question.types.matching import (
        MatchingData,
        MatchingPair,
        MatchingQuestionType,
    )

    question_type = MatchingQuestionType()
    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    data = MatchingData(
        question_text="Match countries to their capitals",
        pairs=pairs,
        distractors=["Madrid", "London"],
    )

    result = question_type.format_for_canvas(data)

    # Validate structure
    assert "title" in result
    assert result["item_body"] == "<p>Match countries to their capitals</p>"
    assert result["calculator_type"] == "none"
    assert result["interaction_type_slug"] == "matching"
    assert result["scoring_algorithm"] == "PartialDeep"
    assert result["points_possible"] == 3

    # Validate interaction_data
    interaction_data = result["interaction_data"]
    assert "answers" in interaction_data
    assert "questions" in interaction_data
    assert len(interaction_data["questions"]) == 3
    assert set(interaction_data["answers"]) == {
        "Paris",
        "Berlin",
        "Rome",
        "Madrid",
        "London",
    }

    # Validate scoring_data
    scoring_data = result["scoring_data"]
    assert "value" in scoring_data
    assert "edit_data" in scoring_data
    assert len(scoring_data["edit_data"]["matches"]) == 3
    assert scoring_data["edit_data"]["distractors"] == ["Madrid", "London"]

    # Validate shuffle rules
    properties = result["properties"]
    assert properties["shuffle_rules"]["questions"]["shuffled"] is False
    assert properties["shuffle_rules"]["answers"]["shuffled"] is True


def test_matching_question_type_format_for_canvas_no_distractors():
    """Test Canvas export formatting without distractors."""
    from src.question.types.matching import (
        MatchingData,
        MatchingPair,
        MatchingQuestionType,
    )

    question_type = MatchingQuestionType()
    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    data = MatchingData(question_text="Match countries to capitals", pairs=pairs)

    result = question_type.format_for_canvas(data)
    assert len(result["interaction_data"]["answers"]) == 3  # Only correct answers
    assert result["scoring_data"]["edit_data"]["distractors"] == []


def test_matching_question_type_format_for_canvas_wrong_type():
    """Test Canvas formatting with wrong data type."""
    from src.question.types.matching import MatchingQuestionType

    question_type = MatchingQuestionType()

    with pytest.raises(ValueError, match="Expected MatchingData"):
        question_type.format_for_canvas("wrong_type")


def test_matching_question_type_format_for_export():
    """Test generic export formatting."""
    from src.question.types.matching import (
        MatchingData,
        MatchingPair,
        MatchingQuestionType,
    )

    question_type = MatchingQuestionType()
    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    data = MatchingData(
        question_text="Match countries to their capitals",
        pairs=pairs,
        distractors=["Madrid", "London"],
        explanation="These are European countries and capitals.",
    )

    result = question_type.format_for_export(data)
    expected = {
        "question_text": "Match countries to their capitals",
        "pairs": [
            {"question": "France", "answer": "Paris"},
            {"question": "Germany", "answer": "Berlin"},
            {"question": "Italy", "answer": "Rome"},
        ],
        "distractors": ["Madrid", "London"],
        "explanation": "These are European countries and capitals.",
        "question_type": "matching",
    }
    assert result == expected


def test_matching_question_type_format_for_export_no_distractors():
    """Test export formatting without distractors."""
    from src.question.types.matching import (
        MatchingData,
        MatchingPair,
        MatchingQuestionType,
    )

    question_type = MatchingQuestionType()
    pairs = [
        MatchingPair(question="France", answer="Paris"),
        MatchingPair(question="Germany", answer="Berlin"),
        MatchingPair(question="Italy", answer="Rome"),
    ]
    data = MatchingData(question_text="Match countries to capitals", pairs=pairs)

    result = question_type.format_for_export(data)
    assert "distractors" not in result


def test_matching_question_type_format_for_export_wrong_type():
    """Test export formatting with wrong data type."""
    from src.question.types.matching import MatchingQuestionType

    question_type = MatchingQuestionType()

    with pytest.raises(ValueError, match="Expected MatchingData"):
        question_type.format_for_export("wrong_type")


def test_matching_registry_registration():
    """Test that matching type is registered."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    assert registry.is_registered(QuestionType.MATCHING)


def test_matching_registry_get_question_type():
    """Test getting matching question type from registry."""
    from src.question.types import QuestionType, get_question_type_registry
    from src.question.types.matching import MatchingQuestionType

    registry = get_question_type_registry()
    question_type = registry.get_question_type(QuestionType.MATCHING)
    assert isinstance(question_type, MatchingQuestionType)


def test_matching_registry_available_types():
    """Test that available types includes matching."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    available_types = registry.get_available_types()
    assert QuestionType.MATCHING in available_types
    assert QuestionType.MULTIPLE_CHOICE in available_types
    assert QuestionType.FILL_IN_BLANK in available_types


def test_matching_end_to_end_workflow():
    """Test complete workflow from raw data to Canvas export."""
    from src.question.types import QuestionType, get_question_type_registry

    # Raw AI response data
    raw_data = {
        "question_text": "Match programming languages to their creators",
        "pairs": [
            {"question": "Python", "answer": "Guido van Rossum"},
            {"question": "JavaScript", "answer": "Brendan Eich"},
            {"question": "Java", "answer": "James Gosling"},
            {"question": "C++", "answer": "Bjarne Stroustrup"},
        ],
        "distractors": ["Linus Torvalds", "Tim Berners-Lee"],
        "explanation": "These are the original creators of popular programming languages.",
    }

    # Get question type and validate data
    registry = get_question_type_registry()
    matching_type = registry.get_question_type(QuestionType.MATCHING)
    validated_data = matching_type.validate_data(raw_data)

    # Format for different outputs
    display_format = matching_type.format_for_display(validated_data)
    canvas_format = matching_type.format_for_canvas(validated_data)
    export_format = matching_type.format_for_export(validated_data)

    # Validate all formats work
    assert display_format["question_type"] == "matching"
    assert canvas_format["interaction_type_slug"] == "matching"
    assert export_format["question_type"] == "matching"

    # Validate data consistency
    assert len(display_format["pairs"]) == 4
    assert len(canvas_format["scoring_data"]["edit_data"]["matches"]) == 4
    assert len(export_format["pairs"]) == 4


def test_matching_validation_round_trip():
    """Test that data can be validated and re-validated."""
    from src.question.types.matching import MatchingQuestionType

    question_type = MatchingQuestionType()
    original_data = {
        "question_text": "Match elements to symbols",
        "pairs": [
            {"question": "Hydrogen", "answer": "H"},
            {"question": "Oxygen", "answer": "O"},
            {"question": "Carbon", "answer": "C"},
        ],
        "explanation": "Chemical element symbols.",
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


def test_matching_complex_validation_scenario():
    """Test complex validation with edge cases."""
    from src.question.types.matching import MatchingQuestionType

    # Test with maximum pairs, distractors, and edge case content
    pairs_data = [
        {"question": f"Question {i}", "answer": f"Answer {i}"}
        for i in range(1, 11)  # 10 pairs (maximum)
    ]

    complex_data = {
        "question_text": "Complex matching question with special characters: áéíóú & symbols!",
        "pairs": pairs_data,
        "distractors": ["Distractor 1", "Distractor 2", "Distractor 3"],  # 3
        "explanation": "This tests maximum complexity with special characters and symbols.",
    }

    matching_type = MatchingQuestionType()
    validated_data = matching_type.validate_data(complex_data)

    # Should validate successfully
    assert len(validated_data.pairs) == 10
    assert validated_data.distractors is not None
    assert len(validated_data.distractors) == 3

    # Canvas export should work
    canvas_format = matching_type.format_for_canvas(validated_data)
    assert canvas_format["points_possible"] == 10
    assert len(canvas_format["interaction_data"]["answers"]) == 13  # 10 + 3 distractors
