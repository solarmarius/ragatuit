import { useMemo } from 'react'

type DateFormat = 'default' | 'short' | 'long' | 'time-only'

const formatOptions: Record<DateFormat, Intl.DateTimeFormatOptions> = {
  default: {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  },
  short: {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  },
  long: {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  },
  'time-only': {
    hour: '2-digit',
    minute: '2-digit',
  },
}

/**
 * Hook for consistent date formatting across the application.
 * Uses en-GB locale by default for consistency.
 */
export function useFormattedDate(
  date: string | Date | null | undefined,
  format: DateFormat = 'default',
  locale: string = 'en-GB'
): string | null {
  return useMemo(() => {
    if (!date) return null

    try {
      const dateObj = typeof date === 'string' ? new Date(date) : date

      if (isNaN(dateObj.getTime())) {
        return null
      }

      return dateObj.toLocaleDateString(locale, formatOptions[format])
    } catch {
      return null
    }
  }, [date, format, locale])
}
