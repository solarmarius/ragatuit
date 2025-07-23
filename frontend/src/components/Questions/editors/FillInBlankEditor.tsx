import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Checkbox } from "@/components/ui/checkbox"
import { getNextBlankPosition, validateBlankTextComprehensive } from "@/lib/utils/fillInBlankUtils"
import { type FillInBlankFormData, fillInBlankSchema } from "@/lib/validation"
import type { BlankValidationError } from "@/types/fillInBlankValidation"
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
import { memo, useMemo } from "react"
import { Controller, useFieldArray, useForm, useWatch } from "react-hook-form"
import { ErrorEditor } from "./ErrorEditor"
import { FillInBlankValidationErrors } from "./FillInBlankValidationErrors"

interface FillInBlankEditorProps {
  question: QuestionResponse
  onSave: (updateData: QuestionUpdateRequest) => void
  onCancel: () => void
  isLoading: boolean
}

export const FillInBlankEditor = memo(function FillInBlankEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: FillInBlankEditorProps) {
  try {
    const fibData = extractQuestionData(question, "fill_in_blank")

    const {
      control,
      handleSubmit,
      formState: { errors, isDirty, isValid },
    } = useForm<FillInBlankFormData>({
      resolver: zodResolver(fillInBlankSchema),
      mode: "onChange", // Enable real-time validation
      defaultValues: {
        questionText: fibData.question_text,
        blanks: fibData.blanks.map((blank) => ({
          position: blank.position,
          correctAnswer: blank.correct_answer,
          answerVariations: blank.answer_variations?.join(", ") || "",
          caseSensitive: blank.case_sensitive || false,
        })),
        explanation: fibData.explanation || "",
      },
    })

    // Watch question text and blanks for real-time validation
    const watchedQuestionText = useWatch({ control, name: "questionText" })
    const watchedBlanks = useWatch({ control, name: "blanks" })

    const { fields, append, remove } = useFieldArray({
      control,
      name: "blanks",
    })

    const onSubmit = (data: FillInBlankFormData) => {
      const updateData: QuestionUpdateRequest = {
        question_data: {
          question_text: data.questionText,
          blanks: data.blanks.map((blank) => ({
            position: blank.position,
            correct_answer: blank.correctAnswer,
            answer_variations: blank.answerVariations
              ? blank.answerVariations
                  .split(",")
                  .map((v) => v.trim())
                  .filter((v) => v)
              : undefined,
            case_sensitive: blank.caseSensitive,
          })),
          explanation: data.explanation || null,
        },
      }
      onSave(updateData)
    }

    // Extract validation errors for display
    const validationErrors = useMemo((): BlankValidationError[] => {
      const formErrors: BlankValidationError[] = []

      // Extract errors from form state
      if (errors.questionText?.message) {
        formErrors.push({
          code: "INVALID_TAG_FORMAT" as any,
          message: errors.questionText.message,
        })
      }

      if (errors.blanks?.message) {
        formErrors.push({
          code: "MISSING_BLANK_CONFIG" as any,
          message: errors.blanks.message,
        })
      }

      // Check for individual blank errors
      if (errors.blanks && Array.isArray(errors.blanks)) {
        errors.blanks.forEach((blankError, index) => {
          if (blankError?.message) {
            formErrors.push({
              code: "MISSING_BLANK_CONFIG" as any,
              message: `Blank ${index + 1}: ${blankError.message}`,
            })
          }
        })
      }

      return formErrors
    }, [errors])

    // Smart blank addition based on question text
    const addBlank = () => {
      if (watchedQuestionText) {
        const configuredPositions = watchedBlanks?.map(blank => blank.position) || []
        const validation = validateBlankTextComprehensive(watchedQuestionText, configuredPositions)

        // Find the first missing position using optimized validation
        const missingPosition = validation.missingConfigurations[0]

        if (missingPosition) {
          // Add blank for missing position from question text
          append({
            position: missingPosition,
            correctAnswer: "",
            answerVariations: "",
            caseSensitive: false,
          })
        } else {
          // No missing positions, add next sequential position
          const nextPosition = getNextBlankPosition(watchedQuestionText)
          append({
            position: nextPosition,
            correctAnswer: "",
            answerVariations: "",
            caseSensitive: false,
          })
        }
      } else {
        // Fallback to old behavior if no question text
        const newPosition = Math.max(...fields.map((_, i) => i + 1), 0) + 1
        append({
          position: newPosition,
          correctAnswer: "",
          answerVariations: "",
          caseSensitive: false,
        })
      }
    }

    // Determine if saving is allowed
    const canSave = isDirty && isValid && validationErrors.length === 0

    return (
      <FormGroup>
        {/* Show validation errors at the top */}
        {validationErrors.length > 0 && (
          <FillInBlankValidationErrors errors={validationErrors} />
        )}

        <Controller
          name="questionText"
          control={control}
          render={({ field }) => (
            <FormField
              label="Question Text"
              isRequired
              error={errors.questionText?.message}
              helperText="Use [blank_1], [blank_2], etc. to mark blanks in your question"
            >
              <Textarea
                {...field}
                placeholder="Enter question text with blanks marked as [blank_1], [blank_2]..."
                rows={3}
              />
            </FormField>
          )}
        />

        <Fieldset.Root>
          <Fieldset.Legend>Blanks</Fieldset.Legend>
          <VStack gap={4} align="stretch">
            {fields.map((field, index) => (
              <Box
                key={field.id}
                p={3}
                border="1px solid"
                borderColor="gray.200"
                borderRadius="md"
              >
                <FormGroup gap={3}>
                  <HStack>
                    <Text fontWeight="medium" fontSize="sm">
                      Blank {index + 1}
                    </Text>
                    <Button
                      size="sm"
                      variant="outline"
                      colorScheme="red"
                      onClick={() => remove(index)}
                    >
                      Remove
                    </Button>
                  </HStack>

                  <Controller
                    name={`blanks.${index}.correctAnswer`}
                    control={control}
                    render={({ field }) => (
                      <FormField
                        label="Correct Answer"
                        isRequired
                        error={errors.blanks?.[index]?.correctAnswer?.message}
                      >
                        <Input
                          {...field}
                          placeholder="Enter correct answer..."
                        />
                      </FormField>
                    )}
                  />

                  <Controller
                    name={`blanks.${index}.answerVariations`}
                    control={control}
                    render={({ field }) => (
                      <FormField
                        label="Answer Variations"
                        error={
                          errors.blanks?.[index]?.answerVariations?.message
                        }
                        helperText="Separate multiple variations with commas"
                      >
                        <Input
                          {...field}
                          placeholder="Enter variations separated by commas..."
                        />
                      </FormField>
                    )}
                  />

                  <Controller
                    name={`blanks.${index}.caseSensitive`}
                    control={control}
                    render={({ field: { onChange, value } }) => (
                      <FormField
                        error={errors.blanks?.[index]?.caseSensitive?.message}
                      >
                        <Checkbox
                          checked={value}
                          onCheckedChange={(e) => onChange(!!e.checked)}
                        >
                          Case sensitive
                        </Checkbox>
                      </FormField>
                    )}
                  />
                </FormGroup>
              </Box>
            ))}

            <Box>
              <Button
                variant="outline"
                onClick={addBlank}
                disabled={!watchedQuestionText}
              >
                Add Blank
              </Button>
              {!watchedQuestionText && (
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Add question text first to enable smart blank creation
                </Text>
              )}
              {watchedQuestionText && (
                <Text fontSize="xs" color="gray.600" mt={1}>
                  Next position: {getNextBlankPosition(watchedQuestionText)}
                </Text>
              )}
            </Box>
          </VStack>
        </Fieldset.Root>

        <Controller
          name="explanation"
          control={control}
          render={({ field }) => (
            <FormField label="Explanation" error={errors.explanation?.message}>
              <Textarea
                {...field}
                placeholder="Enter explanation for the answers..."
                rows={2}
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
            disabled={!canSave}
          >
            Save Changes
          </Button>
          {!canSave && isDirty && (
            <Text fontSize="xs" color="gray.500">
              {validationErrors.length > 0
                ? "Fix validation errors to save"
                : !isValid
                  ? "Complete required fields to save"
                  : "No changes to save"}
            </Text>
          )}
        </HStack>
      </FormGroup>
    )
  } catch (error) {
    return (
      <ErrorEditor
        error="Error loading Fill in Blank question data"
        onCancel={onCancel}
      />
    )
  }
})
