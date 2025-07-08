"use client"

import { toaster } from "@/components/ui/toaster"

/**
 * Custom hook for displaying toast notifications with consistent styling and behavior.
 * Provides standardized success and error toast methods with predefined titles and styling.
 *
 * @returns Object containing toast methods
 * @returns {function} returns.showSuccessToast - Function to display success toast
 * @returns {function} returns.showErrorToast - Function to display error toast
 *
 * @example
 * ```tsx
 * const { showSuccessToast, showErrorToast } = useCustomToast()
 *
 * // Show success notification
 * showSuccessToast("Quiz created successfully!")
 *
 * // Show error notification
 * showErrorToast("Failed to create quiz. Please try again.")
 * ```
 */
const useCustomToast = () => {
  /**
   * Display a success toast notification with a predefined success title.
   *
   * @param description - The message to display in the toast
   *
   * @example
   * ```tsx
   * showSuccessToast("Quiz deleted successfully!")
   * ```
   */
  const showSuccessToast = (description: string) => {
    toaster.create({
      title: "Success!",
      description,
      type: "success",
    })
  }

  /**
   * Display an error toast notification with a predefined error title.
   *
   * @param description - The error message to display in the toast
   *
   * @example
   * ```tsx
   * showErrorToast("Failed to delete quiz. Please try again.")
   * ```
   */
  const showErrorToast = (description: string) => {
    toaster.create({
      title: "Something went wrong!",
      description,
      type: "error",
    })
  }

  return { showSuccessToast, showErrorToast }
}

export default useCustomToast
export { useCustomToast }
