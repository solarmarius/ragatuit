import { Box, Text } from "@chakra-ui/react"

interface ExplanationBoxProps {
  explanation: string
}

export function ExplanationBox({ explanation }: ExplanationBoxProps) {
  return (
    <Box
      p={3}
      bg="blue.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="blue.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={1}>
        Explanation:
      </Text>
      <Text fontSize="sm" color="blue.600">
        {explanation}
      </Text>
    </Box>
  )
}
