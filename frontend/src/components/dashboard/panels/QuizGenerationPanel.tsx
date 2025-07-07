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
import { EmptyState } from "@/components/common"
import { getQuizzesBeingGenerated } from "@/lib/utils"
import { UI_SIZES, UI_TEXT } from "@/lib/constants"
import { QuizGenerationCard } from "../QuizGenerationCard"
import { QuizGenerationPanelSkeleton } from "../QuizGenerationPanelSkeleton"

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
            title={UI_TEXT.EMPTY_STATES.NO_QUIZZES_GENERATING}
            description="Start creating a quiz to see generation progress here"
            action={
              <Button size="sm" variant="outline" asChild>
                <RouterLink to="/create-quiz">{UI_TEXT.ACTIONS.CREATE_QUIZ}</RouterLink>
              </Button>
            }
          />
        ) : (
          <VStack gap={4} align="stretch">
            {generatingQuizzes.slice(0, UI_SIZES.PANEL.MAX_ITEMS).map((quiz) => (
              <QuizGenerationCard key={quiz.id} quiz={quiz} />
            ))}

            {generatingQuizzes.length > UI_SIZES.PANEL.MAX_ITEMS && (
              <Box textAlign="center" pt={2}>
                <Text fontSize="sm" color="gray.500">
                  +{generatingQuizzes.length - UI_SIZES.PANEL.MAX_ITEMS} more quizzes in progress
                </Text>
                <Button size="sm" variant="ghost" asChild mt={2}>
                  <RouterLink to="/quizzes">{UI_TEXT.ACTIONS.VIEW_ALL}</RouterLink>
                </Button>
              </Box>
            )}
          </VStack>
        )}
      </Card.Body>
    </Card.Root>
  )
}
