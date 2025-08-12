import type { QuestionResponse } from "@/client"
import { ErrorState } from "@/components/Common"
import { extractQuestionData } from "@/types/questionTypes"
import { Badge, Box, Card, SimpleGrid, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"
import { ExplanationBox } from "../shared/ExplanationBox"

interface CategorizationDisplayProps {
  question: QuestionResponse
  showCorrectAnswer?: boolean
}

/**
 * Display component for categorization questions.
 * Shows categories with their assigned items and optional distractors.
 */
function CategorizationDisplayComponent({
  question,
  showCorrectAnswer: _showCorrectAnswer = false, // Always show answers in teacher-facing view
}: CategorizationDisplayProps) {
  // Note: showCorrectAnswer is kept for API consistency but we always show answers for teachers
  try {
    const categorizationData = extractQuestionData(question, "categorization")

    return (
      <VStack gap={6} align="stretch">
        {/* Question Text */}
        <Box>
          <Text fontSize="md" fontWeight="medium">
            {categorizationData.question_text}
          </Text>
        </Box>

        {/* Categories Display */}
        <Box>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
            {categorizationData.categories.map((category) => (
              <Card.Root key={category.id} variant="outline">
                <Card.Header>
                  <Text fontSize="sm" fontWeight="semibold">
                    {category.name}
                  </Text>
                </Card.Header>
                <Card.Body>
                  <VStack gap={2} align="stretch">
                    {category.correct_items.map((itemId) => {
                      const item = categorizationData.items.find(
                        (i) => i.id === itemId,
                      )
                      return item ? (
                        <Box
                          key={itemId}
                          flex={1}
                          p={3}
                          borderWidth={1}
                          borderColor="green.300"
                          bg="green.50"
                          borderRadius="md"
                        >
                          <Text fontSize="sm">{item.text}</Text>
                        </Box>
                      ) : null
                    })}
                  </VStack>
                </Card.Body>
              </Card.Root>
            ))}
          </SimpleGrid>
        </Box>

        {/* Distractors */}
        {categorizationData.distractors &&
          categorizationData.distractors.length > 0 && (
            <Box>
              <VStack gap={2} align="stretch">
                {categorizationData.distractors.map((distractor) => (
                  <Box
                    key={distractor.id}
                    p={3}
                    borderWidth={1}
                    borderRadius="md"
                    borderColor="red.200"
                    bg="red.50"
                    position="relative"
                  >
                    <Text fontSize="sm">{distractor.text}</Text>
                    <Badge
                      position="absolute"
                      top={1}
                      right={1}
                      size="sm"
                      colorScheme="red"
                    >
                      Distractor
                    </Badge>
                  </Box>
                ))}
              </VStack>
            </Box>
          )}

        {/* Explanation */}
        {categorizationData.explanation && (
          <ExplanationBox explanation={categorizationData.explanation} />
        )}
      </VStack>
    )
  } catch (error) {
    console.error("Error rendering categorization question:", error)
    return (
      <ErrorState
        title="Display Error"
        message="Error loading categorization question data"
        variant="inline"
        showRetry={false}
      />
    )
  }
}

/**
 * Memoized categorization display component for performance optimization.
 */
export const CategorizationDisplay = memo(CategorizationDisplayComponent)
CategorizationDisplay.displayName = "CategorizationDisplay"
