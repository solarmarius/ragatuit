import { Checkbox } from "@/components/ui/checkbox"
import {
  Alert,
  Box,
  Card,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import type React from "react"

import { CanvasService } from "@/client"
import { LoadingSkeleton } from "@/components/common"
import { analyzeCanvasError } from "@/utils"

interface Module {
  id: number
  name: string
}

interface ModuleSelectionStepProps {
  courseId: number
  selectedModules: { [id: number]: string }
  onModulesSelect: (modules: { [id: number]: string }) => void
}

export function ModuleSelectionStep({
  courseId,
  selectedModules,
  onModulesSelect,
}: ModuleSelectionStepProps) {
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

  const handleModuleToggle = (module: Module, checked: boolean) => {
    const newSelectedModules = { ...selectedModules }

    if (checked) {
      newSelectedModules[module.id] = module.name
    } else {
      delete newSelectedModules[module.id]
    }

    onModulesSelect(newSelectedModules)
  }

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

  const selectedModuleIds = Object.keys(selectedModules).map(Number)
  const selectedCount = selectedModuleIds.length

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

      <VStack gap={3} align="stretch">
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
    </VStack>
  )
}
