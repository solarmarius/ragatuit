/**
 * Strongly typed question data structures for the polymorphic question system.
 * These types replace the generic {[key: string]: unknown} question_data
 * with proper type-safe interfaces for each question type.
 */

import type {
  QuestionDifficulty,
  QuestionResponse,
  QuestionType,
} from "@/client"

// Multiple Choice Question Data
export interface MCQData {
  [key: string]: unknown
  question_text: string
  option_a: string
  option_b: string
  option_c: string
  option_d: string
  correct_answer: "A" | "B" | "C" | "D"
  explanation?: string | null
}

// True/False Question Data
export interface TrueFalseData {
  [key: string]: unknown
  question_text: string
  correct_answer: boolean
  explanation?: string | null
}

// Short Answer Question Data
export interface ShortAnswerData {
  [key: string]: unknown
  question_text: string
  correct_answer: string
  answer_variations?: string[]
  case_sensitive?: boolean
  explanation?: string | null
}

// Essay Question Data
export interface EssayData {
  [key: string]: unknown
  question_text: string
  grading_rubric?: string | null
  max_words?: number | null
  expected_length?: "short" | "medium" | "long"
  sample_answer?: string | null
}

// Fill in the Blank Question Data
export interface FillInBlankData {
  [key: string]: unknown
  question_text: string
  blanks: Array<{
    position: number
    correct_answer: string
    answer_variations?: string[]
    case_sensitive?: boolean
  }>
  explanation?: string | null
}

// Discriminated union for all question data types
export type QuestionData =
  | ({ type: "multiple_choice" } & MCQData)
  | ({ type: "true_false" } & TrueFalseData)
  | ({ type: "short_answer" } & ShortAnswerData)
  | ({ type: "essay" } & EssayData)
  | ({ type: "fill_in_blank" } & FillInBlankData)

// Strongly typed question response
export interface TypedQuestionResponse<T extends QuestionType = QuestionType> {
  id: string
  quiz_id: string
  question_type: T
  question_data: T extends "multiple_choice"
    ? MCQData
    : T extends "true_false"
      ? TrueFalseData
      : T extends "short_answer"
        ? ShortAnswerData
        : T extends "essay"
          ? EssayData
          : T extends "fill_in_blank"
            ? FillInBlankData
            : never
  difficulty?: QuestionDifficulty | null
  tags?: string[] | null
  is_approved: boolean
  approved_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  canvas_item_id?: string | null
}

// Specific typed question response types
export type MCQQuestionResponse = TypedQuestionResponse<"multiple_choice">
export type TrueFalseQuestionResponse = TypedQuestionResponse<"true_false">
export type ShortAnswerQuestionResponse = TypedQuestionResponse<"short_answer">
export type EssayQuestionResponse = TypedQuestionResponse<"essay">
export type FillInBlankQuestionResponse = TypedQuestionResponse<"fill_in_blank">

// Type guards for question data
export function isMCQData(data: any): data is MCQData {
  return (
    typeof data === "object" &&
    data !== null &&
    typeof data.question_text === "string" &&
    typeof data.option_a === "string" &&
    typeof data.option_b === "string" &&
    typeof data.option_c === "string" &&
    typeof data.option_d === "string" &&
    typeof data.correct_answer === "string" &&
    ["A", "B", "C", "D"].includes(data.correct_answer)
  )
}

export function isTrueFalseData(data: any): data is TrueFalseData {
  return (
    typeof data === "object" &&
    data !== null &&
    typeof data.question_text === "string" &&
    typeof data.correct_answer === "boolean"
  )
}

export function isShortAnswerData(data: any): data is ShortAnswerData {
  return (
    typeof data === "object" &&
    data !== null &&
    typeof data.question_text === "string" &&
    typeof data.correct_answer === "string"
  )
}

export function isEssayData(data: any): data is EssayData {
  return (
    typeof data === "object" &&
    data !== null &&
    typeof data.question_text === "string"
  )
}

export function isFillInBlankData(data: any): data is FillInBlankData {
  return (
    typeof data === "object" &&
    data !== null &&
    typeof data.question_text === "string" &&
    Array.isArray(data.blanks) &&
    data.blanks.every(
      (blank: any) =>
        typeof blank === "object" &&
        typeof blank.position === "number" &&
        typeof blank.correct_answer === "string",
    )
  )
}

// Type guard for question responses
export function isQuestionType<T extends QuestionType>(
  question: QuestionResponse,
  type: T,
): boolean {
  return question.question_type === type
}

// Helper function to extract typed question data
export function extractQuestionData<T extends QuestionType>(
  question: QuestionResponse,
  type: T,
): TypedQuestionResponse<T>["question_data"] {
  if (question.question_type !== type) {
    throw new Error(`Expected ${type} question, got ${question.question_type}`)
  }

  const data = question.question_data as any

  switch (type) {
    case "multiple_choice":
      if (!isMCQData(data)) {
        throw new Error("Invalid MCQ question data structure")
      }
      return data as any
    case "true_false":
      if (!isTrueFalseData(data)) {
        throw new Error("Invalid True/False question data structure")
      }
      return data as any
    case "short_answer":
      if (!isShortAnswerData(data)) {
        throw new Error("Invalid Short Answer question data structure")
      }
      return data as any
    case "essay":
      if (!isEssayData(data)) {
        throw new Error("Invalid Essay question data structure")
      }
      return data as any
    case "fill_in_blank":
      if (!isFillInBlankData(data)) {
        throw new Error("Invalid Fill in Blank question data structure")
      }
      return data as any
    default:
      throw new Error(`Unsupported question type: ${type}`)
  }
}
