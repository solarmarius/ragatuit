import {
  Badge,
  Box,
  Button,
  Card,
  HStack,
  Progress,
  Skeleton,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SiCanvas } from "react-icons/si";

import { QuestionsService, type Quiz, QuizService } from "@/client";
import useCustomToast from "@/hooks/useCustomToast";

interface QuestionStatsProps {
  quiz: Quiz;
}

export function QuestionStats({ quiz }: QuestionStatsProps) {
  const { showErrorToast, showSuccessToast } = useCustomToast();
  const queryClient = useQueryClient();

  const {
    data: stats,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["quiz", quiz.id, "questions", "stats"],
    queryFn: async () => {
      if (!quiz.id) {
        throw new Error("Quiz ID is required");
      }
      const fullStats = await QuestionsService.getQuestionStatistics({
        quizId: quiz.id,
      });
      // Convert to legacy format for compatibility
      return {
        total: fullStats.total_questions,
        approved: fullStats.approved_questions,
      };
    },
  });

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
      queryClient.invalidateQueries({ queryKey: ["quiz", quiz.id] });
    },
    onError: (error: any) => {
      const message = error?.body?.detail || "Failed to export quiz to Canvas";
      showErrorToast(message);
    },
  });

  if (isLoading) {
    return <QuestionStatsSkeleton />;
  }

  if (error || !stats) {
    return (
      <Card.Root>
        <Card.Body>
          <Text color="red.500">Failed to load question statistics</Text>
        </Card.Body>
      </Card.Root>
    );
  }

  const progressPercentage =
    stats.total > 0 ? (stats.approved / stats.total) * 100 : 0;

  return (
    <Card.Root>
      <Card.Header>
        <Text fontSize="xl" fontWeight="semibold">
          Question Review Progress
        </Text>
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          <HStack justify="space-between">
            <Text fontWeight="medium" color="gray.700">
              Approved Questions
            </Text>
            <Badge variant="outline" colorScheme="green" size="lg">
              {stats.approved} of {stats.total}
            </Badge>
          </HStack>

          <Box>
            <HStack justify="space-between" mb={2}>
              <Text fontWeight="medium" color="gray.700">
                Progress
              </Text>
              <Text fontSize="sm" color="gray.600">
                {progressPercentage.toFixed(0)}%
              </Text>
            </HStack>
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

          {stats.total > 0 && stats.approved === stats.total && (
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
                mb={quiz.export_status !== "completed" ? 3 : 0}
              >
                All questions have been reviewed and approved!
              </Text>

              {(() => {
                const isExported = quiz.export_status === "completed";
                const isExporting =
                  exportMutation.isPending ||
                  quiz.export_status === "processing";
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
                    <Text
                      fontSize="sm"
                      fontWeight="medium"
                      color="green.600"
                      textAlign="center"
                      mt={2}
                    >
                      ✅ Quiz has been successfully exported to Canvas!
                      {quiz.exported_at && (
                        <Text fontSize="xs" color="green.500" mt={1}>
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
                    </Text>
                  );
                }

                return null;
              })()}
            </Box>
          )}

          {stats.total === 0 && (
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
}

function QuestionStatsSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <Skeleton height="24px" width="200px" />
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          <HStack justify="space-between">
            <Skeleton height="20px" width="120px" />
            <Skeleton height="24px" width="40px" />
          </HStack>
          <HStack justify="space-between">
            <Skeleton height="20px" width="140px" />
            <Skeleton height="24px" width="40px" />
          </HStack>
          <Box>
            <HStack justify="space-between" mb={2}>
              <Skeleton height="20px" width="80px" />
              <Skeleton height="16px" width="30px" />
            </HStack>
            <Skeleton height="8px" width="100%" />
          </Box>
        </VStack>
      </Card.Body>
    </Card.Root>
  );
}
