# True/False Question Type Implementation Guide

**Document Date**: January 30, 2025
**Feature**: True/False Question Type Support
**Target System**: Rag@UiT Canvas LMS Quiz Generator

## 1. Feature Overview

### What It Does

The True/False question type allows instructors to create quiz questions where students must determine whether a given statement is true or false. This question type supports:

- **Binary Choice**: Simple true/false responses with boolean validation
- **Canvas Integration**: Direct export to Canvas LMS New Quizzes format
- **AI Generation**: Automated question creation from course content with balanced distribution
- **Multilingual Support**: Both English and Norwegian question generation
- **Comprehensive Validation**: Ensures data integrity and Canvas compatibility

### Business Value

- **Enhanced Question Variety**: Expands beyond Multiple Choice, Fill-in-Blank, and Matching types
- **Effective Assessment**: Tests factual knowledge and conceptual understanding
- **Canvas Compatible**: Seamless integration with existing Canvas LMS workflows
- **Time Saving**: AI-powered generation reduces manual question creation effort
- **Educational Flexibility**: Suitable for testing definitions, facts, and basic concepts

### User Benefits

- Instructors can create fact-based assessments automatically from course materials
- Students get clear, unambiguous questions that test foundational knowledge
- Questions are directly exported to Canvas without manual reformatting
- Balanced true/false distribution ensures fair assessment

## 2. Technical Architecture

### High-Level Architecture

The True/False question type follows Rag@UiT's established polymorphic question architecture:

```
Question Generation Pipeline:
Course Content → AI Templates → Question Data → Canvas Export

Architecture Components:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Templates  │    │   Data Models    │    │  Canvas Export  │
│  (English/NO)   │───▶│  TrueFalseData   │───▶│  New Quiz API   │
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
Raw AI Response → validate_data() → TrueFalseData → format_for_canvas() → Canvas API
```

## 3. Dependencies & Prerequisites

### External Dependencies

- **Existing**: All dependencies already in project
  - `pydantic`: Data validation and serialization
  - `sqlmodel`: Database ORM
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
│   │   ├── base.py                    # ← UPDATE: Add TRUE_FALSE enum
│   │   ├── true_false.py              # ← CREATE: New implementation
│   │   └── registry.py                # ← UPDATE: Register new type
│   └── templates/
│       └── files/
│           ├── batch_true_false.json    # ← CREATE: English template
│           └── batch_true_false_no.json # ← CREATE: Norwegian template
├── canvas/
│   └── constants.py                   # ← UPDATE: Add Canvas constants
└── tests/
    └── question/
        └── types/
            └── test_true_false.py     # ← CREATE: Comprehensive tests
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
    MATCHING = "matching"
    CATEGORIZATION = "categorization"
    TRUE_FALSE = "true_false"  # ← ADD THIS LINE
```

**File**: `backend/src/canvas/constants.py`

**Changes**:

```python
class CanvasInteractionType:
    """Canvas New Quizzes API interaction types."""

    CHOICE = "choice"  # Multiple choice questions
    RICH_FILL_BLANK = "rich-fill-blank"  # Fill-in-blank questions
    MATCHING = "matching"  # Matching questions
    CATEGORIZATION = "categorization"  # Categorization questions
    TRUE_FALSE = "true-false"  # ← ADD THIS LINE (True/False questions)
```

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add TRUE_FALSE question type constants"`

#### Step 2: Create Data Models

**File**: `backend/src/question/types/true_false.py` (NEW FILE)

**Complete Implementation**:

```python
"""True/False Question type implementation."""

from typing import Any

from pydantic import Field

from src.canvas.constants import CanvasInteractionType, CanvasScoringAlgorithm

from .base import (
    BaseQuestionData,
    BaseQuestionType,
    QuestionType,
    generate_canvas_title,
)


class TrueFalseData(BaseQuestionData):
    """Data model for true/false questions."""

    correct_answer: bool = Field(
        description="Whether the statement is true (True) or false (False)"
    )


class TrueFalseQuestionType(BaseQuestionType):
    """Implementation for true/false questions."""

    @property
    def question_type(self) -> QuestionType:
        """Return the question type enum."""
        return QuestionType.TRUE_FALSE

    @property
    def data_model(self) -> type[TrueFalseData]:
        """Return the data model class for True/False."""
        return TrueFalseData

    def validate_data(self, data: dict[str, Any]) -> TrueFalseData:
        """
        Validate and parse True/False data.

        Args:
            data: Raw question data dictionary

        Returns:
            Validated True/False data

        Raises:
            ValidationError: If data is invalid
        """
        return TrueFalseData(**data)

    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format True/False data for API display.

        Args:
            data: Validated True/False data

        Returns:
            Dictionary formatted for frontend display
        """
        if not isinstance(data, TrueFalseData):
            raise ValueError("Expected TrueFalseData")

        return {
            "question_text": data.question_text,
            "correct_answer": data.correct_answer,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format True/False data for Canvas New Quizzes export.

        Args:
            data: Validated True/False data

        Returns:
            Dictionary formatted for Canvas New Quizzes API
        """
        if not isinstance(data, TrueFalseData):
            raise ValueError("Expected TrueFalseData")

        # Wrap question text in paragraph tag if not already wrapped
        item_body = data.question_text
        if not item_body.strip().startswith("<p>"):
            item_body = f"<p>{item_body}</p>"

        return {
            "title": generate_canvas_title(data.question_text),
            "item_body": item_body,
            "calculator_type": "none",
            "interaction_data": {
                "true_choice": "True",
                "false_choice": "False",
            },
            "properties": {},
            "scoring_data": {"value": data.correct_answer},
            "answer_feedback": {},
            "scoring_algorithm": CanvasScoringAlgorithm.EQUIVALENCE,
            "interaction_type_slug": CanvasInteractionType.TRUE_FALSE,
            "feedback": {},
            "points_possible": 1,
        }

    def format_for_export(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format True/False data for generic export.

        Args:
            data: Validated True/False data

        Returns:
            Dictionary with True/False data for export
        """
        if not isinstance(data, TrueFalseData):
            raise ValueError("Expected TrueFalseData")

        return {
            "question_text": data.question_text,
            "correct_answer": data.correct_answer,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }
```

**Code Explanation**:

- `TrueFalseData`: Simple model extending `BaseQuestionData` with a boolean `correct_answer` field
- `TrueFalseQuestionType`: Complete implementation of all abstract methods
- Canvas export uses "true-false" interaction type with boolean scoring
- Validation ensures correct_answer is a proper boolean value

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add TrueFalseData model and TrueFalseQuestionType implementation"`

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
        from .categorization import CategorizationQuestionType
        from .fill_in_blank import FillInBlankQuestionType
        from .matching import MatchingQuestionType
        from .mcq import MultipleChoiceQuestionType
        from .true_false import TrueFalseQuestionType  # ← ADD THIS IMPORT

        self.register_question_type(
            QuestionType.MULTIPLE_CHOICE, MultipleChoiceQuestionType()
        )
        self.register_question_type(
            QuestionType.FILL_IN_BLANK, FillInBlankQuestionType()
        )
        self.register_question_type(QuestionType.MATCHING, MatchingQuestionType())
        self.register_question_type(
            QuestionType.CATEGORIZATION, CategorizationQuestionType()
        )
        self.register_question_type(  # ← ADD THIS REGISTRATION
            QuestionType.TRUE_FALSE, TrueFalseQuestionType()
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
3. Commit changes: `git add -A && git commit -m "feat: register True/False question type in registry"`

#### Step 4: Create English AI Template

**File**: `backend/src/question/templates/files/batch_true_false.json` (NEW FILE)

**Complete Template**:

```json
{
  "name": "batch_true_false",
  "version": "1.0",
  "question_type": "true_false",
  "description": "Template for generating True/False questions from module content",
  "system_prompt": "You are an expert educator creating true/false quiz questions. Generate high-quality questions that test factual knowledge and understanding of key concepts.\n\nIMPORTANT REQUIREMENTS:\n1. Generate EXACTLY {{ question_count }} true/false questions\n2. Ensure BALANCED distribution: approximately 50% true and 50% false statements\n3. Focus on FACTUAL statements that are clearly true or false (avoid ambiguous or opinion-based statements)\n4. Create meaningful questions that test important concepts from the content\n5. Avoid trivial facts that don't contribute to learning\n6. Include clear explanations for why each statement is true or false\n7. Vary the difficulty levels and topics covered\n\nQUESTION GUIDELINES:\n- **True statements**: Should be accurate, verifiable facts from the content\n- **False statements**: Should contain clear factual errors, not subtle ambiguities\n- **Avoid**: Opinions, subjective statements, trick questions, or overly complex statements\n- **Focus on**: Key concepts, definitions, processes, relationships, and important facts\n\nReturn your response as a valid JSON array with exactly {{ question_count }} question objects.\n\nEach question object must have this exact structure:\n{\n    \"question_text\": \"Python is a programming language.\",\n    \"correct_answer\": true,\n    \"explanation\": \"Python is indeed a high-level, interpreted programming language.\"\n}\n\nIMPORTANT:\n- Return ONLY a valid JSON array\n- No markdown code blocks (```json or ```)\n- No explanatory text before or after the JSON\n- Use boolean values: true or false (not strings \"true\"/\"false\")\n- Ensure roughly equal numbers of true and false questions\n- The array must contain exactly {{ question_count }} question objects\n- Each statement should be clear and unambiguous",
  "user_prompt": "Based on the following content from the module '{{ module_name }}', generate exactly {{ question_count }} true/false questions.\n\nMODULE CONTENT:\n{{ module_content }}\n\nGenerate exactly {{ question_count }} questions with balanced true/false distribution:",
  "variables": {
    "module_name": "The name of the module",
    "module_content": "The module content to generate questions from",
    "question_count": "Number of questions to generate",
    "difficulty": "Question difficulty level (optional)",
    "tags": "List of topic tags to focus on (optional)",
    "custom_instructions": "Additional custom instructions (optional)"
  },
  "author": "System",
  "tags": [
    "batch",
    "true_false",
    "module"
  ],
  "created_at": null,
  "updated_at": null,
  "min_content_length": 100,
  "max_content_length": 50000
}
```

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add English AI template for True/False questions"`

#### Step 5: Create Norwegian AI Template

**File**: `backend/src/question/templates/files/batch_true_false_no.json` (NEW FILE)

**Complete Template**:

```json
{
  "name": "batch_true_false_no",
  "version": "1.0",
  "question_type": "true_false",
  "language": "no",
  "description": "Mal for generering av sant/usant spørsmål fra modulinnhold",
  "system_prompt": "Du er en ekspert pedagog som lager sant/usant quiz-spørsmål. Generer høykvalitets spørsmål som tester faktakunnskap og forståelse av nøkkelkonsepter.\n\nVIKTIGE KRAV:\n1. Generer NØYAKTIG {{ question_count }} sant/usant spørsmål\n2. Sørg for BALANSERT fordeling: omtrent 50% sanne og 50% usanne påstander\n3. Fokuser på FAKTUELLE påstander som er klart sanne eller usanne (unngå tvetydige eller meningsbaserte påstander)\n4. Lag meningsfulle spørsmål som tester viktige konsepter fra innholdet\n5. Unngå trivielle fakta som ikke bidrar til læring\n6. Inkluder klare forklaringer på hvorfor hver påstand er sann eller usann\n7. Varier vanskegrad og emner som dekkes\n\nSPØRSMÅLSRETNINGSLINJER:\n- **Sanne påstander**: Bør være nøyaktige, verifiserbare fakta fra innholdet\n- **Usanne påstander**: Bør inneholde klare faktafeil, ikke subtile tvetydigheter\n- **Unngå**: Meninger, subjektive påstander, lurerspørsmål eller altfor komplekse påstander\n- **Fokuser på**: Nøkkelkonsepter, definisjoner, prosesser, sammenhenger og viktige fakta\n\nReturnér svaret ditt som en gyldig JSON-array med nøyaktig {{ question_count }} spørsmålsobjekter.\n\nHvert spørsmålsobjekt må ha denne nøyaktige strukturen:\n{\n    \"question_text\": \"Python er et programmeringsspråk.\",\n    \"correct_answer\": true,\n    \"explanation\": \"Python er faktisk et høynivå, tolket programmeringsspråk.\"\n}\n\nVIKTIG:\n- Returnér KUN en gyldig JSON-array\n- Ingen markdown-kodeblokker (```json eller ```)\n- Ingen forklarende tekst før eller etter JSON\n- Bruk boolske verdier: true eller false (ikke strenger \"true\"/\"false\")\n- Sørg for omtrent like mange sanne og usanne spørsmål\n- Arrayen må inneholde nøyaktig {{ question_count }} spørsmålsobjekter\n- Hver påstand bør være klar og utvetydig",
  "user_prompt": "Basert på følgende innhold fra modulen '{{ module_name }}', generer nøyaktig {{ question_count }} sant/usant spørsmål.\n\nMODULINNHOLD:\n{{ module_content }}\n\nGenerer nøyaktig {{ question_count }} spørsmål med balansert sant/usant fordeling:",
  "variables": {
    "module_name": "Navnet på modulen",
    "module_content": "Modulinnholdet å generere spørsmål fra",
    "question_count": "Antall spørsmål å generere",
    "difficulty": "Spørsmålsvanskegrad (valgfritt)",
    "tags": "Liste over emnetagg å fokusere på (valgfritt)",
    "custom_instructions": "Ytterligere tilpassede instruksjoner (valgfritt)"
  },
  "author": "System",
  "tags": [
    "batch",
    "true_false",
    "module",
    "norsk"
  ],
  "created_at": null,
  "updated_at": null,
  "min_content_length": 100,
  "max_content_length": 50000
}
```

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add Norwegian AI template for True/False questions"`

#### Step 6: Create Comprehensive Tests

**File**: `backend/tests/question/types/test_true_false.py` (NEW FILE)

**Complete Test Suite** (sample tests - full version is 559 lines):

```python
"""Tests for True/False question type implementation."""

import pytest


def test_true_false_data_creation_true():
    """Test creating valid true/false data with correct_answer=True."""
    from src.question.types.true_false import TrueFalseData

    data = TrueFalseData(
        question_text="Python is a programming language.",
        correct_answer=True,
        explanation="Python is indeed a high-level programming language."
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
        explanation="Python was actually first released in 1991."
    )
    assert data.question_text == "Python was invented in 1995."
    assert data.correct_answer is False
    assert data.explanation == "Python was actually first released in 1991."


def test_true_false_data_empty_question_text_validation():
    """Test that empty question text fails validation."""
    from pydantic import ValidationError

    from src.question.types.true_false import TrueFalseData

    with pytest.raises(ValidationError) as exc_info:
        TrueFalseData(question_text="", correct_answer=True)
    assert "String should have at least 1 character" in str(exc_info.value)


def test_true_false_question_type_format_for_canvas_true():
    """Test Canvas export formatting with True answer."""
    from src.question.types.true_false import TrueFalseQuestionType

    question_type = TrueFalseQuestionType()
    data = {
        "question_text": "Python is an interpreted language.",
        "correct_answer": True,
        "explanation": "Python code is executed line by line by an interpreter."
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
        "false_choice": "False"
    }

    # Validate scoring_data
    assert result["scoring_data"] == {"value": True}


def test_true_false_end_to_end_workflow_true():
    """Test complete workflow from raw data to Canvas export (True answer)."""
    from src.question.types import QuestionType, get_question_type_registry

    # Raw AI response data
    raw_data = {
        "question_text": "Machine learning is a subset of artificial intelligence.",
        "correct_answer": True,
        "explanation": "Machine learning is indeed a subset of AI that enables computers to learn without explicit programming."
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

# ... 27 more test functions covering all aspects
```

**Testing**: After this step:

1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add comprehensive test suite for True/False question type"`

### 4.3 Data Models & Schemas

#### Core Data Structures

**TrueFalseData Model**:

```python
class TrueFalseData(BaseQuestionData):
    correct_answer: bool  # Required boolean field
    # Inherits: question_text (str), explanation (str | None)
```

#### Validation Rules

- **question_text**: Required, 1-2000 characters
- **correct_answer**: Required, must be boolean (true/false)
- **explanation**: Optional, max 1000 characters
- **Extra fields**: Forbidden (Pydantic strict mode)

#### Example Data

```json
{
  "question_text": "Python is a programming language.",
  "correct_answer": true,
  "explanation": "Python is indeed a high-level, interpreted programming language."
}
```

#### Canvas Export Format

```json
{
    "title": "Question Python is a programming language...",
    "item_body": "<p>Python is a programming language.</p>",
    "calculator_type": "none",
    "interaction_data": {
        "true_choice": "True",
        "false_choice": "False"
    },
    "properties": {},
    "scoring_data": {"value": true},
    "answer_feedback": {},
    "scoring_algorithm": "Equivalence",
    "interaction_type_slug": "true-false",
    "feedback": {},
    "points_possible": 1
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

### Unit Tests (32 tests total)

- **TrueFalseData Tests (9)**: Basic creation, validation, edge cases
- **TrueFalseQuestionType Tests (15)**: All interface methods, error handling
- **Registry Tests (3)**: Registration, retrieval, availability
- **End-to-End Tests (5)**: Complete workflows, data consistency

### Test Coverage Areas

1. **Data Model Validation**
   - Valid true/false data creation
   - Validation of required fields
   - Field length limits
   - Type validation (boolean enforcement)

2. **Question Type Implementation**
   - All abstract method implementations
   - Data formatting for display, Canvas, and export
   - Error handling for wrong data types

3. **Canvas Integration**
   - Proper Canvas API format
   - HTML wrapping behavior
   - Scoring data structure

4. **Registry Integration**
   - Type registration verification
   - Dynamic discovery functionality

### Manual Testing Steps

1. **Template Validation**:
   ```bash
   # Test template loading
   curl -X POST http://localhost:8000/api/v1/questions/generate \
     -H "Content-Type: application/json" \
     -d '{"question_type": "true_false", "target_count": 2, "language": "en"}'
   ```

2. **Canvas Export Testing**:
   - Generate True/False questions through UI
   - Export to Canvas and verify format
   - Check Canvas quiz display and functionality

3. **AI Generation Testing**:
   - Test with various content types (text, PDFs)
   - Verify balanced true/false distribution
   - Check multilingual generation quality

### Performance Benchmarks

- **Question Validation**: < 5ms per question
- **Canvas Export**: < 20ms per question
- **Database Storage**: Uses existing JSONB indexing
- **Template Rendering**: < 3ms per template

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
   # Should include "true_false" in response
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

- **Question Generation Success Rate**: Track True/False question generation success
- **Canvas Export Success Rate**: Monitor Canvas API integration
- **Template Performance**: Track template rendering times
- **Validation Error Rates**: Monitor validation failures

### Log Entries to Watch For

```python
# Success indicators
"question_type_registered" with question_type="true_false"
"question_generation_success" with question_type="true_false"
"canvas_export_success" with question_type="true_false"

# Error indicators
"question_validation_error" with question_type="true_false"
"template_not_found" for true_false templates
"canvas_export_error" with true_false questions
```

### Common Issues and Troubleshooting

#### Template Not Found

```
Error: No template found for question type true_false
Solution: Verify template files exist in templates/files/
Check: batch_true_false.json and batch_true_false_no.json
```

#### Validation Errors

```
Error: Input should be a valid boolean
Solution: Ensure AI generates proper boolean values, not strings
Action: Check template instructions for boolean formatting
```

#### Canvas Export Issues

```
Error: Canvas API rejection of true-false format
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
class TrueFalseData(BaseQuestionData):
    correct_answer: bool = Field(description="...")  # Type enforcement

# Canvas export sanitizes HTML
item_body = f"<p>{data.question_text}</p>"  # Safe HTML generation
```

## 9. Future Considerations

### Known Limitations

- **Binary Choice Only**: Currently supports only true/false, not multiple true/false variations
- **Simple Scoring**: No partial credit or weighted scoring options
- **Canvas Dependency**: Tied to Canvas New Quizzes API format

### Potential Improvements

1. **Enhanced Question Types**:
   - True/False with multiple statements
   - Confidence-based scoring
   - Certainty indicators

2. **Advanced AI Generation**:
   - Context-aware difficulty adjustment
   - Topic-specific balanced generation
   - Fact-checking integration

3. **Extended Canvas Support**:
   - Canvas Classic quiz compatibility
   - Rich media support (images, videos)
   - Custom feedback per choice

4. **Performance Optimizations**:
   - Caching for frequent validations
   - Batch processing for large generations
   - Optimized Canvas API calls

### Scalability Considerations

- **Database**: Current JSONB storage scales to millions of questions
- **Template System**: File-based templates scale well with caching
- **Canvas API**: Rate limiting handled by existing client
- **Memory Usage**: Validation objects are lightweight and short-lived

### Extension Points

```python
# Future true/false variations can extend base classes
class MultipleTrueFalseData(BaseQuestionData):
    # Support multiple true/false statements
    statements: list[TrueFalseStatement]

class WeightedTrueFalseData(TrueFalseData):
    # Add confidence scoring
    confidence_weight: float
```

### Migration Path for Enhancements

1. **Backward Compatibility**: New features extend existing models
2. **Database Evolution**: Additional JSONB fields don't require migration
3. **API Evolution**: New endpoints can coexist with existing ones
4. **Template Evolution**: New template versions can coexist

---

## Implementation Checklist

- [x] **Step 1**: Update base enum and constants
- [x] **Step 2**: Create true_false.py data models
- [x] **Step 3**: Register question type in registry
- [x] **Step 4**: Create English AI template
- [x] **Step 5**: Create Norwegian AI template
- [x] **Step 6**: Write comprehensive tests
- [x] **Final**: Run full test suite and validate deployment

**Remember**: After each step, run `test.sh`, `lint.sh`, and commit changes.

---

_End of Implementation Document_
