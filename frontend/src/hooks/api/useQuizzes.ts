import { QuizService } from "@/client"
import { useQuizStatusPolling } from "@/hooks/common"
import { queryKeys } from "@/lib/queryConfig"
import { useQuery } from "@tanstack/react-query"

export function useUserQuizzes() {
  return useQuery({
    queryKey: queryKeys.userQuizzes(),
    queryFn: QuizService.getUserQuizzesEndpoint,
    refetchInterval: useQuizStatusPolling(),
    refetchIntervalInBackground: false, // Only poll when tab is active
  })
}

export function useQuizDetail(quizId: string) {
  return useQuery({
    queryKey: queryKeys.quiz(quizId),
    queryFn: () => QuizService.getQuiz({ quizId }),
    enabled: !!quizId,
    refetchInterval: useQuizStatusPolling(),
    refetchIntervalInBackground: false, // Only poll when tab is active
  })
}
