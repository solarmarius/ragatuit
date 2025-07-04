export function formatDate(date: string | Date, locale = 'en-GB'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date

  if (isNaN(dateObj.getTime())) {
    return 'Invalid date'
  }

  return dateObj.toLocaleDateString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(date: string | Date, locale = 'en-GB'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date

  if (isNaN(dateObj.getTime())) {
    return 'Invalid date'
  }

  return dateObj.toLocaleString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTimeAgo(timestamp: string): string {
  try {
    // Ensure the timestamp is treated as UTC if it doesn't have timezone info
    let normalizedTimestamp = timestamp
    if (
      !timestamp.includes('Z') &&
      !timestamp.includes('+') &&
      !timestamp.includes('-', 10)
    ) {
      normalizedTimestamp = `${timestamp}Z`
    }

    const date = new Date(normalizedTimestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))

    if (diffMins < 1) return 'just now'
    if (diffMins < 60)
      return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`

    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24)
      return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`

    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`
  } catch {
    return ''
  }
}
