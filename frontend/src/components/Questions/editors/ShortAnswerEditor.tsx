import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Checkbox } from "@/components/ui/checkbox"
import { type ShortAnswerFormData, shortAnswerSchema } from "@/lib/validation"
import { extractQuestionData } from "@/types/questionTypes"
import { Button, HStack, Input, Textarea } from "@chakra-ui/react"
import { zodResolver } from "@hookform/resolvers/zod"
import { memo } from "react"
import { Controller, useForm } from "react-hook-form"
import { ErrorEditor } from "./ErrorEditor"

interface ShortAnswerEditorProps {
  question: QuestionResponse
  onSave: (updateData: QuestionUpdateRequest) => void
  onCancel: () => void
  isLoading: boolean
}

export const ShortAnswerEditor = memo(function ShortAnswerEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: ShortAnswerEditorProps) {
  try {
    const saData = extractQuestionData(question, "short_answer")

    const {
      control,
      handleSubmit,
      formState: { errors, isDirty },
    } = useForm<ShortAnswerFormData>({
      resolver: zodResolver(shortAnswerSchema),
      defaultValues: {
        questionText: saData.question_text,
        correctAnswer: saData.correct_answer,
        answerVariations: saData.answer_variations?.join(", ") || "",
        caseSensitive: saData.case_sensitive || false,
        explanation: saData.explanation || "",
      },
    })

    const onSubmit = (data: ShortAnswerFormData) => {
      const updateData: QuestionUpdateRequest = {
        question_data: {
          question_text: data.questionText,
          correct_answer: data.correctAnswer,
          answer_variations: data.answerVariations
            ? data.answerVariations
                .split(",")
                .map((v) => v.trim())
                .filter((v) => v)
            : undefined,
          case_sensitive: data.caseSensitive,
          explanation: data.explanation || null,
        },
      }
      onSave(updateData)
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
                placeholder="Enter question text..."
                rows={3}
              />
            </FormField>
          )}
        />

        <Controller
          name="correctAnswer"
          control={control}
          render={({ field }) => (
            <FormField
              label="Correct Answer"
              isRequired
              error={errors.correctAnswer?.message}
            >
              <Input {...field} placeholder="Enter the correct answer..." />
            </FormField>
          )}
        />

        <Controller
          name="answerVariations"
          control={control}
          render={({ field }) => (
            <FormField
              label="Answer Variations"
              error={errors.answerVariations?.message}
              helperText="Separate multiple accepted variations with commas"
            >
              <Input
                {...field}
                placeholder="Enter variations separated by commas..."
              />
            </FormField>
          )}
        />

        <Controller
          name="caseSensitive"
          control={control}
          render={({ field: { onChange, value } }) => (
            <FormField error={errors.caseSensitive?.message}>
              <Checkbox
                checked={value}
                onCheckedChange={(e) => onChange(!!e.checked)}
              >
                Case sensitive
              </Checkbox>
            </FormField>
          )}
        />

        <Controller
          name="explanation"
          control={control}
          render={({ field }) => (
            <FormField label="Explanation" error={errors.explanation?.message}>
              <Textarea
                {...field}
                placeholder="Enter explanation for the answer..."
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
        error="Error loading Short Answer question data"
        onCancel={onCancel}
      />
    )
  }
})
