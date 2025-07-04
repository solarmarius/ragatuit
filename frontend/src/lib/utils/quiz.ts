import type { Quiz } from '@/client/types.gen'
import { PROCESSING_STATUSES } from '@/lib/constants'

export type QuizStatusType = 'pending' | 'processing' | 'completed' | 'failed'

/**
 * Get quizzes that are currently being generated (pending or processing)
 */
export function getQuizzesBeingGenerated(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
    const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

    return (
      extractionStatus === PROCESSING_STATUSES.PROCESSING ||
      generationStatus === PROCESSING_STATUSES.PROCESSING ||
      (extractionStatus === PROCESSING_STATUSES.COMPLETED &&
       generationStatus === PROCESSING_STATUSES.PENDING)
    )
  })
}

/**
 * Get quizzes that need review (both extraction and generation are completed)
 */
export function getQuizzesNeedingReview(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
    const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

    return (
      extractionStatus === PROCESSING_STATUSES.COMPLETED &&
      generationStatus === PROCESSING_STATUSES.COMPLETED
    )
  })
}

/**
 * Get the current processing phase for a quiz being generated
 */
export function getQuizProcessingPhase(quiz: Quiz): string {
  const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
  const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

  if (extractionStatus === PROCESSING_STATUSES.FAILED || generationStatus === PROCESSING_STATUSES.FAILED) {
    return 'Failed'
  }

  if (extractionStatus === PROCESSING_STATUSES.COMPLETED && generationStatus === PROCESSING_STATUSES.COMPLETED) {
    return 'Complete'
  }

  if (extractionStatus === PROCESSING_STATUSES.PROCESSING) {
    return 'Extracting content...'
  }

  if (generationStatus === PROCESSING_STATUSES.PROCESSING) {
    return 'Generating questions...'
  }

  if (extractionStatus === PROCESSING_STATUSES.COMPLETED && generationStatus === PROCESSING_STATUSES.PENDING) {
    return 'Ready for generation'
  }

  return 'Pending'
}

/**
 * Get human-readable status text for a quiz
 */
export function getQuizStatusText(quiz: Quiz): string {
  const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
  const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

  if (extractionStatus === PROCESSING_STATUSES.FAILED || generationStatus === PROCESSING_STATUSES.FAILED) {
    return 'Failed'
  }

  if (extractionStatus === PROCESSING_STATUSES.COMPLETED && generationStatus === PROCESSING_STATUSES.COMPLETED) {
    return 'Ready for Review'
  }

  if (extractionStatus === PROCESSING_STATUSES.PROCESSING || generationStatus === PROCESSING_STATUSES.PROCESSING) {
    return 'Processing'
  }

  return 'Pending'
}

/**
 * Get color scheme for quiz status
 */
export function getQuizStatusColor(quiz: Quiz): string {
  const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
  const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

  if (extractionStatus === PROCESSING_STATUSES.FAILED || generationStatus === PROCESSING_STATUSES.FAILED) {
    return 'red'
  }

  if (extractionStatus === PROCESSING_STATUSES.COMPLETED && generationStatus === PROCESSING_STATUSES.COMPLETED) {
    return 'green'
  }

  return 'orange'
}

/**
 * Check if a quiz has any failed status
 */
export function hasQuizFailed(quiz: Quiz): boolean {
  const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
  const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

  return extractionStatus === PROCESSING_STATUSES.FAILED || generationStatus === PROCESSING_STATUSES.FAILED
}

/**
 * Check if a quiz is completely done (both extraction and generation completed)
 */
export function isQuizComplete(quiz: Quiz): boolean {
  const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
  const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

  return extractionStatus === PROCESSING_STATUSES.COMPLETED && generationStatus === PROCESSING_STATUSES.COMPLETED
}

/**
 * Check if a quiz is currently being processed
 */
export function isQuizProcessing(quiz: Quiz): boolean {
  const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
  const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

  return extractionStatus === PROCESSING_STATUSES.PROCESSING || generationStatus === PROCESSING_STATUSES.PROCESSING
}
