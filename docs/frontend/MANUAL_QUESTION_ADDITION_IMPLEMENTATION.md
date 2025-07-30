# Manual Question Addition Feature - Implementation Documentation

**Date:** July 30, 2025
**Version:** 1.0
**Author:** Development Team
**Target Audience:** Developers implementing this feature from scratch

---

## 1. Feature Overview

### Description
The Manual Question Addition feature allows instructors to manually create quiz questions outside of the AI-powered question generation workflow. This feature provides a user-friendly interface for creating questions in any of the five supported question types: Multiple Choice, True/False, Fill in the Blank, Matching, and Categorization.

### Business Value
- **Flexibility**: Instructors can add specific questions they have in mind that complement AI-generated content
- **Quality Control**: Teachers can ensure critical concepts are covered with questions they've crafted themselves
- **Workflow Integration**: Manually created questions seamlessly integrate with the existing review and approval process
- **Content Completeness**: Fills gaps in AI-generated question sets with instructor expertise

### User Benefits
- Familiar, intuitive question creation interface
- Real-time validation and error feedback
- Seamless integration with existing quiz workflow
- Support for all question types available in the system

### Context
This feature is part of the Rag@UiT Canvas LMS quiz generator application. It extends the existing question generation and review system by allowing manual question creation during the review phase of quiz development.

---

## 2. Technical Architecture

### High-Level Architecture
The feature follows a layered architecture pattern:

```
┌─────────────────────────────────────────────────────────┐
│                    UI Layer                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────┐   │
│  │ Questions Route │ │ Question Dialog │ │ Type     │   │
│  │ (Add Button)    │ │ (Full Screen)   │ │ Selector │   │
│  └─────────────────┘ └─────────────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                  Component Layer                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────┐   │
│  │ Question        │ │ Existing        │ │ Form     │   │
│  │ Creator         │ │ Question        │ │ Validation│   │
│  │ Wrapper         │ │ Editors         │ │ (Zod)    │   │
│  └─────────────────┘ └─────────────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────┐   │
│  │ API Mutations   │ │ Query           │ │ Toast    │   │
│  │ (TanStack)      │ │ Invalidation    │ │ Notifications│
│  └─────────────────┘ └─────────────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   Backend API                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────┐   │
│  │ POST            │ │ Polymorphic     │ │ Database │   │
│  │ /questions/{id} │ │ Validation      │ │ Storage  │   │
│  └─────────────────┘ └─────────────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Integration Points
- **Existing Question System**: Reuses all question editors, validation schemas, and display components
- **API Layer**: Utilizes existing question creation endpoint without backend modifications
- **State Management**: Integrates with TanStack Query for caching and invalidation
- **UI Framework**: Built with Chakra UI v3 components following established patterns

### Data Flow
1. User clicks "Add Question" button (visible only in review states)
2. Dialog opens with question type selection step
3. User selects question type → transitions to creation step
4. User fills out question form with real-time validation
5. On save → API call to create question → success/error handling
6. Success → close dialog, refresh question list, show success toast

---

## 3. Dependencies & Prerequisites

### External Dependencies
All dependencies are already present in the existing codebase:

- **React** ^18.0.0 - Core UI framework
- **@chakra-ui/react** ^3.x - UI component library
- **@tanstack/react-query** ^5.x - Data fetching and caching
- **@tanstack/react-router** ^1.x - Routing solution
- **react-hook-form** ^7.x - Form state management
- **@hookform/resolvers** ^3.x - Form validation integration
- **zod** ^3.x - Schema validation library

### Prerequisites
- Existing Rag@UiT application setup
- Node.js 18+ environment
- TypeScript configuration
- Existing question types and validation schemas
- Backend question creation API endpoint

### Environment Setup
No additional environment setup required. The feature uses existing infrastructure.

---

## 4. Implementation Details

### 4.1 File Structure

#### Files to Create
```
frontend/src/components/Questions/
├── ManualQuestionDialog.tsx       # Main dialog component
├── QuestionTypeSelector.tsx       # Question type selection step
└── ManualQuestionCreator.tsx      # Question creation wrapper
```

#### Files to Modify
```
frontend/src/routes/_layout/quiz.$id.questions.tsx  # Add "Add Question" button
```

#### Purpose of Each File

**ManualQuestionDialog.tsx**
- Main orchestrator component managing the two-step workflow
- Handles dialog state, API calls, and error handling
- Provides full-screen dialog experience

**QuestionTypeSelector.tsx**
- First step of the workflow
- Displays 5 question types as selectable cards
- Handles type selection and navigation to next step

**ManualQuestionCreator.tsx**
- Second step of the workflow
- Wraps existing question editors, hiding tags/difficulty
- Transforms form data for API submission

**quiz.$id.questions.tsx**
- Integration point for the feature
- Adds "Add Question" button with conditional visibility
- Imports and renders the dialog component

### 4.2 Step-by-Step Implementation

#### Step 1: Create QuestionTypeSelector Component

**File:** `frontend/src/components/Questions/QuestionTypeSelector.tsx`

```tsx
import { Box, Button, Card, SimpleGrid, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"

import { QUESTION_TYPES, QUESTION_TYPE_LABELS } from "@/lib/constants"

interface QuestionTypeSelectorProps {
  /** Callback when a question type is selected */
  onSelectType: (questionType: string) => void
  /** Whether the selection process is loading */
  isLoading?: boolean
}

/**
 * Question type selector component that displays all available question types
 * as selectable cards. This is the first step in the manual question creation workflow.
 *
 * @example
 * ```tsx
 * <QuestionTypeSelector
 *   onSelectType={(type) => setSelectedType(type)}
 *   isLoading={false}
 * />
 * ```
 */
export const QuestionTypeSelector = memo(function QuestionTypeSelector({
  onSelectType,
  isLoading = false,
}: QuestionTypeSelectorProps) {
  // Define question types with descriptions for better UX
  const questionTypeOptions = [
    {
      type: QUESTION_TYPES.MULTIPLE_CHOICE,
      label: QUESTION_TYPE_LABELS.multiple_choice,
      description: "Choose the correct answer from 4 options (A, B, C, D)",
      icon: "📝",
    },
    {
      type: QUESTION_TYPES.TRUE_FALSE,
      label: QUESTION_TYPE_LABELS.true_false,
      description: "Simple true or false statements",
      icon: "✓✗",
    },
    {
      type: QUESTION_TYPES.FILL_IN_BLANK,
      label: QUESTION_TYPE_LABELS.fill_in_blank,
      description: "Complete sentences with missing words",
      icon: "📄",
    },
    {
      type: QUESTION_TYPES.MATCHING,
      label: QUESTION_TYPE_LABELS.matching,
      description: "Match questions to their correct answers",
      icon: "🔗",
    },
    {
      type: QUESTION_TYPES.CATEGORIZATION,
      label: QUESTION_TYPE_LABELS.categorization,
      description: "Group items into appropriate categories",
      icon: "📊",
    },
  ]

  return (
    <VStack gap={6} align="stretch">
      <Box>
        <Text fontSize="xl" fontWeight="bold" mb={2}>
          Select Question Type
        </Text>
        <Text color="gray.600">
          Choose the type of question you want to create.
        </Text>
      </Box>

      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
        {questionTypeOptions.map((option) => (
          <Card.Root
            key={option.type}
            variant="outline"
            cursor="pointer"
            transition="all 0.2s"
            _hover={{
              borderColor: "blue.300",
              shadow: "md",
            }}
            onClick={() => onSelectType(option.type)}
          >
            <Card.Body p={4}>
              <VStack gap={3} align="center" textAlign="center">
                <Text fontSize="2xl" role="img" aria-label={option.label}>
                  {option.icon}
                </Text>
                <Text fontWeight="semibold" fontSize="md">
                  {option.label}
                </Text>
                <Text fontSize="sm" color="gray.600" lineHeight="1.4">
                  {option.description}
                </Text>
              </VStack>
            </Card.Body>
          </Card.Root>
        ))}
      </SimpleGrid>

      <Box>
        <Text fontSize="sm" color="gray.500" textAlign="center">
          All question types support real-time validation and will be added to your quiz
          in pending status for review.
        </Text>
      </Box>
    </VStack>
  )
})
```

**Key Implementation Notes:**
- Uses existing constants for question types and labels
- Provides clear descriptions for each question type
- Responsive grid layout for different screen sizes
- Accessible design with proper ARIA labels
- Hover effects for better user interaction

#### Step 2: Create ManualQuestionCreator Component

**File:** `frontend/src/components/Questions/ManualQuestionCreator.tsx`

```tsx
import { memo, useCallback } from "react"

import type { QuestionCreateRequest, QuestionUpdateRequest } from "@/client"
import { QuestionEditor } from "@/components/Questions/editors/QuestionEditor"
import { QUESTION_TYPES } from "@/lib/constants"

interface ManualQuestionCreatorProps {
  /** The selected question type */
  questionType: string
  /** Quiz ID for the question */
  quizId: string
  /** Callback when question is saved */
  onSave: (questionData: QuestionCreateRequest) => void
  /** Callback when creation is canceled */
  onCancel: () => void
  /** Whether the save operation is loading */
  isLoading?: boolean
}

/**
 * Wrapper component that adapts existing question editors for manual question creation.
 * This component hides tags and difficulty fields, setting appropriate defaults,
 * and transforms the form data for API submission.
 *
 * @example
 * ```tsx
 * <ManualQuestionCreator
 *   questionType={QUESTION_TYPES.MULTIPLE_CHOICE}
 *   quizId="quiz-123"
 *   onSave={(data) => createQuestion(data)}
 *   onCancel={() => setStep('type-selection')}
 *   isLoading={mutation.isPending}
 * />
 * ```
 */
export const ManualQuestionCreator = memo(function ManualQuestionCreator({
  questionType,
  quizId,
  onSave,
  onCancel,
  isLoading = false,
}: ManualQuestionCreatorProps) {
  // Transform the update request to a create request
  const handleSave = useCallback(
    (updateData: QuestionUpdateRequest) => {
      if (!updateData.question_data) {
        console.error("No question data provided")
        return
      }

      // Transform to create request format with defaults
      const createData: QuestionCreateRequest = {
        quiz_id: quizId,
        question_type: questionType as any, // Type assertion needed for polymorphic types
        question_data: updateData.question_data,
        difficulty: "MEDIUM", // Default difficulty as specified in requirements
        tags: [], // Empty tags array as specified in requirements
      }

      onSave(createData)
    },
    [questionType, quizId, onSave]
  )

  // Create a mock question response object for the editor
  // This allows us to reuse existing editor components without modification
  const mockQuestion = {
    id: "temp-id", // Temporary ID for editor compatibility
    quiz_id: quizId,
    question_type: questionType,
    question_data: getDefaultQuestionData(questionType),
    difficulty: "MEDIUM",
    tags: [],
    is_approved: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }

  return (
    <QuestionEditor
      question={mockQuestion}
      onSave={handleSave}
      onCancel={onCancel}
      isLoading={isLoading}
    />
  )
})

/**
 * Provides default question data based on question type.
 * This ensures the editor has valid initial state.
 */
function getDefaultQuestionData(questionType: string): Record<string, any> {
  switch (questionType) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return {
        question_text: "",
        option_a: "",
        option_b: "",
        option_c: "",
        option_d: "",
        correct_answer: "A",
        explanation: null,
      }

    case QUESTION_TYPES.TRUE_FALSE:
      return {
        question_text: "",
        correct_answer: true,
        explanation: null,
      }

    case QUESTION_TYPES.FILL_IN_BLANK:
      return {
        question_text: "",
        blanks: [],
        explanation: null,
      }

    case QUESTION_TYPES.MATCHING:
      return {
        question_text: "",
        pairs: [
          { question: "", answer: "" },
          { question: "", answer: "" },
          { question: "", answer: "" },
        ],
        distractors: [],
        explanation: null,
      }

    case QUESTION_TYPES.CATEGORIZATION:
      return {
        question_text: "",
        categories: [
          { id: crypto.randomUUID(), name: "", correct_items: [] },
          { id: crypto.randomUUID(), name: "", correct_items: [] },
        ],
        items: [],
        distractors: [],
        explanation: null,
      }

    default:
      return {
        question_text: "",
        explanation: null,
      }
  }
}
```

**Key Implementation Notes:**
- Wraps existing QuestionEditor without modifying it
- Sets default difficulty to "MEDIUM" and empty tags
- Creates mock question object for editor compatibility
- Provides sensible defaults for each question type
- Transforms update requests to create requests

#### Step 3: Create ManualQuestionDialog Component

**File:** `frontend/src/components/Questions/ManualQuestionDialog.tsx`

```tsx
import { Button, VStack } from "@chakra-ui/react"
import { memo, useState } from "react"

import type { QuestionCreateRequest } from "@/client"
import { QuestionsService } from "@/client"
import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import { useApiMutation } from "@/hooks/common"
import { QUIZ_STATUS } from "@/lib/constants"
import { queryKeys } from "@/lib/queryConfig"
import { ManualQuestionCreator } from "./ManualQuestionCreator"
import { QuestionTypeSelector } from "./QuestionTypeSelector"

type DialogStep = "type-selection" | "question-creation"

interface ManualQuestionDialogProps {
  /** Quiz ID for creating questions */
  quizId: string
  /** Quiz object to check status permissions */
  quiz: { status: string }
  /** Whether the dialog is open */
  isOpen: boolean
  /** Callback when dialog open state changes */
  onOpenChange: (isOpen: boolean) => void
}

/**
 * Main dialog component for manual question creation.
 * Provides a two-step workflow: question type selection followed by question creation.
 *
 * Features:
 * - Full-screen dialog experience
 * - Two-step workflow with navigation
 * - API integration with error handling
 * - Auto-close on successful creation
 * - Status-based access control
 *
 * @example
 * ```tsx
 * <ManualQuestionDialog
 *   quizId="quiz-123"
 *   quiz={quiz}
 *   isOpen={isDialogOpen}
 *   onOpenChange={setIsDialogOpen}
 * />
 * ```
 */
export const ManualQuestionDialog = memo(function ManualQuestionDialog({
  quizId,
  quiz,
  isOpen,
  onOpenChange,
}: ManualQuestionDialogProps) {
  const [currentStep, setCurrentStep] = useState<DialogStep>("type-selection")
  const [selectedQuestionType, setSelectedQuestionType] = useState<string>("")

  // Reset dialog state when it closes
  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setCurrentStep("type-selection")
      setSelectedQuestionType("")
    }
    onOpenChange(open)
  }

  // Create question mutation with proper error handling and query invalidation
  const createQuestionMutation = useApiMutation(
    async (questionData: QuestionCreateRequest) => {
      return await QuestionsService.createQuestion({
        quizId,
        requestBody: questionData,
      })
    },
    {
      successMessage: "Question created successfully",
      invalidateQueries: [
        queryKeys.quizQuestions(quizId),
        queryKeys.quizQuestionStats(quizId),
        queryKeys.quiz(quizId), // Update question count
      ],
      onSuccess: () => {
        // Auto-close dialog on successful creation as specified in requirements
        handleOpenChange(false)
      },
    }
  )

  // Handle question type selection and navigation to next step
  const handleSelectType = (questionType: string) => {
    setSelectedQuestionType(questionType)
    setCurrentStep("question-creation")
  }

  // Handle back navigation to type selection
  const handleBackToTypeSelection = () => {
    setCurrentStep("type-selection")
    setSelectedQuestionType("")
  }

  // Handle question creation
  const handleCreateQuestion = (questionData: QuestionCreateRequest) => {
    createQuestionMutation.mutate(questionData)
  }

  // Check if manual question creation is allowed based on quiz status
  const canCreateQuestions =
    quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
    quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL

  if (!canCreateQuestions) {
    return null // Don't render dialog if not allowed
  }

  return (
    <DialogRoot
      size="full" // Full-screen dialog as specified in requirements
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => handleOpenChange(open)}
    >
      <DialogContent>
        <DialogCloseTrigger />
        <DialogHeader>
          <DialogTitle>
            {currentStep === "type-selection"
              ? "Add Question"
              : `Create ${selectedQuestionType.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())} Question`}
          </DialogTitle>
        </DialogHeader>

        <DialogBody>
          <VStack gap={6} align="stretch" h="full">
            {currentStep === "type-selection" && (
              <QuestionTypeSelector
                onSelectType={handleSelectType}
                isLoading={createQuestionMutation.isPending}
              />
            )}

            {currentStep === "question-creation" && selectedQuestionType && (
              <VStack gap={4} align="stretch" h="full">
                {/* Back button for navigation */}
                <Button
                  variant="ghost"
                  size="sm"
                  alignSelf="flex-start"
                  onClick={handleBackToTypeSelection}
                  disabled={createQuestionMutation.isPending}
                >
                  ← Back to Question Types
                </Button>

                <ManualQuestionCreator
                  questionType={selectedQuestionType}
                  quizId={quizId}
                  onSave={handleCreateQuestion}
                  onCancel={handleBackToTypeSelection}
                  isLoading={createQuestionMutation.isPending}
                />
              </VStack>
            )}
          </VStack>
        </DialogBody>
      </DialogContent>
    </DialogRoot>
  )
})
```

**Key Implementation Notes:**
- Full-screen dialog for optimal editing experience
- Two-step workflow with proper state management
- Status-based access control (only review states)
- Auto-close on successful creation
- Proper error handling and loading states
- Query invalidation for data consistency

#### Step 4: Integrate Button into Questions Route

**File:** `frontend/src/routes/_layout/quiz.$id.questions.tsx`

**Modifications to make:**

1. **Add imports at the top:**
```tsx
// Add this import with existing imports
import { ManualQuestionDialog } from "@/components/Questions/ManualQuestionDialog"
```

2. **Add state management in QuizQuestions component:**
```tsx
function QuizQuestions() {
  const { id } = Route.useParams()

  // Add this state for dialog management
  const [isManualQuestionDialogOpen, setIsManualQuestionDialogOpen] = useState(false)

  // ... existing code ...
```

3. **Add the "Add Question" button to the filter buttons section:**

Replace the existing filter buttons section (around lines 198-215) with:

```tsx
      {/* Filter Toggle Buttons and Add Question Button */}
      {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
        quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL ||
        quiz.status === QUIZ_STATUS.EXPORTING_TO_CANVAS ||
        quiz.status === QUIZ_STATUS.PUBLISHED ||
        (quiz.status === QUIZ_STATUS.FAILED &&
          quiz.failure_reason === FAILURE_REASON.CANVAS_EXPORT_ERROR)) && (
        <HStack gap={3} justify="space-between">
          <HStack gap={3}>
            {/* Add Question Button - Only show in review states */}
            {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
              quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL) && (
              <Button
                variant="solid"
                colorPalette="green"
                size="sm"
                onClick={() => setIsManualQuestionDialogOpen(true)}
              >
                Add Question
              </Button>
            )}

            {/* Existing Filter Buttons */}
            <Button
              variant={filterView === "pending" ? "solid" : "outline"}
              colorPalette="blue"
              size="sm"
              onClick={() => setFilterView("pending")}
            >
              Pending Approval ({pendingCount})
            </Button>
            <Button
              variant={filterView === "all" ? "solid" : "outline"}
              colorPalette="blue"
              size="sm"
              onClick={() => setFilterView("all")}
            >
              All Questions ({totalCount})
            </Button>
          </HStack>
        </HStack>
      )}
```

4. **Add the dialog component before the closing VStack:**

```tsx
      {/* Manual Question Dialog */}
      <ManualQuestionDialog
        quizId={id}
        quiz={quiz}
        isOpen={isManualQuestionDialogOpen}
        onOpenChange={setIsManualQuestionDialogOpen}
      />

    </VStack>
  )
}
```

5. **Add missing import:**
```tsx
// Add this import with existing imports
import { useState } from "react"
```

**Complete Modified Section:**

Here's the complete modified QuizQuestions component with the integration:

```tsx
function QuizQuestions() {
  const { id } = Route.useParams()

  // Add dialog state management
  const [isManualQuestionDialogOpen, setIsManualQuestionDialogOpen] = useState(false)

  // Custom polling for questions route - stops polling during review state
  const questionsPolling = useConditionalPolling<Quiz>((data) => {
    if (!data?.status) return true // Poll if no status yet

    // Stop polling for stable states where user is actively working or quiz is complete
    const stableReviewStates = [
      QUIZ_STATUS.READY_FOR_REVIEW, // User is actively reviewing questions
      QUIZ_STATUS.PUBLISHED,        // Quiz completed and exported
      QUIZ_STATUS.FAILED           // Terminal error state
    ] as const

    return !stableReviewStates.includes(data.status as typeof stableReviewStates[number])
  }, 5000) // Continue polling every 5 seconds for active processing states

  const { data: quiz, isLoading } = useQuery({
    queryKey: queryKeys.quiz(id),
    queryFn: async () => {
      const response = await QuizService.getQuiz({ quizId: id })
      return response
    },
    ...quizQueryConfig,
    refetchInterval: questionsPolling, // Use questions-specific polling logic
  })

  // Only show skeleton when loading and no cached data exists
  if (isLoading && !quiz) {
    return <QuizQuestionsSkeleton />
  }

  if (!quiz) {
    return <QuizQuestionsSkeleton />
  }

  return (
    <VStack gap={6} align="stretch">
      {/* Question Statistics */}
      {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
        quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL ||
        quiz.status === QUIZ_STATUS.EXPORTING_TO_CANVAS ||
        quiz.status === QUIZ_STATUS.PUBLISHED ||
        (quiz.status === QUIZ_STATUS.FAILED &&
          quiz.failure_reason === FAILURE_REASON.CANVAS_EXPORT_ERROR)) && (
        <QuestionStats quiz={quiz} />
      )}

      {/* Canvas Export Error Banner */}
      {quiz.status === QUIZ_STATUS.FAILED &&
        quiz.failure_reason === FAILURE_REASON.CANVAS_EXPORT_ERROR &&
        renderErrorForFailureReason(quiz.failure_reason)}

      {/* Filter Toggle Buttons and Add Question Button */}
      {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
        quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL ||
        quiz.status === QUIZ_STATUS.EXPORTING_TO_CANVAS ||
        quiz.status === QUIZ_STATUS.PUBLISHED ||
        (quiz.status === QUIZ_STATUS.FAILED &&
          quiz.failure_reason === FAILURE_REASON.CANVAS_EXPORT_ERROR)) && (
        <HStack gap={3} justify="space-between">
          <HStack gap={3}>
            {/* Add Question Button - Only show in review states */}
            {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
              quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL) && (
              <Button
                variant="solid"
                colorPalette="green"
                size="sm"
                onClick={() => setIsManualQuestionDialogOpen(true)}
              >
                Add Question
              </Button>
            )}

            {/* Existing Filter Buttons */}
            <Button
              variant={filterView === "pending" ? "solid" : "outline"}
              colorPalette="blue"
              size="sm"
              onClick={() => setFilterView("pending")}
            >
              Pending Approval ({pendingCount})
            </Button>
            <Button
              variant={filterView === "all" ? "solid" : "outline"}
              colorPalette="blue"
              size="sm"
              onClick={() => setFilterView("all")}
            >
              All Questions ({totalCount})
            </Button>
          </HStack>
        </HStack>
      )}

      {/* Question Review */}
      {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
        quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL ||
        quiz.status === QUIZ_STATUS.EXPORTING_TO_CANVAS ||
        quiz.status === QUIZ_STATUS.PUBLISHED ||
        (quiz.status === QUIZ_STATUS.FAILED &&
          quiz.failure_reason === FAILURE_REASON.CANVAS_EXPORT_ERROR)) && (
        <QuestionReview quizId={id} />
      )}

      {/* Error Display for Failed Status (except Canvas Export Error which is handled above) */}
      {quiz.status === QUIZ_STATUS.FAILED &&
        quiz.failure_reason !== FAILURE_REASON.CANVAS_EXPORT_ERROR &&
        renderErrorForFailureReason(quiz.failure_reason)}

      {/* Message when questions aren't ready */}
      {quiz.status !== QUIZ_STATUS.READY_FOR_REVIEW &&
        quiz.status !== QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL &&
        quiz.status !== QUIZ_STATUS.EXPORTING_TO_CANVAS &&
        quiz.status !== QUIZ_STATUS.PUBLISHED &&
        quiz.status !== QUIZ_STATUS.FAILED && (
          <Card.Root>
            <Card.Body>
              <EmptyState
                title="Questions Not Available Yet"
                description="Questions will appear here once the generation process is complete."
              />
            </Card.Body>
          </Card.Root>
        )}

      {/* Manual Question Dialog */}
      <ManualQuestionDialog
        quizId={id}
        quiz={quiz}
        isOpen={isManualQuestionDialogOpen}
        onOpenChange={setIsManualQuestionDialogOpen}
      />
    </VStack>
  )
}
```

### 4.3 Data Models & Schemas

#### QuestionCreateRequest Schema
```typescript
interface QuestionCreateRequest {
  quiz_id: string           // UUID of the quiz
  question_type: QuestionType // One of 5 supported types
  question_data: Record<string, any> // Polymorphic question data
  difficulty: "EASY" | "MEDIUM" | "HARD" | null // Default: "MEDIUM"
  tags: string[]           // Array of tags, default: []
}
```

#### Question Type Validation
The system uses existing Zod validation schemas:

- **Multiple Choice**: `mcqSchema` - validates A/B/C/D options and correct answer
- **True/False**: `trueFalseSchema` - validates boolean correct answer
- **Fill in Blank**: `fillInBlankSchema` - validates blank positions and answers
- **Matching**: `matchingSchema` - validates pairs and distractors
- **Categorization**: `categorizationSchema` - validates categories and items

#### Example Question Data Structures

**Multiple Choice:**
```typescript
{
  question_text: "What is the capital of France?",
  option_a: "London",
  option_b: "Berlin",
  option_c: "Paris",
  option_d: "Madrid",
  correct_answer: "C",
  explanation: "Paris is the capital and largest city of France."
}
```

**True/False:**
```typescript
{
  question_text: "The Earth is flat.",
  correct_answer: false,
  explanation: "The Earth is spherical, not flat."
}
```

### 4.4 Configuration

#### Feature Configuration
No additional configuration required. The feature uses existing application settings:

- Question types are defined in `QUESTION_TYPES` constant
- Validation schemas are pre-configured
- API endpoints use existing routing
- UI components use existing Chakra UI theme

#### Status-Based Access Control
```typescript
// Feature is only available in these quiz states
const ALLOWED_STATUSES = [
  QUIZ_STATUS.READY_FOR_REVIEW,
  QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL
]
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

#### QuestionTypeSelector Tests
```typescript
describe('QuestionTypeSelector', () => {
  it('should render all 5 question types', () => {
    render(<QuestionTypeSelector onSelectType={jest.fn()} />)

    expect(screen.getByText('Multiple Choice')).toBeInTheDocument()
    expect(screen.getByText('True/False')).toBeInTheDocument()
    expect(screen.getByText('Fill in the Blank')).toBeInTheDocument()
    expect(screen.getByText('Matching')).toBeInTheDocument()
    expect(screen.getByText('Categorization')).toBeInTheDocument()
  })

  it('should call onSelectType when a card is clicked', () => {
    const mockOnSelect = jest.fn()
    render(<QuestionTypeSelector onSelectType={mockOnSelect} />)

    fireEvent.click(screen.getByText('Multiple Choice'))

    expect(mockOnSelect).toHaveBeenCalledWith(QUESTION_TYPES.MULTIPLE_CHOICE)
  })
})
```

#### ManualQuestionCreator Tests
```typescript
describe('ManualQuestionCreator', () => {
  it('should transform form data correctly for MCQ', () => {
    const mockOnSave = jest.fn()
    const props = {
      questionType: QUESTION_TYPES.MULTIPLE_CHOICE,
      quizId: 'quiz-123',
      onSave: mockOnSave,
      onCancel: jest.fn()
    }

    render(<ManualQuestionCreator {...props} />)

    // Fill out form and submit
    // ... form interactions ...

    expect(mockOnSave).toHaveBeenCalledWith({
      quiz_id: 'quiz-123',
      question_type: 'multiple_choice',
      question_data: expect.objectContaining({
        question_text: expect.any(String),
        option_a: expect.any(String),
        // ... other fields
      }),
      difficulty: 'MEDIUM',
      tags: []
    })
  })
})
```

### 5.2 Integration Tests

#### Dialog Workflow Tests
```typescript
describe('ManualQuestionDialog Integration', () => {
  it('should complete full workflow for creating a question', async () => {
    const mockCreateQuestion = jest.fn().mockResolvedValue({ id: 'new-question' })

    render(
      <ManualQuestionDialog
        quizId="quiz-123"
        quiz={{ status: QUIZ_STATUS.READY_FOR_REVIEW }}
        isOpen={true}
        onOpenChange={jest.fn()}
      />
    )

    // Step 1: Select question type
    fireEvent.click(screen.getByText('Multiple Choice'))

    // Step 2: Fill out question form
    fireEvent.change(screen.getByLabelText('Question Text'), {
      target: { value: 'Test question?' }
    })
    // ... fill out other fields ...

    // Step 3: Submit
    fireEvent.click(screen.getByText('Save Changes'))

    await waitFor(() => {
      expect(mockCreateQuestion).toHaveBeenCalled()
    })
  })
})
```

### 5.3 Manual Testing Steps

#### Happy Path Testing
1. **Setup**: Navigate to a quiz in `ready_for_review` status
2. **Verify Button**: Confirm "Add Question" button is visible and accessible
3. **Open Dialog**: Click button and verify dialog opens full-screen
4. **Type Selection**: Test all 5 question type cards are clickable
5. **Question Creation**: For each question type:
   - Fill out all required fields
   - Test real-time validation
   - Submit and verify success
6. **Dialog Behavior**: Confirm dialog closes on successful creation
7. **Data Verification**: Verify new question appears in question list

#### Error Case Testing
1. **Status Restrictions**: Verify button is hidden in non-review states
2. **Validation Errors**: Test form validation for each question type
3. **API Errors**: Test handling of backend validation failures
4. **Network Errors**: Test behavior with network connectivity issues

#### Accessibility Testing
1. **Keyboard Navigation**: Verify full functionality with keyboard only
2. **Screen Reader**: Test with screen reader for proper announcements
3. **Focus Management**: Verify focus behavior in dialog
4. **Color Contrast**: Ensure all elements meet WCAG guidelines

### 5.4 Performance Considerations

#### Expected Performance Metrics
- **Dialog Open Time**: < 100ms
- **Type Selection Response**: < 50ms
- **Form Validation**: < 10ms per field
- **API Call Time**: < 2 seconds (depends on network)
- **Question List Refresh**: < 500ms

#### Performance Testing
```typescript
describe('Performance Tests', () => {
  it('should open dialog within 100ms', async () => {
    const start = performance.now()

    render(<ManualQuestionDialog {...props} isOpen={true} />)

    await waitFor(() => {
      expect(screen.getByText('Select Question Type')).toBeInTheDocument()
    })

    const end = performance.now()
    expect(end - start).toBeLessThan(100)
  })
})
```

---

## 6. Deployment Instructions

### 6.1 Pre-Deployment Checklist

1. **Code Quality**: Ensure all TypeScript errors are resolved
   ```bash
   cd frontend && npx tsc --noEmit
   ```

2. **Linting**: Run linting checks
   ```bash
   cd frontend && npm run lint
   ```

3. **Testing**: Run all tests
   ```bash
   cd frontend && npm test
   ```

4. **Build Verification**: Ensure production build succeeds
   ```bash
   cd frontend && npm run build
   ```

### 6.2 Deployment Steps

#### Development Environment
1. **Install Dependencies** (if needed):
   ```bash
   cd frontend && npm install
   ```

2. **Start Development Server**:
   ```bash
   cd frontend && npm run dev
   ```

3. **Verify Feature**: Test the feature in development environment

#### Staging Environment
1. **Build Application**:
   ```bash
   cd frontend && npm run build
   ```

2. **Deploy Build**: Deploy built assets to staging server

3. **Run E2E Tests**: Execute end-to-end test suite

4. **User Acceptance Testing**: Have stakeholders test the feature

#### Production Environment
1. **Final Build**:
   ```bash
   cd frontend && npm run build
   ```

2. **Deploy to Production**: Deploy using established deployment pipeline

3. **Health Checks**: Verify application loads and feature is accessible

4. **Monitor**: Watch for any errors or performance issues

### 6.3 Rollback Procedures

#### Immediate Rollback (Feature Toggle)
If a feature toggle system exists, disable the manual question feature:
```typescript
// In feature configuration
const FEATURES = {
  MANUAL_QUESTION_CREATION: false, // Disable feature
}
```

#### Code Rollback
1. **Identify Commit**: Find the commit before feature deployment
2. **Create Rollback Branch**:
   ```bash
   git checkout -b rollback-manual-questions
   git revert <feature-commit-hash>
   ```
3. **Test Rollback**: Verify application works without feature
4. **Deploy Rollback**: Deploy the rollback version

#### Database Considerations
- No database changes required for this feature
- No data migration rollback needed
- Manually created questions will remain in database but won't be creatable

---

## 7. Monitoring & Maintenance

### 7.1 Key Metrics to Monitor

#### Usage Metrics
- **Manual Question Creation Rate**: Number of questions created per day/week
- **Question Type Distribution**: Which types are created most frequently
- **Success Rate**: Percentage of successful question creations
- **User Adoption**: Number of unique users creating manual questions

#### Performance Metrics
- **Dialog Load Time**: Time to render question creation dialog
- **API Response Time**: Time for question creation API calls
- **Form Validation Performance**: Time for real-time validation
- **Error Rate**: Percentage of failed question creation attempts

#### User Experience Metrics
- **Completion Rate**: Percentage of users who complete question creation
- **Drop-off Points**: Where users abandon the creation process
- **Error Recovery**: How often users retry after errors

### 7.2 Log Entries to Monitor

#### Success Logs
```typescript
// Successful question creation
{
  level: "info",
  event: "manual_question_created",
  quiz_id: "quiz-123",
  question_type: "multiple_choice",
  user_id: "user-456",
  timestamp: "2025-07-30T10:30:00Z"
}
```

#### Error Logs
```typescript
// Question creation failure
{
  level: "error",
  event: "manual_question_creation_failed",
  quiz_id: "quiz-123",
  question_type: "fill_in_blank",
  error_type: "validation_error",
  error_message: "Blank positions must be sequential",
  user_id: "user-456",
  timestamp: "2025-07-30T10:35:00Z"
}
```

#### Performance Logs
```typescript
// Slow question creation
{
  level: "warn",
  event: "slow_question_creation",
  quiz_id: "quiz-123",
  response_time_ms: 5000,
  user_id: "user-456",
  timestamp: "2025-07-30T10:40:00Z"
}
```

### 7.3 Common Issues and Troubleshooting

#### Issue: "Add Question" Button Not Visible
**Symptoms**: Users report they can't find the add question button
**Diagnosis**: Check quiz status - button only appears in review states
**Resolution**:
1. Verify quiz is in `ready_for_review` or `ready_for_review_partial` status
2. Check for any status-checking logic errors
3. Ensure proper conditional rendering

#### Issue: Dialog Won't Open
**Symptoms**: Button clicks don't open the dialog
**Diagnosis**: Check browser console for JavaScript errors
**Resolution**:
1. Verify dialog state management is working
2. Check for any React rendering errors
3. Ensure proper event handling

#### Issue: Question Creation Fails
**Symptoms**: Form submission results in errors
**Diagnosis**: Check both frontend validation and backend API responses
**Resolution**:
1. Review validation error messages
2. Check API endpoint availability
3. Verify question data format matches expected schema

#### Issue: Real-time Validation Not Working
**Symptoms**: Form doesn't show validation errors as user types
**Diagnosis**: Check Zod schema integration and react-hook-form setup
**Resolution**:
1. Verify form validation configuration
2. Check for any schema validation errors
3. Ensure proper error state management

### 7.4 Maintenance Tasks

#### Weekly Tasks
- Review error logs for patterns
- Check performance metrics for degradation
- Verify feature usage statistics

#### Monthly Tasks
- Update dependencies if needed
- Review and optimize performance
- Analyze user feedback and usage patterns

#### Quarterly Tasks
- Comprehensive security review
- Performance optimization analysis
- User experience evaluation and improvements

---

## 8. Security Considerations

### 8.1 Authentication & Authorization

#### Access Control
- **User Authentication**: Feature requires valid Canvas OAuth authentication
- **Quiz Ownership**: Users can only create questions for quizzes they own
- **Status-Based Access**: Question creation restricted to appropriate quiz states

#### API Security
```typescript
// Backend endpoint security (existing)
@router.post("/{quiz_id}", response_model=QuestionResponse)
async def create_question(
    quiz_id: UUID,
    question_request: QuestionCreateRequest,
    current_user: CurrentUser,  // Authentication required
) -> dict[str, Any]:
    # Verify quiz ownership
    await _verify_quiz_ownership(quiz_id, current_user.id)
    # ... rest of implementation
```

### 8.2 Data Privacy & Validation

#### Input Sanitization
- **XSS Prevention**: All user inputs are sanitized through React's built-in protections
- **SQL Injection**: Backend uses parameterized queries through SQLModel
- **Content Validation**: Comprehensive validation through Zod schemas

#### Data Handling
- **No Sensitive Data**: Question content is educational, not sensitive
- **Audit Trail**: All question creation events are logged
- **Data Retention**: Questions persist as educational content

### 8.3 Frontend Security

#### Content Security Policy
Ensure CSP headers allow necessary resources:
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
```

#### XSS Protection
- React automatically escapes content in JSX
- No use of `dangerouslySetInnerHTML`
- All user inputs go through controlled components

### 8.4 Backend Security

#### Rate Limiting
Consider implementing rate limiting for question creation:
```python
# Example rate limiting (if needed)
@rate_limit("10/minute")  # Max 10 questions per minute
async def create_question(...):
```

#### Validation Security
- Server-side validation prevents malicious data
- Polymorphic validation ensures type safety
- Schema validation prevents injection attacks

---

## 9. Future Considerations

### 9.1 Known Limitations

#### Current Limitations
1. **No Bulk Creation**: Users must create questions one at a time
2. **No Templates**: No question templates or presets available
3. **No Import/Export**: Cannot import questions from external sources
4. **Single Language**: No multi-language question creation in single session

#### Technical Debt
- No comprehensive audit logging for question modifications
- Limited performance optimization for large question sets
- No offline support for question creation

### 9.2 Potential Improvements

#### Short-term Enhancements (Next 3 months)
1. **Question Templates**: Pre-built templates for common question patterns
2. **Bulk Operations**: Create multiple questions in single workflow
3. **Question Preview**: Preview mode before saving
4. **Auto-save Drafts**: Prevent loss of work during creation

#### Medium-term Features (3-6 months)
1. **Question Import**: Import from Word/Excel/CSV formats
2. **Collaboration**: Multiple users editing same quiz
3. **Version History**: Track question modifications over time
4. **Advanced Validation**: More sophisticated content validation

#### Long-term Vision (6+ months)
1. **AI Assistance**: AI-powered question suggestions and improvements
2. **Analytics**: Detailed analytics on question performance
3. **Integration**: Integration with external question banks
4. **Mobile Support**: Mobile-optimized question creation interface

### 9.3 Scalability Considerations

#### Performance Scaling
- **Question List Virtualization**: Already implemented for large question sets
- **Database Indexing**: Proper indexes on question queries
- **API Caching**: Consider caching for frequently accessed data

#### Architecture Scaling
- **Microservices**: Question service could be extracted to separate service
- **Event-Driven**: Question creation could trigger events for other services
- **CDN**: Static assets could be served via CDN for better performance

#### Data Scaling
- **Question Storage**: Consider file storage for complex question media
- **Search Indexing**: Full-text search capabilities for large question banks
- **Archival**: Archive old questions to maintain performance

### 9.4 Technology Evolution

#### Framework Updates
- **React 19**: Prepare for React 19 when released
- **Chakra UI v4**: Monitor for next major version
- **TypeScript 6**: Stay current with TypeScript releases

#### Browser Support
- **Modern Browsers**: Focus on evergreen browsers
- **Performance APIs**: Utilize new browser performance features
- **Accessibility**: Keep up with latest a11y standards

---

## Conclusion

This implementation document provides a comprehensive guide for implementing the Manual Question Addition feature. The feature integrates seamlessly with the existing Rag@UiT application architecture while providing instructors with the flexibility to create custom questions alongside AI-generated content.

The implementation follows established patterns in the codebase, maintains type safety throughout, and provides a robust user experience with proper error handling and validation. The feature enhances the overall value of the quiz generation system by combining the efficiency of AI with the expertise of human instructors.

For any questions or clarifications about this implementation, please refer to the existing codebase patterns and documentation, or consult with the development team.
