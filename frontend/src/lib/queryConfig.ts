/**
 * Centralized React Query configuration for different data types.
 * Provides optimized caching strategies based on data volatility and usage patterns.
 */

import type { UseQueryOptions } from "@tanstack/react-query"

/**
 * Query options for quiz data.
 * Quiz data changes infrequently, so we cache aggressively.
 */
export const quizQueryConfig = {
  staleTime: 10 * 60 * 1000, // 10 minutes - quiz data is relatively stable
  gcTime: 30 * 60 * 1000, // 30 minutes - keep in memory longer
  refetchOnWindowFocus: false,
} as const

/**
 * Query options for questions data.
 * Questions can be edited/approved, so shorter cache time but still optimized.
 */
export const questionsQueryConfig = {
  staleTime: 3 * 60 * 1000, // 3 minutes - questions can be modified frequently
  gcTime: 15 * 60 * 1000, // 15 minutes
  refetchOnWindowFocus: false,
} as const

/**
 * Query options for question statistics.
 * Stats need to be relatively fresh but can be cached briefly.
 */
export const questionStatsQueryConfig = {
  staleTime: 2 * 60 * 1000, // 2 minutes - stats should be fairly current
  gcTime: 10 * 60 * 1000, // 10 minutes
  refetchOnWindowFocus: false,
} as const

/**
 * Query options for data that should be fetched fresh every time.
 * Used for critical real-time data that changes frequently.
 */
export const freshDataQueryConfig = {
  staleTime: 0, // Always consider stale
  gcTime: 5 * 60 * 1000, // 5 minutes - minimal caching
  refetchOnWindowFocus: true,
} as const

/**
 * Creates a query configuration with optional polling.
 * Useful for quiz status monitoring with intelligent polling.
 */
export function createPollingQueryConfig<T>(
  baseConfig: UseQueryOptions<T>,
  pollingFn?: (query: { state: { data?: T } }) => number | false,
): UseQueryOptions<T> {
  return {
    ...baseConfig,
    refetchInterval: pollingFn,
    refetchIntervalInBackground: false,
  }
}

/**
 * Query keys factory for consistent cache management.
 * Provides standardized query keys across the application.
 */
export const queryKeys = {
  // Quiz-related keys
  quiz: (id: string) => ["quiz", id] as const,
  quizQuestions: (id: string) => ["quiz", id, "questions"] as const,
  quizQuestionStats: (id: string) =>
    ["quiz", id, "questions", "stats"] as const,

  // User-related keys
  user: () => ["user"] as const,
  userQuizzes: () => ["user", "quizzes"] as const,

  // Canvas-related keys
  canvasCourses: () => ["canvas", "courses"] as const,
  canvasCourse: (id: string) => ["canvas", "course", id] as const,
} as const

/**
 * Utility function to invalidate related queries after mutations.
 * Ensures cache consistency when data changes.
 */
export function getRelatedQueryKeys(quizId: string) {
  return [
    queryKeys.quiz(quizId),
    queryKeys.quizQuestions(quizId),
    queryKeys.quizQuestionStats(quizId),
  ]
}
