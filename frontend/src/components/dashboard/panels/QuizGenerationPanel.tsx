import {
  Badge,
  Box,
  Card,
  HStack,
  Progress,
  Text,
  VStack,
} from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"

import type { Quiz } from "@/client/types.gen"
import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import { EmptyState, LoadingSkeleton } from "@/components/common"
import { getQuizProcessingPhase, getQuizzesBeingGenerated, getQuizProgressPercentage } from "@/lib/utils"

interface QuizGenerationPanelProps {
  quizzes: Quiz[]
  isLoading: boolean
}

export function QuizGenerationPanel({
  quizzes,
  isLoading,
}: QuizGenerationPanelProps) {
  const generatingQuizzes = getQuizzesBeingGenerated(quizzes)

  if (isLoading) {
    return <QuizGenerationPanelSkeleton />
  }

  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <Text fontSize="lg" fontWeight="semibold">
            Quizzes Being Generated
          </Text>
          <Badge variant="outline" colorScheme="orange" data-testid="badge">
            {generatingQuizzes.length}
          </Badge>
        </HStack>
        <Text fontSize="sm" color="gray.600">
          Quizzes currently in progress
        </Text>
      </Card.Header>
      <Card.Body>
        {generatingQuizzes.length === 0 ? (
          <EmptyState
            title="No quizzes being generated"
            description="Start creating a quiz to see generation progress here"
            action={
              <Button size="sm" variant="outline" asChild>
                <RouterLink to="/create-quiz">Create New Quiz</RouterLink>
              </Button>
            }
          />
        ) : (
          <VStack gap={4} align="stretch">
            {generatingQuizzes.slice(0, 4).map((quiz) => {
              const processingPhase = getQuizProcessingPhase(quiz)
              const progressPercentage = getQuizProgressPercentage(quiz)

              return (
                <Box
                  key={quiz.id}
                  p={4}
                  border="1px solid"
                  borderColor="orange.200"
                  borderRadius="md"
                  bg="orange.50"
                  _hover={{ bg: "orange.100" }}
                  transition="background-color 0.2s"
                >
                  <VStack align="stretch" gap={3}>
                    <HStack justify="space-between" align="start">
                      <VStack align="start" gap={1} flex={1}>
                        <Text
                          fontWeight="medium"
                          fontSize="sm"
                          lineHeight="tight"
                        >
                          {quiz.title}
                        </Text>
                        <Text fontSize="xs" color="gray.600">
                          {quiz.canvas_course_name}
                        </Text>
                      </VStack>
                      <HStack gap={2}>
                        <StatusLight
                          extractionStatus={
                            quiz.content_extraction_status || "pending"
                          }
                          generationStatus={
                            quiz.llm_generation_status || "pending"
                          }
                        />
                      </HStack>
                    </HStack>

                    <Box>
                      <HStack justify="space-between" mb={2}>
                        <Text
                          fontSize="xs"
                          color="gray.700"
                          fontWeight="medium"
                        >
                          {processingPhase}
                        </Text>
                        <Text fontSize="xs" color="gray.600">
                          {progressPercentage}%
                        </Text>
                      </HStack>
                      <Progress.Root
                        value={progressPercentage}
                        size="sm"
                        colorPalette="orange"
                      >
                        <Progress.Track>
                          <Progress.Range />
                        </Progress.Track>
                      </Progress.Root>
                    </Box>

                    <HStack justify="space-between" align="center">
                      <HStack gap={2}>
                        <Badge variant="solid" colorScheme="blue" size="sm">
                          {quiz.question_count} questions
                        </Badge>
                        {quiz.llm_model && (
                          <Badge
                            variant="outline"
                            colorScheme="purple"
                            size="sm"
                          >
                            {quiz.llm_model}
                          </Badge>
                        )}
                      </HStack>

                      <Button size="sm" variant="outline" asChild>
                        <RouterLink
                          to="/quiz/$id"
                          params={{ id: quiz.id || "" }}
                        >
                          View Details
                        </RouterLink>
                      </Button>
                    </HStack>
                  </VStack>
                </Box>
              )
            })}

            {generatingQuizzes.length > 4 && (
              <Box textAlign="center" pt={2}>
                <Text fontSize="sm" color="gray.500">
                  +{generatingQuizzes.length - 4} more quizzes in progress
                </Text>
                <Button size="sm" variant="ghost" asChild mt={2}>
                  <RouterLink to="/quizzes">View All Quizzes</RouterLink>
                </Button>
              </Box>
            )}
          </VStack>
        )}
      </Card.Body>
    </Card.Root>
  )
}

function QuizGenerationPanelSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <LoadingSkeleton height="24px" width="180px" />
          <LoadingSkeleton height="20px" width="30px" />
        </HStack>
        <Box mt={2}>
          <LoadingSkeleton height="16px" width="200px" />
        </Box>
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          {[1, 2].map((i) => (
            <Box
              key={i}
              p={4}
              border="1px solid"
              borderColor="orange.200"
              borderRadius="md"
              bg="orange.50"
            >
              <VStack align="stretch" gap={3}>
                <HStack justify="space-between" align="start">
                  <VStack align="start" gap={1} flex={1}>
                    <LoadingSkeleton height="16px" width="140px" />
                    <LoadingSkeleton height="12px" width="100px" />
                  </VStack>
                  <LoadingSkeleton height="12px" width="12px" />
                </HStack>

                <Box>
                  <HStack justify="space-between" mb={2}>
                    <LoadingSkeleton height="12px" width="120px" />
                    <LoadingSkeleton height="12px" width="30px" />
                  </HStack>
                  <LoadingSkeleton height="6px" width="100%" />
                </Box>

                <HStack justify="space-between" align="center">
                  <HStack gap={2}>
                    <LoadingSkeleton height="20px" width="80px" />
                    <LoadingSkeleton height="20px" width="60px" />
                  </HStack>
                  <LoadingSkeleton height="24px" width="80px" />
                </HStack>
              </VStack>
            </Box>
          ))}
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
