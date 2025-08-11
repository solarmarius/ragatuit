import {
  Box,
  Container,
  HStack,
  SimpleGrid,
  Text,
  VStack,
} from "@chakra-ui/react";
import { Link as RouterLink, createFileRoute } from "@tanstack/react-router";

import { ErrorState } from "@/components/Common";
import { OnboardingModal } from "@/components/Onboarding/OnboardingModal";
import {
  HelpPanel,
  QuizGenerationPanel,
  QuizReviewPanel,
} from "@/components/dashboard";
import { Button } from "@/components/ui/button";
import { useUserQuizzes } from "@/hooks/api";
import { useAuth } from "@/hooks/auth";
import { useCustomToast, useOnboarding } from "@/hooks/common";

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
});

function Dashboard() {
  const { user: currentUser } = useAuth();
  const { showErrorToast } = useCustomToast();
  const {
    currentStep,
    isOpen,
    nextStep,
    previousStep,
    markOnboardingCompleted,
  } = useOnboarding();

  const { data: quizzes, isLoading, error } = useUserQuizzes();

  if (error) {
    showErrorToast("Failed to load quizzes");
    return (
      <Container maxW="6xl" py={8}>
        <ErrorState
          title="Error Loading Dashboard"
          message="There was an error loading your dashboard. Please try refreshing the page."
          showRetry={false}
        />
      </Container>
    );
  }

  return (
    <>
      <Container maxW="6xl" py={8} data-testid="dashboard-container">
        <VStack gap={6} align="stretch">
          {/* Header */}
          <HStack justify="space-between" align="center">
            <Box>
              <Text fontSize="3xl" fontWeight="bold">
                Hi, {currentUser?.name} 👋🏼
              </Text>
              <Text color="gray.600">
                Welcome back! Here's an overview of your quizzes and helpful
                resources.
              </Text>
            </Box>
            <Button asChild>
              <RouterLink to="/create-quiz">Create New Quiz</RouterLink>
            </Button>
          </HStack>
          {/* Warning Box */}
          <Box
            bg="orange.50"
            border="1px"
            borderColor="orange.200"
            borderRadius="md"
            px={4}
            py={3}
          >
            <Text color="orange.700" fontWeight="medium">
              ⚠️ This application is not yet officially released. Quiz data may
              be deleted without notice.
            </Text>
          </Box>

          {/* Dashboard Panels */}
          <SimpleGrid
            columns={{ base: 1, md: 2, lg: 3 }}
            gap={6}
            data-testid="dashboard-grid"
          >
            <QuizReviewPanel quizzes={quizzes || []} isLoading={isLoading} />
            <QuizGenerationPanel
              quizzes={quizzes || []}
              isLoading={isLoading}
            />
            <HelpPanel />
          </SimpleGrid>
        </VStack>
      </Container>

      <OnboardingModal
        isOpen={isOpen}
        currentStep={currentStep}
        onNext={nextStep}
        onPrevious={previousStep}
        onComplete={markOnboardingCompleted}
      />
    </>
  );
}
