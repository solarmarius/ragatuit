import { Box } from "@chakra-ui/react"
import { PROCESSING_STATUSES, UI_SIZES } from "@/lib/constants"

interface StatusLightProps {
  extractionStatus: string
  generationStatus: string
}

export function StatusLight({
  extractionStatus,
  generationStatus,
}: StatusLightProps) {
  const getStatusColor = () => {
    // Red: Something failed
    if (extractionStatus === PROCESSING_STATUSES.FAILED || generationStatus === PROCESSING_STATUSES.FAILED) {
      return "red.500"
    }

    // Green: Questions have been generated (both completed)
    if (extractionStatus === PROCESSING_STATUSES.COMPLETED && generationStatus === PROCESSING_STATUSES.COMPLETED) {
      return "green.500"
    }

    // Orange: Pending generation (any step is pending or processing)
    return "orange.500"
  }

  const getStatusTitle = () => {
    if (extractionStatus === PROCESSING_STATUSES.FAILED || generationStatus === PROCESSING_STATUSES.FAILED) {
      return "Generation failed"
    }

    if (extractionStatus === PROCESSING_STATUSES.COMPLETED && generationStatus === PROCESSING_STATUSES.COMPLETED) {
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
