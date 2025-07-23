import { memo } from "react";
import { Box, VStack, HStack, Text, SimpleGrid, Badge, Card } from "@chakra-ui/react";
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
  showCorrectAnswer = false,
  showExplanation = false,
}: CategorizationDisplayProps) {
  try {
    const categorizationData = extractQuestionData(question, "categorization");

    // Create a mapping of item IDs to category names for easy lookup
    const itemToCategoryMap = new Map<string, string>();
    categorizationData.categories.forEach((category) => {
      category.correct_items.forEach((itemId) => {
        itemToCategoryMap.set(itemId, category.name);
      });
    });

    // Combine all items (main items + distractors) for display
    const allItems = [
      ...categorizationData.items,
      ...(categorizationData.distractors || []),
    ];

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
                  {showCorrectAnswer ? (
                    <VStack gap={2} align="stretch">
                      {category.correct_items.map((itemId) => {
                        const item = categorizationData.items.find((i) => i.id === itemId);
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
                  ) : (
                    <Text fontSize="sm" color="gray.500" fontStyle="italic">
                      Items will be placed here
                    </Text>
                  )}
                </Card.Body>
              </Card.Root>
            ))}
          </SimpleGrid>
        </Box>

        {/* Items to Categorize */}
        <Box>
          <Text fontSize="sm" fontWeight="semibold" color="gray.600" mb={3}>
            Items to Categorize:
          </Text>
          <SimpleGrid columns={{ base: 2, md: 3, lg: 4 }} gap={3}>
            {allItems.map((item) => {
              const correctCategory = itemToCategoryMap.get(item.id);
              const isDistractor = !correctCategory;

              return (
                <Box
                  key={item.id}
                  p={3}
                  borderWidth={1}
                  borderRadius="md"
                  borderColor={
                    showCorrectAnswer
                      ? isDistractor
                        ? "red.200"
                        : "green.200"
                      : "gray.200"
                  }
                  bg={
                    showCorrectAnswer
                      ? isDistractor
                        ? "red.50"
                        : "green.50"
                      : "white"
                  }
                  position="relative"
                  cursor={showCorrectAnswer ? "default" : "pointer"}
                  _hover={
                    !showCorrectAnswer
                      ? {
                          borderColor: "blue.300",
                          bg: "blue.50",
                        }
                      : {}
                  }
                >
                  <Text fontSize="sm" textAlign="center">
                    {item.text}
                  </Text>

                  {showCorrectAnswer && (
                    <Badge
                      position="absolute"
                      top={1}
                      right={1}
                      size="sm"
                      colorScheme={isDistractor ? "red" : "green"}
                    >
                      {isDistractor ? "Distractor" : correctCategory}
                    </Badge>
                  )}
                </Box>
              );
            })}
          </SimpleGrid>
        </Box>

        {/* Correct Answer Summary (when showing answers) */}
        {showCorrectAnswer && (
          <Card.Root variant="outline" bg="blue.50">
            <Card.Header>
              <Text fontSize="sm" fontWeight="semibold" color="blue.800">
                Correct Categorization:
              </Text>
            </Card.Header>
            <Card.Body>
              <VStack gap={3} align="stretch">
                {categorizationData.categories.map((category) => (
                  <Box key={category.id}>
                    <Text fontSize="sm" fontWeight="medium" mb={2}>
                      {category.name}:
                    </Text>
                    <HStack wrap="wrap" gap={2}>
                      {category.correct_items.map((itemId) => {
                        const item = categorizationData.items.find((i) => i.id === itemId);
                        return item ? (
                          <Badge key={itemId} colorScheme="green" variant="subtle">
                            {item.text}
                          </Badge>
                        ) : null;
                      })}
                    </HStack>
                  </Box>
                ))}
                {categorizationData.distractors && categorizationData.distractors.length > 0 && (
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={2}>
                      Distractors (don't belong to any category):
                    </Text>
                    <HStack wrap="wrap" gap={2}>
                      {categorizationData.distractors.map((distractor) => (
                        <Badge key={distractor.id} colorScheme="red" variant="subtle">
                          {distractor.text}
                        </Badge>
                      ))}
                    </HStack>
                  </Box>
                )}
              </VStack>
            </Card.Body>
          </Card.Root>
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
