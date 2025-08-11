import { Box, Stack, Text } from "@chakra-ui/react";
import { Link } from "@tanstack/react-router";

export const PrivacyPolicyStep = () => {
  return (
    <Stack gap={6} align="center" py={8} minH="300px" justify="center">
      <Box textAlign="center">
        <Text fontSize="2xl" fontWeight="bold" color="ui.main" mb={4}>
          Privacy & Data Usage
        </Text>
        <Text fontSize="lg" color="gray.600" lineHeight="tall" mb={4}>
          Before getting started, please take a moment to review our privacy
          policy to understand how we handle your data and quiz information.
        </Text>
        <Link to="/privacy-policy">
          <Text
            color="teal.500"
            textDecoration="underline"
            fontSize="lg"
            _hover={{ color: "teal.600" }}
            cursor="pointer"
          >
            View Privacy Policy
          </Text>
        </Link>
        <Text mt={2} fontSize="sm" color="gray.600">
          By continuing, you confirm that you have read and agree to our Privacy
          Policy.
        </Text>
      </Box>
    </Stack>
  );
};
