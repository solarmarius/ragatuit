import type { ApiError } from "@/client"
import { extractErrorDetails } from "@/lib/utils"
import { useCustomToast } from "./useCustomToast"

/**
 * Hook for consistent error handling across the application.
 * Provides standardized error processing and user notification through toast messages.
 * Handles API errors, generic errors, and unknown error types with appropriate fallbacks.
 *
 * @returns Object containing error handling methods
 * @returns {function} returns.handleError - Function to process and display errors
 *
 * @example
 * ```tsx
 * // Basic usage in a mutation
 * const { handleError } = useErrorHandler()
 *
 * const createQuizMutation = useMutation({
 *   mutationFn: createQuiz,
 *   onError: (error) => {
 *     handleError(error) // Displays appropriate error toast
 *   }
 * })
 *
 * // Usage in async functions
 * const { handleError } = useErrorHandler()
 *
 * const handleSubmit = async (data: FormData) => {
 *   try {
 *     await submitForm(data)
 *   } catch (error) {
 *     handleError(error) // Automatically shows error toast
 *   }
 * }
 *
 * // Usage with different error types
 * const { handleError } = useErrorHandler()
 *
 * // Handles ApiError with detailed messages
 * handleError(new ApiError('API request failed', 400))
 *
 * // Handles generic Error objects
 * handleError(new Error('Something went wrong'))
 *
 * // Handles unknown error types with fallbacks
 * handleError('String error message')
 * handleError({ message: 'Custom error object' })
 * ```
 */
export function useErrorHandler() {
  const { showErrorToast } = useCustomToast()

  const handleError = (err: ApiError | Error | unknown) => {
    const errorDetails = extractErrorDetails(err)
    showErrorToast(errorDetails.message)
  }

  return { handleError }
}
