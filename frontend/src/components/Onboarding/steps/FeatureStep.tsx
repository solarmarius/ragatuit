import { Box, Stack, Text } from "@chakra-ui/react";

export const FeatureStep = () => {
  return (
    <Stack align="center" minH="300px" justify="center">
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
        <Text fontSize="lg" color="gray.600" lineHeight="tall">
          To generate the best questions for the material, ensure that
        </Text>
        <Text fontSize="lg" color="gray.600" lineHeight="tall">
          - Content are using "pages" or uploaded as PDFs
        </Text>
        <Text fontSize="lg" color="gray.600" lineHeight="tall">
          - All content is being referenced with a module
        </Text>
        <Text fontSize="lg" color="gray.600" lineHeight="tall">
          - Describe any diagrams/images/equations with plain text
        </Text>
      </Box>
    </Stack>
  );
};
