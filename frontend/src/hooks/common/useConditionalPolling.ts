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
 * // Usage with multiple conditions
 * const pollWhileAnyProcessing = useConditionalPolling(
 *   (data: QuizData) => {
 *     return data?.extraction_status === 'processing' ||
 *            data?.generation_status === 'processing' ||
 *            data?.export_status === 'processing'
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
 * Predefined polling condition for quiz processing status.
 * Polls while any status is pending or processing. Checks content extraction,
 * LLM generation, and export status for active processing states.
 *
 * @param interval - Polling interval in milliseconds (default: 5000)
 *
 * @returns Function that can be used with TanStack Query's refetchInterval
 *
 * @example
 * ```tsx
 * // Use with quiz queries to poll while processing
 * const { data: quiz, isLoading } = useQuery({
 *   queryKey: ['quiz', quizId],
 *   queryFn: () => QuizzesService.getQuiz(quizId),
 *   refetchInterval: useQuizStatusPolling(3000), // Poll every 3 seconds
 * })
 *
 * // Custom interval for different polling needs
 * const { data: quizProgress } = useQuery({
 *   queryKey: ['quiz', 'progress', quizId],
 *   queryFn: () => QuizzesService.getQuizProgress(quizId),
 *   refetchInterval: useQuizStatusPolling(10000), // Poll every 10 seconds
 * })
 * ```
 */
export function useQuizStatusPolling(interval = 5000) {
  return useConditionalPolling((data: any) => {
    if (!data) return false

    const extractionStatus = data.content_extraction_status || "pending"
    const generationStatus = data.llm_generation_status || "pending"
    const exportStatus = data.export_status || "pending"

    return (
      extractionStatus === "pending" ||
      extractionStatus === "processing" ||
      generationStatus === "pending" ||
      generationStatus === "processing" ||
      exportStatus === "pending" ||
      exportStatus === "processing"
    )
  }, interval)
}
