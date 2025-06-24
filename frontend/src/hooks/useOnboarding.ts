import { UsersService } from "@/client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import useAuth from "./useCanvasAuth";

export const useOnboarding = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [isOpen, setIsOpen] = useState(false);
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const updateOnboardingMutation = useMutation({
    mutationFn: () =>
      UsersService.updateUserMe({
        requestBody: {
          name: user?.name || "",
          onboarding_completed: true,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentUser"] });
      setIsOpen(false);
    },
  });

  const isOnboardingCompleted = (): boolean => {
    return user?.onboarding_completed ?? false;
  };

  const markOnboardingCompleted = (): void => {
    updateOnboardingMutation.mutate();
  };

  const startOnboarding = (): void => {
    if (!isOnboardingCompleted()) {
      setCurrentStep(1);
      setIsOpen(true);
    }
  };

  const nextStep = (): void => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1);
    }
  };

  const previousStep = (): void => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const skipOnboarding = (): void => {
    markOnboardingCompleted();
  };

  useEffect(() => {
    if (user && !isOnboardingCompleted()) {
      const timer = setTimeout(() => {
        startOnboarding();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [user]);

  return {
    currentStep,
    isOpen,
    isOnboardingCompleted: isOnboardingCompleted(),
    startOnboarding,
    nextStep,
    previousStep,
    markOnboardingCompleted,
    skipOnboarding,
    setIsOpen,
    isLoading: updateOnboardingMutation.isPending,
  };
};
