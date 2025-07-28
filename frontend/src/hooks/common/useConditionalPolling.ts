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
 * - Active processing: 2000ms (extracting, generating, exporting)
 * - Ready for review: 10000ms (slower polling)
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

    if (status === "ready_for_review") {
      return 10000 // Poll every 10 seconds for review state
    }

    // No polling for terminal states
    if (status === "published" || status === "failed") {
      return false
    }

    return 5000 // Default polling interval for other states
  }
}
