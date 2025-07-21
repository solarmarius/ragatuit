# Fill-in-Blank Question Type Implementation

## Overview

This document provides comprehensive documentation for the Fill-in-Blank question type implementation in Rag@UiT. The implementation adds support for generating, validating, and exporting fill-in-blank questions that integrate seamlessly with the existing question generation workflow and Canvas LMS export functionality.

## Architecture

The Fill-in-Blank question type follows the established polymorphic architecture pattern used throughout the question module, ensuring consistency and maintainability.

### Key Components

1. **Data Models** (`backend/src/question/types/fill_in_blank.py`)
   - `BlankData`: Individual blank configuration
   - `FillInBlankData`: Complete question data structure
   - `FillInBlankQuestionType`: Question type implementation

2. **AI Generation Templates** (`backend/src/question/templates/files/`)
   - `batch_fill_in_blank.json`: English question generation
   - `batch_fill_in_blank_no.json`: Norwegian question generation

3. **Registry Integration** (`backend/src/question/types/registry.py`)
   - Automatic registration in question type registry
   - Dynamic type discovery support

4. **Frontend Integration** (Already implemented)
   - Complete UI components for display and editing
   - Type-safe TypeScript interfaces
   - Validation schemas

## Data Structure

### BlankData Model

Represents a single blank within a fill-in-blank question:

```python
class BlankData(BaseModel):
    position: int = Field(ge=1, le=100)
    correct_answer: str = Field(min_length=1, max_length=200)
    answer_variations: list[str] | None = Field(default=None)
    case_sensitive: bool = Field(default=False)
```

**Field Specifications:**
- `position`: Unique position number (1-100) for the blank
- `correct_answer`: Primary correct answer (1-200 characters)
- `answer_variations`: Optional list of acceptable alternative answers (max 10)
- `case_sensitive`: Whether answer matching is case-sensitive (default: false)

### FillInBlankData Model

Represents the complete fill-in-blank question:

```python
class FillInBlankData(BaseQuestionData):
    blanks: list[BlankData] = Field(description="List of blanks in the question")
```

**Validation Rules:**
- Minimum 1 blank, maximum 10 blanks per question
- Each blank must have a unique position
- Blanks are automatically sorted by position
- Inherits `question_text` and `explanation` from `BaseQuestionData`

## Canvas Integration

### Rich Fill In The Blank Format

The implementation exports questions using Canvas's modern "Rich Fill In The Blank" format:

```python
{
    "question_type": "rich-fill-blank",
    "interaction_data": {
        "blanks": [
            {
                "id": "uuid-string",
                "answer_type": "openEntry"
            }
        ]
    },
    "scoring_data": {
        "value": [
            {
                "id": "uuid-string",
                "scoring_data": {
                    "value": "correct_answer",
                    "blank_text": "correct_answer",
                    "scoring_algorithm": "TextCloseEnough"
                }
            }
        ],
        "working_item_body": "question_text"
    },
    "points_possible": number_of_blanks
}
```

### Scoring Algorithms

- **TextCloseEnough**: Default algorithm for case-insensitive matching (handles typos)
- **Equivalence**: Used for case-sensitive matching
- Separate scoring entries for each answer variation

## AI Generation Templates

### Template Structure

Both English and Norwegian templates follow the same structure:

```json
{
    "name": "batch_fill_in_blank",
    "version": "1.0",
    "question_type": "fill_in_blank",
    "system_prompt": "Detailed instructions for AI model...",
    "user_prompt": "Template with variables...",
    "variables": {
        "module_name": "The name of the module",
        "module_content": "The module content to generate questions from",
        "question_count": "Number of questions to generate"
    }
}
```

### Expected AI Output Format

The AI model generates JSON arrays with this structure:

```json
[
    {
        "question_text": "The capital of France is _____ and it has _____ residents.",
        "blanks": [
            {
                "position": 1,
                "correct_answer": "Paris",
                "answer_variations": ["paris", "PARIS"],
                "case_sensitive": false
            },
            {
                "position": 2,
                "correct_answer": "2.2 million",
                "answer_variations": ["2.2M", "2,200,000"],
                "case_sensitive": false
            }
        ],
        "explanation": "Paris is the capital and largest city of France."
    }
]
```

## Implementation Details

### Validation Features

1. **Position Validation**
   - Positions must be unique integers between 1-100
   - Automatic sorting by position for consistency

2. **Answer Validation**
   - Correct answers: 1-200 characters, non-empty
   - Answer variations: maximum 10 per blank
   - Automatic filtering of empty variations
   - Duplicate removal while preserving order

3. **Question Limits**
   - Maximum 10 blanks per question
   - Minimum 1 blank required

### Frontend Compatibility

The backend data structure is designed to match the existing frontend expectations:

```typescript
interface FillInBlankData {
    question_text: string;
    blanks: Array<{
        position: number;
        correct_answer: string;
        answer_variations?: string[];
        case_sensitive?: boolean;
    }>;
    explanation?: string | null;
}
```

## Usage Examples

### Creating a Fill-in-Blank Question

```python
from src.question.types.fill_in_blank import BlankData, FillInBlankData

# Create blanks
blanks = [
    BlankData(
        position=1,
        correct_answer="Paris",
        answer_variations=["paris", "PARIS"],
        case_sensitive=False
    ),
    BlankData(
        position=2,
        correct_answer="Seine",
        answer_variations=["seine", "Seine River"],
        case_sensitive=False
    )
]

# Create question
question = FillInBlankData(
    question_text="The capital of France is _____ and it's located on the _____ river.",
    blanks=blanks,
    explanation="Paris is the capital of France and is situated on the Seine river."
)
```

### Using the Question Type

```python
from src.question.types import get_question_type_registry, QuestionType

# Get the question type from registry
registry = get_question_type_registry()
question_type = registry.get_question_type(QuestionType.FILL_IN_BLANK)

# Validate data
validated_data = question_type.validate_data(raw_data)

# Format for display
display_format = question_type.format_for_display(validated_data)

# Format for Canvas export
canvas_format = question_type.format_for_canvas(validated_data)
```

## Testing

### Test Coverage

The implementation includes comprehensive tests covering:

- **Data Model Validation** (8 tests)
  - BlankData creation and validation
  - Position and answer validation
  - Answer variations processing

- **Question Type Implementation** (10 tests)
  - Data validation and formatting
  - Canvas export format
  - Error handling

- **Registry Integration** (3 tests)
  - Type registration verification
  - Registry access functionality

- **End-to-End Workflow** (2 tests)
  - Complete workflow testing
  - Data round-trip validation

### Running Tests

```bash
# Run all Fill-in-Blank tests
cd backend && source .venv/bin/activate
python -m pytest tests/question/types/test_fill_in_blank.py -v

# Run specific test
python -m pytest tests/question/types/test_fill_in_blank.py::test_fill_in_blank_end_to_end_workflow -v
```

## Configuration

### Environment Variables

No additional environment variables are required. The implementation uses existing configuration:

- `QUIZ_LANGUAGE`: Supports both English ("en") and Norwegian ("no")
- LLM provider configuration (OpenAI, mock, etc.)

### Template Configuration

Templates are automatically loaded from:
- `backend/src/question/templates/files/batch_fill_in_blank.json`
- `backend/src/question/templates/files/batch_fill_in_blank_no.json`

## Performance Considerations

### Database Impact

- Uses existing polymorphic `Question` model
- JSONB storage for question data (no schema changes)
- Efficient indexing on `question_type` field

### Memory Usage

- Blanks are stored as lightweight objects
- Answer variations are optional and filtered
- Automatic deduplication reduces storage overhead

### Canvas Export Performance

- UUID generation for each blank
- Efficient mapping to Canvas format
- Minimal API calls required

## Troubleshooting

### Common Issues

1. **Template Not Found**
   ```
   ValueError: No template found for question type fill_in_blank
   ```
   - Verify template files exist in correct location
   - Check template naming convention
   - Ensure `question_type` field matches enum value

2. **Validation Errors**
   ```
   ValidationError: Each blank must have a unique position
   ```
   - Check for duplicate position values
   - Ensure positions are integers ≥ 1
   - Verify blanks array is not empty

3. **Canvas Export Issues**
   - Verify Rich Fill In The Blank format compatibility
   - Check Canvas API version support
   - Ensure proper UUID generation

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger("question_type_registry").setLevel(logging.DEBUG)
```

## Future Enhancements

### Planned Features

1. **Advanced Scoring Options**
   - Partial credit for close answers
   - Custom scoring algorithms
   - Weighted blank scoring

2. **Enhanced AI Generation**
   - Context-aware blank placement
   - Difficulty level targeting
   - Topic-specific templates

3. **Extended Canvas Support**
   - Dropdown and word bank options
   - Rich text formatting
   - Mathematical expression support

### Extension Points

The implementation is designed for easy extension:

- Custom scoring algorithms via `scoring_algorithm` field
- Additional blank types through `answer_type` field
- Template customization for specific use cases

## Migration Guide

### From MCQ to Fill-in-Blank

For users migrating from Multiple Choice Questions:

1. **Question Structure**
   ```python
   # MCQ
   {
       "question_text": "What is the capital of France?",
       "option_a": "London",
       "option_b": "Paris",
       "option_c": "Berlin",
       "option_d": "Madrid",
       "correct_answer": "B"
   }

   # Fill-in-Blank
   {
       "question_text": "The capital of France is _____.",
       "blanks": [
           {
               "position": 1,
               "correct_answer": "Paris",
               "answer_variations": ["paris", "PARIS"]
           }
       ]
   }
   ```

2. **Canvas Export**
   - MCQ: `multiple_choice_question`
   - Fill-in-Blank: `rich-fill-blank`

### Database Migration

No database migration required - uses existing polymorphic structure.

## API Reference

### Question Type Methods

#### `validate_data(data: dict[str, Any]) -> FillInBlankData`
Validates and parses raw question data.

**Parameters:**
- `data`: Dictionary with question_text, blanks, and optional explanation

**Returns:**
- `FillInBlankData`: Validated question data

**Raises:**
- `ValidationError`: If data is invalid

#### `format_for_display(data: BaseQuestionData) -> dict[str, Any]`
Formats question data for API display.

**Parameters:**
- `data`: FillInBlankData instance

**Returns:**
- Dictionary with formatted question data

#### `format_for_canvas(data: BaseQuestionData) -> dict[str, Any]`
Formats question data for Canvas Rich Fill In The Blank export.

**Parameters:**
- `data`: FillInBlankData instance

**Returns:**
- Dictionary with Canvas-formatted question data

### Data Model Methods

#### `FillInBlankData.get_blank_by_position(position: int) -> BlankData | None`
Retrieves a blank by its position.

#### `FillInBlankData.get_all_answers() -> dict[int, list[str]]`
Returns all possible answers for each blank position.

## Contributing

### Adding New Features

1. **New Validation Rules**
   - Add validators to `BlankData` or `FillInBlankData`
   - Update tests to cover new validation
   - Document validation behavior

2. **Canvas Format Extensions**
   - Modify `format_for_canvas` method
   - Test with Canvas LMS integration
   - Update documentation

3. **Template Improvements**
   - Update template files
   - Test AI generation quality
   - Consider backward compatibility

### Code Style

Follow existing patterns:
- Use type hints for all parameters
- Include comprehensive docstrings
- Add validation for user inputs
- Write tests for new functionality

## Conclusion

The Fill-in-Blank question type implementation provides a complete, production-ready solution that integrates seamlessly with Rag@UiT's existing architecture. The implementation follows established patterns, includes comprehensive testing, and supports both English and Norwegian question generation with Canvas LMS integration.

The feature is immediately usable and provides a solid foundation for future enhancements while maintaining full backward compatibility with existing Multiple Choice functionality.
