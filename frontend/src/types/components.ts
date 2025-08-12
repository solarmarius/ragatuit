import type { QuestionResponse } from "@/client"
import type { SkeletonProps } from "@chakra-ui/react"

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

export interface FillInBlankDisplayProps extends BaseQuestionDisplayProps {
  question: QuestionResponse & { question_type: "fill_in_blank" }
}

// Common component props
export interface StatusLightProps {
  extractionStatus: "pending" | "processing" | "completed" | "failed"
  generationStatus: "pending" | "processing" | "completed" | "failed"
  size?: "sm" | "md" | "lg"
}

export interface LoadingSkeletonProps extends Omit<SkeletonProps, 'height' | 'width'> {
  height?: string
  width?: string
  lines?: number
  gap?: string | number
}
