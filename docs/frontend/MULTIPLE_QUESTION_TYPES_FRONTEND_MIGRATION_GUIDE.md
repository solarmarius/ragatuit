# Frontend Migration Guide: Multiple Question Types per Module

**Document Version:** 1.0
**Date:** 2025-07-25
**Target Audience:** Frontend Engineers
**Migration Complexity:** High

## Table of Contents

1. [Overview & Breaking Changes](#1-overview--breaking-changes)
2. [API Schema Changes Analysis](#2-api-schema-changes-analysis)
3. [Question Count Display](#3-question-count-display)
4. [Question Type Handling](#4-question-type-handling)
5. [Quiz Creation Request Structure](#5-quiz-creation-request-structure)
6. [Component-Level Changes](#6-component-level-changes)
7. [API Client Updates](#7-api-client-updates)
8. [Migration Steps](#8-migration-steps)
9. [Testing Strategy](#9-testing-strategy)
10. [Examples & Code Samples](#10-examples--code-samples)

---

## 1. Overview & Breaking Changes

### 1.1 What Changed

The backend has been refactored to support **multiple question types per module** instead of a single question type per entire quiz. This enables more flexible quiz creation where each module can have 1-4 different question type "batches".

### 1.2 Key Breaking Changes

| **Change**             | **Before**                                 | **After**                                        |
| ---------------------- | ------------------------------------------ | ------------------------------------------------ |
| **Quiz Question Type** | Single `question_type` field per quiz      | Multiple `question_type` values per module batch |
| **Module Selection**   | `ModuleSelection { name, question_count }` | `ModuleSelection { name, question_batches[] }`   |
| **Question Count**     | Single `question_count` per module         | Multiple counts per batch, aggregated total      |
| **Batch Structure**    | Not applicable                             | `QuestionBatch { question_type, count }` array   |

### 1.3 Business Impact

- **Enhanced Flexibility**: Users can now create mixed question types per module (e.g., 10 MCQ + 5 Fill-in-blank for Module 1)
- **Better Assessment Quality**: Diverse question types provide comprehensive evaluation
- **Improved User Experience**: More granular control over quiz composition

### 1.4 Backward Compatibility

⚠️ **NO BACKWARD COMPATIBILITY**: This is a breaking change requiring full frontend migration. The API endpoints expect the new schema format immediately.

---

## 2. API Schema Changes Analysis

### 2.1 Current Frontend Types (OUTDATED)

```typescript
// CURRENT - Will break after backend update
export type ModuleSelection = {
  name: string;
  question_count: number; // ❌ Removed
};

export type QuizCreate = {
  canvas_course_id: number;
  canvas_course_name: string;
  selected_modules: {
    [key: string]: ModuleSelection;
  };
  title: string;
  llm_model?: string;
  llm_temperature?: number;
  language?: QuizLanguage;
  question_type?: QuestionType; // ❌ Removed
};

export type Quiz = {
  id?: string;
  // ... other fields
  question_count?: number; // ❌ Replaced with calculated total
  question_type?: QuestionType; // ❌ Removed
  // ... other fields
};
```

### 2.2 Required New Types

```typescript
// NEW - Required for backend compatibility
export type QuestionBatch = {
  question_type: QuestionType;
  count: number; // 1-20 questions per batch
};

export type ModuleSelection = {
  name: string;
  question_batches: QuestionBatch[]; // 1-4 batches per module
};

export type QuizCreate = {
  canvas_course_id: number;
  canvas_course_name: string;
  selected_modules: {
    [key: string]: ModuleSelection;
  };
  title: string;
  llm_model?: string;
  llm_temperature?: number;
  language?: QuizLanguage;
  // question_type removed - now per batch
};

export type Quiz = {
  id?: string;
  // ... other fields
  question_count?: number; // ✅ Total across all batches (read-only)
  selected_modules?: {
    [key: string]: {
      name: string;
      question_batches: Array<{
        question_type: string;
        count: number;
      }>;
    };
  };
  // question_type removed
  // ... other fields
};
```

### 2.3 Schema Validation Rules

The new schema enforces these validation rules:

- **Per Module**: 1-4 question batches maximum
- **Per Batch**: 1-20 questions maximum
- **No Duplicates**: Cannot have same question type twice in one module
- **Required Fields**: Each batch must have `question_type` and `count`

---

## 3. Question Count Display

### 3.1 How Question Count is Calculated

**Before**: Direct `question_count` field from API response

```typescript
// OLD approach
const totalQuestions = quiz.question_count;
```

**After**: Use the `question_count` field directly from the API response.

```typescript
// NEW approach
const totalQuestions = quiz.question_count;
```

### 3.2 Badge Display Components

These components likely need updates to use the new calculation:

```typescript
// Components that display question counts
-QuizBadges.tsx -
  QuizListCard.tsx -
  QuizGenerationCard.tsx -
  QuizTable.tsx / QuizTableRow.tsx;

// Example update in QuizBadges.tsx
const QuizBadges = ({ quiz }: { quiz: Quiz }) => {
  // OLD: const questionCount = quiz.question_count
  const questionCount = quiz.question_count || 0;

  return <Badge variant="outline">{questionCount} Questions</Badge>;
};
```

### 3.3 Per-Module Question Count

You may also want to show question counts per module:

```typescript
export const calculateModuleQuestions = (module: ModuleData): number => {
  if (!module.question_batches) return 0;

  return module.question_batches.reduce((sum, batch) => sum + batch.count, 0);
};

// Usage example
const moduleCount = calculateModuleQuestions(quiz.selected_modules["module_1"]);
```

---

## 4. Question Type Handling

### 4.1 Should You Remove All Question Type Displays?

**No** - Question types are still relevant, but they're now displayed differently:

- **Remove**: Single quiz-level question type display
- **Keep**: Question type displays, but show them per batch/module
- **Add**: Multi-question-type indicators

### 4.2 Displaying Multiple Question Types

**Pattern 1: Show All Types for a Quiz**

```typescript
export const getQuizQuestionTypes = (quiz: Quiz): QuestionType[] => {
  const types = new Set<QuestionType>();

  if (quiz.selected_modules) {
    Object.values(quiz.selected_modules).forEach((module) => {
      module.question_batches?.forEach((batch) => {
        types.add(batch.question_type);
      });
    });
  }

  return Array.from(types);
};

// Usage in component
const QuizTypesBadge = ({ quiz }: { quiz: Quiz }) => {
  const types = getQuizQuestionTypes(quiz);

  return (
    <div className="flex gap-1">
      {types.map((type) => (
        <Badge key={type} variant="secondary">
          {formatQuestionType(type)}
        </Badge>
      ))}
    </div>
  );
};
```

**Pattern 2: Show Types per Module**

```typescript
const ModuleQuestionTypes = ({ module }: { module: ModuleData }) => {
  return (
    <div className="space-y-1">
      {module.question_batches?.map((batch, index) => (
        <div key={index} className="flex justify-between text-sm">
          <span>{formatQuestionType(batch.question_type)}</span>
          <span>{batch.count} questions</span>
        </div>
      ))}
    </div>
  );
};
```

**Pattern 3: Compact Multi-Type Display**

```typescript
const QuizTypesSummary = ({ quiz }: { quiz: Quiz }) => {
  const typeCounts = new Map<QuestionType, number>();

  // Aggregate counts by type across all modules
  if (quiz.selected_modules) {
    Object.values(quiz.selected_modules).forEach((module) => {
      module.question_batches?.forEach((batch) => {
        const current = typeCounts.get(batch.question_type) || 0;
        typeCounts.set(batch.question_type, current + batch.count);
      });
    });
  }

  return (
    <div className="text-sm text-gray-600">
      {Array.from(typeCounts.entries())
        .map(([type, count]) => (
          <span key={type}>
            {count} {formatQuestionType(type)}
          </span>
        ))
        .join(" • ")}
    </div>
  );
};
```

---

## 5. Quiz Creation Request Structure

### 5.1 Old Request Format (BROKEN)

```typescript
// ❌ This will be rejected by the new backend
const oldQuizRequest = {
  canvas_course_id: 12345,
  canvas_course_name: "Biology 101",
  title: "Chapter 3 Quiz",
  selected_modules: {
    module_001: {
      name: "Cell Structure",
      question_count: 15, // ❌ Invalid
    },
    module_002: {
      name: "Photosynthesis",
      question_count: 10, // ❌ Invalid
    },
  },
  question_type: "multiple_choice", // ❌ Invalid
  language: "en",
};
```

### 5.2 New Request Format (REQUIRED)

```typescript
// ✅ This is the required format
const newQuizRequest = {
  canvas_course_id: 12345,
  canvas_course_name: "Biology 101",
  title: "Chapter 3 Quiz",
  selected_modules: {
    module_001: {
      name: "Cell Structure",
      question_batches: [
        { question_type: "multiple_choice", count: 10 },
        { question_type: "fill_in_blank", count: 5 },
      ],
    },
    module_002: {
      name: "Photosynthesis",
      question_batches: [
        { question_type: "multiple_choice", count: 8 },
        { question_type: "matching", count: 2 },
      ],
    },
  },
  // question_type removed
  language: "en",
};
```

### 5.3 Request Builder Helper

Create a helper function to build requests safely:

```typescript
export const buildQuizCreateRequest = (
  courseId: number,
  courseName: string,
  title: string,
  moduleSelections: Record<string, ModuleSelection>,
  options: {
    language?: QuizLanguage;
    llmModel?: string;
    llmTemperature?: number;
  } = {}
): QuizCreate => {
  return {
    canvas_course_id: courseId,
    canvas_course_name: courseName,
    title,
    selected_modules: moduleSelections,
    language: options.language || "en",
    llm_model: options.llmModel || "o3",
    llm_temperature: options.llmTemperature || 1.0,
  };
};

// Usage
const request = buildQuizCreateRequest(12345, "Biology 101", "Quiz Title", {
  mod1: {
    name: "Module 1",
    question_batches: [{ question_type: "multiple_choice", count: 10 }],
  },
});
```

---

## 6. Component-Level Changes

### 6.1 Quiz Creation Components

**Priority 1: ModuleQuestionSelectionStep.tsx**

This component likely handles the UI for selecting question types and counts per module. Major changes needed:

```typescript
// OLD approach (single type/count per module)
interface ModuleQuestionSelectionProps {
  modules: CanvasModule[];
  questionType: QuestionType; // ❌ Remove
  onSelectionChange: (
    selections: Record<
      string,
      {
        name: string;
        question_count: number; // ❌ Change to question_batches
      }
    >
  ) => void;
}

// NEW approach (multiple batches per module)
interface ModuleQuestionSelectionProps {
  modules: CanvasModule[];
  onSelectionChange: (selections: Record<string, ModuleSelection>) => void;
}

// Component needs to support:
// - Adding/removing question batches per module
// - Selecting question type per batch
// - Setting count (1-20) per batch
// - Validation (max 4 batches, no duplicates)
```

**Priority 2: QuizSettingsStep.tsx**

Remove global question type selection:

```typescript
// OLD - Remove question type selector from quiz settings
<FormField>
  <FormLabel>Question Type</FormLabel>
  <Select>
    {" "}
    {/* ❌ Remove this */}
    <option value="multiple_choice">Multiple Choice</option>
    <option value="fill_in_blank">Fill in Blank</option>
  </Select>
</FormField>

// NEW - Question types are selected per module/batch
// Keep other settings (language, model, temperature)
```

### 6.2 Quiz Display Components

**QuizListCard.tsx**

```typescript
// Update to show multiple question types
const QuizListCard = ({ quiz }: { quiz: Quiz }) => {
  const totalQuestions = quiz.question_count || 0;
  const questionTypes = getQuizQuestionTypes(quiz);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{quiz.title}</CardTitle>
        <Badge>{totalQuestions} Questions</Badge>
      </CardHeader>
      <CardBody>
        {/* Show multiple types instead of single type */}
        <QuizTypesSummary quiz={quiz} />
      </CardBody>
    </Card>
  );
};
```

**QuizTable.tsx / QuizTableRow.tsx**

```typescript
// Update table columns
const columns = [
  { header: "Title", accessorKey: "title" },
  {
    header: "Questions",
    accessorKey: "question_count",
  },
  {
    header: "Types",
    cell: ({ row }) => <QuizTypesBadge quiz={row.original} />,
  },
  // ... other columns
];
```

### 6.3 Question Review Components

**QuestionReview.tsx** - May need updates if it filters by question type:

```typescript
// If component has question type filtering
const QuestionReview = ({ quiz }: { quiz: Quiz }) => {
  const [selectedType, setSelectedType] = useState<QuestionType | "all">("all");
  const availableTypes = getQuizQuestionTypes(quiz);

  return (
    <div>
      {/* Type filter dropdown */}
      <Select value={selectedType} onValueChange={setSelectedType}>
        <option value="all">All Types</option>
        {availableTypes.map((type) => (
          <option key={type} value={type}>
            {formatQuestionType(type)}
          </option>
        ))}
      </Select>

      {/* Question list with type filtering */}
      <QuestionList
        questions={questions.filter(
          (q) => selectedType === "all" || q.question_type === selectedType
        )}
      />
    </div>
  );
};
```

---

## 7. API Client Updates

### 7.1 Regenerate OpenAPI Client

The frontend API client is auto-generated from the backend OpenAPI schema. After backend changes, you must regenerate it:

```bash
# From frontend directory
cd frontend

# Regenerate API client from updated backend
npm run generate-client

# This will update:
# - src/client/types.gen.ts
# - src/client/sdk.gen.ts
# - src/client/schemas.gen.ts
```

### 7.2 Type Safety Considerations

After regeneration, TypeScript will show errors in existing code. This is expected and helps identify all places that need updates.

**Common Type Errors After Migration:**

```typescript
// Error: Property 'question_type' does not exist on type 'QuizCreate'
const quiz: QuizCreate = {
  // ...
  question_type: "multiple_choice", // ❌ Remove
};

// Error: Property 'question_count' does not exist on type 'ModuleSelection'
const module: ModuleSelection = {
  name: "Module 1",
  question_count: 10, // ❌ Replace with question_batches
};
```

### 7.3 Error Handling for New Validation

The backend now validates batch limits. Update error handling:

```typescript
// New validation errors to handle
const handleQuizCreation = async (data: QuizCreate) => {
  try {
    await api.quiz.quizCreateNewQuiz({ requestBody: data });
  } catch (error) {
    if (error.status === 422) {
      // Validation errors
      const details = error.body?.detail || [];

      // Handle specific validation messages:
      // - "Module {id} cannot have more than 4 question batches"
      // - "Module {id} has duplicate question types"
      // - "Module {id} batch {i} count must be between 1 and 20"

      const batchErrors = details.filter(
        (d) =>
          d.msg.includes("question batches") ||
          d.msg.includes("duplicate question types")
      );

      if (batchErrors.length > 0) {
        // Show batch-specific error messages
        setBatchValidationErrors(batchErrors);
        return;
      }
    }

    // Handle other errors...
  }
};
```

---

## 8. Migration Steps

### 8.1 Phase 1: Backend Integration (Priority: Critical)

**Step 1**: Update API Client

```bash
cd frontend
npm run generate-client
```

**Step 2**: Fix Type Definitions

- Create `QuestionBatch` type
- Update `ModuleSelection` interface
- Remove `question_type` from `QuizCreate`
- Add utility functions for question count calculation

**Step 3**: Update Core Quiz Creation

- Fix `QuizSettingsStep.tsx` (remove global question type)
- Update `ModuleQuestionSelectionStep.tsx` (add batch selection UI)
- Update request building logic

### 8.2 Phase 2: Display Components (Priority: High)

**Step 4**: Update Question Count Display

- Replace direct `quiz.question_count` usage
- Add `calculateTotalQuestions()` helper
- Update all badge/counter components

**Step 5**: Update Question Type Display

- Replace single type displays with multi-type displays
- Add question type aggregation utilities
- Update quiz cards, tables, and detail views

### 8.3 Phase 3: Advanced Features (Priority: Medium)

**Step 6**: Enhanced UX Features

- Add batch management UI (add/remove/reorder batches)
- Implement question type suggestions
- Add validation feedback for batch limits

**Step 7**: Question Review Updates

- Add filtering by question type
- Show batch-level question organization
- Update question editing workflows

### 8.4 Phase 4: Testing & Polish (Priority: Low)

**Step 8**: Comprehensive Testing

- Test all quiz creation flows
- Verify question count calculations
- Test error handling for new validation rules

**Step 9**: Documentation & Training

- Update component documentation
- Add Storybook stories for new batch components
- Create user-facing help content

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Test Question Type Aggregation**

```typescript
describe("getQuizQuestionTypes", () => {
  it("should return unique question types", () => {
    const quiz: Quiz = {
      selected_modules: {
        mod1: {
          name: "Module 1",
          question_batches: [
            { question_type: "multiple_choice", count: 10 },
            { question_type: "fill_in_blank", count: 5 },
          ],
        },
        mod2: {
          name: "Module 2",
          question_batches: [
            { question_type: "multiple_choice", count: 8 }, // Duplicate type
            { question_type: "matching", count: 3 },
          ],
        },
      },
    };

    const types = getQuizQuestionTypes(quiz);
    expect(types).toHaveLength(3);
    expect(types).toContain("multiple_choice");
    expect(types).toContain("fill_in_blank");
    expect(types).toContain("matching");
  });
});
```

### 9.2 Integration Tests

**Test Quiz Creation Flow**

```typescript
// Test complete creation flow with new schema
describe("Quiz Creation Integration", () => {
  it("should create quiz with multiple question types", async () => {
    // Setup
    render(<QuizCreationFlow />);

    // Navigate through steps
    await fillCourseSelection();
    await fillModuleSelection();

    // Configure question batches
    await user.click(screen.getByText("Add Question Batch"));
    await user.selectOptions(
      screen.getByLabelText("Question Type"),
      "multiple_choice"
    );
    await user.type(screen.getByLabelText("Question Count"), "10");

    await user.click(screen.getByText("Add Question Batch"));
    await user.selectOptions(
      screen.getByLabelText("Question Type"),
      "fill_in_blank"
    );
    await user.type(screen.getByLabelText("Question Count"), "5");

    // Submit
    await user.click(screen.getByText("Create Quiz"));

    // Verify API call
    expect(mockApi.quiz.quizCreateNewQuiz).toHaveBeenCalledWith({
      requestBody: expect.objectContaining({
        selected_modules: expect.objectContaining({
          mod1: {
            name: "Module 1",
            question_batches: [
              { question_type: "multiple_choice", count: 10 },
              { question_type: "fill_in_blank", count: 5 },
            ],
          },
        }),
      }),
    });
  });
});
```

### 9.3 E2E Tests

**Test Complete User Journey**

```typescript
// playwright/e2e/quiz-creation.spec.ts
test("user can create quiz with multiple question types per module", async ({
  page,
}) => {
  await page.goto("/create-quiz");

  // Course selection
  await page.selectOption('[data-testid="course-select"]', "12345");
  await page.click('[data-testid="next-step"]');

  // Module selection
  await page.check('[data-testid="module-mod1"]');
  await page.click('[data-testid="next-step"]');

  // Question batch configuration
  await page.click('[data-testid="add-batch-mod1"]');
  await page.selectOption('[data-testid="batch-type-0"]', "multiple_choice");
  await page.fill('[data-testid="batch-count-0"]', "10");

  await page.click('[data-testid="add-batch-mod1"]');
  await page.selectOption('[data-testid="batch-type-1"]', "fill_in_blank");
  await page.fill('[data-testid="batch-count-1"]', "5");

  await page.click('[data-testid="next-step"]');

  // Quiz settings
  await page.fill('[data-testid="quiz-title"]', "Test Quiz");
  await page.click('[data-testid="create-quiz"]');

  // Verify success
  await expect(page.locator('[data-testid="quiz-created"]')).toBeVisible();
  await expect(page.locator('[data-testid="total-questions"]')).toHaveText(
    "15"
  );
});
```

---

## 10. Examples & Code Samples

### 10.1 Complete ModuleQuestionSelectionStep Example

```typescript
interface QuestionBatch {
  question_type: QuestionType;
  count: number;
}

interface ModuleSelection {
  name: string;
  question_batches: QuestionBatch[];
}

interface ModuleQuestionSelectionStepProps {
  modules: CanvasModule[];
  initialSelections?: Record<string, ModuleSelection>;
  onSelectionChange: (selections: Record<string, ModuleSelection>) => void;
  onNext: () => void;
  onBack: () => void;
}

const ModuleQuestionSelectionStep: React.FC<
  ModuleQuestionSelectionStepProps
> = ({
  modules,
  initialSelections = {},
  onSelectionChange,
  onNext,
  onBack,
}) => {
  const [selections, setSelections] =
    useState<Record<string, ModuleSelection>>(initialSelections);
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string[]>
  >({});

  const selectedModules = modules.filter((m) => selections[m.id]);

  const addBatch = (moduleId: string) => {
    const module = selections[moduleId];
    if (!module) return;

    if (module.question_batches.length >= 4) {
      setValidationErrors((prev) => ({
        ...prev,
        [moduleId]: ["Maximum 4 question batches per module"],
      }));
      return;
    }

    const newBatch: QuestionBatch = {
      question_type: "multiple_choice",
      count: 5,
    };

    const updatedSelections = {
      ...selections,
      [moduleId]: {
        ...module,
        question_batches: [...module.question_batches, newBatch],
      },
    };

    setSelections(updatedSelections);
    onSelectionChange(updatedSelections);

    // Clear validation errors
    setValidationErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors[moduleId];
      return newErrors;
    });
  };

  const removeBatch = (moduleId: string, batchIndex: number) => {
    const module = selections[moduleId];
    if (!module) return;

    const updatedBatches = module.question_batches.filter(
      (_, index) => index !== batchIndex
    );

    if (updatedBatches.length === 0) {
      // Remove module entirely if no batches
      const updatedSelections = { ...selections };
      delete updatedSelections[moduleId];
      setSelections(updatedSelections);
      onSelectionChange(updatedSelections);
    } else {
      const updatedSelections = {
        ...selections,
        [moduleId]: {
          ...module,
          question_batches: updatedBatches,
        },
      };
      setSelections(updatedSelections);
      onSelectionChange(updatedSelections);
    }
  };

  const updateBatch = (
    moduleId: string,
    batchIndex: number,
    updates: Partial<QuestionBatch>
  ) => {
    const module = selections[moduleId];
    if (!module) return;

    const updatedBatches = module.question_batches.map((batch, index) =>
      index === batchIndex ? { ...batch, ...updates } : batch
    );

    // Validate no duplicate question types
    const types = updatedBatches.map((b) => b.question_type);
    const hasDuplicates = types.length !== new Set(types).size;

    if (hasDuplicates) {
      setValidationErrors((prev) => ({
        ...prev,
        [moduleId]: ["Cannot have duplicate question types in the same module"],
      }));
      return;
    }

    const updatedSelections = {
      ...selections,
      [moduleId]: {
        ...module,
        question_batches: updatedBatches,
      },
    };

    setSelections(updatedSelections);
    onSelectionChange(updatedSelections);

    // Clear validation errors
    setValidationErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors[moduleId];
      return newErrors;
    });
  };

  const calculateModuleTotal = (module: ModuleSelection): number => {
    return module.question_batches.reduce((sum, batch) => sum + batch.count, 0);
  };

  const calculateGrandTotal = (): number => {
    return Object.values(selections).reduce(
      (sum, module) => sum + calculateModuleTotal(module),
      0
    );
  };

  const isValid = (): boolean => {
    return (
      Object.keys(validationErrors).length === 0 && selectedModules.length > 0
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configure Question Types"
        description="Set up different question types and counts for each module"
      />

      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Quiz Summary</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="font-medium">Total Questions:</span>{" "}
              {calculateGrandTotal()}
            </div>
            <div>
              <span className="font-medium">Modules Selected:</span>{" "}
              {selectedModules.length}
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Module Configuration */}
      <div className="space-y-4">
        {selectedModules.map((module) => {
          const moduleSelection = selections[module.id];
          const moduleErrors = validationErrors[module.id] || [];

          return (
            <Card
              key={module.id}
              className={moduleErrors.length > 0 ? "border-red-200" : ""}
            >
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle className="text-lg">{module.name}</CardTitle>
                    <p className="text-sm text-gray-600">
                      {calculateModuleTotal(moduleSelection)} questions total
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => addBatch(module.id)}
                    disabled={moduleSelection.question_batches.length >= 4}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Add Batch
                  </Button>
                </div>
              </CardHeader>

              <CardBody className="space-y-3">
                {/* Validation Errors */}
                {moduleErrors.length > 0 && (
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    {moduleErrors.map((error, index) => (
                      <p key={index} className="text-sm text-red-600">
                        {error}
                      </p>
                    ))}
                  </div>
                )}

                {/* Question Batches */}
                {moduleSelection.question_batches.map((batch, batchIndex) => (
                  <div
                    key={batchIndex}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded"
                  >
                    <div className="flex-1">
                      <label className="block text-sm font-medium mb-1">
                        Question Type
                      </label>
                      <Select
                        value={batch.question_type}
                        onValueChange={(value: QuestionType) =>
                          updateBatch(module.id, batchIndex, {
                            question_type: value,
                          })
                        }
                      >
                        <option value="multiple_choice">Multiple Choice</option>
                        <option value="fill_in_blank">Fill in Blank</option>
                        <option value="matching">Matching</option>
                        <option value="categorization">Categorization</option>
                      </Select>
                    </div>

                    <div className="w-24">
                      <label className="block text-sm font-medium mb-1">
                        Count
                      </label>
                      <Input
                        type="number"
                        min="1"
                        max="20"
                        value={batch.count}
                        onChange={(e) =>
                          updateBatch(module.id, batchIndex, {
                            count: parseInt(e.target.value) || 1,
                          })
                        }
                      />
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeBatch(module.id, batchIndex)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}

                {moduleSelection.question_batches.length === 0 && (
                  <p className="text-gray-500 text-center py-4">
                    No question batches configured. Click "Add Batch" to get
                    started.
                  </p>
                )}
              </CardBody>
            </Card>
          );
        })}
      </div>

      {selectedModules.length === 0 && (
        <Card>
          <CardBody className="text-center py-8">
            <p className="text-gray-500">
              No modules selected. Go back to select modules first.
            </p>
          </CardBody>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext} disabled={!isValid()}>
          Next: Quiz Settings
        </Button>
      </div>
    </div>
  );
};

export default ModuleQuestionSelectionStep;
```

### 10.2 Question Count Utilities

```typescript
// src/lib/utils/quiz.ts

export interface QuestionBatch {
  question_type: string;
  count: number;
}

export interface ModuleData {
  name: string;
  question_batches?: QuestionBatch[];
}

export interface Quiz {
  question_count?: number;
  selected_modules?: Record<string, ModuleData>;
  // ... other fields
}

/**
 * Get all unique question types used in a quiz
 */
export const getQuizQuestionTypes = (quiz: Quiz): string[] => {
  if (!quiz.selected_modules) return [];

  const types = new Set<string>();

  Object.values(quiz.selected_modules).forEach((module) => {
    module.question_batches?.forEach((batch) => {
      if (batch.question_type) {
        types.add(batch.question_type);
      }
    });
  });

  return Array.from(types);
};

/**
 * Get question type counts aggregated across all modules
 */
export const getQuizQuestionTypeCounts = (
  quiz: Quiz
): Record<string, number> => {
  if (!quiz.selected_modules) return {};

  const counts: Record<string, number> = {};

  Object.values(quiz.selected_modules).forEach((module) => {
    module.question_batches?.forEach((batch) => {
      if (batch.question_type) {
        counts[batch.question_type] =
          (counts[batch.question_type] || 0) + batch.count;
      }
    });
  });

  return counts;
};

/**
 * Format question type for display
 */
export const formatQuestionType = (type: string): string => {
  const typeLabels: Record<string, string> = {
    multiple_choice: "Multiple Choice",
    fill_in_blank: "Fill in Blank",
    matching: "Matching",
    categorization: "Categorization",
  };

  return typeLabels[type] || type;
};

/**
 * Validate module question batches
 */
export const validateModuleBatches = (batches: QuestionBatch[]): string[] => {
  const errors: string[] = [];

  // Check batch count limit
  if (batches.length > 4) {
    errors.push("Maximum 4 question batches per module");
  }

  // Check for duplicate question types
  const types = batches.map((b) => b.question_type);
  const uniqueTypes = new Set(types);
  if (types.length !== uniqueTypes.size) {
    errors.push("Cannot have duplicate question types in the same module");
  }

  // Check individual batch counts
  batches.forEach((batch, index) => {
    if (batch.count < 1 || batch.count > 20) {
      errors.push(
        `Batch ${index + 1}: Question count must be between 1 and 20`
      );
    }
  });

  return errors;
};
```

### 10.3 Request/Response Examples

**Example Quiz Creation Request:**

```json
{
  "canvas_course_id": 12345,
  "canvas_course_name": "Introduction to Biology",
  "title": "Midterm Quiz - Chapters 3-5",
  "selected_modules": {
    "module_ch3": {
      "name": "Chapter 3: Cell Structure",
      "question_batches": [
        {
          "question_type": "multiple_choice",
          "count": 15
        },
        {
          "question_type": "fill_in_blank",
          "count": 5
        }
      ]
    },
    "module_ch4": {
      "name": "Chapter 4: Cell Division",
      "question_batches": [
        {
          "question_type": "multiple_choice",
          "count": 10
        },
        {
          "question_type": "matching",
          "count": 3
        },
        {
          "question_type": "categorization",
          "count": 2
        }
      ]
    },
    "module_ch5": {
      "name": "Chapter 5: Photosynthesis",
      "question_batches": [
        {
          "question_type": "multiple_choice",
          "count": 20
        }
      ]
    }
  },
  "language": "en",
  "llm_model": "o3",
  "llm_temperature": 1.0
}
```

**Example Quiz Response:**

```json
{
  "id": "quiz-uuid-123",
  "owner_id": "user-uuid-456",
  "canvas_course_id": 12345,
  "canvas_course_name": "Introduction to Biology",
  "title": "Midterm Quiz - Chapters 3-5",
  "question_count": 55,
  "selected_modules": {
    "module_ch3": {
      "name": "Chapter 3: Cell Structure",
      "question_batches": [
        {
          "question_type": "multiple_choice",
          "count": 15
        },
        {
          "question_type": "fill_in_blank",
          "count": 5
        }
      ]
    },
    "module_ch4": {
      "name": "Chapter 4: Cell Division",
      "question_batches": [
        {
          "question_type": "multiple_choice",
          "count": 10
        },
        {
          "question_type": "matching",
          "count": 3
        },
        {
          "question_type": "categorization",
          "count": 2
        }
      ]
    },
    "module_ch5": {
      "name": "Chapter 5: Photosynthesis",
      "question_batches": [
        {
          "question_type": "multiple_choice",
          "count": 20
        }
      ]
    }
  },
  "status": "created",
  "language": "en",
  "llm_model": "o3",
  "llm_temperature": 1.0,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

## Summary

This migration requires significant changes to the frontend but provides much more flexibility for quiz creation. The key is to:

1. **Start with API client regeneration** to get the new types
2. **Update core quiz creation logic first** to restore basic functionality
3. **Gradually enhance the UI** to take advantage of the new batch capabilities
4. **Test thoroughly** to ensure all edge cases are handled

The new system allows for much richer quiz configurations and better user experiences, but requires careful attention to validation and user interface design to handle the increased complexity effectively.
