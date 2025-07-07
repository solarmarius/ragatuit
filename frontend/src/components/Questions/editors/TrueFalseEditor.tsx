import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Radio, RadioGroup } from "@/components/ui/radio"
import { extractQuestionData } from "@/types/questionTypes"
import {
  Button,
  HStack,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { memo, useState } from "react"
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

    const [formData, setFormData] = useState({
      questionText: tfData.question_text,
      correctAnswer: tfData.correct_answer,
      explanation: tfData.explanation || "",
    })

    const handleSave = () => {
      const updateData: QuestionUpdateRequest = {
        question_data: {
          question_text: formData.questionText,
          correct_answer: formData.correctAnswer,
          explanation: formData.explanation || null,
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

        <FormField label="Correct Answer" isRequired>
          <RadioGroup
            value={formData.correctAnswer.toString()}
            onValueChange={(details) =>
              setFormData({
                ...formData,
                correctAnswer: details.value === "true",
              })
            }
          >
            <VStack gap={2} align="start">
              <Radio value="true">True</Radio>
              <Radio value="false">False</Radio>
            </VStack>
          </RadioGroup>
        </FormField>

        <FormField label="Explanation">
          <Textarea
            value={formData.explanation}
            onChange={(e) =>
              setFormData({ ...formData, explanation: e.target.value })
            }
            placeholder="Enter explanation for the answer..."
            rows={2}
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
        error="Error loading True/False question data"
        onCancel={onCancel}
      />
    )
  }
})
