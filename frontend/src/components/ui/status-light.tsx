import { Box } from "@chakra-ui/react"

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
    if (extractionStatus === "failed" || generationStatus === "failed") {
      return "red.500"
    }

    // Green: Questions have been generated (both completed)
    if (extractionStatus === "completed" && generationStatus === "completed") {
      return "green.500"
    }

    // Orange: Pending generation (any step is pending or processing)
    return "orange.500"
  }

  const getStatusTitle = () => {
    if (extractionStatus === "failed" || generationStatus === "failed") {
      return "Generation failed"
    }

    if (extractionStatus === "completed" && generationStatus === "completed") {
      return "Questions generated successfully"
    }

    if (
      extractionStatus === "processing" ||
      generationStatus === "processing"
    ) {
      return "Generating questions..."
    }

    return "Waiting to generate questions"
  }

  return (
    <Box
      width="12px"
      height="12px"
      borderRadius="full"
      bg={getStatusColor()}
      title={getStatusTitle()}
      cursor="help"
      flexShrink={0}
      boxShadow={`0 0 8px ${getStatusColor()}`}
    />
  )
}
