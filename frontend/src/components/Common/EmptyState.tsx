import { Box, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"
import type { ReactNode } from "react"

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
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
