import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { Checkbox } from "@/components/ui/checkbox"
import {
  type FillInBlankData,
  extractQuestionData,
} from "@/types/questionTypes"
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
import { memo, useState } from "react"
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

    const [formData, setFormData] = useState({
      questionText: fibData.question_text,
      blanks: fibData.blanks.map((blank) => ({
        position: blank.position,
        correctAnswer: blank.correct_answer,
        answerVariations: blank.answer_variations?.join(", ") || "",
        caseSensitive: blank.case_sensitive || false,
      })),
      explanation: fibData.explanation || "",
    })

    const handleSave = () => {
      const updateData: QuestionUpdateRequest = {
        question_data: {
          question_text: formData.questionText,
          blanks: formData.blanks.map((blank) => ({
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
          explanation: formData.explanation || null,
        },
      }
      onSave(updateData)
    }

    const addBlank = () => {
      const newPosition =
        Math.max(...formData.blanks.map((b) => b.position), 0) + 1
      setFormData({
        ...formData,
        blanks: [
          ...formData.blanks,
          {
            position: newPosition,
            correctAnswer: "",
            answerVariations: "",
            caseSensitive: false,
          },
        ],
      })
    }

    const removeBlank = (index: number) => {
      setFormData({
        ...formData,
        blanks: formData.blanks.filter((_, i) => i !== index),
      })
    }

    const updateBlank = (
      index: number,
      field: keyof FillInBlankData["blanks"][0],
      value: string | boolean,
    ) => {
      const updatedBlanks = [...formData.blanks]
      const fieldMap: Record<
        keyof FillInBlankData["blanks"][0],
        keyof (typeof updatedBlanks)[0]
      > = {
        correct_answer: "correctAnswer",
        answer_variations: "answerVariations",
        case_sensitive: "caseSensitive",
        position: "position",
      }
      const formField = fieldMap[field]
      updatedBlanks[index] = { ...updatedBlanks[index], [formField]: value }
      setFormData({ ...formData, blanks: updatedBlanks })
    }

    return (
      <FormGroup>
        <FormField label="Question Text" isRequired>
          <Textarea
            value={formData.questionText}
            onChange={(e) =>
              setFormData({ ...formData, questionText: e.target.value })
            }
            placeholder="Enter question text with blanks marked..."
            rows={3}
          />
        </FormField>

        <Fieldset.Root>
          <Fieldset.Legend>Blanks</Fieldset.Legend>
          <VStack gap={4} align="stretch">
            {formData.blanks.map((blank, index) => (
              <Box
                key={index}
                p={3}
                border="1px solid"
                borderColor="gray.200"
                borderRadius="md"
              >
                <FormGroup gap={3}>
                  <HStack>
                    <Text fontWeight="medium" fontSize="sm">
                      Blank {blank.position}
                    </Text>
                    <Button
                      size="sm"
                      variant="outline"
                      colorScheme="red"
                      onClick={() => removeBlank(index)}
                    >
                      Remove
                    </Button>
                  </HStack>

                  <FormField label="Correct Answer" isRequired>
                    <Input
                      value={blank.correctAnswer}
                      onChange={(e) =>
                        updateBlank(index, "correct_answer", e.target.value)
                      }
                      placeholder="Enter correct answer..."
                    />
                  </FormField>

                  <FormField label="Answer Variations">
                    <Input
                      value={blank.answerVariations}
                      onChange={(e) =>
                        updateBlank(index, "answer_variations", e.target.value)
                      }
                      placeholder="Enter variations separated by commas..."
                    />
                  </FormField>

                  <FormField>
                    <Checkbox
                      checked={blank.caseSensitive}
                      onCheckedChange={(e) =>
                        updateBlank(index, "case_sensitive", !!e.checked)
                      }
                    >
                      Case sensitive
                    </Checkbox>
                  </FormField>
                </FormGroup>
              </Box>
            ))}

            <Button variant="outline" onClick={addBlank}>
              Add Blank
            </Button>
          </VStack>
        </Fieldset.Root>

        <FormField label="Explanation">
          <Textarea
            value={formData.explanation}
            onChange={(e) =>
              setFormData({ ...formData, explanation: e.target.value })
            }
            placeholder="Enter explanation for the answers..."
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
        error="Error loading Fill in Blank question data"
        onCancel={onCancel}
      />
    )
  }
})
