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
      <ErrorState title="Editor Error" message={error} showRetry={false} />
      <HStack gap={3} justify="end">
        <Button variant="outline" onClick={onCancel}>
          Close
        </Button>
      </HStack>
    </>
  )
})
