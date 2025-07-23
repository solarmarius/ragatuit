/**
 * Utility functions for parsing and validating Fill-in-the-Blank question text
 * and blank configurations to ensure synchronization and proper formatting.
 */

// Regular expression to match [blank_N] tags (lowercase, numeric only)
const BLANK_TAG_REGEX = /\[blank_(\d+)\]/g
const SINGLE_BLANK_TAG_REGEX = /^\[blank_(\d+)\]$/

/**
 * Extracts all [blank_N] tags from question text
 * @param questionText - The question text to parse
 * @returns Array of matched blank tag strings
 */
export function parseBlankTags(questionText: string): string[] {
  if (!questionText) return []

  const matches = questionText.match(BLANK_TAG_REGEX)
  return matches || []
}

/**
 * Validates if a single tag matches the correct [blank_N] format
 * @param tag - The tag to validate (e.g., "[blank_1]")
 * @returns true if valid format, false otherwise
 */
export function validateBlankTagFormat(tag: string): boolean {
  return SINGLE_BLANK_TAG_REGEX.test(tag)
}

/**
 * Extracts position numbers from all [blank_N] tags in question text
 * @param questionText - The question text to parse
 * @returns Sorted array of position numbers
 */
export function getBlankPositions(questionText: string): number[] {
  if (!questionText) return []

  const tags = parseBlankTags(questionText)
  const positions: number[] = []

  tags.forEach((tag) => {
    const match = tag.match(/\[blank_(\d+)\]/)
    if (match) {
      const position = Number.parseInt(match[1], 10)
      positions.push(position)
    }
  })

  // Sort positions and return unique values
  return [...new Set(positions)].sort((a, b) => a - b)
}

/**
 * Validates that positions are sequential starting from 1 (no gaps)
 * @param positions - Array of position numbers
 * @returns true if sequential, false if gaps exist
 */
export function validateSequentialPositions(positions: number[]): boolean {
  if (positions.length === 0) return true

  // Check if positions start from 1 and are sequential
  for (let i = 0; i < positions.length; i++) {
    if (positions[i] !== i + 1) {
      return false
    }
  }

  return true
}

/**
 * Finds duplicate positions in question text
 * @param questionText - The question text to analyze
 * @returns Array of position numbers that appear multiple times
 */
export function findDuplicatePositions(questionText: string): number[] {
  if (!questionText) return []

  const tags = parseBlankTags(questionText)
  const positionCounts: Record<number, number> = {}

  tags.forEach((tag) => {
    const match = tag.match(/\[blank_(\d+)\]/)
    if (match) {
      const position = Number.parseInt(match[1], 10)
      positionCounts[position] = (positionCounts[position] || 0) + 1
    }
  })

  return Object.entries(positionCounts)
    .filter(([_, count]) => count > 1)
    .map(([position, _]) => Number.parseInt(position, 10))
    .sort((a, b) => a - b)
}

/**
 * Finds all invalid blank tag formats in question text
 * @param questionText - The question text to analyze
 * @returns Array of invalid tag strings
 */
export function findInvalidBlankTags(questionText: string): string[] {
  if (!questionText) return []

  // Find all potential blank-like patterns
  const potentialTags = questionText.match(/\[blank_[^\]]*\]/gi) || []

  return potentialTags.filter((tag) => !validateBlankTagFormat(tag))
}

/**
 * Gets the positions that exist in question text but are missing from blank configurations
 * @param questionText - The question text
 * @param configuredPositions - Array of positions from blank configurations
 * @returns Array of missing position numbers
 */
export function getMissingBlankConfigurations(
  questionText: string,
  configuredPositions: number[],
): number[] {
  const textPositions = getBlankPositions(questionText)
  return textPositions.filter((pos) => !configuredPositions.includes(pos))
}

/**
 * Gets the positions that exist in blank configurations but are missing from question text
 * @param questionText - The question text
 * @param configuredPositions - Array of positions from blank configurations
 * @returns Array of extra position numbers
 */
export function getExtraBlankConfigurations(
  questionText: string,
  configuredPositions: number[],
): number[] {
  const textPositions = getBlankPositions(questionText)
  return configuredPositions.filter((pos) => !textPositions.includes(pos))
}

/**
 * Calculates the next sequential position for adding a new blank
 * @param questionText - The current question text
 * @returns The next position number to use
 */
export function getNextBlankPosition(questionText: string): number {
  const positions = getBlankPositions(questionText)
  if (positions.length === 0) return 1

  // Return the next sequential number
  return Math.max(...positions) + 1
}

/**
 * Checks if question text and blank configurations are synchronized
 * @param questionText - The question text
 * @param configuredPositions - Array of positions from blank configurations
 * @returns true if synchronized, false otherwise
 */
export function areBlanksSynchronized(
  questionText: string,
  configuredPositions: number[],
): boolean {
  const textPositions = getBlankPositions(questionText)

  // Check if arrays have same length and same elements
  if (textPositions.length !== configuredPositions.length) return false

  const sortedTextPositions = [...textPositions].sort((a, b) => a - b)
  const sortedConfigPositions = [...configuredPositions].sort((a, b) => a - b)

  return sortedTextPositions.every(
    (pos, index) => pos === sortedConfigPositions[index],
  )
}
