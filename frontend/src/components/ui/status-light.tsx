import { PROCESSING_STATUSES, UI_SIZES } from "@/lib/constants"
import { Box } from "@chakra-ui/react"

/**
 * Props for the StatusLight component.
 * Displays a colored status indicator based on content extraction and question generation status.
 *
 * Status colors:
 * - Red: Any process failed
 * - Green: Both processes completed successfully
 * - Orange: Processes are pending or in progress
 *
 * @example
 * ```tsx
 * // Basic usage with processing statuses
 * <StatusLight
 *   extractionStatus="completed"
 *   generationStatus="processing"
 * />
 *
 * // With quiz data
 * <StatusLight
 *   extractionStatus={quiz.content_extraction_status}
 *   generationStatus={quiz.llm_generation_status}
 * />
 *
 * // All possible status combinations
 * <StatusLight
 *   extractionStatus="pending"     // waiting to start
 *   generationStatus="pending"
 * />
 * <StatusLight
 *   extractionStatus="processing"  // in progress
 *   generationStatus="pending"
 * />
 * <StatusLight
 *   extractionStatus="completed"   // success
 *   generationStatus="completed"
 * />
 * <StatusLight
 *   extractionStatus="failed"      // error state
 *   generationStatus="pending"
 * />
 * ```
 */
interface StatusLightProps {
  /** Status of content extraction process (pending, processing, completed, failed) */
  extractionStatus: string
  /** Status of LLM question generation process (pending, processing, completed, failed) */
  generationStatus: string
}

export function StatusLight({
  extractionStatus,
  generationStatus,
}: StatusLightProps) {
  const getStatusColor = () => {
    // Red: Something failed
    if (
      extractionStatus === PROCESSING_STATUSES.FAILED ||
      generationStatus === PROCESSING_STATUSES.FAILED
    ) {
      return "red.500"
    }

    // Green: Questions have been generated (both completed)
    if (
      extractionStatus === PROCESSING_STATUSES.COMPLETED &&
      generationStatus === PROCESSING_STATUSES.COMPLETED
    ) {
      return "green.500"
    }

    // Orange: Pending generation (any step is pending or processing)
    return "orange.500"
  }

  const getStatusTitle = () => {
    if (
      extractionStatus === PROCESSING_STATUSES.FAILED ||
      generationStatus === PROCESSING_STATUSES.FAILED
    ) {
      return "Generation failed"
    }

    if (
      extractionStatus === PROCESSING_STATUSES.COMPLETED &&
      generationStatus === PROCESSING_STATUSES.COMPLETED
    ) {
      return "Questions generated successfully"
    }

    if (
      extractionStatus === PROCESSING_STATUSES.PROCESSING ||
      generationStatus === PROCESSING_STATUSES.PROCESSING
    ) {
      return "Generating questions..."
    }

    return "Waiting to generate questions"
  }

  return (
    <Box
      width={UI_SIZES.SKELETON.HEIGHT.SM}
      height={UI_SIZES.SKELETON.HEIGHT.SM}
      borderRadius="full"
      bg={getStatusColor()}
      title={getStatusTitle()}
      cursor="help"
      flexShrink={0}
      boxShadow={`0 0 8px ${getStatusColor()}`}
    />
  )
}
