import { Box, HStack, Text, VStack } from "@chakra-ui/react"
import {
  MdCheckCircle,
  MdError,
  MdRadioButtonUnchecked,
  MdSchedule,
} from "react-icons/md"

import type { FailureReason, QuizStatus } from "@/client/types.gen"
import { QUIZ_STATUS } from "@/lib/constants"
import { formatTimeAgo } from "@/lib/utils"

/**
 * Props for the QuizPhaseProgress component.
 * Displays a detailed three-phase breakdown of quiz generation progress.
 */
interface QuizPhaseProgressProps {
  /** Current consolidated quiz status */
  status: QuizStatus
  /** Failure reason if status is failed */
  failureReason?: FailureReason | null
  /** Timestamp when content was extracted */
  contentExtractedAt?: string | null
  /** Timestamp when quiz was exported */
  exportedAt?: string | null
  /** Last status update timestamp */
  lastStatusUpdate?: string | null
  /** Whether to show timestamps */
  showTimestamps?: boolean
}

/**
 * Individual phase status derived from consolidated status
 */
type PhaseStatus = "pending" | "processing" | "completed" | "failed" | "partial"

/**
 * Phase information for display
 */
interface Phase {
  id: string
  title: string
  status: PhaseStatus
  description: string
  timestamp?: string | null
  failureMessage?: string
}

/**
 * Maps consolidated quiz status to individual phase statuses
 */
function getPhaseStatuses(
  quizStatus: QuizStatus,
  failureReason?: FailureReason | null,
): { extraction: PhaseStatus; generation: PhaseStatus; export: PhaseStatus } {
  // Handle failed status - determine which phase failed based on failure reason
  if (quizStatus === QUIZ_STATUS.FAILED) {
    if (
      failureReason === "content_extraction_error" ||
      failureReason === "no_content_found"
    ) {
      return { extraction: "failed", generation: "pending", export: "pending" }
    }
    if (
      failureReason === "llm_generation_error" ||
      failureReason === "no_questions_generated"
    ) {
      return {
        extraction: "completed",
        generation: "failed",
        export: "pending",
      }
    }
    if (failureReason === "canvas_export_error") {
      return {
        extraction: "completed",
        generation: "completed",
        export: "failed",
      }
    }
    // Default: assume extraction failed
    return { extraction: "failed", generation: "pending", export: "pending" }
  }

  // Map consolidated status to phase statuses
  switch (quizStatus) {
    case QUIZ_STATUS.CREATED:
      return { extraction: "pending", generation: "pending", export: "pending" }

    case QUIZ_STATUS.EXTRACTING_CONTENT:
      return {
        extraction: "processing",
        generation: "pending",
        export: "pending",
      }

    case QUIZ_STATUS.GENERATING_QUESTIONS:
      return {
        extraction: "completed",
        generation: "processing",
        export: "pending",
      }

    case QUIZ_STATUS.READY_FOR_REVIEW:
      return {
        extraction: "completed",
        generation: "completed",
        export: "pending",
      }

    case QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL:
      return {
        extraction: "completed",
        generation: "partial",
        export: "pending",
      }

    case QUIZ_STATUS.EXPORTING_TO_CANVAS:
      return {
        extraction: "completed",
        generation: "completed",
        export: "processing",
      }

    case QUIZ_STATUS.PUBLISHED:
      return {
        extraction: "completed",
        generation: "completed",
        export: "completed",
      }

    default:
      return { extraction: "pending", generation: "pending", export: "pending" }
  }
}

/**
 * Gets appropriate icon for phase status
 */
function getPhaseIcon(status: PhaseStatus) {
  switch (status) {
    case "completed":
      return <MdCheckCircle size={20} />
    case "processing":
      return <MdSchedule size={20} />
    case "failed":
      return <MdError size={20} />
    case "partial":
      return <MdSchedule size={20} />
    default:
      return <MdRadioButtonUnchecked size={20} />
  }
}

/**
 * Gets appropriate color scheme for phase status
 */
function getPhaseColor(status: PhaseStatus) {
  switch (status) {
    case "completed":
      return "green"
    case "processing":
      return "blue"
    case "failed":
      return "red"
    case "partial":
      return "yellow"
    default:
      return "gray"
  }
}

/**
 * Gets phase-specific descriptions
 */
function getPhaseDescription(phase: string, status: PhaseStatus): string {
  if (status === "failed") {
    switch (phase) {
      case "extraction":
        return "Content extraction failed. Please check your module selection and try again."
      case "generation":
        return "Question generation failed. This may be due to insufficient content or AI service issues."
      case "export":
        return "Canvas export failed. Please check your Canvas permissions and try again."
      default:
        return "Process failed."
    }
  }

  switch (phase) {
    case "extraction":
      switch (status) {
        case "pending":
          return "Waiting to extract content from selected Canvas modules"
        case "processing":
          return "Extracting and processing content from Canvas modules..."
        case "completed":
          return "Content successfully extracted from Canvas modules"
        default:
          return "Content extraction"
      }

    case "generation":
      switch (status) {
        case "pending":
          return "Waiting for content extraction to complete"
        case "processing":
          return "AI is generating multiple-choice questions from extracted content..."
        case "completed":
          return "Questions generated successfully and ready for review"
        case "partial":
          return "Some questions generated successfully - retry available for remaining questions"
        default:
          return "Question generation"
      }

    case "export":
      switch (status) {
        case "pending":
          return "Waiting for questions to be reviewed and approved"
        case "processing":
          return "Exporting approved questions to Canvas as a new quiz..."
        case "completed":
          return "Quiz successfully published to Canvas"
        default:
          return "Canvas export"
      }

    default:
      return ""
  }
}

/**
 * Individual phase component
 */
function PhaseItem({
  phase,
  isLast = false,
}: { phase: Phase; isLast?: boolean }) {
  const color = getPhaseColor(phase.status)
  const icon = getPhaseIcon(phase.status)

  return (
    <Box position="relative">
      <HStack gap={3} align="start">
        {/* Icon */}
        <Box color={`${color}.500`} flexShrink={0} mt={1}>
          {icon}
        </Box>

        {/* Content */}
        <VStack align="start" gap={1} flex={1}>
          <Text fontWeight="medium" color={`${color}.700`}>
            {phase.title}
          </Text>
          <Text fontSize="sm" color="gray.600" lineHeight="1.4">
            {phase.description}
          </Text>
          {phase.timestamp && (
            <Text fontSize="xs" color="gray.500">
              {formatTimeAgo(phase.timestamp)}
            </Text>
          )}
          {phase.failureMessage && (
            <Text fontSize="xs" color="red.600" mt={1}>
              {phase.failureMessage}
            </Text>
          )}
        </VStack>
      </HStack>

      {/* Connecting line */}
      {!isLast && (
        <Box
          position="absolute"
          left="10px"
          top="28px"
          width="2px"
          height="24px"
          bg="gray.200"
        />
      )}
    </Box>
  )
}

/**
 * QuizPhaseProgress component that shows detailed three-phase breakdown
 */
export function QuizPhaseProgress({
  status,
  failureReason,
  contentExtractedAt,
  exportedAt,
  lastStatusUpdate,
  showTimestamps = true,
}: QuizPhaseProgressProps) {
  const phaseStatuses = getPhaseStatuses(status, failureReason)

  const phases: Phase[] = [
    {
      id: "extraction",
      title: "Content Extraction",
      status: phaseStatuses.extraction,
      description: getPhaseDescription("extraction", phaseStatuses.extraction),
      timestamp: showTimestamps ? contentExtractedAt : null,
    },
    {
      id: "generation",
      title: "Question Generation",
      status: phaseStatuses.generation,
      description: getPhaseDescription("generation", phaseStatuses.generation),
      timestamp:
        showTimestamps &&
        (phaseStatuses.generation === "completed" ||
          phaseStatuses.generation === "partial")
          ? lastStatusUpdate
          : null,
    },
    {
      id: "export",
      title: "Canvas Export",
      status: phaseStatuses.export,
      description: getPhaseDescription("export", phaseStatuses.export),
      timestamp: showTimestamps ? exportedAt : null,
    },
  ]

  return (
    <VStack gap={4} align="stretch">
      {phases.map((phase, index) => (
        <PhaseItem
          key={phase.id}
          phase={phase}
          isLast={index === phases.length - 1}
        />
      ))}
    </VStack>
  )
}
