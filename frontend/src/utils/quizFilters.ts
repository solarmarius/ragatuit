import type { Quiz } from "@/client/types.gen"

export type QuizStatusType = "pending" | "processing" | "completed" | "failed"

/**
 * Get quizzes that need review (both extraction and generation are completed)
 */
export function getQuizzesNeedingReview(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    const extractionStatus = quiz.content_extraction_status || "pending"
    const generationStatus = quiz.llm_generation_status || "pending"

    return extractionStatus === "completed" && generationStatus === "completed"
  })
}

/**
 * Get quizzes that are currently being generated (pending or processing)
 */
export function getQuizzesBeingGenerated(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    const extractionStatus = quiz.content_extraction_status || "pending"
    const generationStatus = quiz.llm_generation_status || "pending"

    return (
      extractionStatus === "pending" ||
      extractionStatus === "processing" ||
      generationStatus === "pending" ||
      generationStatus === "processing"
    )
  })
}

/**
 * Get human-readable status text for a quiz
 */
export function getQuizStatusText(quiz: Quiz): string {
  const extractionStatus = quiz.content_extraction_status || "pending"
  const generationStatus = quiz.llm_generation_status || "pending"

  if (extractionStatus === "failed" || generationStatus === "failed") {
    return "Failed"
  }

  if (extractionStatus === "completed" && generationStatus === "completed") {
    return "Ready for Review"
  }

  if (extractionStatus === "processing" || generationStatus === "processing") {
    return "Processing"
  }

  return "Pending"
}

/**
 * Get the current processing phase for a quiz being generated
 */
export function getQuizProcessingPhase(quiz: Quiz): string {
  const extractionStatus = quiz.content_extraction_status || "pending"
  const generationStatus = quiz.llm_generation_status || "pending"

  if (extractionStatus === "pending") {
    return "Waiting to extract content"
  }

  if (extractionStatus === "processing") {
    return "Extracting content from modules"
  }

  if (extractionStatus === "completed" && generationStatus === "pending") {
    return "Waiting to generate questions"
  }

  if (extractionStatus === "completed" && generationStatus === "processing") {
    return "Generating questions with AI"
  }

  return "Processing"
}

/**
 * Get color scheme for quiz status
 */
export function getQuizStatusColor(quiz: Quiz): string {
  const extractionStatus = quiz.content_extraction_status || "pending"
  const generationStatus = quiz.llm_generation_status || "pending"

  if (extractionStatus === "failed" || generationStatus === "failed") {
    return "red"
  }

  if (extractionStatus === "completed" && generationStatus === "completed") {
    return "green"
  }

  return "orange"
}

/**
 * Check if a quiz has any failed status
 */
export function hasQuizFailed(quiz: Quiz): boolean {
  const extractionStatus = quiz.content_extraction_status || "pending"
  const generationStatus = quiz.llm_generation_status || "pending"

  return extractionStatus === "failed" || generationStatus === "failed"
}

/**
 * Check if a quiz is completely done (both extraction and generation completed)
 */
export function isQuizComplete(quiz: Quiz): boolean {
  const extractionStatus = quiz.content_extraction_status || "pending"
  const generationStatus = quiz.llm_generation_status || "pending"

  return extractionStatus === "completed" && generationStatus === "completed"
}

/**
 * Check if a quiz is currently being processed
 */
export function isQuizProcessing(quiz: Quiz): boolean {
  const extractionStatus = quiz.content_extraction_status || "pending"
  const generationStatus = quiz.llm_generation_status || "pending"

  return extractionStatus === "processing" || generationStatus === "processing"
}
