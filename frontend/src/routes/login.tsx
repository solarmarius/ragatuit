import {
  Container,
  Text,
  VStack,
  Alert,
  Image,
  Box,
  AspectRatio,
} from "@chakra-ui/react";
import { createFileRoute, redirect } from "@tanstack/react-router";

import Illustration from "/assets/images/test-illustration.svg";
import CanvasLoginButton from "@/components/ui/canvas-button";
import { isLoggedIn } from "@/hooks/useCanvasAuth";

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      });
    }
  },
  validateSearch: (search: Record<string, unknown>) => {
    return {
      error: search.error as string | undefined,
    };
  },
});

function Login() {
  const { error } = Route.useSearch();

  return (
    <Container
      h="100vh"
      maxW="md"
      alignItems="stretch"
      justifyContent="center"
      gap={4}
      centerContent
    >
      <VStack width="100%">
        <Image src={Illustration} p={2} />

        {/* App Title/Logo */}
        <VStack mb={4}>
          <Text fontSize="2xl" fontWeight="bold" textAlign="center">
            Welcome to QuizCrafter
          </Text>
          <Text fontSize="sm" color="gray.600" textAlign="center">
            Turn your Canvas course material into high-quality multiple-choice
            questions with LLMs. Build your question bank, approve with a click,
            and generate exams in minutes.
          </Text>
        </VStack>

        {/* Error Display */}
        {error && (
          <Alert.Root status="error">
            <Alert.Indicator />
            <Alert.Title>
              There was an error processing your request:{" "}
              {decodeURIComponent(error)}
            </Alert.Title>
          </Alert.Root>
        )}

        {/* Canvas Login */}
        <CanvasLoginButton />

        {/* Help Section */}
        <Box bg="gray.50" p={4} borderRadius="md" width="100%" mt={4}>
          <Text fontSize="sm" fontWeight="medium" mb={3}>
            Unsure how it works?
          </Text>
          <AspectRatio ratio={16 / 9} mb={3}>
            <iframe
              width="560"
              height="315"
              src="https://www.youtube.com/embed/1UpoZpMBM9Y?si=CLGw71b8uKHWR4sK"
              title="YouTube video player"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              referrerPolicy="strict-origin-when-cross-origin"
              allowFullScreen
              style={{
                borderRadius: "8px",
                border: "none",
              }}
            ></iframe>
          </AspectRatio>
          <Text fontSize="xs" color="gray.600">
            Watch how QuizCrafter seamlessly integrates with Canvas to analyze
            your course materials and generate high-quality multiple-choice
            questions.
          </Text>
        </Box>
      </VStack>
    </Container>
  );
}
