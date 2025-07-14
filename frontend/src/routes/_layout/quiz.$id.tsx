import {
  Badge,
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
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"

import { QuizService } from "@/client"
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/Common"
import { QuestionGenerationTrigger } from "@/components/Questions/QuestionGenerationTrigger"
import { QuestionReview } from "@/components/Questions/QuestionReview"
import { QuestionStats } from "@/components/Questions/QuestionStats"
import DeleteQuizConfirmation from "@/components/QuizCreation/DeleteQuizConfirmation"
import { QuizPhaseProgress } from "@/components/ui/quiz-phase-progress"
import { StatusLight } from "@/components/ui/status-light"
import { useFormattedDate, useQuizStatusPolling } from "@/hooks/common"
import { FAILURE_REASON, QUIZ_STATUS, UI_SIZES, UI_TEXT } from "@/lib/constants"

export const Route = createFileRoute("/_layout/quiz/$id")({
  component: QuizDetail,
})

function DateDisplay({ date }: { date: string | null | undefined }) {
  const formattedDate = useFormattedDate(date, "default")

  if (!formattedDate) return <Text color="gray.500">Not available</Text>

  return <Text color="gray.600">{formattedDate}</Text>
}

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

function QuizDetail() {
  const { id } = Route.useParams()
  const [currentTab, setCurrentTab] = useState("info")
  const pollingInterval = useQuizStatusPolling()

  const {
    data: quiz,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["quiz", id],
    queryFn: async () => {
      const response = await QuizService.getQuiz({ quizId: id })
      return response
    },
    refetchInterval: pollingInterval,
    refetchIntervalInBackground: false, // Only poll when tab is active
  })

  if (isLoading) {
    return <QuizDetailSkeleton />
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

  // Get selected modules - parse JSON string if needed
  const selectedModules = (() => {
    if (!quiz.selected_modules) return {}

    // If it's already an object, use it directly
    if (typeof quiz.selected_modules === "object") {
      return quiz.selected_modules
    }

    // If it's a string, parse it as JSON
    if (typeof quiz.selected_modules === "string") {
      try {
        return JSON.parse(quiz.selected_modules)
      } catch {
        return {}
      }
    }

    return {}
  })()

  const moduleNames = Object.values(selectedModules)
    .filter((moduleData): moduleData is { name: string; question_count: number } =>
      typeof moduleData === "object" &&
      moduleData !== null &&
      "name" in moduleData &&
      typeof moduleData.name === "string"
    )
    .map(moduleData => moduleData.name)

  // Check if quiz is ready for approval
  const isQuizReadyForApproval = quiz.status === QUIZ_STATUS.READY_FOR_REVIEW

  const handleApproveQuiz = () => {
    setCurrentTab("questions")
  }

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
                  onClick={handleApproveQuiz}
                >
                  Review Quiz
                </Button>
              )}
              <DeleteQuizConfirmation quizId={id} quizTitle={quiz.title} />
            </HStack>
          </HStack>
          <Text color="gray.600" fontSize="lg">
            Quiz Details
          </Text>
        </Box>

        {/* Tabs */}
        <Tabs.Root
          value={currentTab}
          onValueChange={(details) => setCurrentTab(details.value)}
          size="lg"
        >
          <Tabs.List>
            <Tabs.Trigger value="info">Quiz Information</Tabs.Trigger>
            <Tabs.Trigger value="questions">Questions</Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="info">
            <VStack gap={6} align="stretch" mt={6}>
              {/* Quiz Information */}
              <Card.Root>
                <Card.Header>
                  <Text fontSize="xl" fontWeight="semibold">
                    Course Information
                  </Text>
                </Card.Header>
                <Card.Body>
                  <VStack gap={4} align="stretch">
                    <Box>
                      <Text fontWeight="medium" color="gray.700">
                        Canvas Course
                      </Text>
                      <Text fontSize="lg">{quiz.canvas_course_name}</Text>
                      <Text fontSize="sm" color="gray.500">
                        Course ID: {quiz.canvas_course_id}
                      </Text>
                    </Box>

                    <Box>
                      <Text fontWeight="medium" color="gray.700" mb={2}>
                        Selected Modules
                      </Text>
                      {moduleNames.length > 0 ? (
                        <HStack wrap="wrap" gap={2}>
                          {moduleNames.map((moduleName, index) => (
                            <Badge
                              key={index}
                              variant="outline"
                              colorScheme="blue"
                            >
                              {moduleName}
                            </Badge>
                          ))}
                        </HStack>
                      ) : (
                        <Text color="gray.500">No modules selected</Text>
                      )}
                    </Box>
                  </VStack>
                </Card.Body>
              </Card.Root>

              {/* Quiz Settings */}
              <Card.Root>
                <Card.Header>
                  <Text fontSize="xl" fontWeight="semibold">
                    Quiz Settings
                  </Text>
                </Card.Header>
                <Card.Body>
                  <VStack gap={4} align="stretch">
                    <HStack justify="space-between">
                      <Text fontWeight="medium" color="gray.700">
                        Question Count
                      </Text>
                      <Badge variant="outline" colorScheme="purple">
                        {quiz.question_count}
                      </Badge>
                    </HStack>
                  </VStack>
                </Card.Body>
              </Card.Root>

              {/* Metadata */}
              <Card.Root>
                <Card.Header>
                  <Text fontSize="xl" fontWeight="semibold">
                    Quiz Metadata
                  </Text>
                </Card.Header>
                <Card.Body>
                  <VStack gap={4} align="stretch">
                    <HStack justify="space-between">
                      <Text fontWeight="medium" color="gray.700">
                        Quiz ID
                      </Text>
                      <Text fontSize="sm" fontFamily="mono" color="gray.600">
                        {quiz.id}
                      </Text>
                    </HStack>

                    {quiz.created_at && (
                      <HStack justify="space-between">
                        <Text fontWeight="medium" color="gray.700">
                          Created
                        </Text>
                        <DateDisplay date={quiz.created_at} />
                      </HStack>
                    )}

                    {quiz.updated_at && (
                      <HStack justify="space-between">
                        <Text fontWeight="medium" color="gray.700">
                          Last Updated
                        </Text>
                        <DateDisplay date={quiz.updated_at} />
                      </HStack>
                    )}
                  </VStack>
                </Card.Body>
              </Card.Root>

              {/* Quiz Generation Progress */}
              <Card.Root>
                <Card.Header>
                  <Text fontSize="xl" fontWeight="semibold">
                    Quiz Generation Progress
                  </Text>
                </Card.Header>
                <Card.Body>
                  <QuizPhaseProgress
                    status={quiz.status || "created"}
                    failureReason={quiz.failure_reason}
                    contentExtractedAt={quiz.content_extracted_at}
                    exportedAt={quiz.exported_at}
                    lastStatusUpdate={quiz.last_status_update}
                    showTimestamps={true}
                  />
                </Card.Body>
              </Card.Root>

              {/* Question Generation Trigger */}
              <QuestionGenerationTrigger quiz={quiz} />
            </VStack>
          </Tabs.Content>

          <Tabs.Content value="questions">
            <VStack gap={6} align="stretch" mt={6}>
              {/* Question Statistics */}
              {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
                quiz.status === QUIZ_STATUS.EXPORTING_TO_CANVAS ||
                quiz.status === QUIZ_STATUS.PUBLISHED ||
                (quiz.status === QUIZ_STATUS.FAILED &&
                  quiz.failure_reason ===
                    FAILURE_REASON.CANVAS_EXPORT_ERROR)) && (
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
                  quiz.failure_reason ===
                    FAILURE_REASON.CANVAS_EXPORT_ERROR)) && (
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
          </Tabs.Content>
        </Tabs.Root>
      </VStack>
    </Container>
  )
}

function QuizDetailSkeleton() {
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
