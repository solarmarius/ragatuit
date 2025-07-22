# Frontend Implementation Guide: Matching Question Type Support

**Document Date**: July 22, 2025
**Feature**: Frontend Matching Question Type Support
**Target System**: Rag@UiT Canvas LMS Quiz Generator Frontend
**Author**: Implementation Guide

## 1. Feature Overview

### What It Does

The Matching Question Type frontend implementation adds comprehensive user interface support for matching questions in the Rag@UiT quiz generator. This feature allows instructors to:

- **Create Matching Questions**: Through the quiz creation interface, selecting matching as a question type
- **Review Generated Questions**: View AI-generated matching questions with proper formatting
- **Edit Question Content**: Modify matching pairs, distractors, and explanations through a user-friendly interface
- **Visual Question Display**: See matching questions rendered with proper left-right column layout

### Business Value

- **Enhanced Question Variety**: Expands quiz creation beyond Multiple Choice and Fill-in-Blank questions
- **Improved Assessment Tools**: Provides instructors with more diverse question types for comprehensive evaluation
- **Seamless Integration**: Works within existing quiz creation and review workflows without disrupting user experience
- **AI-Powered Generation**: Leverages existing AI question generation for automatic matching question creation

### User Benefits

- **Instructors**: Can create engaging matching exercises that test associative knowledge and conceptual connections
- **Students**: Experience diverse question types that assess different cognitive skills and learning outcomes
- **Canvas Integration**: Questions export directly to Canvas LMS without manual formatting or conversion

### Technical Context

This implementation builds upon the existing polymorphic question system refactoring completed in the frontend. The backend already supports matching questions with AI templates for both English and Norwegian, making this purely a frontend integration task.

## 2. Technical Architecture

### High-Level Architecture

The matching question type follows the established polymorphic question architecture:

```
Frontend Question System Architecture:

┌─────────────────────────────────────────────────────────────┐
│                    Quiz Creation Flow                       │
├─────────────────────────────────────────────────────────────┤
│ QuizSettingsStep → Course Selection → Module Selection     │
│                           ↓                                 │
│              Question Generation (Backend AI)               │
│                           ↓                                 │
│              QuestionReview Component                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                Polymorphic Component System                 │
├─────────────────────────────────────────────────────────────┤
│  QuestionDisplay (Router)    │  QuestionEditor (Router)     │
│  ├── MCQDisplay             │  ├── MCQEditor                │
│  ├── FillInBlankDisplay     │  ├── FillInBlankEditor        │
│  └── MatchingDisplay ←NEW   │  └── MatchingEditor ←NEW      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Type System Foundation                    │
├─────────────────────────────────────────────────────────────┤
│  Question Types:                                            │
│  ├── Constants (QUESTION_TYPES.MATCHING)                   │
│  ├── TypeScript Interfaces (MatchingData)                  │
│  ├── Runtime Validation (Zod Schemas)                      │
│  └── Type Guards (isMatchingData)                          │
└─────────────────────────────────────────────────────────────┘
```

### System Integration

The matching question type integrates with existing systems:

- **State Management**: Uses TanStack Query for server state, React Hook Form for local form state
- **UI Framework**: Built with Chakra UI components for consistency with existing interface
- **Validation**: Leverages Zod for runtime validation and TypeScript for compile-time safety
- **API Integration**: Uses auto-generated API client from backend OpenAPI specification
- **Error Handling**: Implements established error boundary and fallback component patterns

### Component Interaction Flow

```
User Workflow:
1. Quiz Creation → Select "Matching" question type
2. AI Generation → Backend generates matching questions
3. Question Review → MatchingDisplay shows generated questions
4. Question Editing → MatchingEditor allows modifications
5. Quiz Export → Questions export to Canvas in proper format

Data Flow:
API Response → Type Validation → Component Routing → UI Rendering
     ↓              ↓               ↓               ↓
QuestionResponse → extractQuestionData → QuestionDisplay → MatchingDisplay
     ↓              ↓               ↓               ↓
Form Editing → Zod Validation → API Update → Optimistic UI Update
```

## 3. Dependencies & Prerequisites

### External Dependencies

All required dependencies are already present in the project:

- **React**: ^18.0.0 (Component framework)
- **TypeScript**: ^5.0.0 (Type safety and development experience)
- **Chakra UI**: ^2.8.0 (UI component library)
- **React Hook Form**: ^7.45.0 (Form management)
- **Zod**: ^3.22.0 (Runtime validation)
- **TanStack Query**: ^4.32.0 (Server state management)

### Version Requirements

- Node.js: 18+ (existing project requirement)
- npm: 9+ (package management)
- TypeScript: 5.0+ with strict mode enabled

### Environment Setup

No additional environment setup required. The implementation uses existing:

- Frontend development environment
- Auto-generated API client from backend OpenAPI specification
- Existing Canvas OAuth integration
- Established UI theme and component system

### Backend Prerequisites

The backend must be running with matching question type support (already implemented):

- Matching question type registered in question type registry
- AI templates available for both English and Norwegian
- Canvas export functionality for matching questions
- Database support for polymorphic question storage

## 4. Implementation Details

### 4.1 File Structure

```
frontend/src/
├── lib/
│   ├── constants/
│   │   └── index.ts                    # ← UPDATE: Add MATCHING constants
│   └── validation/
│       └── questionSchemas.ts          # ← UPDATE: Add matching validation
├── types/
│   └── questionTypes.ts                # ← UPDATE: Add MatchingData interface
├── components/
│   ├── Questions/
│   │   ├── display/
│   │   │   ├── MatchingDisplay.tsx     # ← CREATE: New display component
│   │   │   ├── QuestionDisplay.tsx     # ← UPDATE: Add matching case
│   │   │   └── index.ts               # ← UPDATE: Export MatchingDisplay
│   │   └── editors/
│   │       ├── MatchingEditor.tsx      # ← CREATE: New editor component
│   │       ├── QuestionEditor.tsx      # ← UPDATE: Add matching case
│   │       └── index.ts               # ← UPDATE: Export MatchingEditor
│   └── QuizCreation/
│       └── QuizSettingsStep.tsx        # ← UPDATE: Add matching option
```

### 4.2 Step-by-Step Implementation

#### Step 1: Update Constants and Configuration

**File**: `/frontend/src/lib/constants/index.ts`

```typescript
// Find the QUESTION_TYPES constant and add matching
export const QUESTION_TYPES = {
  MULTIPLE_CHOICE: "multiple_choice",
  FILL_IN_BLANK: "fill_in_blank",
  MATCHING: "matching", // ← ADD THIS LINE
} as const;

// Find the QUESTION_TYPE_LABELS constant and add matching
export const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  multiple_choice: "Multiple Choice",
  fill_in_blank: "Fill in the Blank",
  matching: "Matching", // ← ADD THIS LINE
};
```

**Purpose**: These constants ensure type safety and provide consistent labels throughout the application.

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

#### Step 2: Define Type System

**File**: `/frontend/src/types/questionTypes.ts`

Add the matching data interface and update the discriminated union:

```typescript
/**
 * Data structure for matching questions.
 * Students match items from left column (questions) to right column (answers).
 */
export interface MatchingData {
  question_text: string;
  pairs: Array<{
    question: string; // Left column item
    answer: string; // Right column correct match
  }>;
  distractors?: string[] | null; // Extra wrong answers (0-5)
  explanation?: string | null; // Optional explanation
}

// Update the discriminated union to include matching
export type QuestionData =
  | ({ type: "multiple_choice" } & MCQData)
  | ({ type: "fill_in_blank" } & FillInBlankData)
  | ({ type: "matching" } & MatchingData); // ← ADD THIS LINE

// Create type guard for runtime validation
export function isMatchingData(data: unknown): data is MatchingData {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const obj = data as Record<string, unknown>;

  // Validate required fields
  if (typeof obj.question_text !== "string") {
    return false;
  }

  // Validate pairs array
  if (
    !Array.isArray(obj.pairs) ||
    obj.pairs.length < 3 ||
    obj.pairs.length > 10
  ) {
    return false;
  }

  // Validate each pair structure
  for (const pair of obj.pairs) {
    if (
      typeof pair !== "object" ||
      pair === null ||
      typeof (pair as any).question !== "string" ||
      typeof (pair as any).answer !== "string"
    ) {
      return false;
    }
  }

  // Validate optional distractors
  if (obj.distractors !== undefined && obj.distractors !== null) {
    if (!Array.isArray(obj.distractors) || obj.distractors.length > 5) {
      return false;
    }
    for (const distractor of obj.distractors) {
      if (typeof distractor !== "string") {
        return false;
      }
    }
  }

  // Validate optional explanation
  if (obj.explanation !== undefined && obj.explanation !== null) {
    if (typeof obj.explanation !== "string") {
      return false;
    }
  }

  return true;
}

// Update extractQuestionData function to handle matching
export function extractQuestionData<T extends QuestionType>(
  question: QuestionResponse,
  expectedType: T
): TypedQuestionResponse<T>["question_data"] {
  if (question.question_type !== expectedType) {
    throw new Error(
      `Expected ${expectedType} question, got ${question.question_type}`
    );
  }

  const data = question.question_data;

  switch (expectedType) {
    case "multiple_choice":
      if (!isMCQData(data)) {
        throw new Error("Invalid Multiple Choice question data structure");
      }
      return data as any;

    case "fill_in_blank":
      if (!isFillInBlankData(data)) {
        throw new Error("Invalid Fill in the Blank question data structure");
      }
      return data as any;

    case "matching": // ← ADD THIS CASE
      if (!isMatchingData(data)) {
        throw new Error("Invalid Matching question data structure");
      }
      return data as any;

    default:
      throw new Error(`Unsupported question type: ${expectedType}`);
  }
}

// Add type alias for convenience
export type MatchingQuestionResponse = TypedQuestionResponse<"matching">;
```

**Purpose**: These type definitions provide compile-time safety and runtime validation for matching question data.

**Key Points**:

- `MatchingData` interface matches the backend data structure
- Type guard validates data at runtime to prevent errors
- Discriminated union enables exhaustive type checking
- Helper functions provide type-safe data extraction

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

#### Step 3: Add Validation Schema

**File**: `/frontend/src/lib/validation/questionSchemas.ts`

Add Zod schema for form validation:

```typescript
// Add matching form data type
export interface MatchingFormData {
  questionText: string;
  pairs: Array<{
    question: string;
    answer: string;
  }>;
  distractors?: string[];
  explanation?: string;
}

// Add matching validation schema
export const matchingSchema = z
  .object({
    questionText: nonEmptyString,
    pairs: z
      .array(
        z.object({
          question: nonEmptyString.min(1, "Question text is required"),
          answer: nonEmptyString.min(1, "Answer text is required"),
        })
      )
      .min(3, "At least 3 matching pairs are required")
      .max(10, "Maximum 10 matching pairs allowed")
      .refine(
        (pairs) => {
          // Check for duplicate questions
          const questions = pairs.map((p) => p.question.toLowerCase().trim());
          return new Set(questions).size === questions.length;
        },
        { message: "Duplicate questions are not allowed" }
      )
      .refine(
        (pairs) => {
          // Check for duplicate answers
          const answers = pairs.map((p) => p.answer.toLowerCase().trim());
          return new Set(answers).size === answers.length;
        },
        { message: "Duplicate answers are not allowed" }
      ),
    distractors: z
      .array(z.string().min(1, "Distractor cannot be empty"))
      .max(5, "Maximum 5 distractors allowed")
      .optional()
      .refine(
        (distractors) => {
          if (!distractors) return true;
          // Check for duplicate distractors
          const unique = new Set(
            distractors.map((d) => d.toLowerCase().trim())
          );
          return unique.size === distractors.length;
        },
        { message: "Duplicate distractors are not allowed" }
      ),
    explanation: optionalString,
  })
  .refine(
    (data) => {
      // Ensure distractors don't match correct answers
      if (!data.distractors) return true;

      const correctAnswers = new Set(
        data.pairs.map((p) => p.answer.toLowerCase().trim())
      );

      for (const distractor of data.distractors) {
        if (correctAnswers.has(distractor.toLowerCase().trim())) {
          return false;
        }
      }

      return true;
    },
    {
      message: "Distractors cannot match any correct answers",
      path: ["distractors"],
    }
  );

// Update getSchemaByType function
export function getSchemaByType<T extends QuestionType>(
  questionType: T
): z.ZodSchema<FormDataByType<T>> {
  switch (questionType) {
    case "multiple_choice":
      return mcqSchema as z.ZodSchema<FormDataByType<T>>;
    case "fill_in_blank":
      return fillInBlankSchema as z.ZodSchema<FormDataByType<T>>;
    case "matching": // ← ADD THIS CASE
      return matchingSchema as z.ZodSchema<FormDataByType<T>>;
    default:
      throw new Error(`No schema defined for question type: ${questionType}`);
  }
}

// Update FormDataByType to include matching
export type FormDataByType<T extends QuestionType> = T extends "multiple_choice"
  ? MCQFormData
  : T extends "fill_in_blank"
  ? FillInBlankFormData
  : T extends "matching" // ← ADD THIS LINE
  ? MatchingFormData // ← ADD THIS LINE
  : never;
```

**Purpose**: Provides comprehensive form validation with business rules and user-friendly error messages.

**Validation Rules**:

- 3-10 matching pairs required
- No duplicate questions or answers within pairs
- Maximum 5 distractors
- Distractors cannot match correct answers
- All text fields must be non-empty

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

#### Step 4: Create Display Component

**File**: `/frontend/src/components/Questions/display/MatchingDisplay.tsx`

Complete display component following established patterns:

```typescript
import { memo } from "react";
import { Box, VStack, HStack, Text, Grid, Badge } from "@chakra-ui/react";
import type { QuestionResponse } from "@/client";
import type { BaseQuestionDisplayProps } from "@/types/components";
import { extractQuestionData } from "@/types/questionTypes";
import { ExplanationBox } from "../shared";
import { ErrorDisplay } from "./ErrorDisplay";

/**
 * Display component for matching questions.
 * Shows question text, matching pairs in two columns, and optional explanation.
 */
function MatchingDisplayComponent({
  question,
  showCorrectAnswer = false,
  showExplanation = false,
}: BaseQuestionDisplayProps) {
  try {
    const matchingData = extractQuestionData(question, "matching");

    // Combine correct answers with distractors for answer column
    const allAnswers = [
      ...matchingData.pairs.map((pair) => pair.answer),
      ...(matchingData.distractors || []),
    ];

    // Shuffle answers if not showing correct answers (for display purposes)
    const displayAnswers = showCorrectAnswer
      ? allAnswers
      : [...allAnswers].sort(() => Math.random() - 0.5);

    return (
      <VStack gap={4} align="stretch">
        {/* Question Text */}
        <Text fontSize="md" fontWeight="medium">
          {matchingData.question_text}
        </Text>

        {/* Matching Interface */}
        <Box>
          <Grid templateColumns="1fr 1fr" gap={6}>
            {/* Left Column - Questions */}
            <VStack gap={3} align="stretch">
              <Text fontSize="sm" fontWeight="semibold" color="gray.600">
                Match These:
              </Text>
              {matchingData.pairs.map((pair, index) => (
                <Box
                  key={index}
                  p={3}
                  borderWidth={1}
                  borderColor="gray.200"
                  borderRadius="md"
                  bg="gray.50"
                >
                  <Text fontSize="sm">{pair.question}</Text>
                </Box>
              ))}
            </VStack>

            {/* Right Column - Answers */}
            <VStack gap={3} align="stretch">
              <Text fontSize="sm" fontWeight="semibold" color="gray.600">
                To These:
              </Text>
              {displayAnswers.map((answer, index) => {
                // Check if this is a correct answer
                const isCorrectAnswer = matchingData.pairs.some(
                  (pair) => pair.answer === answer
                );
                const isDistractor = !isCorrectAnswer;

                return (
                  <Box
                    key={index}
                    p={3}
                    borderWidth={1}
                    borderColor={
                      showCorrectAnswer && isCorrectAnswer
                        ? "green.300"
                        : showCorrectAnswer && isDistractor
                        ? "red.200"
                        : "gray.200"
                    }
                    borderRadius="md"
                    bg={
                      showCorrectAnswer && isCorrectAnswer
                        ? "green.50"
                        : showCorrectAnswer && isDistractor
                        ? "red.50"
                        : "white"
                    }
                    position="relative"
                  >
                    <Text fontSize="sm">{answer}</Text>

                    {showCorrectAnswer && (
                      <Badge
                        position="absolute"
                        top={1}
                        right={1}
                        size="sm"
                        colorScheme={isCorrectAnswer ? "green" : "red"}
                      >
                        {isCorrectAnswer ? "Correct" : "Distractor"}
                      </Badge>
                    )}
                  </Box>
                );
              })}
            </VStack>
          </Grid>

          {/* Correct Matches Display (when showing answers) */}
          {showCorrectAnswer && (
            <Box mt={6} p={4} bg="blue.50" borderRadius="md">
              <Text fontSize="sm" fontWeight="semibold" mb={3} color="blue.800">
                Correct Matches:
              </Text>
              <VStack gap={2} align="stretch">
                {matchingData.pairs.map((pair, index) => (
                  <HStack key={index} spacing={3}>
                    <Box flex={1} p={2} bg="white" borderRadius="sm">
                      <Text fontSize="sm">{pair.question}</Text>
                    </Box>
                    <Text fontSize="sm" color="blue.600" fontWeight="medium">
                      →
                    </Text>
                    <Box flex={1} p={2} bg="white" borderRadius="sm">
                      <Text fontSize="sm">{pair.answer}</Text>
                    </Box>
                  </HStack>
                ))}
              </VStack>
            </Box>
          )}
        </Box>

        {/* Explanation */}
        {showExplanation && matchingData.explanation && (
          <ExplanationBox explanation={matchingData.explanation} />
        )}
      </VStack>
    );
  } catch (error) {
    console.error("Error rendering matching question:", error);
    return <ErrorDisplay error="Error loading matching question data" />;
  }
}

/**
 * Memoized matching display component for performance optimization.
 */
export const MatchingDisplay = memo(MatchingDisplayComponent);
MatchingDisplay.displayName = "MatchingDisplay";
```

**Purpose**: Renders matching questions with proper visual layout and correct answer highlighting.

**Key Features**:

- Two-column grid layout for questions and answers
- Color-coded correct/incorrect answers when `showCorrectAnswer` is true
- Distractor identification with badges
- Correct matches summary section
- Responsive design with Chakra UI components
- Error boundary with fallback component

**Update exports in** `/frontend/src/components/Questions/display/index.ts`:

```typescript
export { MatchingDisplay } from "./MatchingDisplay";
```

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

#### Step 5: Create Editor Component

**File**: `/frontend/src/components/Questions/editors/MatchingEditor.tsx`

Complete editor component with form management:

```typescript
import { memo, useCallback, useState } from "react";
import {
  VStack,
  HStack,
  Button,
  Text,
  Box,
  Grid,
  IconButton,
  Divider,
} from "@chakra-ui/react";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PlusIcon, XIcon } from "lucide-react";
import type { QuestionResponse, QuestionUpdateRequest } from "@/client";
import type { BaseQuestionEditorProps } from "@/types/components";
import { extractQuestionData } from "@/types/questionTypes";
import type { MatchingFormData } from "@/lib/validation/questionSchemas";
import { matchingSchema } from "@/lib/validation/questionSchemas";
import { Field } from "@/components/ui/field";
import { ErrorEditor } from "./ErrorEditor";

/**
 * Editor component for matching questions.
 * Allows editing of question text, matching pairs, distractors, and explanation.
 */
function MatchingEditorComponent({
  question,
  onSave,
  onCancel,
  isLoading = false,
}: BaseQuestionEditorProps) {
  try {
    const matchingData = extractQuestionData(question, "matching");

    // Initialize form with current question data
    const form = useForm<MatchingFormData>({
      resolver: zodResolver(matchingSchema),
      defaultValues: {
        questionText: matchingData.question_text,
        pairs: matchingData.pairs,
        distractors: matchingData.distractors || [],
        explanation: matchingData.explanation || "",
      },
    });

    const {
      control,
      handleSubmit,
      formState: { errors, isDirty },
    } = form;

    // Field arrays for dynamic pairs and distractors
    const {
      fields: pairFields,
      append: appendPair,
      remove: removePair,
    } = useFieldArray({
      control,
      name: "pairs",
    });

    const {
      fields: distractorFields,
      append: appendDistractor,
      remove: removeDistractor,
    } = useFieldArray({
      control,
      name: "distractors",
    });

    // Handle form submission
    const onSubmit = useCallback(
      (formData: MatchingFormData) => {
        const updateData: QuestionUpdateRequest = {
          question_data: {
            question_text: formData.questionText,
            pairs: formData.pairs,
            distractors: formData.distractors?.length
              ? formData.distractors
              : null,
            explanation: formData.explanation || null,
          },
        };
        onSave(updateData);
      },
      [onSave]
    );

    // Add new matching pair
    const handleAddPair = useCallback(() => {
      if (pairFields.length < 10) {
        appendPair({ question: "", answer: "" });
      }
    }, [appendPair, pairFields.length]);

    // Add new distractor
    const handleAddDistractor = useCallback(() => {
      if (distractorFields.length < 5) {
        appendDistractor("");
      }
    }, [appendDistractor, distractorFields.length]);

    return (
      <Box as="form" onSubmit={handleSubmit(onSubmit)}>
        <VStack gap={6} align="stretch">
          {/* Question Text */}
          <Field
            label="Question Text"
            required
            invalid={!!errors.questionText}
            errorText={errors.questionText?.message}
          >
            <Controller
              name="questionText"
              control={control}
              render={({ field }) => (
                <textarea
                  {...field}
                  placeholder="Enter the matching question instructions..."
                  rows={3}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    border: "1px solid #e2e8f0",
                    borderRadius: "0.375rem",
                    fontSize: "0.875rem",
                  }}
                />
              )}
            />
          </Field>

          {/* Matching Pairs */}
          <Box>
            <HStack justify="space-between" mb={4}>
              <Text fontSize="md" fontWeight="semibold">
                Matching Pairs ({pairFields.length}/10)
              </Text>
              <Button
                size="sm"
                leftIcon={<PlusIcon />}
                onClick={handleAddPair}
                isDisabled={pairFields.length >= 10}
                colorScheme="blue"
                variant="outline"
              >
                Add Pair
              </Button>
            </HStack>

            {errors.pairs && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.pairs.message}
              </Text>
            )}

            <VStack gap={4} align="stretch">
              {pairFields.map((field, index) => (
                <Box key={field.id} p={4} borderWidth={1} borderRadius="md">
                  <HStack align="flex-start" spacing={4}>
                    <Box flex={1}>
                      <Field
                        label={`Question ${index + 1}`}
                        required
                        invalid={!!errors.pairs?.[index]?.question}
                        errorText={errors.pairs?.[index]?.question?.message}
                      >
                        <Controller
                          name={`pairs.${index}.question`}
                          control={control}
                          render={({ field: inputField }) => (
                            <input
                              {...inputField}
                              placeholder="Enter question/left item..."
                              style={{
                                width: "100%",
                                padding: "0.5rem",
                                border: "1px solid #e2e8f0",
                                borderRadius: "0.375rem",
                                fontSize: "0.875rem",
                              }}
                            />
                          )}
                        />
                      </Field>
                    </Box>

                    <Box flex={1}>
                      <Field
                        label={`Answer ${index + 1}`}
                        required
                        invalid={!!errors.pairs?.[index]?.answer}
                        errorText={errors.pairs?.[index]?.answer?.message}
                      >
                        <Controller
                          name={`pairs.${index}.answer`}
                          control={control}
                          render={({ field: inputField }) => (
                            <input
                              {...inputField}
                              placeholder="Enter answer/right item..."
                              style={{
                                width: "100%",
                                padding: "0.5rem",
                                border: "1px solid #e2e8f0",
                                borderRadius: "0.375rem",
                                fontSize: "0.875rem",
                              }}
                            />
                          )}
                        />
                      </Field>
                    </Box>

                    <IconButton
                      aria-label={`Remove pair ${index + 1}`}
                      icon={<XIcon />}
                      size="sm"
                      colorScheme="red"
                      variant="ghost"
                      onClick={() => removePair(index)}
                      isDisabled={pairFields.length <= 3}
                      mt={6}
                    />
                  </HStack>
                </Box>
              ))}
            </VStack>

            <Text fontSize="sm" color="gray.600" mt={2}>
              At least 3 pairs required, maximum 10 pairs allowed.
            </Text>
          </Box>

          <Divider />

          {/* Distractors */}
          <Box>
            <HStack justify="space-between" mb={4}>
              <Text fontSize="md" fontWeight="semibold">
                Distractors ({distractorFields.length}/5)
              </Text>
              <Button
                size="sm"
                leftIcon={<PlusIcon />}
                onClick={handleAddDistractor}
                isDisabled={distractorFields.length >= 5}
                colorScheme="blue"
                variant="outline"
              >
                Add Distractor
              </Button>
            </HStack>

            {errors.distractors && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.distractors.message}
              </Text>
            )}

            <VStack gap={3} align="stretch">
              {distractorFields.map((field, index) => (
                <HStack key={field.id} align="flex-start">
                  <Box flex={1}>
                    <Field
                      label={`Distractor ${index + 1}`}
                      invalid={!!errors.distractors?.[index]}
                      errorText={errors.distractors?.[index]?.message}
                    >
                      <Controller
                        name={`distractors.${index}`}
                        control={control}
                        render={({ field: inputField }) => (
                          <input
                            {...inputField}
                            placeholder="Enter incorrect answer option..."
                            style={{
                              width: "100%",
                              padding: "0.5rem",
                              border: "1px solid #e2e8f0",
                              borderRadius: "0.375rem",
                              fontSize: "0.875rem",
                            }}
                          />
                        )}
                      />
                    </Field>
                  </Box>
                  <IconButton
                    aria-label={`Remove distractor ${index + 1}`}
                    icon={<XIcon />}
                    size="sm"
                    colorScheme="red"
                    variant="ghost"
                    onClick={() => removeDistractor(index)}
                    mt={6}
                  />
                </HStack>
              ))}
            </VStack>

            <Text fontSize="sm" color="gray.600" mt={2}>
              Optional incorrect answers that don't match any question. Maximum
              5 allowed.
            </Text>
          </Box>

          <Divider />

          {/* Explanation */}
          <Field
            label="Explanation (Optional)"
            invalid={!!errors.explanation}
            errorText={errors.explanation?.message}
          >
            <Controller
              name="explanation"
              control={control}
              render={({ field }) => (
                <textarea
                  {...field}
                  placeholder="Optional explanation for the correct matches..."
                  rows={3}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    border: "1px solid #e2e8f0",
                    borderRadius: "0.375rem",
                    fontSize: "0.875rem",
                  }}
                />
              )}
            />
          </Field>

          {/* Action Buttons */}
          <HStack gap={3} justify="end" pt={4}>
            <Button variant="outline" onClick={onCancel} isDisabled={isLoading}>
              Cancel
            </Button>
            <Button
              type="submit"
              colorScheme="blue"
              loading={isLoading}
              isDisabled={!isDirty}
            >
              Save Changes
            </Button>
          </HStack>
        </VStack>
      </Box>
    );
  } catch (error) {
    console.error("Error rendering matching question editor:", error);
    return (
      <ErrorEditor
        error="Error loading question data for editing"
        onCancel={onCancel}
      />
    );
  }
}

/**
 * Memoized matching editor component for performance optimization.
 */
export const MatchingEditor = memo(MatchingEditorComponent);
MatchingEditor.displayName = "MatchingEditor";
```

**Purpose**: Provides comprehensive editing interface for matching questions with validation and dynamic field management.

**Key Features**:

- Dynamic pair management (add/remove pairs, 3-10 limit)
- Dynamic distractor management (add/remove, 0-5 limit)
- Form validation with Zod schema integration
- React Hook Form for optimal performance
- Visual feedback for errors and requirements
- Disabled states for limits and validation

**Update exports in** `/frontend/src/components/Questions/editors/index.ts`:

```typescript
export { MatchingEditor } from "./MatchingEditor";
```

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

### 4.3 Data Models & Schemas

#### Matching Question Data Structure

```typescript
interface MatchingData {
  question_text: string; // Main question instruction
  pairs: Array<{
    // 3-10 required pairs
    question: string; // Left column item
    answer: string; // Correct right column match
  }>;
  distractors?: string[] | null; // 0-5 optional wrong answers
  explanation?: string | null; // Optional explanation text
}
```

#### Example Data

```json
{
  "question_text": "Match each country to its capital city.",
  "pairs": [
    { "question": "France", "answer": "Paris" },
    { "question": "Germany", "answer": "Berlin" },
    { "question": "Italy", "answer": "Rome" },
    { "question": "Spain", "answer": "Madrid" }
  ],
  "distractors": ["London", "Vienna"],
  "explanation": "These are the current capital cities of their respective countries."
}
```

#### Validation Rules

- **Pairs**: 3-10 pairs required
- **Uniqueness**: No duplicate questions or answers within pairs
- **Distractors**: Maximum 5, cannot match any correct answer
- **Text Fields**: All must be non-empty strings
- **Explanation**: Optional, can be null or empty string

### 4.4 Configuration

#### No Additional Configuration Required

The matching question type uses existing application configuration:

- **API Client**: Uses auto-generated client from backend OpenAPI
- **Theme**: Follows existing Chakra UI theme configuration
- **Routing**: Integrates with existing TanStack Router setup
- **State Management**: Uses existing TanStack Query configuration

#### Environment Variables

No new environment variables required. Uses existing:

```env
# Backend API configuration (existing)
VITE_API_BASE_URL=http://localhost:8000

# No additional configuration needed
```

## 5. Testing Strategy

### Unit Test Examples

#### Type Guard Testing

```typescript
// Test file: src/types/__tests__/questionTypes.test.ts
import { isMatchingData } from "@/types/questionTypes";

describe("isMatchingData", () => {
  it("should return true for valid matching data", () => {
    const validData = {
      question_text: "Match countries to capitals",
      pairs: [
        { question: "France", answer: "Paris" },
        { question: "Germany", answer: "Berlin" },
        { question: "Italy", answer: "Rome" },
      ],
      distractors: ["London"],
      explanation: "Capital cities",
    };

    expect(isMatchingData(validData)).toBe(true);
  });

  it("should return false for insufficient pairs", () => {
    const invalidData = {
      question_text: "Test",
      pairs: [
        { question: "A", answer: "B" },
        { question: "C", answer: "D" },
      ], // Only 2 pairs, need 3 minimum
    };

    expect(isMatchingData(invalidData)).toBe(false);
  });

  it("should return false for too many distractors", () => {
    const invalidData = {
      question_text: "Test",
      pairs: [
        { question: "A", answer: "B" },
        { question: "C", answer: "D" },
        { question: "E", answer: "F" },
      ],
      distractors: ["G", "H", "I", "J", "K", "L"], // 6 distractors, max 5
    };

    expect(isMatchingData(invalidData)).toBe(false);
  });
});
```

#### Component Testing

```typescript
// Test file: src/components/Questions/display/__tests__/MatchingDisplay.test.tsx
import { render, screen } from "@testing-library/react";
import { MatchingDisplay } from "../MatchingDisplay";
import type { QuestionResponse } from "@/client";

const mockMatchingQuestion: QuestionResponse = {
  id: "test-id",
  question_type: "matching",
  question_data: {
    question_text: "Match programming languages to their creators",
    pairs: [
      { question: "Python", answer: "Guido van Rossum" },
      { question: "JavaScript", answer: "Brendan Eich" },
      { question: "Java", answer: "James Gosling" },
    ],
    distractors: ["Linus Torvalds"],
    explanation: "These are the original creators",
  },
  quiz_id: "quiz-id",
  is_approved: false,
  created_at: "2025-01-22T10:00:00Z",
  updated_at: "2025-01-22T10:00:00Z",
};

describe("MatchingDisplay", () => {
  it("renders question text and pairs", () => {
    render(<MatchingDisplay question={mockMatchingQuestion} />);

    expect(
      screen.getByText("Match programming languages to their creators")
    ).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("Guido van Rossum")).toBeInTheDocument();
    expect(screen.getByText("JavaScript")).toBeInTheDocument();
    expect(screen.getByText("Brendan Eich")).toBeInTheDocument();
  });

  it("shows correct matches when showCorrectAnswer is true", () => {
    render(
      <MatchingDisplay
        question={mockMatchingQuestion}
        showCorrectAnswer={true}
      />
    );

    expect(screen.getByText("Correct Matches:")).toBeInTheDocument();
    expect(screen.getAllByText("Correct")).toHaveLength(3); // 3 correct answers
    expect(screen.getAllByText("Distractor")).toHaveLength(1); // 1 distractor
  });

  it("shows explanation when showExplanation is true", () => {
    render(
      <MatchingDisplay question={mockMatchingQuestion} showExplanation={true} />
    );

    expect(
      screen.getByText("These are the original creators")
    ).toBeInTheDocument();
  });
});
```

### Integration Test Scenarios

#### Form Validation Integration

```typescript
// Test file: src/components/Questions/editors/__tests__/MatchingEditor.integration.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MatchingEditor } from "../MatchingEditor";

describe("MatchingEditor Integration", () => {
  const mockOnSave = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("validates minimum pairs requirement", async () => {
    render(
      <MatchingEditor
        question={mockMatchingQuestion}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Remove pairs to get below minimum
    const removeBtns = screen.getAllByLabelText(/Remove pair/);
    await userEvent.click(removeBtns[0]); // Should be disabled if only 3 pairs

    expect(removeBtns[0]).toBeDisabled();
  });

  it("prevents duplicate answers", async () => {
    render(
      <MatchingEditor
        question={mockMatchingQuestion}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Set duplicate answer
    const answerInputs = screen.getAllByPlaceholderText(
      "Enter answer/right item..."
    );
    await userEvent.clear(answerInputs[1]);
    await userEvent.type(answerInputs[1], "Guido van Rossum"); // Same as first answer

    const saveBtn = screen.getByText("Save Changes");
    await userEvent.click(saveBtn);

    await waitFor(() => {
      expect(
        screen.getByText("Duplicate answers are not allowed")
      ).toBeInTheDocument();
    });

    expect(mockOnSave).not.toHaveBeenCalled();
  });

  it("saves valid form data", async () => {
    render(
      <MatchingEditor
        question={mockMatchingQuestion}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Modify question text
    const questionInput = screen.getByPlaceholderText(
      "Enter the matching question instructions..."
    );
    await userEvent.clear(questionInput);
    await userEvent.type(questionInput, "Updated question text");

    const saveBtn = screen.getByText("Save Changes");
    await userEvent.click(saveBtn);

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        question_data: {
          question_text: "Updated question text",
          pairs: expect.arrayContaining([
            expect.objectContaining({
              question: expect.any(String),
              answer: expect.any(String),
            }),
          ]),
          distractors: expect.any(Array),
          explanation: expect.any(String),
        },
      });
    });
  });
});
```

### Manual Testing Steps

1. **Quiz Creation Flow**

   ```
   1. Navigate to quiz creation
   2. Select "Matching" question type
   3. Complete course and module selection
   4. Verify matching questions are generated
   5. Check question display renders correctly
   ```

2. **Question Editing Flow**

   ```
   1. Open matching question for editing
   2. Add/remove matching pairs
   3. Add/remove distractors
   4. Test validation errors
   5. Save changes and verify updates
   ```

3. **Error Handling**
   ```
   1. Test with malformed question data
   2. Verify error boundaries activate
   3. Check fallback components display
   4. Test recovery after errors
   ```

### Performance Benchmarks

- **Component Render Time**: < 50ms for typical matching question
- **Form Validation**: < 10ms for complete form validation
- **Memory Usage**: < 2MB additional for matching components
- **Bundle Size Impact**: < 10KB gzipped for all matching components

## 6. Deployment Instructions

### Step-by-Step Deployment

1. **Pre-deployment Validation**

   ```bash
   # Verify TypeScript compilation
   cd frontend
   npx tsc --noEmit

   # Run linting
   npm run lint

   # Build production bundle
   npm run build
   ```

2. **Frontend Build Process**

   ```bash
   # Production build with matching support
   npm run build

   # Verify bundle size increase is minimal
   npm run build -- --analyze
   ```

3. **Integration Testing**

   ```bash
   # Start backend with matching support
   cd backend
   docker compose up -d

   # Run frontend with backend
   cd frontend
   npm run dev

   # Test matching question creation
   # Navigate to http://localhost:5173
   ```

4. **Deployment Verification**

   ```bash
   # Check that matching questions work
   curl -X GET http://localhost:8000/api/v1/questions/types
   # Should include "matching" in response

   # Verify frontend loads matching components
   # Test complete quiz creation workflow
   ```

### Environment-Specific Configurations

#### Development Environment

- No special configuration required
- Uses existing development setup

#### Staging Environment

- Verify backend matching support is deployed
- Test with staging Canvas API credentials
- Validate AI question generation works

#### Production Environment

- Ensure Canvas production API access
- Monitor question generation performance
- Verify proper error handling and logging

### Rollback Procedures

1. **Frontend Rollback**

   ```bash
   # If issues occur, rollback to previous version
   git revert <commit-range>
   npm run build
   # Redeploy frontend bundle
   ```

2. **Component Rollback**

   - Remove matching option from QuizSettingsStep
   - Update router to show unsupported message
   - Disable matching in constants temporarily

3. **Graceful Degradation**
   - Matching questions show as "Unsupported" type
   - No data loss occurs
   - Users can still use MCQ and Fill-in-Blank

## 7. Monitoring & Maintenance

### Key Metrics to Monitor

#### Application Metrics

- **Question Type Usage**: Track percentage of matching questions created
- **Error Rates**: Monitor component error boundaries and validation failures
- **Performance Metrics**: Component render times, form validation speed
- **User Engagement**: Time spent editing matching questions vs other types

#### Technical Metrics

- **Bundle Size**: Monitor impact of matching components on bundle size
- **Memory Usage**: Track memory consumption during question editing
- **API Calls**: Monitor backend API usage for matching operations
- **TypeScript Errors**: Watch for type-related issues in production

### Log Entries to Watch For

#### Success Indicators

```javascript
// Component mounting successfully
console.log("MatchingDisplay rendered successfully", { questionId });

// Form validation passing
console.log("Matching question validation passed", {
  pairCount,
  distractorCount,
});

// Successful saves
console.log("Matching question saved successfully", { questionId, updateData });
```

#### Error Indicators

```javascript
// Component errors
console.error("Error rendering matching question:", error);

// Validation errors
console.error("Matching question validation failed:", validationError);

// Type errors
console.error("Invalid matching question data structure:", dataError);
```

#### Browser Console Monitoring

- Watch for React component warnings
- Monitor for validation error messages
- Check for failed API calls or data loading issues

### Common Issues and Troubleshooting

#### Issue: "Matching option not appearing in quiz creation"

**Symptoms**: Matching question type not shown in QuizSettingsStep
**Causes**:

- Constants not updated correctly
- TypeScript compilation errors
- Component not imported properly

**Solutions**:

```bash
# Check TypeScript compilation
npx tsc --noEmit

# Verify constants are exported correctly
grep -r "MATCHING" src/lib/constants/

# Check component imports
grep -r "MatchingDisplay\|MatchingEditor" src/components/
```

#### Issue: "Validation errors in matching editor"

**Symptoms**: Form won't save, validation messages appear
**Causes**:

- Duplicate questions/answers
- Too few pairs (< 3)
- Distractors match correct answers

**Solutions**:

```typescript
// Debug validation in browser console
const formData = form.getValues();
console.log("Form data:", formData);
console.log("Validation errors:", form.formState.errors);

// Check for duplicates
const questions = formData.pairs.map((p) => p.question.toLowerCase());
console.log(
  "Duplicate questions:",
  questions.length !== new Set(questions).size
);
```

#### Issue: "Error loading matching question data"

**Symptoms**: ErrorDisplay component shows instead of MatchingDisplay
**Causes**:

- Invalid question data from backend
- Type guard rejection
- Missing required fields

**Solutions**:

```javascript
// Debug in browser console
console.log("Question data:", question.question_data);
console.log("Is valid matching data:", isMatchingData(question.question_data));

// Check backend response format
fetch("/api/v1/questions/{id}")
  .then((r) => r.json())
  .then((data) => console.log("Backend question data:", data));
```

#### Issue: "TypeScript compilation errors"

**Symptoms**: Build fails with type errors
**Causes**:

- Missing type exports
- Discriminated union not updated
- Component prop mismatches

**Solutions**:

```bash
# Check specific TypeScript errors
npx tsc --noEmit --pretty

# Verify all exports are correct
grep -r "export.*Matching" src/

# Check discriminated union includes matching
grep -A 10 "type QuestionData" src/types/questionTypes.ts
```

## 8. Security Considerations

### Authentication/Authorization

#### No Changes Required

- **Canvas OAuth**: Uses existing Canvas OAuth flow for user authentication
- **API Security**: Leverages existing JWT token-based API security
- **Question Access**: Follows existing question ownership and access control patterns
- **User Permissions**: Inherits from existing quiz creation permission system

#### Data Access Patterns

```typescript
// Questions are accessed through existing secure API
const { data: questions } = useQuery({
  queryKey: ["quiz", quizId, "questions"],
  queryFn: () => QuestionsService.getQuizQuestions({ quizId }), // Secured endpoint
});
```

### Data Privacy

#### Content Storage

- **Question Data**: Stored in existing encrypted PostgreSQL database
- **User Content**: Course content remains within Canvas OAuth scope
- **No Additional Storage**: No new data storage requirements or patterns

#### Data Handling

```typescript
// Matching questions follow same data patterns
interface MatchingData {
  question_text: string; // Encrypted at rest
  pairs: Array<{
    // Encrypted at rest
    question: string;
    answer: string;
  }>;
  distractors?: string[]; // Optional, encrypted at rest
  explanation?: string; // Optional, encrypted at rest
}
```

### Security Best Practices

#### Input Validation

```typescript
// Comprehensive client-side validation
export const matchingSchema = z.object({
  questionText: nonEmptyString,
  pairs: z
    .array(...)
    .refine(...), // Prevents injection and validates structure
  // ... additional validation
});

// Runtime type checking
export function isMatchingData(data: unknown): data is MatchingData {
  // Validates data structure to prevent malicious payloads
}
```

#### Output Sanitization

```typescript
// All text content is escaped by React by default
<Text fontSize="md" fontWeight="medium">
  {matchingData.question_text} {/* Automatically escaped */}
</Text>

// HTML content handled safely
<ExplanationBox explanation={matchingData.explanation} />
```

#### API Security

```typescript
// All API calls use existing secure patterns
const updateMutation = useApiMutation(
  (data: QuestionUpdateRequest) =>
    QuestionsService.updateQuestion({ questionId, data }), // Authenticated endpoint
  {
    successMessage: "Question updated successfully!",
    invalidateQueries: [["quiz", quizId, "questions"]], // Cache invalidation
  }
);
```

### Cross-Site Scripting (XSS) Prevention

#### React Built-in Protection

- **Automatic Escaping**: All text content automatically escaped by React
- **No Dangerous HTML**: No `dangerouslySetInnerHTML` usage in matching components
- **Safe Attributes**: All component props are type-safe and validated

#### Input Sanitization

```typescript
// Form validation prevents malicious input
const matchingSchema = z.object({
  questionText: nonEmptyString.max(1000), // Length limits
  pairs: z.array(
    z.object({
      question: nonEmptyString.max(500), // Reasonable limits
      answer: nonEmptyString.max(500), // Prevent large payloads
    })
  ),
});
```

### Cross-Site Request Forgery (CSRF) Prevention

#### Existing Token-Based Security

- **JWT Tokens**: All API requests use existing JWT authentication
- **SameSite Cookies**: Existing cookie configuration prevents CSRF
- **Origin Validation**: Backend validates request origins

### Data Validation Security

#### Type Guards as Security Layer

```typescript
export function isMatchingData(data: unknown): data is MatchingData {
  // Prevents type confusion attacks
  if (typeof data !== "object" || data === null) return false;

  // Validates all required fields exist and have correct types
  // Prevents prototype pollution and injection
  const obj = data as Record<string, unknown>;

  // Strict validation prevents malicious data structures
  return validateAllFields(obj);
}
```

#### Schema Validation

```typescript
// Zod provides additional runtime protection
const result = matchingSchema.safeParse(formData);
if (!result.success) {
  // Prevents invalid data from reaching backend
  throw new ValidationError(result.error);
}
```

## 9. Future Considerations

### Known Limitations

#### Current Implementation Constraints

1. **1:1 Matching Only**

   - **Limitation**: Each question has exactly one correct answer
   - **Impact**: Cannot create complex many-to-many matching scenarios
   - **Workaround**: Use multiple matching questions for complex relationships

2. **Static Distractor Count**

   - **Limitation**: Maximum 5 distractors per question
   - **Impact**: May not provide enough confusion for complex topics
   - **Future Enhancement**: Dynamic distractor generation based on content

3. **No Visual Media Support**

   - **Limitation**: Text-only matching pairs
   - **Impact**: Cannot create image-based or multimedia matching questions
   - **Future Enhancement**: Rich media support for pairs and distractors

4. **Fixed Scoring Model**
   - **Limitation**: All pairs have equal weight
   - **Impact**: Cannot emphasize more important matches
   - **Future Enhancement**: Weighted scoring system

### Potential Improvements

#### Enhanced Matching Types

```typescript
// Future: Complex matching with categories
interface CategorizedMatchingData {
  question_text: string;
  categories: Array<{
    name: string;
    items: string[];
    matches: string[];
  }>;
  // Multiple items can match multiple categories
}

// Future: Visual matching with media
interface MediaMatchingData {
  question_text: string;
  pairs: Array<{
    question: string | { type: "image"; url: string };
    answer: string | { type: "image"; url: string };
  }>;
}
```

#### Advanced UI Features

1. **Drag and Drop Interface**

   ```typescript
   // Enhanced editor with drag-and-drop
   import { DragDropContext, Droppable, Draggable } from "react-beautiful-dnd";

   function EnhancedMatchingEditor() {
     // Allow visual pairing through drag-and-drop
     // Provide preview of student experience
     // Real-time validation feedback
   }
   ```

2. **Visual Question Preview**

   ```typescript
   // Student-view preview in editor
   function MatchingEditorPreview({
     formData,
   }: {
     formData: MatchingFormData;
   }) {
     // Show how question will appear to students
     // Interactive preview with drag-and-drop
     // Instant feedback on changes
   }
   ```

3. **Bulk Operations**
   ```typescript
   // Future: Import/export matching questions
   interface MatchingImportFormat {
     questions: MatchingData[];
     format: "csv" | "json" | "qti";
     validation: boolean;
   }
   ```

#### Performance Optimizations

1. **Virtual Scrolling for Large Questions**

   ```typescript
   // For questions with many pairs
   import { FixedSizeList as List } from "react-window";

   function LargeMatchingDisplay({ pairs }: { pairs: MatchingPair[] }) {
     // Virtualize rendering for 50+ pairs
     // Maintain performance with large datasets
   }
   ```

2. **Lazy Loading of Components**

   ```typescript
   // Code splitting for matching components
   const MatchingEditor = lazy(() =>
     import("./MatchingEditor").then((module) => ({
       default: module.MatchingEditor,
     }))
   );
   ```

3. **Optimized Form State**

   ```typescript
   // Future: Optimized form performance for large questions
   import { useFormContext } from "react-hook-form";

   function OptimizedPairEditor({ index }: { index: number }) {
     // Only re-render specific pair on change
     // Debounced validation
     // Minimal re-renders
   }
   ```

### Scalability Considerations

#### Component Scalability

1. **Modular Architecture**

   ```
   Matching Question System:
   ├── Core Components (MatchingDisplay, MatchingEditor)
   ├── Specialized Variants (DragDropMatching, MediaMatching)
   ├── Shared Utilities (validation, type guards)
   └── Extension Points (custom question types)
   ```

2. **Type System Evolution**

   ```typescript
   // Extensible type system for future question types
   interface BaseMatchingData {
     question_text: string;
     explanation?: string;
   }

   // Different matching implementations can extend base
   interface StandardMatchingData extends BaseMatchingData {
     pairs: MatchingPair[];
     distractors?: string[];
   }

   interface CategoryMatchingData extends BaseMatchingData {
     categories: MatchingCategory[];
   }
   ```

#### Database Scalability

- **JSONB Storage**: Current polymorphic storage scales to millions of questions
- **Indexing Strategy**: Can add specialized indexes for matching question queries
- **Query Optimization**: Existing query patterns support complex matching operations

#### Bundle Size Management

```typescript
// Future: Dynamic imports for question types
const questionComponents = {
  multiple_choice: () => import("./MCQDisplay"),
  fill_in_blank: () => import("./FillInBlankDisplay"),
  matching: () => import("./MatchingDisplay"), // Loaded on demand
};

// Code splitting by question type usage
function DynamicQuestionDisplay({ questionType, ...props }) {
  const [Component, setComponent] = useState(null);

  useEffect(() => {
    questionComponents[questionType]().then((module) => {
      setComponent(() => module.default);
    });
  }, [questionType]);

  return Component ? <Component {...props} /> : <LoadingDisplay />;
}
```

### Extension Points for Future Development

#### Plugin Architecture

```typescript
// Future: Plugin system for custom question types
interface QuestionTypePlugin {
  type: string;
  displayName: string;
  displayComponent: ComponentType<BaseQuestionDisplayProps>;
  editorComponent: ComponentType<BaseQuestionEditorProps>;
  validationSchema: ZodSchema;
  typeGuard: (data: unknown) => boolean;
}

// Plugin registration system
const questionTypeRegistry = new Map<string, QuestionTypePlugin>();

export function registerQuestionType(plugin: QuestionTypePlugin) {
  questionTypeRegistry.set(plugin.type, plugin);
}
```

#### API Evolution Strategy

```typescript
// Versioned API support for backward compatibility
interface MatchingDataV1 {
  // Current implementation
  question_text: string;
  pairs: MatchingPair[];
  distractors?: string[];
}

interface MatchingDataV2 {
  // Future enhanced version
  question_text: string;
  pairs: EnhancedMatchingPair[]; // With weights, media, etc.
  categories?: MatchingCategory[];
  scoring?: MatchingScoringConfig;
}

// Migration strategy
function migrateMatchingData(data: MatchingDataV1): MatchingDataV2 {
  // Automatic migration for backward compatibility
}
```

#### Accessibility Enhancements

```typescript
// Future: Enhanced accessibility features
interface AccessibleMatchingProps {
  // Screen reader support
  ariaLabels: {
    questionColumn: string;
    answerColumn: string;
    matchInstruction: string;
  };

  // Keyboard navigation
  keyboardShortcuts: boolean;

  // High contrast mode
  highContrast: boolean;

  // Alternative input methods
  alternativeInput: "keyboard" | "voice" | "switch";
}
```

### Migration Path for Future Enhancements

#### Backward Compatibility Strategy

1. **Additive Changes Only**

   ```typescript
   // New features extend existing interfaces
   interface EnhancedMatchingData extends MatchingData {
     // New optional fields don't break existing data
     categories?: MatchingCategory[];
     weights?: number[];
   }
   ```

2. **Graceful Degradation**

   ```typescript
   // Future components handle legacy data
   function EnhancedMatchingDisplay({ question }: Props) {
     const data = extractQuestionData(question, "matching");

     // Detect data version and render appropriately
     if (isLegacyMatchingData(data)) {
       return <LegacyMatchingView data={data} />;
     }

     return <EnhancedMatchingView data={data} />;
   }
   ```

3. **Incremental Migration**
   ```typescript
   // Database migration strategy
   function upgradeMatchingQuestion(oldData: MatchingDataV1): MatchingDataV2 {
     return {
       ...oldData,
       // Add new fields with sensible defaults
       categories: null,
       weights: oldData.pairs.map(() => 1), // Equal weights
     };
   }
   ```

---

## Implementation Checklist

- [ ] **Step 1**: Update constants (QUESTION_TYPES, QUESTION_TYPE_LABELS)
- [ ] **Step 2**: Define MatchingData interface and type guards
- [ ] **Step 3**: Add matchingSchema with Zod validation
- [ ] **Step 4**: Create MatchingDisplay.tsx component
- [ ] **Step 5**: Create MatchingEditor.tsx component
- [ ] **Step 6**: Update router components (QuestionDisplay, QuestionEditor)
- [ ] **Step 7**: Add matching option to QuizSettingsStep.tsx
- [ ] **Step 8**: Update export files and test TypeScript compilation
- [ ] **Step 9**: Manual testing of complete workflow
- [ ] **Step 10**: Deployment and monitoring setup

### After Each Step

1. **Run TypeScript Check**: `npx tsc --noEmit`
2. **Commit Changes**: `git add -A && git commit -m "descriptive message"`
3. **Test Functionality**: Manual verification of component behavior

---

**Remember**: This implementation maintains full compatibility with the existing system while adding comprehensive matching question support. The polymorphic architecture makes it easy to add additional question types in the future following the same patterns.

_End of Implementation Document_
