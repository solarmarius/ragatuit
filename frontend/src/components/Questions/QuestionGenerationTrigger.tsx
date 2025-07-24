import { Box, Button, Card, HStack, Text, VStack, Badge } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { MdAutoAwesome, MdRefresh } from "react-icons/md"

import { QuizService, type Quiz } from "@/client"
import { useCustomToast, useErrorHandler } from "@/hooks/common"
import { QUIZ_STATUS } from "@/lib/constants"

interface QuestionGenerationTriggerProps {
  quiz: Quiz
}

export function QuestionGenerationTrigger({
  quiz,
}: QuestionGenerationTriggerProps) {
  const { showSuccessToast } = useCustomToast()
  const { handleError } = useErrorHandler()
  const queryClient = useQueryClient()

  // Determine if this is a retry scenario
  const isPartialRetry = quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL
  const isFailedRetry = quiz.status === QUIZ_STATUS.FAILED &&
    (quiz.failure_reason === "llm_generation_error" ||
     quiz.failure_reason === "no_questions_generated")

  const triggerGenerationMutation = useMutation({
    mutationFn: async () => {
      if (!quiz.id) {
        throw new Error("Quiz ID is required")
      }

      return await QuizService.triggerQuestionGeneration({
        quizId: quiz.id,
      })
    },
    onSuccess: (response) => {
      const successMessage = response.message ||
        (isPartialRetry ? "Failed batch retry started" : "Question generation started")
      showSuccessToast(successMessage)
      queryClient.invalidateQueries({ queryKey: ["quiz", quiz.id] })
    },
    onError: handleError,
  })

  // Don't show if quiz ID is missing
  if (!quiz.id) {
    return null
  }

  // Only show if generation can be retried (failed or partial success)
  if (!isPartialRetry && !isFailedRetry) {
    return null
  }

  // Get progress information for partial retry scenarios
  const getProgressInfo = () => {
    if (!isPartialRetry || !quiz.generation_metadata) return null

    const metadata = quiz.generation_metadata as any
    const totalQuestions = Number(metadata.total_questions_target) || Number(quiz.question_count) || 0
    const savedQuestions = Number(metadata.total_questions_saved) || 0
    const remainingQuestions = totalQuestions - savedQuestions
    const successRate = totalQuestions > 0 ? (savedQuestions / totalQuestions) * 100 : 0

    return {
      totalQuestions,
      savedQuestions,
      remainingQuestions,
      successRate,
      successfulBatches: Array.isArray(metadata.successful_batches) ? metadata.successful_batches.length : 0,
      failedBatches: Array.isArray(metadata.failed_batches) ? metadata.failed_batches.length : 0,
    }
  }

  const progressInfo = getProgressInfo()

  return (
    <Card.Root>
      <Card.Body>
        <VStack gap={4} align="stretch">
          <Box textAlign="center">
            <Text fontSize="xl" fontWeight="bold" mb={2}>
              {isPartialRetry ? "Partial Success - Retry Available" : "Question Generation Failed"}
            </Text>
            <Text color="gray.600" mb={4}>
              {isPartialRetry
                ? `Some questions were generated successfully. Click below to retry generating the remaining ${progressInfo?.remainingQuestions || 0} questions.`
                : `The previous question generation attempt failed. Click below to retry generating ${quiz.question_count} multiple-choice questions.`
              }
            </Text>
          </Box>

          {/* Progress information for partial retry */}
          {isPartialRetry && progressInfo && (
            <Box
              p={4}
              bg="purple.50"
              borderRadius="md"
              border="1px solid"
              borderColor="purple.200"
            >
              <VStack gap={3}>
                <HStack justify="space-between" width="100%">
                  <Text fontSize="sm" fontWeight="medium" color="purple.700">
                    Progress
                  </Text>
                  <Badge colorScheme="purple" variant="subtle">
                    {Math.round(progressInfo.successRate)}% Complete
                  </Badge>
                </HStack>

                <HStack justify="space-between" width="100%" fontSize="sm" color="purple.600">
                  <Text>{progressInfo.savedQuestions} saved</Text>
                  <Text>{progressInfo.remainingQuestions} remaining</Text>
                </HStack>

                <HStack gap={4} fontSize="sm" color="purple.600">
                  <Text>✓ {progressInfo.successfulBatches} batches succeeded</Text>
                  <Text>✗ {progressInfo.failedBatches} batches failed</Text>
                </HStack>
              </VStack>
            </Box>
          )}

          {/* Settings information for complete failure */}
          {isFailedRetry && (
            <Box
              p={4}
              bg="blue.50"
              borderRadius="md"
              border="1px solid"
              borderColor="blue.200"
            >
              <VStack gap={2}>
                <Text fontSize="sm" fontWeight="medium" color="blue.700">
                  Generation Settings
                </Text>
                <HStack gap={4} fontSize="sm" color="blue.600">
                  <Text>Questions: {quiz.question_count}</Text>
                </HStack>
              </VStack>
            </Box>
          )}

          <Button
            size="lg"
            colorScheme={isPartialRetry ? "purple" : "blue"}
            onClick={() => triggerGenerationMutation.mutate()}
            loading={triggerGenerationMutation.isPending}
            width="100%"
          >
            {isPartialRetry ? <MdRefresh /> : <MdAutoAwesome />}
            {isPartialRetry ? "Retry Failed Batches" : "Retry Question Generation"}
          </Button>
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
