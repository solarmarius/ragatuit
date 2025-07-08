import type { ApiError } from "@/client"
import { extractErrorDetails } from "@/lib/utils"
import { useCustomToast } from "./useCustomToast"

/**
 * Hook for consistent error handling across the application
 */
export function useErrorHandler() {
  const { showErrorToast } = useCustomToast()

  const handleError = (err: ApiError | Error | unknown) => {
    const errorDetails = extractErrorDetails(err)
    showErrorToast(errorDetails.message)
  }

  return { handleError }
}
