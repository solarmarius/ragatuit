# Multiple Question Types per Module - Implementation Guide

**Document Version:** 1.0
**Date:** 2025-07-25
**Target Audience:** Frontend Engineers
**Estimated Implementation Time:** 3-4 days

---

## 1. Feature Overview

### What This Feature Does

The Multiple Question Types per Module feature allows users to configure different types of questions (Multiple Choice, Fill in Blank, Matching, Categorization) for each Canvas module when creating a quiz. Instead of selecting a single question type for the entire quiz, users can create 1-4 "question batches" per module, each with its own question type and count.

### Business Value and User Benefits

- **Enhanced Assessment Quality**: Instructors can create more comprehensive quizzes by mixing question types within a single assessment
- **Granular Control**: Users can tailor question types to match the content and learning objectives of each module
- **Improved Learning Outcomes**: Different question types test different cognitive skills, providing better evaluation of student understanding
- **Flexibility**: Accommodates diverse teaching styles and assessment strategies

### Context and Background

Previously, the Rag@UiT quiz generator supported only one question type per entire quiz. The backend has been updated to support multiple question types per module, and this document details the frontend migration required to support this new capability.

---

## 2. Technical Architecture

### High-Level Architecture

The feature operates within the existing React-based frontend architecture:

```
Quiz Creation Flow:
1. Course Selection
2. Module Selection
3. Question Batch Configuration (NEW - Enhanced)
4. Quiz Settings (MODIFIED - Question type removed)

Data Flow:
User Input → ModuleQuestionSelectionStep → Quiz Creation State → API Request → Backend
```

### System Integration

This feature integrates with:
- **Canvas API**: For fetching course modules
- **Quiz Generation Backend**: For creating quizzes with multiple question types
- **Database**: Stores quiz configurations with question batch details
- **UI Components**: Enhanced display throughout the application

### Architectural Changes

```
BEFORE:
QuizFormData {
  moduleQuestions: { [moduleId]: questionCount }
  questionType: single_type_for_all
}

AFTER:
QuizFormData {
  moduleQuestions: { [moduleId]: QuestionBatch[] }
  // questionType removed
}

QuestionBatch {
  question_type: string
  count: number (1-20)
}
```

---

## 3. Dependencies & Prerequisites

### External Dependencies

All required dependencies are already installed in the existing project:
- React 18+
- TypeScript 4.8+
- Chakra UI v3
- TanStack Router
- Auto-generated API client (`@hey-api/openapi-ts`)

### Version Requirements

- Node.js 18+
- npm 9+
- TypeScript strict mode enabled

### Environment Setup

No additional environment setup required. The backend API client types are already updated to support the new schema.

---

## 4. Implementation Details

### 4.1 File Structure

```
frontend/src/
├── components/
│   ├── QuizCreation/
│   │   ├── ModuleQuestionSelectionStep.tsx (REPLACE)
│   │   └── QuizSettingsStep.tsx (MODIFY)
│   ├── Common/
│   │   ├── QuizListCard.tsx (MODIFY)
│   │   ├── QuizTableRow.tsx (MODIFY)
│   │   ├── QuestionTypeBreakdown.tsx (NEW)
│   │   └── ModuleQuestionSummary.tsx (NEW)
│   └── dashboard/
│       └── QuizBadges.tsx (MODIFY)
├── routes/
│   └── _layout/
│       ├── create-quiz.tsx (MODIFY)
│       └── quiz.$id.tsx (MODIFY)
└── lib/
    ├── utils/
    │   └── quiz.ts (MODIFY)
    └── constants/
        └── index.ts (MODIFY)
```

### 4.2 Step-by-Step Implementation

#### Step 1: Add Utility Functions and Constants

**File:** `/src/lib/constants/index.ts`

Add new validation constants at the end of the file:

```typescript
// =============================================================================
// Question Batch Validation Constants
// =============================================================================

export const VALIDATION_RULES = {
  MAX_BATCHES_PER_MODULE: 4,
  MIN_QUESTIONS_PER_BATCH: 1,
  MAX_QUESTIONS_PER_BATCH: 20,
} as const;

export const VALIDATION_MESSAGES = {
  MAX_BATCHES: "Maximum 4 question batches per module",
  DUPLICATE_TYPES: "Cannot have duplicate question types in the same module",
  INVALID_COUNT: "Question count must be between 1 and 20",
  NO_BATCHES: "Each module must have at least one question batch",
} as const;

export const QUESTION_BATCH_DEFAULTS = {
  DEFAULT_QUESTION_TYPE: QUESTION_TYPES.MULTIPLE_CHOICE,
  DEFAULT_QUESTION_COUNT: 10,
} as const;
```

**File:** `/src/lib/utils/quiz.ts`

Add these new functions at the end of the file:

```typescript
// =============================================================================
// Question Batch Functions
// =============================================================================

import type { QuestionBatch, ModuleSelection } from "@/client/types.gen"
import { QUESTION_TYPE_LABELS, VALIDATION_RULES, VALIDATION_MESSAGES } from "@/lib/constants"

/**
 * Calculate total questions from question batches across all modules
 */
export function calculateTotalQuestionsFromBatches(
  moduleQuestions: Record<string, QuestionBatch[]>
): number {
  return Object.values(moduleQuestions).reduce(
    (total, batches) => total + calculateModuleQuestions(batches),
    0
  )
}

/**
 * Calculate questions for a single module's batches
 */
export function calculateModuleQuestions(batches: QuestionBatch[]): number {
  return batches.reduce((sum, batch) => sum + batch.count, 0)
}

/**
 * Get all unique question types used in a quiz
 */
export function getQuizQuestionTypes(quiz: Quiz): string[] {
  if (!quiz.selected_modules) return []

  const types = new Set<string>()

  Object.values(quiz.selected_modules).forEach((module: any) => {
    if (module.question_batches) {
      module.question_batches.forEach((batch: QuestionBatch) => {
        types.add(batch.question_type)
      })
    }
  })

  return Array.from(types)
}

/**
 * Get detailed question type breakdown per module
 * Returns: { moduleId: { questionType: count } }
 */
export function getModuleQuestionTypeBreakdown(
  quiz: Quiz
): Record<string, Record<string, number>> {
  if (!quiz.selected_modules) return {}

  const breakdown: Record<string, Record<string, number>> = {}

  Object.entries(quiz.selected_modules).forEach(([moduleId, module]: [string, any]) => {
    breakdown[moduleId] = {}

    if (module.question_batches) {
      module.question_batches.forEach((batch: QuestionBatch) => {
        breakdown[moduleId][batch.question_type] =
          (breakdown[moduleId][batch.question_type] || 0) + batch.count
      })
    }
  })

  return breakdown
}

/**
 * Validate question batches for a module
 * Returns array of error messages (empty if valid)
 */
export function validateModuleBatches(batches: QuestionBatch[]): string[] {
  const errors: string[] = []

  // Check batch count limit
  if (batches.length > VALIDATION_RULES.MAX_BATCHES_PER_MODULE) {
    errors.push(VALIDATION_MESSAGES.MAX_BATCHES)
  }

  // Check for duplicate question types
  const types = batches.map(batch => batch.question_type)
  const uniqueTypes = new Set(types)
  if (types.length !== uniqueTypes.size) {
    errors.push(VALIDATION_MESSAGES.DUPLICATE_TYPES)
  }

  // Check individual batch counts
  batches.forEach((batch, index) => {
    if (batch.count < VALIDATION_RULES.MIN_QUESTIONS_PER_BATCH ||
        batch.count > VALIDATION_RULES.MAX_QUESTIONS_PER_BATCH) {
      errors.push(`Batch ${index + 1}: ${VALIDATION_MESSAGES.INVALID_COUNT}`)
    }
  })

  return errors
}

/**
 * Format question type for display
 */
export function formatQuestionTypeDisplay(questionType: string): string {
  return QUESTION_TYPE_LABELS[questionType as keyof typeof QUESTION_TYPE_LABELS] || questionType
}

/**
 * Format multiple question types for compact display
 */
export function formatQuestionTypesDisplay(types: string[]): string {
  if (types.length === 0) return "No questions"
  if (types.length === 1) return formatQuestionTypeDisplay(types[0])

  const formatted = types.map(formatQuestionTypeDisplay)
  if (formatted.length <= 2) {
    return formatted.join(" & ")
  }

  return `${formatted.slice(0, 2).join(", ")} & ${formatted.length - 2} more`
}
```

#### Step 2: Update Quiz Creation State Management

**File:** `/src/routes/_layout/create-quiz.tsx`

Replace the existing QuizFormData interface and related logic:

```typescript
import {
  Box,
  Button,
  Card,
  Container,
  HStack,
  Progress,
  Text,
  VStack,
} from "@chakra-ui/react"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useCallback, useState } from "react"

import { type QuizLanguage, QuizService, type QuestionBatch } from "@/client"
import { CourseSelectionStep } from "@/components/QuizCreation/CourseSelectionStep"
import { ModuleQuestionSelectionStep } from "@/components/QuizCreation/ModuleQuestionSelectionStep"
import { ModuleSelectionStep } from "@/components/QuizCreation/ModuleSelectionStep"
import { QuizSettingsStep } from "@/components/QuizCreation/QuizSettingsStep"
import { useCustomToast, useErrorHandler } from "@/hooks/common"
import { QUIZ_LANGUAGES } from "@/lib/constants"
import { calculateTotalQuestionsFromBatches } from "@/lib/utils"

export const Route = createFileRoute("/_layout/create-quiz")({
  component: CreateQuiz,
})

// UPDATED: New interface structure
interface QuizFormData {
  selectedCourse?: {
    id: number
    name: string
  }
  selectedModules?: { [id: number]: string }
  moduleQuestions?: { [id: string]: QuestionBatch[] } // CHANGED: Now array of batches
  title?: string
  language?: QuizLanguage
  // questionType removed - now per batch
}

const TOTAL_STEPS = 4 // Course selection, Module selection, Questions per module, Quiz settings

function CreateQuiz() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<QuizFormData>({})
  const [isCreating, setIsCreating] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleError } = useErrorHandler()

  const handleNext = () => {
    if (currentStep < TOTAL_STEPS) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleCancel = () => {
    navigate({ to: "/" })
  }

  const updateFormData = useCallback((data: Partial<QuizFormData>) => {
    setFormData((prev) => ({ ...prev, ...data }))
  }, [])

  // UPDATED: Initialize empty question batches instead of default counts
  const handleModuleSelection = useCallback(
    (modules: { [id: number]: string }) => {
      const moduleQuestions = { ...formData.moduleQuestions }

      // Initialize empty arrays for newly selected modules
      Object.keys(modules).forEach((moduleId) => {
        if (!moduleQuestions[moduleId]) {
          moduleQuestions[moduleId] = [] // CHANGED: Empty array instead of default count
        }
      })

      // Remove deselected modules
      Object.keys(moduleQuestions).forEach((moduleId) => {
        if (!modules[Number(moduleId)]) {
          delete moduleQuestions[moduleId]
        }
      })

      updateFormData({
        selectedModules: modules,
        moduleQuestions,
      })
    },
    [formData.moduleQuestions, updateFormData],
  )

  // UPDATED: Handle question batch changes instead of simple counts
  const handleModuleQuestionChange = useCallback(
    (moduleId: string, batches: QuestionBatch[]) => {
      updateFormData({
        moduleQuestions: {
          ...formData.moduleQuestions,
          [moduleId]: batches,
        },
      })
    },
    [formData.moduleQuestions, updateFormData],
  )

  // UPDATED: Build new API request format
  const handleCreateQuiz = async () => {
    if (
      !formData.selectedCourse ||
      !formData.selectedModules ||
      !formData.moduleQuestions ||
      !formData.title
    ) {
      showErrorToast("Missing required quiz data")
      return
    }

    setIsCreating(true)

    try {
      // UPDATED: Transform data to new backend format
      const selectedModulesWithBatches = Object.entries(
        formData.selectedModules,
      ).reduce(
        (acc, [moduleId, moduleName]) => ({
          ...acc,
          [moduleId]: {
            name: moduleName,
            question_batches: formData.moduleQuestions?.[moduleId] || [], // CHANGED: Use question_batches
          },
        }),
        {},
      )

      const quizData = {
        canvas_course_id: formData.selectedCourse.id,
        canvas_course_name: formData.selectedCourse.name,
        selected_modules: selectedModulesWithBatches,
        title: formData.title,
        language: formData.language || QUIZ_LANGUAGES.ENGLISH,
        // question_type removed - now per batch
      }

      const response = await QuizService.createNewQuiz({
        requestBody: quizData,
      })

      if (response) {
        showSuccessToast("Quiz created successfully!")
        navigate({ to: `/quiz/${response.id}`, params: { id: response.id! } })
      } else {
        throw new Error("Failed to create quiz")
      }
    } catch (error) {
      handleError(error)
    } finally {
      setIsCreating(false)
    }
  }

  const getStepTitle = () => {
    switch (currentStep) {
      case 1:
        return "Select Course"
      case 2:
        return "Select Modules"
      case 3:
        return "Configure Question Types" // UPDATED: More descriptive title
      case 4:
        return "Quiz Settings"
      default:
        return "Create Quiz"
    }
  }

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <CourseSelectionStep
            selectedCourse={formData.selectedCourse}
            onCourseSelect={(course) =>
              updateFormData({
                selectedCourse: course,
                title: course.name, // Auto-fill title with course name
              })
            }
            title={formData.title}
            onTitleChange={(title) => updateFormData({ title })}
          />
        )
      case 2:
        return (
          <ModuleSelectionStep
            courseId={formData.selectedCourse?.id || 0}
            selectedModules={formData.selectedModules || {}}
            onModulesSelect={handleModuleSelection}
          />
        )
      case 3:
        return (
          <ModuleQuestionSelectionStep
            selectedModules={Object.fromEntries(
              Object.entries(formData.selectedModules || {}).map(
                ([id, name]) => [id, name],
              ),
            )}
            moduleQuestions={formData.moduleQuestions || {}} // UPDATED: Pass batches
            onModuleQuestionChange={handleModuleQuestionChange} // UPDATED: Handle batches
          />
        )
      case 4:
        return (
          <QuizSettingsStep
            settings={{
              language: formData.language || QUIZ_LANGUAGES.ENGLISH,
              // questionType removed
            }}
            onSettingsChange={(settings) =>
              updateFormData({
                language: settings.language,
                // questionType removed
              })
            }
          />
        )
      default:
        return null
    }
  }

  // UPDATED: Validation logic for new data structure
  const isStepValid = () => {
    switch (currentStep) {
      case 1:
        return (
          formData.selectedCourse != null &&
          formData.title != null &&
          formData.title.trim().length > 0
        )
      case 2:
        return (
          formData.selectedModules != null &&
          Object.keys(formData.selectedModules).length > 0
        )
      case 3:
        // UPDATED: Validate question batches instead of simple counts
        if (!formData.moduleQuestions) return false

        const hasValidBatches = Object.values(formData.moduleQuestions).every(
          (batches) => {
            // Each module must have at least one batch
            if (batches.length === 0) return false

            // All batches must have valid counts
            return batches.every(
              (batch) => batch.count >= 1 && batch.count <= 20
            )
          }
        )

        return hasValidBatches && Object.keys(formData.moduleQuestions).length > 0
      case 4:
        // Step 4 is always valid since we have default values
        return true
      default:
        return false
    }
  }

  return (
    <Container maxW="4xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Box>
          <Text fontSize="3xl" fontWeight="bold">
            Create New Quiz
          </Text>
          <Text color="gray.600">
            Step {currentStep} of {TOTAL_STEPS}: {getStepTitle()}
          </Text>
        </Box>

        {/* Progress Bar */}
        <Progress.Root
          value={(currentStep / TOTAL_STEPS) * 100}
          colorScheme="blue"
          size="lg"
          borderRadius="md"
        >
          <Progress.Track>
            <Progress.Range />
          </Progress.Track>
        </Progress.Root>

        {/* Step Content */}
        <Card.Root>
          <Card.Body p={8}>{renderStep()}</Card.Body>
        </Card.Root>

        {/* Navigation Buttons */}
        <HStack justify="space-between">
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>

          <HStack>
            {currentStep > 1 && (
              <Button variant="outline" onClick={handlePrevious}>
                Previous
              </Button>
            )}

            {currentStep < TOTAL_STEPS ? (
              <Button
                colorScheme="blue"
                onClick={handleNext}
                disabled={!isStepValid()}
              >
                Next
              </Button>
            ) : (
              <Button
                colorScheme="green"
                disabled={!isStepValid()}
                onClick={handleCreateQuiz}
                loading={isCreating}
              >
                Create Quiz
              </Button>
            )}
          </HStack>
        </HStack>
      </VStack>
    </Container>
  )
}
```

#### Step 3: Replace ModuleQuestionSelectionStep Component

**File:** `/src/components/QuizCreation/ModuleQuestionSelectionStep.tsx`

Replace the entire file content:

```typescript
import {
  Alert,
  Box,
  Button,
  Card,
  HStack,
  Heading,
  Input,
  Text,
  VStack,
  Select,
} from "@chakra-ui/react"
import { Plus, Trash2 } from "lucide-react"
import type React from "react"
import { useMemo, useState } from "react"

import type { QuestionBatch, QuestionType } from "@/client"
import {
  QUESTION_TYPES,
  QUESTION_TYPE_LABELS,
  VALIDATION_RULES,
  VALIDATION_MESSAGES,
  QUESTION_BATCH_DEFAULTS
} from "@/lib/constants"
import {
  calculateTotalQuestionsFromBatches,
  calculateModuleQuestions,
  validateModuleBatches
} from "@/lib/utils"

interface ModuleQuestionSelectionStepProps {
  selectedModules: Record<string, string>
  moduleQuestions: Record<string, QuestionBatch[]>
  onModuleQuestionChange: (moduleId: string, batches: QuestionBatch[]) => void
}

export const ModuleQuestionSelectionStep: React.FC<
  ModuleQuestionSelectionStepProps
> = ({ selectedModules, moduleQuestions, onModuleQuestionChange }) => {
  const [validationErrors, setValidationErrors] = useState<Record<string, string[]>>({})

  const totalQuestions = useMemo(() => {
    return calculateTotalQuestionsFromBatches(moduleQuestions)
  }, [moduleQuestions])

  const moduleIds = Object.keys(selectedModules)

  // Question type options in the specified order
  const questionTypeOptions = [
    {
      value: QUESTION_TYPES.MULTIPLE_CHOICE,
      label: QUESTION_TYPE_LABELS.multiple_choice,
    },
    {
      value: QUESTION_TYPES.FILL_IN_BLANK,
      label: QUESTION_TYPE_LABELS.fill_in_blank,
    },
    {
      value: QUESTION_TYPES.MATCHING,
      label: QUESTION_TYPE_LABELS.matching,
    },
    {
      value: QUESTION_TYPES.CATEGORIZATION,
      label: QUESTION_TYPE_LABELS.categorization,
    },
  ]

  const addBatch = (moduleId: string) => {
    const currentBatches = moduleQuestions[moduleId] || []

    if (currentBatches.length >= VALIDATION_RULES.MAX_BATCHES_PER_MODULE) {
      setValidationErrors(prev => ({
        ...prev,
        [moduleId]: [VALIDATION_MESSAGES.MAX_BATCHES]
      }))
      return
    }

    const newBatch: QuestionBatch = {
      question_type: QUESTION_BATCH_DEFAULTS.DEFAULT_QUESTION_TYPE as QuestionType,
      count: QUESTION_BATCH_DEFAULTS.DEFAULT_QUESTION_COUNT,
    }

    const updatedBatches = [...currentBatches, newBatch]
    onModuleQuestionChange(moduleId, updatedBatches)

    // Clear validation errors
    setValidationErrors(prev => {
      const newErrors = { ...prev }
      delete newErrors[moduleId]
      return newErrors
    })
  }

  const removeBatch = (moduleId: string, batchIndex: number) => {
    const currentBatches = moduleQuestions[moduleId] || []
    const updatedBatches = currentBatches.filter((_, index) => index !== batchIndex)
    onModuleQuestionChange(moduleId, updatedBatches)

    // Clear validation errors if removing resolved the issue
    if (updatedBatches.length <= VALIDATION_RULES.MAX_BATCHES_PER_MODULE) {
      setValidationErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[moduleId]
        return newErrors
      })
    }
  }

  const updateBatch = (
    moduleId: string,
    batchIndex: number,
    updates: Partial<QuestionBatch>
  ) => {
    const currentBatches = moduleQuestions[moduleId] || []
    const updatedBatches = currentBatches.map((batch, index) =>
      index === batchIndex ? { ...batch, ...updates } : batch
    )

    // Validate the updated batches
    const errors = validateModuleBatches(updatedBatches)

    if (errors.length > 0) {
      setValidationErrors(prev => ({
        ...prev,
        [moduleId]: errors
      }))
    } else {
      setValidationErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[moduleId]
        return newErrors
      })
    }

    onModuleQuestionChange(moduleId, updatedBatches)
  }

  const handleQuestionCountChange = (
    moduleId: string,
    batchIndex: number,
    value: string
  ) => {
    const numValue = Number.parseInt(value, 10)
    if (!Number.isNaN(numValue) && numValue >= 1 && numValue <= 20) {
      updateBatch(moduleId, batchIndex, { count: numValue })
    }
  }

  return (
    <Box>
      <VStack gap={6} align="stretch">
        <Box>
          <Heading size="md" mb={2}>
            Configure Question Types per Module
          </Heading>
          <Text color="gray.600">
            Add question batches for each module. Each batch can have a different
            question type and count (1-20 questions per batch, max 4 batches per module).
          </Text>
        </Box>

        {/* Summary Card */}
        <Card.Root
          variant="elevated"
          bg="blue.50"
          borderColor="blue.200"
          borderWidth={1}
        >
          <Card.Body>
            <Box textAlign="center">
              <Text fontSize="sm" color="gray.600" mb={1}>
                Total Questions
              </Text>
              <Text fontSize="3xl" fontWeight="bold" color="blue.600">
                {totalQuestions}
              </Text>
              <Text fontSize="sm" color="gray.500">
                Across {moduleIds.length} modules
              </Text>
            </Box>
          </Card.Body>
        </Card.Root>

        {/* Large question count warning */}
        {totalQuestions > 500 && (
          <Alert.Root status="warning">
            <Alert.Indicator />
            <Alert.Title>Large Question Count</Alert.Title>
            <Alert.Description>
              Large number of questions may take longer to generate.
            </Alert.Description>
          </Alert.Root>
        )}

        {/* Module Configuration */}
        <VStack gap={4} align="stretch">
          {moduleIds.map((moduleId) => {
            const moduleBatches = moduleQuestions[moduleId] || []
            const moduleErrors = validationErrors[moduleId] || []
            const moduleTotal = calculateModuleQuestions(moduleBatches)

            return (
              <Card.Root
                key={moduleId}
                variant="outline"
                borderColor={moduleErrors.length > 0 ? "red.200" : "gray.200"}
                bg={moduleErrors.length > 0 ? "red.50" : "white"}
              >
                <Card.Body>
                  <VStack align="stretch" gap={4}>
                    {/* Module Header */}
                    <HStack justify="space-between" align="center">
                      <Box>
                        <Text fontWeight="medium" fontSize="lg">
                          {selectedModules[moduleId]}
                        </Text>
                        <Text fontSize="sm" color="gray.600">
                          {moduleTotal} questions total • {moduleBatches.length} batches
                        </Text>
                      </Box>
                      <Button
                        size="sm"
                        variant="outline"
                        leftIcon={<Plus size={16} />}
                        onClick={() => addBatch(moduleId)}
                        disabled={moduleBatches.length >= VALIDATION_RULES.MAX_BATCHES_PER_MODULE}
                      >
                        Add Batch
                      </Button>
                    </HStack>

                    {/* Validation Errors */}
                    {moduleErrors.length > 0 && (
                      <Alert.Root status="error" size="sm">
                        <Alert.Indicator />
                        <Alert.Description>
                          {moduleErrors.map((error, index) => (
                            <Text key={index} fontSize="sm">
                              {error}
                            </Text>
                          ))}
                        </Alert.Description>
                      </Alert.Root>
                    )}

                    {/* Question Batches */}
                    {moduleBatches.length > 0 ? (
                      <VStack gap={3} align="stretch">
                        {moduleBatches.map((batch, batchIndex) => (
                          <Box
                            key={batchIndex}
                            p={3}
                            bg="gray.50"
                            borderRadius="md"
                            border="1px solid"
                            borderColor="gray.200"
                          >
                            <HStack gap={3} align="end">
                              <Box flex={1}>
                                <Text fontSize="sm" fontWeight="medium" mb={1}>
                                  Question Type
                                </Text>
                                <Select.Root
                                  value={batch.question_type}
                                  onValueChange={(details) =>
                                    updateBatch(moduleId, batchIndex, {
                                      question_type: details.value as QuestionType,
                                    })
                                  }
                                >
                                  <Select.Trigger>
                                    <Select.ValueText />
                                  </Select.Trigger>
                                  <Select.Content>
                                    {questionTypeOptions.map((option) => (
                                      <Select.Item key={option.value} item={option.value}>
                                        <Select.ItemText>{option.label}</Select.ItemText>
                                      </Select.Item>
                                    ))}
                                  </Select.Content>
                                </Select.Root>
                              </Box>

                              <Box width="100px">
                                <Text fontSize="sm" fontWeight="medium" mb={1}>
                                  Questions
                                </Text>
                                <Input
                                  type="number"
                                  min={1}
                                  max={20}
                                  value={batch.count}
                                  onChange={(e) =>
                                    handleQuestionCountChange(
                                      moduleId,
                                      batchIndex,
                                      e.target.value
                                    )
                                  }
                                  textAlign="center"
                                />
                              </Box>

                              <Button
                                size="sm"
                                variant="ghost"
                                colorScheme="red"
                                onClick={() => removeBatch(moduleId, batchIndex)}
                              >
                                <Trash2 size={16} />
                              </Button>
                            </HStack>
                          </Box>
                        ))}
                      </VStack>
                    ) : (
                      <Box textAlign="center" py={6} color="gray.500">
                        <Text>No question batches configured</Text>
                        <Text fontSize="sm">Click "Add Batch" to get started</Text>
                      </Box>
                    )}
                  </VStack>
                </Card.Body>
              </Card.Root>
            )
          })}
        </VStack>

        {moduleIds.length === 0 && (
          <Card.Root variant="outline">
            <Card.Body textAlign="center" py={8}>
              <Text color="gray.500">
                No modules selected. Go back to select modules first.
              </Text>
            </Card.Body>
          </Card.Root>
        )}

        <Box mt={4}>
          <Text fontSize="sm" color="gray.600">
            <strong>Tip:</strong> Mix different question types to create comprehensive
            assessments. Each module can have up to 4 different question batches with
            1-20 questions each.
          </Text>
        </Box>
      </VStack>
    </Box>
  )
}
```

#### Step 4: Update QuizSettingsStep Component

**File:** `/src/components/QuizCreation/QuizSettingsStep.tsx`

Replace the file content to remove question type selection:

```typescript
import type { QuizLanguage } from "@/client";
import { FormField, FormGroup } from "@/components/forms";
import { QUIZ_LANGUAGES } from "@/lib/constants";
import { Box, Card, HStack, RadioGroup, Text, VStack } from "@chakra-ui/react";

// UPDATED: Removed questionType from interface
interface QuizSettings {
  language: QuizLanguage;
}

interface QuizSettingsStepProps {
  settings?: QuizSettings;
  onSettingsChange: (settings: QuizSettings) => void;
}

// UPDATED: Removed questionType from default settings
const DEFAULT_SETTINGS: QuizSettings = {
  language: QUIZ_LANGUAGES.ENGLISH,
};

export function QuizSettingsStep({
  settings = DEFAULT_SETTINGS,
  onSettingsChange,
}: QuizSettingsStepProps) {
  const updateSettings = (updates: Partial<QuizSettings>) => {
    const newSettings = { ...settings, ...updates };
    onSettingsChange(newSettings);
  };

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
  ];

  return (
    <FormGroup gap={6}>
      {/* Question Type section completely removed */}

      <FormField label="Quiz Language" isRequired>
        <Box>
          <Text fontSize="sm" color="gray.600" mb={3}>
            Select the language for question generation
          </Text>
          <RadioGroup.Root
            value={settings.language}
            onValueChange={(details) =>
              updateSettings({ language: details.value as QuizLanguage })
            }
          >
            <VStack gap={3} align="stretch" maxW="500px">
              {languageOptions.map((option) => (
                <Card.Root
                  key={option.value}
                  variant="outline"
                  cursor="pointer"
                  _hover={{ borderColor: "blue.300" }}
                  borderColor={
                    settings.language === option.value ? "blue.500" : "gray.200"
                  }
                  bg={settings.language === option.value ? "blue.50" : "white"}
                  onClick={() => updateSettings({ language: option.value })}
                  data-testid={`language-card-${option.value}`}
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

      {/* Additional settings note */}
      <Box p={4} bg="blue.50" borderRadius="md" borderColor="blue.200" borderWidth={1}>
        <Text fontSize="sm" color="blue.800">
          <strong>Note:</strong> Question types are now configured per module in the previous step.
          This allows you to create more comprehensive assessments with mixed question types.
        </Text>
      </Box>
    </FormGroup>
  );
}
```

#### Step 5: Create Display Components

**File:** `/src/components/Common/QuestionTypeBreakdown.tsx` (NEW FILE)

```typescript
import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"

import type { Quiz } from "@/client/types.gen"
import { getModuleQuestionTypeBreakdown, formatQuestionTypeDisplay } from "@/lib/utils"

interface QuestionTypeBreakdownProps {
  quiz: Quiz
  variant?: "compact" | "detailed"
}

export const QuestionTypeBreakdown = memo(function QuestionTypeBreakdown({
  quiz,
  variant = "detailed"
}: QuestionTypeBreakdownProps) {
  const breakdown = getModuleQuestionTypeBreakdown(quiz)
  const moduleEntries = Object.entries(breakdown)

  if (moduleEntries.length === 0) {
    return (
      <Text fontSize="sm" color="gray.500">
        No question types configured
      </Text>
    )
  }

  if (variant === "compact") {
    // Show aggregated counts across all modules
    const aggregatedTypes: Record<string, number> = {}

    moduleEntries.forEach(([_, moduleTypes]) => {
      Object.entries(moduleTypes).forEach(([type, count]) => {
        aggregatedTypes[type] = (aggregatedTypes[type] || 0) + count
      })
    })

    return (
      <HStack gap={2} flexWrap="wrap">
        {Object.entries(aggregatedTypes).map(([type, count]) => (
          <Badge key={type} variant="solid" colorScheme="blue" size="sm">
            {count} {formatQuestionTypeDisplay(type)}
          </Badge>
        ))}
      </HStack>
    )
  }

  return (
    <VStack align="stretch" gap={2}>
      {moduleEntries.map(([moduleId, moduleTypes]) => {
        const moduleName = quiz.selected_modules?.[moduleId]?.name || `Module ${moduleId}`

        return (
          <Box key={moduleId}>
            <Text fontSize="sm" fontWeight="medium" color="gray.700">
              {moduleName}:
            </Text>
            <HStack gap={2} ml={2} flexWrap="wrap">
              {Object.entries(moduleTypes).map(([type, count]) => (
                <Badge key={type} variant="outline" colorScheme="blue" size="sm">
                  {count} {formatQuestionTypeDisplay(type)}
                </Badge>
              ))}
            </HStack>
          </Box>
        )
      })}
    </VStack>
  )
})
```

**File:** `/src/components/Common/ModuleQuestionSummary.tsx` (NEW FILE)

```typescript
import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"

import type { QuestionBatch } from "@/client/types.gen"
import { formatQuestionTypeDisplay, calculateModuleQuestions } from "@/lib/utils"

interface ModuleQuestionSummaryProps {
  moduleName: string
  questionBatches?: QuestionBatch[]
}

export const ModuleQuestionSummary = memo(function ModuleQuestionSummary({
  moduleName,
  questionBatches = []
}: ModuleQuestionSummaryProps) {
  const totalQuestions = calculateModuleQuestions(questionBatches)

  if (questionBatches.length === 0) {
    return (
      <Box>
        <Text fontWeight="medium">{moduleName}</Text>
        <Text fontSize="sm" color="gray.500">No questions configured</Text>
      </Box>
    )
  }

  return (
    <VStack align="stretch" gap={2}>
      <HStack justify="space-between">
        <Text fontWeight="medium">{moduleName}</Text>
        <Text fontSize="sm" color="gray.600">
          {totalQuestions} total questions
        </Text>
      </HStack>

      <HStack gap={2} flexWrap="wrap">
        {questionBatches.map((batch, index) => (
          <Badge key={index} variant="solid" colorScheme="blue" size="sm">
            {batch.count} {formatQuestionTypeDisplay(batch.question_type)}
          </Badge>
        ))}
      </HStack>
    </VStack>
  )
})
```

### 4.3 Data Models & Schemas

#### Core Data Structures

```typescript
// Question Batch - represents a group of questions of the same type
interface QuestionBatch {
  question_type: QuestionType  // "multiple_choice" | "fill_in_blank" | "matching" | "categorization"
  count: number               // 1-20 questions per batch
}

// Module Selection - updated to support multiple question batches
interface ModuleSelection {
  name: string
  question_batches: QuestionBatch[]  // 1-4 batches per module
}

// Quiz Creation Request - updated structure
interface QuizCreate {
  canvas_course_id: number
  canvas_course_name: string
  selected_modules: {
    [moduleId: string]: ModuleSelection
  }
  title: string
  llm_model?: string
  llm_temperature?: number
  language?: QuizLanguage
  // question_type removed
}
```

#### Validation Rules

```typescript
const VALIDATION_RULES = {
  MAX_BATCHES_PER_MODULE: 4,    // Maximum question batches per module
  MIN_QUESTIONS_PER_BATCH: 1,   // Minimum questions per batch
  MAX_QUESTIONS_PER_BATCH: 20,  // Maximum questions per batch
}
```

#### Example Data

```typescript
// Example quiz creation request
const exampleQuizRequest = {
  canvas_course_id: 12345,
  canvas_course_name: "Introduction to Biology",
  title: "Chapter 3-5 Quiz",
  selected_modules: {
    "module_001": {
      name: "Cell Structure",
      question_batches: [
        { question_type: "multiple_choice", count: 15 },
        { question_type: "fill_in_blank", count: 5 }
      ]
    },
    "module_002": {
      name: "Cell Division",
      question_batches: [
        { question_type: "multiple_choice", count: 10 },
        { question_type: "matching", count: 3 }
      ]
    }
  },
  language: "en"
}
```

### 4.4 Configuration

No additional configuration files are needed. All constants are defined in `/src/lib/constants/index.ts`:

```typescript
// Question batch validation
export const VALIDATION_RULES = {
  MAX_BATCHES_PER_MODULE: 4,
  MIN_QUESTIONS_PER_BATCH: 1,
  MAX_QUESTIONS_PER_BATCH: 20,
} as const;

// Default values for new batches
export const QUESTION_BATCH_DEFAULTS = {
  DEFAULT_QUESTION_TYPE: QUESTION_TYPES.MULTIPLE_CHOICE,
  DEFAULT_QUESTION_COUNT: 10,
} as const;
```

---

## 5. Testing Strategy

### Unit Tests

Test the utility functions with various inputs:

```typescript
// Test question count calculation
describe('calculateTotalQuestionsFromBatches', () => {
  it('should calculate total questions correctly', () => {
    const moduleQuestions = {
      'mod1': [
        { question_type: 'multiple_choice', count: 10 },
        { question_type: 'fill_in_blank', count: 5 }
      ],
      'mod2': [
        { question_type: 'matching', count: 8 }
      ]
    }

    const total = calculateTotalQuestionsFromBatches(moduleQuestions)
    expect(total).toBe(23)
  })
})

// Test validation
describe('validateModuleBatches', () => {
  it('should return errors for duplicate question types', () => {
    const batches = [
      { question_type: 'multiple_choice', count: 10 },
      { question_type: 'multiple_choice', count: 5 }
    ]

    const errors = validateModuleBatches(batches)
    expect(errors).toContain('Cannot have duplicate question types in the same module')
  })
})
```

### Integration Tests

Test the complete quiz creation flow:

```typescript
describe('Quiz Creation Flow', () => {
  it('should create quiz with multiple question types', async () => {
    render(<CreateQuiz />)

    // Navigate through steps
    await selectCourse()
    await selectModules()

    // Configure question batches
    await user.click(screen.getByText('Add Batch'))
    await user.selectOptions(screen.getByLabelText('Question Type'), 'multiple_choice')
    await user.type(screen.getByLabelText('Questions'), '10')

    await user.click(screen.getByText('Add Batch'))
    await user.selectOptions(screen.getByLabelText('Question Type'), 'fill_in_blank')
    await user.type(screen.getByLabelText('Questions'), '5')

    // Complete creation
    await user.click(screen.getByText('Create Quiz'))

    // Verify API call
    expect(mockQuizService.createNewQuiz).toHaveBeenCalledWith({
      requestBody: expect.objectContaining({
        selected_modules: expect.objectContaining({
          'mod1': {
            name: 'Module 1',
            question_batches: [
              { question_type: 'multiple_choice', count: 10 },
              { question_type: 'fill_in_blank', count: 5 }
            ]
          }
        })
      })
    })
  })
})
```

### Manual Testing Steps

1. **Basic Flow**:
   - Create new quiz
   - Select course and modules
   - Add question batches with different types
   - Verify totals are calculated correctly
   - Complete quiz creation

2. **Validation Testing**:
   - Try to add more than 4 batches per module
   - Try to add duplicate question types in same module
   - Try invalid question counts (0, 21+)
   - Verify error messages appear

3. **Display Testing**:
   - Check quiz list shows question type breakdown
   - Verify quiz detail page shows per-module information
   - Test responsive design on different screen sizes

### Performance Considerations

- Question count calculations are memoized to prevent unnecessary recalculations
- Validation runs on user input with debouncing to avoid excessive API calls
- Large question counts (500+) show warning to user

---

## 6. Deployment Instructions

### Step-by-Step Deployment

1. **Backend Prerequisites**:
   - Ensure backend API is updated to support new question_batches schema
   - Verify API client is regenerated: `cd frontend && npm run generate-client`

2. **Frontend Deployment**:
   ```bash
   # Install dependencies (if needed)
   cd frontend
   npm install

   # Run type checking
   npm run type-check

   # Run linting
   npm run lint

   # Build for production
   npm run build

   # Deploy build artifacts
   ```

3. **Environment Configuration**:
   - No environment variables need to be changed
   - All configurations are in constants files

### Rollback Procedures

If rollback is needed:
1. Revert to previous frontend build
2. Ensure backend API maintains backward compatibility
3. Monitor for any API errors in logs

---

## 7. Monitoring & Maintenance

### Key Metrics to Monitor

- **Quiz Creation Success Rate**: Monitor API success/failure rates
- **Validation Errors**: Track most common validation failures
- **User Engagement**: Monitor how many users utilize multiple question types
- **Performance**: Track quiz creation completion times

### Log Entries to Watch

```javascript
// Frontend errors to monitor
console.error('Quiz creation failed:', error)
console.warn('Large question count:', totalQuestions)
console.info('Batch validation failed:', validationErrors)
```

### Common Issues and Troubleshooting

1. **"Duplicate question types" error**:
   - User tried to add same question type twice in one module
   - Solution: Remove duplicate or change question type

2. **"Maximum batches exceeded" error**:
   - User tried to add more than 4 batches per module
   - Solution: Remove batches or distribute across multiple modules

3. **Quiz creation fails with validation error**:
   - Frontend validation passed but backend rejected request
   - Check API client is up to date: `npm run generate-client`

---

## 8. Security Considerations

### Authentication/Authorization

- Feature inherits existing Canvas OAuth authentication
- No additional permissions required
- Quiz creation follows existing user permissions model

### Data Privacy

- No additional PII is collected
- Question batch configurations are stored with existing quiz data
- Follows existing data retention policies

### Security Best Practices

- Client-side validation is supplemented by server-side validation
- All API requests use existing authentication tokens
- No sensitive data is logged in console

---

## 9. Future Considerations

### Known Limitations

1. **Batch Reordering**: Currently no drag-and-drop reordering of batches
2. **Bulk Operations**: No bulk add/remove/duplicate batch operations
3. **Question Type Suggestions**: No AI-powered suggestions based on module content
4. **Advanced Validation**: No validation for optimal question type distributions

### Potential Improvements

1. **Enhanced UX**:
   - Drag-and-drop batch reordering
   - Batch templates/presets
   - Copy batch configuration between modules

2. **Advanced Features**:
   - Question type recommendations based on content analysis
   - Statistical analysis of question type effectiveness
   - Export question batch configurations for reuse

3. **Performance Optimizations**:
   - Lazy loading for modules with many batches
   - Virtualization for large module lists
   - Optimistic updates for better perceived performance

### Scalability Considerations

- Current implementation scales to hundreds of modules per quiz
- Question batch validation is O(n) where n is number of batches
- Memory usage grows linearly with number of configured batches
- Consider pagination if module counts exceed 100+ per quiz

---

**Document End**

*This implementation guide provides complete coverage of the Multiple Question Types per Module feature implementation. For questions or clarifications, refer to the frontend architecture documentation or consult the development team.*
