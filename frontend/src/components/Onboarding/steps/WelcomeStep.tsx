import { Box, Stack, Text } from "@chakra-ui/react";

export const WelcomeStep = () => {
  return (
    <Stack gap={6} align="center" py={8}>
      <Box textAlign="center">
        <Text fontSize="2xl" fontWeight="bold" color="ui.main" mb={4}>
          Welcome to Rag@UiT
        </Text>
        <Text fontSize="lg" color="gray.600" maxW="400px" lineHeight="tall">
          We're excited to have you here. Let us show you around and help you
          get started with everything our platform has to offer.
        </Text>
      </Box>
    </Stack>
  );
};
