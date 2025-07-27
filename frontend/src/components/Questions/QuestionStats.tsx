import {
  Badge,
  Box,
  Button,
  Card,
  HStack,
  Progress,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { memo, useMemo } from "react";
import { SiCanvas } from "react-icons/si";

import { type Quiz, QuizService } from "@/client";
import { ErrorState, LoadingSkeleton } from "@/components/Common";
import { useCustomToast, useErrorHandler } from "@/hooks/common";
import { QUIZ_STATUS, UI_SIZES } from "@/lib/constants";
import { queryKeys, questionStatsQueryConfig } from "@/lib/queryConfig";
import {
  type QuestionStats as TypedQuestionStats,
  mergeLegacyStats,
} from "@/types/questionStats";

/**
 * Props for the QuestionStats component.
 * Displays question approval statistics and Canvas export functionality.
 * Shows progress bar, approval counts, and export status.
 *
 * @example
 * ```tsx
 * // Basic usage with quiz data
 * <QuestionStats quiz={quiz} />
 *
 * // Usage in a dashboard panel
 * function QuizDashboard({ quizId }: { quizId: string }) {
 *   const { data: quiz } = useQuery(['quiz', quizId], getQuiz)
 *
 *   return (
 *     <VStack gap={4}>
 *       <QuestionStats quiz={quiz} />
 *       <QuestionReview quizId={quizId} />
 *     </VStack>
 *   )
 * }
 *
 * // Usage with conditional rendering
 * {quiz && <QuestionStats quiz={quiz} />}
 * ```
 */
interface QuestionStatsProps {
  /** The quiz object containing ID and export status information */
  quiz: Quiz;
}

export const QuestionStats = memo(function QuestionStats({
  quiz,
}: QuestionStatsProps) {
  const { showSuccessToast } = useCustomToast();
  const { handleError } = useErrorHandler();
  const queryClient = useQueryClient();

  const {
    data: rawStats,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKeys.quizQuestionStats(quiz.id!),
    queryFn: async () => {
      if (!quiz.id) {
        throw new Error("Quiz ID is required");
      }
      return await QuizService.getQuizQuestionStats({
        quizId: quiz.id,
      });
    },
    ...questionStatsQueryConfig,
    enabled: !!quiz.id, // Only run query if quiz.id exists
  });

  // Convert legacy stats format to typed format
  const stats: TypedQuestionStats | null = rawStats
    ? mergeLegacyStats(rawStats)
    : null;

  // Calculate progress percentage with memoization
  const progressPercentage = useMemo(
    () => (stats?.approval_rate ? stats.approval_rate * 100 : 0),
    [stats?.approval_rate]
  );

  // Export quiz to Canvas mutation
  const exportMutation = useMutation({
    mutationFn: async () => {
      if (!quiz.id) {
        throw new Error("Quiz ID is required");
      }
      return await QuizService.exportQuizToCanvas({ quizId: quiz.id });
    },
    onSuccess: () => {
      showSuccessToast("Quiz export to Canvas started successfully");
      // Invalidate quiz queries to trigger status updates and polling
      queryClient.invalidateQueries({ queryKey: queryKeys.quiz(quiz.id!) });
    },
    onError: handleError,
  });

  if (isLoading) {
    return <QuestionStatsSkeleton />;
  }

  if (error || !stats) {
    return (
      <Card.Root>
        <Card.Body>
          <ErrorState
            title="Failed to load question statistics"
            message="There was an error loading the statistics for this quiz."
            showRetry={false}
          />
        </Card.Body>
      </Card.Root>
    );
  }

  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" mb={2}>
          {" "}
          <Text fontSize="xl" fontWeight="semibold">
            Progress
          </Text>
          <HStack justify="flex-end" mb={2}>
            <Text fontSize="sm" color="gray.600">
              {progressPercentage.toFixed(0)}%
            </Text>
            <HStack justify="center">
              <Badge variant="outline" colorScheme="green" size="lg">
                {stats.approved_questions} of {stats.total_questions}
              </Badge>
            </HStack>
          </HStack>
        </HStack>
        <Box>
          <Progress.Root
            value={progressPercentage}
            size="lg"
            colorPalette="green"
          >
            <Progress.Track>
              <Progress.Range />
            </Progress.Track>
          </Progress.Root>
        </Box>
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          {stats.total_questions > 0 &&
            stats.approved_questions === stats.total_questions && (
              <Box
                p={3}
                bg="green.50"
                borderRadius="md"
                border="1px solid"
                borderColor="green.200"
              >
                <Text
                  fontSize="sm"
                  fontWeight="medium"
                  color="green.700"
                  textAlign="center"
                  mb={quiz.status !== QUIZ_STATUS.PUBLISHED ? 3 : 2}
                >
                  All questions have been reviewed and approved!
                </Text>

                {(() => {
                  const isExported = quiz.status === QUIZ_STATUS.PUBLISHED;
                  const isExporting =
                    exportMutation.isPending ||
                    quiz.status === QUIZ_STATUS.EXPORTING_TO_CANVAS;
                  const canExport = !isExported;

                  if (canExport) {
                    return (
                      <Button
                        size="lg"
                        colorPalette="green"
                        onClick={() => exportMutation.mutate()}
                        loading={isExporting}
                        width="100%"
                      >
                        <SiCanvas />
                        Post to Canvas
                      </Button>
                    );
                  }

                  if (isExported) {
                    return (
                      <VStack gap={1}>
                        <Text
                          fontSize="sm"
                          fontWeight="medium"
                          color="green.600"
                          textAlign="center"
                        >
                          Quiz has been successfully exported to Canvas
                        </Text>
                        {quiz.exported_at && (
                          <Text
                            fontSize="xs"
                            color="green.500"
                            textAlign="center"
                          >
                            Exported on{" "}
                            {new Date(quiz.exported_at).toLocaleDateString(
                              "en-GB",
                              {
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              }
                            )}
                          </Text>
                        )}
                      </VStack>
                    );
                  }

                  return null;
                })()}
              </Box>
            )}

          {stats.total_questions === 0 && (
            <Box
              p={3}
              bg="gray.50"
              borderRadius="md"
              border="1px solid"
              borderColor="gray.200"
            >
              <Text fontSize="sm" color="gray.600" textAlign="center">
                No questions generated yet. Questions will appear here once
                generation is complete.
              </Text>
            </Box>
          )}
        </VStack>
      </Card.Body>
    </Card.Root>
  );
});

function QuestionStatsSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <LoadingSkeleton
          height={UI_SIZES.SKELETON.HEIGHT.XL}
          width={UI_SIZES.SKELETON.WIDTH.TEXT_LG}
        />
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          <HStack justify="space-between">
            <LoadingSkeleton
              height={UI_SIZES.SKELETON.HEIGHT.LG}
              width={UI_SIZES.SKELETON.WIDTH.TEXT_MD}
            />
            <LoadingSkeleton
              height={UI_SIZES.SKELETON.HEIGHT.XL}
              width={UI_SIZES.SKELETON.WIDTH.SM}
            />
          </HStack>
          <HStack justify="space-between">
            <LoadingSkeleton
              height={UI_SIZES.SKELETON.HEIGHT.LG}
              width={UI_SIZES.SKELETON.WIDTH.TEXT_LG}
            />
            <LoadingSkeleton
              height={UI_SIZES.SKELETON.HEIGHT.XL}
              width={UI_SIZES.SKELETON.WIDTH.SM}
            />
          </HStack>
          <Box>
            <HStack justify="space-between" mb={2}>
              <LoadingSkeleton
                height={UI_SIZES.SKELETON.HEIGHT.LG}
                width={UI_SIZES.SKELETON.WIDTH.LG}
              />
              <LoadingSkeleton
                height={UI_SIZES.SKELETON.HEIGHT.MD}
                width={UI_SIZES.SKELETON.WIDTH.XS}
              />
            </HStack>
            <LoadingSkeleton
              height={UI_SIZES.PANEL.PROGRESS_HEIGHT}
              width={UI_SIZES.SKELETON.WIDTH.FULL}
            />
          </Box>
        </VStack>
      </Card.Body>
    </Card.Root>
  );
}
