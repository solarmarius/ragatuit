import { Box, Button, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  showRetry?: boolean
}

export const ErrorState = memo(function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  showRetry = true,
}: ErrorStateProps) {
  return (
    <Box textAlign="center" py={12}>
      <VStack gap={4}>
        <Text fontSize="xl" fontWeight="bold" color="red.500">
          {title}
        </Text>
        <Text color="gray.600">{message}</Text>
        {showRetry && onRetry && (
          <Button onClick={onRetry} colorScheme="red" variant="outline" mt={4}>
            Try Again
          </Button>
        )}
      </VStack>
    </Box>
  )
})
