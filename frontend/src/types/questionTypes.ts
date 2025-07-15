/**
 * Strongly typed question data structures for the polymorphic question system.
 * These types replace the generic {[key: string]: unknown} question_data
 * with proper type-safe interfaces for each question type.
 */

import type {
  QuestionDifficulty,
  QuestionResponse,
  QuestionType,
} from "@/client";

// Multiple Choice Question Data
export interface MCQData {
  question_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_answer: "A" | "B" | "C" | "D";
  explanation?: string | null;
}

// Fill in the Blank Question Data
export interface FillInBlankData {
  question_text: string;
  blanks: Array<{
    position: number;
    correct_answer: string;
    answer_variations?: string[];
    case_sensitive?: boolean;
  }>;
  explanation?: string | null;
}

// Discriminated union for all question data types
export type QuestionData =
  | ({ type: "multiple_choice" } & MCQData)
  | ({ type: "fill_in_blank" } & FillInBlankData);

// Strongly typed question response
export interface TypedQuestionResponse<T extends QuestionType = QuestionType> {
  id: string;
  quiz_id: string;
  question_type: T;
  question_data: T extends "multiple_choice"
    ? MCQData
    : T extends "fill_in_blank"
      ? FillInBlankData
      : never;
  difficulty?: QuestionDifficulty | null;
  tags?: string[] | null;
  is_approved: boolean;
  approved_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  canvas_item_id?: string | null;
}

// Specific typed question response types
export type MCQQuestionResponse = TypedQuestionResponse<"multiple_choice">;
export type FillInBlankQuestionResponse =
  TypedQuestionResponse<"fill_in_blank">;

// Type guards for question data
export function isMCQData(data: unknown): data is MCQData {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const obj = data as Record<string, unknown>;
  return (
    typeof obj.question_text === "string" &&
    typeof obj.option_a === "string" &&
    typeof obj.option_b === "string" &&
    typeof obj.option_c === "string" &&
    typeof obj.option_d === "string" &&
    typeof obj.correct_answer === "string" &&
    ["A", "B", "C", "D"].includes(obj.correct_answer)
  );
}

export function isFillInBlankData(data: unknown): data is FillInBlankData {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const obj = data as Record<string, unknown>;
  return (
    typeof obj.question_text === "string" &&
    Array.isArray(obj.blanks) &&
    obj.blanks.every((blank: unknown) => {
      if (typeof blank !== "object" || blank === null) {
        return false;
      }
      const blankObj = blank as Record<string, unknown>;
      return (
        typeof blankObj.position === "number" &&
        typeof blankObj.correct_answer === "string"
      );
    })
  );
}

// Type guard for question responses
export function isQuestionType<T extends QuestionType>(
  question: QuestionResponse,
  type: T
): boolean {
  return question.question_type === type;
}

// Helper function to extract typed question data
export function extractQuestionData<T extends QuestionType>(
  question: QuestionResponse,
  type: T
): TypedQuestionResponse<T>["question_data"] {
  if (question.question_type !== type) {
    throw new Error(`Expected ${type} question, got ${question.question_type}`);
  }

  const data = question.question_data;

  switch (type) {
    case "multiple_choice":
      if (!isMCQData(data)) {
        throw new Error("Invalid MCQ question data structure");
      }
      return data as unknown as TypedQuestionResponse<T>["question_data"];
    case "fill_in_blank":
      if (!isFillInBlankData(data)) {
        throw new Error("Invalid Fill in Blank question data structure");
      }
      return data as unknown as TypedQuestionResponse<T>["question_data"];
    default: {
      // TypeScript exhaustiveness check - this should never happen
      const _exhaustiveCheck: never = type;
      throw new Error(`Unsupported question type: ${String(_exhaustiveCheck)}`);
    }
  }
}
