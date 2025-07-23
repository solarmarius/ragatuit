import { memo } from "react";
import { Box, VStack, Text, SimpleGrid, Badge, Card } from "@chakra-ui/react";
import type { QuestionResponse } from "@/client";
import { extractQuestionData } from "@/types/questionTypes";
import { ExplanationBox } from "../shared/ExplanationBox";
import { ErrorDisplay } from "./ErrorDisplay";

interface CategorizationDisplayProps {
  question: QuestionResponse;
  showCorrectAnswer?: boolean;
  showExplanation?: boolean;
}

/**
 * Display component for categorization questions.
 * Shows categories with their assigned items and optional distractors.
 */
function CategorizationDisplayComponent({
  question,
  showCorrectAnswer: _showCorrectAnswer = false, // Always show answers in teacher-facing view
  showExplanation = false,
}: CategorizationDisplayProps) {
  // Note: showCorrectAnswer is kept for API consistency but we always show answers for teachers
  try {
    const categorizationData = extractQuestionData(question, "categorization");

    return (
      <VStack gap={6} align="stretch">
        {/* Question Text */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {categorizationData.question_text}
          </Text>
        </Box>

        {/* Categories Display */}
        <Box>
          <Text fontSize="sm" fontWeight="semibold" color="gray.600" mb={4}>
            Categories:
          </Text>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4} mb={6}>
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
                        (i) => i.id === itemId
                      );
                      return item ? (
                        <Box
                          key={itemId}
                          p={2}
                          bg="green.50"
                          borderRadius="sm"
                          borderLeft="3px solid"
                          borderColor="green.300"
                        >
                          <Text fontSize="sm">{item.text}</Text>
                        </Box>
                      ) : null;
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
              <Text fontSize="sm" fontWeight="semibold" color="gray.600" mb={3}>
                Distractors:
              </Text>
              <SimpleGrid columns={{ base: 2, md: 3, lg: 4 }} gap={3}>
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
                    <Text fontSize="sm" textAlign="center">
                      {distractor.text}
                    </Text>
                  </Box>
                ))}
              </SimpleGrid>
            </Box>
          )}

        {/* Explanation */}
        {showExplanation && categorizationData.explanation && (
          <ExplanationBox explanation={categorizationData.explanation} />
        )}
      </VStack>
    );
  } catch (error) {
    console.error("Error rendering categorization question:", error);
    return <ErrorDisplay error="Error loading categorization question data" />;
  }
}

/**
 * Memoized categorization display component for performance optimization.
 */
export const CategorizationDisplay = memo(CategorizationDisplayComponent);
CategorizationDisplay.displayName = "CategorizationDisplay";
