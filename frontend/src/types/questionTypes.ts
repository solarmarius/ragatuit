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

// Matching Question Data
export interface MatchingData {
  question_text: string;
  pairs: Array<{
    question: string; // Left column item
    answer: string;   // Right column correct match
  }>;
  distractors?: string[] | null; // Extra wrong answers (0-5)
  explanation?: string | null;   // Optional explanation
}

// Categorization Question Data
export interface CategorizationData {
  question_text: string;
  categories: Array<{
    id: string;
    name: string;
    correct_items: string[]; // IDs of items that belong to this category
  }>;
  items: Array<{
    id: string;
    text: string;
  }>;
  distractors?: Array<{
    id: string;
    text: string;
  }> | null; // Optional incorrect items that don't belong to any category
  explanation?: string | null;
}

// Discriminated union for all question data types
export type QuestionData =
  | ({ type: "multiple_choice" } & MCQData)
  | ({ type: "fill_in_blank" } & FillInBlankData)
  | ({ type: "matching" } & MatchingData)
  | ({ type: "categorization" } & CategorizationData);

// Strongly typed question response
export interface TypedQuestionResponse<T extends QuestionType = QuestionType> {
  id: string;
  quiz_id: string;
  question_type: T;
  question_data: T extends "multiple_choice"
    ? MCQData
    : T extends "fill_in_blank"
      ? FillInBlankData
      : T extends "matching"
        ? MatchingData
        : T extends "categorization"
          ? CategorizationData
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
export type MatchingQuestionResponse = TypedQuestionResponse<"matching">;
export type CategorizationQuestionResponse = TypedQuestionResponse<"categorization">;

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

export function isMatchingData(data: unknown): data is MatchingData {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const obj = data as Record<string, unknown>;

  // Validate required fields
  if (typeof obj.question_text !== "string") {
    return false;
  }

  // Validate pairs array
  if (!Array.isArray(obj.pairs) || obj.pairs.length < 3 || obj.pairs.length > 10) {
    return false;
  }

  // Validate each pair structure
  for (const pair of obj.pairs) {
    if (
      typeof pair !== "object" ||
      pair === null ||
      typeof (pair as any).question !== "string" ||
      typeof (pair as any).answer !== "string"
    ) {
      return false;
    }
  }

  // Validate optional distractors
  if (obj.distractors !== undefined && obj.distractors !== null) {
    if (!Array.isArray(obj.distractors) || obj.distractors.length > 5) {
      return false;
    }
    for (const distractor of obj.distractors) {
      if (typeof distractor !== "string") {
        return false;
      }
    }
  }

  // Validate optional explanation
  if (obj.explanation !== undefined && obj.explanation !== null) {
    if (typeof obj.explanation !== "string") {
      return false;
    }
  }

  return true;
}

export function isCategorizationData(data: unknown): data is CategorizationData {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const obj = data as Record<string, unknown>;

  // Validate required fields
  if (typeof obj.question_text !== "string") {
    return false;
  }

  // Validate categories array
  if (!Array.isArray(obj.categories) || obj.categories.length < 2 || obj.categories.length > 8) {
    return false;
  }

  // Validate each category structure
  for (const category of obj.categories) {
    if (
      typeof category !== "object" ||
      category === null ||
      typeof (category as any).id !== "string" ||
      typeof (category as any).name !== "string" ||
      !Array.isArray((category as any).correct_items)
    ) {
      return false;
    }
  }

  // Validate items array
  if (!Array.isArray(obj.items) || obj.items.length < 4 || obj.items.length > 20) {
    return false;
  }

  // Validate each item structure
  for (const item of obj.items) {
    if (
      typeof item !== "object" ||
      item === null ||
      typeof (item as any).id !== "string" ||
      typeof (item as any).text !== "string"
    ) {
      return false;
    }
  }

  // Validate optional distractors
  if (obj.distractors !== undefined && obj.distractors !== null) {
    if (!Array.isArray(obj.distractors) || obj.distractors.length > 5) {
      return false;
    }
    for (const distractor of obj.distractors) {
      if (
        typeof distractor !== "object" ||
        distractor === null ||
        typeof (distractor as any).id !== "string" ||
        typeof (distractor as any).text !== "string"
      ) {
        return false;
      }
    }
  }

  // Validate optional explanation
  if (obj.explanation !== undefined && obj.explanation !== null) {
    if (typeof obj.explanation !== "string") {
      return false;
    }
  }

  return true;
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
    case "matching":
      if (!isMatchingData(data)) {
        throw new Error("Invalid Matching question data structure");
      }
      return data as unknown as TypedQuestionResponse<T>["question_data"];
    case "categorization":
      if (!isCategorizationData(data)) {
        throw new Error("Invalid Categorization question data structure");
      }
      return data as unknown as TypedQuestionResponse<T>["question_data"];
    default: {
      // TypeScript exhaustiveness check - this should never happen
      const _exhaustiveCheck: never = type;
      throw new Error(`Unsupported question type: ${String(_exhaustiveCheck)}`);
    }
  }
}
