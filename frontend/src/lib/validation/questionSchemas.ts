/**
 * Zod validation schemas for question editor forms.
 * These schemas provide runtime validation and type safety for form data.
 */

import { z } from "zod";
import { QUESTION_TYPES } from "@/lib/constants";

// Define a stable local type for QuestionType to avoid dependency on auto-generated code
export type QuestionType = typeof QUESTION_TYPES[keyof typeof QUESTION_TYPES];

// Base validation helpers
const nonEmptyString = z.string().min(1, "This field is required");
const optionalString = z.string().optional();

// Multiple Choice Question Schema
export const mcqSchema = z.object({
  questionText: nonEmptyString,
  optionA: nonEmptyString,
  optionB: nonEmptyString,
  optionC: nonEmptyString,
  optionD: nonEmptyString,
  correctAnswer: z.enum(["A", "B", "C", "D"], {
    required_error: "Please select the correct answer",
  }),
  explanation: optionalString,
});

export type MCQFormData = z.infer<typeof mcqSchema>;

// Fill in the Blank Question Schema
export const fillInBlankSchema = z.object({
  questionText: nonEmptyString,
  blanks: z
    .array(
      z.object({
        position: z.number().min(1, "Position must be at least 1"),
        correctAnswer: nonEmptyString,
        answerVariations: optionalString,
        caseSensitive: z.boolean().default(false),
      })
    )
    .min(1, "At least one blank is required")
    .max(10, "Maximum 10 blanks allowed")
    .refine(
      (blanks) => {
        const positions = blanks.map((blank) => blank.position);
        return new Set(positions).size === positions.length;
      },
      {
        message: "Each blank must have a unique position",
      }
    ),
  explanation: optionalString,
});

export type FillInBlankFormData = z.infer<typeof fillInBlankSchema>;

// Matching Question Schema
export const matchingSchema = z
  .object({
    questionText: nonEmptyString,
    pairs: z
      .array(
        z.object({
          question: nonEmptyString.min(1, "Question text is required"),
          answer: nonEmptyString.min(1, "Answer text is required"),
        })
      )
      .min(3, "At least 3 matching pairs are required")
      .max(10, "Maximum 10 matching pairs allowed")
      .refine(
        (pairs) => {
          // Check for duplicate questions
          const questions = pairs.map((p) => p.question.toLowerCase().trim());
          return new Set(questions).size === questions.length;
        },
        { message: "Duplicate questions are not allowed" }
      )
      .refine(
        (pairs) => {
          // Check for duplicate answers
          const answers = pairs.map((p) => p.answer.toLowerCase().trim());
          return new Set(answers).size === answers.length;
        },
        { message: "Duplicate answers are not allowed" }
      ),
    distractors: z
      .array(z.string().min(1, "Distractor cannot be empty"))
      .max(5, "Maximum 5 distractors allowed")
      .optional()
      .refine(
        (distractors) => {
          if (!distractors) return true;
          // Check for duplicate distractors
          const unique = new Set(
            distractors.map((d) => d.toLowerCase().trim())
          );
          return unique.size === distractors.length;
        },
        { message: "Duplicate distractors are not allowed" }
      ),
    explanation: optionalString,
  })
  .refine(
    (data) => {
      // Ensure distractors don't match correct answers
      if (!data.distractors) return true;

      const correctAnswers = new Set(
        data.pairs.map((p) => p.answer.toLowerCase().trim())
      );

      for (const distractor of data.distractors) {
        if (correctAnswers.has(distractor.toLowerCase().trim())) {
          return false;
        }
      }

      return true;
    },
    {
      message: "Distractors cannot match any correct answers",
      path: ["distractors"],
    }
  );

export type MatchingFormData = z.infer<typeof matchingSchema>;

// Helper function to get schema by question type
export function getSchemaByType(questionType: QuestionType): z.ZodSchema<any> {
  switch (questionType) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return mcqSchema;
    case QUESTION_TYPES.FILL_IN_BLANK:
      return fillInBlankSchema;
    case QUESTION_TYPES.MATCHING:
      return matchingSchema;
    default:
      throw new Error(`No schema defined for question type: ${questionType}`);
  }
}

// Helper function to get form data type by question type
export type FormDataByType<T extends QuestionType> = T extends typeof QUESTION_TYPES.MULTIPLE_CHOICE
  ? MCQFormData
  : T extends typeof QUESTION_TYPES.FILL_IN_BLANK
    ? FillInBlankFormData
    : T extends typeof QUESTION_TYPES.MATCHING
      ? MatchingFormData
      : never;

// Common validation messages
export const validationMessages = {
  required: "This field is required",
  minLength: (min: number) => `Must be at least ${min} characters`,
  maxLength: (max: number) => `Must be less than ${max} characters`,
  invalidEmail: "Please enter a valid email address",
  invalidUrl: "Please enter a valid URL",
  positiveNumber: "Must be a positive number",
  uniquePositions: "Each blank must have a unique position",
  duplicateQuestions: "Duplicate questions are not allowed",
  duplicateAnswers: "Duplicate answers are not allowed",
  duplicateDistractors: "Duplicate distractors are not allowed",
  distractorMatchesAnswer: "Distractors cannot match any correct answers",
  minMatchingPairs: "At least 3 matching pairs are required",
  maxMatchingPairs: "Maximum 10 matching pairs allowed",
  maxDistractors: "Maximum 5 distractors allowed",
};
