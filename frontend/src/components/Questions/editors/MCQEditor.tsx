import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Radio, RadioGroup } from "@/components/ui/radio"
import { extractQuestionData } from "@/types/questionTypes"
import {
  Button,
  Fieldset,
  HStack,
  Input,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { memo, useState } from "react"
import { ErrorEditor } from "./ErrorEditor"

interface MCQEditorProps {
  question: QuestionResponse
  onSave: (updateData: QuestionUpdateRequest) => void
  onCancel: () => void
  isLoading: boolean
}

export const MCQEditor = memo(function MCQEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: MCQEditorProps) {
  try {
    const mcqData = extractQuestionData(question, "multiple_choice")

    const [formData, setFormData] = useState({
      questionText: mcqData.question_text,
      optionA: mcqData.option_a,
      optionB: mcqData.option_b,
      optionC: mcqData.option_c,
      optionD: mcqData.option_d,
      correctAnswer: mcqData.correct_answer,
      explanation: mcqData.explanation || "",
    })

    const handleSave = () => {
      const updateData: QuestionUpdateRequest = {
        question_data: {
          question_text: formData.questionText,
          option_a: formData.optionA,
          option_b: formData.optionB,
          option_c: formData.optionC,
          option_d: formData.optionD,
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

        <Fieldset.Root>
          <Fieldset.Legend>Answer Options</Fieldset.Legend>
          <VStack gap={3} align="stretch">
            <FormField label="Option A" isRequired>
              <Input
                value={formData.optionA}
                onChange={(e) =>
                  setFormData({ ...formData, optionA: e.target.value })
                }
                placeholder="Enter option A..."
              />
            </FormField>
            <FormField label="Option B" isRequired>
              <Input
                value={formData.optionB}
                onChange={(e) =>
                  setFormData({ ...formData, optionB: e.target.value })
                }
                placeholder="Enter option B..."
              />
            </FormField>
            <FormField label="Option C" isRequired>
              <Input
                value={formData.optionC}
                onChange={(e) =>
                  setFormData({ ...formData, optionC: e.target.value })
                }
                placeholder="Enter option C..."
              />
            </FormField>
            <FormField label="Option D" isRequired>
              <Input
                value={formData.optionD}
                onChange={(e) =>
                  setFormData({ ...formData, optionD: e.target.value })
                }
                placeholder="Enter option D..."
              />
            </FormField>
          </VStack>
        </Fieldset.Root>

        <FormField label="Correct Answer" isRequired>
          <RadioGroup
            value={formData.correctAnswer}
            onValueChange={(details) =>
              setFormData({
                ...formData,
                correctAnswer: details.value as "A" | "B" | "C" | "D",
              })
            }
          >
            <HStack gap={4}>
              <Radio value="A">A</Radio>
              <Radio value="B">B</Radio>
              <Radio value="C">C</Radio>
              <Radio value="D">D</Radio>
            </HStack>
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
        error="Error loading MCQ question data"
        onCancel={onCancel}
      />
    )
  }
})
