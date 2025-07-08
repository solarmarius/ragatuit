import { Box, Text } from "@chakra-ui/react"

interface UnsupportedDisplayProps {
  questionType: string
}

export function UnsupportedDisplay({ questionType }: UnsupportedDisplayProps) {
  return (
    <Box
      p={4}
      bg="orange.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="orange.200"
    >
      <Text fontSize="md" fontWeight="medium" color="orange.700" mb={1}>
        Unsupported Question Type
      </Text>
      <Text fontSize="sm" color="orange.600">
        Question type "{questionType}" is not yet supported in the display
        interface.
      </Text>
    </Box>
  )
}
