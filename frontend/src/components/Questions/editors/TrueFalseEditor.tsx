import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Radio, RadioGroup } from "@/components/ui/radio"
import { type TrueFalseFormData, trueFalseSchema } from "@/lib/validation"
import { extractQuestionData } from "@/types/questionTypes"
import { Button, HStack, Textarea, VStack } from "@chakra-ui/react"
import { zodResolver } from "@hookform/resolvers/zod"
import { memo } from "react"
import { Controller, useForm } from "react-hook-form"
import { ErrorEditor } from "./ErrorEditor"

interface TrueFalseEditorProps {
  question: QuestionResponse
  onSave: (updateData: QuestionUpdateRequest) => void
  onCancel: () => void
  isLoading: boolean
}

export const TrueFalseEditor = memo(function TrueFalseEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: TrueFalseEditorProps) {
  try {
    const tfData = extractQuestionData(question, "true_false")

    const {
      control,
      handleSubmit,
      formState: { errors, isDirty },
    } = useForm<TrueFalseFormData>({
      resolver: zodResolver(trueFalseSchema),
      defaultValues: {
        questionText: tfData.question_text,
        correctAnswer: tfData.correct_answer,
        explanation: tfData.explanation || "",
      },
    })

    const onSubmit = (data: TrueFalseFormData) => {
      const updateData: QuestionUpdateRequest = {
        question_data: {
          question_text: data.questionText,
          correct_answer: data.correctAnswer,
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
          render={({ field: { onChange, value } }) => (
            <FormField
              label="Correct Answer"
              isRequired
              error={errors.correctAnswer?.message}
            >
              <RadioGroup
                value={value.toString()}
                onValueChange={(details) => onChange(details.value === "true")}
              >
                <VStack gap={2} align="start">
                  <Radio value="true">True</Radio>
                  <Radio value="false">False</Radio>
                </VStack>
              </RadioGroup>
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
        error="Error loading True/False question data"
        onCancel={onCancel}
      />
    )
  }
})
