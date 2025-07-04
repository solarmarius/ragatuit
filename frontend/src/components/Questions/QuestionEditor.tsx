/**
 * Question editor components for different question types.
 * These components handle the editing of questions in a polymorphic way.
 */

import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { Checkbox } from "@/components/ui/checkbox"
import { Field } from "@/components/ui/field"
import { Radio, RadioGroup } from "@/components/ui/radio"
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
import { useState } from "react"

interface QuestionEditorProps {
  question: QuestionResponse
  onSave: (updateData: QuestionUpdateRequest) => void
  onCancel: () => void
  isLoading?: boolean
}

export function QuestionEditor({
  question,
  onSave,
  onCancel,
  isLoading = false,
}: QuestionEditorProps) {
  switch (question.question_type) {
    case "multiple_choice":
      return (
        <MCQQuestionEditor
          question={question}
          onSave={onSave}
          onCancel={onCancel}
          isLoading={isLoading}
        />
      )
    case "true_false":
      return (
        <TrueFalseQuestionEditor
          question={question}
          onSave={onSave}
          onCancel={onCancel}
          isLoading={isLoading}
        />
      )
    case "short_answer":
      return (
        <ShortAnswerQuestionEditor
          question={question}
          onSave={onSave}
          onCancel={onCancel}
          isLoading={isLoading}
        />
      )
    case "essay":
      return (
        <EssayQuestionEditor
          question={question}
          onSave={onSave}
          onCancel={onCancel}
          isLoading={isLoading}
        />
      )
    case "fill_in_blank":
      return (
        <FillInBlankQuestionEditor
          question={question}
          onSave={onSave}
          onCancel={onCancel}
          isLoading={isLoading}
        />
      )
    default:
      return (
        <UnsupportedQuestionEditor
          questionType={question.question_type}
          onCancel={onCancel}
        />
      )
  }
}

interface TypedQuestionEditorProps {
  question: QuestionResponse
  onSave: (updateData: QuestionUpdateRequest) => void
  onCancel: () => void
  isLoading: boolean
}

function MCQQuestionEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: TypedQuestionEditorProps) {
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
      <VStack gap={4} align="stretch">
        <Field label="Question Text">
          <Textarea
            value={formData.questionText}
            onChange={(e) =>
              setFormData({ ...formData, questionText: e.target.value })
            }
            placeholder="Enter question text..."
            rows={3}
          />
        </Field>

        <Fieldset.Root>
          <Fieldset.Legend>Answer Options</Fieldset.Legend>
          <VStack gap={3} align="stretch">
            <Field label="Option A">
              <Input
                value={formData.optionA}
                onChange={(e) =>
                  setFormData({ ...formData, optionA: e.target.value })
                }
                placeholder="Enter option A..."
              />
            </Field>
            <Field label="Option B">
              <Input
                value={formData.optionB}
                onChange={(e) =>
                  setFormData({ ...formData, optionB: e.target.value })
                }
                placeholder="Enter option B..."
              />
            </Field>
            <Field label="Option C">
              <Input
                value={formData.optionC}
                onChange={(e) =>
                  setFormData({ ...formData, optionC: e.target.value })
                }
                placeholder="Enter option C..."
              />
            </Field>
            <Field label="Option D">
              <Input
                value={formData.optionD}
                onChange={(e) =>
                  setFormData({ ...formData, optionD: e.target.value })
                }
                placeholder="Enter option D..."
              />
            </Field>
          </VStack>
        </Fieldset.Root>

        <Field label="Correct Answer">
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
        </Field>

        <Field label="Explanation (Optional)">
          <Textarea
            value={formData.explanation}
            onChange={(e) =>
              setFormData({ ...formData, explanation: e.target.value })
            }
            placeholder="Enter explanation for the answer..."
            rows={2}
          />
        </Field>

        <HStack gap={3} justify="end">
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button colorScheme="blue" onClick={handleSave} loading={isLoading}>
            Save Changes
          </Button>
        </HStack>
      </VStack>
    )
  } catch (error) {
    return (
      <ErrorQuestionEditor
        error="Error loading MCQ question data"
        onCancel={onCancel}
      />
    )
  }
}

function TrueFalseQuestionEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: TypedQuestionEditorProps) {
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
      <VStack gap={4} align="stretch">
        <Field label="Question Text">
          <Textarea
            value={formData.questionText}
            onChange={(e) =>
              setFormData({ ...formData, questionText: e.target.value })
            }
            placeholder="Enter question text..."
            rows={3}
          />
        </Field>

        <Field label="Correct Answer">
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
        </Field>

        <Field label="Explanation (Optional)">
          <Textarea
            value={formData.explanation}
            onChange={(e) =>
              setFormData({ ...formData, explanation: e.target.value })
            }
            placeholder="Enter explanation for the answer..."
            rows={2}
          />
        </Field>

        <HStack gap={3} justify="end">
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button colorScheme="blue" onClick={handleSave} loading={isLoading}>
            Save Changes
          </Button>
        </HStack>
      </VStack>
    )
  } catch (error) {
    return (
      <ErrorQuestionEditor
        error="Error loading True/False question data"
        onCancel={onCancel}
      />
    )
  }
}

function ShortAnswerQuestionEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: TypedQuestionEditorProps) {
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
      <VStack gap={4} align="stretch">
        <Field label="Question Text">
          <Textarea
            value={formData.questionText}
            onChange={(e) =>
              setFormData({ ...formData, questionText: e.target.value })
            }
            placeholder="Enter question text..."
            rows={3}
          />
        </Field>

        <Field label="Correct Answer">
          <Input
            value={formData.correctAnswer}
            onChange={(e) =>
              setFormData({ ...formData, correctAnswer: e.target.value })
            }
            placeholder="Enter the correct answer..."
          />
        </Field>

        <Field label="Answer Variations (Optional)">
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
        </Field>

        <Field>
          <Checkbox
            checked={formData.caseSensitive}
            onCheckedChange={(e) =>
              setFormData({ ...formData, caseSensitive: !!e.checked })
            }
          >
            Case sensitive
          </Checkbox>
        </Field>

        <Field label="Explanation (Optional)">
          <Textarea
            value={formData.explanation}
            onChange={(e) =>
              setFormData({ ...formData, explanation: e.target.value })
            }
            placeholder="Enter explanation for the answer..."
            rows={2}
          />
        </Field>

        <HStack gap={3} justify="end">
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button colorScheme="blue" onClick={handleSave} loading={isLoading}>
            Save Changes
          </Button>
        </HStack>
      </VStack>
    )
  } catch (error) {
    return (
      <ErrorQuestionEditor
        error="Error loading Short Answer question data"
        onCancel={onCancel}
      />
    )
  }
}

function EssayQuestionEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: TypedQuestionEditorProps) {
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
      <VStack gap={4} align="stretch">
        <Field label="Question Text">
          <Textarea
            value={formData.questionText}
            onChange={(e) =>
              setFormData({ ...formData, questionText: e.target.value })
            }
            placeholder="Enter question text..."
            rows={3}
          />
        </Field>

        <Field label="Expected Length (Optional)">
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
        </Field>

        <Field label="Maximum Words (Optional)">
          <Input
            type="number"
            value={formData.maxWords}
            onChange={(e) =>
              setFormData({ ...formData, maxWords: e.target.value })
            }
            placeholder="Enter maximum word count..."
          />
        </Field>

        <Field label="Grading Rubric (Optional)">
          <Textarea
            value={formData.gradingRubric}
            onChange={(e) =>
              setFormData({ ...formData, gradingRubric: e.target.value })
            }
            placeholder="Enter grading criteria and rubric..."
            rows={4}
          />
        </Field>

        <Field label="Sample Answer (Optional)">
          <Textarea
            value={formData.sampleAnswer}
            onChange={(e) =>
              setFormData({ ...formData, sampleAnswer: e.target.value })
            }
            placeholder="Enter a sample answer or key points..."
            rows={4}
          />
        </Field>

        <HStack gap={3} justify="end">
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button colorScheme="blue" onClick={handleSave} loading={isLoading}>
            Save Changes
          </Button>
        </HStack>
      </VStack>
    )
  } catch (error) {
    return (
      <ErrorQuestionEditor
        error="Error loading Essay question data"
        onCancel={onCancel}
      />
    )
  }
}

function FillInBlankQuestionEditor({
  question,
  onSave,
  onCancel,
  isLoading,
}: TypedQuestionEditorProps) {
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

    const updateBlank = (index: number, field: string, value: any) => {
      const updatedBlanks = [...formData.blanks]
      updatedBlanks[index] = { ...updatedBlanks[index], [field]: value }
      setFormData({ ...formData, blanks: updatedBlanks })
    }

    return (
      <VStack gap={4} align="stretch">
        <Field label="Question Text">
          <Textarea
            value={formData.questionText}
            onChange={(e) =>
              setFormData({ ...formData, questionText: e.target.value })
            }
            placeholder="Enter question text with blanks marked..."
            rows={3}
          />
        </Field>

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
                <VStack gap={3} align="stretch">
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

                  <Field label="Correct Answer">
                    <Input
                      value={blank.correctAnswer}
                      onChange={(e) =>
                        updateBlank(index, "correctAnswer", e.target.value)
                      }
                      placeholder="Enter correct answer..."
                    />
                  </Field>

                  <Field label="Answer Variations (Optional)">
                    <Input
                      value={blank.answerVariations}
                      onChange={(e) =>
                        updateBlank(index, "answerVariations", e.target.value)
                      }
                      placeholder="Enter variations separated by commas..."
                    />
                  </Field>

                  <Field>
                    <Checkbox
                      checked={blank.caseSensitive}
                      onCheckedChange={(e) =>
                        updateBlank(index, "caseSensitive", !!e.checked)
                      }
                    >
                      Case sensitive
                    </Checkbox>
                  </Field>
                </VStack>
              </Box>
            ))}

            <Button variant="outline" onClick={addBlank}>
              Add Blank
            </Button>
          </VStack>
        </Fieldset.Root>

        <Field label="Explanation (Optional)">
          <Textarea
            value={formData.explanation}
            onChange={(e) =>
              setFormData({ ...formData, explanation: e.target.value })
            }
            placeholder="Enter explanation for the answers..."
            rows={2}
          />
        </Field>

        <HStack gap={3} justify="end">
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button colorScheme="blue" onClick={handleSave} loading={isLoading}>
            Save Changes
          </Button>
        </HStack>
      </VStack>
    )
  } catch (error) {
    return (
      <ErrorQuestionEditor
        error="Error loading Fill in Blank question data"
        onCancel={onCancel}
      />
    )
  }
}

function UnsupportedQuestionEditor({
  questionType,
  onCancel,
}: {
  questionType: string
  onCancel: () => void
}) {
  return (
    <VStack gap={4} align="stretch">
      <Box
        p={4}
        bg="orange.50"
        borderRadius="md"
        borderLeft="4px solid"
        borderColor="orange.200"
      >
        <Text fontSize="md" fontWeight="medium" color="orange.700" mb={1}>
          Unsupported Question Type
        </Text>
        <Text fontSize="sm" color="orange.600">
          Editing for question type "{questionType}" is not yet supported.
        </Text>
      </Box>

      <HStack gap={3} justify="end">
        <Button variant="outline" onClick={onCancel}>
          Close
        </Button>
      </HStack>
    </VStack>
  )
}

function ErrorQuestionEditor({
  error,
  onCancel,
}: {
  error: string
  onCancel: () => void
}) {
  return (
    <VStack gap={4} align="stretch">
      <Box
        p={4}
        bg="red.50"
        borderRadius="md"
        borderLeft="4px solid"
        borderColor="red.200"
      >
        <Text fontSize="md" fontWeight="medium" color="red.700" mb={1}>
          Editor Error
        </Text>
        <Text fontSize="sm" color="red.600">
          {error}
        </Text>
      </Box>

      <HStack gap={3} justify="end">
        <Button variant="outline" onClick={onCancel}>
          Close
        </Button>
      </HStack>
    </VStack>
  )
}
