import { useEffect } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Container, Spinner, Text, VStack } from "@chakra-ui/react";

import useCanvasAuth from "@/hooks/useCanvasAuth";

export const Route = createFileRoute("/callback")({
  component: CanvasCallback,
});

function CanvasCallback() {
  const navigate = useNavigate();
  const { handleCanvasCallback, error } = useCanvasAuth();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    if (params.get("error")) {
      // Handle authorization denied or other OAuth errors
      const errorDescription =
        params.get("error_description") || "Canvas authorization failed";
      navigate({
        to: "/login",
        search: { error: errorDescription },
      });
      return;
    }

    if (params.get("code")) {
      handleCanvasCallback.mutate(params);
    } else {
      navigate({ to: "/login" });
    }
  }, []);

  if (error) {
    return (
      <Container centerContent h="100vh" justifyContent="center">
        <VStack spacing={4}>
          <Text color="red.500">Authentication failed</Text>
          <Text>{error}</Text>
          <Text
            as="a"
            href="/login"
            color="blue.500"
            textDecoration="underline"
          >
            Return to login
          </Text>
        </VStack>
      </Container>
    );
  }

  return (
    <Container centerContent h="100vh" justifyContent="center">
      <VStack spacing={4}>
        <Spinner size="xl" />
        <Text>Completing Canvas authentication...</Text>
      </VStack>
    </Container>
  );
}
