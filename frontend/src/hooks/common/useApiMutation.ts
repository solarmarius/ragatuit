import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query'

import { useCustomToast, useErrorHandler } from '@/hooks/common'

interface UseApiMutationOptions<TData, TVariables> {
  successMessage?: string
  invalidateQueries?: QueryKey[]
  onSuccess?: (data: TData, variables: TVariables) => void
  onError?: (error: unknown) => void
}

/**
 * Enhanced useMutation hook that provides consistent success/error handling
 * with toast notifications and query invalidation.
 */
export function useApiMutation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options: UseApiMutationOptions<TData, TVariables> = {}
) {
  const { showSuccessToast } = useCustomToast()
  const { handleError } = useErrorHandler()
  const queryClient = useQueryClient()

  const {
    successMessage,
    invalidateQueries = [],
    onSuccess,
    onError,
  } = options

  return useMutation({
    mutationFn,
    onSuccess: (data, variables) => {
      // Show success toast if message provided
      if (successMessage) {
        showSuccessToast(successMessage)
      }

      // Invalidate queries if specified
      if (invalidateQueries.length > 0) {
        invalidateQueries.forEach(queryKey => {
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
