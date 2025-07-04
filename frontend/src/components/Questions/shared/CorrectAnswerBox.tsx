import { Box, Text } from "@chakra-ui/react"

interface CorrectAnswerBoxProps {
  correctAnswer: string
  answerVariations?: string[]
  caseSensitive?: boolean
}

export function CorrectAnswerBox({
  correctAnswer,
  answerVariations,
  caseSensitive,
}: CorrectAnswerBoxProps) {
  return (
    <Box
      p={3}
      bg="green.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="green.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="green.700" mb={1}>
        Correct Answer:
      </Text>
      <Text fontSize="sm" color="green.600" fontFamily="mono">
        {correctAnswer}
      </Text>
      {answerVariations && answerVariations.length > 0 && (
        <>
          <Text
            fontSize="sm"
            fontWeight="medium"
            color="green.700"
            mt={2}
            mb={1}
          >
            Accepted Variations:
          </Text>
          <Text fontSize="sm" color="green.600" fontFamily="mono">
            {answerVariations.join(", ")}
          </Text>
        </>
      )}
      {caseSensitive && (
        <Text fontSize="xs" color="orange.600" mt={1}>
          (Case sensitive)
        </Text>
      )}
    </Box>
  )
}
