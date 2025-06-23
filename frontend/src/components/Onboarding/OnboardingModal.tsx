import { Button, Card, HStack, Stack, Text } from "@chakra-ui/react";
import {
  DialogRoot,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogFooter,
  DialogBackdrop,
} from "../ui/dialog";
import { WelcomeStep } from "./steps/WelcomeStep";
import { FeatureStep } from "./steps/FeatureStep";
import { SetupStep } from "./steps/SetupStep";

interface OnboardingModalProps {
  isOpen: boolean;
  currentStep: number;
  onNext: () => void;
  onPrevious: () => void;
  onComplete: () => void;
  onSkip: () => void;
}

export const OnboardingModal = ({
  isOpen,
  currentStep,
  onNext,
  onPrevious,
  onComplete,
  onSkip,
}: OnboardingModalProps) => {
  const totalSteps = 3;
  const progressValue = (currentStep / totalSteps) * 100;

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 1:
        return <WelcomeStep />;
      case 2:
        return <FeatureStep />;
      case 3:
        return <SetupStep />;
      default:
        return <WelcomeStep />;
    }
  };

  const isLastStep = currentStep === totalSteps;
  const isFirstStep = currentStep === 1;

  return (
    <DialogRoot open={isOpen} size="lg" placement="center">
      <DialogBackdrop />
      <DialogContent>
        <DialogHeader>
          <Stack gap={3}>
            <HStack justify="space-between" align="center">
              <Text fontSize="sm" color="gray.500">
                Step {currentStep} of {totalSteps}
              </Text>
              <Button variant="ghost" size="sm" onClick={onSkip}>
                Skip
              </Button>
            </HStack>
            <Stack bg="gray.100" h="2" borderRadius="full" overflow="hidden">
              <Stack
                bg="teal.500"
                h="full"
                width={`${progressValue}%`}
                borderRadius="full"
                transition="width 0.3s"
              />
            </Stack>
          </Stack>
        </DialogHeader>

        <DialogBody>
          <Card.Root
            variant="elevated"
            size="lg"
            _hover={{
              transform: "translateY(-2px)",
              shadow: "lg",
            }}
            transition="all 0.2s"
          >
            <Card.Body>{renderCurrentStep()}</Card.Body>
          </Card.Root>
        </DialogBody>

        <DialogFooter>
          <HStack justify="space-between" width="full">
            <Button
              variant="outline"
              onClick={onPrevious}
              disabled={isFirstStep}
              visibility={isFirstStep ? "hidden" : "visible"}
            >
              Previous
            </Button>

            <Button
              colorPalette="teal"
              onClick={isLastStep ? onComplete : onNext}
            >
              {isLastStep ? "Get Started" : "Next"}
            </Button>
          </HStack>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  );
};
