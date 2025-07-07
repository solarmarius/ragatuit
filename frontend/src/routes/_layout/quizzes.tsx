import {
  Badge,
  Box,
  Card,
  Container,
  HStack,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react"
import { Link as RouterLink, createFileRoute } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/common"
import { useUserQuizzes } from "@/hooks/api"
import { formatDate } from "@/lib/utils"
import { useCustomToast } from "@/hooks/common"

export const Route = createFileRoute("/_layout/quizzes")({
  component: QuizList,
})

function QuizList() {
  const { showErrorToast } = useCustomToast()

  const {
    data: quizzes,
    isLoading,
    error,
  } = useUserQuizzes()

  if (isLoading) {
    return <QuizListSkeleton />
  }

  if (error) {
    showErrorToast("Failed to load quizzes")
    return (
      <Container maxW="6xl" py={8}>
        <Card.Root>
          <Card.Body>
            <ErrorState
              title="Failed to Load Quizzes"
              message="There was an error loading your quizzes. Please try again."
              showRetry={false}
            />
          </Card.Body>
        </Card.Root>
      </Container>
    )
  }

  return (
    <Container maxW="6xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <Box>
            <Text fontSize="3xl" fontWeight="bold">
              My Quizzes
            </Text>
            <Text color="gray.600">
              Manage and view all your created quizzes
            </Text>
          </Box>
          <Button asChild>
            <RouterLink to="/create-quiz">Create New Quiz</RouterLink>
          </Button>
        </HStack>

        {/* Quizzes Table */}
        {!quizzes || quizzes.length === 0 ? (
          <Card.Root>
            <Card.Body>
              <EmptyState
                title="No Quizzes Found"
                description="You haven't created any quizzes yet. Get started by creating your first quiz."
                action={
                  <Button asChild>
                    <RouterLink to="/create-quiz">
                      Create Your First Quiz
                    </RouterLink>
                  </Button>
                }
              />
            </Card.Body>
          </Card.Root>
        ) : (
          <Card.Root>
            <Card.Body p={0}>
              <Table.Root>
                <Table.Header>
                  <Table.Row>
                    <Table.ColumnHeader>Quiz Title</Table.ColumnHeader>
                    <Table.ColumnHeader>Course</Table.ColumnHeader>
                    <Table.ColumnHeader>Questions</Table.ColumnHeader>
                    <Table.ColumnHeader>LLM Model</Table.ColumnHeader>
                    <Table.ColumnHeader>Status</Table.ColumnHeader>
                    <Table.ColumnHeader>Created</Table.ColumnHeader>
                    <Table.ColumnHeader>Actions</Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {quizzes.map((quiz) => {
                    // Get selected modules for display (already an object from API)
                    const selectedModules = quiz.selected_modules || {}
                    const moduleCount = Object.keys(selectedModules).length

                    return (
                      <Table.Row key={quiz.id}>
                        <Table.Cell>
                          <VStack align="start" gap={1}>
                            <Text fontWeight="medium">{quiz.title}</Text>
                            <Text fontSize="sm" color="gray.500">
                              {moduleCount} module{moduleCount !== 1 ? "s" : ""}{" "}
                              selected
                            </Text>
                          </VStack>
                        </Table.Cell>
                        <Table.Cell>
                          <VStack align="start" gap={1}>
                            <Text>{quiz.canvas_course_name}</Text>
                            <Text fontSize="sm" color="gray.500">
                              ID: {quiz.canvas_course_id}
                            </Text>
                          </VStack>
                        </Table.Cell>
                        <Table.Cell>
                          <Badge variant="solid" colorScheme="blue">
                            {quiz.question_count}
                          </Badge>
                        </Table.Cell>
                        <Table.Cell>
                          <Badge variant="outline" colorScheme="purple">
                            {quiz.llm_model}
                          </Badge>
                        </Table.Cell>
                        <Table.Cell>
                          <HStack gap={2} align="center">
                            <StatusLight
                              extractionStatus={
                                quiz.content_extraction_status || "pending"
                              }
                              generationStatus={
                                quiz.llm_generation_status || "pending"
                              }
                            />
                            <Text fontSize="sm" color="gray.600">
                              {(() => {
                                const extractionStatus =
                                  quiz.content_extraction_status || "pending"
                                const generationStatus =
                                  quiz.llm_generation_status || "pending"

                                if (
                                  extractionStatus === "failed" ||
                                  generationStatus === "failed"
                                ) {
                                  return "Failed"
                                }

                                if (
                                  extractionStatus === "completed" &&
                                  generationStatus === "completed"
                                ) {
                                  return "Complete"
                                }

                                if (
                                  extractionStatus === "processing" ||
                                  generationStatus === "processing"
                                ) {
                                  return "Processing"
                                }

                                return "Pending"
                              })()}
                            </Text>
                          </HStack>
                        </Table.Cell>
                        <Table.Cell>
                          <Text fontSize="sm">
                            {quiz.created_at
                              ? formatDate(quiz.created_at)
                              : "Unknown"}
                          </Text>
                        </Table.Cell>
                        <Table.Cell>
                          <HStack gap={2}>
                            <Button size="sm" variant="outline" asChild>
                              <RouterLink to={`/quiz/${quiz.id}`}>
                                View
                              </RouterLink>
                            </Button>
                          </HStack>
                        </Table.Cell>
                      </Table.Row>
                    )
                  })}
                </Table.Body>
              </Table.Root>
            </Card.Body>
          </Card.Root>
        )}
      </VStack>
    </Container>
  )
}

function QuizListSkeleton() {
  return (
    <Container maxW="6xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header Skeleton */}
        <HStack justify="space-between" align="center">
          <Box>
            <LoadingSkeleton height="36px" width="200px" />
            <Box mt={2}>
              <LoadingSkeleton height="20px" width="300px" />
            </Box>
          </Box>
          <LoadingSkeleton height="40px" width="150px" />
        </HStack>

        {/* Table Skeleton */}
        <Card.Root>
          <Card.Body p={0}>
            <VStack gap={4} p={6}>
              {[1, 2, 3, 4, 5].map((i) => (
                <HStack key={i} justify="space-between" width="100%">
                  <LoadingSkeleton height="20px" width="200px" />
                  <LoadingSkeleton height="20px" width="150px" />
                  <LoadingSkeleton height="20px" width="60px" />
                  <LoadingSkeleton height="20px" width="80px" />
                  <LoadingSkeleton height="20px" width="100px" />
                  <LoadingSkeleton height="32px" width="60px" />
                </HStack>
              ))}
            </VStack>
          </Card.Body>
        </Card.Root>
      </VStack>
    </Container>
  )
}
