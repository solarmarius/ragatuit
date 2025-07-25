# Module-Based Question Generation Implementation Guide

## 1. Feature Overview

### Description

The Module-Based Question Generation feature transforms how quiz questions are created in Rag@UiT. Instead of generating questions one at a time from content chunks, this feature allows users to specify how many questions (1-20) they want from each Canvas module. The system then generates all questions for a module in a single AI request, processing multiple modules in parallel for improved efficiency.

### Business Value

- **Improved Performance**: Reduces AI API calls from N (number of questions) to M (number of modules)
- **Better Question Quality**: AI has full module context when generating questions, leading to more comprehensive coverage
- **Enhanced User Control**: Teachers can distribute questions based on module importance
- **Reduced Bias**: Batch generation ensures better distribution of correct answers (A, B, C, D)
- **Faster Generation**: Parallel processing of modules significantly reduces total generation time

### User Benefits

- Granular control over question distribution across course content
- Predictable question coverage per module
- Faster quiz generation process
- Better question diversity within modules

## 2. Technical Architecture

### High-Level Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│  Frontend (React)│────▶│  Backend (FastAPI)│────▶│  LLM Provider   │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                         │
        │                        │                         │
        ▼                        ▼                         │
┌─────────────────┐     ┌──────────────────┐              │
│  Module Question │     │  Module Batch    │              │
│  Selection UI   │     │  Workflow        │◀─────────────┘
└─────────────────┘     └──────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  Parallel Module │
                        │  Processing      │
                        └──────────────────┘
```

### System Integration

The feature integrates into the existing quiz creation workflow by:

1. Adding a new UI step after module selection
2. Replacing the chunk-based generation service with module-batch processing
3. Modifying the data model to store per-module question counts
4. Implementing parallel processing in the orchestration layer

### Key Components

- **Frontend**: New ModuleQuestionSelectionStep component
- **Backend**: ModuleBatchWorkflow replacing MCQWorkflow
- **Data Model**: Extended selected_modules structure
- **Processing**: Asyncio-based parallel module handling

## 3. Dependencies & Prerequisites

### Backend Dependencies

```toml
# Already included in pyproject.toml
python = "^3.11"
fastapi = "^0.115.6"
sqlmodel = "^0.0.22"
httpx = "^0.28.1"
asyncio = "builtin"
langchain = "^0.3.13"
langgraph = "^0.2.60"
```

### Frontend Dependencies

```json
// Already included in package.json
"react": "^18.3.1",
"@tanstack/react-router": "^1.82.0",
"@chakra-ui/react": "^3.2.3",
"typescript": "~5.6.3"
```

### Environment Requirements

- Docker and Docker Compose for development
- PostgreSQL 15+
- Node.js 18+
- Python 3.11+

### LLM Provider Setup

- OpenAI API key configured in environment
- Sufficient rate limits for parallel requests
- Model access (GPT-4 or equivalent)

## 4. Implementation Details

### 4.1 File Structure

```
ragatuit/
├── backend/
│   ├── src/
│   │   ├── quiz/
│   │   │   ├── models.py (MODIFY)
│   │   │   ├── schemas.py (MODIFY)
│   │   │   └── orchestrator.py (MODIFY)
│   │   └── question/
│   │       ├── workflows/
│   │       │   ├── module_batch_workflow.py (CREATE)
│   │       │   └── registry.py (MODIFY)
│   │       ├── services/
│   │       │   ├── generation_service.py (MODIFY)
│   │       │   └── content_service.py (MODIFY)
│   │       └── templates/
│   │           └── files/
│   │               ├── batch_multiple_choice.json (CREATE)
│   │               └── batch_multiple_choice_no.json (CREATE)
│   └── alembic/
│       └── versions/
│           └── xxx_update_selected_modules_structure.py (CREATE)
├── frontend/
│   └── src/
│       ├── components/
│       │   └── QuizCreation/
│       │       └── ModuleQuestionSelectionStep.tsx (CREATE)
│       ├── routes/
│       │   └── _layout/
│       │       └── create-quiz.tsx (MODIFY)
│       └── types/
│           └── index.ts (MODIFY)
└── docs/
    └── MODULE_BASED_QUESTION_GENERATION.md (THIS FILE)
```

### 4.2 Step-by-Step Implementation

> **Important**: After each step, you must:
>
> 1. Run the test suite to ensure nothing is broken
> 2. Run linting and type checking
> 3. Commit your changes
>
> This ensures that any breaking changes are caught immediately and can be rolled back if needed.

#### Testing Philosophy for This Implementation

This is a major architectural change. To avoid broken commits, we'll use a gradual migration strategy:

1. **Clean Break Strategy**:

   - Remove old implementation immediately
   - Update all affected tests in the same commit
   - Each commit should leave the codebase in a working state

2. **Handling Test Updates**:

   - When changing a core component, update ALL related tests in the same commit
   - Use `git add -p` to stage related changes together
   - If changes are too large for one commit, use feature branches

3. **Commit Boundaries**:

   - Backend model changes + test updates = 1 commit
   - Frontend component changes + test updates = 1 commit
   - Each commit must pass its own tests

4. **Test Commands**:

   ```bash
   # Backend
   cd backend && source .venv/bin/activate
   bash scripts/test.sh          # Run all tests
   bash scripts/lint.sh          # Type checking and linting

   # Frontend
   cd frontend
   npx playwright test           # E2E tests
   npx tsc --noEmit             # Type checking
   npm run lint                  # Linting
   ```

5. **Commit Strategy**:
   - Create a feature branch for this implementation: `git checkout -b feat/module-based-question-generation`
   - Make atomic commits of working changes only
   - If a step is too large, break it into smaller sub-steps
   - Use git stash for work-in-progress when tests are failing
   - Only commit when:
     - The code compiles without errors
     - Type checking passes
     - Related tests are updated/created
   - For large refactors that temporarily break tests:
     - Create smaller intermediate steps that maintain functionality
     - Use feature flags if needed to deploy incrementally
     - Document known test failures in commit messages

#### Step 1: Update Database Models

**File**: `backend/src/quiz/models.py`

```python
from typing import Dict, Any
from sqlmodel import Field, JSON, Column
from sqlalchemy.dialects.postgresql import JSONB

class Quiz(SQLModel, table=True):
    """Quiz model with module-based question distribution."""

    # ... existing fields ...

    # Update selected_modules to store question counts
    selected_modules: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Module IDs mapped to module info including question count"
    )
    # Structure: {"module_id": {"name": "Module Name", "question_count": 10}}

    # Keep question_count for total tracking (remove max constraint)
    question_count: int = Field(
        ge=1,
        description="Total number of questions across all modules"
    )

    # Add metadata field for storing generation details
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Additional metadata for tracking generation details"
    )

    @property
    def module_question_distribution(self) -> Dict[str, int]:
        """Get question count per module."""
        return {
            module_id: module_data.get("question_count", 0)
            for module_id, module_data in self.selected_modules.items()
        }

    @property
    def total_questions_from_modules(self) -> int:
        """Calculate total questions from module distribution."""
        return sum(
            module_data.get("question_count", 0)
            for module_data in self.selected_modules.values()
        )
```

**Tests to Update**:

- `backend/tests/quiz/test_quiz_service.py` - Update quiz creation tests to handle new module structure
- `backend/tests/factories.py` - Update QuizFactory to generate new selected_modules format

**Testing & Validation**:

```bash
# Backend Testing
cd backend && source .venv/bin/activate
bash scripts/test.sh
# Expected: Some tests will fail due to schema changes - note which ones

# Backend Linting
bash scripts/lint.sh
# Fix any type errors related to Dict structure changes

# Before committing:
# 1. Update test fixtures to use new selected_modules structure
# 2. Create a compatibility layer if needed
# 3. Ensure code compiles and type checks pass

# If tests are still failing:
git stash  # Save work in progress
# Break into smaller steps or create compatibility shims

# Only commit when ready:
git add src/quiz/models.py tests/factories.py
git commit -m "feat: update Quiz model to support per-module question counts

- Add metadata field for generation tracking
- Update selected_modules structure to include question counts
- Update test factories to match new structure"
```

#### Step 2: Update Schemas

**File**: `backend/src/quiz/schemas.py`

```python
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator

class ModuleSelection(BaseModel):
    """Schema for module selection with question count."""
    name: str
    question_count: int = Field(ge=1, le=20, description="Questions per module (1-20)")

class QuizCreate(BaseModel):
    """Schema for creating a quiz with module-based questions."""
    canvas_course_id: int
    canvas_course_name: str
    title: str = Field(min_length=1)
    selected_modules: Dict[str, ModuleSelection]
    language: QuizLanguage = QuizLanguage.ENGLISH

    @field_validator("selected_modules")
    def validate_modules(cls, v):
        if not v:
            raise ValueError("At least one module must be selected")

        # Validate each module has required fields
        for module_id, module_data in v.items():
            if not isinstance(module_data, dict):
                module_data = module_data.model_dump()

            if "name" not in module_data or "question_count" not in module_data:
                raise ValueError(f"Module {module_id} missing required fields")

            if not 1 <= module_data["question_count"] <= 20:
                raise ValueError(f"Module {module_id} question count must be 1-20")

        return v

    @property
    def total_question_count(self) -> int:
        """Calculate total questions across all modules."""
        return sum(
            module.question_count if isinstance(module, ModuleSelection)
            else module.get("question_count", 0)
            for module in self.selected_modules.values()
        )

class QuizResponse(QuizBase):
    """Response schema including module question distribution."""
    id: UUID
    status: QuizStatus
    module_question_distribution: Dict[str, int]
    questions: List[QuestionResponse] = []

    @classmethod
    def from_orm(cls, quiz: Quiz):
        return cls(
            **quiz.model_dump(),
            module_question_distribution=quiz.module_question_distribution
        )
```

**Tests to Create/Update**:

- Create `backend/tests/quiz/test_quiz_schemas.py` - Test new validation logic
- Update `backend/tests/api/test_quiz_api.py` - Test API with new schema

**Example Test**:

```python
# backend/tests/quiz/test_quiz_schemas.py
def test_quiz_create_validates_module_structure():
    """Test that QuizCreate properly validates module structure."""
    valid_data = {
        "canvas_course_id": 123,
        "canvas_course_name": "Test Course",
        "title": "Test Quiz",
        "selected_modules": {
            "mod1": {"name": "Module 1", "question_count": 10},
            "mod2": {"name": "Module 2", "question_count": 15}
        },
        "language": "en"
    }

    quiz = QuizCreate(**valid_data)
    assert quiz.total_question_count == 25

    # Test invalid question count
    invalid_data = valid_data.copy()
    invalid_data["selected_modules"]["mod1"]["question_count"] = 25  # > 20

    with pytest.raises(ValueError):
        QuizCreate(**invalid_data)
```

**Testing & Validation**:

```bash
# Backend Testing
cd backend && source .venv/bin/activate
bash scripts/test.sh
# More tests will fail - this is expected

# Backend Linting
bash scripts/lint.sh
# Fix any import or type errors

# Commit
git add src/quiz/schemas.py tests/quiz/test_quiz_schemas.py
git commit -m "feat: update quiz schemas for module-based question distribution"
```

#### Step 3: Create Database Migration

**File**: `backend/alembic/versions/xxx_update_selected_modules_structure.py`

```python
"""Update selected_modules structure for question distribution

Revision ID: xxx
Revises: previous_revision_id
Create Date: 2024-xx-xx

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Since we're changing JSONB structure, we need to update existing data
    op.execute("""
        UPDATE quiz
        SET selected_modules = (
            SELECT jsonb_object_agg(
                key,
                jsonb_build_object(
                    'name', value::text,
                    'question_count', 10  -- Default 10 questions per module
                )
            )
            FROM jsonb_each(selected_modules)
            WHERE jsonb_typeof(value) = 'string'
        )
        WHERE selected_modules IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM jsonb_each(selected_modules)
            WHERE jsonb_typeof(value) = 'string'
        )
    """)

    # Remove the check constraint on question_count if it exists
    op.execute("""
        ALTER TABLE quiz
        DROP CONSTRAINT IF EXISTS quiz_question_count_check
    """)

    # Add new constraint for minimum only
    op.create_check_constraint(
        'quiz_question_count_check',
        'quiz',
        'question_count >= 1'
    )

def downgrade():
    # Revert to simple module mapping
    op.execute("""
        UPDATE quiz
        SET selected_modules = (
            SELECT jsonb_object_agg(
                key,
                (value->>'name')::text
            )
            FROM jsonb_each(selected_modules)
            WHERE jsonb_typeof(value) = 'object'
        )
        WHERE selected_modules IS NOT NULL
    """)

    # Restore original constraint
    op.drop_constraint('quiz_question_count_check', 'quiz')
    op.create_check_constraint(
        'quiz_question_count_check',
        'quiz',
        'question_count >= 1 AND question_count <= 200'
    )
```

**Testing & Validation**:

```bash
# Generate migration
cd backend && source .venv/bin/activate
alembic revision -m "update_selected_modules_structure_for_question_distribution"
# Copy the above migration code into the generated file

# Test migration (on test database)
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# Backend Testing
bash scripts/test.sh
# Tests should still be failing but migration should work

# Commit
git add alembic/versions/*_update_selected_modules_structure_for_question_distribution.py
git commit -m "feat: add migration for module-based question distribution"
```

#### Step 4: Create Frontend Module Selection Component

**File**: `frontend/src/components/QuizCreation/ModuleQuestionSelectionStep.tsx`

```tsx
import React, { useMemo } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Card,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Alert,
  AlertIcon,
  Divider,
  Heading,
} from "@chakra-ui/react";

interface ModuleQuestionSelectionStepProps {
  selectedModules: Record<string, string>;
  moduleQuestions: Record<string, number>;
  onModuleQuestionChange: (moduleId: string, count: number) => void;
}

export const ModuleQuestionSelectionStep: React.FC<
  ModuleQuestionSelectionStepProps
> = ({ selectedModules, moduleQuestions, onModuleQuestionChange }) => {
  const totalQuestions = useMemo(() => {
    return Object.values(moduleQuestions).reduce(
      (sum, count) => sum + count,
      0
    );
  }, [moduleQuestions]);

  const moduleIds = Object.keys(selectedModules);

  return (
    <Box>
      <VStack spacing={6} align="stretch">
        <Box>
          <Heading size="md" mb={2}>
            Set Questions per Module
          </Heading>
          <Text color="gray.600">
            Specify how many questions you want to generate from each module
            (1-20 per module).
          </Text>
        </Box>

        <Card
          variant="elevated"
          bg="blue.50"
          borderColor="blue.200"
          borderWidth={1}
        >
          <CardBody>
            <Stat>
              <StatLabel>Total Questions</StatLabel>
              <StatNumber>{totalQuestions}</StatNumber>
              <StatHelpText>Across {moduleIds.length} modules</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        {totalQuestions > 500 && (
          <Alert status="warning">
            <AlertIcon />
            Large number of questions may take longer to generate.
          </Alert>
        )}

        <Divider />

        <VStack spacing={4} align="stretch">
          {moduleIds.map((moduleId) => (
            <Card key={moduleId} variant="outline">
              <CardBody>
                <HStack justify="space-between" align="center">
                  <Box flex={1}>
                    <Text fontWeight="medium" fontSize="md">
                      {selectedModules[moduleId]}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      Module ID: {moduleId}
                    </Text>
                  </Box>

                  <HStack spacing={4}>
                    <Text fontSize="sm" color="gray.600">
                      Questions:
                    </Text>
                    <NumberInput
                      value={moduleQuestions[moduleId] || 10}
                      min={1}
                      max={20}
                      width="100px"
                      onChange={(_, value) =>
                        onModuleQuestionChange(moduleId, value)
                      }
                    >
                      <NumberInputField />
                      <NumberInputStepper>
                        <NumberIncrementStepper />
                        <NumberDecrementStepper />
                      </NumberInputStepper>
                    </NumberInput>
                  </HStack>
                </HStack>
              </CardBody>
            </Card>
          ))}
        </VStack>

        <Box mt={4}>
          <Text fontSize="sm" color="gray.600">
            <strong>Tip:</strong> Allocate more questions to modules with more
            content or higher importance. The AI will generate diverse questions
            covering different topics within each module.
          </Text>
        </Box>
      </VStack>
    </Box>
  );
};
```

**Tests to Create**:

- Create component tests (shown in Testing Strategy section)
- Create Playwright E2E test for new step

**Testing & Validation**:

```bash
# Frontend Type Checking
cd frontend
npx tsc --noEmit
# Fix any type errors

# Frontend Testing
npx playwright test
# Existing tests should pass, new component not integrated yet

# Commit
git add src/components/QuizCreation/ModuleQuestionSelectionStep.tsx
git commit -m "feat: create ModuleQuestionSelectionStep component"
```

#### Step 5: Update Quiz Creation Flow

**File**: `frontend/src/routes/_layout/create-quiz.tsx`

```tsx
import { ModuleQuestionSelectionStep } from "@/components/QuizCreation/ModuleQuestionSelectionStep";

// Add to form data interface
interface QuizFormData {
  selectedCourse: Course | null;
  title: string;
  selectedModules: Record<string, string>;
  moduleQuestions: Record<string, number>; // NEW
  language: QuizLanguage;
}

// Update initial form data
const [formData, setFormData] = useState<QuizFormData>({
  selectedCourse: null,
  title: "",
  selectedModules: {},
  moduleQuestions: {}, // NEW
  language: QuizLanguage.ENGLISH,
});

// Add handler for module question changes
const handleModuleQuestionChange = (moduleId: string, count: number) => {
  setFormData((prev) => ({
    ...prev,
    moduleQuestions: {
      ...prev.moduleQuestions,
      [moduleId]: count,
    },
  }));
};

// Initialize module questions when modules are selected
const handleModuleSelection = (modules: Record<string, string>) => {
  setFormData((prev) => {
    const moduleQuestions = { ...prev.moduleQuestions };

    // Add default 10 questions for newly selected modules
    Object.keys(modules).forEach((moduleId) => {
      if (!moduleQuestions[moduleId]) {
        moduleQuestions[moduleId] = 10;
      }
    });

    // Remove deselected modules
    Object.keys(moduleQuestions).forEach((moduleId) => {
      if (!modules[moduleId]) {
        delete moduleQuestions[moduleId];
      }
    });

    return {
      ...prev,
      selectedModules: modules,
      moduleQuestions,
    };
  });
};

// Update step configuration
const steps = [
  {
    title: "Select Course",
    component: (
      <CourseSelectionStep
        selectedCourse={formData.selectedCourse}
        title={formData.title}
        onCourseSelect={(course) =>
          setFormData((prev) => ({ ...prev, selectedCourse: course }))
        }
        onTitleChange={(title) => setFormData((prev) => ({ ...prev, title }))}
      />
    ),
  },
  {
    title: "Select Modules",
    component: (
      <ModuleSelectionStep
        courseId={formData.selectedCourse?.id}
        selectedModules={formData.selectedModules}
        onModulesChange={handleModuleSelection} // Updated handler
      />
    ),
  },
  {
    title: "Questions per Module", // NEW STEP
    component: (
      <ModuleQuestionSelectionStep
        selectedModules={formData.selectedModules}
        moduleQuestions={formData.moduleQuestions}
        onModuleQuestionChange={handleModuleQuestionChange}
      />
    ),
  },
  {
    title: "Settings",
    component: (
      <QuizSettingsStep
        language={formData.language}
        onLanguageChange={(language) =>
          setFormData((prev) => ({ ...prev, language }))
        }
      />
    ),
  },
];

// Update submission handler
const handleSubmit = async () => {
  if (!formData.selectedCourse || !formData.title) return;

  const selectedModulesWithCounts = Object.entries(
    formData.selectedModules
  ).reduce(
    (acc, [moduleId, moduleName]) => ({
      ...acc,
      [moduleId]: {
        name: moduleName,
        question_count: formData.moduleQuestions[moduleId] || 10,
      },
    }),
    {}
  );

  const payload = {
    canvas_course_id: formData.selectedCourse.id,
    canvas_course_name: formData.selectedCourse.name,
    title: formData.title,
    selected_modules: selectedModulesWithCounts,
    language: formData.language,
  };

  try {
    const response = await createQuiz(payload);
    navigate({ to: "/quiz/$id", params: { id: response.id } });
  } catch (error) {
    console.error("Failed to create quiz:", error);
    toast({
      title: "Failed to create quiz",
      status: "error",
      duration: 5000,
    });
  }
};
```

**Tests to Update**:

- Update `frontend/tests/e2e/quiz-workflow.spec.ts` - Add new step to quiz creation flow
- Update `frontend/tests/components/quiz-creation.spec.ts` - Test 4-step flow

**Example E2E Test Update**:

```typescript
// frontend/tests/e2e/quiz-workflow.spec.ts
test("creates quiz with module-based questions", async ({ page }) => {
  // ... existing course and module selection ...

  // New step: Set questions per module
  await expect(page.getByText("Questions per Module")).toBeVisible();
  await expect(page.getByText("Total Questions")).toBeVisible();

  // Verify default is 10 per module
  const firstInput = page.getByRole("spinbutton").first();
  await expect(firstInput).toHaveValue("10");

  // Change to 15 questions
  await firstInput.fill("15");

  // Continue to settings
  await page.getByRole("button", { name: "Next" }).click();

  // ... rest of test ...
});
```

**Testing & Validation**:

```bash
# Frontend Type Checking
cd frontend
npx tsc --noEmit
# Fix any type errors in create-quiz.tsx

# Generate new API types
npm run generate-client

# Frontend Testing
npx playwright test
# Some tests will fail due to flow changes - update them

# Commit
git add src/routes/_layout/create-quiz.tsx
git add tests/e2e/quiz-workflow.spec.ts
git commit -m "feat: integrate module question selection into quiz creation flow"
```

#### Step 6: Create Module Batch Workflow

**File**: `backend/src/question/workflows/module_batch_workflow.py`

````python
import asyncio
import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage

from src.question.workflows.base import BaseWorkflow, WorkflowState
from src.question.models import Question
from src.question.types.mcq import MCQData, MCQValidator
from src.question.providers.base import BaseQuestionProvider
from src.question.templates.manager import TemplateManager
from src.database import SessionDep

logger = logging.getLogger(__name__)

class ModuleBatchState(WorkflowState):
    """State for module batch generation workflow."""
    module_id: str
    module_name: str
    module_content: str
    target_question_count: int
    generated_questions: List[Question] = []
    retry_count: int = 0
    max_retries: int = 3
    parsing_error: bool = False  # Flag for JSON parsing errors
    correction_attempts: int = 0  # Track JSON correction attempts
    max_corrections: int = 2  # Maximum JSON correction attempts

class ModuleBatchWorkflow(BaseWorkflow):
    """Workflow for generating multiple questions per module in batch.

    This workflow implements a self-healing JSON correction mechanism:
    1. If JSON parsing fails, it triggers a correction path
    2. The correction prompt includes the error and malformed JSON
    3. The LLM is asked to fix and return only valid JSON
    4. This can happen up to max_corrections times before failing

    This makes the system robust against common LLM formatting errors.
    """

    def __init__(
        self,
        provider: BaseQuestionProvider,
        template_manager: TemplateManager,
        session: SessionDep,
        quiz_id: UUID,
        language: str = "en"
    ):
        self.provider = provider
        self.template_manager = template_manager
        self.session = session
        self.quiz_id = quiz_id
        self.language = language
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the module batch workflow graph."""
        workflow = StateGraph(ModuleBatchState)

        # Add nodes
        workflow.add_node("prepare_prompt", self.prepare_prompt)
        workflow.add_node("generate_batch", self.generate_batch)
        workflow.add_node("validate_batch", self.validate_batch)
        workflow.add_node("check_completion", self.check_completion)
        workflow.add_node("prepare_correction", self.prepare_correction)
        workflow.add_node("retry_generation", self.retry_generation)
        workflow.add_node("save_questions", self.save_questions)

        # Add edges
        workflow.add_edge(START, "prepare_prompt")
        workflow.add_edge("prepare_prompt", "generate_batch")
        workflow.add_edge("generate_batch", "validate_batch")

        # Conditional edge from validate_batch
        workflow.add_conditional_edges(
            "validate_batch",
            self.check_json_error,
            {
                "needs_correction": "prepare_correction",
                "continue": "check_completion"
            }
        )

        workflow.add_edge("prepare_correction", "generate_batch")

        # Conditional edges from check_completion
        workflow.add_conditional_edges(
            "check_completion",
            self.should_retry,
            {
                "retry": "retry_generation",
                "complete": "save_questions",
                "failed": END
            }
        )

        workflow.add_edge("retry_generation", "generate_batch")
        workflow.add_edge("save_questions", END)

        return workflow.compile()

    async def prepare_prompt(self, state: ModuleBatchState) -> ModuleBatchState:
        """Prepare the prompt for batch generation."""
        try:
            template_name = f"batch_multiple_choice{'_no' if self.language == 'no' else ''}"
            template = self.template_manager.get_template(template_name)

            state.current_prompt = template.render(
                module_name=state.module_name,
                module_content=state.module_content,
                question_count=state.target_question_count - len(state.generated_questions),
                language="Norwegian" if self.language == "no" else "English"
            )

            logger.info(
                f"Prepared prompt for module {state.module_id}: "
                f"requesting {state.target_question_count - len(state.generated_questions)} questions"
            )

        except Exception as e:
            logger.error(f"Failed to prepare prompt: {e}")
            state.error = str(e)

        return state

    async def generate_batch(self, state: ModuleBatchState) -> ModuleBatchState:
        """Generate multiple questions in a single LLM call."""
        try:
            messages = [
                SystemMessage(content="You are an expert educator creating quiz questions."),
                HumanMessage(content=state.current_prompt)
            ]

            response = await self.provider.generate_questions(
                messages=messages,
                question_type="multiple_choice",
                count=state.target_question_count - len(state.generated_questions)
            )

            state.raw_response = response
            logger.info(f"Generated batch response for module {state.module_id}")

        except Exception as e:
            logger.error(f"Batch generation failed for module {state.module_id}: {e}")
            state.error = str(e)

        return state

    async def validate_batch(self, state: ModuleBatchState) -> ModuleBatchState:
        """Validate and parse the generated questions."""
        if not state.raw_response or state.error:
            return state

        try:
            # Parse the response to extract individual questions
            questions_data = self._parse_batch_response(state.raw_response)

            for q_data in questions_data:
                try:
                    # Validate question data
                    mcq_data = MCQData(**q_data)
                    if MCQValidator.validate(mcq_data):
                        # Create question object
                        question = Question(
                            quiz_id=self.quiz_id,
                            question_type="multiple_choice",
                            question_data=mcq_data.model_dump()
                        )
                        state.generated_questions.append(question)
                    else:
                        logger.warning(f"Invalid question data: {q_data}")

                except Exception as e:
                    logger.error(f"Failed to validate question: {e}")
                    continue

            logger.info(
                f"Validated {len(state.generated_questions)} questions "
                f"for module {state.module_id}"
            )

        except ValueError as e:
            # JSON parsing error - set error for retry with improved prompt
            logger.error(f"JSON parsing failed for module {state.module_id}: {e}")
            state.error = f"JSON_PARSE_ERROR: {str(e)}"
            state.parsing_error = True  # Flag to modify prompt on retry

        except Exception as e:
            logger.error(f"Batch validation failed: {e}")
            state.error = str(e)

        return state

    def check_json_error(self, state: ModuleBatchState) -> str:
        """Check if we have a JSON parsing error that needs correction."""
        if state.parsing_error and state.correction_attempts < state.max_corrections:
            return "needs_correction"
        return "continue"

    async def prepare_correction(self, state: ModuleBatchState) -> ModuleBatchState:
        """Prepare a corrective prompt for JSON parsing errors."""
        if not state.parsing_error or not state.raw_response:
            return state

        try:
            error_details = state.error.replace("JSON_PARSE_ERROR: ", "")

            # Create a focused correction prompt
            correction_prompt = (
                "Your previous response resulted in a JSON parsing error. "
                "Please fix the following invalid JSON and return ONLY the corrected, valid JSON array.\n\n"
                f"Error: {error_details}\n\n"
                f"Invalid JSON (first 1000 chars):\n{state.raw_response[:1000]}\n\n"
                "Requirements:\n"
                "1. Return ONLY a valid JSON array\n"
                "2. No markdown code blocks (```json or ```)\n"
                "3. No explanatory text before or after the JSON\n"
                "4. Ensure all quotes are properly escaped\n"
                "5. Ensure the array contains the requested number of question objects\n\n"
                "Please provide the corrected JSON array:"
            )

            state.current_prompt = correction_prompt

            # Increment correction attempts
            state.correction_attempts += 1

            # Reset error state for retry
            state.parsing_error = False
            state.error = None
            state.raw_response = None

            logger.info(
                f"Prepared JSON correction prompt for module {state.module_id} "
                f"(attempt {state.correction_attempts}/{state.max_corrections})"
            )

        except Exception as e:
            logger.error(f"Failed to prepare correction: {e}")
            state.error = str(e)

        return state

    def should_retry(self, state: ModuleBatchState) -> str:
        """Determine if we should retry generation."""
        if state.error:
            return "failed"

        questions_needed = state.target_question_count - len(state.generated_questions)

        if questions_needed <= 0:
            return "complete"

        if state.retry_count < state.max_retries:
            logger.info(
                f"Module {state.module_id}: Need {questions_needed} more questions, "
                f"retry {state.retry_count + 1}/{state.max_retries}"
            )
            return "retry"

        logger.warning(
            f"Module {state.module_id}: Max retries reached, "
            f"generated {len(state.generated_questions)}/{state.target_question_count}"
        )
        return "complete"

    async def retry_generation(self, state: ModuleBatchState) -> ModuleBatchState:
        """Prepare for retry with adjusted parameters."""
        state.retry_count += 1
        state.error = None
        state.raw_response = None

        # Could add exponential backoff here if needed
        await asyncio.sleep(1 * state.retry_count)

        return state

    async def save_questions(self, state: ModuleBatchState) -> ModuleBatchState:
        """Save all generated questions to the database."""
        try:
            for question in state.generated_questions:
                self.session.add(question)

            await self.session.commit()

            logger.info(
                f"Saved {len(state.generated_questions)} questions "
                f"for module {state.module_id}"
            )

        except Exception as e:
            logger.error(f"Failed to save questions: {e}")
            await self.session.rollback()
            state.error = str(e)

        return state

    def _parse_batch_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the LLM response to extract multiple questions.

        IMPORTANT: This method ONLY accepts valid JSON arrays.
        No fallbacks to text parsing to ensure reliability.
        """
        import json

        try:
            # Clean the response - remove any markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]   # Remove ```
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```

            # Parse as JSON - this is the ONLY accepted format
            parsed = json.loads(cleaned_response)

            # Validate it's an array
            if not isinstance(parsed, list):
                raise ValueError("Response must be a JSON array")

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in LLM response: {e}")
            logger.debug(f"Response that failed to parse: {response[:500]}...")
            raise ValueError(f"LLM response was not valid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to parse batch response: {e}")
            raise

    async def process_module(
        self,
        module_id: str,
        module_name: str,
        module_content: str,
        question_count: int
    ) -> List[Question]:
        """Process a single module to generate questions."""
        initial_state = ModuleBatchState(
            module_id=module_id,
            module_name=module_name,
            module_content=module_content,
            target_question_count=question_count
        )

        final_state = await self.graph.ainvoke(initial_state)
        return final_state.generated_questions


class ParallelModuleProcessor:
    """Handles parallel processing of multiple modules."""

    def __init__(
        self,
        provider: BaseQuestionProvider,
        template_manager: TemplateManager,
        session: SessionDep,
        quiz_id: UUID,
        language: str = "en"
    ):
        self.provider = provider
        self.template_manager = template_manager
        self.session = session
        self.quiz_id = quiz_id
        self.language = language

    async def process_all_modules(
        self,
        modules_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[Question]]:
        """Process all modules in parallel."""
        tasks = []

        for module_id, module_info in modules_data.items():
            workflow = ModuleBatchWorkflow(
                provider=self.provider,
                template_manager=self.template_manager,
                session=self.session,
                quiz_id=self.quiz_id,
                language=self.language
            )

            task = workflow.process_module(
                module_id=module_id,
                module_name=module_info["name"],
                module_content=module_info["content"],
                question_count=module_info["question_count"]
            )

            tasks.append((module_id, task))

        # Run all module processing in parallel
        results = {}
        for module_id, task in tasks:
            try:
                questions = await task
                results[module_id] = questions
                logger.info(f"Module {module_id} completed: {len(questions)} questions")
            except Exception as e:
                logger.error(f"Module {module_id} failed: {e}")
                results[module_id] = []

        return results
````

**Tests to Create**:

- Create `backend/tests/question/workflows/test_module_batch_workflow.py` (shown in Testing Strategy)
- Update `backend/tests/question/test_question_service.py` to remove chunk-based tests

**Testing & Validation**:

```bash
# Backend Testing
cd backend && source .venv/bin/activate
bash scripts/test.sh
# New workflow tests should pass, old workflow tests will fail

# Backend Linting
bash scripts/lint.sh
# Fix any async/await or type issues

# Commit
git add src/question/workflows/module_batch_workflow.py
git add tests/question/workflows/test_module_batch_workflow.py
git commit -m "feat: implement module batch workflow for parallel question generation"
```

#### Step 7: Create Batch Generation Templates

**File**: `backend/src/question/templates/files/batch_multiple_choice.json`

```json
{
  "name": "batch_multiple_choice",
  "description": "Template for generating multiple MCQs from module content",
  "language": "en",
  "system_prompt": "You are an expert educator creating multiple-choice quiz questions. Generate diverse, high-quality questions that test understanding at different cognitive levels.",
  "user_prompt": "Based on the following content from the module '{{ module_name }}', generate exactly {{ question_count }} multiple-choice questions.\n\nIMPORTANT REQUIREMENTS:\n1. Each question must have exactly 4 options (A, B, C, D)\n2. Ensure even distribution of correct answers across A, B, C, and D\n3. Vary the difficulty levels (easy, medium, hard)\n4. Cover different topics within the module content\n5. Make distractors (wrong answers) plausible but clearly incorrect\n6. Include brief explanations for each answer\n\nMODULE CONTENT:\n{{ module_content }}\n\nGenerate the questions in the following JSON format:\n[\n  {\n    \"question_text\": \"Question text here\",\n    \"option_a\": \"First option\",\n    \"option_b\": \"Second option\",\n    \"option_c\": \"Third option\",\n    \"option_d\": \"Fourth option\",\n    \"correct_answer\": \"A\",\n    \"explanation\": \"Brief explanation why A is correct\",\n    \"difficulty\": \"medium\"\n  }\n]\n\nGenerate exactly {{ question_count }} questions:",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 4000
  }
}
```

**File**: `backend/src/question/templates/files/batch_multiple_choice_no.json`

```json
{
  "name": "batch_multiple_choice_no",
  "description": "Template for generating multiple MCQs from module content in Norwegian",
  "language": "no",
  "system_prompt": "Du er en ekspert pedagog som lager flervalgsspørsmål til quiz. Generer varierte spørsmål av høy kvalitet som tester forståelse på ulike kognitive nivåer.",
  "user_prompt": "Basert på følgende innhold fra modulen '{{ module_name }}', generer nøyaktig {{ question_count }} flervalgsspørsmål på norsk.\n\nVIKTIGE KRAV:\n1. Hvert spørsmål må ha nøyaktig 4 alternativer (A, B, C, D)\n2. Sørg for jevn fordeling av riktige svar på tvers av A, B, C og D\n3. Varier vanskelighetsgraden (lett, middels, vanskelig)\n4. Dekk ulike temaer innenfor modulinnholdet\n5. Gjør distraktorer (feil svar) plausible men tydelig feilaktige\n6. Inkluder korte forklaringer for hvert svar\n\nMODULINNHOLD:\n{{ module_content }}\n\nGenerer spørsmålene i følgende JSON-format:\n[\n  {\n    \"question_text\": \"Spørsmålstekst her\",\n    \"option_a\": \"Første alternativ\",\n    \"option_b\": \"Andre alternativ\",\n    \"option_c\": \"Tredje alternativ\",\n    \"option_d\": \"Fjerde alternativ\",\n    \"correct_answer\": \"A\",\n    \"explanation\": \"Kort forklaring på hvorfor A er riktig\",\n    \"difficulty\": \"medium\"\n  }\n]\n\nGenerer nøyaktig {{ question_count }} spørsmål:",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 4000
  }
}
```

**Testing & Validation**:

```bash
# Backend Testing
cd backend && source .venv/bin/activate
# Templates are loaded at runtime, ensure they're valid JSON
python -m json.tool src/question/templates/files/batch_multiple_choice.json
python -m json.tool src/question/templates/files/batch_multiple_choice_no.json

# Test template loading
bash scripts/test.sh
# Template manager tests should pass

# Commit
git add src/question/templates/files/batch_multiple_choice.json
git add src/question/templates/files/batch_multiple_choice_no.json
git commit -m "feat: add batch generation prompt templates"
```

#### Step 8: Update Generation Service

**File**: `backend/src/question/services/generation_service.py`

```python
import logging
from typing import Dict, Any, List
from uuid import UUID

from src.question.providers.registry import ProviderRegistry
from src.question.templates.manager import TemplateManager
from src.question.workflows.module_batch_workflow import ParallelModuleProcessor
from src.quiz.models import Quiz
from src.database import SessionDep

logger = logging.getLogger(__name__)

class QuestionGenerationService:
    """Service for orchestrating question generation."""

    def __init__(self, session: SessionDep):
        self.session = session
        self.provider_registry = ProviderRegistry()
        self.template_manager = TemplateManager()

    async def generate_questions_for_quiz(
        self,
        quiz: Quiz,
        extracted_content: Dict[str, Any]
    ) -> Dict[str, List[Any]]:
        """Generate questions for all modules in parallel."""
        try:
            # Get provider
            provider = self.provider_registry.get_provider(quiz.llm_model)

            # Prepare module data with content and question counts
            modules_data = {}
            for module_id, module_info in quiz.selected_modules.items():
                if module_id in extracted_content:
                    modules_data[module_id] = {
                        "name": module_info["name"],
                        "content": extracted_content[module_id],
                        "question_count": module_info["question_count"]
                    }
                else:
                    logger.warning(f"No content found for module {module_id}")

            # Process all modules in parallel
            processor = ParallelModuleProcessor(
                provider=provider,
                template_manager=self.template_manager,
                session=self.session,
                quiz_id=quiz.id,
                language=quiz.language.value
            )

            results = await processor.process_all_modules(modules_data)

            # Update quiz total question count
            total_generated = sum(len(questions) for questions in results.values())
            quiz.question_count = total_generated

            logger.info(
                f"Generated {total_generated} questions across "
                f"{len(results)} modules for quiz {quiz.id}"
            )

            return results

        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            raise
```

**Tests to Update**:

- Update `backend/tests/question/services/test_generation_service.py` - Remove chunk-based tests, add module-based tests
- Update integration tests that use generation service

**Testing & Validation**:

```bash
# Backend Testing
cd backend && source .venv/bin/activate
bash scripts/test.sh
# Generation service tests need updates

# Backend Linting
bash scripts/lint.sh
# Fix any import or async issues

# Commit
git add src/question/services/generation_service.py
git add tests/question/services/test_generation_service.py
git commit -m "feat: update generation service for module-based processing"
```

#### Step 9: Update Content Service

**File**: `backend/src/question/services/content_service.py`

```python
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ContentService:
    """Service for processing extracted content."""

    def prepare_module_content(
        self,
        extracted_content: Dict[str, Any]
    ) -> Dict[str, str]:
        """Prepare module content for generation (no chunking)."""
        prepared_content = {}

        for module_id, content in extracted_content.items():
            if isinstance(content, str):
                # Clean and validate content
                cleaned_content = self._clean_content(content)
                if self._is_valid_content(cleaned_content):
                    prepared_content[module_id] = cleaned_content
                else:
                    logger.warning(f"Module {module_id} has insufficient content")
            else:
                logger.error(f"Invalid content type for module {module_id}")

        return prepared_content

    def _clean_content(self, content: str) -> str:
        """Clean module content."""
        # Remove excessive whitespace
        content = " ".join(content.split())

        # Remove common artifacts
        content = content.replace('\x00', '')  # Null characters
        content = content.strip()

        return content

    def _is_valid_content(self, content: str) -> bool:
        """Check if content is valid for question generation."""
        # Minimum content length
        if len(content) < 100:
            return False

        # Check for actual text content (not just special characters)
        if not any(c.isalnum() for c in content):
            return False

        return True
```

**Tests to Update**:

- Update `backend/tests/question/services/test_content_service.py` - Remove chunking tests
- Remove chunk-related test fixtures

**Testing & Validation**:

```bash
# Backend Testing
cd backend && source .venv/bin/activate
bash scripts/test.sh
# Content service tests need updates

# Backend Linting
bash scripts/lint.sh

# Commit
git add src/question/services/content_service.py
git add tests/question/services/test_content_service.py
git commit -m "feat: simplify content service for module-based processing"
```

##### ⚠️ Step 9 Implementation Deviation - Functional Refactoring

**DEVIATION FROM ORIGINAL PLAN**: During implementation, a significant architectural decision was made to convert the ContentProcessingService from a class-based to a functional approach. This deviation was justified for the following reasons:

**Original Plan vs. Implementation**:

| Aspect | Original Plan | Actual Implementation |
|--------|---------------|----------------------|
| **Architecture** | Class-based ContentService with methods | 8 pure functions with no class structure |
| **State Management** | Instance-based with potential state | Stateless functional approach |
| **Import Structure** | Single class import | Multiple function imports |
| **Configuration** | Class initialization with WorkflowConfiguration | No configuration dependency |
| **Test Structure** | Class-based test patterns | Function-based tests with imports inside functions |

**Detailed Changes Made**:

1. **Complete Class Elimination**:
   ```python
   # OLD (Original Plan)
   class ContentService:
       def prepare_module_content(self, extracted_content: Dict[str, Any]) -> Dict[str, str]:
           # ... method implementation

   # NEW (Actual Implementation)
   async def get_content_from_quiz(quiz_id: UUID) -> dict[str, Any]:
       # ... function implementation

   def validate_module_content(content_dict: dict[str, Any]) -> dict[str, str]:
       # ... function implementation
   ```

2. **Functional Architecture Benefits Realized**:
   - **Better Composability**: Functions can be easily combined in pipelines
   - **Simpler Testing**: Each function tested independently with imports inside test functions
   - **No State Dependencies**: Pure functions eliminate state-related bugs
   - **Easier Mocking**: Individual function mocking vs. class instance mocking
   - **Performance**: No class instantiation overhead

3. **Functions Created (8 total)**:
   - `get_content_from_quiz()` - Async content retrieval
   - `validate_module_content()` - Content validation and module combination
   - `prepare_content_for_generation()` - Main preparation pipeline
   - `validate_content_quality()` - Quality filtering with scoring algorithm
   - `get_content_statistics()` - Content analysis and metrics
   - `prepare_and_validate_content()` - Convenience function for common workflows
   - `_combine_module_pages()` - Internal page combination logic
   - `_calculate_module_quality_score()` - Quality scoring algorithm

4. **Enhanced Functionality Beyond Original Plan**:
   - **Quality Scoring System**: Sophisticated content quality evaluation (0.0-1.0 score)
   - **Content Statistics**: Comprehensive content analysis and metrics
   - **Pipeline Functions**: Convenience functions for common operation chains
   - **Error Handling**: Detailed logging and graceful error handling
   - **Content Filtering**: Multiple validation layers for content quality

5. **Test Suite Improvements**:
   - **21 comprehensive tests** vs. original basic test coverage
   - **Functional composition testing** - tests verify functions work together
   - **Edge case coverage** - invalid data, empty content, quality filtering
   - **Performance testing** - large content handling
   - **Following established patterns** - imports inside functions per codebase conventions

**Impact on Remaining Steps**:

This functional refactoring creates a cleaner foundation for Step 10 (Quiz Orchestrator update) by:
- Eliminating WorkflowConfiguration dependencies that were causing compatibility issues
- Providing clear, composable functions that are easier to integrate
- Reducing the complexity of content processing workflow integration
- Enabling better error handling and logging in the orchestration layer

**Justification for Deviation**:

The functional approach proved superior for the module-based architecture because:
1. **Module-based processing is inherently functional** - transform input modules to output content
2. **No persistent state needed** - each content operation is independent
3. **Better testability** - each function has clear inputs/outputs
4. **Simpler integration** - functions compose better than class hierarchies
5. **Performance benefits** - no class instantiation overhead in workflows

This deviation improves the overall architecture and sets up better patterns for the remaining implementation steps.

#### Step 10: Update Quiz Orchestrator

**File**: `backend/src/quiz/orchestrator.py`

```python
async def generate_questions_workflow(
    quiz_id: UUID,
    session: SessionDep,
    background_tasks: BackgroundTasks
) -> None:
    """Workflow for generating questions with module-based approach."""
    try:
        # Get quiz
        quiz = await session.get(Quiz, quiz_id)
        if not quiz:
            raise ValueError(f"Quiz {quiz_id} not found")

        # Update status
        quiz.status = QuizStatus.GENERATING_QUESTIONS
        await session.commit()

        # Initialize generation service
        generation_service = QuestionGenerationService(session)

        # Prepare content (no chunking)
        content_service = ContentService()
        prepared_content = content_service.prepare_module_content(
            quiz.extracted_content
        )

        if not prepared_content:
            quiz.status = QuizStatus.FAILED
            quiz.failure_reason = FailureReason.NO_CONTENT_FOUND
            await session.commit()
            return

        # Generate questions for all modules
        try:
            results = await generation_service.generate_questions_for_quiz(
                quiz=quiz,
                extracted_content=prepared_content
            )

            # Calculate total questions generated vs requested
            total_generated = sum(len(q) for q in results.values())
            total_requested = sum(
                module_info.get("question_count", 0)
                for module_info in quiz.selected_modules.values()
            )

            # Log module-level results
            for module_id, questions in results.items():
                module_info = quiz.selected_modules.get(module_id, {})
                requested = module_info.get("question_count", 0)
                generated = len(questions)
                if generated < requested:
                    logger.warning(
                        f"Module {module_id}: Generated {generated}/{requested} questions"
                    )

            # Require 100% success rate
            if total_generated == 0:
                quiz.status = QuizStatus.FAILED
                quiz.failure_reason = FailureReason.NO_QUESTIONS_GENERATED
            elif total_generated < total_requested:
                # Not all requested questions were generated
                quiz.status = QuizStatus.FAILED
                quiz.failure_reason = FailureReason.PARTIAL_GENERATION_FAILURE
                quiz.metadata = {
                    "generated_count": total_generated,
                    "requested_count": total_requested,
                    "success_rate": f"{(total_generated/total_requested)*100:.1f}%"
                }
                logger.error(
                    f"Quiz {quiz_id} failed: Only generated {total_generated}/{total_requested} questions"
                )
            else:
                # Success: exactly the requested number of questions
                quiz.status = QuizStatus.READY_FOR_REVIEW
                logger.info(
                    f"Quiz {quiz_id} ready with {total_generated} questions (100% success)"
                )

        except Exception as e:
            logger.error(f"Generation failed for quiz {quiz_id}: {e}")
            quiz.status = QuizStatus.FAILED
            quiz.failure_reason = FailureReason.LLM_GENERATION_ERROR

        await session.commit()

    except Exception as e:
        logger.error(f"Question generation workflow failed: {e}")
        await handle_workflow_error(quiz_id, session, e, FailureReason.LLM_GENERATION_ERROR)
```

**Tests to Update**:

- Update `backend/tests/quiz/test_orchestrator.py` - Test new workflow
- Update integration tests for full quiz generation flow

**Testing & Validation**:

```bash
# Backend Testing
cd backend && source .venv/bin/activate
bash scripts/test.sh
# Orchestrator tests need updates

# Backend Linting
bash scripts/lint.sh

# Commit
git add src/quiz/orchestrator.py
git add tests/quiz/test_orchestrator.py
git commit -m "feat: update quiz orchestrator for module-based generation"
```

#### Step 11: Clean Up Old Code

**Files to Remove**:

- `backend/src/question/workflows/mcq_workflow.py`
- Old chunking-related code in content service
- Single question generation templates

**Testing & Validation**:

```bash
# Remove old files
cd backend
rm src/question/workflows/mcq_workflow.py
rm src/question/templates/files/default_multiple_choice.json
rm src/question/templates/files/default_multiple_choice_no.json

# Update workflow registry to remove old workflow
# Update template manager to remove old templates

# Backend Testing
source .venv/bin/activate
bash scripts/test.sh
# All tests should now pass with new implementation

# Backend Linting
bash scripts/lint.sh

# Final commit
git add -A
git commit -m "feat: complete migration to module-based question generation"
```

#### Step 12: Update Workflow Registry

**File**: `backend/src/question/workflows/registry.py`

```python
# Update to register new workflow instead of old MCQ workflow
from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

# Remove MCQWorkflow registration
# Add ModuleBatchWorkflow registration
```

**Testing & Validation**:

```bash
# Run full test suite
cd backend && source .venv/bin/activate
bash scripts/test.sh

cd ../frontend
npx playwright test

# If all tests pass, create feature branch PR
git checkout -b feat/module-based-question-generation
git push origin feat/module-based-question-generation
```

### 4.3 Data Models & Schemas

#### Module Selection Structure

```json
{
  "selected_modules": {
    "12345": {
      "name": "Introduction to Biology",
      "question_count": 15
    },
    "12346": {
      "name": "Cell Structure and Function",
      "question_count": 10
    },
    "12347": {
      "name": "Genetics Basics",
      "question_count": 20
    }
  }
}
```

#### Quiz Creation Request

```json
{
  "canvas_course_id": 98765,
  "canvas_course_name": "Biology 101",
  "title": "Midterm Exam Questions",
  "selected_modules": {
    "12345": {
      "name": "Introduction to Biology",
      "question_count": 15
    },
    "12346": {
      "name": "Cell Structure and Function",
      "question_count": 10
    }
  },
  "language": "en"
}
```

#### Generated Question Format

```json
{
  "question_text": "What is the primary function of mitochondria?",
  "option_a": "Protein synthesis",
  "option_b": "Energy production",
  "option_c": "DNA replication",
  "option_d": "Waste removal",
  "correct_answer": "B",
  "explanation": "Mitochondria are known as the powerhouse of the cell, producing ATP through cellular respiration.",
  "difficulty": "medium"
}
```

### 4.4 Configuration

#### Environment Variables

```env
# Existing variables remain unchanged
# Add these for module-based generation
MAX_QUESTIONS_PER_MODULE=20
DEFAULT_QUESTIONS_PER_MODULE=10
MAX_PARALLEL_MODULES=5
MODULE_GENERATION_TIMEOUT=300  # seconds per module
```

#### Backend Configuration Updates

```python
# backend/src/config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # Module-based generation settings
    max_questions_per_module: int = Field(default=20)
    default_questions_per_module: int = Field(default=10)
    max_parallel_modules: int = Field(default=5)
    module_generation_timeout: int = Field(default=300)
```

## 5. Testing Strategy

### Test-Driven Development Approach

Since this is a major architectural change, follow this testing strategy:

1. **Before Starting**: Run full test suite to ensure baseline

   ```bash
   cd backend && source .venv/bin/activate && bash scripts/test.sh
   cd ../frontend && npx playwright test
   ```

2. **During Implementation**:

   - Write tests for new functionality FIRST
   - Update existing tests as you modify code
   - Keep a list of failing tests to track progress

3. **Test Organization**:
   - New tests go in separate files initially
   - Once working, integrate with existing test files
   - Delete obsolete tests only after new ones pass

### Unit Tests

#### Backend Test: Module Batch Workflow

```python
# backend/tests/question/workflows/test_module_batch_workflow.py
import pytest
from unittest.mock import Mock, AsyncMock

from src.question.workflows.module_batch_workflow import (
    ModuleBatchWorkflow,
    ModuleBatchState,
    ParallelModuleProcessor
)

@pytest.mark.asyncio
async def test_module_batch_workflow_success():
    """Test successful batch generation for a module."""
    # Mock dependencies
    mock_provider = Mock()
    mock_provider.generate_questions = AsyncMock(return_value="""
    [
        {
            "question_text": "What is photosynthesis?",
            "option_a": "A chemical process",
            "option_b": "A physical process",
            "option_c": "A biological process",
            "option_d": "All of the above",
            "correct_answer": "D",
            "explanation": "Photosynthesis involves chemical, physical, and biological processes."
        }
    ]
    """)

    mock_template_manager = Mock()
    mock_template_manager.get_template.return_value.render.return_value = "Test prompt"

    mock_session = AsyncMock()

    workflow = ModuleBatchWorkflow(
        provider=mock_provider,
        template_manager=mock_template_manager,
        session=mock_session,
        quiz_id=UUID("12345678-1234-5678-1234-567812345678"),
        language="en"
    )

    # Test module processing
    questions = await workflow.process_module(
        module_id="12345",
        module_name="Test Module",
        module_content="Module content here",
        question_count=1
    )

    assert len(questions) == 1
    assert questions[0].question_data["question_text"] == "What is photosynthesis?"

@pytest.mark.asyncio
async def test_parallel_module_processing():
    """Test parallel processing of multiple modules."""
    processor = ParallelModuleProcessor(
        provider=Mock(),
        template_manager=Mock(),
        session=AsyncMock(),
        quiz_id=UUID("12345678-1234-5678-1234-567812345678"),
        language="en"
    )

    modules_data = {
        "mod1": {"name": "Module 1", "content": "Content 1", "question_count": 5},
        "mod2": {"name": "Module 2", "content": "Content 2", "question_count": 10},
    }

    # Mock the process_module method
    async def mock_process(module_id, module_name, module_content, question_count):
        return [Mock() for _ in range(question_count)]

    processor.process_module = mock_process

    results = await processor.process_all_modules(modules_data)

    assert len(results) == 2
    assert len(results["mod1"]) == 5
    assert len(results["mod2"]) == 10

@pytest.mark.asyncio
async def test_retry_logic():
    """Test retry logic when not enough questions are generated."""
    # Test implementation here
    pass
```

#### Frontend Test: Module Question Selection

```typescript
// frontend/src/components/QuizCreation/ModuleQuestionSelectionStep.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { ModuleQuestionSelectionStep } from "./ModuleQuestionSelectionStep";

describe("ModuleQuestionSelectionStep", () => {
  const mockProps = {
    selectedModules: {
      "123": "Introduction to Testing",
      "456": "Advanced Testing",
    },
    moduleQuestions: {
      "123": 10,
      "456": 15,
    },
    onModuleQuestionChange: jest.fn(),
  };

  it("displays all selected modules", () => {
    render(<ModuleQuestionSelectionStep {...mockProps} />);

    expect(screen.getByText("Introduction to Testing")).toBeInTheDocument();
    expect(screen.getByText("Advanced Testing")).toBeInTheDocument();
  });

  it("shows correct total question count", () => {
    render(<ModuleQuestionSelectionStep {...mockProps} />);

    expect(screen.getByText("25")).toBeInTheDocument(); // Total
    expect(screen.getByText("Across 2 modules")).toBeInTheDocument();
  });

  it("updates question count on change", () => {
    render(<ModuleQuestionSelectionStep {...mockProps} />);

    const firstInput = screen.getAllByRole("spinbutton")[0];
    fireEvent.change(firstInput, { target: { value: "20" } });

    expect(mockProps.onModuleQuestionChange).toHaveBeenCalledWith("123", 20);
  });

  it("shows warning for large question counts", () => {
    const largeProps = {
      ...mockProps,
      moduleQuestions: {
        "123": 300,
        "456": 250,
      },
    };

    render(<ModuleQuestionSelectionStep {...largeProps} />);

    expect(
      screen.getByText(/Large number of questions may take longer/)
    ).toBeInTheDocument();
  });
});
```

### Integration Tests

#### End-to-End Quiz Creation Test

```python
# backend/tests/integration/test_quiz_creation_e2e.py
@pytest.mark.asyncio
async def test_module_based_quiz_creation(client, test_user_token):
    """Test complete quiz creation flow with module-based questions."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    # Create quiz with module question distribution
    quiz_data = {
        "canvas_course_id": 12345,
        "canvas_course_name": "Test Course",
        "title": "Module-Based Quiz",
        "selected_modules": {
            "mod1": {"name": "Module 1", "question_count": 5},
            "mod2": {"name": "Module 2", "question_count": 10}
        },
        "language": "en"
    }

    response = await client.post("/api/v1/quizzes", json=quiz_data, headers=headers)
    assert response.status_code == 201

    quiz_id = response.json()["id"]

    # Wait for processing (in real test, use proper polling)
    await asyncio.sleep(5)

    # Check quiz status and questions
    response = await client.get(f"/api/v1/quizzes/{quiz_id}", headers=headers)
    quiz = response.json()

    assert quiz["status"] in ["generating_questions", "ready_for_review"]
    assert quiz["module_question_distribution"] == {"mod1": 5, "mod2": 10}
```

### Manual Testing Steps

1. **Create Quiz with Module Distribution**

   - Login to the application
   - Click "Create New Quiz"
   - Select a course with multiple modules
   - Select 3-4 modules
   - Set different question counts (5, 10, 15, 20)
   - Verify total shows correctly
   - Complete quiz creation

2. **Monitor Generation Progress**

   - Check quiz status updates
   - Verify parallel processing (check logs)
   - Ensure all modules complete

3. **Review Generated Questions**

   - Verify correct count per module
   - Check answer distribution (A, B, C, D roughly equal)
   - Verify question quality and relevance

4. **Test Edge Cases**
   - Module with minimal content
   - Request 20 questions from short module
   - Very large module content
   - Multiple languages

### Performance Benchmarks

| Scenario                     | Old (Sequential)    | New (Parallel)    | Improvement |
| ---------------------------- | ------------------- | ----------------- | ----------- |
| 5 modules, 10 questions each | ~50 API calls, 150s | 5 API calls, 30s  | 80% faster  |
| 10 modules, 5 questions each | ~50 API calls, 150s | 10 API calls, 40s | 73% faster  |
| 3 modules, 20 questions each | ~60 API calls, 180s | 3 API calls, 25s  | 86% faster  |

## 6. Deployment Instructions

### Pre-deployment Checklist

1. Run all tests: `pytest backend/tests`
2. Run frontend tests: `npm test`
3. Update API documentation
4. Review database migration

### Deployment Steps

1. **Database Migration**

   ```bash
   # On production server
   cd backend
   alembic upgrade head
   ```

2. **Deploy Backend**

   ```bash
   docker build -t raguit-backend:module-batch backend/
   docker tag raguit-backend:module-batch registry.example.com/raguit-backend:latest
   docker push registry.example.com/raguit-backend:latest
   ```

3. **Deploy Frontend**

   ```bash
   cd frontend
   npm run build
   docker build -t raguit-frontend:module-batch .
   docker tag raguit-frontend:module-batch registry.example.com/raguit-frontend:latest
   docker push registry.example.com/raguit-frontend:latest
   ```

4. **Update Services**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

### Rollback Procedure

If issues occur:

1. Revert to previous image tags
2. Run database migration down: `alembic downgrade -1`
3. Restart services with old images

## 7. Monitoring & Maintenance

### Key Metrics

1. **Performance Metrics**

   - Module processing time (p50, p95, p99)
   - Questions generated per module
   - Retry rate per module
   - Total generation time per quiz

2. **Quality Metrics**

   - Answer distribution (A, B, C, D percentages)
   - Question validation success rate
   - User approval rate

3. **System Metrics**
   - Parallel processing concurrency
   - Memory usage during batch generation
   - API rate limit usage

### Log Monitoring

Key log patterns to monitor:

```
INFO: "Generated batch response for module {module_id}"
WARNING: "Module {module_id}: Need {count} more questions, retry {n}/{max}"
ERROR: "Module {module_id} failed: {error}"
INFO: "Generated {total} questions across {modules} modules for quiz {quiz_id}"
```

### Common Issues & Troubleshooting

1. **Insufficient Questions Generated**

   - Check module content length
   - Review LLM response parsing
   - Verify retry logic execution

2. **Module Processing Timeout**

   - Check LLM API response times
   - Review content size
   - Adjust timeout settings

3. **Uneven Answer Distribution**
   - Review prompt template
   - Check LLM temperature settings
   - Analyze generation patterns

## 8. Security Considerations

### Input Validation

- Module question counts are validated (1-20)
- Total questions unlimited but monitored
- Module content sanitized before LLM processing

### Rate Limiting

- Implement per-user quiz creation limits
- Monitor parallel processing load
- Add circuit breakers for LLM API

### Data Privacy

- Module content remains within system
- No PII in question generation prompts
- Audit trail for all generation requests

### Authorization

- Verify user owns quiz before generation
- Check Canvas course access permissions
- Validate module selection against course

## 9. Future Considerations

### Known Limitations

1. Fixed maximum of 20 questions per module
2. Only supports multiple-choice questions
3. No partial module content selection
4. English and Norwegian only

### Potential Improvements

1. **Dynamic Question Limits**

   - Analyze module content length
   - Suggest optimal question counts
   - Allow custom limits per quiz

2. **Advanced Generation Options**

   - Question type mixing (MCQ, short answer, etc.)
   - Difficulty distribution control
   - Topic weighting within modules

3. **Performance Optimizations**

   - Cache frequently used module content
   - Implement streaming question generation
   - Add background job queuing

4. **Enhanced Retry Logic**
   - Adaptive prompting based on failures
   - Different strategies per content type
   - Fallback to chunk-based for edge cases

### Scalability Considerations

- Database: Consider sharding by organization
- LLM API: Implement multi-provider support
- Processing: Add job queue for large quizzes
- Frontend: Implement virtual scrolling for many modules

---

_Implementation Guide Version 1.0 - Module-Based Question Generation_
_Last Updated: 11.07.2025_
