# Language Support Implementation Documentation

## Overview

This document describes the implementation of multi-language support in the Rag@UiT quiz generation system. The feature allows users to select the language (English or Norwegian) for AI-generated quiz questions during the quiz creation process.

## Architecture Overview

### Language Flow

```
User Selection → Quiz Creation → Content Extraction → Question Generation → Template Selection
     (UI)           (API)         (Orchestrator)      (Service Layer)    (Template Manager)
```

### Key Components

1. **QuizLanguage Enum** (`question/types/base.py`)
   - Defines supported languages: ENGLISH = "en", NORWEGIAN = "no"
   - Placed in question module to avoid circular imports

2. **Quiz Model** (`quiz/models.py`)
   - Added `language` field with default value `QuizLanguage.ENGLISH`
   - Persisted in database for entire quiz lifecycle

3. **Template System** (`question/templates/`)
   - Language-aware template selection
   - Norwegian templates use `_no` suffix convention
   - Automatic fallback to English if Norwegian template not found

4. **Frontend UI** (`components/QuizCreation/QuizSettingsStep.tsx`)
   - Card-based language selection interface
   - Consistent with existing UI patterns
   - Visual feedback for selected language

## Implementation Details

### Backend Implementation

#### 1. Database Schema
```python
# quiz/models.py
class Quiz(SQLModel, table=True):
    # ... existing fields ...
    language: QuizLanguage = Field(
        default=QuizLanguage.ENGLISH,
        description="Language for question generation",
    )
```

#### 2. Template Naming Convention
```
English:    default_multiple_choice.json
Norwegian:  default_multiple_choice_no.json
```

#### 3. Template Selection Logic
```python
# question/templates/manager.py
def get_template(self, question_type, template_name=None, language=None):
    if language and language != QuizLanguage.ENGLISH:
        # Try language-specific template first
        language_suffix = f"_{language}"
        template_path = base_path + language_suffix + ".json"
        if template_path.exists():
            return load_template(template_path)

    # Fallback to English template
    return load_template(base_path + ".json")
```

#### 4. Generation Flow Integration
```python
# quiz/orchestrator.py
async def orchestrate_quiz_question_generation(
    quiz_id: UUID,
    target_question_count: int,
    llm_model: str,
    llm_temperature: float,
    language: QuizLanguage,  # Added language parameter
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE,
):
    # Language flows through entire generation pipeline
    generation_parameters = GenerationParameters(
        target_count=target_question_count,
        language=language
    )
```

### Frontend Implementation

#### 1. UI Component
```tsx
// components/QuizCreation/QuizSettingsStep.tsx
const languageOptions = [
  {
    value: QUIZ_LANGUAGES.ENGLISH,
    label: "English",
    description: "Generate questions in English",
  },
  {
    value: QUIZ_LANGUAGES.NORWEGIAN,
    label: "Norwegian",
    description: "Generate questions in Norwegian (Norsk)",
  },
]

// Card-based selection UI
<RadioGroup.Root value={settings.language}>
  {languageOptions.map((option) => (
    <Card.Root
      key={option.value}
      onClick={() => updateSettings({ language: option.value })}
    >
      {/* Card content */}
    </Card.Root>
  ))}
</RadioGroup.Root>
```

#### 2. Type Definitions
```typescript
// Generated from backend OpenAPI
export type QuizLanguage = "en" | "no"

// Constants
export const QUIZ_LANGUAGES = {
  ENGLISH: "en",
  NORWEGIAN: "no",
} as const
```

## Template Structure

### English Template Example
```json
{
  "name": "default_multiple_choice",
  "description": "Default template for generating multiple choice questions",
  "language": "en",
  "version": "1.0.0",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert educator creating multiple-choice questions..."
    }
  ]
}
```

### Norwegian Template Example
```json
{
  "name": "default_multiple_choice_no",
  "description": "Standard mal for generering av flervalgsspørsmål",
  "language": "no",
  "version": "1.0.0",
  "messages": [
    {
      "role": "system",
      "content": "Du er en ekspert pedagog som lager flervalgsspørsmål..."
    }
  ]
}
```

## Error Handling

### Missing Template Handling
1. System attempts to load language-specific template
2. If not found, falls back to English template
3. If English template also missing, raises TemplateNotFoundError
4. Quiz status set to FAILED with appropriate failure reason

### Validation
- Language field validated at API level
- Only accepts values from QuizLanguage enum
- Default to English if not specified

## Testing Strategy

### Backend Tests
- Unit tests for language field validation
- Template selection logic tests
- Integration tests for full generation flow
- Fallback mechanism tests

### Frontend Tests
- UI component rendering tests
- Form validation with language field
- API integration tests
- End-to-end workflow tests

## Future Extensibility

### Adding New Languages

1. **Update Enum**
   ```python
   class QuizLanguage(str, Enum):
       ENGLISH = "en"
       NORWEGIAN = "no"
       SWEDISH = "sv"  # New language
   ```

2. **Create Templates**
   - Copy existing templates
   - Add language suffix (e.g., `_sv`)
   - Translate content

3. **Update Frontend**
   ```typescript
   export const QUIZ_LANGUAGES = {
     ENGLISH: "en",
     NORWEGIAN: "no",
     SWEDISH: "sv",  // New language
   } as const
   ```

4. **Add UI Option**
   ```typescript
   const languageOptions = [
     // ... existing options ...
     {
       value: QUIZ_LANGUAGES.SWEDISH,
       label: "Swedish",
       description: "Generate questions in Swedish",
     },
   ]
   ```

### Considerations for Scale

- **Template Management**: Consider database storage for templates as language count grows
- **Translation Quality**: Establish review process for language-specific educational terminology
- **Performance**: Template caching may be needed with many languages
- **UI/UX**: Consider dropdown instead of cards if supporting 5+ languages

## Migration Guide

### Database Migration
```sql
ALTER TABLE quiz ADD COLUMN language VARCHAR(2) DEFAULT 'en';
```

### Data Migration
- Existing quizzes default to English
- No data transformation required

## Best Practices

1. **Template Quality**: Ensure educational terminology is appropriate for each language
2. **Consistent Naming**: Always use ISO 639-1 language codes
3. **Fallback Strategy**: Always provide English templates as baseline
4. **User Communication**: Clear UI messaging about available languages
5. **Testing**: Test each language template with actual content

## Conclusion

The language support implementation provides a robust, extensible foundation for multi-language quiz generation. The architecture supports easy addition of new languages while maintaining system stability through fallback mechanisms and comprehensive error handling.
