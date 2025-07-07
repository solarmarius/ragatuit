import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Radio, RadioGroup } from "@/components/ui/radio"
import { extractQuestionData } from "@/types/questionTypes"
import {
  Button,
  HStack,
  Input,
  Textarea,
} from "@chakra-ui/react"
import { memo, useState } from "react"
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

    const [formData, setFormData] = useState({
      questionText: essayData.question_text,
      gradingRubric: essayData.grading_rubric || "",
      maxWords: essayData.max_words?.toString() || "",
      expectedLength: essayData.expected_length || "",
      sampleAnswer: essayData.sample_answer || "",
    })

    const handleSave = () => {
      const updateData: QuestionUpdateRequest = {
        question_data: {
          question_text: formData.questionText,
          grading_rubric: formData.gradingRubric || null,
          max_words: formData.maxWords
            ? Number.parseInt(formData.maxWords)
            : null,
          expected_length: formData.expectedLength || null,
          sample_answer: formData.sampleAnswer || null,
        },
      }
      onSave(updateData)
    }

    return (
      <FormGroup>
        <FormField label="Question Text" isRequired>
          <Textarea
            value={formData.questionText}
            onChange={(e) =>
              setFormData({ ...formData, questionText: e.target.value })
            }
            placeholder="Enter question text..."
            rows={3}
          />
        </FormField>

        <FormField label="Expected Length">
          <RadioGroup
            value={formData.expectedLength}
            onValueChange={(details) =>
              setFormData({ ...formData, expectedLength: details.value })
            }
          >
            <HStack gap={4}>
              <Radio value="">None</Radio>
              <Radio value="short">Short</Radio>
              <Radio value="medium">Medium</Radio>
              <Radio value="long">Long</Radio>
            </HStack>
          </RadioGroup>
        </FormField>

        <FormField label="Maximum Words">
          <Input
            type="number"
            value={formData.maxWords}
            onChange={(e) =>
              setFormData({ ...formData, maxWords: e.target.value })
            }
            placeholder="Enter maximum word count..."
          />
        </FormField>

        <FormField label="Grading Rubric">
          <Textarea
            value={formData.gradingRubric}
            onChange={(e) =>
              setFormData({ ...formData, gradingRubric: e.target.value })
            }
            placeholder="Enter grading criteria and rubric..."
            rows={4}
          />
        </FormField>

        <FormField label="Sample Answer">
          <Textarea
            value={formData.sampleAnswer}
            onChange={(e) =>
              setFormData({ ...formData, sampleAnswer: e.target.value })
            }
            placeholder="Enter a sample answer or key points..."
            rows={4}
          />
        </FormField>

        <HStack gap={3} justify="end">
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button colorScheme="blue" onClick={handleSave} loading={isLoading}>
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
