import { Field } from "@/components/ui/field"
import {
  Alert,
  Box,
  Button,
  Card,
  HStack,
  Heading,
  Input,
  Select,
  Text,
  VStack,
  createListCollection,
} from "@chakra-ui/react"
import type React from "react"
import { useMemo, useState } from "react"
import { IoAdd, IoClose } from "react-icons/io5"

import type { QuestionBatch, QuestionDifficulty, QuestionType } from "@/client"
import {
  QUESTION_BATCH_DEFAULTS,
  QUESTION_DIFFICULTIES,
  QUESTION_DIFFICULTY_LABELS,
  VALIDATION_MESSAGES,
  VALIDATION_RULES,
} from "@/lib/constants"
import {
  calculateModuleQuestions,
  calculateTotalQuestionsFromBatches,
  validateModuleBatches,
} from "@/lib/utils"

interface ModuleQuestionSelectionStepProps {
  selectedModules: Record<string, string>
  moduleQuestions: Record<string, QuestionBatch[]>
  onModuleQuestionChange: (moduleId: string, batches: QuestionBatch[]) => void
}

// Question type options collection for Chakra UI Select
const questionTypeCollection = createListCollection({
  items: [
    {
      value: "multiple_choice" as QuestionType,
      label: "Multiple Choice",
    },
    {
      value: "fill_in_blank" as QuestionType,
      label: "Fill in the Blank",
    },
    {
      value: "matching" as QuestionType,
      label: "Matching",
    },
    {
      value: "categorization" as QuestionType,
      label: "Categorization",
    },
    {
      value: "true_false" as QuestionType,
      label: "True/False",
    },
  ],
})

// Difficulty options collection for Chakra UI Select
const difficultyCollection = createListCollection({
  items: [
    {
      value: QUESTION_DIFFICULTIES.EASY,
      label: QUESTION_DIFFICULTY_LABELS.easy,
    },
    {
      value: QUESTION_DIFFICULTIES.MEDIUM,
      label: QUESTION_DIFFICULTY_LABELS.medium,
    },
    {
      value: QUESTION_DIFFICULTIES.HARD,
      label: QUESTION_DIFFICULTY_LABELS.hard,
    },
  ],
})

export const ModuleQuestionSelectionStep: React.FC<
  ModuleQuestionSelectionStepProps
> = ({ selectedModules, moduleQuestions, onModuleQuestionChange }) => {
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string[]>
  >({})

  const totalQuestions = useMemo(() => {
    return calculateTotalQuestionsFromBatches(moduleQuestions)
  }, [moduleQuestions])

  const moduleIds = Object.keys(selectedModules)

  const addBatch = (moduleId: string) => {
    const currentBatches = moduleQuestions[moduleId] || []

    if (currentBatches.length >= VALIDATION_RULES.MAX_BATCHES_PER_MODULE) {
      setValidationErrors((prev) => ({
        ...prev,
        [moduleId]: [VALIDATION_MESSAGES.MAX_BATCHES],
      }))
      return
    }

    const newBatch: QuestionBatch = {
      question_type: QUESTION_BATCH_DEFAULTS.DEFAULT_QUESTION_TYPE,
      count: QUESTION_BATCH_DEFAULTS.DEFAULT_QUESTION_COUNT,
      difficulty: QUESTION_BATCH_DEFAULTS.DEFAULT_DIFFICULTY,
    }

    const updatedBatches = [...currentBatches, newBatch]
    onModuleQuestionChange(moduleId, updatedBatches)

    // Clear validation errors
    setValidationErrors((prev) => {
      const newErrors = { ...prev }
      delete newErrors[moduleId]
      return newErrors
    })
  }

  const removeBatch = (moduleId: string, batchIndex: number) => {
    const currentBatches = moduleQuestions[moduleId] || []
    const updatedBatches = currentBatches.filter(
      (_, index) => index !== batchIndex,
    )
    onModuleQuestionChange(moduleId, updatedBatches)

    // Clear validation errors if removing resolved the issue
    if (updatedBatches.length <= VALIDATION_RULES.MAX_BATCHES_PER_MODULE) {
      setValidationErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[moduleId]
        return newErrors
      })
    }
  }

  const updateBatch = (
    moduleId: string,
    batchIndex: number,
    updates: Partial<QuestionBatch>,
  ) => {
    const currentBatches = moduleQuestions[moduleId] || []
    const updatedBatches = currentBatches.map((batch, index) =>
      index === batchIndex ? { ...batch, ...updates } : batch,
    )

    // Validate the updated batches
    const errors = validateModuleBatches(updatedBatches)

    if (errors.length > 0) {
      setValidationErrors((prev) => ({
        ...prev,
        [moduleId]: errors,
      }))
    } else {
      setValidationErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[moduleId]
        return newErrors
      })
    }

    onModuleQuestionChange(moduleId, updatedBatches)
  }

  const handleQuestionCountChange = (
    moduleId: string,
    batchIndex: number,
    value: string,
  ) => {
    const numValue = Number.parseInt(value, 10)
    if (!Number.isNaN(numValue) && numValue >= 1 && numValue <= 20) {
      updateBatch(moduleId, batchIndex, { count: numValue })
    }
  }

  return (
    <Box>
      <VStack gap={6} align="stretch">
        <Box>
          <Heading size="md" mb={2}>
            Configure Question Types per Module
          </Heading>
          <Text color="gray.600">
            Add question batches for each module. Each batch can have a
            different question type, count (1-20 questions), and difficulty
            level (max 4 batches per module).
          </Text>
        </Box>

        {/* Summary Card */}
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

        {/* Large question count warning */}
        {totalQuestions > 500 && (
          <Alert.Root status="warning">
            <Alert.Indicator />
            <Alert.Title>Large Question Count</Alert.Title>
            <Alert.Description>
              Large number of questions may take longer to generate.
            </Alert.Description>
          </Alert.Root>
        )}

        {/* Module Configuration */}
        <VStack gap={4} align="stretch">
          {moduleIds.map((moduleId) => {
            const moduleBatches = moduleQuestions[moduleId] || []
            const moduleErrors = validationErrors[moduleId] || []
            const moduleTotal = calculateModuleQuestions(moduleBatches)

            return (
              <Card.Root
                key={moduleId}
                variant="outline"
                borderColor={moduleErrors.length > 0 ? "red.200" : "gray.200"}
                bg={moduleErrors.length > 0 ? "red.50" : "white"}
              >
                <Card.Body>
                  <VStack align="stretch" gap={4}>
                    {/* Module Header */}
                    <HStack justify="space-between" align="center">
                      <Box>
                        <Text fontWeight="medium" fontSize="lg">
                          {selectedModules[moduleId]}
                        </Text>
                        <Text fontSize="sm" color="gray.600">
                          {moduleTotal} questions total • {moduleBatches.length}{" "}
                          batches
                        </Text>
                      </Box>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => addBatch(moduleId)}
                        disabled={
                          moduleBatches.length >=
                          VALIDATION_RULES.MAX_BATCHES_PER_MODULE
                        }
                      >
                        <IoAdd />
                        Add Batch
                      </Button>
                    </HStack>

                    {/* Validation Errors */}
                    {moduleErrors.length > 0 && (
                      <Alert.Root status="error" size="sm">
                        <Alert.Indicator />
                        <Alert.Description>
                          {moduleErrors.map((error, index) => (
                            <Text key={index} fontSize="sm">
                              {error}
                            </Text>
                          ))}
                        </Alert.Description>
                      </Alert.Root>
                    )}

                    {/* Question Batches */}
                    {moduleBatches.length > 0 ? (
                      <VStack gap={3} align="stretch">
                        {moduleBatches.map((batch, batchIndex) => (
                          <Box
                            key={batchIndex}
                            p={3}
                            bg="gray.50"
                            borderRadius="md"
                            border="1px solid"
                            borderColor="gray.200"
                          >
                            <HStack gap={3} align="end">
                              <Box flex={1}>
                                <Field label="Question Type">
                                  <Select.Root
                                    collection={questionTypeCollection}
                                    value={[batch.question_type]}
                                    onValueChange={(details) =>
                                      updateBatch(moduleId, batchIndex, {
                                        question_type: details
                                          .value[0] as QuestionType,
                                      })
                                    }
                                    size="sm"
                                  >
                                    <Select.Control>
                                      <Select.Trigger>
                                        <Select.ValueText placeholder="Select question type" />
                                      </Select.Trigger>
                                      <Select.IndicatorGroup>
                                        <Select.Indicator />
                                      </Select.IndicatorGroup>
                                    </Select.Control>
                                    <Select.Positioner>
                                      <Select.Content>
                                        {questionTypeCollection.items.map(
                                          (option) => (
                                            <Select.Item
                                              item={option}
                                              key={option.value}
                                            >
                                              {option.label}
                                              <Select.ItemIndicator />
                                            </Select.Item>
                                          ),
                                        )}
                                      </Select.Content>
                                    </Select.Positioner>
                                  </Select.Root>
                                </Field>
                              </Box>

                              <Box width="100px">
                                <Field label="Questions">
                                  <Input
                                    type="number"
                                    min={1}
                                    max={20}
                                    value={batch.count}
                                    onChange={(e) =>
                                      handleQuestionCountChange(
                                        moduleId,
                                        batchIndex,
                                        e.target.value,
                                      )
                                    }
                                    textAlign="center"
                                    size="sm"
                                  />
                                </Field>
                              </Box>

                              <Box width="120px">
                                <Field label="Difficulty">
                                  <Select.Root
                                    collection={difficultyCollection}
                                    value={[
                                      batch.difficulty ||
                                        QUESTION_DIFFICULTIES.MEDIUM,
                                    ]}
                                    onValueChange={(details) =>
                                      updateBatch(moduleId, batchIndex, {
                                        difficulty: details
                                          .value[0] as QuestionDifficulty,
                                      })
                                    }
                                    size="sm"
                                  >
                                    <Select.Control>
                                      <Select.Trigger>
                                        <Select.ValueText placeholder="Select difficulty" />
                                      </Select.Trigger>
                                      <Select.IndicatorGroup>
                                        <Select.Indicator />
                                      </Select.IndicatorGroup>
                                    </Select.Control>
                                    <Select.Positioner>
                                      <Select.Content>
                                        {difficultyCollection.items.map(
                                          (option) => (
                                            <Select.Item
                                              item={option}
                                              key={option.value}
                                            >
                                              {option.label}
                                              <Select.ItemIndicator />
                                            </Select.Item>
                                          ),
                                        )}
                                      </Select.Content>
                                    </Select.Positioner>
                                  </Select.Root>
                                </Field>
                              </Box>

                              <Button
                                size="sm"
                                variant="ghost"
                                colorScheme="red"
                                onClick={() =>
                                  removeBatch(moduleId, batchIndex)
                                }
                              >
                                <IoClose />
                              </Button>
                            </HStack>
                          </Box>
                        ))}
                      </VStack>
                    ) : (
                      <Box textAlign="center" py={6} color="gray.500">
                        <Text>No question batches configured</Text>
                        <Text fontSize="sm">
                          Click "Add Batch" to get started
                        </Text>
                      </Box>
                    )}
                  </VStack>
                </Card.Body>
              </Card.Root>
            )
          })}
        </VStack>

        {moduleIds.length === 0 && (
          <Card.Root variant="outline">
            <Card.Body textAlign="center" py={8}>
              <Text color="gray.500">
                No modules selected. Go back to select modules first.
              </Text>
            </Card.Body>
          </Card.Root>
        )}

        <Box mt={4}>
          <Text fontSize="sm" color="gray.600">
            <strong>Tip:</strong> Mix different question types and difficulty
            levels to create comprehensive assessments. Each module can have up
            to 4 different question batches with 1-20 questions each.
          </Text>
        </Box>
      </VStack>
    </Box>
  )
}
