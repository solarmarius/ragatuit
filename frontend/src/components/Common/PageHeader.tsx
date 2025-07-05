import { Box, HStack, Text } from "@chakra-ui/react"
import { memo } from "react"
import type { ReactNode } from "react"

interface PageHeaderProps {
  title: string
  description?: string
  action?: ReactNode
}

export const PageHeader = memo(function PageHeader({
  title,
  description,
  action,
}: PageHeaderProps) {
  return (
    <HStack justify="space-between" align="center">
      <Box>
        <Text fontSize="3xl" fontWeight="bold">
          {title}
        </Text>
        {description && <Text color="gray.600">{description}</Text>}
      </Box>
      {action && <Box>{action}</Box>}
    </HStack>
  )
})
