import { Box, Button, Text, VStack } from "@chakra-ui/react"
import type { ErrorInfo, ReactNode } from "react"
import { ErrorBoundary as ReactErrorBoundary } from "react-error-boundary"

interface ErrorFallbackProps {
  error: Error
  resetErrorBoundary: () => void
}

function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  return (
    <Box
      role="alert"
      p={6}
      bg="red.50"
      borderRadius="md"
      border="1px solid"
      borderColor="red.200"
    >
      <VStack gap={4} align="start">
        <Text fontSize="lg" fontWeight="bold" color="red.700">
          Something went wrong
        </Text>
        <Text color="red.600" fontSize="sm">
          {error.message}
        </Text>
        <Button
          onClick={resetErrorBoundary}
          colorScheme="red"
          size="sm"
          variant="outline"
        >
          Try again
        </Button>
      </VStack>
    </Box>
  )
}

interface ErrorBoundaryProps {
  children: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

export function ErrorBoundary({ children, onError }: ErrorBoundaryProps) {
  return (
    <ReactErrorBoundary FallbackComponent={ErrorFallback} onError={onError}>
      {children}
    </ReactErrorBoundary>
  )
}
