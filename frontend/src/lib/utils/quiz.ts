import type { Quiz, QuestionBatch } from "@/client/types.gen"
import { QUIZ_STATUS, UI_TEXT, QUESTION_TYPE_LABELS, VALIDATION_RULES, VALIDATION_MESSAGES } from "@/lib/constants"

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
  if (!quiz.status) return UI_TEXT.STATUS.CREATED // Default to "Ready to Start"

  // Map lowercase status values to uppercase UI_TEXT keys
  const statusMapping = {
    [QUIZ_STATUS.CREATED]: UI_TEXT.STATUS.CREATED,
    [QUIZ_STATUS.EXTRACTING_CONTENT]: UI_TEXT.STATUS.EXTRACTING_CONTENT,
    [QUIZ_STATUS.GENERATING_QUESTIONS]: UI_TEXT.STATUS.GENERATING_QUESTIONS,
    [QUIZ_STATUS.READY_FOR_REVIEW]: UI_TEXT.STATUS.READY_FOR_REVIEW,
    [QUIZ_STATUS.EXPORTING_TO_CANVAS]: UI_TEXT.STATUS.EXPORTING_TO_CANVAS,
    [QUIZ_STATUS.PUBLISHED]: UI_TEXT.STATUS.PUBLISHED,
    [QUIZ_STATUS.FAILED]: UI_TEXT.STATUS.FAILED,
  }

  return (
    statusMapping[quiz.status as keyof typeof statusMapping] ||
    UI_TEXT.STATUS.CREATED
  )
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

// =============================================================================
// Question Batch Functions
// =============================================================================

/**
 * Calculate total questions from question batches across all modules
 */
export function calculateTotalQuestionsFromBatches(
  moduleQuestions: Record<string, QuestionBatch[]>
): number {
  return Object.values(moduleQuestions).reduce(
    (total, batches) => total + calculateModuleQuestions(batches),
    0
  )
}

/**
 * Calculate questions for a single module's batches
 */
export function calculateModuleQuestions(batches: QuestionBatch[]): number {
  return batches.reduce((sum, batch) => sum + batch.count, 0)
}

/**
 * Get all unique question types used in a quiz
 */
export function getQuizQuestionTypes(quiz: Quiz): string[] {
  if (!quiz.selected_modules) return []

  const types = new Set<string>()

  Object.values(quiz.selected_modules).forEach((module: any) => {
    if (module.question_batches) {
      module.question_batches.forEach((batch: QuestionBatch) => {
        types.add(batch.question_type)
      })
    }
  })

  return Array.from(types)
}

/**
 * Get detailed question type breakdown per module
 * Returns: { moduleId: { questionType: count } }
 */
export function getModuleQuestionTypeBreakdown(
  quiz: Quiz
): Record<string, Record<string, number>> {
  if (!quiz.selected_modules) return {}

  const breakdown: Record<string, Record<string, number>> = {}

  Object.entries(quiz.selected_modules).forEach(([moduleId, module]: [string, any]) => {
    breakdown[moduleId] = {}

    if (module.question_batches) {
      module.question_batches.forEach((batch: QuestionBatch) => {
        breakdown[moduleId][batch.question_type] =
          (breakdown[moduleId][batch.question_type] || 0) + batch.count
      })
    }
  })

  return breakdown
}

/**
 * Validate question batches for a module
 * Returns array of error messages (empty if valid)
 */
export function validateModuleBatches(batches: QuestionBatch[]): string[] {
  const errors: string[] = []

  // Check batch count limit
  if (batches.length > VALIDATION_RULES.MAX_BATCHES_PER_MODULE) {
    errors.push(VALIDATION_MESSAGES.MAX_BATCHES)
  }

  // Check for duplicate question types
  const types = batches.map(batch => batch.question_type)
  const uniqueTypes = new Set(types)
  if (types.length !== uniqueTypes.size) {
    errors.push(VALIDATION_MESSAGES.DUPLICATE_TYPES)
  }

  // Check individual batch counts
  batches.forEach((batch, index) => {
    if (batch.count < VALIDATION_RULES.MIN_QUESTIONS_PER_BATCH ||
        batch.count > VALIDATION_RULES.MAX_QUESTIONS_PER_BATCH) {
      errors.push(`Batch ${index + 1}: ${VALIDATION_MESSAGES.INVALID_COUNT}`)
    }
  })

  return errors
}

/**
 * Format question type for display
 */
export function formatQuestionTypeDisplay(questionType: string): string {
  return QUESTION_TYPE_LABELS[questionType as keyof typeof QUESTION_TYPE_LABELS] || questionType
}

/**
 * Format multiple question types for compact display
 */
export function formatQuestionTypesDisplay(types: string[]): string {
  if (types.length === 0) return "No questions"
  if (types.length === 1) return formatQuestionTypeDisplay(types[0])

  const formatted = types.map(formatQuestionTypeDisplay)
  if (formatted.length <= 2) {
    return formatted.join(" & ")
  }

  return `${formatted.slice(0, 2).join(", ")} & ${formatted.length - 2} more`
}
