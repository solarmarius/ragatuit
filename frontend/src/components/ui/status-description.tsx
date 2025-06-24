import { Text } from "@chakra-ui/react";
import { formatTimeAgo } from "@/utils/time";

interface StatusDescriptionProps {
  status: string;
  type: "extraction" | "generation";
  timestamp?: string | null;
}

export function StatusDescription({
  status,
  type,
  timestamp,
}: StatusDescriptionProps) {
  const getDescription = () => {
    const isExtraction = type === "extraction";

    switch (status) {
      case "pending":
        return isExtraction
          ? "Waiting to extract content from selected modules"
          : "Waiting for content extraction to complete";
      case "processing":
        return isExtraction
          ? "Extracting and cleaning content from Canvas pages. This may take a few minutes depending on the amount of content."
          : "Generating questions using the language model. This process typically takes 2-5 minutes.";
      case "completed":
        const timeAgo = timestamp ? formatTimeAgo(timestamp) : "";
        return isExtraction
          ? `Content extracted successfully${timeAgo ? ` (${timeAgo})` : ""}`
          : `Questions generated successfully${timeAgo ? ` (${timeAgo})` : ""}`;
      case "failed":
        return isExtraction
          ? "Content extraction failed. This may be due to network issues, Canvas permissions, or content size limits. Try again or contact support if the issue persists."
          : "Question generation failed. This may be due to LLM service issues or content processing errors. Try again or contact support if the issue persists.";
      default:
        return "Status unknown";
    }
  };

  return (
    <Text fontSize="sm" color="gray.600">
      {getDescription()}
    </Text>
  );
}
