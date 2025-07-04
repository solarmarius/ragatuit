import { Box, Text } from "@chakra-ui/react"

interface SampleAnswerBoxProps {
  sampleAnswer: string
}

export function SampleAnswerBox({ sampleAnswer }: SampleAnswerBoxProps) {
  return (
    <Box
      p={3}
      bg="blue.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="blue.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={1}>
        Sample Answer:
      </Text>
      <Text fontSize="sm" color="blue.600" whiteSpace="pre-wrap">
        {sampleAnswer}
      </Text>
    </Box>
  )
}
