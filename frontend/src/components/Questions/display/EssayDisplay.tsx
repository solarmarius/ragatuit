import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Badge, Box, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"
import { GradingRubricBox } from "../shared/GradingRubricBox"
import { SampleAnswerBox } from "../shared/SampleAnswerBox"
import { ErrorDisplay } from "./ErrorDisplay"

interface EssayDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

export const EssayDisplay = memo(function EssayDisplay({
  question,
  showCorrectAnswer,
}: EssayDisplayProps) {
  try {
    const essayData = extractQuestionData(question, "essay")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {essayData.question_text}
          </Text>
        </Box>

        {essayData.expected_length && (
          <Box>
            <Text fontSize="sm" color="gray.600">
              Expected length:{" "}
              <Badge size="sm" colorScheme="blue">
                {essayData.expected_length}
              </Badge>
            </Text>
          </Box>
        )}

        {essayData.max_words && (
          <Box>
            <Text fontSize="sm" color="gray.600">
              Maximum words:{" "}
              <Badge size="sm" colorScheme="orange">
                {essayData.max_words}
              </Badge>
            </Text>
          </Box>
        )}

        {showCorrectAnswer && essayData.grading_rubric && (
          <GradingRubricBox rubric={essayData.grading_rubric} />
        )}

        {showCorrectAnswer && essayData.sample_answer && (
          <SampleAnswerBox sampleAnswer={essayData.sample_answer} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading Essay question data" />
  }
})
