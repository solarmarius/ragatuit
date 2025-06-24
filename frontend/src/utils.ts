import { ApiError } from "./client"
import useCustomToast from "./hooks/useCustomToast"

export const handleError = (err: ApiError) => {
  const { showErrorToast } = useCustomToast()
  const errDetail = (err.body as any)?.detail
  let errorMessage = errDetail || "Something went wrong."
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    errorMessage = errDetail[0].msg
  }
  showErrorToast(errorMessage)
}

export interface CanvasErrorInfo {
  isCanvasError: boolean
  isPermissionError: boolean
  userFriendlyMessage: string
  actionableGuidance: string
}

export function analyzeCanvasError(error: unknown): CanvasErrorInfo {
  // Default response for non-API errors
  if (!(error instanceof ApiError)) {
    return {
      isCanvasError: false,
      isPermissionError: false,
      userFriendlyMessage: "An unexpected error occurred",
      actionableGuidance:
        "Please try again or contact support if the problem persists.",
    }
  }

  const isCanvasApiCall = error.url?.includes("/canvas") || false

  // Handle 403 errors from Canvas API calls
  if (error.status === 403 && isCanvasApiCall) {
    return {
      isCanvasError: true,
      isPermissionError: true,
      userFriendlyMessage:
        "You don't have permission to access this Canvas content",
      actionableGuidance:
        "This course may be restricted or you may need additional permissions. Contact your Canvas administrator or course instructor for access.",
    }
  }

  // Handle other Canvas-related errors
  if (isCanvasApiCall) {
    if (error.status === 404) {
      return {
        isCanvasError: true,
        isPermissionError: false,
        userFriendlyMessage: "Canvas content not found",
        actionableGuidance:
          "The requested course or modules may have been removed or are no longer available.",
      }
    }

    if (error.status === 500) {
      return {
        isCanvasError: true,
        isPermissionError: false,
        userFriendlyMessage: "Canvas server error",
        actionableGuidance:
          "There's an issue with the Canvas integration. Please try again in a few minutes.",
      }
    }

    return {
      isCanvasError: true,
      isPermissionError: false,
      userFriendlyMessage: "Canvas connection issue",
      actionableGuidance: "Please check your Canvas connection and try again.",
    }
  }

  // Generic API error
  return {
    isCanvasError: false,
    isPermissionError: false,
    userFriendlyMessage: "An error occurred while loading data",
    actionableGuidance:
      "Please try again or contact support if the problem persists.",
  }
}
