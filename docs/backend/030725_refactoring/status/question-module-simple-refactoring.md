# Question Module Simple Refactoring Guide

## Overview

This document outlines a minimal refactoring strategy for the Rag@UiT question module to support multiple question types beyond Multiple Choice Questions (MCQs). The approach leverages the existing polymorphic architecture while making minimal changes to support new question types like Fill in the Blank.

## Current Architecture Strengths

The current implementation already has excellent foundations:

1. **Polymorphic Database Model**: The `Question` model uses a discriminator pattern with `question_type` field and JSONB storage for flexible question data
2. **Abstract Base Classes**: Well-defined `BaseQuestionType` and `BaseQuestionData` interfaces
3. **Registry Pattern**: Dynamic question type registration system
4. **Service Layer**: Clear separation of concerns with type-agnostic service methods
5. **Template System**: Flexible Jinja2-based template manager

## Minimal Changes Required

### 1. Template Manager Enhancement

The template manager needs a small update to automatically find templates based on question type:

```python
# backend/src/question/templates/manager.py

def get_template(
    self,
    question_type: QuestionType,
    template_name: str | None = None,
    language: QuizLanguage | str | None = None,
) -> PromptTemplate:
    """
    Get a prompt template for a question type.

    Args:
        question_type: The question type
        template_name: Specific template name, uses default if None
        language: Language for template, uses English if None

    Returns:
        Prompt template
    """
    if not self._initialized:
        self.initialize()

    # Normalize language
    if language is None:
        language = QuizLanguage.ENGLISH
    elif isinstance(language, str):
        language = QuizLanguage(language)

    # If no specific template name, build default name based on question type
    if template_name is None:
        template_name = f"batch_{question_type.value}"
        if language == QuizLanguage.NORWEGIAN:
            template_name += "_no"

    # Try to find the template
    if template_name in self._template_cache:
        template = self._template_cache[template_name]
        if template.question_type == question_type:
            return template

    # If not found, raise clear error
    raise ValueError(
        f"No template found for question type {question_type.value} "
        f"with name {template_name} and language {language.value}"
    )
```

### 2. Generation Service Update

Update the generation service to use the quiz's question type:

```python
# backend/src/question/services/generation_service.py

async def generate_questions_for_quiz(
    self,
    quiz_id: UUID,
    extracted_content: dict[str, str],
    provider_name: str = "openai",
) -> dict[str, list[Any]]:
    """
    Generate questions for all modules based on quiz configuration.

    The quiz defines:
    - question_type: Type of questions to generate
    - language: Language for generation
    - selected_modules: Modules with question counts
    """
    try:
        # Get quiz to access configuration
        quiz = await self._get_quiz(quiz_id)

        # Get the template for this quiz's question type and language
        template = self.template_manager.get_template(
            question_type=quiz.question_type,  # Use quiz's question type
            language=quiz.language
        )

        # Process modules with the appropriate template
        # ... rest of the existing logic ...
```

### 3. Template File Naming Convention

Establish a clear naming convention for template files:

```
templates/files/
├── batch_multiple_choice.json       # English MCQ template
├── batch_multiple_choice_no.json    # Norwegian MCQ template
├── batch_fill_in_blank.json        # English Fill in the Blank (future)
├── batch_fill_in_blank_no.json     # Norwegian Fill in the Blank (future)
└── ...
```

## Adding a New Question Type (Example: Fill in the Blank)

Here's the complete process for adding Fill in the Blank questions:

### Step 1: Update the Enum

```python
# backend/src/question/types/base.py

class QuestionType(str, Enum):
    """Enumeration of supported question types."""

    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"  # Add new type
```

### Step 2: Create the Question Type Implementation

```python
# backend/src/question/types/fib.py

from typing import Any
from pydantic import Field, field_validator
from .base import BaseQuestionData, BaseQuestionType, QuestionType

class FillInBlankData(BaseQuestionData):
    """Data model for fill-in-the-blank questions."""

    # Store the question with blanks marked as [BLANK_1], [BLANK_2], etc.
    # This makes it easy to display and process
    correct_answers: list[str] = Field(
        min_items=1,
        max_items=10,
        description="List of correct answers for each blank in order"
    )
    case_sensitive: bool = Field(
        default=False,
        description="Whether answers are case-sensitive"
    )

    @field_validator("correct_answers")
    @classmethod
    def validate_answers(cls, v: list[str]) -> list[str]:
        """Ensure all answers are non-empty."""
        for i, answer in enumerate(v):
            if not answer.strip():
                raise ValueError(f"Answer {i+1} cannot be empty")
        return v

    @field_validator("question_text")
    @classmethod
    def validate_blanks(cls, v: str, values: dict) -> str:
        """Ensure question has the correct number of blanks."""
        if 'correct_answers' in values:
            expected_blanks = len(values['correct_answers'])
            # Count [BLANK_N] patterns in the text
            import re
            blank_pattern = r'\[BLANK_\d+\]'
            found_blanks = len(re.findall(blank_pattern, v))

            if found_blanks != expected_blanks:
                raise ValueError(
                    f"Question has {found_blanks} blanks but "
                    f"{expected_blanks} answers provided"
                )
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
            "blank_count": len(data.correct_answers),
            "question_type": self.question_type.value,
        }

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """Format for Canvas LMS export."""
        if not isinstance(data, FillInBlankData):
            raise ValueError("Expected FillInBlankData")

        # Canvas expects specific format for fill-in-multiple-blanks
        # Replace [BLANK_N] with Canvas syntax
        import re
        canvas_text = data.question_text

        # Build answers structure for Canvas
        answers = []
        for i, answer in enumerate(data.correct_answers, 1):
            blank_id = f"blank_{i}"
            # Replace [BLANK_N] with Canvas reference
            canvas_text = canvas_text.replace(f"[BLANK_{i}]", f"[{blank_id}]")

            answers.append({
                "blank_id": blank_id,
                "blank_text": answer,
                "weight": 100
            })

        return {
            "question_type": "fill_in_multiple_blanks_question",
            "question_text": canvas_text,
            "answers": answers,
            "points_possible": len(data.correct_answers),
        }
```

### Step 3: Register the New Type

```python
# backend/src/question/types/registry.py

def _initialize_default_types(self) -> None:
    """Initialize the registry with default question type implementations."""
    if self._initialized:
        return

    try:
        # Import question types
        from .mcq import MultipleChoiceQuestionType
        from .fib import FillInBlankQuestionType  # Import new type

        # Register question types
        self.register_question_type(
            QuestionType.MULTIPLE_CHOICE,
            MultipleChoiceQuestionType()
        )
        self.register_question_type(
            QuestionType.FILL_IN_BLANK,
            FillInBlankQuestionType()  # Register new type
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

Create template files for the new question type:

**English Template** (`batch_fill_in_blank.json`):
```json
{
  "name": "batch_fill_in_blank",
  "version": "1.0",
  "question_type": "fill_in_blank",
  "description": "Template for generating fill-in-the-blank questions",
  "system_prompt": "You are an expert educator creating fill-in-the-blank questions. Generate questions where key terms or concepts are replaced with blanks marked as [BLANK_1], [BLANK_2], etc.\n\nIMPORTANT REQUIREMENTS:\n1. Generate EXACTLY {{ question_count }} fill-in-the-blank questions\n2. Each blank should be marked as [BLANK_N] where N is the blank number\n3. Provide the correct answer for each blank\n4. Focus on important concepts, definitions, or key terms\n5. Make questions clear and unambiguous\n6. Vary difficulty levels\n\nReturn your response as a valid JSON array with exactly {{ question_count }} question objects.\n\nEach question object must have this exact structure:\n{\n    \"question_text\": \"The capital of France is [BLANK_1].\",\n    \"correct_answers\": [\"Paris\"],\n    \"case_sensitive\": false,\n    \"explanation\": \"Brief explanation of the answer\"\n}\n\nIMPORTANT:\n- Return ONLY a valid JSON array\n- No markdown code blocks\n- Each question can have multiple blanks\n- correct_answers array must match the number of blanks",
  "user_prompt": "Based on the following content from the module '{{ module_name }}', generate exactly {{ question_count }} fill-in-the-blank questions.\n\nMODULE CONTENT:\n{{ module_content }}\n\nGenerate exactly {{ question_count }} questions:",
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

**Norwegian Template** (`batch_fill_in_blank_no.json`):
```json
{
  "name": "batch_fill_in_blank_no",
  "version": "1.0",
  "question_type": "fill_in_blank",
  "language": "no",
  "description": "Template for generating fill-in-the-blank questions in Norwegian",
  "system_prompt": "Du er en ekspert pedagog som lager fyll-inn-spørsmål. Generer spørsmål der nøkkeltermer eller konsepter er erstattet med blanke felt merket som [BLANK_1], [BLANK_2], osv.\n\nVIKTIGE KRAV:\n1. Generer NØYAKTIG {{ question_count }} fyll-inn-spørsmål\n2. Hvert blankt felt skal merkes som [BLANK_N] der N er feltnummeret\n3. Oppgi riktig svar for hvert felt\n4. Fokuser på viktige konsepter, definisjoner eller nøkkeltermer\n5. Lag klare og entydige spørsmål\n6. Varier vanskelighetsgraden\n\nReturner svaret som en gyldig JSON-array med nøyaktig {{ question_count }} spørsmålsobjekter.\n\nHvert spørsmålsobjekt må ha denne eksakte strukturen:\n{\n    \"question_text\": \"Hovedstaden i Norge er [BLANK_1].\",\n    \"correct_answers\": [\"Oslo\"],\n    \"case_sensitive\": false,\n    \"explanation\": \"Kort forklaring av svaret\"\n}\n\nVIKTIG:\n- Returner KUN en gyldig JSON-array\n- Ingen markdown-kodeblokker\n- Hvert spørsmål kan ha flere blanke felt\n- correct_answers-arrayen må matche antall blanke felt",
  "user_prompt": "Basert på følgende innhold fra modulen '{{ module_name }}', generer nøyaktig {{ question_count }} fyll-inn-spørsmål.\n\nMODULINNHOLD:\n{{ module_content }}\n\nGenerer nøyaktig {{ question_count }} spørsmål:",
  "variables": {
    "module_name": "Navnet på modulen",
    "module_content": "Modulinnholdet for å generere spørsmål fra",
    "question_count": "Antall spørsmål som skal genereres"
  },
  "author": "System",
  "tags": ["batch", "fill_in_blank", "module", "norwegian"],
  "created_at": null,
  "updated_at": null,
  "min_content_length": 100,
  "max_content_length": 50000
}
```

### Step 5: Test the New Type

```python
# backend/src/question/tests/test_fib_question_type.py

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
        "question_text": "The capital of [BLANK_1] is [BLANK_2].",
        "correct_answers": ["France", "Paris"],
        "case_sensitive": False,
        "explanation": "France is a country and Paris is its capital."
    }

    result = fib_type.validate_data(valid_data)
    assert isinstance(result, FillInBlankData)
    assert len(result.correct_answers) == 2

    # Invalid data - mismatch between blanks and answers
    invalid_data = {
        "question_text": "The capital is [BLANK_1].",
        "correct_answers": ["Paris", "London"],  # Too many answers
        "case_sensitive": False
    }

    with pytest.raises(ValueError):
        fib_type.validate_data(invalid_data)

def test_fib_canvas_format():
    """Test Canvas export formatting."""
    fib_type = FillInBlankQuestionType()

    data = FillInBlankData(
        question_text="The [BLANK_1] of France is [BLANK_2].",
        correct_answers=["capital", "Paris"],
        case_sensitive=False
    )

    canvas_format = fib_type.format_for_canvas(data)

    assert canvas_format["question_type"] == "fill_in_multiple_blanks_question"
    assert "[blank_1]" in canvas_format["question_text"]
    assert "[blank_2]" in canvas_format["question_text"]
    assert len(canvas_format["answers"]) == 2
```

## Testing Strategy

### Unit Tests
- Test each question type implementation in isolation
- Verify validation rules work correctly
- Test formatting methods for display and Canvas export

### Integration Tests
- Test question creation through the service layer
- Verify template loading for each question type
- Test question generation with mock LLM responses

### End-to-End Tests
- Test complete flow from quiz creation to question generation
- Verify Canvas export works for all question types

## Benefits of This Approach

1. **Minimal Changes**: Leverages existing polymorphic architecture
2. **Type Safety**: Strong validation through Pydantic models
3. **Extensibility**: Adding new types is straightforward
4. **Maintainability**: Each question type is self-contained
5. **No Breaking Changes**: Existing MCQ functionality unchanged

## Summary

The current architecture is already well-designed for multiple question types. The only changes needed are:

1. Small update to template manager for automatic template discovery
2. Clear template naming convention
3. Proper implementation of new question types following the existing pattern

This approach keeps the codebase simple while making it easy to add new question types in the future.
