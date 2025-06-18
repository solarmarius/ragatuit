import { Container, Text, VStack, Alert } from "@chakra-ui/react";
import { createFileRoute, redirect } from "@tanstack/react-router";

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
      maxW="sm"
      alignItems="stretch"
      justifyContent="center"
      gap={4}
      centerContent
    >
      <VStack spacing={6} width="100%">
        {/* App Title/Logo */}
        <VStack spacing={2}>
          <Text fontSize="2xl" fontWeight="bold" textAlign="center">
            Welcome to RagATuit
          </Text>
          <Text fontSize="md" color="gray.600" textAlign="center">
            Sign in with your Canvas account to continue
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
      </VStack>
    </Container>
  );
}
