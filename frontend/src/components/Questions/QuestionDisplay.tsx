/**
 * Question display components for different question types.
 * These components handle the display of questions in a polymorphic way.
 */

import type { QuestionResponse } from "@/client"
import { extractQuestionData } from "@/types/questionTypes"
import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"

interface QuestionDisplayProps {
  question: QuestionResponse
  showCorrectAnswer?: boolean
  showExplanation?: boolean
}

export function QuestionDisplay({
  question,
  showCorrectAnswer = false,
  showExplanation = false,
}: QuestionDisplayProps) {
  switch (question.question_type) {
    case "multiple_choice":
      return (
        <MCQQuestionDisplay
          question={question}
          showCorrectAnswer={showCorrectAnswer}
          showExplanation={showExplanation}
        />
      )
    case "true_false":
      return (
        <TrueFalseQuestionDisplay
          question={question}
          showCorrectAnswer={showCorrectAnswer}
          showExplanation={showExplanation}
        />
      )
    case "short_answer":
      return (
        <ShortAnswerQuestionDisplay
          question={question}
          showCorrectAnswer={showCorrectAnswer}
          showExplanation={showExplanation}
        />
      )
    case "essay":
      return (
        <EssayQuestionDisplay
          question={question}
          showCorrectAnswer={showCorrectAnswer}
          showExplanation={showExplanation}
        />
      )
    case "fill_in_blank":
      return (
        <FillInBlankQuestionDisplay
          question={question}
          showCorrectAnswer={showCorrectAnswer}
          showExplanation={showExplanation}
        />
      )
    default:
      return (
        <UnsupportedQuestionDisplay questionType={question.question_type} />
      )
  }
}

interface TypedQuestionDisplayProps {
  question: QuestionResponse
  showCorrectAnswer: boolean
  showExplanation: boolean
}

function MCQQuestionDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: TypedQuestionDisplayProps) {
  try {
    const mcqData = extractQuestionData(question, "multiple_choice")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {mcqData.question_text}
          </Text>
        </Box>

        <VStack gap={2} align="stretch">
          {[
            { key: "A", text: mcqData.option_a },
            { key: "B", text: mcqData.option_b },
            { key: "C", text: mcqData.option_c },
            { key: "D", text: mcqData.option_d },
          ].map((option) => (
            <HStack
              key={option.key}
              p={3}
              bg={
                showCorrectAnswer && option.key === mcqData.correct_answer
                  ? "green.50"
                  : "gray.50"
              }
              borderRadius="md"
              border={
                showCorrectAnswer && option.key === mcqData.correct_answer
                  ? "2px solid"
                  : "1px solid"
              }
              borderColor={
                showCorrectAnswer && option.key === mcqData.correct_answer
                  ? "green.200"
                  : "gray.200"
              }
            >
              <Badge
                colorScheme={
                  showCorrectAnswer && option.key === mcqData.correct_answer
                    ? "green"
                    : "gray"
                }
                variant="solid"
                size="sm"
              >
                {option.key}
              </Badge>
              <Text flex={1}>{option.text}</Text>
              {showCorrectAnswer && option.key === mcqData.correct_answer && (
                <Badge colorScheme="green" variant="subtle" size="sm">
                  Correct
                </Badge>
              )}
            </HStack>
          ))}
        </VStack>

        {showExplanation && mcqData.explanation && (
          <Box
            p={3}
            bg="blue.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="blue.200"
          >
            <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={1}>
              Explanation:
            </Text>
            <Text fontSize="sm" color="blue.600">
              {mcqData.explanation}
            </Text>
          </Box>
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorQuestionDisplay error="Error loading MCQ question data" />
  }
}

function TrueFalseQuestionDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: TypedQuestionDisplayProps) {
  try {
    const tfData = extractQuestionData(question, "true_false")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {tfData.question_text}
          </Text>
        </Box>

        <VStack gap={2} align="stretch">
          {[
            { key: "True", value: true },
            { key: "False", value: false },
          ].map((option) => (
            <HStack
              key={option.key}
              p={3}
              bg={
                showCorrectAnswer && option.value === tfData.correct_answer
                  ? "green.50"
                  : "gray.50"
              }
              borderRadius="md"
              border={
                showCorrectAnswer && option.value === tfData.correct_answer
                  ? "2px solid"
                  : "1px solid"
              }
              borderColor={
                showCorrectAnswer && option.value === tfData.correct_answer
                  ? "green.200"
                  : "gray.200"
              }
            >
              <Badge
                colorScheme={
                  showCorrectAnswer && option.value === tfData.correct_answer
                    ? "green"
                    : "gray"
                }
                variant="solid"
                size="sm"
              >
                {option.key}
              </Badge>
              <Text flex={1}>{option.key}</Text>
              {showCorrectAnswer && option.value === tfData.correct_answer && (
                <Badge colorScheme="green" variant="subtle" size="sm">
                  Correct
                </Badge>
              )}
            </HStack>
          ))}
        </VStack>

        {showExplanation && tfData.explanation && (
          <Box
            p={3}
            bg="blue.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="blue.200"
          >
            <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={1}>
              Explanation:
            </Text>
            <Text fontSize="sm" color="blue.600">
              {tfData.explanation}
            </Text>
          </Box>
        )}
      </VStack>
    )
  } catch (error) {
    return (
      <ErrorQuestionDisplay error="Error loading True/False question data" />
    )
  }
}

function ShortAnswerQuestionDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: TypedQuestionDisplayProps) {
  try {
    const saData = extractQuestionData(question, "short_answer")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {saData.question_text}
          </Text>
        </Box>

        {showCorrectAnswer && (
          <Box
            p={3}
            bg="green.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="green.200"
          >
            <Text fontSize="sm" fontWeight="medium" color="green.700" mb={1}>
              Correct Answer:
            </Text>
            <Text fontSize="sm" color="green.600" fontFamily="mono">
              {saData.correct_answer}
            </Text>
            {saData.answer_variations &&
              saData.answer_variations.length > 0 && (
                <>
                  <Text
                    fontSize="sm"
                    fontWeight="medium"
                    color="green.700"
                    mt={2}
                    mb={1}
                  >
                    Accepted Variations:
                  </Text>
                  <Text fontSize="sm" color="green.600" fontFamily="mono">
                    {saData.answer_variations.join(", ")}
                  </Text>
                </>
              )}
            {saData.case_sensitive && (
              <Text fontSize="xs" color="orange.600" mt={1}>
                (Case sensitive)
              </Text>
            )}
          </Box>
        )}

        {showExplanation && saData.explanation && (
          <Box
            p={3}
            bg="blue.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="blue.200"
          >
            <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={1}>
              Explanation:
            </Text>
            <Text fontSize="sm" color="blue.600">
              {saData.explanation}
            </Text>
          </Box>
        )}
      </VStack>
    )
  } catch (error) {
    return (
      <ErrorQuestionDisplay error="Error loading Short Answer question data" />
    )
  }
}

function EssayQuestionDisplay({
  question,
  showCorrectAnswer,
}: TypedQuestionDisplayProps) {
  try {
    const essayData = extractQuestionData(question, "essay")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {essayData.question_text}
          </Text>
        </Box>

        {essayData.expected_length && (
          <Box>
            <Text fontSize="sm" color="gray.600">
              Expected length:{" "}
              <Badge size="sm" colorScheme="blue">
                {essayData.expected_length}
              </Badge>
            </Text>
          </Box>
        )}

        {essayData.max_words && (
          <Box>
            <Text fontSize="sm" color="gray.600">
              Maximum words:{" "}
              <Badge size="sm" colorScheme="orange">
                {essayData.max_words}
              </Badge>
            </Text>
          </Box>
        )}

        {showCorrectAnswer && essayData.grading_rubric && (
          <Box
            p={3}
            bg="green.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="green.200"
          >
            <Text fontSize="sm" fontWeight="medium" color="green.700" mb={1}>
              Grading Rubric:
            </Text>
            <Text fontSize="sm" color="green.600" whiteSpace="pre-wrap">
              {essayData.grading_rubric}
            </Text>
          </Box>
        )}

        {showCorrectAnswer && essayData.sample_answer && (
          <Box
            p={3}
            bg="blue.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="blue.200"
          >
            <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={1}>
              Sample Answer:
            </Text>
            <Text fontSize="sm" color="blue.600" whiteSpace="pre-wrap">
              {essayData.sample_answer}
            </Text>
          </Box>
        )}
      </VStack>
    )
  } catch (error) {
    return <ErrorQuestionDisplay error="Error loading Essay question data" />
  }
}

function FillInBlankQuestionDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: TypedQuestionDisplayProps) {
  try {
    const fibData = extractQuestionData(question, "fill_in_blank")

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {fibData.question_text}
          </Text>
        </Box>

        {showCorrectAnswer && (
          <Box
            p={3}
            bg="green.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="green.200"
          >
            <Text fontSize="sm" fontWeight="medium" color="green.700" mb={2}>
              Correct Answers:
            </Text>
            <VStack gap={2} align="stretch">
              {fibData.blanks.map((blank, index) => (
                <Box key={index}>
                  <Text fontSize="sm" color="green.600">
                    <strong>Blank {blank.position}:</strong>{" "}
                    <Text as="span" fontFamily="mono">
                      {blank.correct_answer}
                    </Text>
                  </Text>
                  {blank.answer_variations &&
                    blank.answer_variations.length > 0 && (
                      <Text fontSize="xs" color="green.500" ml={4}>
                        Variations: {blank.answer_variations.join(", ")}
                      </Text>
                    )}
                  {blank.case_sensitive && (
                    <Text fontSize="xs" color="orange.600" ml={4}>
                      (Case sensitive)
                    </Text>
                  )}
                </Box>
              ))}
            </VStack>
          </Box>
        )}

        {showExplanation && fibData.explanation && (
          <Box
            p={3}
            bg="blue.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="blue.200"
          >
            <Text fontSize="sm" fontWeight="medium" color="blue.700" mb={1}>
              Explanation:
            </Text>
            <Text fontSize="sm" color="blue.600">
              {fibData.explanation}
            </Text>
          </Box>
        )}
      </VStack>
    )
  } catch (error) {
    return (
      <ErrorQuestionDisplay error="Error loading Fill in Blank question data" />
    )
  }
}

function UnsupportedQuestionDisplay({
  questionType,
}: { questionType: string }) {
  return (
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
        Question type "{questionType}" is not yet supported in the display
        interface.
      </Text>
    </Box>
  )
}

function ErrorQuestionDisplay({ error }: { error: string }) {
  return (
    <Box
      p={4}
      bg="red.50"
      borderRadius="md"
      borderLeft="4px solid"
      borderColor="red.200"
    >
      <Text fontSize="md" fontWeight="medium" color="red.700" mb={1}>
        Display Error
      </Text>
      <Text fontSize="sm" color="red.600">
        {error}
      </Text>
    </Box>
  )
}
