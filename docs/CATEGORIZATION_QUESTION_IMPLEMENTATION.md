# Categorization Question Type Implementation Guide

**Document Date**: January 23, 2025
**Feature**: Categorization Question Type Support
**Target System**: Rag@UiT Canvas LMS Quiz Generator

## 1. Feature Overview

### What It Does

The Categorization question type allows instructors to create quiz questions where students categorize items by dragging and dropping them into appropriate categories. This question type supports:

- **Multiple Categories**: Create 2-8 categories (e.g., "Mammals", "Reptiles", "Birds")
- **Drag-and-Drop Items**: 6-20 items that students categorize (e.g., "Dolphin", "Snake", "Eagle")
- **Distractors**: Optional incorrect items that don't belong in any category
- **Canvas Integration**: Direct export to Canvas LMS New Quizzes format
- **AI Generation**: Automated question creation from course content
- **Multilingual Support**: Both English and Norwegian question generation

### Business Value

- **Enhanced Question Variety**: Expands beyond Multiple Choice, Fill-in-Blank, and Matching
- **Effective Assessment**: Tests associative knowledge and conceptual understanding
- **Canvas Compatible**: Seamless integration with existing Canvas LMS workflows
- **Time Saving**: AI-powered generation reduces manual question creation time
- **Student Engagement**: Interactive drag-and-drop interface improves user experience

### User Benefits

- Instructors can create engaging categorization exercises automatically
- Students get diverse question types that test different cognitive skills
- Questions are directly exported to Canvas without manual reformatting
- Support for complex taxonomies and classification systems

## 2. Technical Architecture

### High-Level Architecture

The Categorization question type follows Rag@UiT's established polymorphic question architecture:

```
Question Generation Pipeline:
Course Content → AI Templates → Question Data → Canvas Export

Architecture Components:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Templates  │    │   Data Models    │    │  Canvas Export  │
│  (English/NO)   │───▶│ CategorizationD. │───▶│  New Quiz API   │
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
Raw AI Response → validate_data() → CategorizationData → format_for_canvas() → Canvas API
```

## 3. Dependencies & Prerequisites

### External Dependencies

- **Existing**: All dependencies already in project
  - `pydantic`: Data validation and serialization (v2.0+)
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
│   │   ├── base.py                        # ← UPDATE: Add CATEGORIZATION enum
│   │   ├── categorization.py              # ← CREATE: New implementation
│   │   └── registry.py                    # ← UPDATE: Register new type
│   └── templates/
│       └── files/
│           ├── batch_categorization.json    # ← CREATE: English template
│           └── batch_categorization_no.json # ← CREATE: Norwegian template
├── canvas/
│   └── constants.py                       # ← UPDATE: Add Canvas constants
└── tests/
    └── question/
        └── types/
            └── test_categorization.py      # ← CREATE: Comprehensive tests
```

### 4.2 Step-by-Step Implementation

#### Step 1: Update Base Constants and Enums

**File**: `backend/src/question/types/base.py`

**Changes**: Add CATEGORIZATION to the QuestionType enum

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
    CATEGORIZATION = "categorization"  # ← ADD THIS LINE
```

**File**: `backend/src/canvas/constants.py`

**Changes**: Add Canvas interaction type constant

```python
class CanvasInteractionType:
    """Canvas New Quizzes API interaction types."""

    CHOICE = "choice"  # Multiple choice questions
    RICH_FILL_BLANK = "rich-fill-blank"  # Fill-in-blank questions
    MATCHING = "matching"  # Matching questions
    CATEGORIZATION = "categorization"  # ← ADD THIS LINE (categorization questions)
```

**Testing**: After this step:
1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add categorization question type constants"`

#### Step 2: Create Data Models and Implementation

**File**: `backend/src/question/types/categorization.py` (NEW FILE)

**Complete Implementation**:

```python
"""Categorization Question type implementation."""

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


class CategoryItem(BaseModel):
    """Data model for a single item that can be categorized."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the item"
    )
    text: str = Field(
        min_length=1,
        max_length=200,
        description="The text content of the item to be categorized"
    )


class Category(BaseModel):
    """Data model for a category that items can be placed into."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the category"
    )
    name: str = Field(
        min_length=1,
        max_length=100,
        description="The name/label of the category"
    )
    correct_items: list[str] = Field(
        min_length=1,
        max_length=10,
        description="List of item IDs that belong in this category"
    )

    @field_validator("correct_items")
    @classmethod
    def validate_correct_items(cls, v: list[str]) -> list[str]:
        """Validate that correct_items is not empty."""
        if not v:
            raise ValueError("Each category must have at least one correct item")
        return v


class CategorizationData(BaseQuestionData):
    """Data model for categorization questions."""

    categories: list[Category] = Field(
        min_length=2,
        max_length=8,
        description="List of categories (2-8 categories)"
    )
    items: list[CategoryItem] = Field(
        min_length=6,
        max_length=20,
        description="List of items to be categorized (6-20 items)"
    )
    distractors: list[CategoryItem] | None = Field(
        default=None,
        max_length=5,
        description="Optional distractor items that don't belong in any category"
    )

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[Category]) -> list[Category]:
        """Validate categories have unique names and IDs."""
        if len(v) < 2:
            raise ValueError("At least 2 categories are required")
        if len(v) > 8:
            raise ValueError("Maximum 8 categories allowed")

        # Check for duplicate category names (case-insensitive)
        names = [cat.name.strip().lower() for cat in v]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate category names are not allowed")

        # Check for duplicate category IDs
        ids = [cat.id for cat in v]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate category IDs are not allowed")

        return v

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: list[CategoryItem]) -> list[CategoryItem]:
        """Validate items have unique texts and IDs."""
        if len(v) < 6:
            raise ValueError("At least 6 items are required")
        if len(v) > 20:
            raise ValueError("Maximum 20 items allowed")

        # Check for duplicate item texts (case-insensitive)
        texts = [item.text.strip().lower() for item in v]
        if len(set(texts)) != len(texts):
            raise ValueError("Duplicate item texts are not allowed")

        # Check for duplicate item IDs
        ids = [item.id for item in v]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate item IDs are not allowed")

        return v

    @field_validator("distractors")
    @classmethod
    def validate_distractors(cls, v: list[CategoryItem] | None) -> list[CategoryItem] | None:
        """Validate distractors and ensure no duplicates."""
        if v is None:
            return v

        if len(v) > 5:
            raise ValueError("Maximum 5 distractors allowed")

        # Check for duplicate distractor texts (case-insensitive)
        texts = [item.text.strip().lower() for item in v]
        if len(set(texts)) != len(texts):
            raise ValueError("Duplicate distractor texts are not allowed")

        # Check for duplicate distractor IDs
        ids = [item.id for item in v]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate distractor IDs are not allowed")

        return v

    def validate_item_assignments(self) -> None:
        """Validate that all referenced items exist and assignments are valid."""
        # Get all item IDs
        all_item_ids = {item.id for item in self.items}
        if self.distractors:
            all_item_ids.update(item.id for item in self.distractors)

        # Check that all correct_items references exist
        for category in self.categories:
            for item_id in category.correct_items:
                if item_id not in all_item_ids:
                    raise ValueError(
                        f"Category '{category.name}' references non-existent item ID: {item_id}"
                    )

        # Check that each item is assigned to exactly one category
        assigned_items = set()
        for category in self.categories:
            for item_id in category.correct_items:
                if item_id in assigned_items:
                    raise ValueError(
                        f"Item ID {item_id} is assigned to multiple categories"
                    )
                assigned_items.add(item_id)

        # Ensure all non-distractor items are assigned to a category
        main_item_ids = {item.id for item in self.items}
        unassigned_items = main_item_ids - assigned_items
        if unassigned_items:
            raise ValueError(
                f"Items not assigned to any category: {list(unassigned_items)}"
            )

    def get_all_items(self) -> list[CategoryItem]:
        """Get all items including distractors for display."""
        all_items = self.items.copy()
        if self.distractors:
            all_items.extend(self.distractors)
        return all_items

    def get_category_by_id(self, category_id: str) -> Category | None:
        """Get a category by its ID."""
        for category in self.categories:
            if category.id == category_id:
                return category
        return None

    def get_item_by_id(self, item_id: str) -> CategoryItem | None:
        """Get an item by its ID (including distractors)."""
        all_items = self.get_all_items()
        for item in all_items:
            if item.id == item_id:
                return item
        return None


class CategorizationQuestionType(BaseQuestionType):
    """Implementation for categorization questions."""

    @property
    def question_type(self) -> QuestionType:
        """Return the question type enum."""
        return QuestionType.CATEGORIZATION

    @property
    def data_model(self) -> type[CategorizationData]:
        """Return the data model class for categorization."""
        return CategorizationData

    def validate_data(self, data: dict[str, Any]) -> CategorizationData:
        """
        Validate and parse categorization data.

        Args:
            data: Raw question data dictionary

        Returns:
            Validated categorization data

        Raises:
            ValidationError: If data is invalid
        """
        categorization_data = CategorizationData(**data)
        # Additional validation for business logic
        categorization_data.validate_item_assignments()
        return categorization_data

    def format_for_display(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format categorization data for API display.

        Args:
            data: Validated categorization data

        Returns:
            Dictionary formatted for frontend display
        """
        if not isinstance(data, CategorizationData):
            raise ValueError("Expected CategorizationData")

        # Convert Category and CategoryItem objects to dictionaries for frontend
        categories_dict = [
            {
                "id": cat.id,
                "name": cat.name,
                "correct_items": cat.correct_items,
            }
            for cat in data.categories
        ]

        items_dict = [
            {"id": item.id, "text": item.text}
            for item in data.items
        ]

        result = {
            "question_text": data.question_text,
            "categories": categories_dict,
            "items": items_dict,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

        if data.distractors:
            result["distractors"] = [
                {"id": item.id, "text": item.text}
                for item in data.distractors
            ]

        return result

    def format_for_canvas(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format categorization data for Canvas New Quizzes export.

        Args:
            data: Validated categorization data

        Returns:
            Dictionary formatted for Canvas New Quizzes API
        """
        if not isinstance(data, CategorizationData):
            raise ValueError("Expected CategorizationData")

        # Build categories dictionary for Canvas
        canvas_categories = {}
        for category in data.categories:
            canvas_categories[category.id] = {
                "id": category.id,
                "item_body": category.name,
            }

        # Build distractors dictionary (all items not belonging to any category)
        canvas_distractors = {}
        all_items = data.get_all_items()

        for item in all_items:
            canvas_distractors[item.id] = {
                "id": item.id,
                "item_body": item.text,
            }

        # Build category order (for consistent display)
        category_order = [cat.id for cat in data.categories]

        # Build scoring data (which items belong to which categories)
        scoring_value = []
        for category in data.categories:
            scoring_value.append({
                "id": category.id,
                "scoring_data": {
                    "value": category.correct_items,
                    "scoring_algorithm": "AllOrNothing"
                }
            })

        # Wrap question text in paragraph tag if not already wrapped
        item_body = data.question_text
        if not item_body.strip().startswith("<p>"):
            item_body = f"<p>{item_body}</p>"

        # Calculate points (typically 1 point per category)
        points_possible = len(data.categories)

        return {
            "title": generate_canvas_title(data.question_text),
            "item_body": item_body,
            "calculator_type": "none",
            "interaction_data": {
                "categories": canvas_categories,
                "distractors": canvas_distractors,
                "category_order": category_order,
            },
            "properties": {
                "shuffle_rules": {
                    "questions": {"shuffled": False}
                }
            },
            "scoring_data": {
                "value": scoring_value,
                "score_method": "all_or_nothing",
            },
            "answer_feedback": {},
            "scoring_algorithm": CanvasScoringAlgorithm.PARTIAL_DEEP,
            "interaction_type_slug": CanvasInteractionType.CATEGORIZATION,
            "feedback": {},
            "points_possible": points_possible,
        }

    def format_for_export(self, data: BaseQuestionData) -> dict[str, Any]:
        """
        Format categorization data for generic export.

        Args:
            data: Validated categorization data

        Returns:
            Dictionary with categorization data for export
        """
        if not isinstance(data, CategorizationData):
            raise ValueError("Expected CategorizationData")

        # Convert to simple dict format for export
        categories_data = [
            {
                "id": cat.id,
                "name": cat.name,
                "correct_items": cat.correct_items,
            }
            for cat in data.categories
        ]

        items_data = [
            {"id": item.id, "text": item.text}
            for item in data.items
        ]

        result = {
            "question_text": data.question_text,
            "categories": categories_data,
            "items": items_data,
            "explanation": data.explanation,
            "question_type": self.question_type.value,
        }

        if data.distractors:
            result["distractors"] = [
                {"id": item.id, "text": item.text}
                for item in data.distractors
            ]

        return result
```

**Code Explanation**:

- `CategoryItem`: Represents individual items to be categorized with UUID and text
- `Category`: Represents categories with names and lists of correct item IDs
- `CategorizationData`: Main data model with comprehensive validation
- `CategorizationQuestionType`: Complete implementation of all abstract methods
- Canvas export generates proper Canvas API structure with categories, distractors, and scoring
- Validation ensures data integrity and Canvas compatibility

**Testing**: After this step:
1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add categorization question data models and implementation"`

#### Step 3: Register Question Type

**File**: `backend/src/question/types/registry.py`

**Changes**: Add import and registration

```python
def _initialize_default_types(self) -> None:
    """Initialize the registry with default question type implementations."""
    if self._initialized:
        return

    try:
        # Import and register default question types
        from .categorization import CategorizationQuestionType  # ← ADD THIS IMPORT
        from .fill_in_blank import FillInBlankQuestionType
        from .matching import MatchingQuestionType
        from .mcq import MultipleChoiceQuestionType

        self.register_question_type(
            QuestionType.MULTIPLE_CHOICE, MultipleChoiceQuestionType()
        )
        self.register_question_type(
            QuestionType.FILL_IN_BLANK, FillInBlankQuestionType()
        )
        self.register_question_type(
            QuestionType.MATCHING, MatchingQuestionType()
        )
        self.register_question_type(  # ← ADD THIS REGISTRATION
            QuestionType.CATEGORIZATION, CategorizationQuestionType()
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
3. Commit changes: `git add -A && git commit -m "feat: register categorization question type in registry"`

#### Step 4: Create English AI Template

**File**: `backend/src/question/templates/files/batch_categorization.json` (NEW FILE)

**Complete Template**:

```json
{
  "name": "batch_categorization",
  "version": "1.0",
  "question_type": "categorization",
  "description": "Template for generating categorization questions from module content",
  "system_prompt": "You are an expert educator creating categorization quiz questions. Generate diverse, high-quality questions that test students' ability to classify and organize concepts, items, or information into appropriate categories.\n\nIMPORTANT REQUIREMENTS:\n1. Generate EXACTLY {{ question_count }} categorization questions\n2. Each question must have 2-8 categories (optimal: 3-5 categories per question)\n3. Each question must have 6-20 items to categorize (optimal: 8-12 items per question)\n4. Each category must have at least 2 correct items\n5. Include 0-3 distractors per question (items that don't belong to any category)\n6. Ensure categories are mutually exclusive and clearly defined\n7. Vary the difficulty levels and categorization types\n8. Include brief explanations for the categorization logic\n\nCATEGORIZATION TYPES TO CREATE:\n- **Taxonomic Classification**: \"Mammals\" vs \"Reptiles\" vs \"Birds\"\n- **Geographic Classification**: \"Europe\" vs \"Asia\" vs \"Africa\"\n- **Functional Classification**: \"Input Devices\" vs \"Output Devices\" vs \"Storage Devices\"\n- **Temporal Classification**: \"Ancient\" vs \"Medieval\" vs \"Modern\"\n- **Conceptual Classification**: \"Renewable Energy\" vs \"Non-renewable Energy\"\n- **Academic Disciplines**: \"Physics\" vs \"Chemistry\" vs \"Biology\"\n- **Literary Genres**: \"Poetry\" vs \"Drama\" vs \"Fiction\"\n\nDISTRACTOR GUIDELINES:\n- Make distractors related to the topic but clearly don't fit any category\n- Don't make distractors that could reasonably fit multiple categories\n- Examples of good distractors: if categorizing animals by habitat, use mythical creatures or extinct species\n\nReturn your response as a valid JSON array with exactly {{ question_count }} question objects.\n\nEach question object must have this exact structure:\n{\n    \"question_text\": \"Categorize each item into the appropriate biological classification.\",\n    \"categories\": [\n        {\n            \"name\": \"Mammals\",\n            \"correct_items\": [\"item_id_1\", \"item_id_2\"]\n        },\n        {\n            \"name\": \"Reptiles\", \n            \"correct_items\": [\"item_id_3\", \"item_id_4\"]\n        },\n        {\n            \"name\": \"Birds\",\n            \"correct_items\": [\"item_id_5\", \"item_id_6\"]\n        }\n    ],\n    \"items\": [\n        {\"id\": \"item_id_1\", \"text\": \"Dolphin\"},\n        {\"id\": \"item_id_2\", \"text\": \"Elephant\"},\n        {\"id\": \"item_id_3\", \"text\": \"Snake\"},\n        {\"id\": \"item_id_4\", \"text\": \"Lizard\"},\n        {\"id\": \"item_id_5\", \"text\": \"Eagle\"},\n        {\"id\": \"item_id_6\", \"text\": \"Penguin\"}\n    ],\n    \"distractors\": [\n        {\"id\": \"distractor_1\", \"text\": \"Jellyfish\"},\n        {\"id\": \"distractor_2\", \"text\": \"Coral\"}\n    ],\n    \"explanation\": \"These categories represent the main vertebrate animal classes based on biological characteristics.\"\n}\n\nIMPORTANT:\n- Return ONLY a valid JSON array\n- No markdown code blocks (```json or ```)\n- No explanatory text before or after the JSON\n- Each item and category must have unique IDs within the question\n- Ensure all item IDs referenced in correct_items exist in the items array\n- The array must contain exactly {{ question_count }} question objects\n- Generate meaningful, educational categorization scenarios based on the module content",
  "user_prompt": "Based on the following content from the module '{{ module_name }}', generate exactly {{ question_count }} categorization questions.\n\nMODULE CONTENT:\n{{ module_content }}\n\nGenerate exactly {{ question_count }} questions:",
  "variables": {
    "module_name": "The name of the module",
    "module_content": "The module content to generate questions from",
    "question_count": "Number of questions to generate",
    "difficulty": "Question difficulty level (optional)",
    "tags": "List of topic tags to focus on (optional)",
    "custom_instructions": "Additional custom instructions (optional)"
  },
  "author": "System",
  "tags": ["batch", "categorization", "module"],
  "created_at": null,
  "updated_at": null,
  "min_content_length": 100,
  "max_content_length": 50000
}
```

**Testing**: After this step:
1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`

#### Step 5: Create Norwegian AI Template

**File**: `backend/src/question/templates/files/batch_categorization_no.json` (NEW FILE)

**Complete Template**:

```json
{
  "name": "batch_categorization_no",
  "version": "1.0",
  "question_type": "categorization",
  "language": "no",
  "description": "Mal for generering av kategoriseringsspørsmål fra modulinnhold",
  "system_prompt": "Du er en ekspert pedagog som lager kategoriseringsspørsmål for quiz. Generer varierte, høykvalitets spørsmål som tester studentenes evne til å klassifisere og organisere konsepter, gjenstander eller informasjon i passende kategorier.\n\nVIKTIGE KRAV:\n1. Generer NØYAKTIG {{ question_count }} kategoriseringsspørsmål\n2. Hvert spørsmål må ha 2-8 kategorier (optimalt: 3-5 kategorier per spørsmål)\n3. Hvert spørsmål må ha 6-20 elementer å kategorisere (optimalt: 8-12 elementer per spørsmål)\n4. Hver kategori må ha minst 2 korrekte elementer\n5. Inkluder 0-3 distraktorer per spørsmål (elementer som ikke hører til noen kategori)\n6. Sørg for at kategoriene er gjensidig utelukkende og klart definerte\n7. Varierér vanskegrad og kategoriseringstyper\n8. Inkluder korte forklaringer for kategoriseringslogikken\n\nKATEGORISERINGSTYPER Å LAGE:\n- **Taksonomisk Klassifisering**: \"Pattedyr\" vs \"Reptiler\" vs \"Fugler\"\n- **Geografisk Klassifisering**: \"Europa\" vs \"Asia\" vs \"Afrika\"\n- **Funksjonell Klassifisering**: \"Inngangsenheter\" vs \"Utgangsenheter\" vs \"Lagringsenheter\"\n- **Temporal Klassifisering**: \"Antikken\" vs \"Middelalderen\" vs \"Moderne tid\"\n- **Konseptuell Klassifisering**: \"Fornybar Energi\" vs \"Ikke-fornybar Energi\"\n- **Akademiske Disipliner**: \"Fysikk\" vs \"Kjemi\" vs \"Biologi\"\n- **Litterære Sjangre**: \"Poesi\" vs \"Drama\" vs \"Skjønnlitteratur\"\n\nDISTRAKTORRETNINGSLINJER:\n- Lag distraktorer som er relatert til temaet men tydelig ikke passer i noen kategori\n- Ikke lag distraktorer som rimelig kunne passe i flere kategorier\n- Eksempler på gode distraktorer: hvis du kategoriserer dyr etter habitat, bruk mytiske skapninger eller utdødde arter\n\nReturnér svaret ditt som en gyldig JSON-array med nøyaktig {{ question_count }} spørsmålsobjekter.\n\nHvert spørsmålsobjekt må ha denne nøyaktige strukturen:\n{\n    \"question_text\": \"Kategoriser hvert element i den passende biologiske klassifiseringen.\",\n    \"categories\": [\n        {\n            \"name\": \"Pattedyr\",\n            \"correct_items\": [\"element_id_1\", \"element_id_2\"]\n        },\n        {\n            \"name\": \"Reptiler\", \n            \"correct_items\": [\"element_id_3\", \"element_id_4\"]\n        },\n        {\n            \"name\": \"Fugler\",\n            \"correct_items\": [\"element_id_5\", \"element_id_6\"]\n        }\n    ],\n    \"items\": [\n        {\"id\": \"element_id_1\", \"text\": \"Delfin\"},\n        {\"id\": \"element_id_2\", \"text\": \"Elefant\"},\n        {\"id\": \"element_id_3\", \"text\": \"Slange\"},\n        {\"id\": \"element_id_4\", \"text\": \"Øgle\"},\n        {\"id\": \"element_id_5\", \"text\": \"Ørn\"},\n        {\"id\": \"element_id_6\", \"text\": \"Pingvin\"}\n    ],\n    \"distractors\": [\n        {\"id\": \"distraktor_1\", \"text\": \"Manet\"},\n        {\"id\": \"distraktor_2\", \"text\": \"Korall\"}\n    ],\n    \"explanation\": \"Disse kategoriene representerer de viktigste virveldyrklassene basert på biologiske kjennetegn.\"\n}\n\nVIKTIG:\n- Returnér KUN en gyldig JSON-array\n- Ingen markdown-kodeblokker (```json eller ```)\n- Ingen forklarende tekst før eller etter JSON\n- Hvert element og kategori må ha unike ID-er innenfor spørsmålet\n- Sørg for at alle element-ID-er referert i correct_items finnes i items-arrayen\n- Arrayen må inneholde nøyaktig {{ question_count }} spørsmålsobjekter\n- Generer meningsfulle, pedagogiske kategoriseringsscenarier basert på modulinnholdet",
  "user_prompt": "Basert på følgende innhold fra modulen '{{ module_name }}', generer nøyaktig {{ question_count }} kategoriseringsspørsmål.\n\nMODULINNHOLD:\n{{ module_content }}\n\nGenerer nøyaktig {{ question_count }} spørsmål:",
  "variables": {
    "module_name": "Navnet på modulen",
    "module_content": "Modulinnholdet å generere spørsmål fra",
    "question_count": "Antall spørsmål å generere",
    "difficulty": "Spørsmålsvanskegrad (valgfritt)",
    "tags": "Liste over emnetagg å fokusere på (valgfritt)",
    "custom_instructions": "Ytterligere tilpassede instruksjoner (valgfritt)"
  },
  "author": "System",
  "tags": ["batch", "categorization", "module", "norsk"],
  "created_at": null,
  "updated_at": null,
  "min_content_length": 100,
  "max_content_length": 50000
}
```

**Testing**: After this step:
1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add AI templates for categorization questions (English and Norwegian)"`

#### Step 6: Create Comprehensive Tests

**File**: `backend/tests/question/types/test_categorization.py` (NEW FILE)

**Complete Test Suite**:

```python
"""Tests for categorization question type implementation."""

import pytest
from pydantic import ValidationError

from src.question.types import QuestionType, get_question_type_registry
from src.question.types.categorization import (
    Category,
    CategoryItem,
    CategorizationData,
    CategorizationQuestionType,
)


class TestCategoryItem:
    """Tests for CategoryItem data model."""

    def test_create_valid_item(self):
        """Test creating a valid category item."""
        item = CategoryItem(text="Dolphin")
        assert item.text == "Dolphin"
        assert item.id is not None
        assert len(item.id) > 0

    def test_create_item_with_custom_id(self):
        """Test creating item with custom ID."""
        item = CategoryItem(id="custom_id", text="Elephant")
        assert item.id == "custom_id"
        assert item.text == "Elephant"

    def test_empty_text_fails(self):
        """Test that empty text fails validation."""
        with pytest.raises(ValidationError):
            CategoryItem(text="")

    def test_whitespace_only_text_fails(self):
        """Test that whitespace-only text fails validation."""
        with pytest.raises(ValidationError):
            CategoryItem(text="   ")

    def test_text_too_long_fails(self):
        """Test that text longer than 200 characters fails."""
        long_text = "x" * 201
        with pytest.raises(ValidationError):
            CategoryItem(text=long_text)


class TestCategory:
    """Tests for Category data model."""

    def test_create_valid_category(self):
        """Test creating a valid category."""
        category = Category(name="Mammals", correct_items=["item1", "item2"])
        assert category.name == "Mammals"
        assert category.correct_items == ["item1", "item2"]
        assert category.id is not None

    def test_create_category_with_custom_id(self):
        """Test creating category with custom ID."""
        category = Category(
            id="custom_id",
            name="Birds",
            correct_items=["item1"]
        )
        assert category.id == "custom_id"
        assert category.name == "Birds"

    def test_empty_name_fails(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValidationError):
            Category(name="", correct_items=["item1"])

    def test_name_too_long_fails(self):
        """Test that name longer than 100 characters fails."""
        long_name = "x" * 101
        with pytest.raises(ValidationError):
            Category(name=long_name, correct_items=["item1"])

    def test_empty_correct_items_fails(self):
        """Test that empty correct_items fails validation."""
        with pytest.raises(ValidationError, match="Each category must have at least one correct item"):
            Category(name="Mammals", correct_items=[])

    def test_too_many_correct_items_fails(self):
        """Test that more than 10 correct items fails."""
        many_items = [f"item{i}" for i in range(11)]
        with pytest.raises(ValidationError):
            Category(name="Mammals", correct_items=many_items)


class TestCategorizationData:
    """Tests for CategorizationData data model."""

    def setup_method(self):
        """Set up test fixtures."""
        self.valid_categories = [
            Category(name="Mammals", correct_items=["item1", "item2"]),
            Category(name="Birds", correct_items=["item3", "item4"]),
        ]
        self.valid_items = [
            CategoryItem(id="item1", text="Dolphin"),
            CategoryItem(id="item2", text="Elephant"),
            CategoryItem(id="item3", text="Eagle"),
            CategoryItem(id="item4", text="Penguin"),
            CategoryItem(id="item5", text="Shark"),
            CategoryItem(id="item6", text="Octopus"),
        ]

    def test_create_valid_categorization_data(self):
        """Test creating valid categorization data."""
        data = CategorizationData(
            question_text="Categorize these animals",
            categories=self.valid_categories,
            items=self.valid_items
        )
        assert len(data.categories) == 2
        assert len(data.items) == 6
        assert data.distractors is None

    def test_create_with_distractors(self):
        """Test creating categorization data with distractors."""
        distractors = [
            CategoryItem(id="dist1", text="Jellyfish"),
            CategoryItem(id="dist2", text="Coral"),
        ]
        data = CategorizationData(
            question_text="Categorize these animals",
            categories=self.valid_categories,
            items=self.valid_items,
            distractors=distractors
        )
        assert len(data.distractors) == 2

    def test_minimum_categories_required(self):
        """Test that at least 2 categories are required."""
        single_category = [Category(name="Mammals", correct_items=["item1"])]
        with pytest.raises(ValidationError, match="At least 2 categories are required"):
            CategorizationData(
                question_text="Test",
                categories=single_category,
                items=self.valid_items
            )

    def test_maximum_categories_limit(self):
        """Test that maximum 8 categories are allowed."""
        many_categories = [
            Category(name=f"Category{i}", correct_items=[f"item{i}"])
            for i in range(9)
        ]
        items = [CategoryItem(id=f"item{i}", text=f"Item{i}") for i in range(9)]

        with pytest.raises(ValidationError, match="Maximum 8 categories allowed"):
            CategorizationData(
                question_text="Test",
                categories=many_categories,
                items=items
            )

    def test_minimum_items_required(self):
        """Test that at least 6 items are required."""
        few_items = [
            CategoryItem(id=f"item{i}", text=f"Item{i}")
            for i in range(5)
        ]
        with pytest.raises(ValidationError, match="At least 6 items are required"):
            CategorizationData(
                question_text="Test",
                categories=self.valid_categories,
                items=few_items
            )

    def test_maximum_items_limit(self):
        """Test that maximum 20 items are allowed."""
        many_items = [
            CategoryItem(id=f"item{i}", text=f"Item{i}")
            for i in range(21)
        ]
        with pytest.raises(ValidationError, match="Maximum 20 items allowed"):
            CategorizationData(
                question_text="Test",
                categories=self.valid_categories,
                items=many_items
            )

    def test_duplicate_category_names_not_allowed(self):
        """Test that duplicate category names are not allowed."""
        duplicate_categories = [
            Category(name="Mammals", correct_items=["item1"]),
            Category(name="mammals", correct_items=["item2"]),  # Case-insensitive duplicate
        ]
        with pytest.raises(ValidationError, match="Duplicate category names are not allowed"):
            CategorizationData(
                question_text="Test",
                categories=duplicate_categories,
                items=self.valid_items
            )

    def test_duplicate_item_texts_not_allowed(self):
        """Test that duplicate item texts are not allowed."""
        duplicate_items = [
            CategoryItem(id="item1", text="Dolphin"),
            CategoryItem(id="item2", text="dolphin"),  # Case-insensitive duplicate
        ] + self.valid_items[2:]

        with pytest.raises(ValidationError, match="Duplicate item texts are not allowed"):
            CategorizationData(
                question_text="Test",
                categories=self.valid_categories,
                items=duplicate_items
            )

    def test_maximum_distractors_limit(self):
        """Test maximum 5 distractors allowed."""
        many_distractors = [
            CategoryItem(id=f"dist{i}", text=f"Distractor{i}")
            for i in range(6)
        ]
        with pytest.raises(ValidationError, match="Maximum 5 distractors allowed"):
            CategorizationData(
                question_text="Test",
                categories=self.valid_categories,
                items=self.valid_items,
                distractors=many_distractors
            )

    def test_validate_item_assignments_success(self):
        """Test successful item assignment validation."""
        data = CategorizationData(
            question_text="Test",
            categories=self.valid_categories,
            items=self.valid_items
        )
        # Should not raise any exception
        data.validate_item_assignments()

    def test_validate_item_assignments_nonexistent_item(self):
        """Test validation fails when category references non-existent item."""
        bad_categories = [
            Category(name="Mammals", correct_items=["nonexistent_item"]),
            Category(name="Birds", correct_items=["item3"]),
        ]
        data = CategorizationData(
            question_text="Test",
            categories=bad_categories,
            items=self.valid_items
        )

        with pytest.raises(ValueError, match="references non-existent item ID"):
            data.validate_item_assignments()

    def test_validate_item_assignments_duplicate_assignment(self):
        """Test validation fails when item is assigned to multiple categories."""
        bad_categories = [
            Category(name="Mammals", correct_items=["item1", "item2"]),
            Category(name="Birds", correct_items=["item2", "item3"]),  # item2 assigned twice
        ]
        data = CategorizationData(
            question_text="Test",
            categories=bad_categories,
            items=self.valid_items
        )

        with pytest.raises(ValueError, match="is assigned to multiple categories"):
            data.validate_item_assignments()

    def test_validate_item_assignments_unassigned_items(self):
        """Test validation fails when items are not assigned to any category."""
        incomplete_categories = [
            Category(name="Mammals", correct_items=["item1"]),
            Category(name="Birds", correct_items=["item3"]),
            # item2, item4, item5, item6 are unassigned
        ]
        data = CategorizationData(
            question_text="Test",
            categories=incomplete_categories,
            items=self.valid_items
        )

        with pytest.raises(ValueError, match="Items not assigned to any category"):
            data.validate_item_assignments()

    def test_get_all_items(self):
        """Test getting all items including distractors."""
        distractors = [CategoryItem(id="dist1", text="Jellyfish")]
        data = CategorizationData(
            question_text="Test",
            categories=self.valid_categories,
            items=self.valid_items,
            distractors=distractors
        )

        all_items = data.get_all_items()
        assert len(all_items) == 7  # 6 items + 1 distractor

    def test_get_all_items_no_distractors(self):
        """Test getting all items when no distractors."""
        data = CategorizationData(
            question_text="Test",
            categories=self.valid_categories,
            items=self.valid_items
        )

        all_items = data.get_all_items()
        assert len(all_items) == 6

    def test_get_category_by_id(self):
        """Test getting category by ID."""
        data = CategorizationData(
            question_text="Test",
            categories=self.valid_categories,
            items=self.valid_items
        )

        category = data.get_category_by_id(self.valid_categories[0].id)
        assert category is not None
        assert category.name == "Mammals"

    def test_get_category_by_id_not_found(self):
        """Test getting category by non-existent ID."""
        data = CategorizationData(
            question_text="Test",
            categories=self.valid_categories,
            items=self.valid_items
        )

        category = data.get_category_by_id("nonexistent")
        assert category is None

    def test_get_item_by_id(self):
        """Test getting item by ID."""
        data = CategorizationData(
            question_text="Test",
            categories=self.valid_categories,
            items=self.valid_items
        )

        item = data.get_item_by_id("item1")
        assert item is not None
        assert item.text == "Dolphin"

    def test_get_item_by_id_not_found(self):
        """Test getting item by non-existent ID."""
        data = CategorizationData(
            question_text="Test",
            categories=self.valid_categories,
            items=self.valid_items
        )

        item = data.get_item_by_id("nonexistent")
        assert item is None


class TestCategorizationQuestionType:
    """Tests for CategorizationQuestionType implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.categorization_type = CategorizationQuestionType()
        self.valid_data = {
            "question_text": "Categorize these animals by their biological class",
            "categories": [
                {
                    "name": "Mammals",
                    "correct_items": ["item1", "item2"]
                },
                {
                    "name": "Birds",
                    "correct_items": ["item3", "item4"]
                }
            ],
            "items": [
                {"id": "item1", "text": "Dolphin"},
                {"id": "item2", "text": "Elephant"},
                {"id": "item3", "text": "Eagle"},
                {"id": "item4", "text": "Penguin"},
                {"id": "item5", "text": "Shark"},
                {"id": "item6", "text": "Octopus"}
            ],
            "distractors": [
                {"id": "dist1", "text": "Jellyfish"},
                {"id": "dist2", "text": "Coral"}
            ],
            "explanation": "These categories represent major vertebrate classes."
        }

    def test_question_type_property(self):
        """Test question type enum property."""
        assert self.categorization_type.question_type == QuestionType.CATEGORIZATION

    def test_data_model_property(self):
        """Test data model property."""
        assert self.categorization_type.data_model == CategorizationData

    def test_validate_data_success(self):
        """Test successful data validation."""
        result = self.categorization_type.validate_data(self.valid_data)
        assert isinstance(result, CategorizationData)
        assert len(result.categories) == 2
        assert len(result.items) == 6
        assert len(result.distractors) == 2

    def test_validate_data_with_item_assignment_error(self):
        """Test validation fails with item assignment errors."""
        invalid_data = self.valid_data.copy()
        invalid_data["categories"] = [
            {
                "name": "Mammals",
                "correct_items": ["nonexistent_item"]
            },
            {
                "name": "Birds",
                "correct_items": ["item3"]
            }
        ]

        with pytest.raises(ValueError, match="references non-existent item ID"):
            self.categorization_type.validate_data(invalid_data)

    def test_validate_data_wrong_structure(self):
        """Test validation with wrong data structure."""
        with pytest.raises(ValidationError):
            self.categorization_type.validate_data({"invalid": "data"})

    def test_format_for_display(self):
        """Test formatting for display."""
        data = self.categorization_type.validate_data(self.valid_data)
        result = self.categorization_type.format_for_display(data)

        assert result["question_text"] == "Categorize these animals by their biological class"
        assert len(result["categories"]) == 2
        assert len(result["items"]) == 6
        assert len(result["distractors"]) == 2
        assert result["question_type"] == "categorization"

        # Check category structure
        mammals_category = next(cat for cat in result["categories"] if cat["name"] == "Mammals")
        assert mammals_category["correct_items"] == ["item1", "item2"]

    def test_format_for_display_no_distractors(self):
        """Test formatting for display without distractors."""
        data_no_distractors = self.valid_data.copy()
        del data_no_distractors["distractors"]

        data = self.categorization_type.validate_data(data_no_distractors)
        result = self.categorization_type.format_for_display(data)

        assert "distractors" not in result

    def test_format_for_display_wrong_type(self):
        """Test format_for_display with wrong data type."""
        from src.question.types.mcq import MultipleChoiceData

        mcq_data = MultipleChoiceData(
            question_text="Test",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_answer="A"
        )

        with pytest.raises(ValueError, match="Expected CategorizationData"):
            self.categorization_type.format_for_display(mcq_data)

    def test_format_for_canvas(self):
        """Test Canvas export formatting."""
        data = self.categorization_type.validate_data(self.valid_data)
        result = self.categorization_type.format_for_canvas(data)

        # Validate basic structure
        assert "title" in result
        assert result["item_body"] == "<p>Categorize these animals by their biological class</p>"
        assert result["calculator_type"] == "none"
        assert result["interaction_type_slug"] == "categorization"
        assert result["scoring_algorithm"] == "Categorization"
        assert result["points_possible"] == 2  # 2 categories

        # Validate interaction_data
        interaction_data = result["interaction_data"]
        assert "categories" in interaction_data
        assert "distractors" in interaction_data
        assert "category_order" in interaction_data

        assert len(interaction_data["categories"]) == 2
        assert len(interaction_data["distractors"]) == 8  # 6 items + 2 distractors
        assert len(interaction_data["category_order"]) == 2

        # Validate scoring_data
        scoring_data = result["scoring_data"]
        assert "value" in scoring_data
        assert "score_method" in scoring_data
        assert scoring_data["score_method"] == "all_or_nothing"
        assert len(scoring_data["value"]) == 2  # 2 categories

        # Check that each category has scoring data
        for category_score in scoring_data["value"]:
            assert "id" in category_score
            assert "scoring_data" in category_score
            assert category_score["scoring_data"]["scoring_algorithm"] == "AllOrNothing"

    def test_format_for_export(self):
        """Test generic export formatting."""
        data = self.categorization_type.validate_data(self.valid_data)
        result = self.categorization_type.format_for_export(data)

        expected_structure = {
            "question_text": "Categorize these animals by their biological class",
            "question_type": "categorization",
            "explanation": "These categories represent major vertebrate classes."
        }

        for key, value in expected_structure.items():
            assert result[key] == value

        assert len(result["categories"]) == 2
        assert len(result["items"]) == 6
        assert len(result["distractors"]) == 2


class TestCategorizationQuestionTypeRegistry:
    """Tests for categorization question type registry integration."""

    def test_categorization_type_registered(self):
        """Test that categorization type is registered in registry."""
        registry = get_question_type_registry()
        assert registry.is_registered(QuestionType.CATEGORIZATION)

    def test_get_categorization_type_from_registry(self):
        """Test retrieving categorization type from registry."""
        registry = get_question_type_registry()
        categorization_type = registry.get_question_type(QuestionType.CATEGORIZATION)
        assert isinstance(categorization_type, CategorizationQuestionType)

    def test_categorization_in_available_types(self):
        """Test that categorization appears in available types."""
        registry = get_question_type_registry()
        available_types = registry.get_available_types()
        assert QuestionType.CATEGORIZATION in available_types


class TestCategorizationQuestionEndToEnd:
    """End-to-end tests for categorization question workflow."""

    def test_full_workflow(self):
        """Test complete workflow from raw data to Canvas export."""
        registry = get_question_type_registry()

        # Raw AI response data
        raw_data = {
            "question_text": "Classify these programming concepts by category",
            "categories": [
                {
                    "name": "Data Structures",
                    "correct_items": ["item1", "item2"]
                },
                {
                    "name": "Algorithms",
                    "correct_items": ["item3", "item4"]
                },
                {
                    "name": "Programming Paradigms",
                    "correct_items": ["item5", "item6"]
                }
            ],
            "items": [
                {"id": "item1", "text": "Array"},
                {"id": "item2", "text": "Linked List"},
                {"id": "item3", "text": "Binary Search"},
                {"id": "item4", "text": "Quick Sort"},
                {"id": "item5", "text": "Object-Oriented"},
                {"id": "item6", "text": "Functional"}
            ],
            "distractors": [
                {"id": "dist1", "text": "IDE"},
                {"id": "dist2", "text": "Compiler"}
            ],
            "explanation": "These represent fundamental computer science concepts organized by their primary domain."
        }

        # Get question type and validate data
        categorization_type = registry.get_question_type(QuestionType.CATEGORIZATION)
        validated_data = categorization_type.validate_data(raw_data)

        # Format for different outputs
        display_format = categorization_type.format_for_display(validated_data)
        canvas_format = categorization_type.format_for_canvas(validated_data)
        export_format = categorization_type.format_for_export(validated_data)

        # Validate all formats work
        assert display_format["question_type"] == "categorization"
        assert canvas_format["interaction_type_slug"] == "categorization"
        assert export_format["question_type"] == "categorization"

        # Validate data consistency
        assert len(display_format["categories"]) == 3
        assert len(canvas_format["scoring_data"]["value"]) == 3
        assert len(export_format["categories"]) == 3

    def test_round_trip_data_validation(self):
        """Test that data survives round-trip through validation."""
        original_data = {
            "question_text": "Categorize these chemical elements",
            "categories": [
                {
                    "name": "Noble Gases",
                    "correct_items": ["item1", "item2"]
                },
                {
                    "name": "Alkali Metals",
                    "correct_items": ["item3", "item4"]
                }
            ],
            "items": [
                {"id": "item1", "text": "Helium"},
                {"id": "item2", "text": "Neon"},
                {"id": "item3", "text": "Sodium"},
                {"id": "item4", "text": "Potassium"},
                {"id": "item5", "text": "Hydrogen"},
                {"id": "item6", "text": "Oxygen"}
            ],
            "explanation": "Chemical elements classified by their properties."
        }

        categorization_type = CategorizationQuestionType()

        # Validate and export
        validated = categorization_type.validate_data(original_data)
        exported = categorization_type.format_for_export(validated)

        # Re-validate exported data
        re_validated = categorization_type.validate_data(exported)
        re_exported = categorization_type.format_for_export(re_validated)

        # Should be identical
        assert exported == re_exported

    def test_complex_validation_scenario(self):
        """Test complex validation with maximum complexity."""
        # Test with maximum categories, items, and distractors
        categories_data = [
            {
                "name": f"Category {i}",
                "correct_items": [f"item{i*2+1}", f"item{i*2+2}"]
            }
            for i in range(4)  # 4 categories
        ]

        items_data = [
            {"id": f"item{i}", "text": f"Item {i}"}
            for i in range(1, 9)  # 8 items (2 per category)
        ]

        # Add additional items to reach minimum requirement
        for i in range(9, 13):
            items_data.append({"id": f"item{i}", "text": f"Extra Item {i}"})

        # Assign extra items to categories
        categories_data[0]["correct_items"].extend(["item9", "item10"])
        categories_data[1]["correct_items"].extend(["item11", "item12"])

        distractors_data = [
            {"id": f"dist{i}", "text": f"Distractor {i}"}
            for i in range(1, 4)  # 3 distractors
        ]

        complex_data = {
            "question_text": "Complex categorization with special characters: áéíóú & symbols!",
            "categories": categories_data,
            "items": items_data,
            "distractors": distractors_data,
            "explanation": "This tests maximum complexity with special characters and symbols."
        }

        categorization_type = CategorizationQuestionType()
        validated_data = categorization_type.validate_data(complex_data)

        # Should validate successfully
        assert len(validated_data.categories) == 4
        assert len(validated_data.items) == 12
        assert len(validated_data.distractors) == 3

        # Canvas export should work
        canvas_format = categorization_type.format_for_canvas(validated_data)
        assert canvas_format["points_possible"] == 4
        assert len(canvas_format["interaction_data"]["distractors"]) == 15  # 12 items + 3 distractors
```

**Testing**: After this step:
1. Run `cd backend && source .venv/bin/activate && bash scripts/test.sh`
2. Run `cd backend && source .venv/bin/activate && bash scripts/lint.sh`
3. Commit changes: `git add -A && git commit -m "feat: add comprehensive test suite for categorization questions"`

### 4.3 Data Models & Schemas

#### Core Data Structures

**CategoryItem Model**:

```python
class CategoryItem(BaseModel):
    id: str          # UUID identifier (auto-generated)
    text: str        # Item text content (1-200 characters)
```

**Category Model**:

```python
class Category(BaseModel):
    id: str                  # UUID identifier (auto-generated)
    name: str               # Category name (1-100 characters)
    correct_items: list[str] # List of item IDs that belong here (1-10)
```

**CategorizationData Model**:

```python
class CategorizationData(BaseQuestionData):
    categories: list[Category]       # 2-8 categories required
    items: list[CategoryItem]        # 6-20 items required
    distractors: list[CategoryItem] | None  # 0-5 optional distractors
```

#### Validation Rules

- **Category Count**: 2-8 categories per question
- **Item Count**: 6-20 items per question (including distractors)
- **Item Assignment**: Each non-distractor item must be assigned to exactly one category
- **Duplicates**: No duplicate category names or item texts (case-insensitive)
- **Category Population**: Each category must have at least 1 correct item

#### Example Data

```json
{
  "question_text": "Categorize these animals by their biological class",
  "categories": [
    {
      "id": "cat1",
      "name": "Mammals",
      "correct_items": ["item1", "item2"]
    },
    {
      "id": "cat2",
      "name": "Birds",
      "correct_items": ["item3", "item4"]
    }
  ],
  "items": [
    {"id": "item1", "text": "Dolphin"},
    {"id": "item2", "text": "Elephant"},
    {"id": "item3", "text": "Eagle"},
    {"id": "item4", "text": "Penguin"},
    {"id": "item5", "text": "Shark"},
    {"id": "item6", "text": "Octopus"}
  ],
  "distractors": [
    {"id": "dist1", "text": "Jellyfish"},
    {"id": "dist2", "text": "Coral"}
  ],
  "explanation": "These categories represent major vertebrate classes"
}
```

#### Canvas Export Format

```json
{
  "interaction_data": {
    "categories": {
      "cat1": {"id": "cat1", "item_body": "Mammals"},
      "cat2": {"id": "cat2", "item_body": "Birds"}
    },
    "distractors": {
      "item1": {"id": "item1", "item_body": "Dolphin"},
      "item2": {"id": "item2", "item_body": "Elephant"},
      "item3": {"id": "item3", "item_body": "Eagle"},
      "item4": {"id": "item4", "item_body": "Penguin"},
      "item5": {"id": "item5", "item_body": "Shark"},
      "item6": {"id": "item6", "item_body": "Octopus"},
      "dist1": {"id": "dist1", "item_body": "Jellyfish"},
      "dist2": {"id": "dist2", "item_body": "Coral"}
    },
    "category_order": ["cat1", "cat2"]
  },
  "scoring_data": {
    "value": [
      {
        "id": "cat1",
        "scoring_data": {
          "value": ["item1", "item2"],
          "scoring_algorithm": "AllOrNothing"
        }
      },
      {
        "id": "cat2",
        "scoring_data": {
          "value": ["item3", "item4"],
          "scoring_algorithm": "AllOrNothing"
        }
      }
    ],
    "score_method": "all_or_nothing"
  },
  "interaction_type_slug": "categorization",
  "scoring_algorithm": "Categorization"
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

### Unit Tests (40+ tests total)

- **CategoryItem Tests (5)**: Basic creation, validation, length limits
- **Category Tests (6)**: Name validation, correct_items validation
- **CategorizationData Tests (15)**: Complex validation, duplicates, assignments
- **CategorizationQuestionType Tests (12)**: All interface methods, error handling
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
     -d '{"question_type": "categorization", "target_count": 2, "language": "en"}'
   ```

2. **Canvas Export Testing**:

   - Generate categorization questions through UI
   - Export to Canvas and verify format
   - Check Canvas quiz display and functionality

3. **AI Generation Testing**:

   - Test with various content types (text, PDFs)
   - Verify category quality and item appropriateness
   - Check multilingual generation quality

### Performance Benchmarks

- **Question Validation**: < 15ms per question
- **Canvas Export**: < 75ms per question
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
   # Should include "categorization" in response
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

- **Question Generation Success Rate**: Track categorization question generation success
- **Canvas Export Success Rate**: Monitor Canvas API integration
- **Template Performance**: Track template rendering times
- **Validation Error Rates**: Monitor validation failures

### Log Entries to Watch For

```python
# Success indicators
"question_type_registered" with question_type="categorization"
"question_generation_success" with question_type="categorization"
"canvas_export_success" with question_type="categorization"

# Error indicators
"question_validation_error" with question_type="categorization"
"template_not_found" for categorization templates
"canvas_export_error" with categorization questions
```

### Common Issues and Troubleshooting

#### Template Not Found

```
Error: No template found for question type categorization
Solution: Verify template files exist in templates/files/
Check: batch_categorization.json and batch_categorization_no.json
```

#### Validation Errors

```
Error: Items not assigned to any category: ['item5', 'item6']
Solution: Review AI generation quality, update templates
Action: Check template instructions for item assignment requirements
```

#### Canvas Export Issues

```
Error: Canvas API rejection of categorization format
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
class CategoryItem(BaseModel):
    text: str = Field(min_length=1, max_length=200)  # Prevents empty injection

class Category(BaseModel):
    name: str = Field(min_length=1, max_length=100)  # Validates content

# Canvas export sanitizes HTML
item_body = f"<p>{data.question_text}</p>"  # Safe HTML generation
```

## 9. Future Considerations

### Known Limitations

- **Fixed Category Assignment**: Currently supports only one correct category per item
- **Distractor Limit**: Maximum 5 distractors may be insufficient for complex topics
- **Canvas Dependency**: Tied to Canvas New Quizzes API format
- **No Partial Credit**: Currently uses all-or-nothing scoring per category

### Potential Improvements

1. **Enhanced Categorization Types**:

   - Multiple correct categories per item
   - Weighted scoring for partial matches
   - Hierarchical categorization (subcategories)

2. **Advanced AI Generation**:

   - Context-aware category generation
   - Difficulty-based item complexity
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
# Future categorization types can extend base classes
class HierarchicalCategorizationData(CategorizationData):
    # Support subcategories
    subcategories: dict[str, list[Category]]

class WeightedCategorizationData(CategorizationData):
    # Add scoring weights
    category_weights: dict[str, float]
```

### Migration Path for Enhancements

1. **Backward Compatibility**: New features extend existing models
2. **Database Evolution**: Additional JSONB fields don't require migration
3. **API Evolution**: New endpoints can coexist with existing ones
4. **Template Evolution**: New template versions can coexist

---

## Implementation Checklist

- [ ] **Step 1**: Add enum and constants (base.py, constants.py)
- [ ] **Step 2**: Create categorization.py data models and implementation
- [ ] **Step 3**: Register in registry and verify basic functionality
- [ ] **Step 4**: Create English AI template
- [ ] **Step 5**: Create Norwegian AI template
- [ ] **Step 6**: Write comprehensive test suite
- [ ] **Final**: Run full test suite and validate deployment

**Remember**: After each step, run `test.sh`, `lint.sh`, and commit changes.

---

_End of Implementation Document_
