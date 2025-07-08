import { Badge, Box, Card, HStack, Text, VStack } from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import { memo, useMemo } from "react"

import type { Quiz } from "@/client/types.gen"
import { EmptyState, LoadingSkeleton, QuizListCard } from "@/components/common"
import { Button } from "@/components/ui/button"
import { UI_SIZES, UI_TEXT } from "@/lib/constants"
import { getQuizzesNeedingReview } from "@/lib/utils"

interface QuizReviewPanelProps {
  quizzes: Quiz[]
  isLoading: boolean
}

export const QuizReviewPanel = memo(function QuizReviewPanel({
  quizzes,
  isLoading,
}: QuizReviewPanelProps) {
  const reviewQuizzes = useMemo(
    () => getQuizzesNeedingReview(quizzes),
    [quizzes],
  )

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
            {reviewQuizzes.slice(0, UI_SIZES.PANEL.MAX_ITEMS).map((quiz) => (
              <QuizListCard
                key={quiz.id}
                quiz={quiz}
                actionButton={{
                  text: "Review",
                  to: "/quiz/$id",
                  params: { id: quiz.id || "" },
                }}
                compact
              />
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
})

function QuizReviewPanelSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <LoadingSkeleton
            height={UI_SIZES.SKELETON.HEIGHT.XL}
            width={UI_SIZES.SKELETON.WIDTH.TEXT_LG}
          />
          <LoadingSkeleton
            height={UI_SIZES.SKELETON.HEIGHT.LG}
            width={UI_SIZES.SKELETON.WIDTH.XS}
          />
        </HStack>
        <Box mt={2}>
          <LoadingSkeleton
            height={UI_SIZES.SKELETON.HEIGHT.MD}
            width={UI_SIZES.SKELETON.WIDTH.TEXT_XL}
          />
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
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.MD}
                      width={UI_SIZES.SKELETON.WIDTH.TEXT_MD}
                    />
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.SM}
                      width={UI_SIZES.SKELETON.WIDTH.XL}
                    />
                  </VStack>
                  <LoadingSkeleton
                    height={UI_SIZES.SKELETON.HEIGHT.SM}
                    width={UI_SIZES.SKELETON.HEIGHT.SM}
                  />
                </HStack>

                <HStack justify="space-between" align="center">
                  <HStack gap={2}>
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.LG}
                      width={UI_SIZES.SKELETON.WIDTH.LG}
                    />
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.LG}
                      width={UI_SIZES.SKELETON.WIDTH.MD}
                    />
                  </HStack>
                  <LoadingSkeleton
                    height={UI_SIZES.SKELETON.HEIGHT.XL}
                    width={UI_SIZES.SKELETON.WIDTH.XL}
                  />
                </HStack>
              </VStack>
            </Box>
          ))}
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
