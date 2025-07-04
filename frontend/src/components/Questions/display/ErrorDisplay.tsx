import { Box, Text } from "@chakra-ui/react"

interface ErrorDisplayProps {
  error: string
}

export function ErrorDisplay({ error }: ErrorDisplayProps) {
  return (
    <Box
      p={4}
      bg="red.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="red.200"
    >
      <Text fontSize="md" fontWeight="medium" color="red.700" mb={1}>
        Display Error
      </Text>
      <Text fontSize="sm" color="red.600">
        {error}
      </Text>
    </Box>
  )
}
