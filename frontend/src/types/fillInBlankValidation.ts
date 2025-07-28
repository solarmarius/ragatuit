/**
 * Types and interfaces for Fill-in-the-Blank question validation
 */

/**
 * Specific error codes for different validation failures
 */
export enum BlankValidationErrorCode {
  // Format errors
  INVALID_TAG_FORMAT = "INVALID_TAG_FORMAT",
  CASE_SENSITIVITY_ERROR = "CASE_SENSITIVITY_ERROR",

  // Position errors
  DUPLICATE_POSITIONS = "DUPLICATE_POSITIONS",
  NON_SEQUENTIAL_POSITIONS = "NON_SEQUENTIAL_POSITIONS",
  POSITION_GAP = "POSITION_GAP",

  // Synchronization errors
  MISSING_BLANK_CONFIG = "MISSING_BLANK_CONFIG",
  EXTRA_BLANK_CONFIG = "EXTRA_BLANK_CONFIG",
  UNSYNCHRONIZED_BLANKS = "UNSYNCHRONIZED_BLANKS",

  // Content errors
  NO_BLANKS_IN_TEXT = "NO_BLANKS_IN_TEXT",
  NO_BLANK_CONFIGURATIONS = "NO_BLANK_CONFIGURATIONS",
}

/**
 * Individual validation error with details
 */
export interface BlankValidationError {
  code: BlankValidationErrorCode
  message: string
  details?: {
    positions?: number[]
    tags?: string[]
    missingPositions?: number[]
    extraPositions?: number[]
    invalidTags?: string[]
  }
}

/**
 * Result of validation check
 */
export interface ValidationResult {
  isValid: boolean
  errors: BlankValidationError[]
}

/**
 * Configuration for a single blank
 */
export interface BlankConfiguration {
  position: number
  correctAnswer: string
  answerVariations?: string
  caseSensitive?: boolean
}

/**
 * Input data for validation
 */
export interface FillInBlankValidationInput {
  questionText: string
  blanks: BlankConfiguration[]
}

/**
 * Detailed validation context for comprehensive checking
 */
export interface ValidationContext {
  questionText: string
  textPositions: number[]
  configuredPositions: number[]
  duplicatePositions: number[]
  invalidTags: string[]
  missingConfigurations: number[]
  extraConfigurations: number[]
  isSequential: boolean
  isSynchronized: boolean
}

/**
 * Error message functions for consistent messaging
 */
export const ERROR_MESSAGE_FUNCTIONS = {
  [BlankValidationErrorCode.INVALID_TAG_FORMAT]: (invalidTags: string[]) =>
    `Invalid blank format found: ${invalidTags.join(
      ", ",
    )}. Use lowercase format: [blank_N]`,

  [BlankValidationErrorCode.CASE_SENSITIVITY_ERROR]: (tags: string[]) =>
    `Blank tags must be lowercase: ${tags.join(", ")}. Use [blank_N] format`,

  [BlankValidationErrorCode.DUPLICATE_POSITIONS]: (positions: number[]) =>
    `Duplicate blank positions found in question text: ${positions
      .map((p) => `[blank_${p}]`)
      .join(", ")}`,

  [BlankValidationErrorCode.NON_SEQUENTIAL_POSITIONS]: (positions: number[]) =>
    `Blank positions must be sequential starting from 1. Found: ${positions
      .map((p) => `[blank_${p}]`)
      .join(", ")}`,

  [BlankValidationErrorCode.POSITION_GAP]: (missing: number[]) =>
    `Missing blank positions: ${missing
      .map((p) => `[blank_${p}]`)
      .join(", ")}. Positions must be sequential`,

  [BlankValidationErrorCode.MISSING_BLANK_CONFIG]: (positions: number[]) =>
    `Question text contains ${positions
      .map((p) => `[blank_${p}]`)
      .join(", ")}, but no corresponding blank configuration exists`,

  [BlankValidationErrorCode.EXTRA_BLANK_CONFIG]: (positions: number[]) =>
    `Blank configuration exists for position${
      positions.length > 1 ? "s" : ""
    } ${positions.join(
      ", ",
    )}, but no corresponding [blank_N] tag found in question text`,

  [BlankValidationErrorCode.UNSYNCHRONIZED_BLANKS]: () =>
    "Question text and blank configurations are not synchronized. Ensure each [blank_N] tag has a corresponding blank configuration",

  [BlankValidationErrorCode.NO_BLANKS_IN_TEXT]: () =>
    "Question text must contain at least one [blank_N] tag",

  [BlankValidationErrorCode.NO_BLANK_CONFIGURATIONS]: () =>
    "At least one blank configuration is required",
} as const

/**
 * Helper function to create validation error
 */
export function createValidationError(
  code: BlankValidationErrorCode,
  details?: BlankValidationError["details"],
): BlankValidationError {
  let message: string

  switch (code) {
    case BlankValidationErrorCode.INVALID_TAG_FORMAT:
      message = ERROR_MESSAGE_FUNCTIONS[code](
        details?.invalidTags || details?.tags || [],
      )
      break
    case BlankValidationErrorCode.CASE_SENSITIVITY_ERROR:
      message = ERROR_MESSAGE_FUNCTIONS[code](
        details?.invalidTags || details?.tags || [],
      )
      break
    case BlankValidationErrorCode.DUPLICATE_POSITIONS:
      message = ERROR_MESSAGE_FUNCTIONS[code](details?.positions || [])
      break
    case BlankValidationErrorCode.NON_SEQUENTIAL_POSITIONS:
      message = ERROR_MESSAGE_FUNCTIONS[code](details?.positions || [])
      break
    case BlankValidationErrorCode.POSITION_GAP:
      message = ERROR_MESSAGE_FUNCTIONS[code](details?.missingPositions || [])
      break
    case BlankValidationErrorCode.MISSING_BLANK_CONFIG:
      message = ERROR_MESSAGE_FUNCTIONS[code](details?.missingPositions || [])
      break
    case BlankValidationErrorCode.EXTRA_BLANK_CONFIG:
      message = ERROR_MESSAGE_FUNCTIONS[code](details?.extraPositions || [])
      break
    case BlankValidationErrorCode.UNSYNCHRONIZED_BLANKS:
      message = ERROR_MESSAGE_FUNCTIONS[code]()
      break
    case BlankValidationErrorCode.NO_BLANKS_IN_TEXT:
      message = ERROR_MESSAGE_FUNCTIONS[code]()
      break
    case BlankValidationErrorCode.NO_BLANK_CONFIGURATIONS:
      message = ERROR_MESSAGE_FUNCTIONS[code]()
      break
    default:
      message = "Unknown validation error"
      break
  }

  return {
    code,
    message,
    details,
  }
}
