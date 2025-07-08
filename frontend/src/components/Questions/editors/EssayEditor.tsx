import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Radio, RadioGroup } from "@/components/ui/radio"
import { type EssayFormData, essaySchema } from "@/lib/validation"
import { extractQuestionData } from "@/types/questionTypes"
import { Button, HStack, Input, Textarea } from "@chakra-ui/react"
import { zodResolver } from "@hookform/resolvers/zod"
import { memo } from "react"
import { Controller, useForm } from "react-hook-form"
import { ErrorEditor } from "./ErrorEditor"

interface EssayEditorProps {
  question: QuestionResponse
  onSave: (updateData: QuestionUpdateRequest) => void
  onCancel: () => void
  isLoading: boolean
}

export const EssayEditor = memo(function EssayEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: EssayEditorProps) {
  try {
    const essayData = extractQuestionData(question, "essay")

    const {
      control,
      handleSubmit,
      formState: { errors, isDirty },
    } = useForm<EssayFormData>({
      resolver: zodResolver(essaySchema),
      defaultValues: {
        questionText: essayData.question_text,
        gradingRubric: essayData.grading_rubric || "",
        maxWords: essayData.max_words || null,
        expectedLength: essayData.expected_length || "",
        sampleAnswer: essayData.sample_answer || "",
      },
    })

    const onSubmit = (data: EssayFormData) => {
      const updateData: QuestionUpdateRequest = {
        question_data: {
          question_text: data.questionText,
          grading_rubric: data.gradingRubric || null,
          max_words: data.maxWords,
          expected_length: data.expectedLength || null,
          sample_answer: data.sampleAnswer || null,
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
          name="expectedLength"
          control={control}
          render={({ field: { onChange, value } }) => (
            <FormField
              label="Expected Length"
              error={errors.expectedLength?.message}
            >
              <RadioGroup
                value={value}
                onValueChange={(details) => onChange(details.value)}
              >
                <HStack gap={4}>
                  <Radio value="">None</Radio>
                  <Radio value="short">Short</Radio>
                  <Radio value="medium">Medium</Radio>
                  <Radio value="long">Long</Radio>
                </HStack>
              </RadioGroup>
            </FormField>
          )}
        />

        <Controller
          name="maxWords"
          control={control}
          render={({ field: { onChange, value, ...field } }) => (
            <FormField
              label="Maximum Words"
              error={errors.maxWords?.message}
              helperText="Optional limit on essay length"
            >
              <Input
                {...field}
                type="number"
                value={value?.toString() || ""}
                onChange={(e) =>
                  onChange(e.target.value ? Number(e.target.value) : null)
                }
                placeholder="Enter maximum word count..."
              />
            </FormField>
          )}
        />

        <Controller
          name="gradingRubric"
          control={control}
          render={({ field }) => (
            <FormField
              label="Grading Rubric"
              error={errors.gradingRubric?.message}
            >
              <Textarea
                {...field}
                placeholder="Enter grading criteria and rubric..."
                rows={4}
              />
            </FormField>
          )}
        />

        <Controller
          name="sampleAnswer"
          control={control}
          render={({ field }) => (
            <FormField
              label="Sample Answer"
              error={errors.sampleAnswer?.message}
            >
              <Textarea
                {...field}
                placeholder="Enter a sample answer or key points..."
                rows={4}
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
        error="Error loading Essay question data"
        onCancel={onCancel}
      />
    )
  }
})
