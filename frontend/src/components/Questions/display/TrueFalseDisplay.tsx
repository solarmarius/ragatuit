import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"
import { ExplanationBox } from "../shared/ExplanationBox"
import { ErrorDisplay } from "./ErrorDisplay"

interface TrueFalseDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

export const TrueFalseDisplay = memo(function TrueFalseDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: TrueFalseDisplayProps) {
  try {
    const tfData = extractQuestionData(question, "true_false")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {tfData.question_text}
          </Text>
        </Box>

        <VStack gap={2} align="stretch">
          {[
            { key: "True", value: true },
            { key: "False", value: false },
          ].map((option) => (
            <HStack
              key={option.key}
              p={3}
              bg={
                showCorrectAnswer && option.value === tfData.correct_answer
                  ? "green.50"
                  : "gray.50"
              }
              borderRadius="md"
              border={
                showCorrectAnswer && option.value === tfData.correct_answer
                  ? "2px solid"
                  : "1px solid"
              }
              borderColor={
                showCorrectAnswer && option.value === tfData.correct_answer
                  ? "green.200"
                  : "gray.200"
              }
            >
              <Badge
                colorScheme={
                  showCorrectAnswer && option.value === tfData.correct_answer
                    ? "green"
                    : "gray"
                }
                variant="solid"
                size="sm"
              >
                {option.key}
              </Badge>
              <Text flex={1}>{option.key}</Text>
              {showCorrectAnswer && option.value === tfData.correct_answer && (
                <Badge colorScheme="green" variant="subtle" size="sm">
                  Correct
                </Badge>
              )}
            </HStack>
          ))}
        </VStack>

        {showExplanation && tfData.explanation && (
          <ExplanationBox explanation={tfData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading True/False question data" />
  }
})
