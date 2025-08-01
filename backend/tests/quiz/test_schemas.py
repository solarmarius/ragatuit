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


def test_manual_module_create_schema_validation():
    """Test ManualModuleCreate schema validation."""
    from src.quiz.schemas import ManualModuleCreate

    # Valid with text content
    valid_module = ManualModuleCreate(
        name="Test Module", text_content="Some test content"
    )
    assert valid_module.name == "Test Module"
    assert valid_module.text_content == "Some test content"

    # Valid without text content (for file uploads)
    valid_module_no_text = ManualModuleCreate(name="File Module")
    assert valid_module_no_text.name == "File Module"
    assert valid_module_no_text.text_content is None


def test_manual_module_create_name_validation():
    """Test ManualModuleCreate name field validation."""
    from src.quiz.schemas import ManualModuleCreate

    # Valid name
    valid_module = ManualModuleCreate(name="Valid Module Name")
    assert valid_module.name == "Valid Module Name"

    # Test name length limits
    with pytest.raises(ValidationError):
        ManualModuleCreate(name="")  # Empty name

    # Very long name (over 255 characters)
    long_name = "A" * 256
    with pytest.raises(ValidationError):
        ManualModuleCreate(name=long_name)

    # Maximum valid length (255 characters)
    max_name = "A" * 255
    valid_long_module = ManualModuleCreate(name=max_name)
    assert len(valid_long_module.name) == 255


def test_manual_module_create_text_content_validation():
    """Test ManualModuleCreate text content validation."""
    from src.quiz.schemas import ManualModuleCreate

    # Valid text content
    valid_module = ManualModuleCreate(name="Test", text_content="Valid content")
    assert valid_module.text_content == "Valid content"

    # Empty string should be rejected
    with pytest.raises(ValidationError) as exc_info:
        ManualModuleCreate(name="Test", text_content="")
    assert "Text content cannot be empty" in str(exc_info.value)

    # Whitespace-only should be rejected
    with pytest.raises(ValidationError) as exc_info:
        ManualModuleCreate(name="Test", text_content="   \n\t  ")
    assert "Text content cannot be empty" in str(exc_info.value)

    # None is valid (for file uploads)
    valid_none = ManualModuleCreate(name="Test", text_content=None)
    assert valid_none.text_content is None


def test_manual_module_response_schema():
    """Test ManualModuleResponse schema structure."""
    from src.quiz.schemas import ManualModuleResponse

    response = ManualModuleResponse(
        module_id="manual_test123",
        name="Test Module",
        content_preview="Preview content...",
        full_content="Full content for testing",
        word_count=10,
        processing_metadata={"source": "test"},
    )

    assert response.module_id == "manual_test123"
    assert response.name == "Test Module"
    assert response.content_preview == "Preview content..."
    assert response.full_content == "Full content for testing"
    assert response.word_count == 10
    assert response.processing_metadata == {"source": "test"}


def test_module_selection_with_manual_source_type():
    """Test ModuleSelection schema with manual source type."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch

    manual_module = ModuleSelection(
        name="Manual Module",
        source_type="manual",
        content="Manual content for testing",
        word_count=5,
        processing_metadata={"source": "manual_text"},
        content_type="text",
        question_batches=[
            QuestionBatch(
                question_type=QuestionType.MULTIPLE_CHOICE,
                count=10,
                difficulty=QuestionDifficulty.MEDIUM,
            )
        ],
    )

    assert manual_module.name == "Manual Module"
    assert manual_module.source_type == "manual"
    assert manual_module.content == "Manual content for testing"
    assert manual_module.word_count == 5
    assert manual_module.processing_metadata == {"source": "manual_text"}
    assert manual_module.content_type == "text"
    assert manual_module.total_questions == 10


def test_module_selection_canvas_default():
    """Test ModuleSelection schema defaults to canvas source type."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch

    canvas_module = ModuleSelection(
        name="Canvas Module",
        question_batches=[
            QuestionBatch(
                question_type=QuestionType.TRUE_FALSE,
                count=5,
                difficulty=QuestionDifficulty.EASY,
            )
        ],
    )

    assert canvas_module.name == "Canvas Module"
    assert canvas_module.source_type == "canvas"  # Default value
    assert canvas_module.content is None
    assert canvas_module.word_count is None
    assert canvas_module.processing_metadata is None
    assert canvas_module.content_type is None
    assert canvas_module.total_questions == 5


def test_module_selection_optional_manual_fields():
    """Test ModuleSelection with manual source but missing optional fields."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch

    # Manual module with minimal required fields
    minimal_manual = ModuleSelection(
        name="Minimal Manual Module",
        source_type="manual",
        question_batches=[
            QuestionBatch(
                question_type=QuestionType.FILL_IN_BLANK,
                count=3,
                difficulty=QuestionDifficulty.HARD,
            )
        ],
    )

    assert minimal_manual.name == "Minimal Manual Module"
    assert minimal_manual.source_type == "manual"
    assert minimal_manual.content is None
    assert minimal_manual.word_count is None
    assert minimal_manual.processing_metadata is None
    assert minimal_manual.content_type is None
    assert minimal_manual.total_questions == 3


def test_module_selection_total_questions_calculation():
    """Test ModuleSelection total_questions property with multiple batches."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch

    multi_batch_module = ModuleSelection(
        name="Multi Batch Module",
        source_type="manual",
        question_batches=[
            QuestionBatch(
                question_type=QuestionType.MULTIPLE_CHOICE,
                count=8,
                difficulty=QuestionDifficulty.EASY,
            ),
            QuestionBatch(
                question_type=QuestionType.TRUE_FALSE,
                count=4,
                difficulty=QuestionDifficulty.MEDIUM,
            ),
            QuestionBatch(
                question_type=QuestionType.MATCHING,
                count=3,
                difficulty=QuestionDifficulty.HARD,
            ),
        ],
    )

    assert multi_batch_module.total_questions == 15  # 8 + 4 + 3


def test_quiz_create_with_manual_modules():
    """Test QuizCreate schema with manual modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate

    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Mixed Quiz Course",
        selected_modules={
            "456": ModuleSelection(
                name="Canvas Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=10,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
            "manual_abc123": ModuleSelection(
                name="Manual Module",
                source_type="manual",
                content="Manual content",
                word_count=5,
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=5,
                        difficulty=QuestionDifficulty.EASY,
                    )
                ],
            ),
        },
        title="Mixed Quiz",
    )

    # Verify structure
    assert quiz_data.canvas_course_id == 123
    assert quiz_data.title == "Mixed Quiz"
    assert len(quiz_data.selected_modules) == 2

    # Verify Canvas module
    canvas_module = quiz_data.selected_modules["456"]
    assert canvas_module.name == "Canvas Module"
    assert canvas_module.source_type == "canvas"

    # Verify manual module
    manual_module = quiz_data.selected_modules["manual_abc123"]
    assert manual_module.name == "Manual Module"
    assert manual_module.source_type == "manual"
    assert manual_module.content == "Manual content"
    assert manual_module.word_count == 5


def test_quiz_create_manual_module_id_prefix_validation():
    """Test that manual modules with proper ID prefix are accepted."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch, QuizCreate

    # Valid manual module ID with manual_ prefix
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Manual ID Test",
        selected_modules={
            "manual_valid123": ModuleSelection(
                name="Valid Manual Module",
                source_type="manual",
                content="Test content for validation",
                word_count=4,
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=5,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title="Manual ID Test Quiz",
    )

    # Should validate successfully
    assert "manual_valid123" in quiz_data.selected_modules
    module = quiz_data.selected_modules["manual_valid123"]
    assert module.source_type == "manual"


def test_question_batch_in_manual_module():
    """Test QuestionBatch validation within manual modules."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch

    # Test all question types work with manual modules
    question_types = [
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.TRUE_FALSE,
        QuestionType.FILL_IN_BLANK,
        QuestionType.MATCHING,
        QuestionType.CATEGORIZATION,
    ]

    for qt in question_types:
        manual_module = ModuleSelection(
            name=f"Manual Module - {qt.value}",
            source_type="manual",
            content="Test content",
            question_batches=[
                QuestionBatch(
                    question_type=qt, count=5, difficulty=QuestionDifficulty.MEDIUM
                )
            ],
        )

        assert manual_module.question_batches[0].question_type == qt
        assert manual_module.total_questions == 5


def test_manual_module_processing_metadata_structure():
    """Test manual module processing metadata can contain various data types."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch

    complex_metadata = {
        "source": "manual_pdf",
        "file_count": 3,
        "total_pages": 15,
        "processing_time": 2.5,
        "extraction_method": "pdf_parser",
        "files": ["doc1.pdf", "doc2.pdf", "doc3.pdf"],
        "individual_word_counts": [100, 150, 200],
        "settings": {"language": "en", "parser_version": "1.2.3"},
    }

    manual_module = ModuleSelection(
        name="Complex Metadata Module",
        source_type="manual",
        content="Content from multiple PDFs",
        word_count=450,
        processing_metadata=complex_metadata,
        content_type="text",
        question_batches=[
            QuestionBatch(
                question_type=QuestionType.MULTIPLE_CHOICE,
                count=10,
                difficulty=QuestionDifficulty.HARD,
            )
        ],
    )

    assert manual_module.processing_metadata == complex_metadata
    assert manual_module.processing_metadata["file_count"] == 3
    assert manual_module.processing_metadata["settings"]["language"] == "en"


def test_module_selection_source_type_validation():
    """Test ModuleSelection source_type field validation."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.schemas import ModuleSelection, QuestionBatch

    # Valid source types
    valid_types = ["canvas", "manual"]

    for source_type in valid_types:
        module = ModuleSelection(
            name=f"Test {source_type.title()} Module",
            source_type=source_type,
            question_batches=[
                QuestionBatch(
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    count=5,
                    difficulty=QuestionDifficulty.MEDIUM,
                )
            ],
        )
        assert module.source_type == source_type

    # Custom source types should also be allowed (for future extensibility)
    custom_module = ModuleSelection(
        name="Custom Source Module",
        source_type="google_drive",  # Future source type
        question_batches=[
            QuestionBatch(
                question_type=QuestionType.TRUE_FALSE,
                count=3,
                difficulty=QuestionDifficulty.EASY,
            )
        ],
    )
    assert custom_module.source_type == "google_drive"


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
