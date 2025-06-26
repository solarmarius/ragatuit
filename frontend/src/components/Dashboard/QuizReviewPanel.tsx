import {
  Badge,
  Box,
  Card,
  HStack,
  Skeleton,
  Text,
  VStack,
} from "@chakra-ui/react";
import { Link as RouterLink } from "@tanstack/react-router";

import type { Quiz } from "@/client/types.gen";
import { Button } from "@/components/ui/button";
import { StatusLight } from "@/components/ui/status-light";
import { getQuizzesNeedingReview } from "@/utils/quizFilters";

interface QuizReviewPanelProps {
  quizzes: Quiz[];
  isLoading: boolean;
}

export function QuizReviewPanel({ quizzes, isLoading }: QuizReviewPanelProps) {
  const reviewQuizzes = getQuizzesNeedingReview(quizzes);

  if (isLoading) {
    return <QuizReviewPanelSkeleton />;
  }

  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <Text fontSize="lg" fontWeight="semibold">
            Quizzes Needing Review
          </Text>
          <Badge variant="outline" colorScheme="green">
            {reviewQuizzes.length}
          </Badge>
        </HStack>
        <Text fontSize="sm" color="gray.600">
          Completed quizzes ready for question approval
        </Text>
      </Card.Header>
      <Card.Body>
        {reviewQuizzes.length === 0 ? (
          <Box textAlign="center" py={6}>
            <Text fontSize="sm" color="gray.500" mb={2}>
              No quizzes need review
            </Text>
            <Text fontSize="sm" color="gray.400">
              Generated quizzes will appear here when ready for approval
            </Text>
          </Box>
        ) : (
          <VStack gap={4} align="stretch">
            {reviewQuizzes.slice(0, 5).map((quiz) => (
              <Box
                key={quiz.id}
                p={3}
                border="1px solid"
                borderColor="gray.200"
                borderRadius="md"
                bg="gray.50"
                _hover={{ bg: "gray.100" }}
                transition="background-color 0.2s"
              >
                <VStack align="stretch" gap={2}>
                  <VStack align="start" gap={1}>
                    <HStack justify="space-between" align="start" width="100%">
                      <Text
                        fontWeight="medium"
                        fontSize="sm"
                        lineHeight="tight"
                        truncate
                      >
                        {quiz.title}
                      </Text>
                      <StatusLight
                        extractionStatus={
                          quiz.content_extraction_status || "pending"
                        }
                        generationStatus={
                          quiz.llm_generation_status || "pending"
                        }
                      />
                    </HStack>
                    <Text fontSize="xs" color="gray.600" truncate>
                      {quiz.canvas_course_name}
                    </Text>
                  </VStack>

                  <HStack
                    justify="space-between"
                    align="center"
                    gap={2}
                    flexWrap="wrap"
                  >
                    <HStack gap={2} flex="1" minW="0">
                      <Badge
                        variant="solid"
                        colorScheme="blue"
                        size="sm"
                        flexShrink={0}
                      >
                        {quiz.question_count} questions
                      </Badge>
                      {quiz.llm_model && (
                        <Badge
                          variant="outline"
                          colorScheme="purple"
                          size="sm"
                          flexShrink={0}
                        >
                          {quiz.llm_model}
                        </Badge>
                      )}
                    </HStack>

                    <Button size="sm" variant="outline" asChild flexShrink={0}>
                      <RouterLink
                        to="/quiz/$id"
                        params={{ id: quiz.id || "" }}
                        search={{ tab: "questions" }}
                      >
                        Review
                      </RouterLink>
                    </Button>
                  </HStack>
                </VStack>
              </Box>
            ))}

            {reviewQuizzes.length > 5 && (
              <Box textAlign="center" pt={2}>
                <Text fontSize="sm" color="gray.500">
                  +{reviewQuizzes.length - 5} more quizzes need review
                </Text>
                <Button size="sm" variant="ghost" asChild mt={2}>
                  <RouterLink to="/quizzes">View All Quizzes</RouterLink>
                </Button>
              </Box>
            )}
          </VStack>
        )}
      </Card.Body>
    </Card.Root>
  );
}

function QuizReviewPanelSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <Skeleton height="24px" width="180px" />
          <Skeleton height="20px" width="30px" />
        </HStack>
        <Skeleton height="16px" width="250px" mt={2} />
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          {[1, 2, 3].map((i) => (
            <Box
              key={i}
              p={4}
              border="1px solid"
              borderColor="gray.200"
              borderRadius="md"
              bg="gray.50"
            >
              <VStack align="stretch" gap={3}>
                <HStack justify="space-between" align="start">
                  <VStack align="start" gap={1} flex={1}>
                    <Skeleton height="16px" width="140px" />
                    <Skeleton height="12px" width="100px" />
                  </VStack>
                  <Skeleton height="12px" width="12px" borderRadius="full" />
                </HStack>

                <HStack justify="space-between" align="center">
                  <HStack gap={2}>
                    <Skeleton height="20px" width="80px" />
                    <Skeleton height="20px" width="60px" />
                  </HStack>
                  <Skeleton height="24px" width="100px" />
                </HStack>
              </VStack>
            </Box>
          ))}
        </VStack>
      </Card.Body>
    </Card.Root>
  );
}
