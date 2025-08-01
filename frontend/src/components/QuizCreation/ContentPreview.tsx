import { Box, HStack, Spinner, Text, VStack } from "@chakra-ui/react";
import { memo } from "react";

interface ContentPreviewProps {
  /** Content preview text */
  content: string;
  /** Word count of the full content */
  wordCount: number;
  /** Whether content is being processed */
  isLoading?: boolean;
  /** Processing metadata */
  metadata?: Record<string, any>;
}

/**
 * Content preview component for manual modules.
 *
 * Features:
 * - Displays processed content preview
 * - Shows word count and metadata
 * - Loading state during processing
 * - Responsive design
 *
 * @example
 * ```tsx
 * <ContentPreview
 *   content="This is a preview of the processed content..."
 *   wordCount={150}
 *   metadata={{ processingTime: 1.2 }}
 *   isLoading={false}
 * />
 * ```
 */
export const ContentPreview = memo(function ContentPreview({
  content,
  wordCount,
  isLoading = false,
}: ContentPreviewProps) {
  if (isLoading) {
    return (
      <VStack gap={4} align="center" py={8}>
        <Spinner size="lg" color="blue.500" />
        <VStack gap={1}>
          <Text fontSize="lg" fontWeight="medium">
            Processing content...
          </Text>
          <Text fontSize="sm" color="gray.600">
            This may take a few seconds
          </Text>
        </VStack>
      </VStack>
    );
  }

  if (!content) {
    return (
      <Box p={6} bg="gray.50" borderRadius="md" textAlign="center">
        <Text color="gray.600">No content to preview yet</Text>
      </Box>
    );
  }

  return (
    <VStack gap={4} align="stretch">
      <HStack justify="space-between" align="center">
        <Text fontSize="lg" fontWeight="semibold">
          Content Preview
        </Text>

        <HStack gap={4}>
          <Box>
            <Text fontSize="sm" color="gray.600">
              Word Count
            </Text>
            <Text fontSize="lg" fontWeight="bold" color="blue.600">
              {wordCount.toLocaleString()}
            </Text>
          </Box>
        </HStack>
      </HStack>

      <Box
        p={4}
        bg="gray.50"
        border="1px solid"
        borderColor="gray.200"
        borderRadius="md"
        maxH="300px"
        overflowY="auto"
      >
        <Text
          fontSize="sm"
          lineHeight="1.6"
          color="gray.700"
          whiteSpace="pre-wrap"
          wordBreak="break-word"
        >
          {content}
        </Text>
      </Box>
    </VStack>
  );
});
