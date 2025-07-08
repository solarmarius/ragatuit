/**
 * Strongly typed question statistics structures.
 * These types replace the generic {[key: string]: number} stats
 * with proper type-safe interfaces for question statistics.
 */

import type { QuestionType } from "@/client"

// Question type-specific statistics
export interface QuestionTypeStats {
  total: number
  approved: number
  approval_rate: number
}

// Comprehensive question statistics
export interface QuestionStats {
  total_questions: number
  approved_questions: number
  approval_rate: number
  by_question_type: Record<QuestionType, QuestionTypeStats>
  by_difficulty?: {
    easy: QuestionTypeStats
    medium: QuestionTypeStats
    hard: QuestionTypeStats
  }
  by_tags?: Record<string, QuestionTypeStats>
  generation_stats?: {
    total_generated: number
    successful_generations: number
    failed_generations: number
    average_questions_per_generation: number
  }
}

// Lightweight stats for summary views
export interface QuestionStatsSummary {
  total_questions: number
  approved_questions: number
  approval_rate: number
  pending_questions: number
}

// Stats for individual question types
export interface MCQStats extends QuestionTypeStats {
  average_options_count: number
  most_common_correct_answer: "A" | "B" | "C" | "D"
  questions_with_explanation: number
}

export interface TrueFalseStats extends QuestionTypeStats {
  true_answers: number
  false_answers: number
  questions_with_explanation: number
}

export interface ShortAnswerStats extends QuestionTypeStats {
  average_answer_length: number
  questions_with_variations: number
  case_sensitive_questions: number
}

export interface EssayStats extends QuestionTypeStats {
  questions_with_rubric: number
  average_expected_length: "short" | "medium" | "long"
  questions_with_sample_answer: number
}

export interface FillInBlankStats extends QuestionTypeStats {
  average_blanks_per_question: number
  questions_with_variations: number
  case_sensitive_questions: number
}

// Type guard for question stats
export function isQuestionStats(data: any): data is QuestionStats {
  return (
    typeof data === "object" &&
    data !== null &&
    typeof data.total_questions === "number" &&
    typeof data.approved_questions === "number" &&
    typeof data.approval_rate === "number" &&
    typeof data.by_question_type === "object"
  )
}

// Helper function to calculate approval rate
export function calculateApprovalRate(total: number, approved: number): number {
  return total > 0 ? approved / total : 0
}

// Helper function to create empty stats
export function createEmptyStats(): QuestionStats {
  return {
    total_questions: 0,
    approved_questions: 0,
    approval_rate: 0,
    by_question_type: {
      multiple_choice: { total: 0, approved: 0, approval_rate: 0 },
      true_false: { total: 0, approved: 0, approval_rate: 0 },
      short_answer: { total: 0, approved: 0, approval_rate: 0 },
      essay: { total: 0, approved: 0, approval_rate: 0 },
      fill_in_blank: { total: 0, approved: 0, approval_rate: 0 },
    },
  }
}

// Helper function to merge stats from legacy format
export function mergeLegacyStats(
  legacyStats: Record<string, number>,
): QuestionStats {
  const total = legacyStats.total || 0
  const approved = legacyStats.approved || 0
  const approval_rate = calculateApprovalRate(total, approved)

  return {
    total_questions: total,
    approved_questions: approved,
    approval_rate,
    by_question_type: {
      multiple_choice: {
        total: legacyStats.multiple_choice_total || total,
        approved: legacyStats.multiple_choice_approved || approved,
        approval_rate: calculateApprovalRate(
          legacyStats.multiple_choice_total || total,
          legacyStats.multiple_choice_approved || approved,
        ),
      },
      true_false: { total: 0, approved: 0, approval_rate: 0 },
      short_answer: { total: 0, approved: 0, approval_rate: 0 },
      essay: { total: 0, approved: 0, approval_rate: 0 },
      fill_in_blank: { total: 0, approved: 0, approval_rate: 0 },
    },
  }
}
