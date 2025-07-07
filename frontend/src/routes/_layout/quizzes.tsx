import {
  Box,
  Card,
  Container,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react"
import { Link as RouterLink, createFileRoute } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import { EmptyState, ErrorState, LoadingSkeleton, QuizTable } from "@/components/common"
import { useUserQuizzes } from "@/hooks/api"
import { useCustomToast } from "@/hooks/common"
import { UI_TEXT, UI_SIZES } from "@/lib/constants"

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
            <RouterLink to="/create-quiz">{UI_TEXT.ACTIONS.CREATE_QUIZ}</RouterLink>
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
            <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.XXL} width={UI_SIZES.SKELETON.WIDTH.TEXT_LG} />
            <Box mt={2}>
              <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.LG} width={UI_SIZES.SKELETON.WIDTH.TEXT_XL} />
            </Box>
          </Box>
          <LoadingSkeleton height="40px" width={UI_SIZES.SKELETON.WIDTH.TEXT_MD} />
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
