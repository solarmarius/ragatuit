import { Badge } from "@chakra-ui/react"
import { memo } from "react"

interface QuizBadgesProps {
  questionCount: number
}

export const QuizBadges = memo(function QuizBadges({
  questionCount,
}: QuizBadgesProps) {
  return (
    <Badge variant="solid" colorScheme="blue" size="sm">
      {questionCount} questions
    </Badge>
  )
})
