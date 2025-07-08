import { Box, HStack, Text, VStack } from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import { memo } from "react"

import type { Quiz } from "@/client/types.gen"
import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import { PROCESSING_STATUSES, UI_COLORS, UI_TEXT } from "@/lib/constants"
import { getQuizProcessingPhase, getQuizProgressPercentage } from "@/lib/utils"
import { QuizBadges } from "./QuizBadges"
import { QuizProgressIndicator } from "./QuizProgressIndicator"

interface QuizGenerationCardProps {
  quiz: Quiz
}

export const QuizGenerationCard = memo(function QuizGenerationCard({
  quiz,
}: QuizGenerationCardProps) {
  const processingPhase = getQuizProcessingPhase(quiz)
  const progressPercentage = getQuizProgressPercentage(quiz)

  return (
    <Box
      p={4}
      border="1px solid"
      borderColor={UI_COLORS.BORDER.PROCESSING}
      borderRadius="md"
      bg={UI_COLORS.BACKGROUND.PROCESSING}
      _hover={{ bg: "orange.100" }}
      transition="background-color 0.2s"
    >
      <VStack align="stretch" gap={3}>
        {/* Header with title and status */}
        <HStack justify="space-between" align="start">
          <VStack align="start" gap={1} flex={1}>
            <Text fontWeight="medium" fontSize="sm" lineHeight="tight">
              {quiz.title}
            </Text>
            <Text fontSize="xs" color="gray.600">
              {quiz.canvas_course_name}
            </Text>
          </VStack>
          <HStack gap={2}>
            <StatusLight
              extractionStatus={
                quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
              }
              generationStatus={
                quiz.llm_generation_status || PROCESSING_STATUSES.PENDING
              }
            />
          </HStack>
        </HStack>

        {/* Progress indicator */}
        <QuizProgressIndicator
          processingPhase={processingPhase}
          progressPercentage={progressPercentage}
        />

        {/* Footer with badges and action */}
        <HStack justify="space-between" align="center">
          <QuizBadges
            questionCount={quiz.question_count || 0}
            llmModel={quiz.llm_model}
          />

          <Button size="sm" variant="outline" asChild>
            <RouterLink to="/quiz/$id" params={{ id: quiz.id || "" }}>
              {UI_TEXT.ACTIONS.VIEW_DETAILS}
            </RouterLink>
          </Button>
        </HStack>
      </VStack>
    </Box>
  )
})
