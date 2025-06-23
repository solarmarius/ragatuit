import { Box, Button, Container, Text, VStack } from "@chakra-ui/react"
import { createFileRoute, useNavigate } from "@tanstack/react-router"

import { OnboardingModal } from "@/components/Onboarding/OnboardingModal"
import useAuth from "@/hooks/useCanvasAuth"
import { useOnboarding } from "@/hooks/useOnboarding"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
})

function Dashboard() {
  const navigate = useNavigate()
  const { user: currentUser } = useAuth()
  const {
    currentStep,
    isOpen,
    nextStep,
    previousStep,
    markOnboardingCompleted,
    skipOnboarding,
  } = useOnboarding()

  const handleCreateQuiz = () => {
    navigate({ to: "/create-quiz" })
  }

  return (
    <>
      <Container maxW="full">
        <VStack gap={6} align="stretch" pt={12} m={4}>
          <Box>
            <Text fontSize="2xl" truncate maxW="sm">
              Hi, {currentUser?.name} 👋🏼
            </Text>
            <Text>Welcome back, nice to see you again!</Text>
          </Box>

          <Box>
            <Button colorScheme="blue" size="lg" onClick={handleCreateQuiz}>
              Create Quiz
            </Button>
          </Box>
        </VStack>
      </Container>

      <OnboardingModal
        isOpen={isOpen}
        currentStep={currentStep}
        onNext={nextStep}
        onPrevious={previousStep}
        onComplete={markOnboardingCompleted}
        onSkip={skipOnboarding}
      />
    </>
  )
}
