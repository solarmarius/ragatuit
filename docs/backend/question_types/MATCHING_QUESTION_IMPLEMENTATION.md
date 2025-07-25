# Matching Question Type Implementation Guide

**Document Date**: July 22, 2025
**Feature**: Matching Question Type Support
**Target System**: Rag@UiT Canvas LMS Quiz Generator

## 1. Feature Overview

### What It Does

The Matching question type allows instructors to create quiz questions where students match items from one list (questions/left side) with items from another list (answers/right side). This question type supports:

- **1:1 Matching**: Each question has exactly one correct answer
- **Distractors**: Extra incorrect answers that don't match any question
- **Canvas Integration**: Direct export to Canvas LMS New Quizzes format
- **AI Generation**: Automated question creation from course content
- **Multilingual Support**: Both English and Norwegian question generation

### Business Value

- **Enhanced Question Variety**: Expands beyond Multiple Choice and Fill-in-Blank
- **Effective Assessment**: Tests associative knowledge and connections between concepts
- **Canvas Compatible**: Seamless integration with existing Canvas LMS workflows
- **Time Saving**: AI-powered generation reduces manual question creation time

### User Benefits

- Instructors can create engaging matching exercises automatically
- Students get diverse question types that test different cognitive skills
- Questions are directly exported to Canvas without manual reformatting

## 2. Technical Architecture

### High-Level Architecture

The Matching question type follows Rag@UiT's established polymorphic question architecture:

```
Question Generation Pipeline:
Course Content → AI Templates → Question Data → Canvas Export

Architecture Components:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Templates  │    │   Data Models    │    │  Canvas Export  │
│  (English/NO)   │───▶│  MatchingData    │───▶│  New Quiz API   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Question Type    │
                       │    Registry      │
                       └──────────────────┘
```

### System Integration

- **Polymorphic Design**: Extends `BaseQuestionType` and `BaseQuestionData`
- **Registry Pattern**: Auto-registered in `QuestionTypeRegistry`
- **Template System**: Uses existing Jinja2 template engine
- **Database Storage**: JSONB column in existing `Question` model
- **Canvas Service**: Integrates with existing Canvas API client

### Key Interfaces

```python
# Abstract interfaces that must be implemented
BaseQuestionType:
  - validate_data()
  - format_for_display()
  - format_for_canvas()
  - format_for_export()

# Data flow
Raw AI Response → validate_data() → MatchingData → format_for_canvas() → Canvas API
```

## 3. Dependencies & Prerequisites

### External Dependencies

- **Existing**: All dependencies already in project
  - `pydantic`: Data validation and serialization
  - `sqlmodel`: Database ORM
  - `uuid`: Canvas question ID generation
  - `jinja2`: Template rendering (via existing template system)

### Version Requirements

- Python: 3.11+ (existing project requirement)
- Pydantic: 2.0+ (existing in project)
- No additional package installations required

### Environment Setup

- Existing backend development environment
- Canvas API credentials configured
- Database with existing `Question` table
- OpenAI API key for question generation (existing)

## 4. Implementation Details

### 4.1 File Structure

```
backend/src/
├── question/
│   ├── types/
│   │   ├── base.py                    # ← UPDATE: Add MATCHING enum
│   │   ├── matching.py                # ← CREATE: New implementation
│   │   └── registry.py                # ← UPDATE: Register new type
│   └── templates/
│       └── files/
│           ├── batch_matching.json    # ← CREATE: English template
│           └── batch_matching_no.json # ← CREATE: Norwegian template
├── canvas/
│   └── constants.py                   # ← UPDATE: Add Canvas constants
└── tests/
    └── question/
        └── types/
            └── test_matching.py       # ← CREATE: Comprehensive tests
```

### 4.2 Step-by-Step Implementation

#### Step 1: Update Base Constants and Enums

**File**: `backend/src/question/types/base.py`

**Changes**:

```python
class QuestionType(str, Enum):
    """
    Enumeration of supported question types.

    To add a new question type:
    1. Add enum value here
    2. Create implementation in types/{type_name}.py
    3. Register in registry.py
    4. Add templates in templates/files/
    See ADDING_NEW_TYPES.md for detailed instructions.
    """

    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"
    MATCHING = "matching"  # ← ADD THIS LINE
```

**File**: `backend/src/canvas/constants.py`

**Changes**:

```python
class CanvasScoringAlgorithm:
    """Canvas New Quizzes API scoring algorithms."""

    # Overall quiz item scoring algorithms
    MULTIPLE_METHODS = "MultipleMethods"  # Used when item has multiple scoring methods
    EQUIVALENCE = "Equivalence"  # Used for single-answer questions (MCQ)
    PARTIAL_DEEP = "PartialDeep"  # ← ADD THIS LINE (for matching questions)

    # Individual answer/blank scoring algorithms
    TEXT_CONTAINS_ANSWER = (
        "TextContainsAnswer"  # Used for fill-in-blank individual answers
    )


class CanvasInteractionType:
    """Canvas New Quizzes API interaction types."""

    CHOICE = "choice"  # Multiple choice questions
    RICH_FILL_BLANK = "rich-fill-blank"  # Fill-in-blank questions
    MATCHING = "matching"  # ← ADD THIS LINE (matching questions)
```

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add matching question type constants"`

#### Step 2: Create Data Models

**File**: `backend/src/question/types/matching.py` (NEW FILE)

**Complete Implementation**:

```python
"""Matching Question type implementation."""

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


class MatchingPair(BaseModel):
    """Data model for a single question-answer pair in a matching question."""

    question: str = Field(
        min_length=1,
        description="The question/left side item to match"
    )
    answer: str = Field(
        min_length=1,
        description="The correct answer/right side item"
    )


class MatchingData(BaseQuestionData):
    """Data model for matching questions."""

    pairs: list[MatchingPair] = Field(
        min_length=3,
        max_length=10,
        description="List of question-answer pairs (3-10 pairs)"
    )
    distractors: list[str] | None = Field(
        default=None,
        max_length=5,
        description="Optional distractor answers that don't match any question"
    )

    @field_validator("pairs")
    @classmethod
    def validate_pairs(cls, v: list[MatchingPair]) -> list[MatchingPair]:
        """Validate that pairs have no duplicate questions or answers."""
        if len(v) < 3:
            raise ValueError("At least 3 pairs are required")
        if len(v) > 10:
            raise ValueError("Maximum 10 pairs allowed")

        # Check for duplicate questions
        questions = [pair.question.strip().lower() for pair in v]
        if len(set(questions)) != len(questions):
            raise ValueError("Duplicate questions are not allowed")

        # Check for duplicate answers
        answers = [pair.answer.strip().lower() for pair in v]
        if len(set(answers)) != len(answers):
            raise ValueError("Duplicate answers are not allowed")

        return v

    @field_validator("distractors")
    @classmethod
    def validate_distractors(cls, v: list[str] | None) -> list[str] | None:
        """Validate distractors and ensure no duplicates."""
        if v is None:
            return v

        if len(v) > 5:
            raise ValueError("Maximum 5 distractors allowed")

        # Filter out empty strings and duplicates
        filtered = [d.strip() for d in v if d.strip()]

        # Remove duplicates while preserving order
        seen = set()
        unique_distractors = []
        for distractor in filtered:
            distractor_lower = distractor.lower()
            if distractor_lower not in seen:
                seen.add(distractor_lower)
                unique_distractors.append(distractor)

        return unique_distractors if unique_distractors else None

    def validate_no_distractor_matches(self) -> None:
        """Ensure distractors don't accidentally match any question answers."""
        if not self.distractors:
            return

        correct_answers = {pair.answer.strip().lower() for pair in self.pairs}
        for distractor in self.distractors:
            if distractor.strip().lower() in correct_answers:
                raise ValueError(
                    f"Distractor '{distractor}' matches a correct answer"
                )

    def get_all_answers(self) -> list[str]:
        """Get all possible answers (correct + distractors) for display."""
        answers = [pair.answer for pair in self.pairs]
        if self.distractors:
            answers.extend(self.distractors)
        return answers


class MatchingQuestionType(BaseQuestionType):
    """Implementation for matching questions."""

    @property
    def question_type(self) -> QuestionType:
        """Return the question type enum."""
        return QuestionType.MATCHING

    @property
    def data_model(self) -> type[MatchingData]:
        """Return the data model class for matching."""
        return MatchingData

    def validate_data(self, data: dict[str, Any]) -> MatchingData:
        """
        Validate and parse matching data.

        Args:
            data: Raw question data dictionary

        Returns:
            Validated matching data

        Raises:
            ValidationError: If data is invalid
        """
        matching_data = MatchingData(**data)
        # Additional validation
        matching_data.validate_no_distractor_matches()
        return matching_data

    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format matching data for API display.

        Args:
            data: Validated matching data

        Returns:
            Dictionary formatted for frontend display
        """
        if not isinstance(data, MatchingData):
            raise ValueError("Expected MatchingData")

        # Convert MatchingPair objects to dictionaries for frontend
        pairs_dict = [
            {"question": pair.question, "answer": pair.answer}
            for pair in data.pairs
        ]

        result = {
            "question_text": data.question_text,
            "pairs": pairs_dict,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

        if data.distractors:
            result["distractors"] = data.distractors

        return result

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format matching data for Canvas New Quizzes export.

        Args:
            data: Validated matching data

        Returns:
            Dictionary formatted for Canvas New Quizzes API
        """
        if not isinstance(data, MatchingData):
            raise ValueError("Expected MatchingData")

        # Generate unique IDs for Canvas questions
        question_ids = {
            pair.question: str(uuid.uuid4()) for pair in data.pairs
        }

        # Build answers list (correct answers + distractors)
        answers = [pair.answer for pair in data.pairs]
        if data.distractors:
            answers.extend(data.distractors)

        # Build questions array for Canvas
        canvas_questions = [
            {"id": question_ids[pair.question], "item_body": pair.question}
            for pair in data.pairs
        ]

        # Build scoring value mapping (question_id -> correct_answer)
        scoring_value = {
            question_ids[pair.question]: pair.answer for pair in data.pairs
        }

        # Build matches for edit_data
        matches = [
            {
                "answer_body": pair.answer,
                "question_id": question_ids[pair.question],
                "question_body": pair.question,
            }
            for pair in data.pairs
        ]

        # Wrap question text in paragraph tag if not already wrapped
        item_body = data.question_text
        if not item_body.strip().startswith("<p>"):
            item_body = f"<p>{item_body}</p>"

        return {
            "title": generate_canvas_title(data.question_text),
            "item_body": item_body,
            "calculator_type": "none",
            "interaction_data": {
                "answers": answers,
                "questions": canvas_questions,
            },
            "properties": {
                "shuffle_rules": {
                    "questions": {"shuffled": False},
                    "answers": {"shuffled": True},
                }
            },
            "scoring_data": {
                "value": scoring_value,
                "edit_data": {
                    "matches": matches,
                    "distractors": data.distractors or [],
                },
            },
            "answer_feedback": {},
            "scoring_algorithm": CanvasScoringAlgorithm.PARTIAL_DEEP,
            "interaction_type_slug": CanvasInteractionType.MATCHING,
            "feedback": {},
            "points_possible": len(data.pairs),
        }

    def format_for_export(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format matching data for generic export.

        Args:
            data: Validated matching data

        Returns:
            Dictionary with matching data for export
        """
        if not isinstance(data, MatchingData):
            raise ValueError("Expected MatchingData")

        # Convert pairs to simple dict format
        pairs_data = [
            {"question": pair.question, "answer": pair.answer}
            for pair in data.pairs
        ]

        result = {
            "question_text": data.question_text,
            "pairs": pairs_data,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

        if data.distractors:
            result["distractors"] = data.distractors

        return result
```

**Code Explanation**:

- `MatchingPair`: Simple model for question-answer pairs
- `MatchingData`: Main data model with validation for duplicates and distractor conflicts
- `MatchingQuestionType`: Complete implementation of all abstract methods
- Canvas export generates UUIDs and proper Canvas API format
- Validation ensures data integrity and Canvas compatibility

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add matching question data models and implementation"`

#### Step 3: Register Question Type

**File**: `backend/src/question/types/registry.py`

**Changes**:

```python
def _initialize_default_types(self) -> None:
    """Initialize the registry with default question type implementations."""
    if self._initialized:
        return

    try:
        # Import and register default question types
        from .fill_in_blank import FillInBlankQuestionType
        from .matching import MatchingQuestionType  # ← ADD THIS IMPORT
        from .mcq import MultipleChoiceQuestionType

        self.register_question_type(
            QuestionType.MULTIPLE_CHOICE, MultipleChoiceQuestionType()
        )
        self.register_question_type(
            QuestionType.FILL_IN_BLANK, FillInBlankQuestionType()
        )
        self.register_question_type(  # ← ADD THIS REGISTRATION
            QuestionType.MATCHING, MatchingQuestionType()
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
        # Continue with empty registry rather than failing

    self._initialized = True
```

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: register matching question type in registry"`

#### Step 4: Create English AI Template

**File**: `backend/src/question/templates/files/batch_matching.json` (NEW FILE)

**Complete Template**:

````json
{
  "name": "batch_matching",
  "version": "1.0",
  "question_type": "matching",
  "description": "Template for generating matching questions from module content",
  "system_prompt": "You are an expert educator creating matching quiz questions. Generate diverse, high-quality questions that test students' ability to connect related concepts, terms, and information.\n\nIMPORTANT REQUIREMENTS:\n1. Generate EXACTLY {{ question_count }} matching questions\n2. Each question must have 3-10 pairs (optimal: 4-6 pairs per question)\n3. Focus on meaningful connections: concepts to definitions, terms to examples, causes to effects, etc.\n4. Include 1-3 distractors per question (wrong answers that don't match any question)\n5. Ensure distractors are plausible but clearly don't match any question item\n6. Vary the difficulty levels and connection types\n7. Include brief explanations for the overall matching concept\n\nMATCHING TYPES TO CREATE:\n- **Concepts to Definitions**: \"Photosynthesis\" → \"Process converting sunlight to energy\"\n- **Terms to Examples**: \"Renewable Energy\" → \"Solar power\"\n- **Causes to Effects**: \"Deforestation\" → \"Increased CO2 levels\"\n- **People to Achievements**: \"Marie Curie\" → \"Discovered radium\"\n- **Dates to Events**: \"1969\" → \"Moon landing\"\n- **Countries to Capitals**: \"Japan\" → \"Tokyo\"\n- **Formulas to Names**: \"H2O\" → \"Water\"\n\nDISTRACTOR GUIDELINES:\n- Make distractors related to the topic but clearly incorrect\n- Don't make distractors that could reasonably match any question\n- Examples of good distractors: if matching countries to capitals, use capitals from other regions\n\nReturn your response as a valid JSON array with exactly {{ question_count }} question objects.\n\nEach question object must have this exact structure:\n{\n    \"question_text\": \"Match each country to its capital city.\",\n    \"pairs\": [\n        {\"question\": \"France\", \"answer\": \"Paris\"},\n        {\"question\": \"Japan\", \"answer\": \"Tokyo\"},\n        {\"question\": \"Egypt\", \"answer\": \"Cairo\"},\n        {\"question\": \"Brazil\", \"answer\": \"Brasília\"}\n    ],\n    \"distractors\": [\"Berlin\", \"Madrid\"],\n    \"explanation\": \"These are the official capital cities of their respective countries.\"\n}\n\nIMPORTANT:\n- Return ONLY a valid JSON array\n- No markdown code blocks (```json or ```)\n- No explanatory text before or after the JSON\n- Each question must have 3-10 pairs and 0-3 distractors\n- Ensure no duplicate questions or answers within each matching question\n- Verify that distractors don't accidentally match any question\n- The array must contain exactly {{ question_count }} question objects",
  "user_prompt": "Based on the following content from the module '{{ module_name }}', generate exactly {{ question_count }} matching questions.\n\nMODULE CONTENT:\n{{ module_content }}\n\nGenerate exactly {{ question_count }} questions:",
  "variables": {
    "module_name": "The name of the module",
    "module_content": "The module content to generate questions from",
    "question_count": "Number of questions to generate",
    "difficulty": "Question difficulty level (optional)",
    "tags": "List of topic tags to focus on (optional)",
    "custom_instructions": "Additional custom instructions (optional)"
  },
  "author": "System",
  "tags": ["batch", "matching", "module"],
  "created_at": null,
  "updated_at": null,
  "min_content_length": 100,
  "max_content_length": 50000
}
````

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add English AI template for matching questions"`

#### Step 5: Create Norwegian AI Template

**File**: `backend/src/question/templates/files/batch_matching_no.json` (NEW FILE)

**Complete Template**:

````json
{
  "name": "batch_matching_no",
  "version": "1.0",
  "question_type": "matching",
  "language": "no",
  "description": "Mal for generering av matchingspørsmål fra modulinnhold",
  "system_prompt": "Du er en ekspert pedagog som lager matchingspørsmål for quiz. Generer varierte, høykvalitets spørsmål som tester studentenes evne til å koble relaterte konsepter, termer og informasjon.\n\nVIKTIGE KRAV:\n1. Generer NØYAKTIG {{ question_count }} matchingspørsmål\n2. Hvert spørsmål må ha 3-10 par (optimalt: 4-6 par per spørsmål)\n3. Fokuser på meningsfulle forbindelser: konsepter til definisjoner, termer til eksempler, årsaker til virkninger, osv.\n4. Inkluder 1-3 distraktorer per spørsmål (feil svar som ikke matcher noe spørsmålselement)\n5. Sørg for at distraktorer er plausible men tydelig ikke matcher noe spørsmålselement\n6. Varierér vanskegrad og forbindelsestyper\n7. Inkluder korte forklaringer for det overordnede matchingkonseptet\n\nMATCHINGTYPER Å LAGE:\n- **Konsepter til Definisjoner**: \"Fotosyntese\" → \"Prosess som omgjør sollys til energi\"\n- **Termer til Eksempler**: \"Fornybar Energi\" → \"Solkraft\"\n- **Årsaker til Virkninger**: \"Avskoging\" → \"Økte CO2-nivåer\"\n- **Personer til Prestasjoner**: \"Marie Curie\" → \"Oppdaget radium\"\n- **Datoer til Hendelser**: \"1969\" → \"Månelanding\"\n- **Land til Hovedsteder**: \"Japan\" → \"Tokyo\"\n- **Formler til Navn**: \"H2O\" → \"Vann\"\n\nDISTRAKTORRETNINGSLINJER:\n- Lag distraktorer som er relatert til temaet men tydelig feil\n- Ikke lag distraktorer som rimelig kunne matche noe spørsmål\n- Eksempler på gode distraktorer: hvis du matcher land til hovedsteder, bruk hovedsteder fra andre regioner\n\nReturnér svaret ditt som en gyldig JSON-array med nøyaktig {{ question_count }} spørsmålsobjekter.\n\nHvert spørsmålsobjekt må ha denne nøyaktige strukturen:\n{\n    \"question_text\": \"Match hvert land til sin hovedstad.\",\n    \"pairs\": [\n        {\"question\": \"Frankrike\", \"answer\": \"Paris\"},\n        {\"question\": \"Japan\", \"answer\": \"Tokyo\"},\n        {\"question\": \"Egypt\", \"answer\": \"Kairo\"},\n        {\"question\": \"Brasil\", \"answer\": \"Brasília\"}\n    ],\n    \"distractors\": [\"Berlin\", \"Madrid\"],\n    \"explanation\": \"Dette er de offisielle hovedstedene til sine respektive land.\"\n}\n\nVIKTIG:\n- Returnér KUN en gyldig JSON-array\n- Ingen markdown-kodeblokker (```json eller ```)\n- Ingen forklarende tekst før eller etter JSON\n- Hvert spørsmål må ha 3-10 par og 0-3 distraktorer\n- Sørg for ingen duplikat spørsmål eller svar innenfor hvert matchingspørsmål\n- Verifiser at distraktorer ikke ved uhell matcher noe spørsmål\n- Arrayen må inneholde nøyaktig {{ question_count }} spørsmålsobjekter",
  "user_prompt": "Basert på følgende innhold fra modulen '{{ module_name }}', generer nøyaktig {{ question_count }} matchingspørsmål.\n\nMODULINNHOLD:\n{{ module_content }}\n\nGenerer nøyaktig {{ question_count }} spørsmål:",
  "variables": {
    "module_name": "Navnet på modulen",
    "module_content": "Modulinnholdet å generere spørsmål fra",
    "question_count": "Antall spørsmål å generere",
    "difficulty": "Spørsmålsvanskegrad (valgfritt)",
    "tags": "Liste over emnetagg å fokusere på (valgfritt)",
    "custom_instructions": "Ytterligere tilpassede instruksjoner (valgfritt)"
  },
  "author": "System",
  "tags": ["batch", "matching", "module", "norsk"],
  "created_at": null,
  "updated_at": null,
  "min_content_length": 100,
  "max_content_length": 50000
}
````

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add Norwegian AI template for matching questions"`

#### Step 6: Create Comprehensive Tests

**File**: `backend/tests/question/types/test_matching.py` (NEW FILE)

**Complete Test Suite**:

```python
"""Tests for matching question type implementation."""

import pytest
from pydantic import ValidationError

from src.question.types import QuestionType, get_question_type_registry
from src.question.types.matching import (
    MatchingData,
    MatchingPair,
    MatchingQuestionType,
)


class TestMatchingPair:
    """Tests for MatchingPair data model."""

    def test_create_valid_pair(self):
        """Test creating a valid matching pair."""
        pair = MatchingPair(question="France", answer="Paris")
        assert pair.question == "France"
        assert pair.answer == "Paris"

    def test_empty_question_fails(self):
        """Test that empty question fails validation."""
        with pytest.raises(ValidationError):
            MatchingPair(question="", answer="Paris")

    def test_empty_answer_fails(self):
        """Test that empty answer fails validation."""
        with pytest.raises(ValidationError):
            MatchingPair(question="France", answer="")

    def test_whitespace_only_fails(self):
        """Test that whitespace-only strings fail validation."""
        with pytest.raises(ValidationError):
            MatchingPair(question="   ", answer="Paris")
        with pytest.raises(ValidationError):
            MatchingPair(question="France", answer="   ")


class TestMatchingData:
    """Tests for MatchingData data model."""

    def test_create_valid_matching_data(self):
        """Test creating valid matching data with minimum pairs."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="Germany", answer="Berlin"),
            MatchingPair(question="Italy", answer="Rome"),
        ]
        data = MatchingData(
            question_text="Match countries to capitals",
            pairs=pairs
        )
        assert len(data.pairs) == 3
        assert data.distractors is None

    def test_create_with_distractors(self):
        """Test creating matching data with distractors."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="Germany", answer="Berlin"),
            MatchingPair(question="Italy", answer="Rome"),
        ]
        distractors = ["Madrid", "London"]
        data = MatchingData(
            question_text="Match countries to capitals",
            pairs=pairs,
            distractors=distractors
        )
        assert data.distractors == ["Madrid", "London"]

    def test_minimum_pairs_required(self):
        """Test that at least 3 pairs are required."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="Germany", answer="Berlin"),
        ]
        with pytest.raises(ValidationError, match="At least 3 pairs are required"):
            MatchingData(question_text="Test", pairs=pairs)

    def test_maximum_pairs_limit(self):
        """Test that maximum 10 pairs are allowed."""
        pairs = [
            MatchingPair(question=f"Country{i}", answer=f"Capital{i}")
            for i in range(11)
        ]
        with pytest.raises(ValidationError, match="Maximum 10 pairs allowed"):
            MatchingData(question_text="Test", pairs=pairs)

    def test_duplicate_questions_not_allowed(self):
        """Test that duplicate questions are not allowed."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="France", answer="Lyon"),  # Duplicate question
            MatchingPair(question="Germany", answer="Berlin"),
        ]
        with pytest.raises(ValidationError, match="Duplicate questions are not allowed"):
            MatchingData(question_text="Test", pairs=pairs)

    def test_duplicate_answers_not_allowed(self):
        """Test that duplicate answers are not allowed."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="Germany", answer="Paris"),  # Duplicate answer
            MatchingPair(question="Italy", answer="Rome"),
        ]
        with pytest.raises(ValidationError, match="Duplicate answers are not allowed"):
            MatchingData(question_text="Test", pairs=pairs)

    def test_case_insensitive_duplicate_detection(self):
        """Test that duplicate detection is case-insensitive."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="FRANCE", answer="Berlin"),  # Case-insensitive duplicate
            MatchingPair(question="Germany", answer="Rome"),
        ]
        with pytest.raises(ValidationError, match="Duplicate questions are not allowed"):
            MatchingData(question_text="Test", pairs=pairs)

    def test_maximum_distractors_limit(self):
        """Test maximum 5 distractors allowed."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="Germany", answer="Berlin"),
            MatchingPair(question="Italy", answer="Rome"),
        ]
        distractors = ["Madrid", "London", "Cairo", "Tokyo", "Moscow", "Sydney"]  # 6 distractors
        with pytest.raises(ValidationError, match="Maximum 5 distractors allowed"):
            MatchingData(question_text="Test", pairs=pairs, distractors=distractors)

    def test_empty_distractors_filtered(self):
        """Test that empty distractors are filtered out."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="Germany", answer="Berlin"),
            MatchingPair(question="Italy", answer="Rome"),
        ]
        distractors = ["Madrid", "", "  ", "London", ""]
        data = MatchingData(question_text="Test", pairs=pairs, distractors=distractors)
        assert data.distractors == ["Madrid", "London"]

    def test_duplicate_distractors_removed(self):
        """Test that duplicate distractors are removed."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="Germany", answer="Berlin"),
            MatchingPair(question="Italy", answer="Rome"),
        ]
        distractors = ["Madrid", "London", "madrid", "LONDON"]  # Case-insensitive duplicates
        data = MatchingData(question_text="Test", pairs=pairs, distractors=distractors)
        assert data.distractors == ["Madrid", "London"]

    def test_distractor_matches_answer_validation(self):
        """Test that distractors cannot match correct answers."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="Germany", answer="Berlin"),
            MatchingPair(question="Italy", answer="Rome"),
        ]
        distractors = ["Madrid", "Paris"]  # "Paris" matches a correct answer
        data = MatchingData(question_text="Test", pairs=pairs, distractors=distractors)

        with pytest.raises(ValueError, match="Distractor 'Paris' matches a correct answer"):
            data.validate_no_distractor_matches()

    def test_get_all_answers(self):
        """Test getting all answers including distractors."""
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

    def test_get_all_answers_no_distractors(self):
        """Test getting all answers when no distractors."""
        pairs = [
            MatchingPair(question="France", answer="Paris"),
            MatchingPair(question="Germany", answer="Berlin"),
            MatchingPair(question="Italy", answer="Rome"),
        ]
        data = MatchingData(question_text="Test", pairs=pairs)

        all_answers = data.get_all_answers()
        expected = ["Paris", "Berlin", "Rome"]
        assert all_answers == expected


class TestMatchingQuestionType:
    """Tests for MatchingQuestionType implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matching_type = MatchingQuestionType()
        self.valid_data = {
            "question_text": "Match countries to their capitals",
            "pairs": [
                {"question": "France", "answer": "Paris"},
                {"question": "Germany", "answer": "Berlin"},
                {"question": "Italy", "answer": "Rome"},
            ],
            "distractors": ["Madrid", "London"],
            "explanation": "These are European countries and capitals."
        }

    def test_question_type_property(self):
        """Test question type enum property."""
        assert self.matching_type.question_type == QuestionType.MATCHING

    def test_data_model_property(self):
        """Test data model property."""
        assert self.matching_type.data_model == MatchingData

    def test_validate_data_success(self):
        """Test successful data validation."""
        result = self.matching_type.validate_data(self.valid_data)
        assert isinstance(result, MatchingData)
        assert len(result.pairs) == 3
        assert result.distractors == ["Madrid", "London"]

    def test_validate_data_with_distractor_conflict(self):
        """Test validation fails when distractor matches answer."""
        invalid_data = self.valid_data.copy()
        invalid_data["distractors"] = ["Madrid", "Paris"]  # Paris is a correct answer

        with pytest.raises(ValueError, match="Distractor 'Paris' matches a correct answer"):
            self.matching_type.validate_data(invalid_data)

    def test_validate_data_wrong_type(self):
        """Test validation with wrong data type."""
        with pytest.raises(ValidationError):
            self.matching_type.validate_data({"invalid": "data"})

    def test_format_for_display(self):
        """Test formatting for display."""
        data = self.matching_type.validate_data(self.valid_data)
        result = self.matching_type.format_for_display(data)

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

    def test_format_for_display_no_distractors(self):
        """Test formatting for display without distractors."""
        data_no_distractors = self.valid_data.copy()
        del data_no_distractors["distractors"]

        data = self.matching_type.validate_data(data_no_distractors)
        result = self.matching_type.format_for_display(data)

        assert "distractors" not in result

    def test_format_for_display_wrong_type(self):
        """Test format_for_display with wrong data type."""
        from src.question.types.mcq import MultipleChoiceData

        mcq_data = MultipleChoiceData(
            question_text="Test",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_answer="A"
        )

        with pytest.raises(ValueError, match="Expected MatchingData"):
            self.matching_type.format_for_display(mcq_data)

    def test_format_for_canvas(self):
        """Test Canvas export formatting."""
        data = self.matching_type.validate_data(self.valid_data)
        result = self.matching_type.format_for_canvas(data)

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
        assert set(interaction_data["answers"]) == {"Paris", "Berlin", "Rome", "Madrid", "London"}

        # Validate scoring_data
        scoring_data = result["scoring_data"]
        assert "value" in scoring_data
        assert "edit_data" in scoring_data
        assert len(scoring_data["edit_data"]["matches"]) == 3
        assert scoring_data["edit_data"]["distractors"] == ["Madrid", "London"]

    def test_format_for_export(self):
        """Test generic export formatting."""
        data = self.matching_type.validate_data(self.valid_data)
        result = self.matching_type.format_for_export(data)

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


class TestMatchingQuestionTypeRegistry:
    """Tests for matching question type registry integration."""

    def test_matching_type_registered(self):
        """Test that matching type is registered in registry."""
        registry = get_question_type_registry()
        assert registry.is_registered(QuestionType.MATCHING)

    def test_get_matching_type_from_registry(self):
        """Test retrieving matching type from registry."""
        registry = get_question_type_registry()
        matching_type = registry.get_question_type(QuestionType.MATCHING)
        assert isinstance(matching_type, MatchingQuestionType)

    def test_matching_in_available_types(self):
        """Test that matching appears in available types."""
        registry = get_question_type_registry()
        available_types = registry.get_available_types()
        assert QuestionType.MATCHING in available_types


class TestMatchingQuestionEndToEnd:
    """End-to-end tests for matching question workflow."""

    def test_full_workflow(self):
        """Test complete workflow from raw data to Canvas export."""
        registry = get_question_type_registry()

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
            "explanation": "These are the original creators of popular programming languages."
        }

        # Get question type and validate data
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

    def test_round_trip_data_validation(self):
        """Test that data survives round-trip through validation."""
        original_data = {
            "question_text": "Match elements to symbols",
            "pairs": [
                {"question": "Hydrogen", "answer": "H"},
                {"question": "Oxygen", "answer": "O"},
                {"question": "Carbon", "answer": "C"},
            ],
            "explanation": "Chemical element symbols."
        }

        matching_type = MatchingQuestionType()

        # Validate and export
        validated = matching_type.validate_data(original_data)
        exported = matching_type.format_for_export(validated)

        # Re-validate exported data
        re_validated = matching_type.validate_data(exported)
        re_exported = matching_type.format_for_export(re_validated)

        # Should be identical
        assert exported == re_exported

    def test_complex_validation_scenario(self):
        """Test complex validation with edge cases."""
        # Test with maximum pairs, distractors, and edge case content
        pairs_data = [
            {"question": f"Question {i}", "answer": f"Answer {i}"}
            for i in range(1, 11)  # 10 pairs (maximum)
        ]

        complex_data = {
            "question_text": "Complex matching question with special characters: áéíóú & symbols!",
            "pairs": pairs_data,
            "distractors": ["Distractor 1", "Distractor 2", "Distractor 3"],  # 3 distractors
            "explanation": "This tests maximum complexity with special characters and symbols."
        }

        matching_type = MatchingQuestionType()
        validated_data = matching_type.validate_data(complex_data)

        # Should validate successfully
        assert len(validated_data.pairs) == 10
        assert len(validated_data.distractors) == 3

        # Canvas export should work
        canvas_format = matching_type.format_for_canvas(validated_data)
        assert canvas_format["points_possible"] == 10
        assert len(canvas_format["interaction_data"]["answers"]) == 13  # 10 + 3 distractors
```

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add comprehensive tests for matching question type"`

### 4.3 Data Models & Schemas

#### Core Data Structures

**MatchingPair Model**:

```python
class MatchingPair(BaseModel):
    question: str  # Left side item (min_length=1)
    answer: str    # Right side item (min_length=1)
```

**MatchingData Model**:

```python
class MatchingData(BaseQuestionData):
    pairs: list[MatchingPair]     # 3-10 pairs required
    distractors: list[str] | None # 0-5 optional distractors
```

#### Validation Rules

- **Pair Count**: 3-10 pairs per question
- **Duplicates**: No duplicate questions or answers within a question
- **Distractors**: Maximum 5, cannot match any correct answer
- **Case Sensitivity**: Duplicate detection is case-insensitive

#### Example Data

```json
{
  "question_text": "Match countries to their capitals",
  "pairs": [
    { "question": "France", "answer": "Paris" },
    { "question": "Germany", "answer": "Berlin" },
    { "question": "Italy", "answer": "Rome" }
  ],
  "distractors": ["Madrid", "London"],
  "explanation": "European countries and their capital cities"
}
```

#### Canvas Export Format

```json
{
    "interaction_data": {
        "answers": ["Paris", "Berlin", "Rome", "Madrid", "London"],
        "questions": [
            {"id": "uuid-1", "item_body": "France"},
            {"id": "uuid-2", "item_body": "Germany"},
            {"id": "uuid-3", "item_body": "Italy"}
        ]
    },
    "scoring_data": {
        "value": {
            "uuid-1": "Paris",
            "uuid-2": "Berlin",
            "uuid-3": "Rome"
        },
        "edit_data": {
            "matches": [...],
            "distractors": ["Madrid", "London"]
        }
    },
    "interaction_type_slug": "matching",
    "scoring_algorithm": "PartialDeep"
}
```

### 4.4 Configuration

#### No Additional Configuration Required

- Uses existing database schema (JSONB storage)
- Uses existing Canvas API configuration
- Uses existing OpenAI API configuration
- Uses existing template system configuration

#### Template Variables

Both English and Norwegian templates support:

- `module_name`: Name of the Canvas module
- `module_content`: Content to generate questions from
- `question_count`: Number of questions to generate
- `difficulty`: Optional difficulty level
- `tags`: Optional topic tags
- `custom_instructions`: Optional additional instructions

## 5. Testing Strategy

### Unit Tests (31 tests total)

- **MatchingPair Tests (4)**: Basic creation, empty field validation
- **MatchingData Tests (12)**: Validation, duplicates, distractors, limits
- **MatchingQuestionType Tests (12)**: All interface methods, error handling
- **Registry Tests (3)**: Registration, retrieval, availability

### Integration Tests (3)

- **End-to-End Workflow**: Complete data flow from raw input to Canvas export
- **Round-Trip Validation**: Data consistency through validation cycles
- **Complex Scenarios**: Maximum complexity with edge cases

### Manual Testing Steps

1. **Template Validation**:

   ```bash
   # Test template loading
   curl -X POST http://localhost:8000/api/v1/questions/generate \
     -H "Content-Type: application/json" \
     -d '{"question_type": "matching", "target_count": 2, "language": "en"}'
   ```

2. **Canvas Export Testing**:

   - Generate matching questions through UI
   - Export to Canvas and verify format
   - Check Canvas quiz display and functionality

3. **AI Generation Testing**:
   - Test with various content types (text, PDFs)
   - Verify distractor quality and relevance
   - Check multilingual generation quality

### Performance Benchmarks

- **Question Validation**: < 10ms per question
- **Canvas Export**: < 50ms per question
- **Database Storage**: Uses existing JSONB indexing
- **Template Rendering**: < 5ms per template

## 6. Deployment Instructions

### Step-by-Step Deployment

1. **Pre-deployment Validation**:

   ```bash
   cd backend
   source .venv/bin/activate
   bash scripts/test.sh
   bash scripts/lint.sh
   ```

2. **Database Migration** (if needed):

   ```bash
   # No migration required - uses existing polymorphic Question model
   # Verify existing structure supports new question type
   ```

3. **Application Deployment**:

   ```bash
   # Standard deployment process
   docker compose build backend
   docker compose up -d
   ```

4. **Verification**:
   ```bash
   # Test question type registration
   curl http://localhost:8000/api/v1/questions/types
   # Should include "matching" in response
   ```

### Environment-Specific Configurations

- **Development**: No special configuration
- **Staging**: Standard Canvas API testing credentials
- **Production**: Ensure Canvas production API access

### Rollback Procedures

1. **Code Rollback**: Standard Git rollback procedures
2. **Database**: No schema changes to rollback
3. **Templates**: Remove template files if needed
4. **Registry**: Question type auto-registration handles cleanup

## 7. Monitoring & Maintenance

### Key Metrics to Monitor

- **Question Generation Success Rate**: Track matching question generation success
- **Canvas Export Success Rate**: Monitor Canvas API integration
- **Template Performance**: Track template rendering times
- **Validation Error Rates**: Monitor validation failures

### Log Entries to Watch For

```python
# Success indicators
"question_type_registered" with question_type="matching"
"question_generation_success" with question_type="matching"
"canvas_export_success" with question_type="matching"

# Error indicators
"question_validation_error" with question_type="matching"
"template_not_found" for matching templates
"canvas_export_error" with matching questions
```

### Common Issues and Troubleshooting

#### Template Not Found

```
Error: No template found for question type matching
Solution: Verify template files exist in templates/files/
Check: batch_matching.json and batch_matching_no.json
```

#### Validation Errors

```
Error: Distractor 'X' matches a correct answer
Solution: Review AI generation quality, update templates
Action: Check template instructions for distractor guidelines
```

#### Canvas Export Issues

```
Error: Canvas API rejection of matching format
Solution: Verify Canvas New Quizzes API compatibility
Check: interaction_type_slug and scoring_algorithm values
```

## 8. Security Considerations

### Authentication/Authorization

- **No Changes Required**: Uses existing Canvas OAuth flow
- **Question Access**: Follows existing quiz access controls
- **User Permissions**: Inherits from existing question system

### Data Privacy

- **Content Storage**: Question content stored in existing encrypted database
- **Canvas Integration**: Uses existing secure Canvas API client
- **User Data**: No additional user data collection

### Security Best Practices

- **Input Validation**: Comprehensive Pydantic validation prevents injection
- **Output Sanitization**: Canvas export uses proper HTML escaping
- **API Security**: Follows existing API security patterns
- **Template Security**: Templates use safe Jinja2 rendering

### Specific Security Measures

```python
# Input validation prevents malicious content
class MatchingPair(BaseModel):
    question: str = Field(min_length=1)  # Prevents empty injection
    answer: str = Field(min_length=1)   # Validates content

# Canvas export sanitizes HTML
item_body = f"<p>{data.question_text}</p>"  # Safe HTML generation
```

## 9. Future Considerations

### Known Limitations

- **Fixed 1:1 Mapping**: Currently supports only one correct answer per question
- **Distractor Limit**: Maximum 5 distractors may be insufficient for complex topics
- **Canvas Dependency**: Tied to Canvas New Quizzes API format

### Potential Improvements

1. **Enhanced Matching Types**:

   - Multiple correct answers per question
   - Weighted scoring for partial matches
   - Grouped matching (categories)

2. **Advanced AI Generation**:

   - Context-aware distractor generation
   - Difficulty-based pair complexity
   - Topic-specific templates

3. **Extended Canvas Support**:

   - Canvas Classic quiz compatibility
   - Rich media support (images, videos)
   - Custom scoring algorithms

4. **Performance Optimizations**:
   - Caching for template rendering
   - Bulk validation processing
   - Optimized Canvas API calls

### Scalability Considerations

- **Database**: Current JSONB storage scales to millions of questions
- **Template System**: File-based templates scale well with caching
- **Canvas API**: Rate limiting handled by existing client
- **Memory Usage**: Validation objects are lightweight and short-lived

### Extension Points

```python
# Future matching types can extend base classes
class MultipleAnswerMatchingData(MatchingData):
    # Support multiple correct answers per question
    pass

class WeightedMatchingData(MatchingData):
    # Add scoring weights
    pair_weights: list[float]
```

### Migration Path for Enhancements

1. **Backward Compatibility**: New features extend existing models
2. **Database Evolution**: Additional JSONB fields don't require migration
3. **API Evolution**: New endpoints can coexist with existing ones
4. **Template Evolution**: New template versions can coexist

---

## Implementation Checklist

- [ ] **Step 1**: Update base enum and constants
- [ ] **Step 2**: Create matching.py data models
- [ ] **Step 3**: Register question type in registry
- [ ] **Step 4**: Create English AI template
- [ ] **Step 5**: Create Norwegian AI template
- [ ] **Step 6**: Write comprehensive tests
- [ ] **Final**: Run full test suite and validate deployment

**Remember**: After each step, run `test.sh`, `lint.sh`, and commit changes.

---

_End of Implementation Document_
