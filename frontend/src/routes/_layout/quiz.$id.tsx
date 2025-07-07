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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"

import { QuizService } from "@/client"
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/common"
import { QuestionGenerationTrigger } from "@/components/Questions/QuestionGenerationTrigger"
import { QuestionReview } from "@/components/Questions/QuestionReview"
import { QuestionStats } from "@/components/Questions/QuestionStats"
import DeleteQuizConfirmation from "@/components/QuizCreation/DeleteQuizConfirmation"
import { StatusBadge } from "@/components/ui/status-badge"
import { StatusDescription } from "@/components/ui/status-description"
import { StatusLight } from "@/components/ui/status-light"
import { useCustomToast, useErrorHandler } from "@/hooks/common"

export const Route = createFileRoute("/_layout/quiz/$id")({
  component: QuizDetail,
})

function QuizDetail() {
  const { id } = Route.useParams()
  const { showSuccessToast } = useCustomToast()
  const { handleError } = useErrorHandler()
  const queryClient = useQueryClient()
  const [currentTab, setCurrentTab] = useState("info")

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
    refetchInterval: (query) => {
      // Poll every 5 seconds if any status is pending or processing
      const data = query?.state?.data
      if (data) {
        const extractionStatus = data.content_extraction_status || "pending"
        const generationStatus = data.llm_generation_status || "pending"
        const exportStatus = data.export_status || "pending"

        if (
          extractionStatus === "pending" ||
          extractionStatus === "processing" ||
          generationStatus === "pending" ||
          generationStatus === "processing" ||
          exportStatus === "pending" ||
          exportStatus === "processing"
        ) {
          return 5000 // 5 seconds
        }
      }
      return false // Stop polling when all are completed or failed
    },
    refetchIntervalInBackground: false, // Only poll when tab is active
  })

  // Retry content extraction mutation
  const retryExtractionMutation = useMutation({
    mutationFn: async () => {
      return await QuizService.triggerContentExtraction({ quizId: id })
    },
    onSuccess: () => {
      showSuccessToast("Content extraction restarted")
      queryClient.invalidateQueries({ queryKey: ["quiz", id] })
    },
    onError: handleError,
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

  // Get selected modules (already an object from API)
  const selectedModules = quiz.selected_modules || {}
  const moduleNames = Object.values(selectedModules) as string[]

  // Check if quiz is ready for approval
  const isQuizReadyForApproval =
    quiz.content_extraction_status === "completed" &&
    quiz.llm_generation_status === "completed"

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
              <StatusLight
                extractionStatus={quiz.content_extraction_status || "pending"}
                generationStatus={quiz.llm_generation_status || "pending"}
              />
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

                    <HStack justify="space-between">
                      <Text fontWeight="medium" color="gray.700">
                        LLM Model
                      </Text>
                      <Badge variant="outline" colorScheme="purple">
                        {quiz.llm_model}
                      </Badge>
                    </HStack>

                    <HStack justify="space-between">
                      <Text fontWeight="medium" color="gray.700">
                        Temperature
                      </Text>
                      <Badge variant="outline" colorScheme="orange">
                        {quiz.llm_temperature}
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
                        <Text color="gray.600">
                          {new Date(quiz.created_at).toLocaleDateString(
                            "en-GB",
                            {
                              year: "numeric",
                              month: "long",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            },
                          )}
                        </Text>
                      </HStack>
                    )}

                    {quiz.updated_at && (
                      <HStack justify="space-between">
                        <Text fontWeight="medium" color="gray.700">
                          Last Updated
                        </Text>
                        <Text color="gray.600">
                          {new Date(quiz.updated_at).toLocaleDateString(
                            "en-GB",
                            {
                              year: "numeric",
                              month: "long",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            },
                          )}
                        </Text>
                      </HStack>
                    )}
                  </VStack>
                </Card.Body>
              </Card.Root>

              {/* Quiz Generation Status */}
              <Card.Root>
                <Card.Header>
                  <Text fontSize="xl" fontWeight="semibold">
                    Quiz Generation Status
                  </Text>
                </Card.Header>
                <Card.Body>
                  <VStack gap={4} align="stretch">
                    {/* Content Extraction Status */}
                    <Box>
                      <HStack justify="space-between" mb={2}>
                        <Text fontWeight="medium" color="gray.700">
                          Content Extraction
                        </Text>
                        <StatusBadge
                          status={quiz.content_extraction_status || "pending"}
                        />
                      </HStack>
                      <StatusDescription
                        status={quiz.content_extraction_status || "pending"}
                        type="extraction"
                        timestamp={quiz.content_extracted_at || null}
                      />

                      {/* Retry button for failed content extraction */}
                      {quiz.content_extraction_status === "failed" && (
                        <Button
                          size="sm"
                          colorScheme="blue"
                          variant="outline"
                          loading={retryExtractionMutation.isPending}
                          onClick={() => retryExtractionMutation.mutate()}
                          mt={2}
                        >
                          Retry Content Extraction
                        </Button>
                      )}
                    </Box>

                    {/* LLM Generation Status */}
                    <Box>
                      <HStack justify="space-between" mb={2}>
                        <Text fontWeight="medium" color="gray.700">
                          Question Generation
                        </Text>
                        <StatusBadge
                          status={quiz.llm_generation_status || "pending"}
                        />
                      </HStack>
                      <StatusDescription
                        status={quiz.llm_generation_status || "pending"}
                        type="generation"
                      />
                    </Box>

                    {/* Canvas Export Status */}
                    <Box>
                      <HStack justify="space-between" mb={2}>
                        <Text fontWeight="medium" color="gray.700">
                          Canvas Export
                        </Text>
                        <StatusBadge status={quiz.export_status || "pending"} />
                      </HStack>
                      <StatusDescription
                        status={quiz.export_status || "pending"}
                        type="export"
                        timestamp={quiz.exported_at || null}
                      />
                    </Box>
                  </VStack>
                </Card.Body>
              </Card.Root>

              {/* Question Generation Trigger */}
              <QuestionGenerationTrigger quiz={quiz} />
            </VStack>
          </Tabs.Content>

          <Tabs.Content value="questions">
            <VStack gap={6} align="stretch" mt={6}>
              {/* Question Statistics */}
              {quiz.llm_generation_status === "completed" && (
                <QuestionStats quiz={quiz} />
              )}

              {/* Question Review */}
              {quiz.llm_generation_status === "completed" && (
                <QuestionReview quizId={id} />
              )}

              {/* Message when questions aren't ready */}
              {quiz.llm_generation_status !== "completed" && (
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
          <LoadingSkeleton height="40px" width="300px" />
          <Box mt={2}>
            <LoadingSkeleton height="24px" width="150px" />
          </Box>
        </Box>

        {/* Cards Skeleton */}
        {[1, 2, 3, 4].map((i) => (
          <Card.Root key={i}>
            <Card.Header>
              <LoadingSkeleton height="24px" width="200px" />
            </Card.Header>
            <Card.Body>
              <VStack gap={3} align="stretch">
                <LoadingSkeleton height="20px" width="100%" lines={3} />
              </VStack>
            </Card.Body>
          </Card.Root>
        ))}
      </VStack>
    </Container>
  )
}
