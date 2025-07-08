import { Badge, HStack } from "@chakra-ui/react"
import { memo } from "react"

interface QuizBadgesProps {
  questionCount: number
  llmModel?: string | null
}

export const QuizBadges = memo(function QuizBadges({
  questionCount,
  llmModel,
}: QuizBadgesProps) {
  return (
    <HStack gap={2}>
      <Badge variant="solid" colorScheme="blue" size="sm">
        {questionCount} questions
      </Badge>
      {llmModel && (
        <Badge variant="outline" colorScheme="purple" size="sm">
          {llmModel}
        </Badge>
      )}
    </HStack>
  )
})
