"""Tests for quiz schemas validation, particularly difficulty feature."""

import pytest
from pydantic import ValidationError

from src.question.types import QuestionDifficulty, QuestionType
from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate


def test_question_batch_requires_difficulty():
    """Test that QuestionBatch requires explicit difficulty."""
    from pydantic import ValidationError

    # Should fail without difficulty
    with pytest.raises(ValidationError):
        QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10)


def test_question_batch_explicit_difficulty():
    """Test QuestionBatch with explicit difficulty values."""
    for difficulty in [
        QuestionDifficulty.EASY,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.HARD,
    ]:
        batch = QuestionBatch(
            question_type=QuestionType.MULTIPLE_CHOICE, count=5, difficulty=difficulty
        )
        assert batch.difficulty == difficulty


def test_question_batch_valid_count_range():
    """Test QuestionBatch accepts valid count range (1-20)."""
    # Test minimum
    batch_min = QuestionBatch(
        question_type=QuestionType.MULTIPLE_CHOICE,
        count=1,
        difficulty=QuestionDifficulty.EASY,
    )
    assert batch_min.count == 1

    # Test maximum
    batch_max = QuestionBatch(
        question_type=QuestionType.MULTIPLE_CHOICE,
        count=20,
        difficulty=QuestionDifficulty.HARD,
    )
    assert batch_max.count == 20


def test_question_batch_invalid_count_rejected():
    """Test QuestionBatch rejects invalid count values."""
    # Test count below minimum
    with pytest.raises(ValidationError):
        QuestionBatch(
            question_type=QuestionType.MULTIPLE_CHOICE,
            count=0,
            difficulty=QuestionDifficulty.MEDIUM,
        )

    # Test count above maximum
    with pytest.raises(ValidationError):
        QuestionBatch(
            question_type=QuestionType.MULTIPLE_CHOICE,
            count=21,
            difficulty=QuestionDifficulty.MEDIUM,
        )


@pytest.mark.parametrize(
    "question_type",
    [
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.FILL_IN_BLANK,
        QuestionType.MATCHING,
        QuestionType.CATEGORIZATION,
        QuestionType.TRUE_FALSE,
    ],
)
def test_question_batch_all_question_types_with_difficulty(question_type):
    """Test all question types work with difficulty."""
    batch = QuestionBatch(
        question_type=question_type, count=5, difficulty=QuestionDifficulty.HARD
    )
    assert batch.question_type == question_type
    assert batch.difficulty == QuestionDifficulty.HARD


def test_quiz_create_same_type_different_difficulties_allowed():
    """Test that same question types with different difficulties are allowed."""
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Test Course",
        title="Difficulty Test Quiz",
        selected_modules={
            "module_1": ModuleSelection(
                name="Test Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=5,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                ],
            )
        },
    )

    # Should not raise ValidationError
    assert len(quiz_data.selected_modules["module_1"].question_batches) == 2

    batches = quiz_data.selected_modules["module_1"].question_batches
    assert batches[0].question_type == QuestionType.MULTIPLE_CHOICE
    assert batches[0].difficulty == QuestionDifficulty.EASY
    assert batches[1].question_type == QuestionType.MULTIPLE_CHOICE
    assert batches[1].difficulty == QuestionDifficulty.HARD


def test_quiz_create_duplicate_type_difficulty_combinations_blocked():
    """Test that duplicate (question_type, difficulty) combinations are blocked."""
    with pytest.raises(ValidationError) as exc_info:
        QuizCreate(
            canvas_course_id=123,
            canvas_course_name="Test Course",
            title="Duplicate Test Quiz",
            selected_modules={
                "module_1": ModuleSelection(
                    name="Test Module",
                    question_batches=[
                        QuestionBatch(
                            question_type=QuestionType.MULTIPLE_CHOICE,
                            count=5,
                            difficulty=QuestionDifficulty.EASY,
                        ),
                        QuestionBatch(
                            question_type=QuestionType.MULTIPLE_CHOICE,
                            count=10,
                            difficulty=QuestionDifficulty.EASY,  # Same type + difficulty
                        ),
                    ],
                )
            },
        )

    error_message = str(exc_info.value)
    assert "duplicate question type and difficulty combinations" in error_message
    assert "module_1" in error_message


def test_quiz_create_multiple_modules_with_difficulties():
    """Test quiz creation with multiple modules each having difficulty batches."""
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Multi-Module Course",
        title="Multi-Module Difficulty Quiz",
        selected_modules={
            "module_1": ModuleSelection(
                name="Introduction Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=5,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.FILL_IN_BLANK,
                        count=3,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                ],
            ),
            "module_2": ModuleSelection(
                name="Advanced Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=8,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MATCHING,
                        count=4,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                ],
            ),
        },
    )

    # Verify structure
    assert len(quiz_data.selected_modules) == 2

    # Check module 1
    mod1_batches = quiz_data.selected_modules["module_1"].question_batches
    assert len(mod1_batches) == 2
    assert mod1_batches[0].difficulty == QuestionDifficulty.EASY
    assert mod1_batches[1].difficulty == QuestionDifficulty.MEDIUM

    # Check module 2
    mod2_batches = quiz_data.selected_modules["module_2"].question_batches
    assert len(mod2_batches) == 2
    assert mod2_batches[0].difficulty == QuestionDifficulty.HARD
    assert mod2_batches[1].difficulty == QuestionDifficulty.HARD


def test_quiz_create_max_batches_per_module_with_difficulty():
    """Test maximum batches per module (4) with different difficulties."""
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Max Batches Course",
        title="Max Batches Quiz",
        selected_modules={
            "module_1": ModuleSelection(
                name="Full Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=5,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=5,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=5,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.FILL_IN_BLANK,
                        count=3,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                ],
            )
        },
    )

    # Should not raise error - 4 batches is maximum allowed
    assert len(quiz_data.selected_modules["module_1"].question_batches) == 4


def test_quiz_create_exceeds_max_batches_per_module():
    """Test that exceeding 4 batches per module is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        QuizCreate(
            canvas_course_id=123,
            canvas_course_name="Too Many Batches Course",
            title="Too Many Batches Quiz",
            selected_modules={
                "module_1": ModuleSelection(
                    name="Overfull Module",
                    question_batches=[
                        QuestionBatch(
                            question_type=QuestionType.MULTIPLE_CHOICE,
                            count=5,
                            difficulty=QuestionDifficulty.EASY,
                        ),
                        QuestionBatch(
                            question_type=QuestionType.MULTIPLE_CHOICE,
                            count=5,
                            difficulty=QuestionDifficulty.MEDIUM,
                        ),
                        QuestionBatch(
                            question_type=QuestionType.MULTIPLE_CHOICE,
                            count=5,
                            difficulty=QuestionDifficulty.HARD,
                        ),
                        QuestionBatch(
                            question_type=QuestionType.FILL_IN_BLANK,
                            count=3,
                            difficulty=QuestionDifficulty.EASY,
                        ),
                        QuestionBatch(
                            question_type=QuestionType.FILL_IN_BLANK,
                            count=3,
                            difficulty=QuestionDifficulty.MEDIUM,
                        ),  # 5th batch
                    ],
                )
            },
        )

    error_message = str(exc_info.value)
    assert "should have at most 4 items" in error_message


@pytest.mark.parametrize(
    "difficulty",
    [QuestionDifficulty.EASY, QuestionDifficulty.MEDIUM, QuestionDifficulty.HARD],
)
def test_quiz_create_all_difficulty_levels(difficulty):
    """Test quiz creation with each difficulty level."""
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name=f"{difficulty.value.title()} Course",
        title=f"{difficulty.value.title()} Quiz",
        selected_modules={
            "module_1": ModuleSelection(
                name="Test Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=difficulty,
                    )
                ],
            )
        },
    )

    batch = quiz_data.selected_modules["module_1"].question_batches[0]
    assert batch.difficulty == difficulty


def test_quiz_create_complex_difficulty_combinations():
    """Test complex combinations of question types and difficulties."""
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Complex Course",
        title="Complex Difficulty Quiz",
        selected_modules={
            "intro_module": ModuleSelection(
                name="Introduction",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=5,
                        difficulty=QuestionDifficulty.EASY,
                    ),
                ],
            ),
            "intermediate_module": ModuleSelection(
                name="Intermediate Topics",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=8,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.FILL_IN_BLANK,
                        count=6,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MATCHING,
                        count=4,
                        difficulty=QuestionDifficulty.MEDIUM,
                    ),
                ],
            ),
            "advanced_module": ModuleSelection(
                name="Advanced Topics",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.CATEGORIZATION,
                        count=3,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=12,
                        difficulty=QuestionDifficulty.HARD,
                    ),
                ],
            ),
        },
    )

    # Verify all modules and batches
    assert len(quiz_data.selected_modules) == 3

    total_batches = sum(
        len(mod.question_batches) for mod in quiz_data.selected_modules.values()
    )
    assert total_batches == 7

    # Verify no duplicate (type, difficulty) combinations within modules
    for module_id, module in quiz_data.selected_modules.items():
        combinations = [
            (batch.question_type, batch.difficulty) for batch in module.question_batches
        ]
        assert len(combinations) == len(
            set(combinations)
        ), f"Duplicate combinations in {module_id}"


def test_module_selection_with_difficulty_batches():
    """Test ModuleSelection with difficulty-enabled batches."""
    module = ModuleSelection(
        name="Test Module",
        question_batches=[
            QuestionBatch(
                question_type=QuestionType.MULTIPLE_CHOICE,
                count=5,
                difficulty=QuestionDifficulty.EASY,
            ),
            QuestionBatch(
                question_type=QuestionType.FILL_IN_BLANK,
                count=3,
                difficulty=QuestionDifficulty.HARD,
            ),
        ],
    )

    assert module.name == "Test Module"
    assert len(module.question_batches) == 2
    assert module.question_batches[0].difficulty == QuestionDifficulty.EASY
    assert module.question_batches[1].difficulty == QuestionDifficulty.HARD


def test_module_selection_empty_batches_rejected():
    """Test that ModuleSelection requires at least one batch."""
    with pytest.raises(ValidationError):
        ModuleSelection(name="Empty Module", question_batches=[])


def test_difficulty_enum_values_in_schema():
    """Test that all QuestionDifficulty enum values work in schema."""
    difficulties = [
        QuestionDifficulty.EASY,
        QuestionDifficulty.MEDIUM,
        QuestionDifficulty.HARD,
    ]

    for difficulty in difficulties:
        batch = QuestionBatch(
            question_type=QuestionType.MULTIPLE_CHOICE, count=5, difficulty=difficulty
        )
        assert batch.difficulty == difficulty
        assert batch.difficulty.value in ["easy", "medium", "hard"]


def test_difficulty_enum_string_values():
    """Test that difficulty enum has expected string values."""
    assert QuestionDifficulty.EASY.value == "easy"
    assert QuestionDifficulty.MEDIUM.value == "medium"
    assert QuestionDifficulty.HARD.value == "hard"


def test_difficulty_explicit_assignment():
    """Test that difficulty must be explicitly assigned."""
    batch = QuestionBatch(
        question_type=QuestionType.MULTIPLE_CHOICE,
        count=10,
        difficulty=QuestionDifficulty.MEDIUM,
    )
    assert batch.difficulty == QuestionDifficulty.MEDIUM
    assert batch.difficulty.value == "medium"
