import { Box, HStack, Text, VStack } from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import { memo } from "react"

import type { Quiz } from "@/client/types.gen"
import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import { UI_COLORS, UI_TEXT } from "@/lib/constants"
import { getQuizProgressPercentage, getQuizStatusText } from "@/lib/utils"
import { QuizBadges } from "./QuizBadges"
import { QuizProgressIndicator } from "./QuizProgressIndicator"

interface QuizGenerationCardProps {
  quiz: Quiz
}

export const QuizGenerationCard = memo(function QuizGenerationCard({
  quiz,
}: QuizGenerationCardProps) {
  const statusText = getQuizStatusText(quiz)
  const progressPercentage = getQuizProgressPercentage(quiz)

  return (
    <Box
      p={4}
      border="1px solid"
      borderColor={UI_COLORS.BORDER.ORANGE}
      borderRadius="md"
      bg={UI_COLORS.BACKGROUND.ORANGE}
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
            <StatusLight status={quiz.status || "created"} />
          </HStack>
        </HStack>

        {/* Progress indicator */}
        <QuizProgressIndicator
          processingPhase={statusText}
          progressPercentage={progressPercentage}
        />

        {/* Footer with badges and action */}
        <HStack justify="space-between" align="center">
          <QuizBadges questionCount={quiz.question_count || 0} />

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
