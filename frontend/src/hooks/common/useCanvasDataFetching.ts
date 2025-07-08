import { type QueryKey, useQuery } from "@tanstack/react-query"

import { useErrorHandler } from "@/hooks/common"

interface UseCanvasDataFetchingOptions {
  enabled?: boolean
  staleTime?: number
  retry?: number
  retryDelay?: number
}

/**
 * Hook for consistent Canvas API data fetching with standardized
 * retry logic, error handling, and caching behavior. Wraps TanStack Query's
 * useQuery with Canvas-specific defaults and error handling.
 *
 * @template T - Type of data returned by the query
 *
 * @param queryKey - Unique key for the query, used for caching and invalidation
 * @param queryFn - Async function that fetches the data
 * @param options - Configuration options for the query
 * @param options.enabled - Whether the query should run (default: true)
 * @param options.staleTime - Time in milliseconds before data is considered stale (default: 30000)
 * @param options.retry - Number of retry attempts on failure (default: 1)
 * @param options.retryDelay - Delay between retry attempts in milliseconds (default: 1000)
 *
 * @returns TanStack Query object with Canvas-specific error handling
 *
 * @example
 * ```tsx
 * // Basic usage for fetching Canvas courses
 * const { data: courses, isLoading, error } = useCanvasDataFetching(
 *   ['canvas', 'courses'],
 *   () => CanvasService.getCourses(),
 *   {
 *     staleTime: 60000, // 1 minute
 *     retry: 2
 *   }
 * )
 *
 * // Conditional fetching based on user state
 * const { data: modules, isLoading } = useCanvasDataFetching(
 *   ['canvas', 'modules', courseId],
 *   () => CanvasService.getModules(courseId),
 *   {
 *     enabled: !!courseId && !!user?.canvas_tokens,
 *     staleTime: 120000, // 2 minutes
 *   }
 * )
 *
 * // Custom retry configuration for unstable endpoints
 * const { data: assignments } = useCanvasDataFetching(
 *   ['canvas', 'assignments', courseId],
 *   () => CanvasService.getAssignments(courseId),
 *   {
 *     retry: 3,
 *     retryDelay: 2000,
 *     staleTime: 300000, // 5 minutes
 *   }
 * )
 * ```
 */
export function useCanvasDataFetching<T>(
  queryKey: QueryKey,
  queryFn: () => Promise<T>,
  options: UseCanvasDataFetchingOptions = {},
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
