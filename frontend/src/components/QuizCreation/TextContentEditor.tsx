import { Box, Text, Textarea, VStack } from "@chakra-ui/react"
import { memo, useCallback } from "react"

interface TextContentEditorProps {
  /** Current text content value */
  value: string
  /** Callback when text content changes */
  onChange: (value: string) => void
  /** Whether the editor is disabled */
  disabled?: boolean
  /** Error message to display */
  error?: string | null
  /** Placeholder text */
  placeholder?: string
}

/**
 * Text content editor for manual module creation.
 *
 * Features:
 * - Large textarea for content input
 * - Character/word count display
 * - Error handling and validation
 * - Responsive design
 *
 * @example
 * ```tsx
 * <TextContentEditor
 *   value={textContent}
 *   onChange={setTextContent}
 *   placeholder="Paste your course content here..."
 *   error={validationError}
 * />
 * ```
 */
export const TextContentEditor = memo(function TextContentEditor({
  value,
  onChange,
  disabled = false,
  error,
  placeholder = "Paste your course content here..."
}: TextContentEditorProps) {
  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value)
  }, [onChange])

  // Calculate basic stats
  const characterCount = value.length
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0

  return (
    <VStack gap={4} align="stretch">
      <Text fontSize="lg" fontWeight="semibold">
        Enter Text Content
      </Text>

      <Box position="relative">
        <Textarea
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          disabled={disabled}
          resize="vertical"
          minH="300px"
          maxH="500px"
          borderColor={error ? "red.300" : "gray.300"}
          bg={error ? "red.50" : "white"}
          _focus={{
            borderColor: error ? "red.400" : "blue.400",
            boxShadow: error ? "0 0 0 1px red.400" : "0 0 0 1px blue.400"
          }}
          _disabled={{
            opacity: 0.6,
            cursor: "not-allowed"
          }}
        />

        {/* Character/word count in bottom right */}
        <Box
          position="absolute"
          bottom={2}
          right={2}
          bg="white"
          px={2}
          py={1}
          borderRadius="sm"
          border="1px solid"
          borderColor="gray.200"
          fontSize="xs"
          color="gray.600"
        >
          {wordCount} words, {characterCount} characters
        </Box>
      </Box>

      {error && (
        <Box p={3} bg="red.50" border="1px solid" borderColor="red.200" borderRadius="md">
          <Text fontSize="sm" color="red.600">
            {error}
          </Text>
        </Box>
      )}

      <Text fontSize="sm" color="gray.600">
        Enter the content you want to generate questions from. This could be lecture notes,
        course materials, or any educational text content.
      </Text>
    </VStack>
  )
})
