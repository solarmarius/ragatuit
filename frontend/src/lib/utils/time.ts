/**
 * Date and time utility functions
 */

/**
 * Safely parse a date string or Date object
 */
function parseDate(date: string | Date): Date {
  return typeof date === "string" ? new Date(date) : date
}

/**
 * Check if a date is valid
 */
function isValidDate(date: Date): boolean {
  return !Number.isNaN(date.getTime())
}

/**
 * Format a date as a localized date string
 */
export function formatDate(date: string | Date, locale = "en-GB"): string {
  const dateObj = parseDate(date)

  if (!isValidDate(dateObj)) {
    return "Invalid date"
  }

  return dateObj.toLocaleDateString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

/**
 * Format a date as a localized date and time string
 */
export function formatDateTime(date: string | Date, locale = "en-GB"): string {
  const dateObj = parseDate(date)

  if (!isValidDate(dateObj)) {
    return "Invalid date"
  }

  return dateObj.toLocaleString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

/**
 * Format a timestamp as a relative time string (e.g., "2 hours ago")
 */
export function formatTimeAgo(timestamp: string): string {
  try {
    // Ensure the timestamp is treated as UTC if it doesn't have timezone info
    let normalizedTimestamp = timestamp
    if (
      !timestamp.includes("Z") &&
      !timestamp.includes("+") &&
      !timestamp.includes("-", 10)
    ) {
      normalizedTimestamp = `${timestamp}Z`
    }

    const date = new Date(normalizedTimestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))

    if (diffMins < 1) return "just now"
    if (diffMins < 60) {
      return `${diffMins} minute${diffMins === 1 ? "" : "s"} ago`
    }

    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) {
      return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`
    }

    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`
  } catch {
    return ""
  }
}

/**
 * Get the current timestamp as an ISO string
 */
export function getCurrentTimestamp(): string {
  return new Date().toISOString()
}

/**
 * Check if a date is today
 */
export function isToday(date: string | Date): boolean {
  const dateObj = parseDate(date)
  if (!isValidDate(dateObj)) return false

  const today = new Date()
  return (
    dateObj.getDate() === today.getDate() &&
    dateObj.getMonth() === today.getMonth() &&
    dateObj.getFullYear() === today.getFullYear()
  )
}
