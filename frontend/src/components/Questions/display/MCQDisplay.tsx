import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"
import { ExplanationBox } from "../shared/ExplanationBox"
import { ErrorDisplay } from "./ErrorDisplay"

interface MCQDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
}

export const MCQDisplay = memo(function MCQDisplay({
  question,
  showCorrectAnswer,
}: MCQDisplayProps) {
  try {
    const mcqData = extractQuestionData(question, "multiple_choice")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {mcqData.question_text}
          </Text>
        </Box>

        <VStack gap={2} align="stretch">
          {[
            { key: "A", text: mcqData.option_a },
            { key: "B", text: mcqData.option_b },
            { key: "C", text: mcqData.option_c },
            { key: "D", text: mcqData.option_d },
          ].map((option) => (
            <HStack
              key={option.key}
              p={3}
              bg={
                showCorrectAnswer && option.key === mcqData.correct_answer
                  ? "green.50"
                  : "gray.50"
              }
              borderRadius="md"
              border={
                showCorrectAnswer && option.key === mcqData.correct_answer
                  ? "2px solid"
                  : "1px solid"
              }
              borderColor={
                showCorrectAnswer && option.key === mcqData.correct_answer
                  ? "green.200"
                  : "gray.200"
              }
            >
              <Badge
                colorScheme={
                  showCorrectAnswer && option.key === mcqData.correct_answer
                    ? "green"
                    : "gray"
                }
                variant="solid"
                size="sm"
              >
                {option.key}
              </Badge>
              <Text flex={1}>{option.text}</Text>
              {showCorrectAnswer && option.key === mcqData.correct_answer && (
                <Badge colorScheme="green" variant="subtle" size="sm">
                  Correct
                </Badge>
              )}
            </HStack>
          ))}
        </VStack>

        {mcqData.explanation && (
          <ExplanationBox explanation={mcqData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading MCQ question data" />
  }
})
