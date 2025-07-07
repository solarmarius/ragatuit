import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import { memo } from "react"

import type { Quiz } from "@/client/types.gen"
import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import { PROCESSING_STATUSES } from "@/lib/constants"

interface QuizListCardProps {
  quiz: Quiz
  actionButton?: {
    text: string
    to: string
    params?: Record<string, any>
    search?: Record<string, any>
  }
  showCourseInfo?: boolean
  compact?: boolean
}

export const QuizListCard = memo(function QuizListCard({
  quiz,
  actionButton = { text: "View", to: `/quiz/${quiz.id}` },
  showCourseInfo = true,
  compact = false,
}: QuizListCardProps) {
  return (
    <Box
      p={compact ? 3 : 4}
      border="1px solid"
      borderColor="gray.200"
      borderRadius="md"
      bg="gray.50"
      _hover={{ bg: "gray.100" }}
      transition="background-color 0.2s"
    >
      <VStack align="stretch" gap={compact ? 2 : 3}>
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
          {showCourseInfo && (
            <Text fontSize="xs" color="gray.600" truncate>
              {quiz.canvas_course_name}
            </Text>
          )}
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
              to={actionButton.to}
              params={actionButton.params}
              search={actionButton.search}
            >
              {actionButton.text}
            </RouterLink>
          </Button>
        </HStack>
      </VStack>
    </Box>
  )
})
