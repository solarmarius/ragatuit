import { UsersService } from "@/client"
import { queryKeys } from "@/lib/queryConfig"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useAuth } from "../auth"

/**
 * Custom hook for managing the application onboarding workflow.
 * Handles onboarding state, navigation between steps, and completion tracking.
 * Automatically triggers onboarding for new users who haven't completed it.
 *
 * @returns Object containing onboarding state and control methods
 * @returns {number} returns.currentStep - Current step number (1-4)
 * @returns {boolean} returns.isOpen - Whether onboarding modal is open
 * @returns {boolean} returns.isOnboardingCompleted - Whether user has completed onboarding
 * @returns {function} returns.startOnboarding - Function to start the onboarding process
 * @returns {function} returns.nextStep - Function to advance to the next step
 * @returns {function} returns.previousStep - Function to go back to the previous step
 * @returns {function} returns.markOnboardingCompleted - Function to mark onboarding as completed
 * @returns {function} returns.setIsOpen - Function to manually control modal visibility
 * @returns {boolean} returns.isLoading - Whether the completion mutation is pending
 *
 * @example
 * ```tsx
 * const {
 *   currentStep,
 *   isOpen,
 *   isOnboardingCompleted,
 *   startOnboarding,
 *   nextStep,
 *   previousStep,
 *   markOnboardingCompleted,
 *   setIsOpen,
 *   isLoading
 * } = useOnboarding()
 *
 * // Start onboarding manually
 * if (!isOnboardingCompleted) {
 *   startOnboarding()
 * }
 *
 * // Navigate through steps
 * if (currentStep < 4) {
 *   nextStep()
 * }
 *
 * // Complete onboarding
 * markOnboardingCompleted()
 * ```
 */
export const useOnboarding = () => {
  const [currentStep, setCurrentStep] = useState(1)
  const [isOpen, setIsOpen] = useState(false)
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const updateOnboardingMutation = useMutation({
    mutationFn: () =>
      UsersService.updateUserMe({
        requestBody: {
          name: user?.name || "",
          onboarding_completed: true,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.user() })
      setIsOpen(false)
    },
  })

  const isOnboardingCompleted = (): boolean => {
    return user?.onboarding_completed ?? false
  }

  const markOnboardingCompleted = (): void => {
    updateOnboardingMutation.mutate()
  }

  const startOnboarding = (): void => {
    if (!isOnboardingCompleted()) {
      setCurrentStep(1)
      setIsOpen(true)
    }
  }

  const nextStep = (): void => {
    if (currentStep < 4) {
      setCurrentStep(currentStep + 1)
    }
  }

  const previousStep = (): void => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  useEffect(() => {
    if (user && !isOnboardingCompleted()) {
      const timer = setTimeout(() => {
        startOnboarding()
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [user])

  return {
    currentStep,
    isOpen,
    isOnboardingCompleted: isOnboardingCompleted(),
    startOnboarding,
    nextStep,
    previousStep,
    markOnboardingCompleted,
    setIsOpen,
    isLoading: updateOnboardingMutation.isPending,
  }
}
