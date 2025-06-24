import {
  Badge,
  Box,
  Card,
  Container,
  HStack,
  Skeleton,
  Text,
  VStack,
} from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"

import { QuizService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/quiz/$id")({
  component: QuizDetail,
})

function QuizDetail() {
  const { id } = Route.useParams()
  const { showErrorToast } = useCustomToast()

  const {
    data: quiz,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["quiz", id],
    queryFn: async () => {
      try {
        const response = await QuizService.getQuiz({ quizId: id })
        return response
      } catch (err) {
        showErrorToast("Failed to load quiz details")
        throw err
      }
    },
  })

  if (isLoading) {
    return <QuizDetailSkeleton />
  }

  if (error || !quiz) {
    return (
      <Container maxW="4xl" py={8}>
        <Card.Root>
          <Card.Body>
            <VStack gap={4}>
              <Text fontSize="xl" fontWeight="bold" color="red.500">
                Quiz Not Found
              </Text>
              <Text color="gray.600">
                The quiz you're looking for doesn't exist or you don't have permission to view it.
              </Text>
            </VStack>
          </Card.Body>
        </Card.Root>
      </Container>
    )
  }

  // Parse selected modules from JSON string
  const selectedModules = JSON.parse(quiz.selected_modules || "{}")
  const moduleNames = Object.values(selectedModules) as string[]

  return (
    <Container maxW="4xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Box>
          <Text fontSize="3xl" fontWeight="bold">
            {quiz.title}
          </Text>
          <Text color="gray.600" fontSize="lg">
            Quiz Details
          </Text>
        </Box>

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
                      <Badge key={index} variant="outline" colorScheme="blue">
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
                <Badge variant="solid" colorScheme="green">
                  {quiz.question_count} questions
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
                    {new Date(quiz.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </Text>
                </HStack>
              )}

              {quiz.updated_at && (
                <HStack justify="space-between">
                  <Text fontWeight="medium" color="gray.700">
                    Last Updated
                  </Text>
                  <Text color="gray.600">
                    {new Date(quiz.updated_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </Text>
                </HStack>
              )}
            </VStack>
          </Card.Body>
        </Card.Root>

        {/* Placeholder for Future Features */}
        <Card.Root>
          <Card.Body>
            <VStack gap={3}>
              <Text fontSize="lg" fontWeight="semibold" color="gray.600">
                Coming Soon
              </Text>
              <Text color="gray.500" textAlign="center">
                Question generation, review, and export features will be available here.
              </Text>
            </VStack>
          </Card.Body>
        </Card.Root>
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
          <Skeleton height="40px" width="300px" mb={2} />
          <Skeleton height="24px" width="150px" />
        </Box>

        {/* Cards Skeleton */}
        {[1, 2, 3, 4].map((i) => (
          <Card.Root key={i}>
            <Card.Header>
              <Skeleton height="24px" width="200px" />
            </Card.Header>
            <Card.Body>
              <VStack gap={3} align="stretch">
                <Skeleton height="20px" width="100%" />
                <Skeleton height="20px" width="80%" />
                <Skeleton height="20px" width="60%" />
              </VStack>
            </Card.Body>
          </Card.Root>
        ))}
      </VStack>
    </Container>
  )
}
