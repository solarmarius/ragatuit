# Frontend Implementation Guide: Categorization Question Type Support

**Document Date**: January 23, 2025
**Feature**: Frontend Categorization Question Type Support
**Target System**: Rag@UiT Canvas LMS Quiz Generator Frontend
**Author**: Implementation Guide

## 1. Feature Overview

### What It Does

The Categorization Question Type frontend implementation adds comprehensive user interface support for categorization questions in the Rag@UiT quiz generator. This feature allows instructors to:

- **Create Categorization Questions**: Through the quiz creation interface, selecting categorization as a question type
- **Review Generated Questions**: View AI-generated categorization questions with proper visual formatting
- **Edit Question Content**: Modify categories, items, distractors, and explanations through a user-friendly interface
- **Visual Question Display**: See categorization questions rendered with clear category-item organization

### Business Value

- **Enhanced Question Variety**: Expands quiz creation beyond Multiple Choice, Fill-in-Blank, and Matching questions
- **Improved Assessment Tools**: Provides instructors with diverse question types for comprehensive evaluation
- **Seamless Integration**: Works within existing quiz creation and review workflows without disrupting user experience
- **AI-Powered Generation**: Leverages existing AI question generation for automatic categorization question creation

### User Benefits

- **Instructors**: Can create engaging categorization exercises that test taxonomic knowledge and conceptual organization
- **Students**: Experience diverse question types that assess classification skills and categorical thinking
- **Canvas Integration**: Questions export directly to Canvas LMS without manual formatting or conversion

### Technical Context

This implementation builds upon the existing polymorphic question system in the frontend. The backend already supports categorization questions with AI templates for both English and Norwegian, making this purely a frontend integration task.

## 2. Technical Architecture

### High-Level Architecture

The categorization question type follows the established polymorphic question architecture:

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
│  ├── MatchingDisplay        │  ├── MatchingEditor           │
│  └── CategorizationDisplay  │  └── CategorizationEditor     │
│      ←NEW                   │      ←NEW                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Type System Foundation                    │
├─────────────────────────────────────────────────────────────┤
│  Question Types:                                            │
│  ├── Constants (QUESTION_TYPES.CATEGORIZATION)             │
│  ├── TypeScript Interfaces (CategorizationData)            │
│  ├── Runtime Validation (Zod Schemas)                      │
│  └── Type Guards (isCategorizationData)                    │
└─────────────────────────────────────────────────────────────┘
```

### System Integration

The categorization question type integrates with existing systems:

- **State Management**: Uses TanStack Query for server state, React Hook Form for local form state
- **UI Framework**: Built with Chakra UI components for consistency with existing interface
- **Validation**: Leverages Zod for runtime validation and TypeScript for compile-time safety
- **API Integration**: Uses auto-generated API client from backend OpenAPI specification
- **Error Handling**: Implements established error boundary and fallback component patterns

### Component Interaction Flow

```
User Workflow:
1. Quiz Creation → Select "Categorization" question type
2. AI Generation → Backend generates categorization questions
3. Question Review → CategorizationDisplay shows generated questions
4. Question Editing → CategorizationEditor allows modifications
5. Quiz Export → Questions export to Canvas in proper format

Data Flow:
API Response → Type Validation → Component Routing → UI Rendering
     ↓              ↓               ↓               ↓
QuestionResponse → extractQuestionData → QuestionDisplay → CategorizationDisplay
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

The backend must be running with categorization question type support (already implemented):

- Categorization question type registered in question type registry
- AI templates available for both English and Norwegian
- Canvas export functionality for categorization questions
- Database support for polymorphic question storage

## 4. Implementation Details

### 4.1 File Structure

```
frontend/src/
├── lib/
│   ├── constants/
│   │   └── index.ts                    # ← UPDATE: Add CATEGORIZATION constants
│   └── validation/
│       └── questionSchemas.ts          # ← UPDATE: Add categorization validation
├── types/
│   └── questionTypes.ts                # ← UPDATE: Add CategorizationData interface
├── components/
│   ├── Questions/
│   │   ├── display/
│   │   │   ├── CategorizationDisplay.tsx     # ← CREATE: New display component
│   │   │   ├── QuestionDisplay.tsx           # ← UPDATE: Add categorization case
│   │   │   └── index.ts                      # ← UPDATE: Export CategorizationDisplay
│   │   └── editors/
│   │       ├── CategorizationEditor.tsx      # ← CREATE: New editor component
│   │       ├── QuestionEditor.tsx            # ← UPDATE: Add categorization case
│   │       └── index.ts                      # ← UPDATE: Export CategorizationEditor
│   └── QuizCreation/
│       └── QuizSettingsStep.tsx              # ← UPDATE: Add categorization option
```

### 4.2 Step-by-Step Implementation

#### Step 1: Update Constants and Configuration

**File**: `frontend/src/lib/constants/index.ts`

**Changes**: Add categorization to the existing question type constants

```typescript
// Find the QUESTION_TYPES constant and add categorization
export const QUESTION_TYPES = {
  MULTIPLE_CHOICE: "multiple_choice",
  FILL_IN_BLANK: "fill_in_blank",
  MATCHING: "matching",
  CATEGORIZATION: "categorization", // ← ADD THIS LINE
} as const;

// Find the QUESTION_TYPE_LABELS constant and add categorization
export const QUESTION_TYPE_LABELS = {
  multiple_choice: "Multiple Choice",
  fill_in_blank: "Fill in the Blank",
  matching: "Matching",
  categorization: "Categorization", // ← ADD THIS LINE
} as const;
```

**Purpose**: These constants ensure type safety and provide consistent labels throughout the application.

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

**Commit**: `git add -A && git commit -m "feat: add categorization constants to frontend"`

#### Step 2: Define Type System

**File**: `frontend/src/types/questionTypes.ts`

Add the categorization data interface and update the discriminated union:

```typescript
// Add after the existing MatchingData interface
/**
 * Data structure for categorization questions.
 * Students categorize items by placing them into appropriate categories.
 */
export interface CategorizationData {
  question_text: string;
  categories: Array<{
    id: string;
    name: string;
    correct_items: string[]; // IDs of items that belong to this category
  }>;
  items: Array<{
    id: string;
    text: string;
  }>;
  distractors?: Array<{
    id: string;
    text: string;
  }> | null; // Optional incorrect items that don't belong to any category
  explanation?: string | null;
}

// Update the discriminated union to include categorization
export type QuestionData =
  | ({ type: "multiple_choice" } & MCQData)
  | ({ type: "fill_in_blank" } & FillInBlankData)
  | ({ type: "matching" } & MatchingData)
  | ({ type: "categorization" } & CategorizationData); // ← ADD THIS LINE

// Update the TypedQuestionResponse to include categorization
export interface TypedQuestionResponse<T extends QuestionType = QuestionType> {
  id: string;
  quiz_id: string;
  question_type: T;
  question_data: T extends "multiple_choice"
    ? MCQData
    : T extends "fill_in_blank"
      ? FillInBlankData
      : T extends "matching"
        ? MatchingData
        : T extends "categorization" // ← ADD THIS LINE
          ? CategorizationData // ← ADD THIS LINE
          : never;
  difficulty?: QuestionDifficulty | null;
  tags?: string[] | null;
  is_approved: boolean;
  approved_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  canvas_item_id?: string | null;
}

// Add type guard for runtime validation
export function isCategorizationData(data: unknown): data is CategorizationData {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const obj = data as Record<string, unknown>;

  // Validate required fields
  if (typeof obj.question_text !== "string") {
    return false;
  }

  // Validate categories array
  if (!Array.isArray(obj.categories) || obj.categories.length < 2 || obj.categories.length > 8) {
    return false;
  }

  // Validate each category structure
  for (const category of obj.categories) {
    if (
      typeof category !== "object" ||
      category === null ||
      typeof (category as any).id !== "string" ||
      typeof (category as any).name !== "string" ||
      !Array.isArray((category as any).correct_items)
    ) {
      return false;
    }
  }

  // Validate items array
  if (!Array.isArray(obj.items) || obj.items.length < 6 || obj.items.length > 20) {
    return false;
  }

  // Validate each item structure
  for (const item of obj.items) {
    if (
      typeof item !== "object" ||
      item === null ||
      typeof (item as any).id !== "string" ||
      typeof (item as any).text !== "string"
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
      if (
        typeof distractor !== "object" ||
        distractor === null ||
        typeof (distractor as any).id !== "string" ||
        typeof (distractor as any).text !== "string"
      ) {
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

// Update extractQuestionData function to handle categorization
export function extractQuestionData<T extends QuestionType>(
  question: QuestionResponse,
  type: T
): TypedQuestionResponse<T>["question_data"] {
  if (question.question_type !== type) {
    throw new Error(`Expected ${type} question, got ${question.question_type}`);
  }

  const data = question.question_data;

  switch (type) {
    case "multiple_choice":
      if (!isMCQData(data)) {
        throw new Error("Invalid MCQ question data structure");
      }
      return data as unknown as TypedQuestionResponse<T>["question_data"];
    case "fill_in_blank":
      if (!isFillInBlankData(data)) {
        throw new Error("Invalid Fill in Blank question data structure");
      }
      return data as unknown as TypedQuestionResponse<T>["question_data"];
    case "matching":
      if (!isMatchingData(data)) {
        throw new Error("Invalid Matching question data structure");
      }
      return data as unknown as TypedQuestionResponse<T>["question_data"];
    case "categorization": // ← ADD THIS CASE
      if (!isCategorizationData(data)) {
        throw new Error("Invalid Categorization question data structure");
      }
      return data as unknown as TypedQuestionResponse<T>["question_data"];
    default: {
      // TypeScript exhaustiveness check - this should never happen
      const _exhaustiveCheck: never = type;
      throw new Error(`Unsupported question type: ${String(_exhaustiveCheck)}`);
    }
  }
}

// Add specific typed question response type
export type CategorizationQuestionResponse = TypedQuestionResponse<"categorization">;
```

**Purpose**: These type definitions provide compile-time safety and runtime validation for categorization question data.

**Key Points**:
- `CategorizationData` interface matches the backend data structure
- Type guard validates data at runtime to prevent errors
- Discriminated union enables exhaustive type checking
- Helper functions provide type-safe data extraction

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

**Commit**: `git add -A && git commit -m "feat: add categorization TypeScript interfaces and type guards"`

#### Step 3: Add Validation Schema

**File**: `frontend/src/lib/validation/questionSchemas.ts`

Add Zod schema for form validation:

```typescript
// Add after the existing matchingSchema

// Categorization form data interface
export interface CategorizationFormData {
  questionText: string;
  categories: Array<{
    name: string;
    correctItems: string[]; // Item IDs that belong to this category
  }>;
  items: Array<{
    text: string;
  }>;
  distractors?: Array<{
    text: string;
  }>;
  explanation?: string;
}

// Categorization validation schema
export const categorizationSchema = z
  .object({
    questionText: nonEmptyString,
    categories: z
      .array(
        z.object({
          name: nonEmptyString.min(1, "Category name is required"),
          correctItems: z
            .array(z.string())
            .min(1, "Each category must have at least one item"),
        })
      )
      .min(2, "At least 2 categories are required")
      .max(8, "Maximum 8 categories allowed")
      .refine(
        (categories) => {
          // Check for duplicate category names
          const names = categories.map((c) => c.name.toLowerCase().trim());
          return new Set(names).size === names.length;
        },
        { message: "Duplicate category names are not allowed" }
      ),
    items: z
      .array(
        z.object({
          text: nonEmptyString.min(1, "Item text is required"),
        })
      )
      .min(6, "At least 6 items are required")
      .max(20, "Maximum 20 items allowed")
      .refine(
        (items) => {
          // Check for duplicate item texts
          const texts = items.map((i) => i.text.toLowerCase().trim());
          return new Set(texts).size === texts.length;
        },
        { message: "Duplicate item texts are not allowed" }
      ),
    distractors: z
      .array(
        z.object({
          text: nonEmptyString.min(1, "Distractor text is required"),
        })
      )
      .max(5, "Maximum 5 distractors allowed")
      .optional()
      .refine(
        (distractors) => {
          if (!distractors) return true;
          // Check for duplicate distractor texts
          const texts = distractors.map((d) => d.text.toLowerCase().trim());
          return new Set(texts).size === texts.length;
        },
        { message: "Duplicate distractor texts are not allowed" }
      ),
    explanation: optionalString,
  })
  .refine(
    (data) => {
      // Validate that all items are assigned to categories
      const totalAssignedItems = data.categories.reduce(
        (sum, cat) => sum + cat.correctItems.length,
        0
      );
      return totalAssignedItems === data.items.length;
    },
    {
      message: "All items must be assigned to categories",
      path: ["categories"],
    }
  )
  .refine(
    (data) => {
      // Ensure distractors don't match any item texts
      if (!data.distractors) return true;

      const itemTexts = new Set(data.items.map((i) => i.text.toLowerCase().trim()));

      for (const distractor of data.distractors) {
        if (itemTexts.has(distractor.text.toLowerCase().trim())) {
          return false;
        }
      }

      return true;
    },
    {
      message: "Distractors cannot match any item texts",
      path: ["distractors"],
    }
  );

// Update getSchemaByType function
export function getSchemaByType(questionType: QuestionType): z.ZodSchema<any> {
  switch (questionType) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return mcqSchema;
    case QUESTION_TYPES.FILL_IN_BLANK:
      return fillInBlankSchema;
    case QUESTION_TYPES.MATCHING:
      return matchingSchema;
    case QUESTION_TYPES.CATEGORIZATION: // ← ADD THIS CASE
      return categorizationSchema;
    default:
      throw new Error(`No schema defined for question type: ${questionType}`);
  }
}

// Update FormDataByType to include categorization
export type FormDataByType<T extends QuestionType> =
  T extends typeof QUESTION_TYPES.MULTIPLE_CHOICE
    ? MCQFormData
    : T extends typeof QUESTION_TYPES.FILL_IN_BLANK
      ? FillInBlankFormData
      : T extends typeof QUESTION_TYPES.MATCHING
        ? MatchingFormData
        : T extends typeof QUESTION_TYPES.CATEGORIZATION // ← ADD THIS LINE
          ? CategorizationFormData // ← ADD THIS LINE
          : never;
```

**Purpose**: Provides comprehensive form validation with business rules and user-friendly error messages.

**Validation Rules**:
- 2-8 categories required
- 6-20 items required
- Each category must have at least 1 item
- No duplicate category names or item texts
- Maximum 5 distractors
- Distractors cannot match item texts
- All items must be assigned to categories

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

**Commit**: `git add -A && git commit -m "feat: add categorization validation schema"`

#### Step 4: Create Display Component

**File**: `frontend/src/components/Questions/display/CategorizationDisplay.tsx`

Complete display component following established patterns:

```typescript
import { memo } from "react";
import { Box, VStack, Text, SimpleGrid, Badge, Card } from "@chakra-ui/react";
import type { QuestionResponse } from "@/client";
import { extractQuestionData } from "@/types/questionTypes";
import { ExplanationBox } from "../shared/ExplanationBox";
import { ErrorDisplay } from "./ErrorDisplay";

interface CategorizationDisplayProps {
  question: QuestionResponse;
  showCorrectAnswer?: boolean;
  showExplanation?: boolean;
}

/**
 * Display component for categorization questions.
 * Shows categories with their assigned items and optional distractors.
 */
function CategorizationDisplayComponent({
  question,
  showCorrectAnswer: _showCorrectAnswer = false, // Always show answers in teacher-facing view
  showExplanation = false,
}: CategorizationDisplayProps) {
  // Note: showCorrectAnswer is kept for API consistency but we always show answers for teachers
  try {
    const categorizationData = extractQuestionData(question, "categorization");

    return (
      <VStack gap={6} align="stretch">
        {/* Question Text */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {categorizationData.question_text}
          </Text>
        </Box>

        {/* Categories Display */}
        <Box>
          <Text fontSize="sm" fontWeight="semibold" color="gray.600" mb={4}>
            Categories:
          </Text>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4} mb={6}>
            {categorizationData.categories.map((category) => (
              <Card.Root key={category.id} variant="outline">
                <Card.Header>
                  <Text fontSize="sm" fontWeight="semibold">
                    {category.name}
                  </Text>
                </Card.Header>
                <Card.Body>
                  <VStack gap={2} align="stretch">
                    {category.correct_items.map((itemId) => {
                      const item = categorizationData.items.find((i) => i.id === itemId);
                      return item ? (
                        <Box
                          key={itemId}
                          p={2}
                          bg="green.50"
                          borderRadius="sm"
                          borderLeft="3px solid"
                          borderColor="green.300"
                        >
                          <Text fontSize="sm">{item.text}</Text>
                        </Box>
                      ) : null;
                    })}
                  </VStack>
                </Card.Body>
              </Card.Root>
            ))}
          </SimpleGrid>
        </Box>

        {/* Distractors */}
        {categorizationData.distractors && categorizationData.distractors.length > 0 && (
          <Box>
            <Text fontSize="sm" fontWeight="semibold" color="gray.600" mb={3}>
              Distractors:
            </Text>
            <SimpleGrid columns={{ base: 2, md: 3, lg: 4 }} gap={3}>
              {categorizationData.distractors.map((distractor) => (
                <Box
                  key={distractor.id}
                  p={3}
                  borderWidth={1}
                  borderRadius="md"
                  borderColor="red.200"
                  bg="red.50"
                  position="relative"
                >
                  <Text fontSize="sm" textAlign="center">
                    {distractor.text}
                  </Text>
                  <Badge
                    position="absolute"
                    top={1}
                    right={1}
                    size="sm"
                    colorScheme="red"
                  >
                    Distractor
                  </Badge>
                </Box>
              ))}
            </SimpleGrid>
          </Box>
        )}

        {/* Explanation */}
        {showExplanation && categorizationData.explanation && (
          <ExplanationBox explanation={categorizationData.explanation} />
        )}
      </VStack>
    );
  } catch (error) {
    console.error("Error rendering categorization question:", error);
    return <ErrorDisplay error="Error loading categorization question data" />;
  }
}

/**
 * Memoized categorization display component for performance optimization.
 */
export const CategorizationDisplay = memo(CategorizationDisplayComponent);
CategorizationDisplay.displayName = "CategorizationDisplay";
```

**Purpose**: Renders categorization questions optimized for teacher review and verification.

**Key Features**:
- **Category cards**: Always display correct items organized by category with green highlighting
- **Distractors section**: Only shows incorrect items that don't belong to any category (conditional rendering)
- **Teacher-focused design**: Eliminates redundant information for cleaner instructor workflow
- **Visual clarity**: Red color coding and "Distractor" badges for easy identification
- **Responsive grid layout**: Adapts to different screen sizes with proper spacing
- **Error boundary**: Fallback component handles malformed question data gracefully

**UI Improvements Made**:
- **Removed redundant "Correct Categorization" summary** that duplicated category card information
- **Simplified distractors display** to show only when distractors exist in the question
- **Eliminated mixed item pool** that confused correct items with distractors
- **Maintained API consistency** with `showCorrectAnswer` prop while optimizing for teacher use

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

**Commit**: `git add -A && git commit -m "feat: add CategorizationDisplay component"`

#### Step 5: Create Editor Component

**File**: `frontend/src/components/Questions/editors/CategorizationEditor.tsx`

Complete editor component with form management:

```typescript
import { memo, useCallback } from "react";
import {
  VStack,
  HStack,
  Button,
  Text,
  Box,
  SimpleGrid,
  Card,
  IconButton,
  Textarea,
  Input,
  Select,
} from "@chakra-ui/react";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { MdAdd, MdDelete } from "react-icons/md";
import type { QuestionResponse, QuestionUpdateRequest } from "@/client";
import { extractQuestionData } from "@/types/questionTypes";
import type { CategorizationFormData } from "@/lib/validation/questionSchemas";
import { categorizationSchema } from "@/lib/validation/questionSchemas";
import { FormField, FormGroup } from "@/components/forms";
import { ErrorEditor } from "./ErrorEditor";

interface CategorizationEditorProps {
  question: QuestionResponse;
  onSave: (updateData: QuestionUpdateRequest) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

/**
 * Editor component for categorization questions.
 * Allows editing of categories, items, item assignments, distractors, and explanation.
 */
function CategorizationEditorComponent({
  question,
  onSave,
  onCancel,
  isLoading = false,
}: CategorizationEditorProps) {
  try {
    const categorizationData = extractQuestionData(question, "categorization");

    // Transform backend data to form data format
    const defaultFormData: CategorizationFormData = {
      questionText: categorizationData.question_text,
      categories: categorizationData.categories.map((cat) => ({
        name: cat.name,
        correctItems: cat.correct_items,
      })),
      items: categorizationData.items.map((item) => ({
        text: item.text,
      })),
      distractors: categorizationData.distractors?.map((dist) => ({
        text: dist.text,
      })) || [],
      explanation: categorizationData.explanation || "",
    };

    const {
      control,
      handleSubmit,
      watch,
      formState: { errors, isDirty },
    } = useForm<CategorizationFormData>({
      resolver: zodResolver(categorizationSchema),
      defaultValues: defaultFormData,
    });

    // Field arrays for dynamic management
    const {
      fields: categoryFields,
      append: appendCategory,
      remove: removeCategory,
    } = useFieldArray({
      control,
      name: "categories",
    });

    const {
      fields: itemFields,
      append: appendItem,
      remove: removeItem,
    } = useFieldArray({
      control,
      name: "items",
    });

    const {
      fields: distractorFields,
      append: appendDistractor,
      remove: removeDistractor,
    } = useFieldArray({
      control,
      name: "distractors",
    });

    // Watch current form values for item assignment
    const watchedCategories = watch("categories");
    const watchedItems = watch("items");

    // Handle form submission
    const onSubmit = useCallback(
      (formData: CategorizationFormData) => {
        // Transform form data back to backend format
        const updateData: QuestionUpdateRequest = {
          question_data: {
            question_text: formData.questionText,
            categories: formData.categories.map((cat, index) => ({
              id: `cat_${index}`, // Generate IDs for new categories
              name: cat.name,
              correct_items: cat.correctItems,
            })),
            items: formData.items.map((item, index) => ({
              id: `item_${index}`, // Generate IDs for new items
              text: item.text,
            })),
            distractors: formData.distractors?.length
              ? formData.distractors.map((dist, index) => ({
                  id: `dist_${index}`, // Generate IDs for new distractors
                  text: dist.text,
                }))
              : null,
            explanation: formData.explanation || null,
          },
        };
        onSave(updateData);
      },
      [onSave]
    );

    // Add new category
    const handleAddCategory = useCallback(() => {
      if (categoryFields.length < 8) {
        appendCategory({ name: "", correctItems: [] });
      }
    }, [appendCategory, categoryFields.length]);

    // Add new item
    const handleAddItem = useCallback(() => {
      if (itemFields.length < 20) {
        appendItem({ text: "" });
      }
    }, [appendItem, itemFields.length]);

    // Add new distractor
    const handleAddDistractor = useCallback(() => {
      if (distractorFields.length < 5) {
        appendDistractor({ text: "" });
      }
    }, [appendDistractor, distractorFields.length]);

    return (
      <Box as="form" onSubmit={handleSubmit(onSubmit)}>
        <VStack gap={8} align="stretch">
          {/* Question Text */}
          <FormField
            label="Question Text"
            isRequired
            invalid={!!errors.questionText}
            errorText={errors.questionText?.message}
          >
            <Controller
              name="questionText"
              control={control}
              render={({ field }) => (
                <Textarea
                  {...field}
                  placeholder="Enter instructions for the categorization question..."
                  rows={3}
                />
              )}
            />
          </FormField>

          {/* Categories Section */}
          <FormGroup>
            <HStack justify="space-between" mb={4}>
              <Text fontSize="md" fontWeight="semibold">
                Categories ({categoryFields.length}/8)
              </Text>
              <Button
                size="sm"
                leftIcon={<MdAdd />}
                onClick={handleAddCategory}
                isDisabled={categoryFields.length >= 8}
                colorScheme="blue"
                variant="outline"
              >
                Add Category
              </Button>
            </HStack>

            {errors.categories && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.categories.message}
              </Text>
            )}

            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
              {categoryFields.map((field, index) => (
                <Card.Root key={field.id} variant="outline">
                  <Card.Header>
                    <HStack justify="space-between">
                      <Text fontSize="sm" fontWeight="medium">
                        Category {index + 1}
                      </Text>
                      <IconButton
                        aria-label={`Remove category ${index + 1}`}
                        icon={<MdDelete />}
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => removeCategory(index)}
                        isDisabled={categoryFields.length <= 2}
                      />
                    </HStack>
                  </Card.Header>
                  <Card.Body>
                    <VStack gap={3} align="stretch">
                      <FormField
                        label="Category Name"
                        isRequired
                        invalid={!!errors.categories?.[index]?.name}
                        errorText={errors.categories?.[index]?.name?.message}
                      >
                        <Controller
                          name={`categories.${index}.name`}
                          control={control}
                          render={({ field: inputField }) => (
                            <Input
                              {...inputField}
                              placeholder="Enter category name..."
                              size="sm"
                            />
                          )}
                        />
                      </FormField>

                      <FormField
                        label="Assigned Items"
                        invalid={!!errors.categories?.[index]?.correctItems}
                        errorText={errors.categories?.[index]?.correctItems?.message}
                      >
                        <Controller
                          name={`categories.${index}.correctItems`}
                          control={control}
                          render={({ field: selectField }) => (
                            <Select.Root
                              {...selectField}
                              multiple
                              size="sm"
                              placeholder="Select items for this category..."
                            >
                              <Select.Trigger />
                              <Select.Content>
                                {watchedItems.map((item, itemIndex) => (
                                  <Select.Item
                                    key={itemIndex}
                                    value={`item_${itemIndex}`}
                                  >
                                    {item.text || `Item ${itemIndex + 1}`}
                                  </Select.Item>
                                ))}
                              </Select.Content>
                            </Select.Root>
                          )}
                        />
                      </FormField>
                    </VStack>
                  </Card.Body>
                </Card.Root>
              ))}
            </SimpleGrid>

            <Text fontSize="sm" color="gray.600" mt={2}>
              At least 2 categories required, maximum 8 categories allowed.
            </Text>
          </FormGroup>

          {/* Items Section */}
          <FormGroup>
            <HStack justify="space-between" mb={4}>
              <Text fontSize="md" fontWeight="semibold">
                Items ({itemFields.length}/20)
              </Text>
              <Button
                size="sm"
                leftIcon={<MdAdd />}
                onClick={handleAddItem}
                isDisabled={itemFields.length >= 20}
                colorScheme="blue"
                variant="outline"
              >
                Add Item
              </Button>
            </HStack>

            {errors.items && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.items.message}
              </Text>
            )}

            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
              {itemFields.map((field, index) => (
                <Card.Root key={field.id} variant="outline" size="sm">
                  <Card.Body>
                    <HStack>
                      <Box flex={1}>
                        <FormField
                          label={`Item ${index + 1}`}
                          isRequired
                          invalid={!!errors.items?.[index]?.text}
                          errorText={errors.items?.[index]?.text?.message}
                        >
                          <Controller
                            name={`items.${index}.text`}
                            control={control}
                            render={({ field: inputField }) => (
                              <Input
                                {...inputField}
                                placeholder="Enter item text..."
                                size="sm"
                              />
                            )}
                          />
                        </FormField>
                      </Box>
                      <IconButton
                        aria-label={`Remove item ${index + 1}`}
                        icon={<MdDelete />}
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => removeItem(index)}
                        isDisabled={itemFields.length <= 6}
                        alignSelf="flex-end"
                        mb={2}
                      />
                    </HStack>
                  </Card.Body>
                </Card.Root>
              ))}
            </SimpleGrid>

            <Text fontSize="sm" color="gray.600" mt={2}>
              At least 6 items required, maximum 20 items allowed.
            </Text>
          </FormGroup>

          {/* Distractors Section */}
          <FormGroup>
            <HStack justify="space-between" mb={4}>
              <Text fontSize="md" fontWeight="semibold">
                Distractors ({distractorFields.length}/5)
              </Text>
              <Button
                size="sm"
                leftIcon={<MdAdd />}
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

            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
              {distractorFields.map((field, index) => (
                <Card.Root key={field.id} variant="outline" size="sm">
                  <Card.Body>
                    <HStack>
                      <Box flex={1}>
                        <FormField
                          label={`Distractor ${index + 1}`}
                          invalid={!!errors.distractors?.[index]?.text}
                          errorText={errors.distractors?.[index]?.text?.message}
                        >
                          <Controller
                            name={`distractors.${index}.text`}
                            control={control}
                            render={({ field: inputField }) => (
                              <Input
                                {...inputField}
                                placeholder="Enter distractor text..."
                                size="sm"
                              />
                            )}
                          />
                        </FormField>
                      </Box>
                      <IconButton
                        aria-label={`Remove distractor ${index + 1}`}
                        icon={<MdDelete />}
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => removeDistractor(index)}
                        alignSelf="flex-end"
                        mb={2}
                      />
                    </HStack>
                  </Card.Body>
                </Card.Root>
              ))}
            </SimpleGrid>

            <Text fontSize="sm" color="gray.600" mt={2}>
              Optional incorrect items that don't belong to any category. Maximum 5 allowed.
            </Text>
          </FormGroup>

          {/* Explanation */}
          <FormField
            label="Explanation (Optional)"
            invalid={!!errors.explanation}
            errorText={errors.explanation?.message}
          >
            <Controller
              name="explanation"
              control={control}
              render={({ field }) => (
                <Textarea
                  {...field}
                  placeholder="Optional explanation for the correct categorization..."
                  rows={3}
                />
              )}
            />
          </FormField>

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
    console.error("Error rendering categorization question editor:", error);
    return (
      <ErrorEditor
        error="Error loading question data for editing"
        onCancel={onCancel}
      />
    );
  }
}

/**
 * Memoized categorization editor component for performance optimization.
 */
export const CategorizationEditor = memo(CategorizationEditorComponent);
CategorizationEditor.displayName = "CategorizationEditor";
```

**Purpose**: Provides comprehensive editing interface for categorization questions with validation and dynamic field management.

**Key Features**:
- Dynamic category management (add/remove, 2-8 limit)
- Dynamic item management (add/remove, 6-20 limit)
- Item-to-category assignment interface
- Dynamic distractor management (add/remove, 0-5 limit)
- Form validation with Zod schema integration
- React Hook Form for optimal performance
- Visual feedback for errors and requirements
- Disabled states for limits and validation

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

**Commit**: `git add -A && git commit -m "feat: add CategorizationEditor component"`

#### Step 6: Update Router Components

**File**: `frontend/src/components/Questions/display/QuestionDisplay.tsx`

Add categorization case to the switch statement:

```typescript
import { memo } from "react";

import type { QuestionResponse } from "@/client";
import { QUESTION_TYPES } from "@/lib/constants";
import { FillInBlankDisplay } from "./FillInBlankDisplay";
import { MatchingDisplay } from "./MatchingDisplay";
import { CategorizationDisplay } from "./CategorizationDisplay"; // ← ADD THIS IMPORT
import { MCQDisplay } from "./MCQDisplay";
import { UnsupportedDisplay } from "./UnsupportedDisplay";

interface QuestionDisplayProps {
  question: QuestionResponse;
  showCorrectAnswer?: boolean;
  showExplanation?: boolean;
}

export const QuestionDisplay = memo(function QuestionDisplay({
  question,
  showCorrectAnswer = false,
  showExplanation = false,
}: QuestionDisplayProps) {
  const commonProps = {
    question,
    showCorrectAnswer,
    showExplanation,
  };

  switch (question.question_type) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return <MCQDisplay {...commonProps} />;
    case QUESTION_TYPES.FILL_IN_BLANK:
      return <FillInBlankDisplay {...commonProps} />;
    case QUESTION_TYPES.MATCHING:
      return <MatchingDisplay {...commonProps} />;
    case QUESTION_TYPES.CATEGORIZATION: // ← ADD THIS CASE
      return <CategorizationDisplay {...commonProps} />;
    default:
      return <UnsupportedDisplay questionType={question.question_type} />;
  }
});
```

**File**: `frontend/src/components/Questions/editors/QuestionEditor.tsx`

Add categorization case to the switch statement:

```typescript
import { memo } from "react";

import type { QuestionResponse, QuestionUpdateRequest } from "@/client";
import { QUESTION_TYPES } from "@/lib/constants";
import { FillInBlankEditor } from "./FillInBlankEditor";
import { MatchingEditor } from "./MatchingEditor";
import { CategorizationEditor } from "./CategorizationEditor"; // ← ADD THIS IMPORT
import { MCQEditor } from "./MCQEditor";
import { UnsupportedEditor } from "./UnsupportedEditor";

interface QuestionEditorProps {
  question: QuestionResponse;
  onSave: (updateData: QuestionUpdateRequest) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export const QuestionEditor = memo(function QuestionEditor({
  question,
  onSave,
  onCancel,
  isLoading = false,
}: QuestionEditorProps) {
  const commonProps = {
    question,
    onSave,
    onCancel,
    isLoading,
  };

  switch (question.question_type) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return <MCQEditor {...commonProps} />;
    case QUESTION_TYPES.FILL_IN_BLANK:
      return <FillInBlankEditor {...commonProps} />;
    case QUESTION_TYPES.MATCHING:
      return <MatchingEditor {...commonProps} />;
    case QUESTION_TYPES.CATEGORIZATION: // ← ADD THIS CASE
      return <CategorizationEditor {...commonProps} />;
    default:
      return (
        <UnsupportedEditor
          questionType={question.question_type}
          onCancel={onCancel}
        />
      );
  }
});
```

**Purpose**: Integrates categorization components into the polymorphic router system.

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

**Commit**: `git add -A && git commit -m "feat: add categorization support to router components"`

#### Step 7: Update Export Files

**File**: `frontend/src/components/Questions/display/index.ts`

Add categorization display export:

```typescript
export * from "./QuestionDisplay";
export * from "./MCQDisplay";
export * from "./FillInBlankDisplay";
export * from "./MatchingDisplay";
export * from "./CategorizationDisplay"; // ← ADD THIS LINE
export * from "./UnsupportedDisplay";
export * from "./ErrorDisplay";
```

**File**: `frontend/src/components/Questions/editors/index.ts`

Add categorization editor export:

```typescript
export * from "./QuestionEditor";
export * from "./MCQEditor";
export * from "./FillInBlankEditor";
export * from "./MatchingEditor";
export * from "./CategorizationEditor"; // ← ADD THIS LINE
export * from "./UnsupportedEditor";
export * from "./ErrorEditor";
```

**Purpose**: Makes categorization components available for import throughout the application.

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

**Commit**: `git add -A && git commit -m "feat: add categorization component exports"`

#### Step 8: Add Quiz Creation Option

**File**: `frontend/src/components/QuizCreation/QuizSettingsStep.tsx`

Add categorization option to the question type selection:

```typescript
// Find the questionTypeOptions array and add categorization
const questionTypeOptions = [
  {
    value: QUESTION_TYPES.MULTIPLE_CHOICE,
    label: "Multiple Choice Questions",
    description: "Generate questions with multiple answer options",
  },
  {
    value: QUESTION_TYPES.FILL_IN_BLANK,
    label: "Fill in the Blank",
    description: "Generate questions with blank spaces to fill in",
  },
  {
    value: QUESTION_TYPES.MATCHING,
    label: "Matching Questions",
    description: "Generate matching questions with pairs and distractors",
  },
  { // ← ADD THIS OBJECT
    value: QUESTION_TYPES.CATEGORIZATION,
    label: "Categorization Questions",
    description: "Generate questions where students categorize items into groups",
  },
];
```

**Purpose**: Allows users to select categorization as a question type during quiz creation.

**Testing**: Run `npx tsc --noEmit` to verify TypeScript compilation passes.

**Commit**: `git add -A && git commit -m "feat: add categorization option to quiz creation UI"`

### 4.3 Data Models & Schemas

#### Categorization Question Data Structure

```typescript
interface CategorizationData {
  question_text: string; // Main question instruction
  categories: Array<{
    id: string; // Unique identifier for the category
    name: string; // Category display name (1-100 characters)
    correct_items: string[]; // IDs of items that belong to this category (1-10 items)
  }>; // 2-8 categories required
  items: Array<{
    id: string; // Unique identifier for the item
    text: string; // Item display text (1-200 characters)
  }>; // 6-20 items required
  distractors?: Array<{
    id: string; // Unique identifier for the distractor
    text: string; // Distractor display text (1-200 characters)
  }> | null; // 0-5 optional distractors
  explanation?: string | null; // Optional explanation text
}
```

#### Form Data Structure

```typescript
interface CategorizationFormData {
  questionText: string;
  categories: Array<{
    name: string;
    correctItems: string[]; // Item indices that belong to this category
  }>;
  items: Array<{
    text: string;
  }>;
  distractors?: Array<{
    text: string;
  }>;
  explanation?: string;
}
```

#### Example Data

```json
{
  "question_text": "Categorize these animals by their biological classification.",
  "categories": [
    {
      "id": "cat_0",
      "name": "Mammals",
      "correct_items": ["item_0", "item_1"]
    },
    {
      "id": "cat_1",
      "name": "Birds",
      "correct_items": ["item_2", "item_3"]
    },
    {
      "id": "cat_2",
      "name": "Reptiles",
      "correct_items": ["item_4", "item_5"]
    }
  ],
  "items": [
    {"id": "item_0", "text": "Dolphin"},
    {"id": "item_1", "text": "Elephant"},
    {"id": "item_2", "text": "Eagle"},
    {"id": "item_3", "text": "Penguin"},
    {"id": "item_4", "text": "Snake"},
    {"id": "item_5", "text": "Lizard"}
  ],
  "distractors": [
    {"id": "dist_0", "text": "Jellyfish"},
    {"id": "dist_1", "text": "Coral"}
  ],
  "explanation": "These categories represent the main vertebrate animal classes based on biological characteristics."
}
```

#### Validation Rules

- **Categories**: 2-8 categories required
- **Category Names**: 1-100 characters, must be unique (case-insensitive)
- **Items**: 6-20 items required
- **Item Texts**: 1-200 characters, must be unique (case-insensitive)
- **Item Assignment**: Each item must be assigned to exactly one category
- **Distractors**: 0-5 optional, must be unique, cannot match any item text
- **Explanation**: Optional, can be null or empty string

### 4.4 Configuration

#### No Additional Configuration Required

The categorization question type uses existing application configuration:

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
import { isCategorizationData } from "@/types/questionTypes";

describe("isCategorizationData", () => {
  it("should return true for valid categorization data", () => {
    const validData = {
      question_text: "Categorize these programming concepts",
      categories: [
        {
          id: "cat1",
          name: "Data Structures",
          correct_items: ["item1", "item2"]
        },
        {
          id: "cat2",
          name: "Algorithms",
          correct_items: ["item3", "item4"]
        }
      ],
      items: [
        {id: "item1", text: "Array"},
        {id: "item2", text: "Linked List"},
        {id: "item3", text: "Binary Search"},
        {id: "item4", text: "Quick Sort"},
        {id: "item5", text: "Hash Table"},
        {id: "item6", text: "Merge Sort"}
      ],
      distractors: [
        {id: "dist1", text: "IDE"}
      ],
      explanation: "These represent fundamental computer science concepts."
    };

    expect(isCategorizationData(validData)).toBe(true);
  });

  it("should return false for insufficient categories", () => {
    const invalidData = {
      question_text: "Test",
      categories: [
        {id: "cat1", name: "Single Category", correct_items: ["item1"]}
      ], // Only 1 category, need 2 minimum
      items: [
        {id: "item1", text: "Item 1"},
        {id: "item2", text: "Item 2"},
        {id: "item3", text: "Item 3"},
        {id: "item4", text: "Item 4"},
        {id: "item5", text: "Item 5"},
        {id: "item6", text: "Item 6"}
      ]
    };

    expect(isCategorizationData(invalidData)).toBe(false);
  });

  it("should return false for insufficient items", () => {
    const invalidData = {
      question_text: "Test",
      categories: [
        {id: "cat1", name: "Category 1", correct_items: ["item1", "item2"]},
        {id: "cat2", name: "Category 2", correct_items: ["item3"]}
      ],
      items: [
        {id: "item1", text: "Item 1"},
        {id: "item2", text: "Item 2"},
        {id: "item3", text: "Item 3"}
      ] // Only 3 items, need 6 minimum
    };

    expect(isCategorizationData(invalidData)).toBe(false);
  });
});
```

#### Component Testing

```typescript
// Test file: src/components/Questions/display/__tests__/CategorizationDisplay.test.tsx
import { render, screen } from "@testing-library/react";
import { CategorizationDisplay } from "../CategorizationDisplay";
import type { QuestionResponse } from "@/client";

const mockCategorizationQuestion: QuestionResponse = {
  id: "test-id",
  question_type: "categorization",
  question_data: {
    question_text: "Categorize these animals by their habitat",
    categories: [
      {
        id: "cat1",
        name: "Land Animals",
        correct_items: ["item1", "item2"]
      },
      {
        id: "cat2",
        name: "Water Animals",
        correct_items: ["item3", "item4"]
      }
    ],
    items: [
      {id: "item1", text: "Elephant"},
      {id: "item2", text: "Lion"},
      {id: "item3", text: "Dolphin"},
      {id: "item4", text: "Shark"},
      {id: "item5", text: "Eagle"},
      {id: "item6", text: "Penguin"}
    ],
    distractors: [
      {id: "dist1", text: "Bacteria"}
    ],
    explanation: "Animals are categorized by their primary habitat."
  },
  quiz_id: "quiz-id",
  is_approved: false,
  created_at: "2025-01-23T10:00:00Z",
  updated_at: "2025-01-23T10:00:00Z",
};

describe("CategorizationDisplay", () => {
  it("renders question text and categories", () => {
    render(<CategorizationDisplay question={mockCategorizationQuestion} />);

    expect(
      screen.getByText("Categorize these animals by their habitat")
    ).toBeInTheDocument();
    expect(screen.getByText("Land Animals")).toBeInTheDocument();
    expect(screen.getByText("Water Animals")).toBeInTheDocument();
  });

  it("shows all items to categorize", () => {
    render(<CategorizationDisplay question={mockCategorizationQuestion} />);

    expect(screen.getByText("Elephant")).toBeInTheDocument();
    expect(screen.getByText("Lion")).toBeInTheDocument();
    expect(screen.getByText("Dolphin")).toBeInTheDocument();
    expect(screen.getByText("Shark")).toBeInTheDocument();
    expect(screen.getByText("Eagle")).toBeInTheDocument();
    expect(screen.getByText("Penguin")).toBeInTheDocument();
    expect(screen.getByText("Bacteria")).toBeInTheDocument();
  });

  it("shows correct categorization when showCorrectAnswer is true", () => {
    render(
      <CategorizationDisplay
        question={mockCategorizationQuestion}
        showCorrectAnswer={true}
      />
    );

    expect(screen.getByText("Correct Categorization:")).toBeInTheDocument();
    expect(screen.getByText("Land Animals:")).toBeInTheDocument();
    expect(screen.getByText("Water Animals:")).toBeInTheDocument();
    expect(screen.getByText("Distractors (don't belong to any category):")).toBeInTheDocument();
  });

  it("shows explanation when showExplanation is true", () => {
    render(
      <CategorizationDisplay
        question={mockCategorizationQuestion}
        showExplanation={true}
      />
    );

    expect(
      screen.getByText("Animals are categorized by their primary habitat.")
    ).toBeInTheDocument();
  });
});
```

### Integration Test Scenarios

#### Form Validation Integration

```typescript
// Test file: src/components/Questions/editors/__tests__/CategorizationEditor.integration.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CategorizationEditor } from "../CategorizationEditor";

describe("CategorizationEditor Integration", () => {
  const mockOnSave = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("validates minimum categories requirement", async () => {
    render(
      <CategorizationEditor
        question={mockCategorizationQuestion}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Try to remove category to get below minimum
    const removeBtns = screen.getAllByLabelText(/Remove category/);
    await userEvent.click(removeBtns[0]); // Should be disabled if only 2 categories

    expect(removeBtns[0]).toBeDisabled();
  });

  it("prevents duplicate category names", async () => {
    render(
      <CategorizationEditor
        question={mockCategorizationQuestion}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Set duplicate category name
    const categoryInputs = screen.getAllByPlaceholderText("Enter category name...");
    await userEvent.clear(categoryInputs[1]);
    await userEvent.type(categoryInputs[1], "Land Animals"); // Same as first category

    const saveBtn = screen.getByText("Save Changes");
    await userEvent.click(saveBtn);

    await waitFor(() => {
      expect(
        screen.getByText("Duplicate category names are not allowed")
      ).toBeInTheDocument();
    });

    expect(mockOnSave).not.toHaveBeenCalled();
  });

  it("saves valid form data", async () => {
    render(
      <CategorizationEditor
        question={mockCategorizationQuestion}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Modify question text
    const questionInput = screen.getByPlaceholderText(
      "Enter instructions for the categorization question..."
    );
    await userEvent.clear(questionInput);
    await userEvent.type(questionInput, "Updated question text");

    const saveBtn = screen.getByText("Save Changes");
    await userEvent.click(saveBtn);

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        question_data: {
          question_text: "Updated question text",
          categories: expect.arrayContaining([
            expect.objectContaining({
              id: expect.any(String),
              name: expect.any(String),
              correct_items: expect.any(Array),
            }),
          ]),
          items: expect.any(Array),
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
   2. Select "Categorization" question type
   3. Complete course and module selection
   4. Verify categorization questions are generated
   5. Check question display renders correctly
   ```

2. **Question Editing Flow**
   ```
   1. Open categorization question for editing
   2. Add/remove categories (test 2-8 limit)
   3. Add/remove items (test 6-20 limit)
   4. Add/remove distractors (test 0-5 limit)
   5. Test item-category assignments
   6. Test validation errors
   7. Save changes and verify updates
   ```

3. **Error Handling**
   ```
   1. Test with malformed question data
   2. Verify error boundaries activate
   3. Check fallback components display
   4. Test recovery after errors
   ```

### Performance Benchmarks

- **Component Render Time**: < 100ms for typical categorization question
- **Form Validation**: < 20ms for complete form validation
- **Memory Usage**: < 5MB additional for categorization components
- **Bundle Size Impact**: < 15KB gzipped for all categorization components

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
   # Production build with categorization support
   npm run build

   # Verify bundle size increase is minimal
   npm run build -- --analyze
   ```

3. **Integration Testing**

   ```bash
   # Start backend with categorization support
   cd backend
   docker compose up -d

   # Run frontend with backend
   cd frontend
   npm run dev

   # Test categorization question creation
   # Navigate to http://localhost:5173
   ```

4. **Deployment Verification**

   ```bash
   # Check that categorization questions work
   curl -X GET http://localhost:8000/api/v1/questions/types
   # Should include "categorization" in response

   # Verify frontend loads categorization components
   # Test complete quiz creation workflow
   ```

### Environment-Specific Configurations

#### Development Environment

- No special configuration required
- Uses existing development setup

#### Staging Environment

- Verify backend categorization support is deployed
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

   - Remove categorization option from QuizSettingsStep
   - Update router to show unsupported message
   - Disable categorization in constants temporarily

3. **Graceful Degradation**
   - Categorization questions show as "Unsupported" type
   - No data loss occurs
   - Users can still use MCQ, Fill-in-Blank, and Matching

## 7. Monitoring & Maintenance

### Key Metrics to Monitor

#### Application Metrics

- **Question Type Usage**: Track percentage of categorization questions created
- **Error Rates**: Monitor component error boundaries and validation failures
- **Performance Metrics**: Component render times, form validation speed
- **User Engagement**: Time spent editing categorization questions vs other types

#### Technical Metrics

- **Bundle Size**: Monitor impact of categorization components on bundle size
- **Memory Usage**: Track memory consumption during question editing
- **API Calls**: Monitor backend API usage for categorization operations
- **TypeScript Errors**: Watch for type-related issues in production

### Log Entries to Watch For

#### Success Indicators

```javascript
// Component mounting successfully
console.log("CategorizationDisplay rendered successfully", { questionId });

// Form validation passing
console.log("Categorization question validation passed", {
  categoriesCount,
  itemsCount,
  distractorsCount,
});

// Successful saves
console.log("Categorization question saved successfully", { questionId, updateData });
```

#### Error Indicators

```javascript
// Component errors
console.error("Error rendering categorization question:", error);

// Validation errors
console.error("Categorization question validation failed:", validationError);

// Type errors
console.error("Invalid categorization question data structure:", dataError);
```

#### Browser Console Monitoring

- Watch for React component warnings
- Monitor for validation error messages
- Check for failed API calls or data loading issues

### Common Issues and Troubleshooting

#### Issue: "Categorization option not appearing in quiz creation"

**Symptoms**: Categorization question type not shown in QuizSettingsStep
**Causes**:
- Constants not updated correctly
- TypeScript compilation errors
- Component not imported properly

**Solutions**:
```bash
# Check TypeScript compilation
npx tsc --noEmit

# Verify constants are exported correctly
grep -r "CATEGORIZATION" src/lib/constants/

# Check component imports
grep -r "CategorizationDisplay\|CategorizationEditor" src/components/
```

#### Issue: "Validation errors in categorization editor"

**Symptoms**: Form won't save, validation messages appear
**Causes**:
- Duplicate category names or item texts
- Too few categories (< 2) or items (< 6)
- Items not properly assigned to categories

**Solutions**:
```typescript
// Debug validation in browser console
const formData = form.getValues();
console.log("Form data:", formData);
console.log("Validation errors:", form.formState.errors);

// Check for duplicates
const categoryNames = formData.categories.map(c => c.name.toLowerCase());
console.log("Duplicate categories:", categoryNames.length !== new Set(categoryNames).size);
```

#### Issue: "Error loading categorization question data"

**Symptoms**: ErrorDisplay component shows instead of CategorizationDisplay
**Causes**:
- Invalid question data from backend
- Type guard rejection
- Missing required fields

**Solutions**:
```javascript
// Debug in browser console
console.log("Question data:", question.question_data);
console.log("Is valid categorization data:", isCategorizationData(question.question_data));

// Check backend response format
fetch("/api/v1/questions/{id}")
  .then(r => r.json())
  .then(data => console.log("Backend question data:", data));
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
grep -r "export.*Categorization" src/

# Check discriminated union includes categorization
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
// Categorization questions follow same data patterns
interface CategorizationData {
  question_text: string; // Encrypted at rest
  categories: Array<{
    // Encrypted at rest
    id: string;
    name: string;
    correct_items: string[];
  }>;
  items: Array<{
    // Encrypted at rest
    id: string;
    text: string;
  }>;
  distractors?: Array<{
    // Optional, encrypted at rest
    id: string;
    text: string;
  }> | null;
  explanation?: string; // Optional, encrypted at rest
}
```

### Security Best Practices

#### Input Validation

```typescript
// Comprehensive client-side validation
export const categorizationSchema = z.object({
  questionText: nonEmptyString,
  categories: z
    .array(...)
    .refine(...), // Prevents injection and validates structure
  // ... additional validation
});

// Runtime type checking
export function isCategorizationData(data: unknown): data is CategorizationData {
  // Validates data structure to prevent malicious payloads
}
```

#### Output Sanitization

```typescript
// All text content is escaped by React by default
<Text fontSize="md" fontWeight="medium">
  {categorizationData.question_text} {/* Automatically escaped */}
</Text>

// HTML content handled safely
<ExplanationBox explanation={categorizationData.explanation} />
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
- **No Dangerous HTML**: No `dangerouslySetInnerHTML` usage in categorization components
- **Safe Attributes**: All component props are type-safe and validated

#### Input Sanitization

```typescript
// Form validation prevents malicious input
const categorizationSchema = z.object({
  questionText: nonEmptyString.max(1000), // Length limits
  categories: z.array(
    z.object({
      name: nonEmptyString.max(100), // Reasonable limits
      correctItems: z.array(z.string()), // Validated structure
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
export function isCategorizationData(data: unknown): data is CategorizationData {
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
const result = categorizationSchema.safeParse(formData);
if (!result.success) {
  // Prevents invalid data from reaching backend
  throw new ValidationError(result.error);
}
```

## 9. Future Considerations

### Known Limitations

#### Current Implementation Constraints

1. **Simple Categorization Only**
   - **Limitation**: Each item can only belong to one category
   - **Impact**: Cannot create multi-category assignments or overlapping classifications
   - **Workaround**: Use multiple categorization questions for complex relationships

2. **Fixed Assignment Model**
   - **Limitation**: Items must be assigned to exactly one category
   - **Impact**: Cannot create questions where some items don't belong to any category (except distractors)
   - **Future Enhancement**: Flexible assignment rules

3. **Limited Visual Feedback**
   - **Limitation**: Basic card-based display without advanced interactions
   - **Impact**: Less engaging than drag-and-drop interfaces
   - **Future Enhancement**: Interactive categorization interface

4. **Static Category Structure**
   - **Limitation**: Categories are pre-defined and cannot be modified during student interaction
   - **Impact**: Cannot create dynamic or conditional categorization scenarios
   - **Future Enhancement**: Hierarchical categorization support

### Potential Improvements

#### Enhanced Categorization Types

```typescript
// Future: Multi-category assignments
interface MultiCategorizationData extends CategorizationData {
  allowMultipleCategories: boolean;
  categoryAssignments: {
    [itemId: string]: string[]; // Item can belong to multiple categories
  };
}

// Future: Hierarchical categorization
interface HierarchicalCategorizationData extends CategorizationData {
  categoryHierarchy: {
    [parentId: string]: string[]; // Subcategory relationships
  };
  maxDepth: number;
}
```

#### Advanced UI Features

1. **Drag and Drop Interface**

   ```typescript
   // Enhanced editor with drag-and-drop
   import { DragDropContext, Droppable, Draggable } from "react-beautiful-dnd";

   function EnhancedCategorizationEditor() {
     // Allow visual categorization through drag-and-drop
     // Provide preview of student experience
     // Real-time validation feedback
   }
   ```

2. **Visual Category Management**

   ```typescript
   // Category relationship visualization
   function CategoryRelationshipMap({
     categories,
     items,
     assignments,
   }: {
     categories: Category[];
     items: CategoryItem[];
     assignments: ItemAssignment[];
   }) {
     // Interactive diagram showing category-item relationships
     // Visual validation of assignment completeness
     // Drag-and-drop assignment interface
   }
   ```

3. **Advanced Validation Interface**
   ```typescript
   // Real-time validation with visual feedback
   function CategorizationValidationPanel({
     formData,
   }: {
     formData: CategorizationFormData;
   }) {
     // Show assignment coverage per category
     // Highlight unassigned items
     // Visual duplicate detection
   }
   ```

#### Performance Optimizations

1. **Virtual Scrolling for Large Questions**

   ```typescript
   // For questions with many categories/items
   import { FixedSizeList as List } from "react-window";

   function LargeCategorizationDisplay({
     categories,
     items
   }: {
     categories: Category[];
     items: CategoryItem[];
   }) {
     // Virtualize rendering for 50+ items
     // Maintain performance with large datasets
   }
   ```

2. **Lazy Loading of Components**

   ```typescript
   // Code splitting for categorization components
   const CategorizationEditor = lazy(() =>
     import("./CategorizationEditor").then((module) => ({
       default: module.CategorizationEditor,
     }))
   );
   ```

3. **Optimized Form State**
   ```typescript
   // Future: Optimized form performance for large questions
   import { useFormContext } from "react-hook-form";

   function OptimizedCategoryEditor({ index }: { index: number }) {
     // Only re-render specific category on change
     // Debounced validation
     // Minimal re-renders
   }
   ```

### Scalability Considerations

#### Component Scalability

1. **Modular Architecture**

   ```
   Categorization Question System:
   ├── Core Components (CategorizationDisplay, CategorizationEditor)
   ├── Specialized Variants (DragDropCategorization, HierarchicalCategorization)
   ├── Shared Utilities (validation, type guards)
   └── Extension Points (custom categorization types)
   ```

2. **Type System Evolution**

   ```typescript
   // Extensible type system for future categorization types
   interface BaseCategorizationData {
     question_text: string;
     explanation?: string;
   }

   // Different categorization implementations can extend base
   interface StandardCategorizationData extends BaseCategorizationData {
     categories: Category[];
     items: CategoryItem[];
     distractors?: CategoryItem[];
   }

   interface HierarchicalCategorizationData extends BaseCategorizationData {
     categoryTree: CategoryNode[];
     assignmentRules: AssignmentRule[];
   }
   ```

#### Database Scalability

- **JSONB Storage**: Current polymorphic storage scales to millions of questions
- **Indexing Strategy**: Can add specialized indexes for categorization question queries
- **Query Optimization**: Existing query patterns support complex categorization operations

#### Bundle Size Management

```typescript
// Future: Dynamic imports for question types
const questionComponents = {
  multiple_choice: () => import("./MCQDisplay"),
  fill_in_blank: () => import("./FillInBlankDisplay"),
  matching: () => import("./MatchingDisplay"),
  categorization: () => import("./CategorizationDisplay"), // Loaded on demand
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
interface CategorizationDataV1 {
  // Current implementation
  question_text: string;
  categories: Category[];
  items: CategoryItem[];
  distractors?: CategoryItem[];
}

interface CategorizationDataV2 {
  // Future enhanced version
  question_text: string;
  categories: EnhancedCategory[]; // With weights, colors, etc.
  items: EnhancedCategoryItem[]; // With metadata, media, etc.
  assignments: ItemAssignment[]; // Flexible assignment rules
  settings: CategorizationSettings; // Question-specific settings
}

// Migration strategy
function migrateCategorizationData(data: CategorizationDataV1): CategorizationDataV2 {
  // Automatic migration for backward compatibility
}
```

#### Accessibility Enhancements

```typescript
// Future: Enhanced accessibility features
interface AccessibleCategorizationProps {
  // Screen reader support
  ariaLabels: {
    categories: string;
    items: string;
    assignmentInstruction: string;
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
   interface EnhancedCategorizationData extends CategorizationData {
     // New optional fields don't break existing data
     categorySettings?: CategorySettings;
     visualTheme?: VisualTheme;
   }
   ```

2. **Graceful Degradation**

   ```typescript
   // Future components handle legacy data
   function EnhancedCategorizationDisplay({ question }: Props) {
     const data = extractQuestionData(question, "categorization");

     // Detect data version and render appropriately
     if (isLegacyCategorizationData(data)) {
       return <LegacyCategorizationView data={data} />;
     }

     return <EnhancedCategorizationView data={data} />;
   }
   ```

3. **Incremental Migration**
   ```typescript
   // Database migration strategy
   function upgradeCategorizationQuestion(oldData: CategorizationDataV1): CategorizationDataV2 {
     return {
       ...oldData,
       // Add new fields with sensible defaults
       assignments: generateDefaultAssignments(oldData),
       settings: getDefaultSettings(),
     };
   }
   ```

---

## Implementation Checklist

- [ ] **Step 1**: Update constants (QUESTION_TYPES, QUESTION_TYPE_LABELS)
- [ ] **Step 2**: Define CategorizationData interface and type guards
- [ ] **Step 3**: Create categorizationSchema with Zod validation
- [ ] **Step 4**: Create CategorizationDisplay.tsx component
- [ ] **Step 5**: Create CategorizationEditor.tsx component
- [ ] **Step 6**: Update router components (QuestionDisplay, QuestionEditor)
- [ ] **Step 7**: Update export files and test TypeScript compilation
- [ ] **Step 8**: Add categorization option to QuizSettingsStep.tsx
- [ ] **Step 9**: Manual testing of complete workflow
- [ ] **Step 10**: Deployment and monitoring setup

### After Each Step

1. **Run TypeScript Check**: `npx tsc --noEmit`
2. **Commit Changes**: `git add -A && git commit -m "descriptive message"`
3. **Test Functionality**: Manual verification of component behavior

---

**Remember**: This implementation maintains full compatibility with the existing system while adding comprehensive categorization question support. The polymorphic architecture makes it easy to add additional question types in the future following the same patterns.

_End of Implementation Document_
