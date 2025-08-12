import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react";
import { Link as RouterLink } from "@tanstack/react-router";
import { memo } from "react";

import type { Quiz } from "@/client/types.gen";
import { QuizProgressIndicator } from "@/components/dashboard/QuizProgressIndicator";
import { Button } from "@/components/ui/button";
import { StatusLight } from "@/components/ui/status-light";
import { UI_COLORS } from "@/lib/constants";
import { getQuizProgressPercentage, getQuizStatusText } from "@/lib/utils";

interface QuizCardProps {
  quiz: Quiz;
  /**
   * Custom action button configuration
   * If not provided, defaults to "View" button linking to quiz details
   */
  actionButton?: {
    text: string;
    to: string;
    params?: Record<string, any>;
    search?: Record<string, any>;
  };
  /**
   * Whether to show course information
   * @default true
   */
  showCourseInfo?: boolean;
  /**
   * Whether to use compact mode with reduced padding and spacing
   * @default false
   */
  compact?: boolean;
  /**
   * Whether to show progress indicator for quizzes in progress
   * Automatically enabled for processing states if not explicitly set
   * @default auto (based on quiz status)
   */
  showProgress?: boolean;
  /**
   * Visual variant for the card styling
   * - "default": Gray background for general quiz lists
   * - "processing": Orange background for quizzes in progress
   * - "auto": Automatically choose based on quiz status
   * @default "auto"
   */
  variant?: "default" | "processing" | "auto";
}

const PROCESSING_STATUSES = [
  "extracting_content",
  "generating_questions",
  "exporting_to_canvas",
];

export const QuizCard = memo(function QuizCard({
  quiz,
  actionButton = { text: "View", to: `/quiz/${quiz.id}` },
  showCourseInfo = true,
  compact = false,
  showProgress,
  variant = "auto",
}: QuizCardProps) {
  // Determine if quiz is in processing state
  const isProcessing = PROCESSING_STATUSES.includes(quiz.status || "");

  // Auto-determine variant based on status if set to auto
  const effectiveVariant =
    variant === "auto" ? (isProcessing ? "processing" : "default") : variant;

  // Auto-determine progress display
  const shouldShowProgress = showProgress ?? effectiveVariant === "processing";

  // Get status-specific data
  const statusText = getQuizStatusText(quiz);
  const progressPercentage = getQuizProgressPercentage(quiz);

  // Styling based on variant
  const cardStyles =
    effectiveVariant === "processing"
      ? {
          borderColor: UI_COLORS.BORDER.ORANGE,
          bg: UI_COLORS.BACKGROUND.ORANGE,
          _hover: { bg: "orange.100" },
        }
      : {
          borderColor: "gray.200",
          bg: "gray.50",
          _hover: { bg: "gray.100" },
        };

  return (
    <Box
      p={compact ? 3 : 4}
      border="1px solid"
      borderRadius="md"
      transition="background-color 0.2s"
      {...cardStyles}
    >
      <VStack align="stretch" gap={compact ? 2 : 3}>
        <VStack align="start" gap={1}>
          <HStack justify="space-between" align="start" width="100%">
            <Text fontWeight="medium" fontSize="sm" lineHeight="tight" truncate>
              {quiz.title}
            </Text>
            <StatusLight status={quiz.status || "created"} />
          </HStack>
          <HStack justify="space-between" align="start" width="100%">
            {showCourseInfo && (
              <Text fontSize="xs" color="gray.600" truncate>
                {quiz.canvas_course_name}
              </Text>
            )}
          </HStack>
        </VStack>

        {/* Progress indicator (only shown for processing quizzes) */}
        {shouldShowProgress && (
          <QuizProgressIndicator
            processingPhase={statusText}
            progressPercentage={progressPercentage}
          />
        )}

        {/* Footer with badges and action */}
        <HStack justify="space-between" align="center" gap={2} flexWrap="wrap">
          <HStack gap={2} flex="1" minW="0">
            <Badge variant="solid" colorScheme="blue" size="sm" flexShrink={0}>
              {quiz.question_count || 0} questions
            </Badge>
          </HStack>

          <Button size="sm" variant="outline" asChild flexShrink={0}>
            <RouterLink
              to={actionButton.to as any}
              params={actionButton.params as any}
              search={actionButton.search as any}
            >
              {actionButton.text}
            </RouterLink>
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
});
