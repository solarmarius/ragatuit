import {
  type QueryKey,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query"

import { useCustomToast, useErrorHandler } from "@/hooks/common"

interface UseApiMutationOptions<TData, TVariables> {
  successMessage?: string
  invalidateQueries?: QueryKey[]
  onSuccess?: (data: TData, variables: TVariables) => void
  onError?: (error: unknown) => void
}

/**
 * Enhanced useMutation hook that provides consistent success/error handling
 * with toast notifications and query invalidation. Wraps TanStack Query's
 * useMutation with standardized error handling, success messages, and
 * automatic query invalidation.
 *
 * @template TData - Type of data returned by the mutation
 * @template TVariables - Type of variables passed to the mutation
 *
 * @param mutationFn - The async function that performs the mutation
 * @param options - Configuration options for the mutation
 * @param options.successMessage - Message to display in success toast
 * @param options.invalidateQueries - Array of query keys to invalidate on success
 * @param options.onSuccess - Custom success callback function
 * @param options.onError - Custom error callback function (overrides default error handling)
 *
 * @returns TanStack Query mutation object with enhanced error handling
 *
 * @example
 * ```tsx
 * // Basic usage with success message
 * const createQuizMutation = useApiMutation(
 *   (data: CreateQuizData) => QuizzesService.createQuiz(data),
 *   {
 *     successMessage: "Quiz created successfully!",
 *     invalidateQueries: [['quizzes']],
 *   }
 * )
 *
 * // Usage with custom callbacks
 * const updateQuizMutation = useApiMutation(
 *   (data: UpdateQuizData) => QuizzesService.updateQuiz(data),
 *   {
 *     successMessage: "Quiz updated successfully!",
 *     invalidateQueries: [['quizzes'], ['quiz', data.id]],
 *     onSuccess: (data, variables) => {
 *       console.log('Quiz updated:', data)
 *       navigate(`/quiz/${data.id}`)
 *     },
 *     onError: (error) => {
 *       console.error('Update failed:', error)
 *       // Custom error handling
 *     }
 *   }
 * )
 *
 * // Trigger mutation
 * createQuizMutation.mutate(newQuizData)
 * ```
 */
export function useApiMutation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options: UseApiMutationOptions<TData, TVariables> = {},
) {
  const { showSuccessToast } = useCustomToast()
  const { handleError } = useErrorHandler()
  const queryClient = useQueryClient()

  const { successMessage, invalidateQueries = [], onSuccess, onError } = options

  return useMutation({
    mutationFn,
    onSuccess: (data, variables) => {
      // Show success toast if message provided
      if (successMessage) {
        showSuccessToast(successMessage)
      }

      // Invalidate queries if specified
      if (invalidateQueries.length > 0) {
        invalidateQueries.forEach((queryKey) => {
          queryClient.invalidateQueries({ queryKey })
        })
      }

      // Call custom onSuccess handler
      onSuccess?.(data, variables)
    },
    onError: (error) => {
      // Handle error with default error handler unless custom handler provided
      if (onError) {
        onError(error)
      } else {
        handleError(error)
      }
    },
  })
}
