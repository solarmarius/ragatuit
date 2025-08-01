import { Button, HStack, Input, Text, VStack } from "@chakra-ui/react"
import { memo, useCallback, useState } from "react"

import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import { useCustomToast } from "@/hooks/common"
import { QuizService } from "@/client"
import { ContentPreview } from "./ContentPreview"
import { FileUploadZone } from "./FileUploadZone"
import { TextContentEditor } from "./TextContentEditor"

type DialogStep = "input-method" | "file-upload" | "text-input" | "preview"
type InputMethod = "file" | "text"

interface ManualModuleDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean
  /** Callback when dialog open state changes */
  onOpenChange: (isOpen: boolean) => void
  /** Callback when module is successfully created */
  onModuleCreated: (moduleData: {
    moduleId: string
    name: string
    contentPreview: string
    fullContent: string
    wordCount: number
    processingMetadata?: Record<string, any>
  }) => void
}

/**
 * Main dialog component for manual module creation.
 * Provides a multi-step workflow for uploading files or entering text content.
 *
 * Features:
 * - Multi-step workflow (method selection → content input → preview)
 * - File upload (PDF) and text input support
 * - Immediate content processing with preview
 * - API integration with error handling
 * - Auto-close on successful creation
 *
 * @example
 * ```tsx
 * <ManualModuleDialog
 *   isOpen={isDialogOpen}
 *   onOpenChange={setIsDialogOpen}
 *   onModuleCreated={handleModuleCreated}
 * />
 * ```
 */
export const ManualModuleDialog = memo(function ManualModuleDialog({
  isOpen,
  onOpenChange,
  onModuleCreated,
}: ManualModuleDialogProps) {
  // State management
  const [currentStep, setCurrentStep] = useState<DialogStep>("input-method")
  const [inputMethod, setInputMethod] = useState<InputMethod | null>(null)
  const [moduleName, setModuleName] = useState("")
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [textContent, setTextContent] = useState("")
  const [isProcessing, setIsProcessing] = useState(false)
  const [previewData, setPreviewData] = useState<{
    moduleId: string
    contentPreview: string
    fullContent: string
    wordCount: number
    metadata?: Record<string, any>
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const toast = useCustomToast()

  // Reset dialog state when it closes
  const handleOpenChange = useCallback(
    (open: boolean) => {
      if (!open) {
        setCurrentStep("input-method")
        setInputMethod(null)
        setModuleName("")
        setSelectedFiles([])
        setTextContent("")
        setIsProcessing(false)
        setPreviewData(null)
        setError(null)
      }
      onOpenChange(open)
    },
    [onOpenChange],
  )

  // Handle method selection
  const handleMethodSelection = useCallback((method: InputMethod) => {
    setInputMethod(method)
    setCurrentStep(method === "file" ? "file-upload" : "text-input")
    setError(null)
  }, [])

  // Handle files selection
  const handleFilesSelect = useCallback((files: File[]) => {
    setSelectedFiles(files)
    setError(null)
  }, [])

  // Handle text content change
  const handleTextChange = useCallback((text: string) => {
    setTextContent(text)
    setError(null)
  }, [])

  // Process content and move to preview
  const handleProcessContent = useCallback(async () => {
    if (!moduleName.trim()) {
      setError("Module name is required")
      return
    }

    if (inputMethod === "file" && selectedFiles.length === 0) {
      setError("Please select at least one PDF file")
      return
    }

    if (inputMethod === "text" && !textContent.trim()) {
      setError("Please enter some text content")
      return
    }

    setIsProcessing(true)
    setError(null)

    try {
      // Prepare the form data for the OpenAPI client
      const formData = {
        name: moduleName.trim(),
        text_content: inputMethod === "text" ? textContent.trim() : undefined,
        files: inputMethod === "file" && selectedFiles.length > 0 ? selectedFiles : undefined,
      }

      // Use the generated OpenAPI client with proper authentication
      const result = await QuizService.uploadManualModule({
        formData,
      })

      setPreviewData({
        moduleId: result.module_id,
        contentPreview: result.content_preview,
        fullContent: result.full_content,
        wordCount: result.word_count,
        metadata: result.processing_metadata,
      })

      setCurrentStep("preview")
      toast.showSuccessToast("Content processed successfully!")
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to process content"
      setError(errorMessage)
      toast.showErrorToast(errorMessage)
    } finally {
      setIsProcessing(false)
    }
  }, [moduleName, inputMethod, selectedFiles, textContent, toast])

  // Handle module creation confirmation
  const handleConfirmCreation = useCallback(() => {
    if (previewData) {
      onModuleCreated({
        moduleId: previewData.moduleId,
        name: moduleName,
        contentPreview: previewData.contentPreview,
        fullContent: previewData.fullContent,
        wordCount: previewData.wordCount,
        processingMetadata: previewData.metadata,
      })
      handleOpenChange(false)
    }
  }, [previewData, moduleName, onModuleCreated, handleOpenChange])

  // Handle back navigation
  const handleBack = useCallback(() => {
    switch (currentStep) {
      case "file-upload":
      case "text-input":
        setCurrentStep("input-method")
        setInputMethod(null)
        setSelectedFiles([])
        setTextContent("")
        setError(null)
        break
      case "preview":
        setCurrentStep(inputMethod === "file" ? "file-upload" : "text-input")
        setPreviewData(null)
        setError(null)
        break
    }
  }, [currentStep, inputMethod])

  // Get dialog title based on current step
  const getDialogTitle = () => {
    switch (currentStep) {
      case "input-method":
        return "Add Manual Module"
      case "file-upload":
        return "Upload PDF File"
      case "text-input":
        return "Enter Text Content"
      case "preview":
        return "Review Content"
      default:
        return "Add Manual Module"
    }
  }

  // Check if next/process button should be enabled
  const canProceed = () => {
    if (!moduleName.trim()) return false

    switch (currentStep) {
      case "file-upload":
        return selectedFiles.length > 0
      case "text-input":
        return !!textContent.trim()
      case "preview":
        return !!previewData
      default:
        return false
    }
  }

  return (
    <DialogRoot
      size="lg"
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => handleOpenChange(open)}
    >
      <DialogContent maxW="800px">
        <DialogCloseTrigger />
        <DialogHeader>
          <DialogTitle>{getDialogTitle()}</DialogTitle>
        </DialogHeader>

        <DialogBody>
          <VStack gap={6} align="stretch" minH="400px">
            {/* Module Name Input (always visible except on method selection) */}
            {currentStep !== "input-method" && (
              <VStack gap={2} align="stretch">
                <Text fontSize="sm" fontWeight="medium">
                  Module Name
                </Text>
                <Input
                  value={moduleName}
                  onChange={(e) => setModuleName(e.target.value)}
                  placeholder="Enter a name for this module"
                  disabled={isProcessing}
                />
              </VStack>
            )}

            {/* Step Content */}
            {currentStep === "input-method" && (
              <VStack gap={4} align="stretch">
                <Text fontSize="md" color="gray.600" textAlign="center">
                  How would you like to add content for this module?
                </Text>

                <VStack gap={3}>
                  <Button
                    size="lg"
                    variant="outline"
                    onClick={() => handleMethodSelection("file")}
                    w="full"
                    justifyContent="start"
                  >
                    <HStack gap={3} align="center">
                      <Text fontSize="xl">📄</Text>
                      <VStack align="start" gap={1}>
                        <Text fontWeight="semibold">Upload PDF File</Text>
                        <Text fontSize="sm" color="gray.600">
                          Upload a PDF document (lecture notes, transcripts,
                          etc.)
                        </Text>
                      </VStack>
                    </HStack>
                  </Button>

                  <Button
                    size="lg"
                    variant="outline"
                    onClick={() => handleMethodSelection("text")}
                    w="full"
                    justifyContent="start"
                  >
                    <HStack gap={3} align="center">
                      <Text fontSize="xl">📝</Text>
                      <VStack align="start" gap={1}>
                        <Text fontWeight="semibold">Enter Text Content</Text>
                        <Text fontSize="sm" color="gray.600">
                          Paste or type content directly
                        </Text>
                      </VStack>
                    </HStack>
                  </Button>
                </VStack>
              </VStack>
            )}

            {currentStep === "file-upload" && (
              <FileUploadZone
                onFilesSelect={handleFilesSelect}
                isLoading={isProcessing}
                error={error}
              />
            )}

            {currentStep === "text-input" && (
              <TextContentEditor
                value={textContent}
                onChange={handleTextChange}
                disabled={isProcessing}
                error={error}
              />
            )}

            {currentStep === "preview" && previewData && (
              <ContentPreview
                content={previewData.contentPreview}
                wordCount={previewData.wordCount}
                metadata={previewData.metadata}
                isLoading={isProcessing}
              />
            )}
          </VStack>
        </DialogBody>

        <DialogFooter>
          <HStack gap={3} justify="space-between" w="full">
            <HStack gap={3}>
              {currentStep !== "input-method" && (
                <Button
                  variant="ghost"
                  onClick={handleBack}
                  disabled={isProcessing}
                >
                  Back
                </Button>
              )}
            </HStack>

            <HStack gap={3}>
              <Button
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={isProcessing}
              >
                Cancel
              </Button>

              {currentStep === "preview" ? (
                <Button
                  colorScheme="blue"
                  onClick={handleConfirmCreation}
                  disabled={!previewData}
                >
                  Add Module
                </Button>
              ) : (
                currentStep !== "input-method" && (
                  <Button
                    colorScheme="blue"
                    onClick={handleProcessContent}
                    disabled={!canProceed() || isProcessing}
                    loading={isProcessing}
                    loadingText="Processing..."
                  >
                    Process Content
                  </Button>
                )
              )}
            </HStack>
          </HStack>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  )
})
