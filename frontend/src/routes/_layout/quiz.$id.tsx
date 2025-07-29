import {
  Box,
  Button,
  Card,
  Container,
  HStack,
  Tabs,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import {
  Outlet,
  createFileRoute,
  useRouter,
  useRouterState,
} from "@tanstack/react-router"

import { type Quiz, QuizService } from "@/client"
import { ErrorState, LoadingSkeleton } from "@/components/Common"
import DeleteQuizConfirmation from "@/components/QuizCreation/DeleteQuizConfirmation"
import { StatusLight } from "@/components/ui/status-light"
import { useConditionalPolling, useQuizStatusPolling } from "@/hooks/common"
import { QUIZ_STATUS, UI_SIZES } from "@/lib/constants"
import { queryKeys, quizQueryConfig } from "@/lib/queryConfig"

export const Route = createFileRoute("/_layout/quiz/$id")({
  component: QuizLayout,
})

function QuizLayout() {
  const { id } = Route.useParams()
  const router = useRouter()
  const globalPollingInterval = useQuizStatusPolling()

  // Use router state to detect current route more reliably
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })
  const isQuestionsRoute = pathname.endsWith("/questions")
  const isIndexRoute = pathname === `/quiz/${id}` || pathname === `/quiz/${id}/`

  // Custom polling logic for index route - stops polling for stable states
  const indexPolling = useConditionalPolling<Quiz>((data) => {
    if (!data?.status) return true // Poll if no status yet

    // Stop polling for stable/terminal states on index route to save resources
    const stableStates = [
      QUIZ_STATUS.READY_FOR_REVIEW, // Quiz is stable, waiting for user review
      QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL, // Quiz is stable with partial success, waiting for user retry
      QUIZ_STATUS.PUBLISHED, // Quiz is completed and exported
      QUIZ_STATUS.FAILED, // Terminal error state
    ] as const

    return !stableStates.includes(data.status as (typeof stableStates)[number])
  }, 3000) // 3-second interval for active processing states

  // Determine polling strategy based on route
  const getPollingInterval = () => {
    if (isQuestionsRoute) return false // No polling on questions page
    if (isIndexRoute) return indexPolling // Custom polling logic for index route
    return globalPollingInterval // Default polling for other routes
  }

  const {
    data: quiz,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKeys.quiz(id),
    queryFn: async () => {
      const response = await QuizService.getQuiz({ quizId: id })
      return response
    },
    ...quizQueryConfig,
    refetchInterval: getPollingInterval(),
    refetchIntervalInBackground: false,
  })

  if (isLoading) {
    return <QuizLayoutSkeleton />
  }

  if (error || !quiz) {
    return (
      <Container maxW="4xl" py={8}>
        <Card.Root>
          <Card.Body>
            <ErrorState
              title="Quiz Not Found"
              message="The quiz you're looking for doesn't exist or you don't have permission to view it."
              showRetry={false}
            />
          </Card.Body>
        </Card.Root>
      </Container>
    )
  }

  // Check if quiz is ready for approval
  const isQuizReadyForApproval =
    quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
    quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL

  return (
    <Container maxW="6xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Box>
          <HStack gap={3} align="center" justify="space-between">
            <HStack gap={3} align="center">
              <Text fontSize="3xl" fontWeight="bold">
                {quiz.title}
              </Text>
              <StatusLight status={quiz.status || "created"} />
            </HStack>
            <HStack gap={3}>
              {isQuizReadyForApproval && (
                <Button
                  colorPalette="blue"
                  size="sm"
                  onClick={() =>
                    router.navigate({
                      to: "/quiz/$id/questions",
                      params: { id },
                    })
                  }
                >
                  Review
                </Button>
              )}
              <DeleteQuizConfirmation quizId={id} quizTitle={quiz.title} />
            </HStack>
          </HStack>
        </Box>

        {/* Tabs */}
        <Tabs.Root value={isQuestionsRoute ? "questions" : "info"} size="lg">
          <Tabs.List>
            <Tabs.Trigger
              value="info"
              onClick={() =>
                router.navigate({
                  to: "/quiz/$id",
                  params: { id },
                })
              }
            >
              Quiz Information
            </Tabs.Trigger>
            <Tabs.Trigger
              value="questions"
              onClick={() =>
                router.navigate({
                  to: "/quiz/$id/questions",
                  params: { id },
                })
              }
            >
              Questions
            </Tabs.Trigger>
          </Tabs.List>

          <Box mt={6}>
            <Outlet />
          </Box>
        </Tabs.Root>
      </VStack>
    </Container>
  )
}

function QuizLayoutSkeleton() {
  return (
    <Container maxW="4xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header Skeleton */}
        <Box>
          <LoadingSkeleton
            height={UI_SIZES.SKELETON.HEIGHT.XXL}
            width={UI_SIZES.SKELETON.WIDTH.TEXT_XL}
          />
          <Box mt={2}>
            <LoadingSkeleton
              height={UI_SIZES.SKELETON.HEIGHT.XL}
              width={UI_SIZES.SKELETON.WIDTH.TEXT_MD}
            />
          </Box>
        </Box>

        {/* Cards Skeleton */}
        {[1, 2, 3, 4].map((i) => (
          <Card.Root key={i}>
            <Card.Header>
              <LoadingSkeleton
                height={UI_SIZES.SKELETON.HEIGHT.XL}
                width={UI_SIZES.SKELETON.WIDTH.TEXT_LG}
              />
            </Card.Header>
            <Card.Body>
              <VStack gap={3} align="stretch">
                <LoadingSkeleton
                  height={UI_SIZES.SKELETON.HEIGHT.LG}
                  width={UI_SIZES.SKELETON.WIDTH.FULL}
                  lines={3}
                />
              </VStack>
            </Card.Body>
          </Card.Root>
        ))}
      </VStack>
    </Container>
  )
}
