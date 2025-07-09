import { QuizService } from "@/client"
import { useQuizStatusPolling } from "@/hooks/common"
import { queryKeys } from "@/lib/api"
import { useQuery } from "@tanstack/react-query"

export function useUserQuizzes() {
  return useQuery({
    queryKey: queryKeys.quizzes.userQuizzes(),
    queryFn: QuizService.getUserQuizzesEndpoint,
  })
}

export function useQuizDetail(quizId: string) {
  return useQuery({
    queryKey: queryKeys.quizzes.detail(quizId),
    queryFn: () => QuizService.getQuiz({ quizId }),
    enabled: !!quizId,
    refetchInterval: useQuizStatusPolling(),
    refetchIntervalInBackground: false, // Only poll when tab is active
  })
}
