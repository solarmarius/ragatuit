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
import { UI_SIZES, UI_COLORS, UI_TEXT } from "@/lib/constants"

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
            {generatingQuizzes.slice(0, UI_SIZES.PANEL.MAX_ITEMS).map((quiz) => {
              const processingPhase = getQuizProcessingPhase(quiz)
              const progressPercentage = getQuizProgressPercentage(quiz)

              return (
                <Box
                  key={quiz.id}
                  p={4}
                  border="1px solid"
                  borderColor={UI_COLORS.BORDER.PROCESSING}
                  borderRadius="md"
                  bg={UI_COLORS.BACKGROUND.PROCESSING}
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
                          {UI_TEXT.ACTIONS.VIEW_DETAILS}
                        </RouterLink>
                      </Button>
                    </HStack>
                  </VStack>
                </Box>
              )
            })}

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

function QuizGenerationPanelSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.XL} width={UI_SIZES.SKELETON.WIDTH.TEXT_LG} />
          <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.LG} width={UI_SIZES.SKELETON.WIDTH.XS} />
        </HStack>
        <Box mt={2}>
          <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.MD} width={UI_SIZES.SKELETON.WIDTH.TEXT_LG} />
        </Box>
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          {[1, 2].map((i) => (
            <Box
              key={i}
              p={4}
              border="1px solid"
              borderColor={UI_COLORS.BORDER.PROCESSING}
              borderRadius="md"
              bg={UI_COLORS.BACKGROUND.PROCESSING}
            >
              <VStack align="stretch" gap={3}>
                <HStack justify="space-between" align="start">
                  <VStack align="start" gap={1} flex={1}>
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.MD} width={UI_SIZES.SKELETON.WIDTH.TEXT_MD} />
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.WIDTH.XL} />
                  </VStack>
                  <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.HEIGHT.SM} />
                </HStack>

                <Box>
                  <HStack justify="space-between" mb={2}>
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.WIDTH.XXL} />
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.WIDTH.XS} />
                  </HStack>
                  <LoadingSkeleton height={UI_SIZES.PANEL.PROGRESS_HEIGHT} width={UI_SIZES.SKELETON.WIDTH.FULL} />
                </Box>

                <HStack justify="space-between" align="center">
                  <HStack gap={2}>
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.LG} width={UI_SIZES.SKELETON.WIDTH.LG} />
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.LG} width={UI_SIZES.SKELETON.WIDTH.MD} />
                  </HStack>
                  <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.XL} width={UI_SIZES.SKELETON.WIDTH.LG} />
                </HStack>
              </VStack>
            </Box>
          ))}
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
