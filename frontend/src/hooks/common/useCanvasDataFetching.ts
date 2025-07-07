import { useQuery, type QueryKey } from '@tanstack/react-query'

import { useErrorHandler } from '@/hooks/common'

interface UseCanvasDataFetchingOptions {
  enabled?: boolean
  staleTime?: number
  retry?: number
  retryDelay?: number
}

/**
 * Hook for consistent Canvas API data fetching with standardized
 * retry logic, error handling, and caching behavior.
 */
export function useCanvasDataFetching<T>(
  queryKey: QueryKey,
  queryFn: () => Promise<T>,
  options: UseCanvasDataFetchingOptions = {}
) {
  const { handleError } = useErrorHandler()

  const {
    enabled = true,
    staleTime = 30000, // 30 seconds
    retry = 1,
    retryDelay = 1000,
  } = options

  const query = useQuery({
    queryKey,
    queryFn,
    enabled,
    staleTime,
    retry,
    retryDelay,
  })

  // Handle errors manually since onError was removed in newer versions
  if (query.error) {
    handleError(query.error)
  }

  return query
}
