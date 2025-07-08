import type { Quiz } from "@/client/types.gen"
import { QUIZ_STATUS, UI_TEXT } from "@/lib/constants"

/**
 * Quiz utility functions for status handling, filtering, and processing
 */

// =============================================================================
// Quiz Filtering Functions
// =============================================================================

/**
 * Get quizzes that are currently being generated (pending or processing)
 */
export function getQuizzesBeingGenerated(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    return (
      quiz.status === QUIZ_STATUS.CREATED ||
      quiz.status === QUIZ_STATUS.EXTRACTING_CONTENT ||
      quiz.status === QUIZ_STATUS.GENERATING_QUESTIONS
    )
  })
}

/**
 * Get quizzes that need review (questions generated, awaiting approval)
 */
export function getQuizzesNeedingReview(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    return quiz.status === QUIZ_STATUS.READY_FOR_REVIEW
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
    return quiz.status === QUIZ_STATUS.CREATED
  })
}

/**
 * Get quizzes that are published to Canvas
 */
export function getPublishedQuizzes(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    return quiz.status === QUIZ_STATUS.PUBLISHED
  })
}

// =============================================================================
// Quiz Status Functions
// =============================================================================

/**
 * Get human-readable status text for a quiz
 */
export function getQuizStatusText(quiz: Quiz): string {
  if (!quiz.status) return "Unknown"

  return UI_TEXT.STATUS[quiz.status as keyof typeof UI_TEXT.STATUS] || "Unknown"
}

/**
 * Get color scheme for quiz status
 */
export function getQuizStatusColor(quiz: Quiz): string {
  if (!quiz.status) return "gray"

  switch (quiz.status) {
    case QUIZ_STATUS.FAILED:
      return "red"
    case QUIZ_STATUS.READY_FOR_REVIEW:
      return "purple"
    case QUIZ_STATUS.EXPORTING_TO_CANVAS:
      return "yellow"
    case QUIZ_STATUS.PUBLISHED:
      return "green"
    default:
      return "orange"
  }
}

/**
 * Calculate quiz processing progress percentage
 */
export function getQuizProgressPercentage(quiz: Quiz): number {
  if (!quiz.status) return 0

  switch (quiz.status) {
    case QUIZ_STATUS.CREATED:
      return 0
    case QUIZ_STATUS.EXTRACTING_CONTENT:
      return 25
    case QUIZ_STATUS.GENERATING_QUESTIONS:
      return 50
    case QUIZ_STATUS.READY_FOR_REVIEW:
      return 75
    case QUIZ_STATUS.EXPORTING_TO_CANVAS:
      return 90
    case QUIZ_STATUS.PUBLISHED:
      return 100
    case QUIZ_STATUS.FAILED:
      return 0
    default:
      return 0
  }
}

// =============================================================================
// Quiz State Checking Functions
// =============================================================================

/**
 * Check if a quiz has failed
 */
export function hasQuizFailed(quiz: Quiz): boolean {
  return quiz.status === QUIZ_STATUS.FAILED
}

/**
 * Check if a quiz is completely done (published to Canvas)
 */
export function isQuizComplete(quiz: Quiz): boolean {
  return quiz.status === QUIZ_STATUS.PUBLISHED
}

/**
 * Check if a quiz is currently being processed
 */
export function isQuizProcessing(quiz: Quiz): boolean {
  return (
    quiz.status === QUIZ_STATUS.EXTRACTING_CONTENT ||
    quiz.status === QUIZ_STATUS.GENERATING_QUESTIONS ||
    quiz.status === QUIZ_STATUS.EXPORTING_TO_CANVAS
  )
}

/**
 * Check if a quiz is pending processing
 */
export function isQuizPending(quiz: Quiz): boolean {
  return quiz.status === QUIZ_STATUS.CREATED
}

/**
 * Check if a quiz is ready for review
 */
export function isQuizReadyForReview(quiz: Quiz): boolean {
  return quiz.status === QUIZ_STATUS.READY_FOR_REVIEW
}

/**
 * Check if a quiz is ready for export
 */
export function isQuizReadyForExport(quiz: Quiz): boolean {
  return quiz.status === QUIZ_STATUS.READY_FOR_REVIEW
}

/**
 * Check if a quiz can be retried
 */
export function canQuizBeRetried(quiz: Quiz): boolean {
  return quiz.status === QUIZ_STATUS.FAILED
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
  return quiz.title || "Untitled Quiz"
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
 * Sort quizzes by status priority (failed -> processing -> pending -> review -> published)
 */
export function sortQuizzesByStatus(quizzes: Quiz[]): Quiz[] {
  return [...quizzes].sort((a, b) => {
    const getPriority = (quiz: Quiz) => {
      if (!quiz.status) return 99
      switch (quiz.status) {
        case QUIZ_STATUS.FAILED:
          return 0
        case QUIZ_STATUS.EXTRACTING_CONTENT:
          return 1
        case QUIZ_STATUS.GENERATING_QUESTIONS:
          return 2
        case QUIZ_STATUS.EXPORTING_TO_CANVAS:
          return 3
        case QUIZ_STATUS.CREATED:
          return 4
        case QUIZ_STATUS.READY_FOR_REVIEW:
          return 5
        case QUIZ_STATUS.PUBLISHED:
          return 6
        default:
          return 99
      }
    }

    return getPriority(a) - getPriority(b)
  })
}
