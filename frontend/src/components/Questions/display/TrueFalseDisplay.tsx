import type { QuestionResponse } from "@/client";
import { extractQuestionData } from "@/types/questionTypes";
import { Box, HStack, Text, VStack } from "@chakra-ui/react";
import { memo } from "react";
import { ExplanationBox } from "../shared/ExplanationBox";
import { ErrorDisplay } from "./ErrorDisplay";

interface TrueFalseDisplayProps {
  question: QuestionResponse;
  showCorrectAnswer: boolean;
  showExplanation: boolean;
}

export const TrueFalseDisplay = memo(function TrueFalseDisplay({
  question,
  showCorrectAnswer,
  showExplanation,
}: TrueFalseDisplayProps) {
  try {
    const trueFalseData = extractQuestionData(question, "true_false");

    return (
      <VStack gap={4} align="stretch">
        <Box>
          <Text fontSize="md" fontWeight="medium">
            {trueFalseData.question_text}
          </Text>
        </Box>

        <HStack gap={4} justify="center">
          {/* True Box */}
          <Box
            flex={1}
            p={3}
            borderWidth={1}
            borderRadius="md"
            borderColor={
              showCorrectAnswer && trueFalseData.correct_answer
                ? "blue.400"
                : "gray.200"
            }
            bg={
              showCorrectAnswer && trueFalseData.correct_answer
                ? "blue.50"
                : "gray.50"
            }
            textAlign="center"
          >
            <Text fontSize="sm">True</Text>
          </Box>

          {/* False Box */}
          <Box
            flex={1}
            p={3}
            borderWidth={1}
            borderRadius="md"
            borderColor={
              showCorrectAnswer && !trueFalseData.correct_answer
                ? "blue.400"
                : "gray.200"
            }
            bg={
              showCorrectAnswer && !trueFalseData.correct_answer
                ? "blue.50"
                : "gray.50"
            }
            textAlign="center"
          >
            <Text fontSize="sm">False</Text>
          </Box>
        </HStack>

        {trueFalseData.explanation && (
          <ExplanationBox explanation={trueFalseData.explanation} />
        )}
      </VStack>
    );
  } catch (error) {
    return <ErrorDisplay error="Error loading true/false question data" />;
  }
});
