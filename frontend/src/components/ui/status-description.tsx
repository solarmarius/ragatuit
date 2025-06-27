import { formatTimeAgo } from "@/utils/time"
import { Text } from "@chakra-ui/react"

interface StatusDescriptionProps {
  status: string
  type: "extraction" | "generation" | "export"
  timestamp?: string | null
}

export function StatusDescription({
  status,
  type,
  timestamp,
}: StatusDescriptionProps) {
  const getDescription = () => {
    const isExtraction = type === "extraction"
    const isGeneration = type === "generation"
    const isExport = type === "export"

    switch (status) {
      case "pending":
        if (isExtraction) return "Waiting to extract content from selected modules"
        if (isGeneration) return "Waiting for content extraction to complete"
        if (isExport) return "Waiting for questions to be approved before export"
        return "Waiting to start"

      case "processing":
        if (isExtraction) return "Extracting and cleaning content from Canvas pages. This may take a few minutes depending on the amount of content."
        if (isGeneration) return "Generating questions using the language model. This process typically takes 2-5 minutes."
        if (isExport) return "Exporting quiz to Canvas. This includes creating the quiz and adding all approved questions."
        return "Processing..."

      case "completed": {
        const timeAgo = timestamp ? formatTimeAgo(timestamp) : ""
        if (isExtraction) return `Content extracted successfully${timeAgo ? ` (${timeAgo})` : ""}`
        if (isGeneration) return `Questions generated successfully${timeAgo ? ` (${timeAgo})` : ""}`
        if (isExport) return `Quiz exported to Canvas successfully${timeAgo ? ` (${timeAgo})` : ""}`
        return "Completed"
      }

      case "failed":
        if (isExtraction) return "Content extraction failed. This may be due to network issues, Canvas permissions, or content size limits. Try again or contact support if the issue persists."
        if (isGeneration) return "Question generation failed. This may be due to LLM service issues or content processing errors. Try again or contact support if the issue persists."
        if (isExport) return "Quiz export to Canvas failed. This may be due to Canvas API issues or permissions. Try again or contact support if the issue persists."
        return "Failed"

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
