import { useMemo } from "react"

type DateFormat = "default" | "short" | "long" | "time-only"

const formatOptions: Record<DateFormat, Intl.DateTimeFormatOptions> = {
  default: {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  },
  short: {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  },
  long: {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  },
  "time-only": {
    hour: "2-digit",
    minute: "2-digit",
  },
}

/**
 * Hook for consistent date formatting across the application.
 * Uses en-GB locale by default for consistency. Provides memoized
 * date formatting with multiple predefined formats and safe error handling.
 *
 * @param date - The date to format (string, Date object, or null/undefined)
 * @param format - The format type to use (default: "default")
 * @param locale - The locale to use for formatting (default: "en-GB")
 *
 * @returns Formatted date string or null if date is invalid/empty
 *
 * @example
 * ```tsx
 * // Basic usage with default format
 * const formattedDate = useFormattedDate(quiz.created_at)
 * // Result: "12 January 2024, 14:30"
 *
 * // Using different formats
 * const shortDate = useFormattedDate(quiz.created_at, "short")
 * // Result: "12 Jan 2024, 14:30"
 *
 * const longDate = useFormattedDate(quiz.created_at, "long")
 * // Result: "12 January 2024, 14:30:45"
 *
 * const timeOnly = useFormattedDate(quiz.created_at, "time-only")
 * // Result: "14:30"
 *
 * // Using custom locale
 * const usDate = useFormattedDate(quiz.created_at, "default", "en-US")
 * // Result: "January 12, 2024, 02:30 PM"
 *
 * // Safe handling of null/undefined dates
 * const safeDate = useFormattedDate(null) // Returns null
 * const invalidDate = useFormattedDate("invalid-date") // Returns null
 *
 * // Usage in components
 * return (
 *   <div>
 *     <p>Created: {useFormattedDate(quiz.created_at)}</p>
 *     <p>Updated: {useFormattedDate(quiz.updated_at, "short")}</p>
 *     <p>Time: {useFormattedDate(quiz.created_at, "time-only")}</p>
 *   </div>
 * )
 * ```
 */
export function useFormattedDate(
  date: string | Date | null | undefined,
  format: DateFormat = "default",
  locale = "en-GB",
): string | null {
  return useMemo(() => {
    if (!date) return null

    try {
      const dateObj = typeof date === "string" ? new Date(date) : date

      if (Number.isNaN(dateObj.getTime())) {
        return null
      }

      return dateObj.toLocaleDateString(locale, formatOptions[format])
    } catch {
      return null
    }
  }, [date, format, locale])
}
