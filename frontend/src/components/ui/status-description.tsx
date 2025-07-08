import { QUIZ_STATUS, UI_TEXT } from "@/lib/constants"
import { formatTimeAgo } from "@/lib/utils"
import { Text } from "@chakra-ui/react"
import type { QuizStatus, FailureReason } from "@/client/types.gen"

interface StatusDescriptionProps {
  /** Current quiz status */
  status: QuizStatus
  /** Failure reason if status is failed */
  failureReason?: FailureReason | null
  /** Last status update timestamp */
  timestamp?: string | null
  /** Whether to show detailed description */
  detailed?: boolean
}

export function StatusDescription({
  status,
  failureReason,
  timestamp,
  detailed = false,
}: StatusDescriptionProps) {
  const getDescription = () => {
    const timeAgo = timestamp ? formatTimeAgo(timestamp) : ""

    switch (status) {
      case QUIZ_STATUS.CREATED:
        return detailed
          ? "Quiz created and ready to start content extraction"
          : UI_TEXT.STATUS.CREATED

      case QUIZ_STATUS.EXTRACTING_CONTENT:
        return detailed
          ? "Extracting and cleaning content from Canvas pages. This may take a few minutes depending on the amount of content."
          : UI_TEXT.STATUS.EXTRACTING_CONTENT

      case QUIZ_STATUS.GENERATING_QUESTIONS:
        return detailed
          ? "Generating questions using the language model. This process typically takes 2-5 minutes."
          : UI_TEXT.STATUS.GENERATING_QUESTIONS

      case QUIZ_STATUS.READY_FOR_REVIEW:
        return detailed
          ? `Questions generated successfully${timeAgo ? ` (${timeAgo})` : ""}`
          : UI_TEXT.STATUS.READY_FOR_REVIEW

      case QUIZ_STATUS.EXPORTING_TO_CANVAS:
        return detailed
          ? "Exporting quiz to Canvas. This includes creating the quiz and adding all approved questions."
          : UI_TEXT.STATUS.EXPORTING_TO_CANVAS

      case QUIZ_STATUS.PUBLISHED:
        return detailed
          ? `Quiz exported to Canvas successfully${timeAgo ? ` (${timeAgo})` : ""}`
          : UI_TEXT.STATUS.PUBLISHED

      case QUIZ_STATUS.FAILED:
        if (detailed && failureReason) {
          const errorMessages = {
            content_extraction_error: "Content extraction failed. This may be due to network issues, Canvas permissions, or content size limits.",
            no_content_found: "No content found in the selected modules. Please check your module selection.",
            llm_generation_error: "Question generation failed. This may be due to LLM service issues or content processing errors.",
            no_questions_generated: "No questions could be generated from the extracted content. Please try different modules.",
            canvas_export_error: "Quiz export to Canvas failed. This may be due to Canvas API issues or permissions.",
            network_error: "Network error occurred. Please check your connection and try again.",
            validation_error: "Validation error occurred. Please check your quiz settings.",
          }
          return errorMessages[failureReason] || "Process failed"
        }
        return UI_TEXT.STATUS.FAILED

      default:
        return "Status unknown"
    }
  }

  return (
    <Text fontSize="sm" color="gray.600">
      {getDescription()}
    </Text>
  )
}
