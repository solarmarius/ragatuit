# Adding New Question Types

This guide explains how to add new question types to the Rag@UiT question module.

## Overview

The question module uses a polymorphic design that makes adding new question types straightforward. Each question type is self-contained and follows a consistent pattern.

## Step-by-Step Guide

### Step 1: Add the Question Type Enum

Edit `backend/src/question/types/base.py` and add your new question type to the `QuestionType` enum:

```python
class QuestionType(str, Enum):
    """Enumeration of supported question types."""

    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"  # Add your new type here
    # TRUE_FALSE = "true_false"      # Future example
```

### Step 2: Create the Question Type Implementation

Create a new file `backend/src/question/types/{your_type}.py`. For example, for Fill in the Blank:

```python
# backend/src/question/types/fib.py

from typing import Any
from pydantic import Field, field_validator
from .base import BaseQuestionData, BaseQuestionType, QuestionType

class FillInBlankData(BaseQuestionData):
    """Data model for fill-in-the-blank questions."""

    # Define your question-specific fields
    correct_answers: list[str] = Field(
        min_items=1,
        description="List of correct answers for each blank"
    )
    case_sensitive: bool = Field(
        default=False,
        description="Whether answers are case-sensitive"
    )

    # Add validators as needed
    @field_validator("correct_answers")
    @classmethod
    def validate_answers(cls, v: list[str]) -> list[str]:
        """Ensure all answers are non-empty."""
        for answer in v:
            if not answer.strip():
                raise ValueError("Answers cannot be empty")
        return v

class FillInBlankQuestionType(BaseQuestionType):
    """Implementation for fill-in-the-blank questions."""

    @property
    def question_type(self) -> QuestionType:
        return QuestionType.FILL_IN_BLANK

    @property
    def data_model(self) -> type[FillInBlankData]:
        return FillInBlankData

    def validate_data(self, data: dict[str, Any]) -> FillInBlankData:
        """Validate and parse fill-in-the-blank data."""
        return FillInBlankData(**data)

    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """Format for API display."""
        if not isinstance(data, FillInBlankData):
            raise ValueError("Expected FillInBlankData")

        return {
            "question_text": data.question_text,
            "correct_answers": data.correct_answers,
            "case_sensitive": data.case_sensitive,
            "question_type": self.question_type.value,
        }

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """Format for Canvas LMS export."""
        if not isinstance(data, FillInBlankData):
            raise ValueError("Expected FillInBlankData")

        # Format according to Canvas API requirements
        # See Canvas API documentation for your question type
        return {
            "question_type": "fill_in_multiple_blanks_question",
            "question_text": data.question_text,
            # ... Canvas-specific formatting ...
        }
```

### Step 3: Register the Question Type

Edit `backend/src/question/types/registry.py` and import/register your new type:

```python
def _initialize_default_types(self) -> None:
    """Initialize the registry with default question type implementations."""
    if self._initialized:
        return

    try:
        # Import question types
        from .mcq import MultipleChoiceQuestionType
        from .fib import FillInBlankQuestionType  # Import your new type

        # Register question types
        self.register_question_type(
            QuestionType.MULTIPLE_CHOICE,
            MultipleChoiceQuestionType()
        )
        self.register_question_type(
            QuestionType.FILL_IN_BLANK,
            FillInBlankQuestionType()  # Register your new type
        )

        logger.info(
            "question_type_registry_initialized",
            registered_types=len(self._question_types),
        )

    except ImportError as e:
        logger.error(
            "failed_to_initialize_default_question_types",
            error=str(e),
            exc_info=True,
        )

    self._initialized = True
```

### Step 4: Create Generation Templates

Create template files for your question type in `backend/src/question/templates/files/`:

#### English Template
Create `batch_{your_type}.json`:

```json
{
  "name": "batch_fill_in_blank",
  "version": "1.0",
  "question_type": "fill_in_blank",
  "description": "Template for generating fill-in-the-blank questions",
  "system_prompt": "You are an expert educator creating fill-in-the-blank questions...",
  "user_prompt": "Based on the following content from module '{{ module_name }}', generate {{ question_count }} questions...",
  "variables": {
    "module_name": "The name of the module",
    "module_content": "The module content to generate questions from",
    "question_count": "Number of questions to generate"
  },
  "author": "System",
  "tags": ["batch", "fill_in_blank", "module"],
  "created_at": null,
  "updated_at": null,
  "min_content_length": 100,
  "max_content_length": 50000
}
```

#### Norwegian Template (if needed)
Create `batch_{your_type}_no.json` with Norwegian prompts and set `"language": "no"`.

### Step 5: Test Your Implementation

Create test file `backend/src/question/tests/test_{your_type}_question_type.py`:

```python
import pytest
from src.question.types import QuestionType, get_question_type_registry
from src.question.types.fib import FillInBlankData, FillInBlankQuestionType

def test_fib_registration():
    """Test that fill-in-the-blank type is registered."""
    registry = get_question_type_registry()
    assert registry.is_registered(QuestionType.FILL_IN_BLANK)

def test_fib_validation():
    """Test fill-in-the-blank data validation."""
    fib_type = FillInBlankQuestionType()

    # Valid data
    valid_data = {
        "question_text": "The capital of France is _____.",
        "correct_answers": ["Paris"],
        "case_sensitive": False,
        "explanation": "Paris is the capital city of France."
    }

    result = fib_type.validate_data(valid_data)
    assert isinstance(result, FillInBlankData)
    assert len(result.correct_answers) == 1

def test_fib_canvas_format():
    """Test Canvas export formatting."""
    fib_type = FillInBlankQuestionType()

    data = FillInBlankData(
        question_text="The capital of France is _____.",
        correct_answers=["Paris"],
        case_sensitive=False
    )

    canvas_format = fib_type.format_for_canvas(data)
    assert canvas_format["question_type"] == "fill_in_multiple_blanks_question"
```

## Template Requirements

### System Prompt
Your system prompt should:
- Clearly explain the question type format
- Specify the exact JSON structure expected
- Include examples if helpful
- Set expectations for difficulty, language, etc.

### User Prompt
Your user prompt should include these variables:
- `{{ module_name }}` - The name of the Canvas module
- `{{ module_content }}` - The actual content to generate questions from
- `{{ question_count }}` - Number of questions to generate

### JSON Response Format
The LLM must return a JSON array of question objects. Each object must include:
- `question_text` - The question text (required by BaseQuestionData)
- `explanation` - Explanation of the answer (optional in BaseQuestionData)
- Your type-specific fields (e.g., `correct_answers`, `case_sensitive`)

## Canvas Integration

Different question types require different Canvas API formats. Consult the Canvas API documentation for your question type:
- [Canvas Quiz Question Types](https://canvas.instructure.com/doc/api/quiz_questions.html)

Common Canvas question types:
- `multiple_choice_question`
- `fill_in_multiple_blanks_question`
- `true_false_question`
- `essay_question`
- `short_answer_question`

## Checklist

Before considering your question type complete:

- [ ] Added enum value to `QuestionType`
- [ ] Created data model extending `BaseQuestionData`
- [ ] Created implementation extending `BaseQuestionType`
- [ ] Registered in the question type registry
- [ ] Created English generation template
- [ ] Created Norwegian generation template (if supporting Norwegian)
- [ ] Added comprehensive unit tests
- [ ] Tested question generation end-to-end
- [ ] Tested Canvas export functionality
- [ ] Updated any relevant documentation

## Troubleshooting

### Template Not Found
- Ensure template filename follows convention: `batch_{question_type}.json`
- Check that template has correct `question_type` field
- Verify template is in `backend/src/question/templates/files/`

### Registration Issues
- Make sure import statement is added to registry
- Check for typos in enum value and registration
- Ensure the implementation class is instantiated when registering

### Generation Failures
- Test your template prompts manually first
- Ensure JSON structure matches your data model
- Check that all required fields are included
- Validate that the LLM response can be parsed

## Future Considerations

When adding a new question type, consider:
- How will it be displayed in the frontend?
- Does it need special validation rules?
- Can it be auto-graded or does it need manual review?
- How should partial credit work (if applicable)?
- What Canvas-specific features does it support?
