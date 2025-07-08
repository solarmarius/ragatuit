/**
 * Zod validation schemas for question editor forms.
 * These schemas provide runtime validation and type safety for form data.
 */

import { z } from "zod"

// Base validation helpers
const nonEmptyString = z.string().min(1, "This field is required")
const optionalString = z.string().optional()

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
})

export type MCQFormData = z.infer<typeof mcqSchema>

// True/False Question Schema
export const trueFalseSchema = z.object({
  questionText: nonEmptyString,
  correctAnswer: z.boolean({
    required_error: "Please select the correct answer",
  }),
  explanation: optionalString,
})

export type TrueFalseFormData = z.infer<typeof trueFalseSchema>

// Short Answer Question Schema
export const shortAnswerSchema = z.object({
  questionText: nonEmptyString,
  correctAnswer: nonEmptyString,
  answerVariations: optionalString,
  caseSensitive: z.boolean().default(false),
  explanation: optionalString,
})

export type ShortAnswerFormData = z.infer<typeof shortAnswerSchema>

// Essay Question Schema
export const essaySchema = z.object({
  questionText: nonEmptyString,
  gradingRubric: optionalString,
  maxWords: z
    .number()
    .min(1, "Must be at least 1 word")
    .max(10000, "Must be less than 10,000 words")
    .optional()
    .nullable(),
  expectedLength: z.enum(["", "short", "medium", "long"]).default(""),
  sampleAnswer: optionalString,
})

export type EssayFormData = z.infer<typeof essaySchema>

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
      }),
    )
    .min(1, "At least one blank is required")
    .max(10, "Maximum 10 blanks allowed")
    .refine(
      (blanks) => {
        const positions = blanks.map((blank) => blank.position)
        return new Set(positions).size === positions.length
      },
      {
        message: "Each blank must have a unique position",
      },
    ),
  explanation: optionalString,
})

export type FillInBlankFormData = z.infer<typeof fillInBlankSchema>

// Helper function to get schema by question type
export function getSchemaByType(type: string) {
  switch (type) {
    case "multiple_choice":
      return mcqSchema
    case "true_false":
      return trueFalseSchema
    case "short_answer":
      return shortAnswerSchema
    case "essay":
      return essaySchema
    case "fill_in_blank":
      return fillInBlankSchema
    default:
      throw new Error(`Unsupported question type: ${type}`)
  }
}

// Helper function to get form data type by question type
export type FormDataByType<T extends string> = T extends "multiple_choice"
  ? MCQFormData
  : T extends "true_false"
    ? TrueFalseFormData
    : T extends "short_answer"
      ? ShortAnswerFormData
      : T extends "essay"
        ? EssayFormData
        : T extends "fill_in_blank"
          ? FillInBlankFormData
          : never

// Common validation messages
export const validationMessages = {
  required: "This field is required",
  minLength: (min: number) => `Must be at least ${min} characters`,
  maxLength: (max: number) => `Must be less than ${max} characters`,
  invalidEmail: "Please enter a valid email address",
  invalidUrl: "Please enter a valid URL",
  positiveNumber: "Must be a positive number",
  uniquePositions: "Each blank must have a unique position",
}
