import type { QuestionResponse } from "@/client"
import { ErrorState } from "@/components/Common"
import { extractQuestionData } from "@/types/questionTypes"
import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"
import { ExplanationBox } from "../shared/ExplanationBox"

interface MatchingDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
}

export const MatchingDisplay = memo(function MatchingDisplay({
  question,
  showCorrectAnswer,
}: MatchingDisplayProps) {
  try {
    const matchingData = extractQuestionData(question, "matching")

    return (
      <VStack gap={4} align="stretch">
        {/* Question Text */}
        <Box>
          <Text fontSize="md" fontWeight="medium">
            {matchingData.question_text}
          </Text>
        </Box>
        <Box>
          <VStack gap={3} align="stretch">
            {matchingData.pairs.map((pair, index) => (
              <HStack key={index} gap={3}>
                <Box
                  flex={1}
                  p={3}
                  borderWidth={1}
                  borderColor="gray.200"
                  borderRadius="md"
                  bg="gray.50"
                >
                  <Text fontSize="sm">{pair.question}</Text>
                </Box>
                <Text fontSize="sm" color="gray.600" fontWeight="medium">
                  →
                </Text>
                <Box
                  flex={1}
                  p={3}
                  borderWidth={1}
                  borderColor="green.300"
                  bg="green.50"
                  borderRadius="md"
                >
                  <Text fontSize="sm">{pair.answer}</Text>
                </Box>
              </HStack>
            ))}
          </VStack>
        </Box>

        {/* Distractors */}
        {matchingData.distractors && matchingData.distractors.length > 0 && (
          <Box>
            <VStack gap={2} align="stretch">
              {matchingData.distractors.map((distractor, index) => (
                <Box
                  key={index}
                  p={3}
                  borderWidth={1}
                  borderColor={showCorrectAnswer ? "red.200" : "gray.200"}
                  borderRadius="md"
                  bg={showCorrectAnswer ? "red.50" : "white"}
                  position="relative"
                >
                  <Text fontSize="sm">{distractor}</Text>
                  {showCorrectAnswer && (
                    <Badge
                      position="absolute"
                      top={1}
                      right={1}
                      size="sm"
                      colorScheme="red"
                    >
                      Distractor
                    </Badge>
                  )}
                </Box>
              ))}
            </VStack>
          </Box>
        )}

        {/* Explanation */}
        {matchingData.explanation && (
          <ExplanationBox explanation={matchingData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    return (
      <ErrorState
        title="Display Error"
        message="Error loading matching question data"
        variant="inline"
        showRetry={false}
      />
    )
  }
})
