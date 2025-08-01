import { Checkbox } from "@/components/ui/checkbox"
import {
  Alert,
  Box,
  Button,
  Card,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import type React from "react"
import { useCallback, useMemo, useState } from "react"

import { CanvasService } from "@/client"
import { LoadingSkeleton } from "@/components/Common"
import { analyzeCanvasError } from "@/lib/utils"
import { ManualModuleDialog } from "./ManualModuleDialog"

interface Module {
  id: number
  name: string
}

interface ManualModule {
  id: string
  name: string
  contentPreview: string
  fullContent: string
  wordCount: number
  processingMetadata?: Record<string, any>
  isManual: true
}

interface ModuleSelectionStepProps {
  courseId: number
  selectedModules: { [id: string]: string }
  manualModules?: ManualModule[]
  onModulesSelect: (modules: { [id: string]: string }) => void
  onManualModuleAdd?: (module: ManualModule) => void
}

export function ModuleSelectionStep({
  courseId,
  selectedModules,
  manualModules = [],
  onModulesSelect,
  onManualModuleAdd,
}: ModuleSelectionStepProps) {
  const [isManualDialogOpen, setIsManualDialogOpen] = useState(false)
  // Show message if no course is selected
  if (!courseId || courseId <= 0) {
    return (
      <Alert.Root status="warning">
        <Alert.Indicator />
        <Alert.Title>No course selected</Alert.Title>
        <Alert.Description>
          Please go back to the previous step and select a course first.
        </Alert.Description>
      </Alert.Root>
    )
  }

  const {
    data: modules,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["canvas-modules", courseId],
    queryFn: () => CanvasService.getCourseModules({ courseId }),
    retry: 1,
    retryDelay: 1000,
    staleTime: 30000,
    enabled: !!courseId && courseId > 0,
  })

  const handleModuleToggle = useCallback(
    (module: Module | ManualModule, checked: boolean) => {
      const newSelectedModules = { ...selectedModules }
      const moduleId = String(module.id)

      if (checked) {
        newSelectedModules[moduleId] = module.name
      } else {
        delete newSelectedModules[moduleId]
      }

      onModulesSelect(newSelectedModules)
    },
    [selectedModules, onModulesSelect],
  )

  const handleManualModuleCreated = useCallback(
    (moduleData: {
      moduleId: string
      name: string
      contentPreview: string
      fullContent: string
      wordCount: number
      processingMetadata?: Record<string, any>
    }) => {
      const manualModule: ManualModule = {
        id: moduleData.moduleId,
        name: moduleData.name,
        contentPreview: moduleData.contentPreview,
        fullContent: moduleData.fullContent,
        wordCount: moduleData.wordCount,
        processingMetadata: moduleData.processingMetadata,
        isManual: true,
      }

      // Add the manual module to the list
      onManualModuleAdd?.(manualModule)

      // Automatically select the new manual module
      const newSelectedModules = { ...selectedModules }
      newSelectedModules[moduleData.moduleId] = moduleData.name
      onModulesSelect(newSelectedModules)
    },
    [selectedModules, onModulesSelect, onManualModuleAdd],
  )

  const selectedCount = useMemo(
    () => Object.keys(selectedModules).length,
    [selectedModules],
  )

  if (isLoading) {
    return (
      <VStack gap={4} align="stretch">
        <Text fontSize="lg" fontWeight="semibold">
          Loading course modules...
        </Text>
        <LoadingSkeleton height="60px" lines={4} />
      </VStack>
    )
  }

  if (error) {
    const errorInfo = analyzeCanvasError(error)

    return (
      <Alert.Root status="error">
        <Alert.Indicator />
        <Alert.Title>Failed to load course modules</Alert.Title>
        <Alert.Description>
          <Text mb={2}>{errorInfo.userFriendlyMessage}</Text>
          <Text fontSize="sm" color="gray.600">
            {errorInfo.actionableGuidance}
          </Text>
        </Alert.Description>
      </Alert.Root>
    )
  }

  if (!modules || modules.length === 0) {
    return (
      <Alert.Root status="info">
        <Alert.Indicator />
        <Alert.Title>No modules found</Alert.Title>
        <Alert.Description>
          This course doesn't have any modules yet. Please add some content to
          the course in Canvas before generating a quiz.
        </Alert.Description>
      </Alert.Root>
    )
  }

  return (
    <VStack gap={4} align="stretch">
      <Box>
        <Text fontSize="lg" fontWeight="semibold" mb={2}>
          Select modules to include in the quiz
        </Text>
        <Text color="gray.600" fontSize="sm">
          Choose which course modules you want to generate quiz questions from.
          You can select multiple modules.
        </Text>
        <Text color="gray.600" fontSize="sm">
          For instance, you can skip including modules with administrative
          details.
        </Text>
      </Box>

      {/* Manual Module Creation Card */}
      <Card.Root
        variant="outline"
        cursor="pointer"
        _hover={{ borderColor: "green.300" }}
        borderColor="green.200"
        bg="green.50"
        onClick={() => setIsManualDialogOpen(true)}
        data-testid="add-manual-module-card"
      >
        <Card.Body p={4}>
          <HStack gap={3}>
            <Box fontSize="xl">➕</Box>
            <Box flex={1}>
              <Text fontWeight="medium" fontSize="md" color="green.700">
                Add Manual Module
              </Text>
              <Text fontSize="sm" color="green.600" mt={1}>
                Upload PDF files or paste text content to create a custom module
              </Text>
            </Box>
            <Button
              size="sm"
              colorScheme="green"
              variant="outline"
              onClick={(e) => {
                e.stopPropagation()
                setIsManualDialogOpen(true)
              }}
            >
              Add Module
            </Button>
          </HStack>
        </Card.Body>
      </Card.Root>

      <VStack gap={3} align="stretch">
        {/* Canvas Modules */}
        {modules.map((module) => (
          <Card.Root
            key={module.id}
            variant="outline"
            cursor="pointer"
            _hover={{ borderColor: "blue.300" }}
            borderColor={selectedModules[module.id] ? "blue.500" : "gray.200"}
            bg={selectedModules[module.id] ? "blue.50" : "white"}
            onClick={() => {
              handleModuleToggle(module, !selectedModules[module.id])
            }}
            data-testid={`module-card-${module.id}`}
          >
            <Card.Body p={4}>
              <HStack gap={3}>
                <Checkbox
                  checked={!!selectedModules[module.id]}
                  inputProps={{
                    onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
                      handleModuleToggle(module, e.target.checked),
                    onClick: (e: React.MouseEvent) => e.stopPropagation(),
                  }}
                />
                <Box flex={1}>
                  <Text fontWeight="medium" fontSize="md" lineClamp={2}>
                    {module.name || "Unnamed Module"}
                  </Text>
                </Box>
              </HStack>
            </Card.Body>
          </Card.Root>
        ))}

        {/* Manual Modules */}
        {manualModules.map((module) => (
          <Card.Root
            key={module.id}
            variant="outline"
            cursor="pointer"
            _hover={{ borderColor: "blue.300" }}
            borderColor={selectedModules[module.id] ? "blue.500" : "gray.200"}
            bg={selectedModules[module.id] ? "blue.50" : "white"}
            onClick={() => {
              handleModuleToggle(module, !selectedModules[module.id])
            }}
            data-testid={`manual-module-card-${module.id}`}
          >
            <Card.Body p={4}>
              <HStack gap={3}>
                <Checkbox
                  checked={!!selectedModules[module.id]}
                  inputProps={{
                    onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
                      handleModuleToggle(module, e.target.checked),
                    onClick: (e: React.MouseEvent) => e.stopPropagation(),
                  }}
                />
                <Box flex={1}>
                  <HStack gap={2} align="center">
                    <Text fontWeight="medium" fontSize="md" lineClamp={2}>
                      {module.name || "Unnamed Module"}
                    </Text>
                    <Box
                      px={2}
                      py={1}
                      bg="purple.100"
                      color="purple.800"
                      fontSize="xs"
                      fontWeight="medium"
                      borderRadius="md"
                    >
                      Manual
                    </Box>
                  </HStack>
                  <Text fontSize="sm" color="gray.600" mt={1}>
                    {module.wordCount.toLocaleString()} words
                  </Text>
                </Box>
              </HStack>
            </Card.Body>
          </Card.Root>
        ))}
      </VStack>

      {selectedCount > 0 && (
        <Alert.Root status="success">
          <Alert.Indicator />
          <Alert.Description>
            Selected {selectedCount} module{selectedCount === 1 ? "" : "s"} for
            quiz generation
          </Alert.Description>
        </Alert.Root>
      )}

      {/* Manual Module Dialog */}
      <ManualModuleDialog
        isOpen={isManualDialogOpen}
        onOpenChange={setIsManualDialogOpen}
        onModuleCreated={handleManualModuleCreated}
      />
    </VStack>
  )
}
