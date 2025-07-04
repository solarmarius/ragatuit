import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Box, Text, VStack } from "@chakra-ui/react"
import { ErrorDisplay } from "./ErrorDisplay"
import { ExplanationBox } from "../shared/ExplanationBox"
import { FillInBlankAnswersBox } from "../shared/FillInBlankAnswersBox"

interface FillInBlankDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

export function FillInBlankDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: FillInBlankDisplayProps) {
  try {
    const fibData = extractQuestionData(question, "fill_in_blank")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {fibData.question_text}
          </Text>
        </Box>

        {showCorrectAnswer && (
          <FillInBlankAnswersBox blanks={fibData.blanks} />
        )}

        {showExplanation && fibData.explanation && (
          <ExplanationBox explanation={fibData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorDisplay error="Error loading Fill in Blank question data" />
  }
}
