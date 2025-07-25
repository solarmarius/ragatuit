import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"

import type { QuestionBatch } from "@/client/types.gen"
import { formatQuestionTypeDisplay, calculateModuleQuestions } from "@/lib/utils"

interface ModuleQuestionSummaryProps {
  moduleName: string
  questionBatches?: QuestionBatch[]
}

/**
 * Component to display question summary for a single module
 *
 * @param moduleName - The name of the module
 * @param questionBatches - Array of question batches for this module
 */
export const ModuleQuestionSummary = memo(function ModuleQuestionSummary({
  moduleName,
  questionBatches = []
}: ModuleQuestionSummaryProps) {
  const totalQuestions = calculateModuleQuestions(questionBatches)

  if (questionBatches.length === 0) {
    return (
      <Box>
        <Text fontWeight="medium">{moduleName}</Text>
        <Text fontSize="sm" color="gray.500">No questions configured</Text>
      </Box>
    )
  }

  return (
    <VStack align="stretch" gap={2}>
      <HStack justify="space-between">
        <Text fontWeight="medium">{moduleName}</Text>
        <Text fontSize="sm" color="gray.600">
          {totalQuestions} total questions
        </Text>
      </HStack>

      <HStack gap={2} flexWrap="wrap">
        {questionBatches.map((batch, index) => (
          <Badge key={index} variant="solid" colorScheme="blue" size="sm">
            {batch.count} {formatQuestionTypeDisplay(batch.question_type)}
          </Badge>
        ))}
      </HStack>
    </VStack>
  )
})
