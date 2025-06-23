import { Box, Text, Stack } from '@chakra-ui/react';

export const SetupStep = () => {
  return (
    <Stack gap={6} align="center" py={8}>
      <Box textAlign="center">
        <Text fontSize="2xl" fontWeight="bold" color="ui.main" mb={4}>
          You're All Set!
        </Text>
        <Text fontSize="lg" color="gray.600" maxW="400px" lineHeight="tall">
          Congratulations! You're ready to start using our platform. This is placeholder content for the final step of the onboarding process.
        </Text>
      </Box>
    </Stack>
  );
};
