import { Box, Text } from "@chakra-ui/react"

interface GradingRubricBoxProps {
  rubric: string
}

export function GradingRubricBox({ rubric }: GradingRubricBoxProps) {
  return (
    <Box
      p={3}
      bg="green.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="green.200"
    >
      <Text fontSize="sm" fontWeight="medium" color="green.700" mb={1}>
        Grading Rubric:
      </Text>
      <Text fontSize="sm" color="green.600" whiteSpace="pre-wrap">
        {rubric}
      </Text>
    </Box>
  )
}
