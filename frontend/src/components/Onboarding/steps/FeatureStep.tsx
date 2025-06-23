import { Box, Text, Stack } from '@chakra-ui/react';

export const FeatureStep = () => {
  return (
    <Stack gap={6} align="center" py={8}>
      <Box textAlign="center">
        <Text fontSize="2xl" fontWeight="bold" color="ui.main" mb={4}>
          Discover Our Features
        </Text>
        <Text fontSize="lg" color="gray.600" maxW="400px" lineHeight="tall">
          Explore the powerful tools and features that will help you accomplish your goals. This is placeholder content for step 2 of the onboarding process.
        </Text>
      </Box>
    </Stack>
  );
};
