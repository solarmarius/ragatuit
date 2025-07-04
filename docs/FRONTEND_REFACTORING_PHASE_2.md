# Frontend Refactoring Phase 2: Component Refactoring

## Overview
This document provides detailed steps 11-20 for breaking down large components into smaller, more maintainable pieces. This phase should be started only after completing Phase 1 (Steps 1-10) successfully.

## Prerequisites
- Phase 1 completed successfully
- All type checks passing
- Application functionality verified
- Feature branch created and Phase 1 changes committed

## Phase 2: Component Refactoring (Steps 11-20)

### Step 11: Create Question Display Component Structure
**Goal:** Break down the large QuestionDisplay component (524 lines) into smaller, focused components.

**Actions:**
- CREATE: `src/components/questions/display/QuestionDisplay.tsx`
- CREATE: `src/components/questions/display/MCQDisplay.tsx`
- CREATE: `src/components/questions/display/TrueFalseDisplay.tsx`
- CREATE: `src/components/questions/display/ShortAnswerDisplay.tsx`
- CREATE: `src/components/questions/display/EssayDisplay.tsx`
- CREATE: `src/components/questions/display/FillInBlankDisplay.tsx`
- CREATE: `src/components/questions/display/UnsupportedDisplay.tsx`
- CREATE: `src/components/questions/display/ErrorDisplay.tsx`
- CREATE: `src/components/questions/display/index.ts`

**Code changes:**
```typescript
// src/components/questions/display/QuestionDisplay.tsx
import type { QuestionResponse } from "@/client"
import { QUESTION_TYPES } from "@/lib/constants"
import { MCQDisplay } from "./MCQDisplay"
import { TrueFalseDisplay } from "./TrueFalseDisplay"
import { ShortAnswerDisplay } from "./ShortAnswerDisplay"
import { EssayDisplay } from "./EssayDisplay"
import { FillInBlankDisplay } from "./FillInBlankDisplay"
import { UnsupportedDisplay } from "./UnsupportedDisplay"

interface QuestionDisplayProps {
  question: QuestionResponse
  showCorrectAnswer?: boolean
  showExplanation?: boolean
}

export function QuestionDisplay({
  question,
  showCorrectAnswer = false,
  showExplanation = false,
}: QuestionDisplayProps) {
  const commonProps = {
    question,
    showCorrectAnswer,
    showExplanation,
  }

  switch (question.question_type) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return <MCQDisplay {...commonProps} />
    case QUESTION_TYPES.TRUE_FALSE:
      return <TrueFalseDisplay {...commonProps} />
    case QUESTION_TYPES.SHORT_ANSWER:
      return <ShortAnswerDisplay {...commonProps} />
    case QUESTION_TYPES.ESSAY:
      return <EssayDisplay {...commonProps} />
    case QUESTION_TYPES.FILL_IN_BLANK:
      return <FillInBlankDisplay {...commonProps} />
    default:
      return <UnsupportedDisplay questionType={question.question_type} />
  }
}
```

```typescript
// src/components/questions/display/MCQDisplay.tsx
import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"
import { ErrorDisplay } from "./ErrorDisplay"
import { ExplanationBox } from "../shared/ExplanationBox"

interface MCQDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

export function MCQDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: MCQDisplayProps) {
  try {
    const mcqData = extractQuestionData(question, "multiple_choice")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {mcqData.question_text}
          </Text>
        </Box>

        <VStack gap={2} align="stretch">
          {[
            { key: "A", text: mcqData.option_a },
            { key: "B", text: mcqData.option_b },
            { key: "C", text: mcqData.option_c },
            { key: "D", text: mcqData.option_d },
          ].map((option) => (
            <HStack
              key={option.key}
              p={3}
              bg={
                showCorrectAnswer && option.key === mcqData.correct_answer
                  ? "green.50"
                  : "gray.50"
              }
              borderRadius="md"
              border={
                showCorrectAnswer && option.key === mcqData.correct_answer
                  ? "2px solid"
                  : "1px solid"
              }
              borderColor={
                showCorrectAnswer && option.key === mcqData.correct_answer
                  ? "green.200"
                  : "gray.200"
              }
            >
              <Badge
                colorScheme={
                  showCorrectAnswer && option.key === mcqData.correct_answer
                    ? "green"
                    : "gray"
                }
                variant="solid"
                size="sm"
              >
                {option.key}
              </Badge>
              <Text flex={1}>{option.text}</Text>
              {showCorrectAnswer && option.key === mcqData.correct_answer && (
                <Badge colorScheme="green" variant="subtle" size="sm">
                  Correct
                </Badge>
              )}
            </HStack>
          ))}
        </VStack>

        {showExplanation && mcqData.explanation && (
          <ExplanationBox explanation={mcqData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading MCQ question data" />
  }
}
```

```typescript
// src/components/questions/display/TrueFalseDisplay.tsx
import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"
import { ErrorDisplay } from "./ErrorDisplay"
import { ExplanationBox } from "../shared/ExplanationBox"

interface TrueFalseDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

export function TrueFalseDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: TrueFalseDisplayProps) {
  try {
    const tfData = extractQuestionData(question, "true_false")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {tfData.question_text}
          </Text>
        </Box>

        <VStack gap={2} align="stretch">
          {[
            { key: "True", value: true },
            { key: "False", value: false },
          ].map((option) => (
            <HStack
              key={option.key}
              p={3}
              bg={
                showCorrectAnswer && option.value === tfData.correct_answer
                  ? "green.50"
                  : "gray.50"
              }
              borderRadius="md"
              border={
                showCorrectAnswer && option.value === tfData.correct_answer
                  ? "2px solid"
                  : "1px solid"
              }
              borderColor={
                showCorrectAnswer && option.value === tfData.correct_answer
                  ? "green.200"
                  : "gray.200"
              }
            >
              <Badge
                colorScheme={
                  showCorrectAnswer && option.value === tfData.correct_answer
                    ? "green"
                    : "gray"
                }
                variant="solid"
                size="sm"
              >
                {option.key}
              </Badge>
              <Text flex={1}>{option.key}</Text>
              {showCorrectAnswer && option.value === tfData.correct_answer && (
                <Badge colorScheme="green" variant="subtle" size="sm">
                  Correct
                </Badge>
              )}
            </HStack>
          ))}
        </VStack>

        {showExplanation && tfData.explanation && (
          <ExplanationBox explanation={tfData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading True/False question data" />
  }
}
```

```typescript
// src/components/questions/display/ShortAnswerDisplay.tsx
import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Box, Text, VStack } from "@chakra-ui/react"
import { ErrorDisplay } from "./ErrorDisplay"
import { ExplanationBox } from "../shared/ExplanationBox"
import { CorrectAnswerBox } from "../shared/CorrectAnswerBox"

interface ShortAnswerDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

export function ShortAnswerDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: ShortAnswerDisplayProps) {
  try {
    const saData = extractQuestionData(question, "short_answer")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {saData.question_text}
          </Text>
        </Box>

        {showCorrectAnswer && (
          <CorrectAnswerBox
            correctAnswer={saData.correct_answer}
            answerVariations={saData.answer_variations}
            caseSensitive={saData.case_sensitive}
          />
        )}

        {showExplanation && saData.explanation && (
          <ExplanationBox explanation={saData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading Short Answer question data" />
  }
}
```

```typescript
// src/components/questions/display/EssayDisplay.tsx
import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Badge, Box, Text, VStack } from "@chakra-ui/react"
import { ErrorDisplay } from "./ErrorDisplay"
import { GradingRubricBox } from "../shared/GradingRubricBox"
import { SampleAnswerBox } from "../shared/SampleAnswerBox"

interface EssayDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

export function EssayDisplay({
  question,
  showCorrectAnswer,
}: EssayDisplayProps) {
  try {
    const essayData = extractQuestionData(question, "essay")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {essayData.question_text}
          </Text>
        </Box>

        {essayData.expected_length && (
          <Box>
            <Text fontSize="sm" color="gray.600">
              Expected length:{" "}
              <Badge size="sm" colorScheme="blue">
                {essayData.expected_length}
              </Badge>
            </Text>
          </Box>
        )}

        {essayData.max_words && (
          <Box>
            <Text fontSize="sm" color="gray.600">
              Maximum words:{" "}
              <Badge size="sm" colorScheme="orange">
                {essayData.max_words}
              </Badge>
            </Text>
          </Box>
        )}

        {showCorrectAnswer && essayData.grading_rubric && (
          <GradingRubricBox rubric={essayData.grading_rubric} />
        )}

        {showCorrectAnswer && essayData.sample_answer && (
          <SampleAnswerBox sampleAnswer={essayData.sample_answer} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading Essay question data" />
  }
}
```

```typescript
// src/components/questions/display/FillInBlankDisplay.tsx
import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Box, Text, VStack } from "@chakra-ui/react"
import { ErrorDisplay } from "./ErrorDisplay"
import { ExplanationBox } from "../shared/ExplanationBox"
import { FillInBlankAnswersBox } from "../shared/FillInBlankAnswersBox"

interface FillInBlankDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

export function FillInBlankDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: FillInBlankDisplayProps) {
  try {
    const fibData = extractQuestionData(question, "fill_in_blank")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {fibData.question_text}
          </Text>
        </Box>

        {showCorrectAnswer && (
          <FillInBlankAnswersBox blanks={fibData.blanks} />
        )}

        {showExplanation && fibData.explanation && (
          <ExplanationBox explanation={fibData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading Fill in Blank question data" />
  }
}
```

```typescript
// src/components/questions/display/UnsupportedDisplay.tsx
import { Box, Text } from "@chakra-ui/react"

interface UnsupportedDisplayProps {
  questionType: string
}

export function UnsupportedDisplay({ questionType }: UnsupportedDisplayProps) {
  return (
    <Box
      p={4}
      bg="orange.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="orange.200"
    >
      <Text fontSize="md" fontWeight="medium" color="orange.700" mb={1}>
        Unsupported Question Type
      </Text>
      <Text fontSize="sm" color="orange.600">
        Question type "{questionType}" is not yet supported in the display
        interface.
      </Text>
    </Box>
  )
}
```

```typescript
// src/components/questions/display/ErrorDisplay.tsx
import { Box, Text } from "@chakra-ui/react"

interface ErrorDisplayProps {
  error: string
}

export function ErrorDisplay({ error }: ErrorDisplayProps) {
  return (
    <Box
      p={4}
      bg="red.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="red.200"
    >
      <Text fontSize="md" fontWeight="medium" color="red.700" mb={1}>
        Display Error
      </Text>
      <Text fontSize="sm" color="red.600">
        {error}
      </Text>
    </Box>
  )
}
```

```typescript
// src/components/questions/display/index.ts
export * from './QuestionDisplay'
export * from './MCQDisplay'
export * from './TrueFalseDisplay'
export * from './ShortAnswerDisplay'
export * from './EssayDisplay'
export * from './FillInBlankDisplay'
export * from './UnsupportedDisplay'
export * from './ErrorDisplay'
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Question display components created with modular structure, some TypeScript errors expected for missing shared components (will be created in next step).

---

### Step 12: Create Shared Question Components
**Goal:** Create reusable components that are shared across different question types.

**Actions:**
- CREATE: `src/components/questions/shared/ExplanationBox.tsx`
- CREATE: `src/components/questions/shared/CorrectAnswerBox.tsx`
- CREATE: `src/components/questions/shared/GradingRubricBox.tsx`
- CREATE: `src/components/questions/shared/SampleAnswerBox.tsx`
- CREATE: `src/components/questions/shared/FillInBlankAnswersBox.tsx`
- CREATE: `src/components/questions/shared/index.ts`

**Code changes:**
```typescript
// src/components/questions/shared/ExplanationBox.tsx
import { Box, Text } from "@chakra-ui/react"

interface ExplanationBoxProps {
  explanation: string
}

export function ExplanationBox({ explanation }: ExplanationBoxProps) {
  return (
    <Box
      p={3}
      bg="blue.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="blue.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={1}>
        Explanation:
      </Text>
      <Text fontSize="sm" color="blue.600">
        {explanation}
      </Text>
    </Box>
  )
}
```

```typescript
// src/components/questions/shared/CorrectAnswerBox.tsx
import { Box, Text } from "@chakra-ui/react"

interface CorrectAnswerBoxProps {
  correctAnswer: string
  answerVariations?: string[]
  caseSensitive?: boolean
}

export function CorrectAnswerBox({
  correctAnswer,
  answerVariations,
  caseSensitive,
}: CorrectAnswerBoxProps) {
  return (
    <Box
      p={3}
      bg="green.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="green.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="green.700" mb={1}>
        Correct Answer:
      </Text>
      <Text fontSize="sm" color="green.600" fontFamily="mono">
        {correctAnswer}
      </Text>
      {answerVariations && answerVariations.length > 0 && (
        <>
          <Text
            fontSize="sm"
            fontWeight="medium"
            color="green.700"
            mt={2}
            mb={1}
          >
            Accepted Variations:
          </Text>
          <Text fontSize="sm" color="green.600" fontFamily="mono">
            {answerVariations.join(", ")}
          </Text>
        </>
      )}
      {caseSensitive && (
        <Text fontSize="xs" color="orange.600" mt={1}>
          (Case sensitive)
        </Text>
      )}
    </Box>
  )
}
```

```typescript
// src/components/questions/shared/GradingRubricBox.tsx
import { Box, Text } from "@chakra-ui/react"

interface GradingRubricBoxProps {
  rubric: string
}

export function GradingRubricBox({ rubric }: GradingRubricBoxProps) {
  return (
    <Box
      p={3}
      bg="green.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="green.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="green.700" mb={1}>
        Grading Rubric:
      </Text>
      <Text fontSize="sm" color="green.600" whiteSpace="pre-wrap">
        {rubric}
      </Text>
    </Box>
  )
}
```

```typescript
// src/components/questions/shared/SampleAnswerBox.tsx
import { Box, Text } from "@chakra-ui/react"

interface SampleAnswerBoxProps {
  sampleAnswer: string
}

export function SampleAnswerBox({ sampleAnswer }: SampleAnswerBoxProps) {
  return (
    <Box
      p={3}
      bg="blue.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="blue.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={1}>
        Sample Answer:
      </Text>
      <Text fontSize="sm" color="blue.600" whiteSpace="pre-wrap">
        {sampleAnswer}
      </Text>
    </Box>
  )
}
```

```typescript
// src/components/questions/shared/FillInBlankAnswersBox.tsx
import { Box, Text, VStack } from "@chakra-ui/react"

interface BlankData {
  position: number
  correct_answer: string
  answer_variations?: string[]
  case_sensitive?: boolean
}

interface FillInBlankAnswersBoxProps {
  blanks: BlankData[]
}

export function FillInBlankAnswersBox({ blanks }: FillInBlankAnswersBoxProps) {
  return (
    <Box
      p={3}
      bg="green.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="green.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="green.700" mb={2}>
        Correct Answers:
      </Text>
      <VStack gap={2} align="stretch">
        {blanks.map((blank, index) => (
          <Box key={index}>
            <Text fontSize="sm" color="green.600">
              <strong>Blank {blank.position}:</strong>{" "}
              <Text as="span" fontFamily="mono">
                {blank.correct_answer}
              </Text>
            </Text>
            {blank.answer_variations && blank.answer_variations.length > 0 && (
              <Text fontSize="xs" color="green.500" ml={4}>
                Variations: {blank.answer_variations.join(", ")}
              </Text>
            )}
            {blank.case_sensitive && (
              <Text fontSize="xs" color="orange.600" ml={4}>
                (Case sensitive)
              </Text>
            )}
          </Box>
        ))}
      </VStack>
    </Box>
  )
}
```

```typescript
// src/components/questions/shared/index.ts
export * from './ExplanationBox'
export * from './CorrectAnswerBox'
export * from './GradingRubricBox'
export * from './SampleAnswerBox'
export * from './FillInBlankAnswersBox'
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Shared question components created, TypeScript errors from previous step should be resolved.

---

### Step 13: Replace Original QuestionDisplay Component
**Goal:** Replace the original large QuestionDisplay component with the new modular version.

**Actions:**
- DELETE: `src/components/Questions/QuestionDisplay.tsx`
- MODIFY: Files that import the old QuestionDisplay component

**Code changes:**

First, let's find which files import the old component:
- Check `src/components/Questions/QuestionReview.tsx`
- Check any other files that might import it

```typescript
// Update any imports in files that use QuestionDisplay
// Change from:
// import { QuestionDisplay } from "@/components/Questions/QuestionDisplay"
// To:
// import { QuestionDisplay } from "@/components/questions/display"
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Old QuestionDisplay removed, new modular version integrated, no TypeScript errors.

---

### Step 14: Create Layout Components
**Goal:** Extract layout-related components into their own directory for better organization.

**Actions:**
- MOVE: `src/components/Common/Sidebar.tsx` → `src/components/layout/Sidebar.tsx`
- MOVE: `src/components/Common/SidebarItems.tsx` → `src/components/layout/SidebarItems.tsx`
- MOVE: `src/components/Common/NotFound.tsx` → `src/components/common/NotFound.tsx`
- CREATE: `src/components/layout/index.ts`
- CREATE: `src/components/common/index.ts`
- MODIFY: All files that import these moved components

**Code changes:**
```typescript
// src/components/layout/index.ts
export { default as Sidebar } from './Sidebar'
export { default as SidebarItems } from './SidebarItems'
```

```typescript
// src/components/common/index.ts
export { default as NotFound } from './NotFound'
```

**Update imports in affected files:**
```typescript
// src/routes/_layout.tsx
// Change from:
// import Sidebar from "@/components/Common/Sidebar"
// To:
import { Sidebar } from "@/components/layout"

// src/routes/__root.tsx
// Change from:
// import NotFound from "@/components/Common/NotFound"
// To:
import { NotFound } from "@/components/common"

// src/components/layout/Sidebar.tsx
// Change from:
// import SidebarItems from "./SidebarItems"
// To:
import { SidebarItems } from "./SidebarItems"
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Layout components organized in proper directories, all imports updated, no TypeScript errors.

---

### Step 15: Create Form Components Base Structure
**Goal:** Set up the foundation for form components to improve form handling consistency.

**Actions:**
- CREATE: `src/components/forms/FormField.tsx`
- CREATE: `src/components/forms/FormError.tsx`
- CREATE: `src/components/forms/FormLabel.tsx`
- CREATE: `src/components/forms/FormGroup.tsx`
- CREATE: `src/components/forms/index.ts`

**Code changes:**
```typescript
// src/components/forms/FormField.tsx
import { Box } from "@chakra-ui/react"
import type { ReactNode } from "react"
import { FormLabel } from "./FormLabel"
import { FormError } from "./FormError"

interface FormFieldProps {
  children: ReactNode
  label?: string
  error?: string
  isRequired?: boolean
  isInvalid?: boolean
  id?: string
}

export function FormField({
  children,
  label,
  error,
  isRequired = false,
  isInvalid = false,
  id,
}: FormFieldProps) {
  return (
    <Box>
      {label && (
        <FormLabel htmlFor={id} isRequired={isRequired}>
          {label}
        </FormLabel>
      )}
      {children}
      {error && <FormError>{error}</FormError>}
    </Box>
  )
}
```

```typescript
// src/components/forms/FormLabel.tsx
import { Text } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface FormLabelProps {
  children: ReactNode
  htmlFor?: string
  isRequired?: boolean
}

export function FormLabel({ children, htmlFor, isRequired }: FormLabelProps) {
  return (
    <Text
      as="label"
      htmlFor={htmlFor}
      fontSize="sm"
      fontWeight="medium"
      color="gray.700"
      mb={1}
      display="block"
    >
      {children}
      {isRequired && (
        <Text as="span" color="red.500" ml={1}>
          *
        </Text>
      )}
    </Text>
  )
}
```

```typescript
// src/components/forms/FormError.tsx
import { Text } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface FormErrorProps {
  children: ReactNode
}

export function FormError({ children }: FormErrorProps) {
  return (
    <Text fontSize="sm" color="red.500" mt={1}>
      {children}
    </Text>
  )
}
```

```typescript
// src/components/forms/FormGroup.tsx
import { VStack } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface FormGroupProps {
  children: ReactNode
  gap?: number
}

export function FormGroup({ children, gap = 4 }: FormGroupProps) {
  return (
    <VStack gap={gap} align="stretch">
      {children}
    </VStack>
  )
}
```

```typescript
// src/components/forms/index.ts
export * from './FormField'
export * from './FormLabel'
export * from './FormError'
export * from './FormGroup'
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Form component foundation created, ready for use in form refactoring, no TypeScript errors.

---

### Step 16: Create Dashboard Component Structure
**Goal:** Break down dashboard components and improve their organization.

**Actions:**
- MOVE: `src/components/Dashboard/` → `src/components/dashboard/`
- CREATE: `src/components/dashboard/panels/` directory
- MOVE: `src/components/dashboard/HelpPanel.tsx` → `src/components/dashboard/panels/HelpPanel.tsx`
- MOVE: `src/components/dashboard/QuizGenerationPanel.tsx` → `src/components/dashboard/panels/QuizGenerationPanel.tsx`
- MOVE: `src/components/dashboard/QuizReviewPanel.tsx` → `src/components/dashboard/panels/QuizReviewPanel.tsx`
- CREATE: `src/components/dashboard/panels/index.ts`
- CREATE: `src/components/dashboard/index.ts`

**Code changes:**
```typescript
// src/components/dashboard/panels/index.ts
export * from './HelpPanel'
export * from './QuizGenerationPanel'
export * from './QuizReviewPanel'
```

```typescript
// src/components/dashboard/index.ts
export * from './panels'
```

**Update imports in affected files:**
```typescript
// src/routes/_layout/index.tsx
// Change from:
// import { HelpPanel } from "@/components/Dashboard/HelpPanel"
// import { QuizGenerationPanel } from "@/components/Dashboard/QuizGenerationPanel"
// import { QuizReviewPanel } from "@/components/Dashboard/QuizReviewPanel"
// To:
import { HelpPanel, QuizGenerationPanel, QuizReviewPanel } from "@/components/dashboard"
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Dashboard components reorganized with better structure, imports updated, no TypeScript errors.

---

### Step 17: Add React.memo to Pure Components
**Goal:** Optimize performance by preventing unnecessary re-renders of pure components.

**Actions:**
- MODIFY: `src/components/questions/display/MCQDisplay.tsx`
- MODIFY: `src/components/questions/display/TrueFalseDisplay.tsx`
- MODIFY: `src/components/questions/display/ShortAnswerDisplay.tsx`
- MODIFY: `src/components/questions/display/EssayDisplay.tsx`
- MODIFY: `src/components/questions/display/FillInBlankDisplay.tsx`
- MODIFY: `src/components/questions/shared/ExplanationBox.tsx`
- MODIFY: `src/components/questions/shared/CorrectAnswerBox.tsx`
- MODIFY: All other pure components

**Code changes:**
```typescript
// src/components/questions/display/MCQDisplay.tsx
// Add at the top:
import { memo } from "react"

// Wrap the component export:
export const MCQDisplay = memo(function MCQDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: MCQDisplayProps) {
  // ... existing component code
})
```

Apply the same pattern to all other display components and shared components:

```typescript
// src/components/questions/shared/ExplanationBox.tsx
import { memo } from "react"

export const ExplanationBox = memo(function ExplanationBox({ explanation }: ExplanationBoxProps) {
  // ... existing component code
})
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Pure components wrapped with React.memo for performance optimization, no TypeScript errors.

---

### Step 18: Create Common Hook Directory Structure
**Goal:** Organize custom hooks into logical groups for better maintainability.

**Actions:**
- MOVE: `src/hooks/useCustomToast.ts` → `src/hooks/common/useCustomToast.ts`
- MOVE: `src/hooks/useOnboarding.ts` → `src/hooks/common/useOnboarding.ts`
- CREATE: `src/hooks/common/index.ts`
- UPDATE: `src/hooks/auth/index.ts`
- UPDATE: `src/hooks/api/index.ts`
- CREATE: `src/hooks/index.ts` (main hooks export)

**Code changes:**
```typescript
// src/hooks/common/index.ts
export * from './useCustomToast'
export * from './useOnboarding'
```

```typescript
// src/hooks/index.ts
export * from './auth'
export * from './api'
export * from './common'
```

**Update imports in affected files:**
```typescript
// src/routes/_layout/index.tsx
// Change from:
// import useCustomToast from "@/hooks/useCustomToast"
// import { useOnboarding } from "@/hooks/useOnboarding"
// To:
import { useCustomToast, useOnboarding } from "@/hooks/common"

// Or use the main barrel export:
// import { useCustomToast, useOnboarding } from "@/hooks"
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Hooks organized in logical directories with barrel exports, imports updated, no TypeScript errors.

---

### Step 19: Improve Type Safety for Question Components
**Goal:** Enhance TypeScript types for better type safety and developer experience.

**Actions:**
- CREATE: `src/types/components.ts`
- MODIFY: Question display components to use stricter types
- CREATE: Type guards for component props

**Code changes:**
```typescript
// src/types/components.ts
import type { QuestionResponse } from "@/client"

// Base props for all question display components
export interface BaseQuestionDisplayProps {
  question: QuestionResponse
  showCorrectAnswer?: boolean
  showExplanation?: boolean
}

// Specific props for each question type
export interface MCQDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: 'multiple_choice' }
}

export interface TrueFalseDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: 'true_false' }
}

export interface ShortAnswerDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: 'short_answer' }
}

export interface EssayDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: 'essay' }
}

export interface FillInBlankDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: 'fill_in_blank' }
}

// Common component props
export interface StatusLightProps {
  extractionStatus: 'pending' | 'processing' | 'completed' | 'failed'
  generationStatus: 'pending' | 'processing' | 'completed' | 'failed'
  size?: 'sm' | 'md' | 'lg'
}

export interface LoadingSkeletonProps {
  height?: string
  width?: string
  lines?: number
}
```

```typescript
// Update src/types/index.ts
export * from "./questionTypes"
export * from "./questionStats"
export * from "./components"
```

**Update question display components to use the new types:**
```typescript
// src/components/questions/display/MCQDisplay.tsx
import type { MCQDisplayProps } from "@/types/components"

export const MCQDisplay = memo(function MCQDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: MCQDisplayProps) {
  // ... component code
})
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Enhanced type safety for components, better TypeScript intellisense, no TypeScript errors.

---

### Step 20: Create Utility Components for Common Patterns
**Goal:** Extract common UI patterns into reusable utility components.

**Actions:**
- CREATE: `src/components/common/LoadingSkeleton.tsx`
- CREATE: `src/components/common/EmptyState.tsx`
- CREATE: `src/components/common/ErrorState.tsx`
- CREATE: `src/components/common/PageHeader.tsx`
- UPDATE: `src/components/common/index.ts`

**Code changes:**
```typescript
// src/components/common/LoadingSkeleton.tsx
import { Skeleton, VStack, HStack } from "@chakra-ui/react"
import { memo } from "react"
import type { LoadingSkeletonProps } from "@/types/components"

export const LoadingSkeleton = memo(function LoadingSkeleton({
  height = "20px",
  width = "100%",
  lines = 1,
}: LoadingSkeletonProps) {
  if (lines === 1) {
    return <Skeleton height={height} width={width} />
  }

  return (
    <VStack gap={2} align="stretch">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          height={height}
          width={index === lines - 1 ? "80%" : width}
        />
      ))}
    </VStack>
  )
})
```

```typescript
// src/components/common/EmptyState.tsx
import { VStack, Text, Box } from "@chakra-ui/react"
import { memo } from "react"
import type { ReactNode } from "react"

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
}

export const EmptyState = memo(function EmptyState({
  title,
  description,
  icon,
  action,
}: EmptyStateProps) {
  return (
    <Box textAlign="center" py={12}>
      <VStack gap={4}>
        {icon && <Box>{icon}</Box>}
        <Text fontSize="lg" fontWeight="semibold" color="gray.600">
          {title}
        </Text>
        {description && <Text color="gray.500">{description}</Text>}
        {action && <Box mt={4}>{action}</Box>}
      </VStack>
    </Box>
  )
})
```

```typescript
// src/components/common/ErrorState.tsx
import { VStack, Text, Box, Button } from "@chakra-ui/react"
import { memo } from "react"

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  showRetry?: boolean
}

export const ErrorState = memo(function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  showRetry = true,
}: ErrorStateProps) {
  return (
    <Box textAlign="center" py={12}>
      <VStack gap={4}>
        <Text fontSize="xl" fontWeight="bold" color="red.500">
          {title}
        </Text>
        <Text color="gray.600">{message}</Text>
        {showRetry && onRetry && (
          <Button onClick={onRetry} colorScheme="red" variant="outline" mt={4}>
            Try Again
          </Button>
        )}
      </VStack>
    </Box>
  )
})
```

```typescript
// src/components/common/PageHeader.tsx
import { Box, HStack, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"
import type { ReactNode } from "react"

interface PageHeaderProps {
  title: string
  description?: string
  action?: ReactNode
}

export const PageHeader = memo(function PageHeader({
  title,
  description,
  action,
}: PageHeaderProps) {
  return (
    <HStack justify="space-between" align="center">
      <Box>
        <Text fontSize="3xl" fontWeight="bold">
          {title}
        </Text>
        {description && <Text color="gray.600">{description}</Text>}
      </Box>
      {action && <Box>{action}</Box>}
    </HStack>
  )
})
```

```typescript
// Update src/components/common/index.ts
export { default as NotFound } from './NotFound'
export * from './LoadingSkeleton'
export * from './EmptyState'
export * from './ErrorState'
export * from './PageHeader'
```

**Update components to use the new utility components:**
```typescript
// Example: Update src/routes/_layout/quizzes.tsx to use new components
import { PageHeader, EmptyState, ErrorState } from "@/components/common"

// Replace the existing header JSX with:
<PageHeader
  title="My Quizzes"
  description="Manage and view all your created quizzes"
  action={
    <Button asChild>
      <RouterLink to="/create-quiz">Create New Quiz</RouterLink>
    </Button>
  }
/>

// Replace empty state JSX with:
<EmptyState
  title="No Quizzes Found"
  description="You haven't created any quizzes yet. Get started by creating your first quiz."
  action={
    <Button asChild>
      <RouterLink to="/create-quiz">Create Your First Quiz</RouterLink>
    </Button>
  }
/>
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Common utility components created and integrated, improved consistency across the app, no TypeScript errors.

---

## Checkpoint: Phase 2 Complete

At this point, you should have completed the component refactoring phase with:

### ✅ Completed Tasks:
- Large QuestionDisplay component broken down into modular pieces
- Shared question components created for reusability
- Layout components properly organized
- Form component foundation established
- Dashboard components restructured
- React.memo added for performance optimization
- Hooks properly organized with barrel exports
- Enhanced type safety for components
- Common utility components created

### 🧪 Testing Checklist:
1. **Type Safety**: Run `npx tsc --noEmit` - should pass with no errors
2. **Build**: Run `npm run build` - should succeed
3. **Linting**: Run `npm run lint` - should pass
4. **Functionality Testing**:
   - All question types display correctly
   - Dashboard panels show proper data
   - Navigation still works
   - Form interactions work
   - Loading states appear correctly
   - Error states handle failures gracefully

### 📊 Phase 2 Benefits Achieved:
- **Maintainability**: Components are now smaller and focused on single responsibilities
- **Reusability**: Shared components reduce code duplication
- **Performance**: React.memo prevents unnecessary re-renders
- **Type Safety**: Enhanced TypeScript types catch errors at compile time
- **Developer Experience**: Better organization and intellisense
- **Consistency**: Common patterns standardized across the app

### 🚀 Ready for Phase 3:
Once Phase 2 testing is complete and all functionality is verified, you can proceed to Phase 3, which will focus on:
- Performance optimizations and bundle analysis
- Code splitting implementation
- Lazy loading of components and routes
- Advanced caching strategies
- Memory optimization

**Continue to Phase 3 when ready, or address any issues found during Phase 2 testing.**
