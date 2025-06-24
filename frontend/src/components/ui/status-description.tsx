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
          ? "Extracting and cleaning content from Canvas pages..."
          : "Generating questions using the language model...";
      case "completed":
        const timeAgo = timestamp ? formatTimeAgo(timestamp) : "";
        return isExtraction
          ? `Content extracted successfully${timeAgo ? ` (${timeAgo})` : ""}`
          : `Questions generated successfully${timeAgo ? ` (${timeAgo})` : ""}`;
      case "failed":
        return isExtraction
          ? "Failed to extract content. Please try again."
          : "Failed to generate questions. Please try again.";
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
