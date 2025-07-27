import {
  Card,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";

import { QuizService } from "@/client";
import {
  EmptyState,
  ErrorState,
} from "@/components/Common";
import { QuestionReview } from "@/components/Questions/QuestionReview";
import { QuestionStats } from "@/components/Questions/QuestionStats";
import {
  FAILURE_REASON,
  QUIZ_STATUS,
  UI_TEXT,
} from "@/lib/constants";

export const Route = createFileRoute("/_layout/quiz/$id/questions")({
  component: QuizQuestions,
});

function renderErrorForFailureReason(failureReason: string | null | undefined) {
  if (!failureReason) {
    return null;
  }

  // Get the error message from constants or use generic fallback
  const errorMessage =
    UI_TEXT.FAILURE_MESSAGES[
      failureReason as keyof typeof UI_TEXT.FAILURE_MESSAGES
    ] || UI_TEXT.FAILURE_MESSAGES.GENERIC;

  return (
    <Card.Root>
      <Card.Body>
        <ErrorState
          title={errorMessage.TITLE}
          message={errorMessage.MESSAGE}
          showRetry={false}
        />
      </Card.Body>
    </Card.Root>
  );
}

function QuizQuestions() {
  const { id } = Route.useParams();

  const { data: quiz } = useQuery({
    queryKey: ["quiz", id],
    queryFn: async () => {
      const response = await QuizService.getQuiz({ quizId: id });
      return response;
    },
    refetchInterval: false, // No polling on questions page as specified
  });

  if (!quiz) {
    return (
      <VStack gap={6} align="stretch">
        <EmptyState
          title="Loading Questions"
          description="Please wait while we load the quiz questions."
        />
      </VStack>
    );
  }

  return (
    <VStack gap={6} align="stretch">
      {/* Question Statistics */}
      {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
        quiz.status === QUIZ_STATUS.EXPORTING_TO_CANVAS ||
        quiz.status === QUIZ_STATUS.PUBLISHED ||
        (quiz.status === QUIZ_STATUS.FAILED &&
          quiz.failure_reason ===
            FAILURE_REASON.CANVAS_EXPORT_ERROR)) && (
        <QuestionStats quiz={quiz} />
      )}

      {/* Canvas Export Error Banner */}
      {quiz.status === QUIZ_STATUS.FAILED &&
        quiz.failure_reason === FAILURE_REASON.CANVAS_EXPORT_ERROR &&
        renderErrorForFailureReason(quiz.failure_reason)}

      {/* Question Review */}
      {(quiz.status === QUIZ_STATUS.READY_FOR_REVIEW ||
        quiz.status === QUIZ_STATUS.EXPORTING_TO_CANVAS ||
        quiz.status === QUIZ_STATUS.PUBLISHED ||
        (quiz.status === QUIZ_STATUS.FAILED &&
          quiz.failure_reason ===
            FAILURE_REASON.CANVAS_EXPORT_ERROR)) && (
        <QuestionReview quizId={id} />
      )}

      {/* Error Display for Failed Status (except Canvas Export Error which is handled above) */}
      {quiz.status === QUIZ_STATUS.FAILED &&
        quiz.failure_reason !== FAILURE_REASON.CANVAS_EXPORT_ERROR &&
        renderErrorForFailureReason(quiz.failure_reason)}

      {/* Message when questions aren't ready */}
      {quiz.status !== QUIZ_STATUS.READY_FOR_REVIEW &&
        quiz.status !== QUIZ_STATUS.EXPORTING_TO_CANVAS &&
        quiz.status !== QUIZ_STATUS.PUBLISHED &&
        quiz.status !== QUIZ_STATUS.FAILED && (
          <Card.Root>
            <Card.Body>
              <EmptyState
                title="Questions Not Available Yet"
                description="Questions will appear here once the generation process is complete."
              />
            </Card.Body>
          </Card.Root>
        )}
    </VStack>
  );
}
