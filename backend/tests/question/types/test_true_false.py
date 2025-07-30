"""Tests for True/False question type implementation."""

import pytest


def test_true_false_data_creation_true():
    """Test creating valid true/false data with correct_answer=True."""
    from src.question.types.true_false import TrueFalseData

    data = TrueFalseData(
        question_text="Python is a programming language.",
        correct_answer=True,
        explanation="Python is indeed a high-level programming language.",
    )
    assert data.question_text == "Python is a programming language."
    assert data.correct_answer is True
    assert data.explanation == "Python is indeed a high-level programming language."


def test_true_false_data_creation_false():
    """Test creating valid true/false data with correct_answer=False."""
    from src.question.types.true_false import TrueFalseData

    data = TrueFalseData(
        question_text="Python was invented in 1995.",
        correct_answer=False,
        explanation="Python was actually first released in 1991.",
    )
    assert data.question_text == "Python was invented in 1995."
    assert data.correct_answer is False
    assert data.explanation == "Python was actually first released in 1991."


def test_true_false_data_creation_without_explanation():
    """Test creating true/false data without explanation."""
    from src.question.types.true_false import TrueFalseData

    data = TrueFalseData(question_text="The Earth is round.", correct_answer=True)
    assert data.question_text == "The Earth is round."
    assert data.correct_answer is True
    assert data.explanation is None


def test_true_false_data_empty_question_text_validation():
    """Test that empty question text fails validation."""
    from pydantic import ValidationError

    from src.question.types.true_false import TrueFalseData

    with pytest.raises(ValidationError) as exc_info:
        TrueFalseData(question_text="", correct_answer=True)
    assert "String should have at least 1 character" in str(exc_info.value)


def test_true_false_data_question_text_too_long_validation():
    """Test that question text over 2000 characters fails validation."""
    from pydantic import ValidationError

    from src.question.types.true_false import TrueFalseData

    long_text = "a" * 2001
    with pytest.raises(ValidationError) as exc_info:
        TrueFalseData(question_text=long_text, correct_answer=True)
    assert "String should have at most 2000 characters" in str(exc_info.value)


def test_true_false_data_explanation_too_long_validation():
    """Test that explanation over 1000 characters fails validation."""
    from pydantic import ValidationError

    from src.question.types.true_false import TrueFalseData

    long_explanation = "a" * 1001
    with pytest.raises(ValidationError) as exc_info:
        TrueFalseData(
            question_text="Test question",
            correct_answer=True,
            explanation=long_explanation,
        )
    assert "String should have at most 1000 characters" in str(exc_info.value)


def test_true_false_data_missing_correct_answer_validation():
    """Test that missing correct_answer fails validation."""
    from pydantic import ValidationError

    from src.question.types.true_false import TrueFalseData

    with pytest.raises(ValidationError):
        TrueFalseData(question_text="Test question")


def test_true_false_data_invalid_correct_answer_type_validation():
    """Test that non-boolean correct_answer fails validation."""
    from pydantic import ValidationError

    from src.question.types.true_false import TrueFalseData

    # Test with string that can't be coerced to boolean
    with pytest.raises(ValidationError):
        TrueFalseData(question_text="Test question", correct_answer="invalid")

    # Test with integer (except 0 and 1 which might be coerced)
    with pytest.raises(ValidationError):
        TrueFalseData(question_text="Test question", correct_answer=2)


def test_true_false_data_extra_fields_forbidden():
    """Test that extra fields are forbidden."""
    from pydantic import ValidationError

    from src.question.types.true_false import TrueFalseData

    with pytest.raises(ValidationError):
        TrueFalseData(
            question_text="Test question",
            correct_answer=True,
            extra_field="not allowed",
        )


def test_true_false_question_type_properties():
    """Test TrueFalseQuestionType properties."""
    from src.question.types import QuestionType
    from src.question.types.true_false import TrueFalseData, TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    assert question_type.question_type == QuestionType.TRUE_FALSE
    assert question_type.data_model == TrueFalseData


def test_true_false_question_type_validate_data_true():
    """Test successful data validation with True answer."""
    from src.question.types.true_false import TrueFalseData, TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    data = {
        "question_text": "Python is an interpreted language.",
        "correct_answer": True,
        "explanation": "Python code is executed line by line by an interpreter.",
    }

    result = question_type.validate_data(data)
    assert isinstance(result, TrueFalseData)
    assert result.correct_answer is True
    assert result.question_text == "Python is an interpreted language."


def test_true_false_question_type_validate_data_false():
    """Test successful data validation with False answer."""
    from src.question.types.true_false import TrueFalseData, TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    data = {
        "question_text": "Python was invented in 2000.",
        "correct_answer": False,
        "explanation": "Python was first released in 1991, not 2000.",
    }

    result = question_type.validate_data(data)
    assert isinstance(result, TrueFalseData)
    assert result.correct_answer is False
    assert result.question_text == "Python was invented in 2000."


def test_true_false_question_type_validate_data_missing_fields():
    """Test validation with missing required fields."""
    from pydantic import ValidationError

    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()

    with pytest.raises(ValidationError):
        question_type.validate_data({"question_text": "Test"})

    with pytest.raises(ValidationError):
        question_type.validate_data({"correct_answer": True})


def test_true_false_question_type_validate_data_invalid_types():
    """Test validation with invalid field types."""
    from pydantic import ValidationError

    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    invalid_data = {
        "question_text": 123,  # Should be string
        "correct_answer": True,
    }
    with pytest.raises(ValidationError):
        question_type.validate_data(invalid_data)


def test_true_false_question_type_format_for_display_true():
    """Test formatting for display with True answer."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    data = {
        "question_text": "Python is an interpreted language.",
        "correct_answer": True,
        "explanation": "Python code is executed line by line by an interpreter.",
    }
    validated_data = question_type.validate_data(data)
    result = question_type.format_for_display(validated_data)

    expected = {
        "question_text": "Python is an interpreted language.",
        "correct_answer": True,
        "explanation": "Python code is executed line by line by an interpreter.",
        "question_type": "true_false",
    }
    assert result == expected


def test_true_false_question_type_format_for_display_false():
    """Test formatting for display with False answer."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    data = {
        "question_text": "Python was invented in 2000.",
        "correct_answer": False,
        "explanation": "Python was first released in 1991, not 2000.",
    }
    validated_data = question_type.validate_data(data)
    result = question_type.format_for_display(validated_data)

    expected = {
        "question_text": "Python was invented in 2000.",
        "correct_answer": False,
        "explanation": "Python was first released in 1991, not 2000.",
        "question_type": "true_false",
    }
    assert result == expected


def test_true_false_question_type_format_for_display_no_explanation():
    """Test formatting for display without explanation."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    data = {"question_text": "The sky is blue.", "correct_answer": True}
    validated_data = question_type.validate_data(data)
    result = question_type.format_for_display(validated_data)

    assert result["explanation"] is None


def test_true_false_question_type_format_for_display_wrong_type():
    """Test format_for_display with wrong data type."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()

    with pytest.raises(ValueError, match="Expected TrueFalseData"):
        question_type.format_for_display("wrong_type")


def test_true_false_question_type_format_for_canvas_true():
    """Test Canvas export formatting with True answer."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    data = {
        "question_text": "Python is an interpreted language.",
        "correct_answer": True,
        "explanation": "Python code is executed line by line by an interpreter.",
    }
    validated_data = question_type.validate_data(data)
    result = question_type.format_for_canvas(validated_data)

    # Validate structure
    assert "title" in result
    assert result["item_body"] == "<p>Python is an interpreted language.</p>"
    assert result["calculator_type"] == "none"
    assert result["interaction_type_slug"] == "true-false"
    assert result["scoring_algorithm"] == "Equivalence"
    assert result["points_possible"] == 1

    # Validate interaction_data
    assert result["interaction_data"] == {
        "true_choice": "True",
        "false_choice": "False",
    }

    # Validate scoring_data
    assert result["scoring_data"] == {"value": True}


def test_true_false_question_type_format_for_canvas_false():
    """Test Canvas export formatting with False answer."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    data = {
        "question_text": "Python was invented in 2000.",
        "correct_answer": False,
        "explanation": "Python was first released in 1991, not 2000.",
    }
    validated_data = question_type.validate_data(data)
    result = question_type.format_for_canvas(validated_data)

    # Validate scoring_data for false answer
    assert result["scoring_data"] == {"value": False}


def test_true_false_question_type_format_for_canvas_html_wrapping():
    """Test that question text gets wrapped in HTML tags."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()

    # Test text without HTML tags
    data_no_html = {"question_text": "Plain text question", "correct_answer": True}
    validated_data = question_type.validate_data(data_no_html)
    result = question_type.format_for_canvas(validated_data)
    assert result["item_body"] == "<p>Plain text question</p>"

    # Test text already with HTML tags
    data_with_html = {
        "question_text": "<p>Already wrapped question</p>",
        "correct_answer": True,
    }
    validated_data = question_type.validate_data(data_with_html)
    result = question_type.format_for_canvas(validated_data)
    assert result["item_body"] == "<p>Already wrapped question</p>"


def test_true_false_question_type_format_for_canvas_wrong_type():
    """Test format_for_canvas with wrong data type."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()

    with pytest.raises(ValueError, match="Expected TrueFalseData"):
        question_type.format_for_canvas("wrong_type")


def test_true_false_question_type_format_for_export():
    """Test generic export formatting."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    data = {
        "question_text": "Python is an interpreted language.",
        "correct_answer": True,
        "explanation": "Python code is executed line by line by an interpreter.",
    }
    validated_data = question_type.validate_data(data)
    result = question_type.format_for_export(validated_data)

    expected = {
        "question_text": "Python is an interpreted language.",
        "correct_answer": True,
        "explanation": "Python code is executed line by line by an interpreter.",
        "question_type": "true_false",
    }
    assert result == expected


def test_true_false_question_type_format_for_export_wrong_type():
    """Test format_for_export with wrong data type."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()

    with pytest.raises(ValueError, match="Expected TrueFalseData"):
        question_type.format_for_export("wrong_type")


def test_true_false_registry_registration():
    """Test that True/False type is registered in registry."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    assert registry.is_registered(QuestionType.TRUE_FALSE)


def test_true_false_registry_get_question_type():
    """Test retrieving True/False type from registry."""
    from src.question.types import QuestionType, get_question_type_registry
    from src.question.types.true_false import TrueFalseQuestionType

    registry = get_question_type_registry()
    question_type = registry.get_question_type(QuestionType.TRUE_FALSE)
    assert isinstance(question_type, TrueFalseQuestionType)


def test_true_false_registry_available_types():
    """Test that available types includes True/False."""
    from src.question.types import QuestionType, get_question_type_registry

    registry = get_question_type_registry()
    available_types = registry.get_available_types()
    assert QuestionType.TRUE_FALSE in available_types
    assert QuestionType.MULTIPLE_CHOICE in available_types
    assert QuestionType.FILL_IN_BLANK in available_types


def test_true_false_end_to_end_workflow_true():
    """Test complete workflow from raw data to Canvas export (True answer)."""
    from src.question.types import QuestionType, get_question_type_registry

    # Raw AI response data
    raw_data = {
        "question_text": "Machine learning is a subset of artificial intelligence.",
        "correct_answer": True,
        "explanation": "Machine learning is indeed a subset of AI that enables computers to learn without explicit programming.",
    }

    # Get question type and validate data
    registry = get_question_type_registry()
    true_false_type = registry.get_question_type(QuestionType.TRUE_FALSE)
    validated_data = true_false_type.validate_data(raw_data)

    # Format for different outputs
    display_format = true_false_type.format_for_display(validated_data)
    canvas_format = true_false_type.format_for_canvas(validated_data)
    export_format = true_false_type.format_for_export(validated_data)

    # Validate all formats work
    assert display_format["question_type"] == "true_false"
    assert canvas_format["interaction_type_slug"] == "true-false"
    assert export_format["question_type"] == "true_false"

    # Validate data consistency
    assert display_format["correct_answer"] is True
    assert canvas_format["scoring_data"]["value"] is True
    assert export_format["correct_answer"] is True


def test_true_false_end_to_end_workflow_false():
    """Test complete workflow from raw data to Canvas export (False answer)."""
    from src.question.types import QuestionType, get_question_type_registry

    # Raw AI response data
    raw_data = {
        "question_text": "HTML is a programming language.",
        "correct_answer": False,
        "explanation": "HTML is a markup language, not a programming language.",
    }

    # Get question type and validate data
    registry = get_question_type_registry()
    true_false_type = registry.get_question_type(QuestionType.TRUE_FALSE)
    validated_data = true_false_type.validate_data(raw_data)

    # Format for different outputs
    display_format = true_false_type.format_for_display(validated_data)
    canvas_format = true_false_type.format_for_canvas(validated_data)
    export_format = true_false_type.format_for_export(validated_data)

    # Validate data consistency
    assert display_format["correct_answer"] is False
    assert canvas_format["scoring_data"]["value"] is False
    assert export_format["correct_answer"] is False


def test_true_false_validation_round_trip():
    """Test that data survives round-trip through validation."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    original_data = {
        "question_text": "JavaScript and Java are the same language.",
        "correct_answer": False,
        "explanation": "JavaScript and Java are completely different programming languages.",
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


def test_true_false_canvas_export_consistency():
    """Test that Canvas export maintains data integrity."""
    from src.question.types.true_false import TrueFalseQuestionType

    test_cases = [
        {
            "question_text": "The Internet was invented in the 1990s.",
            "correct_answer": False,
            "explanation": "The Internet's precursor, ARPANET, was developed in the 1960s.",
        },
        {
            "question_text": "Python supports object-oriented programming.",
            "correct_answer": True,
            "explanation": "Python fully supports object-oriented programming paradigms.",
        },
    ]

    question_type = TrueFalseQuestionType()

    for test_case in test_cases:
        validated_data = question_type.validate_data(test_case)
        canvas_format = question_type.format_for_canvas(validated_data)

        # Validate Canvas format structure
        assert isinstance(canvas_format["scoring_data"]["value"], bool)
        assert canvas_format["scoring_data"]["value"] == test_case["correct_answer"]
        assert canvas_format["interaction_data"]["true_choice"] == "True"
        assert canvas_format["interaction_data"]["false_choice"] == "False"
        assert canvas_format["interaction_type_slug"] == "true-false"
        assert canvas_format["points_possible"] == 1


def test_true_false_edge_cases():
    """Test edge cases and boundary conditions."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()

    # Minimum length question text
    minimal_data = {"question_text": "X", "correct_answer": True}
    validated = question_type.validate_data(minimal_data)
    assert validated.question_text == "X"

    # Maximum length question text (just under limit)
    max_length_text = "a" * 2000
    max_data = {"question_text": max_length_text, "correct_answer": False}
    validated = question_type.validate_data(max_data)
    assert len(validated.question_text) == 2000

    # Maximum length explanation (just under limit)
    max_explanation = "b" * 1000
    max_exp_data = {
        "question_text": "Test question",
        "correct_answer": True,
        "explanation": max_explanation,
    }
    validated = question_type.validate_data(max_exp_data)
    assert len(validated.explanation) == 1000
