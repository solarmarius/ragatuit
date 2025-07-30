import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import {
  type MatchingFormData,
  matchingSchema,
} from "@/lib/validation/questionSchemas"
import { extractQuestionData } from "@/types/questionTypes"
import {
  Box,
  Button,
  Fieldset,
  HStack,
  Input,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { zodResolver } from "@hookform/resolvers/zod"
import { memo, useCallback } from "react"
import { Controller, useFieldArray, useForm } from "react-hook-form"
import { MdAdd, MdDelete } from "react-icons/md"
import { ErrorEditor } from "./ErrorEditor"

interface MatchingEditorProps {
  question: QuestionResponse
  onSave: (updateData: QuestionUpdateRequest) => void
  onCancel: () => void
  isLoading: boolean
}

export const MatchingEditor = memo(function MatchingEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: MatchingEditorProps) {
  try {
    const matchingData = extractQuestionData(question, "matching")

    const {
      control,
      handleSubmit,
      watch,
      setValue,
      formState: { errors, isDirty },
    } = useForm<MatchingFormData>({
      resolver: zodResolver(matchingSchema),
      defaultValues: {
        questionText: matchingData.question_text,
        pairs: matchingData.pairs,
        distractors: matchingData.distractors || [],
        explanation: matchingData.explanation || "",
      },
    })

    const {
      fields: pairFields,
      append: appendPair,
      remove: removePair,
    } = useFieldArray({
      control,
      name: "pairs",
    })

    // Handle distractors as array of strings
    const distractors = watch("distractors") || []

    const handleDistractorChange = useCallback(
      (index: number, value: string) => {
        const newDistractors = [...distractors]
        newDistractors[index] = value
        setValue("distractors", newDistractors, {
          shouldValidate: true,
          shouldDirty: true,
        })
      },
      [distractors, setValue],
    )

    const appendDistractor = useCallback(
      (value: string) => {
        setValue("distractors", [...distractors, value], {
          shouldValidate: true,
          shouldDirty: true,
        })
      },
      [distractors, setValue],
    )

    const removeDistractor = useCallback(
      (index: number) => {
        const newDistractors = distractors.filter((_, i) => i !== index)
        setValue("distractors", newDistractors, {
          shouldValidate: true,
          shouldDirty: true,
        })
      },
      [distractors, setValue],
    )

    const onSubmit = useCallback(
      (formData: MatchingFormData) => {
        const updateData: QuestionUpdateRequest = {
          question_data: {
            question_text: formData.questionText,
            pairs: formData.pairs,
            distractors: formData.distractors?.length
              ? formData.distractors
              : null,
            explanation: formData.explanation || null,
          },
        }
        onSave(updateData)
      },
      [onSave],
    )

    const handleAddPair = useCallback(() => {
      if (pairFields.length < 10) {
        appendPair({ question: "", answer: "" })
      }
    }, [appendPair, pairFields.length])

    const handleAddDistractor = useCallback(() => {
      if (distractors.length < 5) {
        appendDistractor("")
      }
    }, [appendDistractor, distractors.length])

    return (
      <FormGroup>
        {/* Form-level validation errors */}
        {errors.root?.message && (
          <Box
            p={3}
            bg="red.50"
            border="1px"
            borderColor="red.200"
            borderRadius="md"
            mb={4}
          >
            <Text color="red.600" fontSize="sm" fontWeight="medium">
              {errors.root.message}
            </Text>
          </Box>
        )}
        <Controller
          name="questionText"
          control={control}
          render={({ field }) => (
            <FormField
              label="Question Text"
              isRequired
              error={errors.questionText?.message}
            >
              <Textarea
                {...field}
                placeholder="Enter the matching question instructions..."
                rows={3}
              />
            </FormField>
          )}
        />

        <Fieldset.Root>
          <Fieldset.Legend>
            Matching Pairs ({pairFields.length}/10)
          </Fieldset.Legend>
          <VStack gap={4} align="stretch">
            {errors.pairs?.message && (
              <Text color="red.500" fontSize="sm">
                {errors.pairs.message}
              </Text>
            )}
            {errors.pairs?.root?.message && (
              <Text color="red.500" fontSize="sm">
                {errors.pairs.root.message}
              </Text>
            )}

            {pairFields.map((field, index) => (
              <Box key={field.id} p={4} borderWidth={1} borderRadius="md">
                <HStack align="flex-start" gap={4} mb={2}>
                  <Text fontSize="sm" fontWeight="medium" color="gray.600">
                    Pair {index + 1}
                  </Text>
                  <Button
                    size="sm"
                    variant="ghost"
                    colorScheme="red"
                    onClick={() => removePair(index)}
                    disabled={pairFields.length <= 3}
                    aria-label={`Remove pair ${index + 1}`}
                  >
                    <MdDelete />
                  </Button>
                </HStack>
                <HStack align="flex-start" gap={4}>
                  <Box flex={1}>
                    <Controller
                      name={`pairs.${index}.question`}
                      control={control}
                      render={({ field: inputField }) => (
                        <FormField
                          label="Question/Left Item"
                          isRequired
                          error={errors.pairs?.[index]?.question?.message}
                        >
                          <Input
                            {...inputField}
                            placeholder="Enter question or left item..."
                          />
                        </FormField>
                      )}
                    />
                  </Box>
                  <Box flex={1}>
                    <Controller
                      name={`pairs.${index}.answer`}
                      control={control}
                      render={({ field: inputField }) => (
                        <FormField
                          label="Answer/Right Item"
                          isRequired
                          error={errors.pairs?.[index]?.answer?.message}
                        >
                          <Input
                            {...inputField}
                            placeholder="Enter answer or right item..."
                          />
                        </FormField>
                      )}
                    />
                  </Box>
                </HStack>
              </Box>
            ))}

            <Button
              onClick={handleAddPair}
              disabled={pairFields.length >= 10}
              variant="outline"
              colorScheme="blue"
              size="sm"
            >
              <MdAdd />
              Add Pair
            </Button>

            <Text fontSize="sm" color="gray.600">
              At least 3 pairs required, maximum 10 pairs allowed.
            </Text>
          </VStack>
        </Fieldset.Root>

        <Fieldset.Root>
          <Fieldset.Legend>
            Distractors ({distractors.length}/5)
          </Fieldset.Legend>
          <VStack gap={3} align="stretch">
            {errors.distractors?.message && (
              <Text color="red.500" fontSize="sm">
                {errors.distractors.message}
              </Text>
            )}
            {errors.distractors?.root?.message && (
              <Text color="red.500" fontSize="sm">
                {errors.distractors.root.message}
              </Text>
            )}

            {distractors.map((distractor: string, index: number) => (
              <HStack key={`distractor-${index}`} align="flex-start">
                <Box flex={1}>
                  <FormField
                    label={`Distractor ${index + 1}`}
                    error={errors.distractors?.[index]?.message}
                  >
                    <Input
                      value={distractor}
                      onChange={(e) =>
                        handleDistractorChange(index, e.target.value)
                      }
                      placeholder="Enter incorrect answer option..."
                    />
                  </FormField>
                </Box>
                <Button
                  size="sm"
                  variant="ghost"
                  colorScheme="red"
                  onClick={() => removeDistractor(index)}
                  aria-label={`Remove distractor ${index + 1}`}
                  mt={6}
                >
                  <MdDelete />
                </Button>
              </HStack>
            ))}

            <Button
              onClick={handleAddDistractor}
              disabled={distractors.length >= 5}
              variant="outline"
              colorScheme="blue"
              size="sm"
            >
              <MdAdd />
              Add Distractor
            </Button>

            <Text fontSize="sm" color="gray.600">
              Optional incorrect answers that don't match any question. Maximum
              5 allowed.
            </Text>
          </VStack>
        </Fieldset.Root>

        <Controller
          name="explanation"
          control={control}
          render={({ field }) => (
            <FormField label="Explanation" error={errors.explanation?.message}>
              <Textarea
                {...field}
                placeholder="Optional explanation for the correct matches..."
                rows={3}
              />
            </FormField>
          )}
        />

        <HStack gap={3} justify="end">
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit(onSubmit)}
            loading={isLoading}
            disabled={!isDirty}
          >
            Save Changes
          </Button>
        </HStack>
      </FormGroup>
    )
  } catch (error) {
    console.error("Error rendering matching question editor:", error)
    return (
      <ErrorEditor
        error="Error loading question data for editing"
        onCancel={onCancel}
      />
    )
  }
})
