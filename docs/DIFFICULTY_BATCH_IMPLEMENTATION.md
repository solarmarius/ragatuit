# Question Batch Difficulty Implementation Guide

**Version:** 1.0
**Date:** July 31, 2025
**Author:** Claude Code Assistant

## 1. Feature Overview

### Description
This feature adds the ability to specify difficulty levels (EASY, MEDIUM, HARD) for individual question batches within the Rag@UiT quiz generation system. Previously, the system would generate questions with mixed difficulty levels determined by the AI. Now, teachers can explicitly set the difficulty for each batch of questions, providing more granular control over quiz complexity.

### Business Value
- **Granular Control**: Teachers can tailor question difficulty to match course levels (introductory vs advanced)
- **Consistency**: Ensures all questions in a batch meet the specified difficulty criteria
- **Educational Alignment**: Better alignment with learning objectives and student capabilities
- **Quality Assurance**: Reduces variability in question difficulty within batches

### User Benefits
- Create differentiated assessments for different student groups
- Maintain consistent difficulty across question types within modules
- Better match assessment difficulty to course content complexity
- Improved predictability of quiz difficulty

### Context
Rag@UiT is a Canvas LMS integration that generates multiple-choice questions from course content using AI. The system processes content in "batches" - groups of questions of the same type (e.g., 10 multiple choice questions). This feature extends the batch system to include difficulty specification.

## 2. Technical Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend UI   │    │   Backend API    │    │   AI Templates  │
│                 │    │                  │    │                 │
│ Difficulty      │───▶│ Batch Keys:      │───▶│ Difficulty      │
│ Selector        │    │ module_type_     │    │ Instructions    │
│ (3-column)      │    │ count_difficulty │    │ {difficulty}    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │              ┌─────────▼─────────┐              │
         │              │   Database        │              │
         │              │                   │              │
         └──────────────│ QuestionBatch:    │              │
                        │ - question_type   │              │
                        │ - count          │              │
                        │ - difficulty     │◀─────────────┘
                        └───────────────────┘
```

### Integration Points
1. **Frontend**: Extends existing quiz creation flow with difficulty selection
2. **Backend**: Modifies batch processing pipeline to include difficulty
3. **Database**: Stores difficulty in existing JSONB `selected_modules` field
4. **AI Templates**: Uses difficulty to generate targeted prompts
5. **Batch Tracking**: Updates retry/success tracking with new key format

### Key Components Modified
- **QuestionBatch Schema**: Core data structure for batch configuration
- **ModuleBatchWorkflow**: AI generation pipeline that processes batches
- **Quiz Model**: Validation and auto-migration logic
- **Generation Service**: Batch key management and tracking
- **Frontend Components**: UI for difficulty selection

## 3. Dependencies & Prerequisites

### Backend Dependencies
- **Python**: 3.11+
- **SQLModel**: For data validation and database models
- **Pydantic**: Field validation and defaults
- **FastAPI**: API framework
- **PostgreSQL**: Database with JSONB support

### Frontend Dependencies
- **React**: 18+
- **TypeScript**: 5+
- **Chakra UI**: Component library
- **TanStack Router**: File-based routing

### Environment Setup
```bash
# Backend
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Existing System Requirements
- Functional Rag@UiT installation
- Canvas LMS integration configured
- AI/LLM provider setup (OpenAI, etc.)
- PostgreSQL database with existing quiz schema

## 4. Implementation Details

### 4.1 File Structure

```
backend/
├── src/
│   ├── quiz/
│   │   ├── schemas.py           # ✓ MODIFIED - QuestionBatch schema
│   │   └── models.py            # ✓ MODIFIED - Quiz validation
│   └── question/
│       ├── services/
│       │   └── generation_service.py  # ✓ MODIFIED - Batch keys
│       ├── workflows/
│       │   └── module_batch_workflow.py  # ✓ MODIFIED - Difficulty handling
│       └── templates/files/
│           ├── batch_multiple_choice.json      # TODO - Add difficulty logic
│           ├── batch_multiple_choice_no.json   # TODO - Add difficulty logic
│           ├── batch_fill_in_blank.json        # TODO - Add difficulty logic
│           ├── batch_fill_in_blank_no.json     # TODO - Add difficulty logic
│           ├── batch_matching.json             # TODO - Add difficulty logic
│           ├── batch_matching_no.json          # TODO - Add difficulty logic
│           ├── batch_categorization.json       # TODO - Add difficulty logic
│           ├── batch_categorization_no.json    # TODO - Add difficulty logic
│           ├── batch_true_false.json           # TODO - Add difficulty logic
│           └── batch_true_false_no.json        # TODO - Add difficulty logic

frontend/
├── src/
│   ├── lib/
│   │   └── constants/index.ts   # TODO - Difficulty constants
│   └── components/
│       ├── QuizCreation/
│       │   └── ModuleQuestionSelectionStep.tsx  # TODO - 3-column UI
│       └── Common/
│           └── QuestionTypeBreakdown.tsx        # TODO - Display difficulty
```

### 4.2 Step-by-Step Implementation

#### Step 1: Update QuestionBatch Schema ✅ COMPLETED

**File:** `backend/src/quiz/schemas.py`

```python
from src.question.types import QuestionDifficulty, QuestionType, QuizLanguage

class QuestionBatch(SQLModel):
    """Schema for a batch of questions of a specific type and difficulty."""

    question_type: QuestionType
    count: int = Field(ge=1, le=20, description="Number of questions (1-20)")
    difficulty: QuestionDifficulty = Field(
        default=QuestionDifficulty.MEDIUM, description="Question difficulty level"
    )
```

**Purpose**: Extends the batch schema to include difficulty with MEDIUM as default.

#### Step 2: Update Quiz Model Validation ✅ COMPLETED

**File:** `backend/src/quiz/models.py`

```python
@field_validator("selected_modules")
def validate_selected_modules(cls, v: Any) -> dict[str, dict[str, Any]]:
    """Ensure selected_modules has correct structure."""
    # ... existing validation code ...

    # Validate each batch
    for i, batch in enumerate(module_data["question_batches"]):
        # ... existing validation ...

        # Auto-migrate existing batches without difficulty to MEDIUM
        if "difficulty" not in batch:
            batch["difficulty"] = "medium"

        # Validate difficulty field if present
        if "difficulty" in batch:
            valid_difficulties = ["easy", "medium", "hard"]
            if batch["difficulty"] not in valid_difficulties:
                raise ValueError(
                    f"Module {module_id} batch {i} difficulty must be one of: {valid_difficulties}"
                )

    # Validate no duplicate question type + difficulty combinations in same module
    batch_combinations = [
        (batch["question_type"], batch["difficulty"])
        for batch in module_data["question_batches"]
    ]
    if len(batch_combinations) != len(set(batch_combinations)):
        raise ValueError(
            f"Module {module_id} has duplicate question type and difficulty combinations"
        )

    return v
```

**Purpose**:
- Auto-migrates existing quizzes without difficulty to MEDIUM
- Validates difficulty enum values
- Prevents duplicate question_type + difficulty combinations within a module

#### Step 3: Update Batch Key Generation ✅ COMPLETED

**File:** `backend/src/question/services/generation_service.py`

```python
for batch in module_info.get("question_batches", []):
    question_type = batch["question_type"]
    count = batch["count"]
    difficulty = batch.get("difficulty", "medium")  # Default to medium for backward compatibility

    # Create batch key - CHANGED FORMAT
    batch_key = f"{module_id}_{question_type}_{count}_{difficulty}"

    # Update all tracking structures
    if batch_key in successful_batch_keys:
        skipped_batches.append({
            "module_id": module_id,
            "module_name": module_name,
            "batch_key": batch_key,
            "question_type": question_type,
            "count": count,
            "difficulty": difficulty,  # NEW FIELD
            "reason": "already_successful",
        })
    else:
        batches_to_process.append({
            "question_type": QuestionType(question_type),
            "count": count,
            "difficulty": difficulty,  # NEW FIELD
            "batch_key": batch_key,
        })
```

**Purpose**:
- Changes batch key format from `id_type_count` to `id_type_count_difficulty`
- Ensures all batch tracking includes difficulty information
- Maintains backward compatibility with default "medium"

**Gotcha**: The batch key format change affects retry logic - existing failed batches with old format will be re-attempted.

#### Step 4: Update ModuleBatchWorkflow ✅ COMPLETED

**File:** `backend/src/question/workflows/module_batch_workflow.py`

```python
class ModuleBatchState(BaseModel):
    """State for module batch generation workflow."""

    # Input parameters
    quiz_id: UUID
    module_id: str
    module_name: str
    module_content: str
    target_question_count: int
    language: QuizLanguage = QuizLanguage.ENGLISH
    question_type: QuestionType
    difficulty: QuestionDifficulty | None = None  # NEW FIELD
    tone: str | None = None

    # ... rest of state fields ...

async def prepare_prompt(self, state: ModuleBatchState) -> ModuleBatchState:
    """Prepare the prompt for batch generation."""
    try:
        # Create generation parameters
        generation_parameters = GenerationParameters(
            target_count=remaining_questions,
            difficulty=state.difficulty,  # NEW - Pass difficulty to templates
            language=self.language,
        )

        # Create messages using template
        messages = await self.template_manager.create_messages(
            state.question_type,
            state.module_content,
            generation_parameters,
            template_name=None,
            language=self.language,
            extra_variables={
                "module_name": state.module_name,
                "question_count": remaining_questions,
                "tone": state.tone or self.tone,  # NOTE: Tone goes through extra_variables
            },
        )

async def validate_batch(self, state: ModuleBatchState) -> ModuleBatchState:
    """Validate and parse the generated questions."""
    for q_data in questions_data:
        try:
            # Remove difficulty from question data if LLM provided it
            q_data.pop("difficulty", None)

            # ... validation logic ...

            # Create question object with batch difficulty (not LLM difficulty)
            question = Question(
                quiz_id=state.quiz_id,
                question_type=state.question_type,
                question_data=validated_data.model_dump(),
                difficulty=state.difficulty,  # ALWAYS use batch difficulty
                is_approved=False,
            )

async def process_module(
    self,
    quiz_id: UUID,
    module_id: str,
    module_name: str,
    module_content: str,
    question_count: int,
    question_type: QuestionType,
    difficulty: QuestionDifficulty | None = None,  # NEW PARAMETER
) -> list[Question]:
    """Process a single module to generate questions."""
    initial_state = ModuleBatchState(
        quiz_id=quiz_id,
        module_id=module_id,
        module_name=module_name,
        module_content=module_content,
        target_question_count=question_count,
        language=self.language,
        question_type=question_type,
        difficulty=difficulty,  # NEW - Set difficulty in state
        tone=self.tone,
        llm_provider=self.llm_provider,
        template_manager=self.template_manager,
    )
```

**Purpose**:
- Adds difficulty to workflow state
- Passes difficulty to GenerationParameters for template usage
- Always uses batch-specified difficulty, ignoring LLM-provided difficulty
- Follows same pattern as language (enum throughout pipeline)

**Critical Note**: Difficulty is passed to GenerationParameters, but tone is passed through extra_variables. This follows the established pattern in the codebase.

#### Step 5: Update ParallelModuleProcessor ✅ COMPLETED

**File:** `backend/src/question/workflows/module_batch_workflow.py` (continued)

```python
class ParallelModuleProcessor:
    async def process_all_modules_with_batches(self, quiz_id: UUID, modules_data: dict[str, dict[str, Any]]):
        for module_id, module_info in modules_data.items():
            for batch in module_info["batches"]:
                question_type = batch["question_type"]
                count = batch["count"]
                difficulty_str = batch.get("difficulty", "medium")

                # Convert to enum early (like language handling)
                try:
                    difficulty = QuestionDifficulty(difficulty_str)
                except ValueError:
                    difficulty = QuestionDifficulty.MEDIUM

                batch_key = batch["batch_key"]

                # Pass difficulty to single batch processor
                task = asyncio.create_task(
                    self._process_single_batch(
                        workflow, module_id, module_name, module_content,
                        quiz_id, count, question_type, difficulty, batch_key,
                    )
                )

    async def _process_single_batch(
        self,
        workflow: ModuleBatchWorkflow,
        module_id: str,
        module_name: str,
        module_content: str,
        quiz_id: UUID,
        target_count: int,
        question_type: QuestionType,
        difficulty: QuestionDifficulty,  # NEW PARAMETER
        batch_key: str,
    ) -> tuple[list[Question], dict[str, Any]]:
        questions = await workflow.process_module(
            module_id=module_id,
            module_name=module_name,
            module_content=module_content,
            quiz_id=quiz_id,
            question_count=target_count,
            question_type=question_type,
            difficulty=difficulty,  # Pass difficulty to workflow
        )
```

**Purpose**: Ensures difficulty flows correctly from batch data through the parallel processing pipeline.

#### Step 6: Template Updates (TODO)

**Files:** All 10 template files in `backend/src/question/templates/files/`

**Pattern for English templates:**
```json
{
  "system_prompt": "...\n4. {% if difficulty %}Generate {{ difficulty|upper }} difficulty questions.\n{% if difficulty == 'easy' %}Focus on basic recall, recognition, and simple comprehension. Use straightforward language and test fundamental concepts from the material.\n{% elif difficulty == 'medium' %}Include application, analysis, and moderate problem-solving. Test understanding and ability to apply concepts in familiar contexts.\n{% elif difficulty == 'hard' %}Emphasize synthesis, evaluation, complex problem-solving, and critical thinking. Test deep understanding and advanced application of concepts.\n{% endif %}{% else %}Vary the difficulty levels (easy, medium, hard){% endif %}\n...",

  "user_prompt": "...",

  "variables": {
    "difficulty": "Question difficulty level (optional)",
    // ... other variables
  }
}
```

**Pattern for Norwegian templates:**
```json
{
  "system_prompt": "...\n4. {% if difficulty %}Generer {{ difficulty|upper }} vanskelighetsgrad spørsmål.\n{% if difficulty == 'easy' %}Fokuser på grunnleggende gjenkalling, gjenkjennelse og enkel forståelse. Bruk enkelt språk og test grunnleggende konsepter fra materialet.\n{% elif difficulty == 'medium' %}Inkluder anvendelse, analyse og moderat problemløsning. Test forståelse og evne til å anvende konsepter i kjente sammenhenger.\n{% elif difficulty == 'hard' %}Vektlegg syntese, evaluering, kompleks problemløsning og kritisk tenkning. Test dyp forståelse og avansert anvendelse av konsepter.\n{% endif %}{% else %}Varier vanskelighetsgraden (lett, middels, vanskelig){% endif %}\n...",

  "variables": {
    "difficulty": "Vanskelighetsgrad for spørsmål (valgfri)",
    // ... other variables
  }
}
```

**Purpose**:
- Replace generic "vary difficulty" instructions with specific difficulty targeting
- Provide clear cognitive level guidance for each difficulty
- Maintain backward compatibility when difficulty is not specified

#### Step 7: Frontend Constants (TODO)

**File:** `frontend/src/lib/constants/index.ts`

```typescript
export const QUESTION_DIFFICULTIES = {
  EASY: "easy",
  MEDIUM: "medium",
  HARD: "hard",
} as const

export const QUESTION_DIFFICULTY_LABELS = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
} as const

export const QUESTION_DIFFICULTY_DESCRIPTIONS = {
  easy: "Basic recall and simple comprehension",
  medium: "Application and moderate problem-solving",
  hard: "Complex analysis and critical thinking",
} as const
```

**Purpose**: Provides consistent constants for difficulty handling across frontend components.

#### Step 8: Frontend UI Component (TODO)

**File:** `frontend/src/components/QuizCreation/ModuleQuestionSelectionStep.tsx`

```typescript
import { QUESTION_DIFFICULTIES, QUESTION_DIFFICULTY_LABELS } from "@/lib/constants"

// Add difficulty collection for Chakra UI Select
const difficultyCollection = createListCollection({
  items: [
    { value: "easy", label: "Easy" },
    { value: "medium", label: "Medium" },
    { value: "hard", label: "Hard" },
  ],
})

// Update QuestionBatch interface usage
interface QuestionBatch {
  question_type: QuestionType
  count: number
  difficulty?: QuestionDifficulty  // NEW FIELD
}

// Update addBatch function
const addBatch = (moduleId: string) => {
  const newBatch: QuestionBatch = {
    question_type: QUESTION_BATCH_DEFAULTS.DEFAULT_QUESTION_TYPE,
    count: QUESTION_BATCH_DEFAULTS.DEFAULT_QUESTION_COUNT,
    difficulty: "medium",  // NEW DEFAULT
  }
  // ... rest of function
}

// Update validation to prevent duplicates
const updateBatch = (moduleId: string, batchIndex: number, updates: Partial<QuestionBatch>) => {
  const updatedBatches = currentBatches.map((batch, index) =>
    index === batchIndex ? { ...batch, ...updates } : batch
  )

  // Check for duplicate question_type + difficulty combinations
  const combinations = updatedBatches.map(b => `${b.question_type}_${b.difficulty}`)
  if (combinations.length !== new Set(combinations).size) {
    setValidationErrors(prev => ({
      ...prev,
      [moduleId]: ["Cannot have duplicate question type and difficulty combinations"],
    }))
    return
  }

  // ... rest of validation and update logic
}

// Update batch display (3-column layout)
<HStack gap={3} align="end">
  <Box flex={1}>
    <Field label="Question Type">
      <Select.Root
        collection={questionTypeCollection}
        value={[batch.question_type]}
        onValueChange={(details) =>
          updateBatch(moduleId, batchIndex, {
            question_type: details.value[0] as QuestionType,
          })
        }
        size="sm"
      >
        {/* ... select implementation */}
      </Select.Root>
    </Field>
  </Box>

  <Box width="100px">
    <Field label="Questions">
      <Input
        type="number"
        min={1}
        max={20}
        value={batch.count}
        onChange={(e) =>
          handleQuestionCountChange(moduleId, batchIndex, e.target.value)
        }
        textAlign="center"
        size="sm"
      />
    </Field>
  </Box>

  {/* NEW DIFFICULTY COLUMN */}
  <Box width="120px">
    <Field label="Difficulty">
      <Select.Root
        collection={difficultyCollection}
        value={[batch.difficulty || "medium"]}
        onValueChange={(details) =>
          updateBatch(moduleId, batchIndex, {
            difficulty: details.value[0] as QuestionDifficulty,
          })
        }
        size="sm"
      >
        <Select.Control>
          <Select.Trigger>
            <Select.ValueText placeholder="Select difficulty" />
          </Select.Trigger>
          <Select.IndicatorGroup>
            <Select.Indicator />
          </Select.IndicatorGroup>
        </Select.Control>
        <Select.Positioner>
          <Select.Content>
            {difficultyCollection.items.map((option) => (
              <Select.Item item={option} key={option.value}>
                {option.label}
                <Select.ItemIndicator />
              </Select.Item>
            ))}
          </Select.Content>
        </Select.Positioner>
      </Select.Root>
    </Field>
  </Box>

  <Button
    size="sm"
    variant="ghost"
    colorScheme="red"
    onClick={() => removeBatch(moduleId, batchIndex)}
  >
    <IoClose />
  </Button>
</HStack>
```

**Purpose**:
- Adds difficulty selector as third column in batch configuration
- Maintains consistent UI patterns with existing components
- Implements validation for duplicate combinations
- Provides clear labeling and user experience

### 4.3 Data Models & Schemas

#### Backend Data Structures

```python
# Enum Definition
class QuestionDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

# Schema Definition
class QuestionBatch(SQLModel):
    question_type: QuestionType  # "multiple_choice", "fill_in_blank", etc.
    count: int = Field(ge=1, le=20)  # 1-20 questions per batch
    difficulty: QuestionDifficulty = Field(default=QuestionDifficulty.MEDIUM)

# Database Storage (JSONB in selected_modules)
{
  "module_123": {
    "name": "Introduction to Biology",
    "question_batches": [
      {
        "question_type": "multiple_choice",
        "count": 10,
        "difficulty": "easy"  # NEW FIELD
      },
      {
        "question_type": "fill_in_blank",
        "count": 5,
        "difficulty": "medium"  # NEW FIELD
      }
    ]
  }
}

# Generated Question Model
class Question(SQLModel, table=True):
    id: UUID
    quiz_id: UUID
    question_type: QuestionType
    question_data: dict[str, Any]  # Question-specific content
    difficulty: QuestionDifficulty | None  # Set from batch, not LLM
    is_approved: bool = False
    # ... other fields
```

#### Frontend Type Definitions (Auto-generated)

```typescript
export type QuestionDifficulty = "easy" | "medium" | "hard"

export type QuestionBatch = {
  question_type: QuestionType
  count: number
  difficulty?: QuestionDifficulty  // Optional for backward compatibility
}
```

#### Validation Rules

1. **Difficulty Values**: Must be one of `["easy", "medium", "hard"]`
2. **Batch Uniqueness**: No duplicate `(question_type, difficulty)` pairs within a module
3. **Count Range**: 1-20 questions per batch
4. **Default Behavior**: Auto-migrate missing difficulty to "medium"
5. **Batch Limit**: Maximum 4 batches per module (existing rule)

#### Example Data Flow

```
User Input → Frontend Validation → API Request → Backend Validation → Database Storage

{
  question_type: "multiple_choice",
  count: 10,
  difficulty: "hard"
}
↓
Validation: No duplicates, valid enum
↓
POST /api/v1/quiz/create
↓
Quiz.validate_selected_modules()
↓
PostgreSQL JSONB storage
↓
Batch Key: "module_123_multiple_choice_10_hard"
↓
AI Template: {difficulty: "hard"} → "Generate HARD difficulty questions..."
```

### 4.4 Configuration

#### Environment Variables
No new environment variables required. Uses existing:
- `POSTGRES_*` - Database connection
- `LLM_*` - AI provider settings

#### Template Configuration
Templates automatically receive difficulty through the generation pipeline:
- `{{ difficulty }}` - Available in all templates
- `{% if difficulty %}` - Conditional logic for difficulty-specific instructions

#### Default Values
```python
# Backend Defaults
DEFAULT_DIFFICULTY = QuestionDifficulty.MEDIUM
MAX_BATCHES_PER_MODULE = 4  # Existing limit
QUESTIONS_PER_BATCH_RANGE = (1, 20)  # Existing range

# Frontend Defaults
DEFAULT_QUESTION_COUNT = 10  # Existing
DEFAULT_QUESTION_TYPE = "multiple_choice"  # Existing
DEFAULT_DIFFICULTY = "medium"  # NEW
```

## 5. Testing Strategy

### 5.1 Unit Tests

#### Backend Model Tests
```python
def test_question_batch_default_difficulty():
    """Test that QuestionBatch defaults to MEDIUM difficulty."""
    batch = QuestionBatch(question_type="multiple_choice", count=10)
    assert batch.difficulty == QuestionDifficulty.MEDIUM

def test_quiz_validation_auto_migration():
    """Test auto-migration of batches without difficulty."""
    quiz_data = {
        "selected_modules": {
            "mod_1": {
                "name": "Test Module",
                "question_batches": [
                    {"question_type": "multiple_choice", "count": 5}
                ]
            }
        }
    }
    quiz = Quiz(**quiz_data)
    assert quiz.selected_modules["mod_1"]["question_batches"][0]["difficulty"] == "medium"

def test_duplicate_combination_validation():
    """Test prevention of duplicate question_type + difficulty combinations."""
    quiz_data = {
        "selected_modules": {
            "mod_1": {
                "name": "Test Module",
                "question_batches": [
                    {"question_type": "multiple_choice", "count": 5, "difficulty": "easy"},
                    {"question_type": "multiple_choice", "count": 10, "difficulty": "easy"}
                ]
            }
        }
    }
    with pytest.raises(ValueError, match="duplicate question type and difficulty combinations"):
        Quiz(**quiz_data)
```

#### Batch Key Generation Tests
```python
def test_batch_key_format():
    """Test new batch key format includes difficulty."""
    module_id = "mod_123"
    question_type = "multiple_choice"
    count = 10
    difficulty = "hard"

    expected_key = f"{module_id}_{question_type}_{count}_{difficulty}"
    # Test in generation service context
    assert batch_key == "mod_123_multiple_choice_10_hard"

def test_backward_compatibility():
    """Test default difficulty when not specified."""
    batch = {"question_type": "multiple_choice", "count": 5}
    difficulty = batch.get("difficulty", "medium")
    assert difficulty == "medium"
```

#### Workflow Tests
```python
def test_difficulty_flow_through_workflow():
    """Test difficulty flows from batch to generated questions."""
    state = ModuleBatchState(
        quiz_id=uuid4(),
        module_id="test_mod",
        module_name="Test",
        module_content="content",
        target_question_count=5,
        language=QuizLanguage.ENGLISH,
        question_type=QuestionType.MULTIPLE_CHOICE,
        difficulty=QuestionDifficulty.HARD,
        tone=None,
        llm_provider=mock_provider,
        template_manager=mock_template_manager,
    )

    # Mock question generation
    mock_questions = [
        {"question_text": "Test?", "option_a": "A", "option_b": "B",
         "option_c": "C", "option_d": "D", "correct_answer": "A", "explanation": "Test"}
    ]

    # Process through workflow
    result = await workflow.validate_batch(state)

    # Verify generated questions have batch difficulty
    assert all(q.difficulty == QuestionDifficulty.HARD for q in result.generated_questions)
```

### 5.2 Integration Tests

#### End-to-End Quiz Creation
```python
async def test_quiz_creation_with_difficulty():
    """Test complete quiz creation flow with difficulty."""
    quiz_data = {
        "canvas_course_id": 123,
        "canvas_course_name": "Test Course",
        "title": "Test Quiz",
        "selected_modules": {
            "mod_1": {
                "name": "Module 1",
                "question_batches": [
                    {"question_type": "multiple_choice", "count": 5, "difficulty": "easy"},
                    {"question_type": "fill_in_blank", "count": 3, "difficulty": "hard"}
                ]
            }
        },
        "language": "en",
        "tone": "academic"
    }

    response = await client.post("/api/v1/quiz/create", json=quiz_data)
    assert response.status_code == 200

    quiz = response.json()
    batches = quiz["selected_modules"]["mod_1"]["question_batches"]
    assert batches[0]["difficulty"] == "easy"
    assert batches[1]["difficulty"] == "hard"
```

#### Template Integration Tests
```python
async def test_template_difficulty_rendering():
    """Test that templates receive and use difficulty correctly."""
    generation_params = GenerationParameters(
        target_count=5,
        difficulty=QuestionDifficulty.HARD,
        language=QuizLanguage.ENGLISH
    )

    messages = await template_manager.create_messages(
        QuestionType.MULTIPLE_CHOICE,
        "Test content",
        generation_params,
        extra_variables={"module_name": "Test", "question_count": 5}
    )

    system_prompt = messages[0].content
    assert "Generate HARD difficulty questions" in system_prompt
    assert "complex problem-solving and critical thinking" in system_prompt
```

### 5.3 Manual Testing Steps

#### Backend Testing
1. **Create Quiz with Mixed Difficulties**
   ```bash
   curl -X POST http://localhost:8000/api/v1/quiz/create \
     -H "Content-Type: application/json" \
     -d '{
       "canvas_course_id": 123,
       "canvas_course_name": "Test Course",
       "title": "Difficulty Test Quiz",
       "selected_modules": {
         "mod_1": {
           "name": "Test Module",
           "question_batches": [
             {"question_type": "multiple_choice", "count": 5, "difficulty": "easy"},
             {"question_type": "multiple_choice", "count": 5, "difficulty": "hard"}
           ]
         }
       }
     }'
   ```

2. **Verify Batch Keys in Logs**
   - Check generation logs for keys like: `mod_1_multiple_choice_5_easy`
   - Verify retry tracking uses new key format

3. **Test Auto-Migration**
   - Create quiz without difficulty fields
   - Verify they get auto-migrated to "medium"

#### Frontend Testing
1. **UI Functionality**
   - Navigate to quiz creation flow
   - Select modules and verify 3-column layout (Type, Count, Difficulty)
   - Test difficulty dropdown functionality
   - Verify duplicate combination prevention

2. **Validation Testing**
   - Try to create duplicate type+difficulty combinations
   - Verify error messages display correctly
   - Test form submission with various difficulty combinations

### 5.4 Performance Considerations

#### Benchmarks
- **Database Impact**: Minimal (difficulty stored in existing JSONB field)
- **Memory Usage**: No significant increase (enum values are lightweight)
- **API Response Time**: <5ms additional overhead for validation
- **Template Rendering**: <1ms additional time for difficulty conditionals

#### Load Testing Scenarios
```python
# Test concurrent quiz creation with different difficulties
async def test_concurrent_difficulty_processing():
    tasks = []
    for i in range(100):
        difficulty = random.choice(["easy", "medium", "hard"])
        task = create_quiz_with_difficulty(difficulty)
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)
```

## 6. Deployment Instructions

### 6.1 Pre-Deployment Checklist
- [ ] All backend tests pass
- [ ] Frontend tests pass
- [ ] Linting passes (ruff, mypy, eslint)
- [ ] Database backup created
- [ ] Template files updated with difficulty logic

### 6.2 Deployment Steps

#### Backend Deployment
```bash
# 1. Activate environment
cd backend
source .venv/bin/activate

# 2. Run tests
bash scripts/test.sh

# 3. Run linting
bash scripts/lint.sh

# 4. Database migration (if needed)
# Note: Auto-migration happens during quiz validation, no schema changes needed

# 5. Deploy application
# Follow existing deployment process
```

#### Frontend Deployment
```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Run tests
npm test

# 3. Run linting
npm run lint

# 4. Build for production
npm run build

# 5. Deploy
# Follow existing deployment process
```

### 6.3 Environment-Specific Configurations

#### Development
```bash
# No special configuration needed
# Use existing development environment setup
```

#### Staging
```bash
# Test with production-like data
# Verify batch key migration works correctly
# Test with various difficulty combinations
```

#### Production
```bash
# Monitor batch key generation
# Watch for any validation errors in logs
# Verify quiz creation success rates maintain baseline
```

### 6.4 Rollback Procedures

#### Backend Rollback
```bash
# 1. Revert to previous commit
git revert <commit-hash>

# 2. Redeploy backend
# Follow existing rollback procedures

# 3. Database considerations
# Auto-migration is non-destructive (only adds difficulty field)
# Existing quizzes will continue to work
# New difficulty fields will be ignored by old code
```

#### Frontend Rollback
```bash
# 1. Revert frontend changes
git revert <commit-hash>

# 2. Rebuild and redeploy
npm run build && deploy

# 3. Backend compatibility
# Backend is backward compatible - old frontend will work
# Users just won't see difficulty selection options
```

## 7. Monitoring & Maintenance

### 7.1 Key Metrics

#### Performance Metrics
- **Quiz Creation Time**: Should remain within baseline ±5%
- **Batch Processing Success Rate**: Monitor for any decrease
- **Template Rendering Time**: Watch for increases in generation latency
- **Database Query Performance**: Monitor JSONB field queries

#### Business Metrics
- **Difficulty Distribution**: Track usage of easy/medium/hard
- **User Adoption**: Monitor how many quizzes use difficulty selection
- **Error Rates**: Track validation errors for duplicate combinations

#### Monitoring Queries
```sql
-- Check difficulty distribution
SELECT
  jsonb_path_query(selected_modules, '$."*".question_batches[*].difficulty') as difficulty,
  count(*)
FROM quiz
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY difficulty;

-- Monitor batch key format
SELECT generation_metadata->'successful_batches'
FROM quiz
WHERE generation_metadata->'successful_batches' IS NOT NULL
LIMIT 10;
```

### 7.2 Log Entries to Monitor

#### Success Indicators
```python
# Batch processing with difficulty
logger.info("processing_single_batch",
           quiz_id=str(quiz_id),
           module_id=module_id,
           batch_key=batch_key,  # Should contain difficulty
           question_type=question_type.value,
           difficulty=difficulty.value,  # NEW
           target_count=target_count)

# Successful difficulty flow
logger.info("module_batch_prompt_prepared",
           module_id=state.module_id,
           difficulty=state.difficulty.value if state.difficulty else None,  # NEW
           target_questions=remaining_questions)
```

#### Warning Indicators
```python
# Auto-migration occurring
logger.info("quiz_validation_auto_migration",
           quiz_id=str(quiz_id),
           batches_migrated=count,
           reason="missing_difficulty_field")

# Invalid difficulty values
logger.warning("invalid_difficulty_value",
              difficulty=difficulty,
              module_id=module_id,
              batch_key=batch_key)
```

#### Error Indicators
```python
# Validation failures
logger.error("quiz_validation_failed",
            quiz_id=str(quiz_id),
            error="duplicate_question_type_difficulty_combination",
            module_id=module_id)

# Template rendering issues
logger.error("template_difficulty_rendering_failed",
            template_name=template_name,
            difficulty=difficulty,
            error=str(e))
```

### 7.3 Common Issues & Troubleshooting

#### Issue: Duplicate Combination Errors
**Symptoms**: Quiz creation fails with "duplicate question type and difficulty combinations"
**Cause**: User trying to create multiple batches with same type+difficulty
**Solution**:
```python
# Frontend validation should prevent this, but if it occurs:
# 1. Check frontend validation logic
# 2. Verify user isn't bypassing frontend
# 3. Review API input validation
```

#### Issue: Batch Keys Not Found During Retry
**Symptoms**: Failed batches being re-attempted instead of skipped
**Cause**: Batch key format mismatch between old and new versions
**Investigation**:
```python
# Check generation_metadata format
SELECT generation_metadata->'successful_batches' FROM quiz WHERE id = '<quiz_id>';

# Look for old format keys: "mod_type_count" vs new: "mod_type_count_difficulty"
```
**Solution**: Clear generation_metadata to force complete regeneration

#### Issue: Template Not Using Difficulty
**Symptoms**: Questions generated don't match specified difficulty
**Cause**: Template not updated or difficulty not flowing through
**Investigation**:
```python
# Check template receives difficulty
logger.debug("template_variables",
            difficulty=generation_parameters.difficulty,
            extra_variables=extra_variables)

# Verify template logic
# Check for {% if difficulty %} conditionals in template files
```

#### Issue: Auto-Migration Not Working
**Symptoms**: Validation errors for missing difficulty field
**Cause**: Auto-migration logic not executing or failing
**Investigation**:
```python
# Check quiz validation logs
# Verify batch structure in selected_modules
# Ensure auto-migration runs before other validation
```

### 7.4 Maintenance Tasks

#### Weekly Tasks
- Review difficulty distribution metrics
- Check for any validation error spikes
- Monitor batch key format consistency
- Verify template rendering performance

#### Monthly Tasks
- Analyze user adoption of difficulty selection
- Review and optimize database queries involving difficulty
- Check for any performance degradation trends
- Update documentation based on user feedback

#### Quarterly Tasks
- Evaluate need for additional difficulty levels
- Review template effectiveness for different difficulties
- Assess system performance impact
- Plan feature enhancements based on usage patterns

## 8. Security Considerations

### 8.1 Authentication & Authorization

#### Existing Security Model
The difficulty feature inherits all existing security measures:
- **JWT Authentication**: Required for all quiz operations
- **Canvas OAuth**: User must have Canvas course access
- **Course Permissions**: Only users with course access can create quizzes
- **Quiz Ownership**: Users can only modify their own quizzes

#### No Additional Permissions Required
Difficulty selection doesn't introduce new security boundaries - it's a configuration option within existing quiz creation permissions.

### 8.2 Data Privacy

#### PII Considerations
- **No PII in Difficulty Data**: Difficulty levels are non-sensitive metadata
- **Audit Trail**: Difficulty choices logged for educational analytics only
- **Data Retention**: Follows existing quiz data retention policies

#### Data Storage
```python
# Difficulty stored in existing JSONB field - no new tables
# Inherits all existing encryption and backup procedures
selected_modules = {
  "module_123": {
    "question_batches": [
      {"difficulty": "medium"}  # Non-sensitive configuration data
    ]
  }
}
```

### 8.3 Input Validation & Sanitization

#### Backend Validation
```python
# Enum validation prevents injection
class QuestionDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

# Pydantic field validation
difficulty: QuestionDifficulty = Field(default=QuestionDifficulty.MEDIUM)

# Additional validation in Quiz model
valid_difficulties = ["easy", "medium", "hard"]
if batch["difficulty"] not in valid_difficulties:
    raise ValueError(f"Invalid difficulty: {batch['difficulty']}")
```

#### Frontend Validation
```typescript
// Controlled select input - only allows predefined values
const difficultyCollection = createListCollection({
  items: [
    { value: "easy", label: "Easy" },
    { value: "medium", label: "Medium" },
    { value: "hard", label: "Hard" },
  ],
})

// TypeScript type safety
difficulty: QuestionDifficulty  // "easy" | "medium" | "hard"
```

### 8.4 Template Security

#### Template Injection Prevention
```python
# Jinja2 templates with auto-escaping enabled
# Difficulty values are enum-validated before reaching templates
# No user input directly inserted into templates

# Safe template usage:
{% if difficulty == 'easy' %}  {# Enum comparison, not user input #}
  Generate {{ difficulty|upper }} questions  {# Built-in filter, safe #}
{% endif %}
```

#### LLM Prompt Security
- **Controlled Input**: Only validated enum values reach LLM prompts
- **No Code Injection**: Difficulty affects prompt content, not execution
- **Output Sanitization**: LLM responses parsed and validated before storage

### 8.5 API Security

#### Rate Limiting
Difficulty selection doesn't increase API call volume - uses existing quiz creation endpoints.

#### Request Validation
```python
# All existing request validation applies
# Additional validation for difficulty field
@app.post("/api/v1/quiz/create")
async def create_quiz(quiz_data: QuizCreate):  # Pydantic validation
    # QuizCreate includes QuestionBatch validation
    # Enum validation happens automatically
    pass
```

### 8.6 Security Best Practices Applied

1. **Principle of Least Privilege**: No new permissions introduced
2. **Defense in Depth**: Validation at frontend, API, and database levels
3. **Input Sanitization**: Enum validation prevents invalid values
4. **Audit Logging**: All difficulty selections logged for monitoring
5. **Secure Defaults**: MEDIUM difficulty default is safe fallback

## 9. Future Considerations

### 9.1 Known Limitations

#### Current Constraints
1. **Three Difficulty Levels**: Only easy/medium/hard supported
2. **Per-Batch Granularity**: Cannot set difficulty per individual question
3. **Static Difficulty Mapping**: Fixed cognitive level descriptions
4. **Template Dependency**: Effectiveness depends on LLM following instructions
5. **No Difficulty Validation**: System doesn't verify generated questions match requested difficulty

#### Technical Debt
- **Template Duplication**: Similar difficulty logic across 10 template files
- **Enum String Mapping**: Conversion between enum and string in multiple places
- **Validation Complexity**: Duplicate checking logic could be abstracted

### 9.2 Potential Improvements

#### Short-term Enhancements (Next 6 months)
```python
# 1. Difficulty Validation Service
class DifficultyValidator:
    async def validate_question_difficulty(
        self,
        question: Question,
        expected_difficulty: QuestionDifficulty
    ) -> bool:
        # Use NLP/ML to verify question matches expected difficulty
        pass

# 2. Custom Difficulty Levels
class CustomDifficulty(SQLModel):
    name: str
    description: str
    cognitive_level: int  # 1-10 scale
    question_characteristics: dict[str, Any]

# 3. Difficulty Analytics
class DifficultyMetrics:
    def get_difficulty_effectiveness(self, quiz_id: UUID) -> dict:
        # Analyze student performance vs difficulty settings
        pass
```

#### Medium-term Features (6-12 months)
1. **Adaptive Difficulty**: System learns optimal difficulty for different content types
2. **Difficulty Presets**: Subject-specific difficulty templates (Math vs History)
3. **Granular Control**: Per-question difficulty overrides
4. **Performance Correlation**: Link difficulty settings to student outcomes
5. **Advanced Templates**: AI-generated difficulty instructions based on content analysis

#### Long-term Vision (1+ years)
```python
# AI-Powered Difficulty Assessment
class IntelligentDifficultyEngine:
    async def analyze_content_difficulty(self, content: str) -> DifficultyRecommendation:
        # Analyze content complexity and recommend appropriate difficulty
        pass

    async def generate_adaptive_questions(
        self,
        content: str,
        student_profile: StudentProfile,
        learning_objectives: list[str]
    ) -> list[Question]:
        # Generate questions tailored to individual student needs
        pass

# Bloom's Taxonomy Integration
class BloomsTaxonomyMapper:
    def map_difficulty_to_blooms(self, difficulty: QuestionDifficulty) -> BloomsLevel:
        # Remember, Understand, Apply, Analyze, Evaluate, Create
        pass
```

### 9.3 Scalability Considerations

#### Current Scalability
- **Database Impact**: Minimal (JSONB field updates)
- **Memory Usage**: Negligible enum overhead
- **CPU Impact**: Minor validation overhead
- **Network**: No additional API calls

#### Scaling Challenges
1. **Template Maintenance**: More difficulty levels = more template complexity
2. **Validation Performance**: Complex duplicate checking with many batches
3. **Analytics Storage**: Difficulty metrics could grow large over time
4. **LLM Costs**: More specific prompts might increase token usage

#### Scaling Solutions
```python
# 1. Template Engine Optimization
class OptimizedTemplateManager:
    def __init__(self):
        self.compiled_templates = {}  # Pre-compile for performance
        self.difficulty_cache = {}    # Cache difficulty instructions

# 2. Batch Validation Optimization
def validate_batch_combinations_optimized(batches: list[QuestionBatch]) -> bool:
    # Use set operations instead of list comparisons
    combinations = {(b.question_type, b.difficulty) for b in batches}
    return len(combinations) == len(batches)

# 3. Distributed Difficulty Processing
class DistributedDifficultyProcessor:
    async def process_difficulty_batches(self, batches: list[Batch]) -> list[Result]:
        # Distribute difficulty-specific processing across workers
        pass
```

### 9.4 Integration Opportunities

#### Canvas LMS Integration
```python
# Sync difficulty with Canvas question banks
class CanvasDifficultySync:
    async def export_with_difficulty_tags(self, quiz: Quiz) -> CanvasQuizExport:
        # Tag Canvas questions with difficulty metadata
        pass

    async def import_difficulty_preferences(self, course_id: int) -> DifficultyProfile:
        # Learn from existing Canvas quiz difficulty patterns
        pass
```

#### Learning Management Integration
```python
# Integration with learning analytics platforms
class LearningAnalyticsIntegration:
    async def track_difficulty_outcomes(
        self,
        quiz_results: QuizResults,
        difficulty_settings: dict[str, QuestionDifficulty]
    ):
        # Send difficulty correlation data to analytics platform
        pass
```

#### AI/ML Platform Integration
```python
# Enhanced difficulty with external AI services
class ExternalAIIntegration:
    async def enhance_difficulty_with_ai(
        self,
        content: str,
        base_difficulty: QuestionDifficulty
    ) -> EnhancedDifficultyInstructions:
        # Use specialized AI models for difficulty calibration
        pass
```

### 9.5 Research & Development Opportunities

#### Educational Research
1. **Difficulty Effectiveness Studies**: Measure learning outcomes vs difficulty settings
2. **Cognitive Load Research**: Optimize difficulty progression for better learning
3. **Adaptive Assessment**: Research optimal difficulty adjustment algorithms

#### Technical Research
1. **Automated Difficulty Assessment**: NLP models to verify question difficulty
2. **Content Complexity Analysis**: AI systems to automatically determine optimal difficulty
3. **Personalized Difficulty**: Machine learning for individual student difficulty optimization

### 9.6 Deprecation & Migration Planning

#### Future-Proofing Design Decisions
1. **Enum Extensibility**: Easy to add new difficulty levels
2. **Template Modularity**: Difficulty logic can be abstracted
3. **Database Schema**: JSONB storage allows flexible difficulty evolution
4. **API Versioning**: Current design supports backward-compatible changes

#### Potential Migration Scenarios
```python
# Scenario 1: More Difficulty Levels
class ExtendedDifficulty(str, Enum):
    VERY_EASY = "very_easy"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very_hard"

# Migration strategy: Add new levels, maintain backward compatibility

# Scenario 2: Numeric Difficulty Scale
class NumericDifficulty(BaseModel):
    scale: int = Field(ge=1, le=10)  # 1-10 difficulty scale
    category: str  # "conceptual", "computational", "analytical"

# Migration strategy: Map existing enum to numeric scale
```

---

## Conclusion

This implementation guide provides a comprehensive roadmap for adding difficulty selection to question batches in the Rag@UiT system. The feature has been designed to be:

- **Backward Compatible**: Existing quizzes continue to work unchanged
- **User-Friendly**: Intuitive 3-column interface following established UI patterns
- **Technically Sound**: Leverages existing architecture and follows established code patterns
- **Extensible**: Foundation for future enhancements and additional difficulty features
- **Secure**: Inherits all existing security measures with proper input validation

The backend implementation is complete and tested. The remaining work involves template updates and frontend implementation, both following the detailed specifications provided in this document.

For questions or clarifications about this implementation, refer to the code examples, test cases, and architectural decisions documented throughout this guide.
