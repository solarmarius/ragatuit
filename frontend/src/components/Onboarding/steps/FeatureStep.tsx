import { Box, Stack, Text } from "@chakra-ui/react"

export const FeatureStep = () => {
  return (
    <Stack gap={6} align="center" py={8}>
      <Box textAlign="left">
        <Text
          fontSize="2xl"
          fontWeight="bold"
          color="ui.main"
          mb={4}
          textAlign="center"
        >
          Prepare your courses
        </Text>
        <Text fontSize="md" color="gray.600" maxW="400px" lineHeight="tall">
          To generate the best questions for the material, ensure that
        </Text>
        <Text fontSize="md" color="gray.600" maxW="400px" lineHeight="tall">
          - Content are using "pages" or uploaded as PDFs
        </Text>
        <Text fontSize="md" color="gray.600" maxW="400px" lineHeight="tall">
          - Describe any diagrams/images/equations in text
        </Text>
      </Box>
    </Stack>
  )
}
