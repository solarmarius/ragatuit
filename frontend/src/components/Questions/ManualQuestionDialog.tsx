import { Button, VStack } from "@chakra-ui/react"
import { memo, useState } from "react"

import type { QuestionCreateRequest } from "@/client"
import { QuestionsService } from "@/client"
import {
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
