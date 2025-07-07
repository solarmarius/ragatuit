import {
  Badge,
  Box,
  Card,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"

import type { Quiz } from "@/client/types.gen"
import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import { EmptyState, LoadingSkeleton } from "@/components/common"
import { getQuizzesNeedingReview } from "@/lib/utils"
import { UI_SIZES, UI_TEXT, PROCESSING_STATUSES } from "@/lib/constants"

interface QuizReviewPanelProps {
  quizzes: Quiz[]
  isLoading: boolean
}

export function QuizReviewPanel({ quizzes, isLoading }: QuizReviewPanelProps) {
  const reviewQuizzes = getQuizzesNeedingReview(quizzes)

  if (isLoading) {
    return <QuizReviewPanelSkeleton />
  }

  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <Text fontSize="lg" fontWeight="semibold">
            Quizzes Needing Review
          </Text>
          <Badge variant="outline" colorScheme="green" data-testid="badge">
            {reviewQuizzes.length}
          </Badge>
        </HStack>
        <Text fontSize="sm" color="gray.600">
          Completed quizzes ready for question approval
        </Text>
      </Card.Header>
      <Card.Body>
        {reviewQuizzes.length === 0 ? (
          <EmptyState
            title={UI_TEXT.EMPTY_STATES.NO_QUIZZES_REVIEW}
            description="Generated quizzes will appear here when ready for approval"
          />
        ) : (
          <VStack gap={4} align="stretch">
            {reviewQuizzes.slice(0, UI_SIZES.PANEL.MAX_ITEMS + 1).map((quiz) => (
              <Box
                key={quiz.id}
                p={3}
                border="1px solid"
                borderColor="gray.200"
                borderRadius="md"
                bg="gray.50"
                _hover={{ bg: "gray.100" }}
                transition="background-color 0.2s"
              >
                <VStack align="stretch" gap={2}>
                  <VStack align="start" gap={1}>
                    <HStack justify="space-between" align="start" width="100%">
                      <Text
                        fontWeight="medium"
                        fontSize="sm"
                        lineHeight="tight"
                        truncate
                      >
                        {quiz.title}
                      </Text>
                      <StatusLight
                        extractionStatus={
                          quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
                        }
                        generationStatus={
                          quiz.llm_generation_status || PROCESSING_STATUSES.PENDING
                        }
                      />
                    </HStack>
                    <Text fontSize="xs" color="gray.600" truncate>
                      {quiz.canvas_course_name}
                    </Text>
                  </VStack>

                  <HStack
                    justify="space-between"
                    align="center"
                    gap={2}
                    flexWrap="wrap"
                  >
                    <HStack gap={2} flex="1" minW="0">
                      <Badge
                        variant="solid"
                        colorScheme="blue"
                        size="sm"
                        flexShrink={0}
                      >
                        {quiz.question_count} questions
                      </Badge>
                      {quiz.llm_model && (
                        <Badge
                          variant="outline"
                          colorScheme="purple"
                          size="sm"
                          flexShrink={0}
                        >
                          {quiz.llm_model}
                        </Badge>
                      )}
                    </HStack>

                    <Button size="sm" variant="outline" asChild flexShrink={0}>
                      <RouterLink
                        to="/quiz/$id"
                        params={{ id: quiz.id || "" }}
                        search={{ tab: "questions" }}
                      >
                        Review
                      </RouterLink>
                    </Button>
                  </HStack>
                </VStack>
              </Box>
            ))}

            {reviewQuizzes.length > 5 && (
              <Box textAlign="center" pt={2}>
                <Text fontSize="sm" color="gray.500">
                  +{reviewQuizzes.length - 5} more quizzes need review
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

function QuizReviewPanelSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.XL} width={UI_SIZES.SKELETON.WIDTH.TEXT_LG} />
          <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.LG} width={UI_SIZES.SKELETON.WIDTH.XS} />
        </HStack>
        <Box mt={2}>
          <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.MD} width={UI_SIZES.SKELETON.WIDTH.TEXT_XL} />
        </Box>
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          {[1, 2, 3].map((i) => (
            <Box
              key={i}
              p={4}
              border="1px solid"
              borderColor="gray.200"
              borderRadius="md"
              bg="gray.50"
            >
              <VStack align="stretch" gap={3}>
                <HStack justify="space-between" align="start">
                  <VStack align="start" gap={1} flex={1}>
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.MD} width={UI_SIZES.SKELETON.WIDTH.TEXT_MD} />
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.WIDTH.XL} />
                  </VStack>
                  <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.HEIGHT.SM} />
                </HStack>

                <HStack justify="space-between" align="center">
                  <HStack gap={2}>
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.LG} width={UI_SIZES.SKELETON.WIDTH.LG} />
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.LG} width={UI_SIZES.SKELETON.WIDTH.MD} />
                  </HStack>
                  <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.XL} width={UI_SIZES.SKELETON.WIDTH.XL} />
                </HStack>
              </VStack>
            </Box>
          ))}
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
