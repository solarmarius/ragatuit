import {
  Box,
  Button,
  Card,
  Container,
  HStack,
  Tabs,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";

import { QuizService } from "@/client";
import {
  ErrorState,
  LoadingSkeleton,
} from "@/components/Common";
import DeleteQuizConfirmation from "@/components/QuizCreation/DeleteQuizConfirmation";
import { StatusLight } from "@/components/ui/status-light";
import { useQuizStatusPolling } from "@/hooks/common";
import {
  QUIZ_STATUS,
  UI_SIZES,
} from "@/lib/constants";

export const Route = createFileRoute("/_layout/quiz/$id")({
  component: QuizLayout,
});

function QuizLayout() {
  const { id } = Route.useParams();
  const pollingInterval = useQuizStatusPolling();

  // Use router state to detect current route more reliably
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const isQuestionsRoute = pathname.endsWith('/questions');

  const {
    data: quiz,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["quiz", id],
    queryFn: async () => {
      const response = await QuizService.getQuiz({ quizId: id });
      return response;
    },
    refetchInterval: isQuestionsRoute ? false : pollingInterval, // No polling on questions page
    refetchIntervalInBackground: false,
  });

  if (isLoading) {
    return <QuizLayoutSkeleton />;
  }

  if (error || !quiz) {
    return (
      <Container maxW="4xl" py={8}>
        <Card.Root>
          <Card.Body>
            <ErrorState
              title="Quiz Not Found"
              message="The quiz you're looking for doesn't exist or you don't have permission to view it."
              showRetry={false}
            />
          </Card.Body>
        </Card.Root>
      </Container>
    );
  }


  // Check if quiz is ready for approval
  const isQuizReadyForApproval = quiz.status === QUIZ_STATUS.READY_FOR_REVIEW;

  return (
    <Container maxW="6xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Box>
          <HStack gap={3} align="center" justify="space-between">
            <HStack gap={3} align="center">
              <Text fontSize="3xl" fontWeight="bold">
                {quiz.title}
              </Text>
              <StatusLight status={quiz.status || "created"} />
            </HStack>
            <HStack gap={3}>
              {isQuizReadyForApproval && (
                <Button
                  colorPalette="blue"
                  size="sm"
                  asChild
                >
                  <Link to="/quiz/$id/questions" params={{ id }}>
                    Review Quiz
                  </Link>
                </Button>
              )}
              <DeleteQuizConfirmation quizId={id} quizTitle={quiz.title} />
            </HStack>
          </HStack>
          <Text color="gray.600" fontSize="lg">
            Quiz Details
          </Text>
        </Box>

        {/* Tabs */}
        <Tabs.Root
          value={isQuestionsRoute ? "questions" : "info"}
          size="lg"
        >
          <Tabs.List>
            <Tabs.Trigger value="info" asChild>
              <Link to="/quiz/$id" params={{ id }}>
                Quiz Information
              </Link>
            </Tabs.Trigger>
            <Tabs.Trigger value="questions" asChild>
              <Link to="/quiz/$id/questions" params={{ id }}>
                Questions
              </Link>
            </Tabs.Trigger>
          </Tabs.List>

          <Box mt={6}>
            <Outlet />
          </Box>
        </Tabs.Root>
      </VStack>
    </Container>
  );
}

function QuizLayoutSkeleton() {
  return (
    <Container maxW="4xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header Skeleton */}
        <Box>
          <LoadingSkeleton
            height={UI_SIZES.SKELETON.HEIGHT.XXL}
            width={UI_SIZES.SKELETON.WIDTH.TEXT_XL}
          />
          <Box mt={2}>
            <LoadingSkeleton
              height={UI_SIZES.SKELETON.HEIGHT.XL}
              width={UI_SIZES.SKELETON.WIDTH.TEXT_MD}
            />
          </Box>
        </Box>

        {/* Cards Skeleton */}
        {[1, 2, 3, 4].map((i) => (
          <Card.Root key={i}>
            <Card.Header>
              <LoadingSkeleton
                height={UI_SIZES.SKELETON.HEIGHT.XL}
                width={UI_SIZES.SKELETON.WIDTH.TEXT_LG}
              />
            </Card.Header>
            <Card.Body>
              <VStack gap={3} align="stretch">
                <LoadingSkeleton
                  height={UI_SIZES.SKELETON.HEIGHT.LG}
                  width={UI_SIZES.SKELETON.WIDTH.FULL}
                  lines={3}
                />
              </VStack>
            </Card.Body>
          </Card.Root>
        ))}
      </VStack>
    </Container>
  );
}
