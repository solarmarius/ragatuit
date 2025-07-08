import { Box, Card, Container, HStack, Text, VStack } from "@chakra-ui/react"
import { Link as RouterLink, createFileRoute } from "@tanstack/react-router"

import {
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  QuizTable,
  QuizTableSkeleton,
} from "@/components/Common"
import { Button } from "@/components/ui/button"
import { useUserQuizzes } from "@/hooks/api"
import { useErrorHandler } from "@/hooks/common"
import { UI_SIZES, UI_TEXT } from "@/lib/constants"

export const Route = createFileRoute("/_layout/quizzes")({
  component: QuizList,
})

function QuizList() {
  const { handleError } = useErrorHandler()

  const { data: quizzes, isLoading, error } = useUserQuizzes()

  if (isLoading) {
    return <QuizListSkeleton />
  }

  if (error) {
    handleError(error)
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
            <RouterLink to="/create-quiz">
              {UI_TEXT.ACTIONS.CREATE_QUIZ}
            </RouterLink>
          </Button>
        </HStack>

        {/* Quizzes Table */}
        {!quizzes || quizzes.length === 0 ? (
          <Card.Root>
            <Card.Body>
              <EmptyState
                title={UI_TEXT.EMPTY_STATES.NO_QUIZZES}
                description="You haven't created any quizzes yet. Get started by creating your first quiz."
                action={
                  <Button asChild>
                    <RouterLink to="/create-quiz">
                      {UI_TEXT.ACTIONS.CREATE_FIRST_QUIZ}
                    </RouterLink>
                  </Button>
                }
              />
            </Card.Body>
          </Card.Root>
        ) : (
          <QuizTable quizzes={quizzes} />
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
            <LoadingSkeleton
              height={UI_SIZES.SKELETON.HEIGHT.XXL}
              width={UI_SIZES.SKELETON.WIDTH.TEXT_LG}
            />
            <Box mt={2}>
              <LoadingSkeleton
                height={UI_SIZES.SKELETON.HEIGHT.LG}
                width={UI_SIZES.SKELETON.WIDTH.TEXT_XL}
              />
            </Box>
          </Box>
          <LoadingSkeleton
            height={UI_SIZES.SKELETON.HEIGHT.XXL}
            width={UI_SIZES.SKELETON.WIDTH.TEXT_MD}
          />
        </HStack>

        {/* Table Skeleton */}
        <QuizTableSkeleton />
      </VStack>
    </Container>
  )
}
