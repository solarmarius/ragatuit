/**
 * Hook for conditional polling based on data state.
 * Returns polling interval when condition is met, false otherwise.
 * Designed to work with TanStack Query's refetchInterval option.
 *
 * @template T - Type of data being polled
 *
 * @param shouldPoll - Function that determines if polling should continue based on current data
 * @param interval - Polling interval in milliseconds (default: 5000)
 *
 * @returns Function that takes a query object and returns polling interval or false
 *
 * @example
 * ```tsx
 * // Basic usage with custom condition
 * const pollWhileProcessing = useConditionalPolling(
 *   (data: QuizData) => data?.status === 'processing',
 *   3000 // Poll every 3 seconds
 * )
 *
 * const { data: quiz } = useQuery({
 *   queryKey: ['quiz', quizId],
 *   queryFn: () => QuizzesService.getQuiz(quizId),
 *   refetchInterval: pollWhileProcessing,
 * })
 *
 * // Usage with consolidated status system
 * const pollWhileProcessing = useConditionalPolling(
 *   (data: QuizData) => {
 *     const activeStatuses = ['extracting_content', 'generating_questions', 'exporting_to_canvas']
 *     return activeStatuses.includes(data?.status)
 *   },
 *   2000
 * )
 * ```
 */
export function useConditionalPolling<T>(
  shouldPoll: (data: T | undefined) => boolean,
  interval = 5000,
) {
  return (query: { state: { data?: T } }) => {
    const data = query?.state?.data
    return shouldPoll(data) ? interval : false
  }
}

/**
 * Smart polling for quiz status based on consolidated status system.
 * Uses different polling intervals based on current status:
 * - Active processing: 5000ms (extracting, generating, exporting)
 * - Stable review states: no polling (ready_for_review, ready_for_review_partial)
 * - Terminal states: no polling (published, failed)
 * - Default: 5000ms
 *
 * @returns Function that dynamically determines polling interval based on quiz status
 *
 * @example
 * ```tsx
 * // Use with quiz queries for intelligent polling
 * const { data: quiz } = useQuery({
 *   queryKey: ['quiz', quizId],
 *   queryFn: () => QuizService.getQuiz(quizId),
 *   refetchInterval: useQuizStatusPolling(),
 * })
 * ```
 */
export function useQuizStatusPolling() {
  return (query: { state: { data?: any } }) => {
    const data = query?.state?.data
    if (!data) return 2000 // Poll every 2 seconds when no data

    const status = data.status
    if (!status) return 5000 // Default polling if no status

    // Different polling intervals based on status
    const activeStatuses = [
      "extracting_content",
      "generating_questions",
      "exporting_to_canvas",
    ]

    if (activeStatuses.includes(status)) {
      return 5000 // Poll every 5 seconds for active processes
    }

    if (
      status === "ready_for_review" ||
      status === "ready_for_review_partial"
    ) {
      return false // No polling for stable review states - user action required
    }

    // No polling for terminal states
    if (status === "published" || status === "failed") {
      return false
    }

    return 5000 // Default polling interval for other states
  }
}

/**
 * Smart polling for user quizzes array based on quiz statuses.
 * Optimizes polling by checking all quizzes in the array:
 * - Stops polling when ALL quizzes are in stable states
 * - Continues polling if ANY quiz is in active processing state
 *
 * @returns Function that dynamically determines polling interval based on all quiz statuses
 *
 * @example
 * ```tsx
 * // Use with user quizzes queries for optimized polling
 * const { data: quizzes } = useQuery({
 *   queryKey: ['user', 'quizzes'],
 *   queryFn: () => QuizService.getUserQuizzes(),
 *   refetchInterval: useUserQuizzesPolling(),
 * })
 * ```
 */
export function useUserQuizzesPolling() {
  return (query: { state: { data?: any[] } }) => {
    const quizzes = query?.state?.data
    if (!quizzes || !Array.isArray(quizzes)) {
      return 2000 // Poll every 2 seconds when data is missing/loading
    }

    if (quizzes.length === 0) {
      return false // Stop polling when no quizzes exist - no need to check for updates
    }

    // Check if any quiz is in an active processing state
    const activeStatuses = [
      "extracting_content",
      "generating_questions",
      "exporting_to_canvas",
    ]

    const hasActiveQuizzes = quizzes.some(
      (quiz) => quiz?.status && activeStatuses.includes(quiz.status),
    )

    if (hasActiveQuizzes) {
      return 5000 // Poll every 5 seconds if any quiz is actively processing
    }

    // All quizzes are in stable/terminal states - stop polling to save resources
    return false
  }
}
