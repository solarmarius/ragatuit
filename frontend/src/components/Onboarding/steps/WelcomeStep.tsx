import { Box, Stack, Text } from "@chakra-ui/react"

export const WelcomeStep = () => {
  return (
    <Stack gap={6} align="center" py={8} minH="300px" justify="center">
      <Box textAlign="center">
        <Text fontSize="2xl" fontWeight="bold" color="ui.main" mb={4}>
          Welcome to RAG@UiT
        </Text>
        <Text fontSize="lg" color="gray.600" maxW="400px" lineHeight="tall">
          Thanks for trying us out. Let us show you around and help you get
          started with everything our application has to offer.
        </Text>
      </Box>
    </Stack>
  )
}
