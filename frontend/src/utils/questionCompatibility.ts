/**
 * Utility functions for handling the migration from old flat MCQ structure
 * to new polymorphic question system.
 */

import type { QuestionResponse, QuestionType } from "@/client"

// Legacy question structure (for backward compatibility)
export interface LegacyQuestionPublic {
  id: string
  quiz_id: string
  question_text: string
  option_a: string
  option_b: string
  option_c: string
  option_d: string
  correct_answer: string
  is_approved: boolean
  approved_at: string | null
  created_at: string | null
  updated_at: string | null
  canvas_item_id: string | null
}

// MCQ-specific data structure for new polymorphic system
export interface MCQData {
  question_text: string
  option_a: string
  option_b: string
  option_c: string
  option_d: string
  correct_answer: string
  explanation?: string | null
}

/**
 * Extract MCQ data from polymorphic question response
 */
export function extractMCQData(question: QuestionResponse): MCQData {
  if (question.question_type !== "multiple_choice") {
    throw new Error(
      `Expected multiple_choice question, got ${question.question_type}`,
    )
  }

  const data = question.question_data as any

  if (
    !data.question_text ||
    !data.option_a ||
    !data.option_b ||
    !data.option_c ||
    !data.option_d ||
    !data.correct_answer
  ) {
    throw new Error("Invalid MCQ question data structure")
  }

  return {
    question_text: data.question_text,
    option_a: data.option_a,
    option_b: data.option_b,
    option_c: data.option_c,
    option_d: data.option_d,
    correct_answer: data.correct_answer,
    explanation: data.explanation || null,
  }
}

/**
 * Convert new QuestionResponse to legacy format for backward compatibility
 */
export function convertToLegacyQuestion(
  question: QuestionResponse,
): LegacyQuestionPublic {
  const mcqData = extractMCQData(question)

  return {
    id: question.id,
    quiz_id: question.quiz_id,
    question_text: mcqData.question_text,
    option_a: mcqData.option_a,
    option_b: mcqData.option_b,
    option_c: mcqData.option_c,
    option_d: mcqData.option_d,
    correct_answer: mcqData.correct_answer,
    is_approved: question.is_approved,
    approved_at: question.approved_at ?? null,
    created_at: question.created_at ?? null,
    updated_at: question.updated_at ?? null,
    canvas_item_id: question.canvas_item_id ?? null,
  }
}

/**
 * Convert legacy question data to new polymorphic format
 */
export function convertFromLegacyQuestion(
  legacyQuestion: LegacyQuestionPublic,
): QuestionResponse {
  return {
    id: legacyQuestion.id,
    quiz_id: legacyQuestion.quiz_id,
    question_type: "multiple_choice" as QuestionType,
    question_data: {
      question_text: legacyQuestion.question_text,
      option_a: legacyQuestion.option_a,
      option_b: legacyQuestion.option_b,
      option_c: legacyQuestion.option_c,
      option_d: legacyQuestion.option_d,
      correct_answer: legacyQuestion.correct_answer,
    },
    difficulty: null,
    tags: null,
    is_approved: legacyQuestion.is_approved,
    approved_at: legacyQuestion.approved_at,
    created_at: legacyQuestion.created_at,
    updated_at: legacyQuestion.updated_at,
    canvas_item_id: legacyQuestion.canvas_item_id,
  }
}

/**
 * Create MCQ question data for new question creation
 */
export function createMCQQuestionData(
  questionText: string,
  optionA: string,
  optionB: string,
  optionC: string,
  optionD: string,
  correctAnswer: string,
  explanation?: string | null,
): { question_data: MCQData; question_type: QuestionType } {
  return {
    question_type: "multiple_choice",
    question_data: {
      question_text: questionText,
      option_a: optionA,
      option_b: optionB,
      option_c: optionC,
      option_d: optionD,
      correct_answer: correctAnswer,
      explanation,
    },
  }
}

/**
 * Validate that question data contains valid MCQ structure
 */
export function validateMCQData(questionData: any): questionData is MCQData {
  return (
    typeof questionData === "object" &&
    questionData !== null &&
    typeof questionData.question_text === "string" &&
    typeof questionData.option_a === "string" &&
    typeof questionData.option_b === "string" &&
    typeof questionData.option_c === "string" &&
    typeof questionData.option_d === "string" &&
    typeof questionData.correct_answer === "string" &&
    ["A", "B", "C", "D"].includes(questionData.correct_answer)
  )
}

/**
 * Get all options as a record for easier manipulation
 */
export function getMCQOptions(questionData: MCQData): Record<string, string> {
  return {
    A: questionData.option_a,
    B: questionData.option_b,
    C: questionData.option_c,
    D: questionData.option_d,
  }
}

/**
 * Convert legacy question stats to new format
 */
export function convertLegacyStats(legacyStats: {
  total: number
  approved: number
}) {
  return {
    total_questions: legacyStats.total,
    approved_questions: legacyStats.approved,
    approval_rate:
      legacyStats.total > 0 ? legacyStats.approved / legacyStats.total : 0,
    by_question_type: {
      multiple_choice: {
        total: legacyStats.total,
        approved: legacyStats.approved,
      },
    },
  }
}
