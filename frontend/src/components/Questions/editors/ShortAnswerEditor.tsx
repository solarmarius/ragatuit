import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Checkbox } from "@/components/ui/checkbox"
import { extractQuestionData } from "@/types/questionTypes"
import {
  Button,
  HStack,
  Input,
  Text,
  Textarea,
} from "@chakra-ui/react"
import { memo, useState } from "react"
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

    const [formData, setFormData] = useState({
      questionText: saData.question_text,
      correctAnswer: saData.correct_answer,
      answerVariations: saData.answer_variations?.join(", ") || "",
      caseSensitive: saData.case_sensitive || false,
      explanation: saData.explanation || "",
    })

    const handleSave = () => {
      const updateData: QuestionUpdateRequest = {
        question_data: {
          question_text: formData.questionText,
          correct_answer: formData.correctAnswer,
          answer_variations: formData.answerVariations
            ? formData.answerVariations
                .split(",")
                .map((v) => v.trim())
                .filter((v) => v)
            : undefined,
          case_sensitive: formData.caseSensitive,
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
          <Input
            value={formData.correctAnswer}
            onChange={(e) =>
              setFormData({ ...formData, correctAnswer: e.target.value })
            }
            placeholder="Enter the correct answer..."
          />
        </FormField>

        <FormField label="Answer Variations">
          <Input
            value={formData.answerVariations}
            onChange={(e) =>
              setFormData({ ...formData, answerVariations: e.target.value })
            }
            placeholder="Enter variations separated by commas..."
          />
          <Text fontSize="xs" color="gray.600" mt={1}>
            Separate multiple accepted variations with commas
          </Text>
        </FormField>

        <FormField>
          <Checkbox
            checked={formData.caseSensitive}
            onCheckedChange={(e) =>
              setFormData({ ...formData, caseSensitive: !!e.checked })
            }
          >
            Case sensitive
          </Checkbox>
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
        error="Error loading Short Answer question data"
        onCancel={onCancel}
      />
    )
  }
})
