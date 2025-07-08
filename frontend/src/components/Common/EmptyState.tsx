import { Box, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"
import type { ReactNode } from "react"

/**
 * Props for the EmptyState component.
 * Displays a centered empty state with optional icon, description, and action button.
 *
 * @example
 * ```tsx
 * // Basic empty state
 * <EmptyState title="No quizzes found" />
 *
 * // Empty state with description
 * <EmptyState
 *   title="No questions available"
 *   description="Create your first quiz to get started"
 * />
 *
 * // Empty state with icon and action
 * <EmptyState
 *   title="No courses selected"
 *   description="Select a course to view available modules"
 *   icon={<BookIcon size={48} />}
 *   action={
 *     <Button onClick={handleSelectCourse}>
 *       Select Course
 *     </Button>
 *   }
 * />
 *
 * // Empty state for loading scenarios
 * <EmptyState
 *   title="Loading your quizzes..."
 *   icon={<Spinner size="xl" />}
 * />
 * ```
 */
interface EmptyStateProps {
  /** Main title text to display */
  title: string
  /** Optional description text below the title */
  description?: string
  /** Optional icon or visual element to display above the title */
  icon?: ReactNode
  /** Optional action button or element to display below the description */
  action?: ReactNode
}

export const EmptyState = memo(function EmptyState({
  title,
  description,
  icon,
  action,
}: EmptyStateProps) {
  return (
    <Box textAlign="center" py={12}>
      <VStack gap={4}>
        {icon && <Box>{icon}</Box>}
        <Text fontSize="lg" fontWeight="semibold" color="gray.600">
          {title}
        </Text>
        {description && <Text color="gray.500">{description}</Text>}
        {action && <Box mt={4}>{action}</Box>}
      </VStack>
    </Box>
  )
})
