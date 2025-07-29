import { Card, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { type Quiz, QuizService } from "@/client"
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/Common"
import { QuestionReview } from "@/components/Questions/QuestionReview"
import { QuestionStats } from "@/components/Questions/QuestionStats"
import { useConditionalPolling } from "@/hooks/common"
import { FAILURE_REASON, QUIZ_STATUS, UI_TEXT } from "@/lib/constants"
import { queryKeys, quizQueryConfig } from "@/lib/queryConfig"

export const Route = createFileRoute("/_layout/quiz/$id/questions")({
  component: QuizQuestions,
})

function renderErrorForFailureReason(failureReason: string | null | undefined) {
  if (!failureReason) {
    return null
  }

  // Get the error message from constants or use generic fallback
  const errorMessage =
    UI_TEXT.FAILURE_MESSAGES[
      failureReason as keyof typeof UI_TEXT.FAILURE_MESSAGES
    ] || UI_TEXT.FAILURE_MESSAGES.GENERIC

  return (
    <Card.Root>
      <Card.Body>
        <ErrorState
          title={errorMessage.TITLE}
          message={errorMessage.MESSAGE}
          showRetry={false}
        />
      </Card.Body>
    </Card.Root>
  )
}

function QuizQuestions() {
  const { id } = Route.useParams()

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

      {/* Question Review */}
      {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
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
    </VStack>
  )
}

function QuizQuestionsSkeleton() {
  return (
    <VStack gap={6} align="stretch">
      {/* Question Statistics Skeleton */}
      <Card.Root>
        <Card.Header>
          <LoadingSkeleton height="24px" width="200px" />
        </Card.Header>
        <Card.Body>
          <VStack gap={4} align="stretch">
            <LoadingSkeleton height="20px" width="100%" lines={2} />
            <LoadingSkeleton height="40px" width="150px" />
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Question Review Skeleton */}
      <Card.Root>
        <Card.Header>
          <LoadingSkeleton height="32px" width="180px" />
          <LoadingSkeleton height="16px" width="300px" />
        </Card.Header>
        <Card.Body>
          <VStack gap={4} align="stretch">
            {/* Filter buttons skeleton */}
            <LoadingSkeleton height="32px" width="200px" />

            {/* Questions list skeleton */}
            {[1, 2, 3].map((i) => (
              <Card.Root key={i}>
                <Card.Body>
                  <VStack gap={3} align="stretch">
                    <LoadingSkeleton height="20px" width="100%" lines={3} />
                    <LoadingSkeleton height="32px" width="120px" />
                  </VStack>
                </Card.Body>
              </Card.Root>
            ))}
          </VStack>
        </Card.Body>
      </Card.Root>
    </VStack>
  )
}
