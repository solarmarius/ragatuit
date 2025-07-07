import type { Quiz } from '@/client/types.gen'
import { PROCESSING_STATUSES } from '@/lib/constants'

/**
 * Quiz utility functions for status handling, filtering, and processing
 */

export type QuizStatusType = 'pending' | 'processing' | 'completed' | 'failed'

/**
 * Get quiz statuses with fallback defaults
 */
function getQuizStatuses(quiz: Quiz) {
  return {
    extraction: quiz.content_extraction_status || PROCESSING_STATUSES.PENDING,
    generation: quiz.llm_generation_status || PROCESSING_STATUSES.PENDING
  }
}

// =============================================================================
// Quiz Filtering Functions
// =============================================================================

/**
 * Get quizzes that are currently being generated (pending or processing)
 */
export function getQuizzesBeingGenerated(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    const { extraction, generation } = getQuizStatuses(quiz)

    return (
      extraction === PROCESSING_STATUSES.PROCESSING ||
      generation === PROCESSING_STATUSES.PROCESSING ||
      (extraction === PROCESSING_STATUSES.COMPLETED && generation === PROCESSING_STATUSES.PENDING)
    )
  })
}

/**
 * Get quizzes that need review (both extraction and generation are completed)
 */
export function getQuizzesNeedingReview(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    const { extraction, generation } = getQuizStatuses(quiz)
    return extraction === PROCESSING_STATUSES.COMPLETED && generation === PROCESSING_STATUSES.COMPLETED
  })
}

/**
 * Get quizzes that have failed processing
 */
export function getFailedQuizzes(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter(hasQuizFailed)
}

/**
 * Get quizzes that are pending processing
 */
export function getPendingQuizzes(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    const { extraction, generation } = getQuizStatuses(quiz)
    return extraction === PROCESSING_STATUSES.PENDING && generation === PROCESSING_STATUSES.PENDING
  })
}

// =============================================================================
// Quiz Status Functions
// =============================================================================

/**
 * Get the current processing phase for a quiz being generated
 */
export function getQuizProcessingPhase(quiz: Quiz): string {
  const { extraction, generation } = getQuizStatuses(quiz)

  if (extraction === PROCESSING_STATUSES.FAILED || generation === PROCESSING_STATUSES.FAILED) {
    return 'Failed'
  }

  if (extraction === PROCESSING_STATUSES.COMPLETED && generation === PROCESSING_STATUSES.COMPLETED) {
    return 'Complete'
  }

  if (extraction === PROCESSING_STATUSES.PROCESSING) {
    return 'Extracting content...'
  }

  if (generation === PROCESSING_STATUSES.PROCESSING) {
    return 'Generating questions...'
  }

  if (extraction === PROCESSING_STATUSES.COMPLETED && generation === PROCESSING_STATUSES.PENDING) {
    return 'Ready for generation'
  }

  return 'Pending'
}

/**
 * Get human-readable status text for a quiz
 */
export function getQuizStatusText(quiz: Quiz): string {
  const { extraction, generation } = getQuizStatuses(quiz)

  if (extraction === PROCESSING_STATUSES.FAILED || generation === PROCESSING_STATUSES.FAILED) {
    return 'Failed'
  }

  if (extraction === PROCESSING_STATUSES.COMPLETED && generation === PROCESSING_STATUSES.COMPLETED) {
    return 'Ready for Review'
  }

  if (extraction === PROCESSING_STATUSES.PROCESSING || generation === PROCESSING_STATUSES.PROCESSING) {
    return 'Processing'
  }

  return 'Pending'
}

/**
 * Get color scheme for quiz status
 */
export function getQuizStatusColor(quiz: Quiz): string {
  const { extraction, generation } = getQuizStatuses(quiz)

  if (extraction === PROCESSING_STATUSES.FAILED || generation === PROCESSING_STATUSES.FAILED) {
    return 'red'
  }

  if (extraction === PROCESSING_STATUSES.COMPLETED && generation === PROCESSING_STATUSES.COMPLETED) {
    return 'green'
  }

  return 'orange'
}

/**
 * Calculate quiz processing progress percentage
 */
export function getQuizProgressPercentage(quiz: Quiz): number {
  const { extraction, generation } = getQuizStatuses(quiz)

  if (extraction === PROCESSING_STATUSES.FAILED || generation === PROCESSING_STATUSES.FAILED) {
    return 0
  }

  if (extraction === PROCESSING_STATUSES.COMPLETED && generation === PROCESSING_STATUSES.COMPLETED) {
    return 100
  }

  if (extraction === PROCESSING_STATUSES.PROCESSING) {
    return 25
  }

  if (extraction === PROCESSING_STATUSES.COMPLETED && generation === PROCESSING_STATUSES.PENDING) {
    return 50
  }

  if (generation === PROCESSING_STATUSES.PROCESSING) {
    return 75
  }

  return 0
}

// =============================================================================
// Quiz State Checking Functions
// =============================================================================

/**
 * Check if a quiz has any failed status
 */
export function hasQuizFailed(quiz: Quiz): boolean {
  const { extraction, generation } = getQuizStatuses(quiz)
  return extraction === PROCESSING_STATUSES.FAILED || generation === PROCESSING_STATUSES.FAILED
}

/**
 * Check if a quiz is completely done (both extraction and generation completed)
 */
export function isQuizComplete(quiz: Quiz): boolean {
  const { extraction, generation } = getQuizStatuses(quiz)
  return extraction === PROCESSING_STATUSES.COMPLETED && generation === PROCESSING_STATUSES.COMPLETED
}

/**
 * Check if a quiz is currently being processed
 */
export function isQuizProcessing(quiz: Quiz): boolean {
  const { extraction, generation } = getQuizStatuses(quiz)
  return extraction === PROCESSING_STATUSES.PROCESSING || generation === PROCESSING_STATUSES.PROCESSING
}

/**
 * Check if a quiz is pending processing
 */
export function isQuizPending(quiz: Quiz): boolean {
  const { extraction, generation } = getQuizStatuses(quiz)
  return extraction === PROCESSING_STATUSES.PENDING && generation === PROCESSING_STATUSES.PENDING
}

// =============================================================================
// Quiz Data Functions
// =============================================================================

/**
 * Get selected modules count for a quiz
 */
export function getSelectedModulesCount(quiz: Quiz): number {
  const selectedModules = quiz.selected_modules || {}
  return Object.keys(selectedModules).length
}

/**
 * Format quiz title with fallback
 */
export function getQuizDisplayTitle(quiz: Quiz): string {
  return quiz.title || 'Untitled Quiz'
}

/**
 * Sort quizzes by creation date (newest first)
 */
export function sortQuizzesByDate(quizzes: Quiz[]): Quiz[] {
  return [...quizzes].sort((a, b) => {
    const dateA = a.created_at ? new Date(a.created_at).getTime() : 0
    const dateB = b.created_at ? new Date(b.created_at).getTime() : 0
    return dateB - dateA
  })
}

/**
 * Sort quizzes by status priority (failed -> processing -> pending -> complete)
 */
export function sortQuizzesByStatus(quizzes: Quiz[]): Quiz[] {
  return [...quizzes].sort((a, b) => {
    const getPriority = (quiz: Quiz) => {
      if (hasQuizFailed(quiz)) return 0
      if (isQuizProcessing(quiz)) return 1
      if (isQuizPending(quiz)) return 2
      if (isQuizComplete(quiz)) return 3
      return 4
    }

    return getPriority(a) - getPriority(b)
  })
}
