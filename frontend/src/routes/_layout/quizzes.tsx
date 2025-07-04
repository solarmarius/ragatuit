import {
  Badge,
  Box,
  Card,
  Container,
  HStack,
  Skeleton,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react"
import { Link as RouterLink, createFileRoute } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import { useUserQuizzes } from "@/hooks/api"
import { formatDate } from "@/lib/utils"
import useCustomToast from "@/hooks/useCustomToast"

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
            <VStack gap={4}>
              <Text fontSize="xl" fontWeight="bold" color="red.500">
                Failed to Load Quizzes
              </Text>
              <Text color="gray.600">
                There was an error loading your quizzes. Please try again.
              </Text>
            </VStack>
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
            <Card.Body textAlign="center" py={12}>
              <VStack gap={4}>
                <Text fontSize="lg" fontWeight="semibold" color="gray.600">
                  No Quizzes Found
                </Text>
                <Text color="gray.500">
                  You haven't created any quizzes yet. Get started by creating
                  your first quiz.
                </Text>
                <Button asChild mt={4}>
                  <RouterLink to="/create-quiz">
                    Create Your First Quiz
                  </RouterLink>
                </Button>
              </VStack>
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
            <Skeleton height="36px" width="200px" mb={2} />
            <Skeleton height="20px" width="300px" />
          </Box>
          <Skeleton height="40px" width="150px" />
        </HStack>

        {/* Table Skeleton */}
        <Card.Root>
          <Card.Body p={0}>
            <VStack gap={4} p={6}>
              {[1, 2, 3, 4, 5].map((i) => (
                <HStack key={i} justify="space-between" width="100%">
                  <Skeleton height="20px" width="200px" />
                  <Skeleton height="20px" width="150px" />
                  <Skeleton height="20px" width="60px" />
                  <Skeleton height="20px" width="80px" />
                  <Skeleton height="20px" width="100px" />
                  <Skeleton height="32px" width="60px" />
                </HStack>
              ))}
            </VStack>
          </Card.Body>
        </Card.Root>
      </VStack>
    </Container>
  )
}
