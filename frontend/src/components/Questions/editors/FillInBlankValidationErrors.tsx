/**
 * Validation error display component for Fill-in-the-Blank questions
 * Shows specific validation errors with clear messaging and actionable guidance
 */

import {
  type BlankValidationError,
  BlankValidationErrorCode,
} from "@/types/fillInBlankValidation"
import { Box, Text, VStack } from "@chakra-ui/react"

interface FillInBlankValidationErrorsProps {
  errors: BlankValidationError[]
  className?: string
}

interface ErrorConfig {
  severity: "error" | "warning" | "info"
  colorScheme: string
  suggestions: string[]
}

/**
 * Configuration for different error types with user guidance
 */
const ERROR_CONFIGS: Record<BlankValidationErrorCode, ErrorConfig> = {
  [BlankValidationErrorCode.INVALID_TAG_FORMAT]: {
    severity: "error",
    colorScheme: "red",
    suggestions: [
      "Use lowercase format: [blank_1], [blank_2], etc.",
      "Ensure proper brackets and underscore",
      "Use only numeric positions",
    ],
  },
  [BlankValidationErrorCode.CASE_SENSITIVITY_ERROR]: {
    severity: "error",
    colorScheme: "red",
    suggestions: [
      "Change uppercase [BLANK_1] to lowercase [blank_1]",
      "Use consistent lowercase formatting throughout question",
    ],
  },
  [BlankValidationErrorCode.DUPLICATE_POSITIONS]: {
    severity: "error",
    colorScheme: "red",
    suggestions: [
      "Each blank position should appear only once in question text",
      "Check for duplicate [blank_N] tags and remove extras",
      "Use sequential numbering: [blank_1], [blank_2], [blank_3]",
    ],
  },
  [BlankValidationErrorCode.NON_SEQUENTIAL_POSITIONS]: {
    severity: "error",
    colorScheme: "red",
    suggestions: [
      "Renumber blanks sequentially starting from 1",
      "Avoid gaps in numbering (e.g., [blank_1], [blank_3])",
      "Update blank configurations to match sequential positions",
    ],
  },
  [BlankValidationErrorCode.POSITION_GAP]: {
    severity: "error",
    colorScheme: "red",
    suggestions: [
      "Fill in missing blank positions",
      "Ensure continuous numbering without gaps",
      "Add missing [blank_N] tags to question text",
    ],
  },
  [BlankValidationErrorCode.MISSING_BLANK_CONFIG]: {
    severity: "error",
    colorScheme: "orange",
    suggestions: [
      "Add blank configurations for each [blank_N] tag in question text",
      'Click "Add Blank" to create missing configurations',
      "Ensure position numbers match question text",
    ],
  },
  [BlankValidationErrorCode.EXTRA_BLANK_CONFIG]: {
    severity: "error",
    colorScheme: "orange",
    suggestions: [
      "Remove blank configurations without corresponding [blank_N] tags",
      "Add missing [blank_N] tags to question text",
      "Ensure synchronization between text and configurations",
    ],
  },
  [BlankValidationErrorCode.UNSYNCHRONIZED_BLANKS]: {
    severity: "error",
    colorScheme: "orange",
    suggestions: [
      "Ensure each [blank_N] tag has a corresponding blank configuration",
      "Remove extra configurations or add missing question text tags",
      "Check position numbers match exactly",
    ],
  },
  [BlankValidationErrorCode.NO_BLANKS_IN_TEXT]: {
    severity: "error",
    colorScheme: "blue",
    suggestions: [
      "Add at least one [blank_1] tag to your question text",
      "Identify the word or phrase to be filled in",
      "Replace it with [blank_1], [blank_2], etc.",
    ],
  },
  [BlankValidationErrorCode.NO_BLANK_CONFIGURATIONS]: {
    severity: "error",
    colorScheme: "blue",
    suggestions: [
      'Click "Add Blank" to create blank configurations',
      "Provide correct answers for each blank position",
      "Configure answer variations if needed",
    ],
  },
}

/**
 * Individual error display component
 */
function ValidationErrorItem({ error }: { error: BlankValidationError }) {
  const config = ERROR_CONFIGS[error.code]

  const getBorderColor = (severity: string) => {
    switch (severity) {
      case "error":
        return "red.400"
      case "warning":
        return "orange.400"
      case "info":
        return "blue.400"
      default:
        return "gray.400"
    }
  }

  const getBgColor = (severity: string) => {
    switch (severity) {
      case "error":
        return "red.50"
      case "warning":
        return "orange.50"
      case "info":
        return "blue.50"
      default:
        return "gray.50"
    }
  }

  return (
    <Box
      p={3}
      bg={getBgColor(config.severity)}
      borderRadius="md"
      borderLeft="4px solid"
      borderColor={getBorderColor(config.severity)}
      mb={3}
    >
      <Text
        fontWeight="medium"
        fontSize="sm"
        mb={2}
        color={`${config.colorScheme}.700`}
      >
        {error.message}
      </Text>

      {config.suggestions.length > 0 && (
        <Box>
          <Text fontSize="xs" fontWeight="medium" color="gray.600" mb={1}>
            How to fix:
          </Text>
          <Box pl={2}>
            {config.suggestions.map((suggestion, index) => (
              <Text key={index} fontSize="xs" color="gray.600" mb={1}>
                • {suggestion}
              </Text>
            ))}
          </Box>
        </Box>
      )}

      {/* Show specific details if available */}
      {error.details && (
        <Box mt={2} p={2} bg="gray.100" borderRadius="sm">
          <Text fontSize="xs" fontWeight="medium" color="gray.700" mb={1}>
            Details:
          </Text>
          {error.details.positions && (
            <Text fontSize="xs" color="gray.600">
              Positions: {error.details.positions.join(", ")}
            </Text>
          )}
          {error.details.invalidTags && (
            <Text fontSize="xs" color="gray.600">
              Invalid tags: {error.details.invalidTags.join(", ")}
            </Text>
          )}
          {error.details.missingPositions && (
            <Text fontSize="xs" color="gray.600">
              Missing positions: {error.details.missingPositions.join(", ")}
            </Text>
          )}
          {error.details.extraPositions && (
            <Text fontSize="xs" color="gray.600">
              Extra positions: {error.details.extraPositions.join(", ")}
            </Text>
          )}
        </Box>
      )}
    </Box>
  )
}

/**
 * Main validation errors display component
 */
export function FillInBlankValidationErrors({
  errors,
  className,
}: FillInBlankValidationErrorsProps) {
  if (!errors || errors.length === 0) {
    return null
  }

  // Group errors by severity
  const errorsBySeverity = errors.reduce(
    (acc, error) => {
      const config = ERROR_CONFIGS[error.code]
      const severity = config.severity

      if (!acc[severity]) {
        acc[severity] = []
      }
      acc[severity].push(error)

      return acc
    },
    {} as Record<string, BlankValidationError[]>,
  )

  const hasErrors = errorsBySeverity.error?.length > 0
  const hasWarnings = errorsBySeverity.warning?.length > 0

  return (
    <Box className={className} mb={4}>
      <VStack gap={3} align="stretch">
        {/* Header with error count */}
        <Box
          bg="red.50"
          p={3}
          borderRadius="md"
          borderLeft="4px solid"
          borderColor="red.400"
        >
          <Text fontWeight="bold" color="red.700" fontSize="sm">
            Validation Errors ({errors.length})
          </Text>
          <Text fontSize="xs" color="red.600" mt={1}>
            Please fix the following issues before saving:
          </Text>
        </Box>

        {/* Critical errors */}
        {hasErrors && (
          <Box>
            <Text fontSize="sm" fontWeight="medium" color="red.700" mb={2}>
              Critical Issues:
            </Text>
            {errorsBySeverity.error.map((error, index) => (
              <ValidationErrorItem key={`error-${index}`} error={error} />
            ))}
          </Box>
        )}

        {/* Warnings */}
        {hasWarnings && (
          <Box>
            <Text fontSize="sm" fontWeight="medium" color="orange.700" mb={2}>
              Warnings:
            </Text>
            {errorsBySeverity.warning.map((error, index) => (
              <ValidationErrorItem key={`warning-${index}`} error={error} />
            ))}
          </Box>
        )}

        {/* Info messages */}
        {errorsBySeverity.info && errorsBySeverity.info.length > 0 && (
          <Box>
            <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={2}>
              Information:
            </Text>
            {errorsBySeverity.info.map((error, index) => (
              <ValidationErrorItem key={`info-${index}`} error={error} />
            ))}
          </Box>
        )}

        {/* Quick help */}
        <Box
          bg="blue.50"
          p={3}
          borderRadius="md"
          borderLeft="4px solid"
          borderColor="blue.300"
        >
          <Text fontSize="xs" fontWeight="medium" color="blue.700" mb={1}>
            Quick Help:
          </Text>
          <Text fontSize="xs" color="blue.600">
            Fill-in-the-blank questions need [blank_1], [blank_2] tags in the
            question text with matching blank configurations below. Positions
            must be sequential (1, 2, 3...) and synchronized between text and
            configuration.
          </Text>
        </Box>
      </VStack>
    </Box>
  )
}

/**
 * Compact error summary for inline display
 */
export function FillInBlankValidationSummary({
  errors,
}: { errors: BlankValidationError[] }) {
  if (!errors || errors.length === 0) {
    return null
  }

  const errorCount = errors.length
  const hasMultiple = errorCount > 1

  return (
    <Box
      bg="red.50"
      px={3}
      py={2}
      borderRadius="md"
      border="1px solid"
      borderColor="red.200"
    >
      <Text fontSize="xs" color="red.700" fontWeight="medium">
        ⚠️ {errorCount} validation {hasMultiple ? "errors" : "error"} found
      </Text>
      <Text fontSize="xs" color="red.600" mt={1}>
        {errors[0].message}
        {hasMultiple && ` (and ${errorCount - 1} more)`}
      </Text>
    </Box>
  )
}
