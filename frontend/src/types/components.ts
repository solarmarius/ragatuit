import type { QuestionResponse } from "@/client"

// Base props for all question display components
export interface BaseQuestionDisplayProps {
  question: QuestionResponse
  showCorrectAnswer?: boolean
  showExplanation?: boolean
}

// Specific props for each question type
export interface MCQDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: "multiple_choice" }
}

export interface TrueFalseDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: "true_false" }
}

export interface ShortAnswerDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: "short_answer" }
}

export interface EssayDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: "essay" }
}

export interface FillInBlankDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: "fill_in_blank" }
}

// Common component props
export interface StatusLightProps {
  extractionStatus: "pending" | "processing" | "completed" | "failed"
  generationStatus: "pending" | "processing" | "completed" | "failed"
  size?: "sm" | "md" | "lg"
}

export interface LoadingSkeletonProps {
  height?: string
  width?: string
  lines?: number
}
