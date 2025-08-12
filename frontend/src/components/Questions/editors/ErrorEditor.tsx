import { ErrorState } from "@/components/Common"
import { Button, HStack } from "@chakra-ui/react"
import { memo } from "react"

interface ErrorEditorProps {
  error: string
  onCancel: () => void
}

export const ErrorEditor = memo(function ErrorEditor({
  error,
  onCancel,
}: ErrorEditorProps) {
  return (
    <>
      <ErrorState
        title="Editor Error"
        message={error}
        showRetry={false}
        variant="inline"
      />
      <HStack gap={3} justify="end" mt={4}>
        <Button variant="outline" onClick={onCancel}>
          Close
        </Button>
      </HStack>
    </>
  )
})
