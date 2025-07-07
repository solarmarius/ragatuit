/**
 * Hook for conditional polling based on data state.
 * Returns polling interval when condition is met, false otherwise.
 */
export function useConditionalPolling<T>(
  shouldPoll: (data: T | undefined) => boolean,
  interval: number = 5000
) {
  return (query: { state: { data?: T } }) => {
    const data = query?.state?.data
    return shouldPoll(data) ? interval : false
  }
}

/**
 * Predefined polling condition for quiz processing status.
 * Polls while any status is pending or processing.
 */
export function useQuizStatusPolling(interval: number = 5000) {
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
