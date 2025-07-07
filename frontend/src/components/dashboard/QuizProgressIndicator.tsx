import { Box, HStack, Progress, Text } from "@chakra-ui/react"
import { memo } from "react"

interface QuizProgressIndicatorProps {
  processingPhase: string
  progressPercentage: number
}

export const QuizProgressIndicator = memo(function QuizProgressIndicator({
  processingPhase,
  progressPercentage,
}: QuizProgressIndicatorProps) {
  return (
    <Box>
      <HStack justify="space-between" mb={2}>
        <Text fontSize="xs" color="gray.700" fontWeight="medium">
          {processingPhase}
        </Text>
        <Text fontSize="xs" color="gray.600">
          {progressPercentage}%
        </Text>
      </HStack>
      <Progress.Root value={progressPercentage} size="sm" colorPalette="orange">
        <Progress.Track>
          <Progress.Range />
        </Progress.Track>
      </Progress.Root>
    </Box>
  )
})
