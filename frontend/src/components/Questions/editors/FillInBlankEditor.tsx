import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Checkbox } from "@/components/ui/checkbox"
import { type FillInBlankFormData, fillInBlankSchema } from "@/lib/validation"
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
import { memo } from "react"
import { Controller, useFieldArray, useForm } from "react-hook-form"
import { ErrorEditor } from "./ErrorEditor"

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
      formState: { errors, isDirty },
    } = useForm<FillInBlankFormData>({
      resolver: zodResolver(fillInBlankSchema),
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

    const addBlank = () => {
      const newPosition = Math.max(...fields.map((_, i) => i + 1), 0) + 1
      append({
        position: newPosition,
        correctAnswer: "",
        answerVariations: "",
        caseSensitive: false,
      })
    }

    return (
      <FormGroup>
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
                placeholder="Enter question text with blanks marked..."
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

            <Button variant="outline" onClick={addBlank}>
              Add Blank
            </Button>
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
            disabled={!isDirty}
          >
            Save Changes
          </Button>
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
