import type { QuizStatus } from "@/client/types.gen"
import { QUIZ_STATUS, UI_SIZES, UI_TEXT } from "@/lib/constants"
import { Box } from "@chakra-ui/react"

/**
 * Props for the StatusLight component.
 * Displays a colored status indicator based on consolidated quiz status.
 *
 * Status colors:
 * - 🔴 Red: failed - Any process failed
 * - 🟠 Orange: created, extracting_content, generating_questions - Pending/In progress
 * - 🟡 Yellow: exporting_to_canvas - Exporting to Canvas
 * - 🟣 Purple: ready_for_review, ready_for_review_partial - Awaiting user review
 * - 🟢 Green: published - Published to Canvas
 *
 * @example
 * ```tsx
 * // Basic usage with quiz status
 * <StatusLight status="extracting_content" />
 *
 * // With quiz data
 * <StatusLight status={quiz.status} />
 *
 * // All possible statuses
 * <StatusLight status="created" />           // Orange - Ready to start
 * <StatusLight status="extracting_content" /> // Orange - Extracting content
 * <StatusLight status="generating_questions" /> // Orange - Generating questions
 * <StatusLight status="ready_for_review" />   // Purple - Ready for review
 * <StatusLight status="ready_for_review_partial" /> // Purple - Partial success, ready for review
 * <StatusLight status="exporting_to_canvas" /> // Yellow - Exporting to Canvas
 * <StatusLight status="published" />          // Green - Published to Canvas
 * <StatusLight status="failed" />             // Red - Failed
 * ```
 */
interface StatusLightProps {
  /** Consolidated quiz status */
  status: QuizStatus
}

export function StatusLight({ status }: StatusLightProps) {
  const getStatusColor = () => {
    switch (status) {
      case QUIZ_STATUS.FAILED:
        return "red.500"
      case QUIZ_STATUS.READY_FOR_REVIEW:
      case QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL:
        return "purple.500"
      case QUIZ_STATUS.EXPORTING_TO_CANVAS:
        return "yellow.500"
      case QUIZ_STATUS.PUBLISHED:
        return "green.500"
      default:
        return "orange.500"
    }
  }

  const getStatusTitle = () => {
    switch (status) {
      case QUIZ_STATUS.CREATED:
        return UI_TEXT.STATUS.CREATED
      case QUIZ_STATUS.EXTRACTING_CONTENT:
        return UI_TEXT.STATUS.EXTRACTING_CONTENT
      case QUIZ_STATUS.GENERATING_QUESTIONS:
        return UI_TEXT.STATUS.GENERATING_QUESTIONS
      case QUIZ_STATUS.READY_FOR_REVIEW:
        return UI_TEXT.STATUS.READY_FOR_REVIEW
      case QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL:
        return UI_TEXT.STATUS.READY_FOR_REVIEW_PARTIAL
      case QUIZ_STATUS.EXPORTING_TO_CANVAS:
        return UI_TEXT.STATUS.EXPORTING_TO_CANVAS
      case QUIZ_STATUS.PUBLISHED:
        return UI_TEXT.STATUS.PUBLISHED
      case QUIZ_STATUS.FAILED:
        return UI_TEXT.STATUS.FAILED
      default:
        return "Unknown status"
    }
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
