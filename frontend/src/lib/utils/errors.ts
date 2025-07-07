import { ApiError } from '@/client'

/**
 * Error handling utility functions
 */

export interface CanvasErrorInfo {
  isCanvasError: boolean
  isPermissionError: boolean
  userFriendlyMessage: string
  actionableGuidance: string
}

export interface ErrorDetails {
  message: string
  details?: string
  code?: string | number
  isRetryable: boolean
}

/**
 * Analyze Canvas-specific errors and provide user-friendly messaging
 */
export function analyzeCanvasError(error: unknown): CanvasErrorInfo {
  // Default response for non-API errors
  if (!(error instanceof ApiError)) {
    return {
      isCanvasError: false,
      isPermissionError: false,
      userFriendlyMessage: 'An unexpected error occurred',
      actionableGuidance: 'Please try again or contact support if the problem persists.',
    }
  }

  const isCanvasApiCall = error.url?.includes('/canvas') || false

  // Handle 403 errors from Canvas API calls
  if (error.status === 403 && isCanvasApiCall) {
    return {
      isCanvasError: true,
      isPermissionError: true,
      userFriendlyMessage: "You don't have permission to access this Canvas content",
      actionableGuidance:
        'This course may be restricted or you may need additional permissions. Contact your Canvas administrator or course instructor for access.',
    }
  }

  // Handle other Canvas-related errors
  if (isCanvasApiCall) {
    if (error.status === 404) {
      return {
        isCanvasError: true,
        isPermissionError: false,
        userFriendlyMessage: 'Canvas content not found',
        actionableGuidance:
          'The requested course or modules may have been removed or are no longer available.',
      }
    }

    if (error.status === 500) {
      return {
        isCanvasError: true,
        isPermissionError: false,
        userFriendlyMessage: 'Canvas server error',
        actionableGuidance:
          "There's an issue with the Canvas integration. Please try again in a few minutes.",
      }
    }

    return {
      isCanvasError: true,
      isPermissionError: false,
      userFriendlyMessage: 'Canvas connection issue',
      actionableGuidance: 'Please check your Canvas connection and try again.',
    }
  }

  // Generic API error
  return {
    isCanvasError: false,
    isPermissionError: false,
    userFriendlyMessage: 'An error occurred while loading data',
    actionableGuidance: 'Please try again or contact support if the problem persists.',
  }
}

/**
 * Extract error details from various error types
 */
export function extractErrorDetails(error: unknown): ErrorDetails {
  if (error instanceof ApiError) {
    const errDetail = (error.body as any)?.detail
    let message = 'An API error occurred'

    if (typeof errDetail === 'string') {
      message = errDetail
    } else if (Array.isArray(errDetail) && errDetail.length > 0) {
      message = errDetail[0].msg || errDetail[0].message || message
    }

    return {
      message,
      code: error.status,
      isRetryable: error.status >= 500 || error.status === 408 || error.status === 429,
      details: error.url ? `Request to ${error.url} failed` : undefined
    }
  }

  if (error instanceof Error) {
    return {
      message: error.message,
      isRetryable: false,
      details: error.stack
    }
  }

  if (typeof error === 'string') {
    return {
      message: error,
      isRetryable: false
    }
  }

  return {
    message: 'An unknown error occurred',
    isRetryable: false
  }
}

/**
 * Check if an error is a network/connectivity error
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.status === 0 || error.status >= 500
  }

  if (error instanceof Error) {
    const message = error.message.toLowerCase()
    return (
      message.includes('network') ||
      message.includes('fetch') ||
      message.includes('connection') ||
      message.includes('timeout')
    )
  }

  return false
}

/**
 * Check if an error indicates authentication issues
 */
export function isAuthError(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.status === 401 || error.status === 403
  }
  return false
}

/**
 * Generate a user-friendly error message based on error type
 */
export function getUserFriendlyErrorMessage(error: unknown): string {
  if (isAuthError(error)) {
    return 'You need to log in again to continue'
  }

  if (isNetworkError(error)) {
    return 'Network connection issue. Please check your internet connection and try again.'
  }

  const canvasInfo = analyzeCanvasError(error)
  if (canvasInfo.isCanvasError) {
    return canvasInfo.userFriendlyMessage
  }

  const details = extractErrorDetails(error)
  return details.message
}

/**
 * Get actionable guidance for an error
 */
export function getErrorActionableGuidance(error: unknown): string {
  if (isAuthError(error)) {
    return 'Please refresh the page and log in again.'
  }

  if (isNetworkError(error)) {
    return 'Check your internet connection and try again. If the problem persists, the service may be temporarily unavailable.'
  }

  const canvasInfo = analyzeCanvasError(error)
  if (canvasInfo.isCanvasError) {
    return canvasInfo.actionableGuidance
  }

  const details = extractErrorDetails(error)
  if (details.isRetryable) {
    return 'This appears to be a temporary issue. Please try again in a few moments.'
  }

  return 'If this problem continues, please contact support for assistance.'
}
