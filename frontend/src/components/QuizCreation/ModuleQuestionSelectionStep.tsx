import {
  Alert,
  Box,
  Button,
  Card,
  HStack,
  Heading,
  Input,
  Text,
  VStack,
} from "@chakra-ui/react"
import type React from "react"
import { useMemo } from "react"

interface ModuleQuestionSelectionStepProps {
  selectedModules: Record<string, string>
  moduleQuestions: Record<string, number>
  onModuleQuestionChange: (moduleId: string, count: number) => void
}

export const ModuleQuestionSelectionStep: React.FC<
  ModuleQuestionSelectionStepProps
> = ({ selectedModules, moduleQuestions, onModuleQuestionChange }) => {
  const totalQuestions = useMemo(() => {
    return Object.values(moduleQuestions).reduce((sum, count) => sum + count, 0)
  }, [moduleQuestions])

  const moduleIds = Object.keys(selectedModules)

  const handleQuestionCountChange = (moduleId: string, value: string) => {
    const numValue = Number.parseInt(value, 10)
    if (!Number.isNaN(numValue) && numValue >= 1 && numValue <= 20) {
      onModuleQuestionChange(moduleId, numValue)
    }
  }

  const incrementCount = (moduleId: string) => {
    const current = moduleQuestions[moduleId] || 10
    if (current < 20) {
      onModuleQuestionChange(moduleId, current + 1)
    }
  }

  const decrementCount = (moduleId: string) => {
    const current = moduleQuestions[moduleId] || 10
    if (current > 1) {
      onModuleQuestionChange(moduleId, current - 1)
    }
  }

  return (
    <Box>
      <VStack gap={6} align="stretch">
        <Box>
          <Heading size="md" mb={2}>
            Set Questions per Module
          </Heading>
          <Text color="gray.600">
            Specify how many questions you want to generate from each module
            (1-20 per module).
          </Text>
        </Box>

        <Card.Root
          variant="elevated"
          bg="blue.50"
          borderColor="blue.200"
          borderWidth={1}
        >
          <Card.Body>
            <Box textAlign="center">
              <Text fontSize="sm" color="gray.600" mb={1}>
                Total Questions
              </Text>
              <Text fontSize="3xl" fontWeight="bold" color="blue.600">
                {totalQuestions}
              </Text>
              <Text fontSize="sm" color="gray.500">
                Across {moduleIds.length} modules
              </Text>
            </Box>
          </Card.Body>
        </Card.Root>

        {totalQuestions > 500 && (
          <Alert.Root status="warning">
            <Alert.Indicator />
            <Alert.Title>Large Question Count</Alert.Title>
            <Alert.Description>
              Large number of questions may take longer to generate.
            </Alert.Description>
          </Alert.Root>
        )}

        <VStack gap={4} align="stretch">
          {moduleIds.map((moduleId) => (
            <Card.Root key={moduleId} variant="outline">
              <Card.Body>
                <HStack justify="space-between" align="center">
                  <Box flex={1}>
                    <Text fontWeight="medium" fontSize="md">
                      {selectedModules[moduleId]}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      Module ID: {moduleId}
                    </Text>
                  </Box>

                  <HStack gap={4}>
                    <Text fontSize="sm" color="gray.600">
                      Questions:
                    </Text>
                    <HStack>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => decrementCount(moduleId)}
                        disabled={(moduleQuestions[moduleId] || 10) <= 1}
                      >
                        -
                      </Button>
                      <Input
                        type="number"
                        min={1}
                        max={20}
                        width="60px"
                        textAlign="center"
                        value={moduleQuestions[moduleId] || 10}
                        onChange={(e) =>
                          handleQuestionCountChange(moduleId, e.target.value)
                        }
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => incrementCount(moduleId)}
                        disabled={(moduleQuestions[moduleId] || 10) >= 20}
                      >
                        +
                      </Button>
                    </HStack>
                  </HStack>
                </HStack>
              </Card.Body>
            </Card.Root>
          ))}
        </VStack>

        <Box mt={4}>
          <Text fontSize="sm" color="gray.600">
            <strong>Tip:</strong> Allocate more questions to modules with more
            content or higher importance. The AI will generate diverse questions
            covering different topics within each module.
          </Text>
        </Box>
      </VStack>
    </Box>
  )
}
