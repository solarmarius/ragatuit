import { Box, Text, VStack } from "@chakra-ui/react"

interface BlankData {
  position: number
  correct_answer: string
  answer_variations?: string[]
  case_sensitive?: boolean
}

interface FillInBlankAnswersBoxProps {
  blanks: BlankData[]
}

export function FillInBlankAnswersBox({ blanks }: FillInBlankAnswersBoxProps) {
  return (
    <Box
      p={3}
      bg="green.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="green.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="green.700" mb={2}>
        Correct Answers:
      </Text>
      <VStack gap={2} align="stretch">
        {blanks.map((blank, index) => (
          <Box key={index}>
            <Text fontSize="sm" color="green.600">
              <strong>Blank {blank.position}:</strong>{" "}
              <Text as="span" fontFamily="mono">
                {blank.correct_answer}
              </Text>
            </Text>
            {blank.answer_variations && blank.answer_variations.length > 0 && (
              <Text fontSize="xs" color="green.500" ml={4}>
                Variations: {blank.answer_variations.join(", ")}
              </Text>
            )}
            {blank.case_sensitive && (
              <Text fontSize="xs" color="orange.600" ml={4}>
                (Case sensitive)
              </Text>
            )}
          </Box>
        ))}
      </VStack>
    </Box>
  )
}
