import { Button, HStack } from "@chakra-ui/react"
import { memo } from "react"

interface UnsupportedEditorProps {
  questionType: string
  onCancel: () => void
}

export const UnsupportedEditor = memo(function UnsupportedEditor({
  questionType,
  onCancel,
}: UnsupportedEditorProps) {
  return (
    <>
      <div
        style={{
          padding: "16px",
          backgroundColor: "#fed7d7",
          borderRadius: "8px",
          borderLeft: "4px solid #f56565",
        }}
      >
        <p style={{ fontWeight: "600", color: "#c53030", marginBottom: "4px" }}>
          Unsupported Question Type
        </p>
        <p style={{ fontSize: "14px", color: "#9c4221" }}>
          Editing for question type "{questionType}" is not yet supported.
        </p>
      </div>

      <HStack gap={3} justify="end">
        <Button variant="outline" onClick={onCancel}>
          Close
        </Button>
      </HStack>
    </>
  )
})
