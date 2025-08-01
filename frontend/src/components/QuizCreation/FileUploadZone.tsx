import { Box, Button, FileUpload, Text, VStack } from "@chakra-ui/react"
import { memo, useCallback, useState } from "react"
import { HiUpload } from "react-icons/hi"

interface FileUploadZoneProps {
  /** Callback when file is selected */
  onFileSelect: (file: File | null) => void
  /** Whether the upload is in progress */
  isLoading?: boolean
  /** Error message to display */
  error?: string | null
}

/**
 * File upload zone for PDF files with drag & drop support.
 *
 * Features:
 * - Drag & drop file upload
 * - PDF file validation (5MB limit)
 * - Visual feedback for drag states
 * - Error handling and validation
 *
 * @example
 * ```tsx
 * <FileUploadZone
 *   onFileSelect={handleFileSelect}
 *   isLoading={isProcessing}
 *   error={uploadError}
 * />
 * ```
 */
export const FileUploadZone = memo(function FileUploadZone({
  onFileSelect,
  isLoading = false,
  error
}: FileUploadZoneProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const validateFile = useCallback((file: File): string | null => {
    // Check file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return "Only PDF files are supported"
    }

    // Check file size (5MB limit)
    const maxSize = 5 * 1024 * 1024 // 5MB
    if (file.size > maxSize) {
      return "File size must be less than 5MB"
    }

    return null
  }, [])

  const handleFileChange = useCallback((details: { acceptedFiles: File[] }) => {
    const file = details.acceptedFiles[0]

    if (!file) {
      setSelectedFile(null)
      onFileSelect(null)
      return
    }

    const validationError = validateFile(file)
    if (validationError) {
      // Handle validation error - for now we'll just not select the file
      // In a more complete implementation, you might want to show the error
      setSelectedFile(null)
      onFileSelect(null)
      return
    }

    setSelectedFile(file)
    onFileSelect(file)
  }, [onFileSelect, validateFile])

  return (
    <VStack gap={4} align="stretch">
      <Text fontSize="lg" fontWeight="semibold">
        Upload PDF File
      </Text>

      <FileUpload.Root
        accept="application/pdf,.pdf"
        maxFiles={1}
        maxFileSize={5 * 1024 * 1024} // 5MB
        onFileChange={handleFileChange}
        disabled={isLoading}
      >
        <FileUpload.HiddenInput />

        <FileUpload.Trigger asChild>
          <Box
            p={8}
            border="2px dashed"
            borderColor={error ? "red.300" : "gray.300"}
            borderRadius="lg"
            bg={error ? "red.50" : "gray.50"}
            cursor={isLoading ? "not-allowed" : "pointer"}
            opacity={isLoading ? 0.6 : 1}
            transition="all 0.2s"
            _hover={!isLoading ? {
              borderColor: "blue.400",
              bg: "blue.50"
            } : {}}
            textAlign="center"
          >
            <VStack gap={3}>
              <Box fontSize="3xl" color="gray.400">
                📄
              </Box>
              <VStack gap={1}>
                <Text fontSize="md" fontWeight="medium" color="gray.700">
                  {isLoading ? "Processing..." : "Click to upload or drag and drop"}
                </Text>
                <Text fontSize="sm" color="gray.500">
                  PDF files only, up to 5MB
                </Text>
              </VStack>
              <Button
                variant="outline"
                size="sm"
                disabled={isLoading}
              >
                <HiUpload /> Choose File
              </Button>
            </VStack>
          </Box>
        </FileUpload.Trigger>

        {/* File list will be handled by our custom selectedFile display */}
      </FileUpload.Root>

      {error && (
        <Box p={3} bg="red.50" border="1px solid" borderColor="red.200" borderRadius="md">
          <Text fontSize="sm" color="red.600">
            {error}
          </Text>
        </Box>
      )}

      {selectedFile && (
        <Box p={3} bg="green.50" border="1px solid" borderColor="green.200" borderRadius="md">
          <Text fontSize="sm" color="green.700">
            Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
          </Text>
        </Box>
      )}
    </VStack>
  )
})
