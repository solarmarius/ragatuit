import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Box, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"
import { ErrorDisplay } from "./ErrorDisplay"
import { ExplanationBox } from "../shared/ExplanationBox"
import { CorrectAnswerBox } from "../shared/CorrectAnswerBox"

interface ShortAnswerDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

export const ShortAnswerDisplay = memo(function ShortAnswerDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: ShortAnswerDisplayProps) {
  try {
    const saData = extractQuestionData(question, "short_answer")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {saData.question_text}
          </Text>
        </Box>

        {showCorrectAnswer && (
          <CorrectAnswerBox
            correctAnswer={saData.correct_answer}
            answerVariations={saData.answer_variations}
            caseSensitive={saData.case_sensitive}
          />
        )}

        {showExplanation && saData.explanation && (
          <ExplanationBox explanation={saData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading Short Answer question data" />
  }
})
