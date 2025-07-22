import type { QuestionResponse } from "@/client";
import { extractQuestionData } from "@/types/questionTypes";
import { Box, VStack, HStack, Text, Grid, Badge } from "@chakra-ui/react";
import { memo } from "react";
import { ExplanationBox } from "../shared/ExplanationBox";
import { ErrorDisplay } from "./ErrorDisplay";

interface MatchingDisplayProps {
  question: QuestionResponse;
  showCorrectAnswer: boolean;
  showExplanation: boolean;
}

export const MatchingDisplay = memo(function MatchingDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: MatchingDisplayProps) {
  try {
    const matchingData = extractQuestionData(question, "matching");

    // Combine correct answers with distractors for answer column
    const allAnswers = [
      ...matchingData.pairs.map((pair) => pair.answer),
      ...(matchingData.distractors || []),
    ];

    // Shuffle answers if not showing correct answers (for display purposes)
    const displayAnswers = showCorrectAnswer
      ? allAnswers
      : [...allAnswers].sort(() => Math.random() - 0.5);

    return (
      <VStack gap={4} align="stretch">
        {/* Question Text */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>
            {matchingData.question_text}
          </Text>
        </Box>

        {/* Matching Interface */}
        <Box>
          <Grid templateColumns="1fr 1fr" gap={6}>
            {/* Left Column - Questions */}
            <VStack gap={3} align="stretch">
              <Text fontSize="sm" fontWeight="semibold" color="gray.600">
                Match These:
              </Text>
              {matchingData.pairs.map((pair, index) => (
                <Box
                  key={index}
                  p={3}
                  borderWidth={1}
                  borderColor="gray.200"
                  borderRadius="md"
                  bg="gray.50"
                >
                  <Text fontSize="sm">{pair.question}</Text>
                </Box>
              ))}
            </VStack>

            {/* Right Column - Answers */}
            <VStack gap={3} align="stretch">
              <Text fontSize="sm" fontWeight="semibold" color="gray.600">
                To These:
              </Text>
              {displayAnswers.map((answer, index) => {
                // Check if this is a correct answer
                const isCorrectAnswer = matchingData.pairs.some(
                  (pair) => pair.answer === answer
                );
                const isDistractor = !isCorrectAnswer;

                return (
                  <Box
                    key={index}
                    p={3}
                    borderWidth={1}
                    borderColor={
                      showCorrectAnswer && isCorrectAnswer
                        ? "green.300"
                        : showCorrectAnswer && isDistractor
                          ? "red.200"
                          : "gray.200"
                    }
                    borderRadius="md"
                    bg={
                      showCorrectAnswer && isCorrectAnswer
                        ? "green.50"
                        : showCorrectAnswer && isDistractor
                          ? "red.50"
                          : "white"
                    }
                    position="relative"
                  >
                    <Text fontSize="sm">{answer}</Text>

                    {showCorrectAnswer && (
                      <Badge
                        position="absolute"
                        top={1}
                        right={1}
                        size="sm"
                        colorScheme={isCorrectAnswer ? "green" : "red"}
                      >
                        {isCorrectAnswer ? "Correct" : "Distractor"}
                      </Badge>
                    )}
                  </Box>
                );
              })}
            </VStack>
          </Grid>

          {/* Correct Matches Display (when showing answers) */}
          {showCorrectAnswer && (
            <Box mt={6} p={4} bg="blue.50" borderRadius="md">
              <Text fontSize="sm" fontWeight="semibold" mb={3} color="blue.800">
                Correct Matches:
              </Text>
              <VStack gap={2} align="stretch">
                {matchingData.pairs.map((pair, index) => (
                  <HStack key={index} gap={3}>
                    <Box flex={1} p={2} bg="white" borderRadius="sm">
                      <Text fontSize="sm">{pair.question}</Text>
                    </Box>
                    <Text fontSize="sm" color="blue.600" fontWeight="medium">
                      →
                    </Text>
                    <Box flex={1} p={2} bg="white" borderRadius="sm">
                      <Text fontSize="sm">{pair.answer}</Text>
                    </Box>
                  </HStack>
                ))}
              </VStack>
            </Box>
          )}
        </Box>

        {/* Explanation */}
        {showExplanation && matchingData.explanation && (
          <ExplanationBox explanation={matchingData.explanation} />
        )}
      </VStack>
    );
  } catch (error) {
    console.error("Error rendering matching question:", error);
    return <ErrorDisplay error="Error loading matching question data" />;
  }
});
