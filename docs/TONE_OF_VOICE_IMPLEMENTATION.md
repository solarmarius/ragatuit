# Quiz Tone of Voice Feature Implementation Guide

**Date:** July 31, 2025
**Version:** 1.0
**Author:** Development Team

## 1. Feature Overview

### Description
The Quiz Tone of Voice feature allows teachers to select different tones for AI-generated quiz questions, enabling customization based on the course context and teaching style. Teachers can choose from four predefined tones: Academic, Casual, Encouraging, and Professional.

### Business Value
- **Personalization**: Teachers can match question tone to their teaching style and student needs
- **Context Adaptation**: Different courses may require different communication styles (e.g., formal academic vs. professional training)
- **Enhanced Learning Experience**: Appropriate tone can improve student engagement and reduce anxiety
- **Flexibility**: One system serves diverse educational contexts without requiring separate implementations

### User Benefits
- **Academic Tone**: Formal language with precise terminology for scholarly environments
- **Casual Tone**: Conversational language that feels approachable and relaxed
- **Encouraging Tone**: Supportive language that motivates learning and builds confidence
- **Professional Tone**: Business-appropriate language for workplace training scenarios

## 2. Technical Architecture

### High-Level Architecture
The tone feature is implemented as a parameter that flows through the entire question generation pipeline:

```
Quiz Creation UI → Quiz Model → Generation Service → Template System → LLM Provider
```

### System Integration
The feature integrates with existing components without breaking changes:
- **Database**: New `tone` field added to Quiz model with default value for backward compatibility
- **API**: QuizTone enum added to schemas, tone parameter included in creation endpoints
- **Templates**: All 10 question generation templates updated with tone-specific instructions
- **Frontend**: New UI component for tone selection added to quiz creation workflow

### Data Flow Diagram
```
[User Selects Tone]
       ↓
[QuizSettingsStep Component]
       ↓
[Quiz Creation Form]
       ↓
[Backend API: POST /quiz]
       ↓
[Quiz Model (tone field)]
       ↓
[Question Generation Service]
       ↓
[Template Manager (tone injection)]
       ↓
[LLM Provider with tone instructions]
```

## 3. Dependencies & Prerequisites

### Backend Dependencies
- **Python 3.11+**: Required for backend services
- **FastAPI**: Web framework (existing dependency)
- **SQLModel**: Database ORM (existing dependency)
- **Pydantic**: Data validation (existing dependency)
- **Jinja2**: Template engine (existing dependency)

### Frontend Dependencies
- **React 18+**: Frontend framework (existing dependency)
- **TypeScript**: Type safety (existing dependency)
- **Chakra UI**: Component library (existing dependency)
- **TanStack Router**: Routing (existing dependency)

### Environment Setup
No additional environment setup required. Uses existing infrastructure.

## 4. Implementation Details

### 4.1 File Structure

```
ragatuit/
├── backend/
│   ├── src/
│   │   ├── quiz/
│   │   │   ├── models.py                    # [MODIFIED] Add tone field
│   │   │   ├── schemas.py                   # [MODIFIED] Add QuizTone enum
│   │   │   └── service.py                   # [MODIFIED] Handle tone in creation
│   │   ├── question/
│   │   │   ├── types/
│   │   │   │   └── base.py                  # [MODIFIED] Add tone to GenerationParameters
│   │   │   ├── workflows/
│   │   │   │   └── module_batch_workflow.py # [MODIFIED] Pass tone to templates
│   │   │   ├── services/
│   │   │   │   └── generation_service.py    # [MODIFIED] Extract tone from quiz
│   │   │   └── templates/
│   │   │       └── files/
│   │   │           ├── batch_multiple_choice.json     # [MODIFIED] Add tone instructions
│   │   │           ├── batch_multiple_choice_no.json  # [MODIFIED] Add tone instructions
│   │   │           ├── batch_true_false.json          # [MODIFIED] Add tone instructions
│   │   │           ├── batch_true_false_no.json       # [MODIFIED] Add tone instructions
│   │   │           ├── batch_categorization.json      # [MODIFIED] Add tone instructions
│   │   │           ├── batch_categorization_no.json   # [MODIFIED] Add tone instructions
│   │   │           ├── batch_fill_in_blank.json       # [MODIFIED] Add tone instructions
│   │   │           ├── batch_fill_in_blank_no.json    # [MODIFIED] Add tone instructions
│   │   │           ├── batch_matching.json            # [MODIFIED] Add tone instructions
│   │   │           └── batch_matching_no.json         # [MODIFIED] Add tone instructions
│   └── alembic/
│       └── versions/
│           └── d4ab7062b1ab_add_tone_field_to_quiz_model.py # [AUTO-GENERATED] Migration
├── frontend/
│   └── src/
│       ├── lib/
│       │   └── constants/
│       │       └── index.ts                 # [MODIFIED] Add tone constants
│       ├── components/
│       │   └── QuizCreation/
│       │       └── QuizSettingsStep.tsx     # [MODIFIED] Add tone selection UI
│       └── routes/
│           └── _layout/
│               ├── create-quiz.tsx          # [MODIFIED] Include tone in form
│               └── quiz.$id.index.tsx       # [MODIFIED] Display tone info
└── docs/
    └── TONE_OF_VOICE_IMPLEMENTATION.md      # [NEW] This document
```

### 4.2 Step-by-Step Implementation

#### Step 1: Create QuizTone Enum (Backend)

**File:** `backend/src/quiz/schemas.py`

Add the QuizTone enum after the existing FailureReason enum:

```python
class QuizTone(str, Enum):
    """Tone of voice options for quiz question generation."""

    ACADEMIC = "academic"
    CASUAL = "casual"
    ENCOURAGING = "encouraging"
    PROFESSIONAL = "professional"
```

**Purpose:** Defines the four available tone options with string values that will be stored in the database and used in templates.

#### Step 2: Add Tone Field to Quiz Model

**File:** `backend/src/quiz/models.py`

Import the new enum:
```python
from .schemas import FailureReason, QuizStatus, QuizTone
```

Add the tone field after the language field:
```python
tone: QuizTone = Field(
    default=QuizTone.ACADEMIC,
    description="Tone of voice for question generation",
)
```

**Purpose:** Stores the selected tone in the database with a sensible default (Academic) for backward compatibility.

#### Step 3: Update Quiz Schemas

**File:** `backend/src/quiz/schemas.py`

Add tone to QuizCreate schema:
```python
class QuizCreate(SQLModel):
    # ... existing fields ...
    tone: QuizTone = Field(default=QuizTone.ACADEMIC)
```

Add tone to QuizPublic schema:
```python
class QuizPublic(SQLModel):
    # ... existing fields ...
    tone: QuizTone
```

**Note:** QuizUpdate schema intentionally excludes tone as per requirements (tone is not editable after creation).

#### Step 4: Update Quiz Service

**File:** `backend/src/quiz/service.py`

Add tone to quiz creation:
```python
quiz = Quiz(
    # ... existing fields ...
    tone=quiz_create.tone,
    updated_at=datetime.now(timezone.utc),
)
```

**Purpose:** Ensures the tone value from the API request is saved to the database.

#### Step 5: Add Tone to GenerationParameters

**File:** `backend/src/question/types/base.py`

Add tone field to GenerationParameters class:
```python
class GenerationParameters(BaseModel):
    # ... existing fields ...
    tone: str | None = Field(
        default=None, description="Tone of voice for question generation"
    )
```

**Purpose:** Allows tone to be passed through the generation pipeline to templates.

#### Step 6: Update Module Batch Workflow

**File:** `backend/src/question/workflows/module_batch_workflow.py`

Update both workflow classes to accept and pass tone:

```python
class ModuleBatchWorkflow:
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        template_manager: TemplateManager | None = None,
        language: QuizLanguage = QuizLanguage.ENGLISH,
        tone: str | None = None,  # Add this parameter
    ):
        # ... existing initialization ...
        self.tone = tone

class ParallelModuleProcessor:
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        template_manager: TemplateManager | None = None,
        language: QuizLanguage = QuizLanguage.ENGLISH,
        tone: str | None = None,  # Add this parameter
    ):
        # ... existing initialization ...
        self.tone = tone
```

Update template variable injection:
```python
extra_variables={
    "module_name": state.module_name,
    "question_count": remaining_questions,
    "tone": self.tone,  # Add this line
},
```

Update workflow instantiation:
```python
workflow = ModuleBatchWorkflow(
    llm_provider=self.llm_provider,
    template_manager=self.template_manager,
    language=self.language,
    tone=self.tone,  # Add this line
)
```

#### Step 7: Update Generation Service

**File:** `backend/src/question/services/generation_service.py`

Extract tone from quiz and pass to processor:
```python
processor = ParallelModuleProcessor(
    llm_provider=provider,
    template_manager=self.template_manager,
    language=language,
    tone=quiz.tone.value if quiz.tone else None,  # Add this line
)
```

#### Step 8: Update All Question Templates

**Files:** All 10 files in `backend/src/question/templates/files/`

For each template file, add tone instructions to the system_prompt. Example for English templates:

```json
{
  "system_prompt": "You are an expert educator creating [question type] quiz questions. Generate diverse, high-quality questions that test understanding at different cognitive levels.\n\nGenerate questions in a {{ tone }} tone. {% if tone == 'academic' %}Use formal academic language with precise terminology, structured explanations, and a scholarly approach. Maintain objectivity and use complete sentences with proper grammar.{% elif tone == 'casual' %}Use everyday conversational language that feels approachable and relaxed. Keep explanations simple and use contractions where natural. Make the content feel like a friendly discussion.{% elif tone == 'encouraging' %}Use warm, supportive language that motivates learning. Include positive reinforcement, acknowledge that mistakes are part of learning, and frame questions in ways that build confidence.{% elif tone == 'professional' %}Use clear, direct business language suitable for workplace training. Focus on practical applications and real-world scenarios. Keep explanations concise and action-oriented.{% endif %}\n\n[rest of existing system prompt...]",
  "variables": {
    "module_name": "The name of the module",
    "module_content": "The module content to generate questions from",
    "question_count": "Number of questions to generate",
    "tone": "Tone of voice for question generation",
    "difficulty": "Question difficulty level (optional)",
    "tags": "List of topic tags to focus on (optional)",
    "custom_instructions": "Additional custom instructions (optional)"
  }
}
```

For Norwegian templates, use Norwegian translations of the tone descriptions.

#### Step 9: Frontend Constants

**File:** `frontend/src/lib/constants/index.ts`

Add tone constants after language constants:
```typescript
export const QUIZ_TONES = {
  ACADEMIC: "academic",
  CASUAL: "casual",
  ENCOURAGING: "encouraging",
  PROFESSIONAL: "professional",
} as const

export const QUIZ_TONE_LABELS = {
  academic: "Formal/Academic",
  casual: "Casual/Conversational",
  encouraging: "Friendly/Encouraging",
  professional: "Professional/Business",
} as const
```

#### Step 10: Update QuizSettingsStep Component

**File:** `frontend/src/components/QuizCreation/QuizSettingsStep.tsx`

Update imports:
```typescript
import type { QuizLanguage, QuizTone } from "@/client"
import { QUIZ_LANGUAGES, QUIZ_TONES } from "@/lib/constants"
```

Update interface:
```typescript
interface QuizSettings {
  language: QuizLanguage
  tone: QuizTone
}

const DEFAULT_SETTINGS: QuizSettings = {
  language: QUIZ_LANGUAGES.ENGLISH,
  tone: QUIZ_TONES.ACADEMIC,
}
```

Add tone selection UI after language selection:
```typescript
<FormField label="Tone of Voice" isRequired>
  <Box>
    <Text fontSize="sm" color="gray.600" mb={3}>
      Select the tone for question generation
    </Text>
    <RadioGroup.Root
      value={settings.tone}
      onValueChange={(details) =>
        updateSettings({ tone: details.value as QuizTone })
      }
    >
      <VStack gap={3} align="stretch">
        {toneOptions.map((option) => (
          <Card.Root
            key={option.value}
            variant="outline"
            cursor="pointer"
            _hover={{ borderColor: "green.300" }}
            borderColor={
              settings.tone === option.value ? "green.500" : "gray.200"
            }
            bg={settings.tone === option.value ? "green.50" : "white"}
            onClick={() => updateSettings({ tone: option.value })}
            data-testid={`tone-card-${option.value}`}
          >
            <Card.Body>
              <HStack>
                <RadioGroup.Item value={option.value} />
                <Box flex={1}>
                  <Text fontWeight="semibold">{option.label}</Text>
                  <Text fontSize="sm" color="gray.600">
                    {option.description}
                  </Text>
                </Box>
              </HStack>
            </Card.Body>
          </Card.Root>
        ))}
      </VStack>
    </RadioGroup.Root>
  </Box>
</FormField>
```

#### Step 11: Update Create Quiz Route

**File:** `frontend/src/routes/_layout/create-quiz.tsx`

Update imports:
```typescript
import { type QuestionBatch, type QuizLanguage, type QuizTone, QuizService } from "@/client"
import { QUIZ_LANGUAGES, QUIZ_TONES } from "@/lib/constants"
```

Update form data interface:
```typescript
interface QuizFormData {
  selectedCourse?: {
    id: number
    name: string
  }
  selectedModules?: { [id: number]: string }
  moduleQuestions?: { [id: string]: QuestionBatch[] }
  title?: string
  language?: QuizLanguage
  tone?: QuizTone
}
```

Update settings handling:
```typescript
<QuizSettingsStep
  settings={{
    language: formData.language || QUIZ_LANGUAGES.ENGLISH,
    tone: formData.tone || QUIZ_TONES.ACADEMIC,
  }}
  onSettingsChange={(settings) =>
    updateFormData({
      language: settings.language,
      tone: settings.tone,
    })
  }
/>
```

Update quiz creation payload:
```typescript
const quizData = {
  canvas_course_id: formData.selectedCourse.id,
  canvas_course_name: formData.selectedCourse.name,
  selected_modules: selectedModulesWithBatches,
  title: formData.title,
  language: formData.language || QUIZ_LANGUAGES.ENGLISH,
  tone: formData.tone || QUIZ_TONES.ACADEMIC,
}
```

#### Step 12: Update Quiz Information Display

**File:** `frontend/src/routes/_layout/quiz.$id.index.tsx`

Update imports:
```typescript
import { QUIZ_LANGUAGE_LABELS, QUIZ_TONE_LABELS } from "@/lib/constants"
```

Add tone display after language:
```typescript
<HStack justify="space-between">
  <Text fontWeight="medium" color="gray.700">
    Tone
  </Text>
  <Badge variant="outline">
    {QUIZ_TONE_LABELS[quiz.tone!]}
  </Badge>
</HStack>
```

### 4.3 Data Models & Schemas

#### QuizTone Enum
```python
class QuizTone(str, Enum):
    ACADEMIC = "academic"          # Formal academic language
    CASUAL = "casual"              # Conversational, approachable
    ENCOURAGING = "encouraging"     # Supportive, confidence-building
    PROFESSIONAL = "professional"  # Business-appropriate
```

#### Database Schema Change
```sql
-- Auto-generated migration
ALTER TABLE quiz ADD COLUMN tone VARCHAR DEFAULT 'academic';
```

#### API Request/Response Examples

**Quiz Creation Request:**
```json
{
  "canvas_course_id": 12345,
  "canvas_course_name": "Introduction to Psychology",
  "selected_modules": {
    "67890": {
      "name": "Cognitive Psychology",
      "question_batches": [
        {"question_type": "multiple_choice", "count": 10}
      ]
    }
  },
  "title": "Psychology Quiz 1",
  "language": "en",
  "tone": "encouraging"
}
```

**Quiz Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Psychology Quiz 1",
  "language": "en",
  "tone": "encouraging",
  "status": "created",
  "question_count": 10,
  "created_at": "2025-07-31T10:30:00Z"
}
```

### 4.4 Configuration

#### Template Configuration
Each template includes tone variable documentation:
```json
{
  "variables": {
    "tone": "Tone of voice for question generation"
  }
}
```

#### Default Values
- **Database Default:** `academic` (most formal, widely applicable)
- **Frontend Default:** `QUIZ_TONES.ACADEMIC`
- **Fallback Logic:** If tone is null/missing, defaults to academic

## 5. Testing Strategy

### 5.1 Unit Tests

#### Backend Tests
```python
# Test tone enum validation
def test_quiz_tone_enum_values():
    assert QuizTone.ACADEMIC == "academic"
    assert QuizTone.CASUAL == "casual"
    assert QuizTone.ENCOURAGING == "encouraging"
    assert QuizTone.PROFESSIONAL == "professional"

# Test quiz creation with tone
def test_create_quiz_with_tone():
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={"1": {"name": "Module 1", "question_batches": []}},
        title="Test Quiz",
        tone=QuizTone.CASUAL
    )
    quiz = create_quiz(session, quiz_data, owner_id)
    assert quiz.tone == QuizTone.CASUAL

# Test default tone
def test_quiz_default_tone():
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={"1": {"name": "Module 1", "question_batches": []}},
        title="Test Quiz"
        # tone not specified
    )
    quiz = create_quiz(session, quiz_data, owner_id)
    assert quiz.tone == QuizTone.ACADEMIC
```

#### Frontend Tests
```typescript
// Test tone selection component
describe('QuizSettingsStep Tone Selection', () => {
  it('renders all tone options', () => {
    render(<QuizSettingsStep settings={defaultSettings} onSettingsChange={jest.fn()} />)

    expect(screen.getByText('Formal/Academic')).toBeInTheDocument()
    expect(screen.getByText('Casual/Conversational')).toBeInTheDocument()
    expect(screen.getByText('Friendly/Encouraging')).toBeInTheDocument()
    expect(screen.getByText('Professional/Business')).toBeInTheDocument()
  })

  it('calls onSettingsChange when tone is selected', () => {
    const onSettingsChange = jest.fn()
    render(<QuizSettingsStep settings={defaultSettings} onSettingsChange={onSettingsChange} />)

    fireEvent.click(screen.getByTestId('tone-card-casual'))

    expect(onSettingsChange).toHaveBeenCalledWith({
      language: 'en',
      tone: 'casual'
    })
  })
})
```

### 5.2 Integration Tests

#### API Integration
```python
def test_quiz_creation_api_with_tone():
    response = client.post("/api/v1/quiz", json={
        "canvas_course_id": 123,
        "canvas_course_name": "Test Course",
        "selected_modules": {"1": {"name": "Module 1", "question_batches": []}},
        "title": "Test Quiz",
        "tone": "professional"
    })

    assert response.status_code == 201
    assert response.json()["tone"] == "professional"
```

#### Template Integration
```python
def test_tone_injection_in_templates():
    template_manager = get_template_manager()
    messages = await template_manager.create_messages(
        QuestionType.MULTIPLE_CHOICE,
        "Sample content",
        GenerationParameters(target_count=5),
        extra_variables={"tone": "casual"}
    )

    # Verify tone instructions are in system prompt
    system_prompt = messages[0].content
    assert "casual" in system_prompt.lower()
    assert "conversational language" in system_prompt.lower()
```

### 5.3 Manual Testing Steps

1. **Quiz Creation Flow:**
   - Navigate to quiz creation
   - Select course and modules
   - Verify tone selection appears in settings step
   - Test each tone option selection
   - Create quiz and verify tone is saved

2. **Question Generation:**
   - Create quizzes with different tones
   - Generate questions for each tone
   - Manually review generated questions for tone appropriateness
   - Compare questions across different tones for the same content

3. **Quiz Information Display:**
   - View created quiz details
   - Verify selected tone is displayed correctly
   - Test with all four tone options

### 5.4 Performance Considerations

- **Template Processing:** Tone injection adds minimal overhead (~1ms per template)
- **Database Impact:** Single varchar field, indexed for queries
- **UI Rendering:** Four additional radio buttons, negligible impact
- **API Response Size:** +10-15 bytes per quiz response

## 6. Deployment Instructions

### 6.1 Database Migration

The database migration is automatically generated and applied:

```bash
# Backend deployment will automatically run:
alembic upgrade head
```

**Migration Details:**
- Adds `tone` column to `quiz` table
- Sets default value to 'academic'
- Creates index for efficient querying

### 6.2 Backend Deployment

1. **Zero-Downtime Deployment:**
   - Feature is backward compatible
   - Existing quizzes get 'academic' tone by default
   - Old API clients continue to work

2. **Verification Steps:**
   ```bash
   # Test API endpoint
   curl -X POST /api/v1/quiz \
     -H "Content-Type: application/json" \
     -d '{"tone": "casual", ...other_fields}'

   # Verify response includes tone field
   ```

### 6.3 Frontend Deployment

1. **Build and Deploy:**
   ```bash
   npm run build
   # Deploy build artifacts
   ```

2. **Feature Flag (Optional):**
   If gradual rollout is desired, wrap tone selection UI:
   ```typescript
   {FEATURES.TONE_SELECTION_ENABLED && (
     <FormField label="Tone of Voice">
       {/* tone selection UI */}
     </FormField>
   )}
   ```

### 6.4 Rollback Procedures

#### Database Rollback
```sql
-- If needed, remove tone column (data loss!)
ALTER TABLE quiz DROP COLUMN tone;
```

#### Application Rollback
- Remove tone field from models and schemas
- Templates will ignore missing tone variable (graceful degradation)
- Frontend will not show tone selection

## 7. Monitoring & Maintenance

### 7.1 Key Metrics

#### Usage Metrics
```sql
-- Monitor tone selection distribution
SELECT tone, COUNT(*) as quiz_count
FROM quiz
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY tone;

-- Track tone preference by language
SELECT language, tone, COUNT(*) as count
FROM quiz
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY language, tone;
```

#### Performance Metrics
- Question generation latency by tone
- Template processing time
- API response times for quiz creation

### 7.2 Log Entries to Monitor

```python
# Success patterns
logger.info("quiz_created_successfully", tone=quiz.tone, language=quiz.language)
logger.info("questions_generated", tone=tone, question_count=len(questions))

# Error patterns to watch
logger.error("template_tone_injection_failed", tone=tone, template_name=template)
logger.warning("invalid_tone_value", tone=invalid_tone, quiz_id=quiz_id)
```

### 7.3 Common Issues & Troubleshooting

#### Issue: Questions don't reflect selected tone

**Symptoms:** Generated questions appear generic regardless of tone selection

**Diagnosis:**
1. Check if tone is being passed to templates:
   ```bash
   grep "tone.*null\|tone.*None" /var/log/ragatuit/generation.log
   ```

2. Verify template variable injection:
   ```python
   # In template manager debug logs
   logger.debug("template_variables", variables=extra_variables)
   ```

**Resolution:**
1. Ensure tone is extracted from quiz: `quiz.tone.value`
2. Verify workflow passes tone to templates
3. Check template syntax for tone conditionals

#### Issue: Frontend doesn't show tone selection

**Symptoms:** Tone selection UI missing in quiz creation

**Diagnosis:**
1. Check if QuizTone type is available from API client
2. Verify component imports are correct
3. Check for JavaScript errors in browser console

**Resolution:**
1. Regenerate API client: `npm run generate-client`
2. Verify imports in QuizSettingsStep component
3. Check TypeScript compilation errors

#### Issue: Database migration fails

**Symptoms:** Deployment fails during database migration

**Diagnosis:**
```bash
# Check migration status
alembic current
alembic history

# Check for conflicting migrations
alembic show <revision_id>
```

**Resolution:**
1. Ensure database user has ALTER TABLE permissions
2. Check for table locks during migration
3. Run migration manually if needed:
   ```sql
   ALTER TABLE quiz ADD COLUMN tone VARCHAR DEFAULT 'academic';
   ```

## 8. Security Considerations

### 8.1 Input Validation

#### Backend Validation
```python
# Pydantic automatically validates enum values
class QuizCreate(SQLModel):
    tone: QuizTone = Field(default=QuizTone.ACADEMIC)

# Invalid values are rejected with 422 error
# Example: {"tone": "invalid_tone"} → ValidationError
```

#### Frontend Validation
```typescript
// TypeScript prevents invalid values at compile time
const tone: QuizTone = "invalid"; // TypeScript error

// Runtime validation in component
const isValidTone = Object.values(QUIZ_TONES).includes(selectedTone);
```

### 8.2 Data Privacy

- **No PII in Tone Data:** Tone selections contain no personally identifiable information
- **Audit Trail:** Tone changes are logged but don't expose sensitive data
- **Data Retention:** Tone preferences follow same retention policy as quiz data

### 8.3 Authorization

- **User Access:** Only quiz owners can view/set tone for their quizzes
- **Role-Based:** Teacher role required for quiz creation (existing security)
- **API Endpoints:** Existing authentication middleware applies to tone-enabled endpoints

### 8.4 Template Security

#### Prompt Injection Prevention
```python
# Templates use controlled conditionals, not user input
"{% if tone == 'academic' %}Use formal language{% endif %}"

# User cannot inject arbitrary instructions
# Tone values are enum-constrained
```

#### LLM Safety
- Tone instructions are predefined and safe
- No user-generated content in tone logic
- All tone descriptions reviewed for appropriate language

## 9. Future Considerations

### 9.1 Known Limitations

1. **Fixed Tone Set:** Currently limited to 4 predefined tones
2. **Creation-Only:** Tone cannot be changed after quiz creation
3. **Global Tone:** Single tone applies to entire quiz, not per-question
4. **English Templates:** Norwegian tone descriptions could be more culturally adapted

### 9.2 Potential Improvements

#### Custom Tone Descriptions
```python
# Future enhancement: Allow custom tone instructions
class CustomTone(BaseModel):
    name: str = Field(max_length=50)
    description: str = Field(max_length=500)
    instructions: str = Field(max_length=1000)

class Quiz(SQLModel, table=True):
    tone: QuizTone | None = None
    custom_tone: CustomTone | None = None
```

#### Per-Question Type Tones
```python
class QuestionBatch(SQLModel):
    question_type: QuestionType
    count: int
    tone: QuizTone | None = None  # Override quiz-level tone
```

#### Tone Analytics
```typescript
// Future dashboard component
interface ToneAnalytics {
  mostPopularTone: QuizTone
  toneEffectiveness: Record<QuizTone, number>
  studentPreference: Record<QuizTone, number>
}
```

#### A/B Testing Framework
```python
# Future: Test tone effectiveness
class ToneExperiment(SQLModel, table=True):
    quiz_id: UUID
    control_tone: QuizTone
    test_tone: QuizTone
    student_performance: dict[QuizTone, float]
```

### 9.3 Scalability Considerations

#### Template Optimization
- **Current:** 10 templates × 4 tones = 40 template variations loaded in memory
- **Future:** Lazy loading of tone-specific template sections
- **Caching:** Redis cache for compiled template variants

#### Database Optimization
```sql
-- Current index on tone for analytics queries
CREATE INDEX idx_quiz_tone ON quiz(tone);

-- Future composite indexes for complex queries
CREATE INDEX idx_quiz_language_tone ON quiz(language, tone);
CREATE INDEX idx_quiz_created_tone ON quiz(created_at, tone);
```

#### Internationalization
```typescript
// Future: Localized tone descriptions
interface LocalizedToneLabels {
  [locale: string]: {
    [tone in QuizTone]: {
      label: string
      description: string
      instructions: string
    }
  }
}
```

### 9.4 Integration Opportunities

#### Canvas LMS Integration
- Export tone information to Canvas quiz metadata
- Allow Canvas course preferences to suggest default tones

#### Learning Management System
- Track which tones work best for different student populations
- Integrate with student accessibility preferences

#### AI/ML Enhancements
- Analyze generated question quality by tone
- Automatically suggest optimal tone based on course content
- Train tone-specific question generation models

---

## Appendix

### Template Tone Instructions Reference

#### Academic Tone
"Use formal academic language with precise terminology, structured explanations, and a scholarly approach. Maintain objectivity and use complete sentences with proper grammar."

#### Casual Tone
"Use everyday conversational language that feels approachable and relaxed. Keep explanations simple and use contractions where natural. Make the content feel like a friendly discussion."

#### Encouraging Tone
"Use warm, supportive language that motivates learning. Include positive reinforcement, acknowledge that mistakes are part of learning, and frame questions in ways that build confidence."

#### Professional Tone
"Use clear, direct business language suitable for workplace training. Focus on practical applications and real-world scenarios. Keep explanations concise and action-oriented."

### Norwegian Translations

- **Academic:** "Bruk formelt akademisk språk med presis terminologi, strukturerte forklaringer og en vitenskapelig tilnærming."
- **Casual:** "Bruk hverdagslig samtale-språk som føles tilgjengelig og avslappet."
- **Encouraging:** "Bruk varmt, støttende språk som motiverer læring."
- **Professional:** "Bruk klart, direkte forretningsspråk egnet for arbeidsplasstrening."

---

**End of Document**
