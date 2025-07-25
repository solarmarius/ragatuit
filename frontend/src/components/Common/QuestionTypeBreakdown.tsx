import { Badge, HStack, Text, VStack } from "@chakra-ui/react";
import { memo } from "react";

import type { Quiz } from "@/client/types.gen";
import {
  getModuleQuestionTypeBreakdown,
  formatQuestionTypeDisplay,
} from "@/lib/utils";

interface QuestionTypeBreakdownProps {
  quiz: Quiz;
  variant?: "compact" | "detailed";
}

/**
 * Component to display question type breakdown for a quiz
 *
 * @param quiz - The quiz object containing selected modules and question batches
 * @param variant - Display style: "compact" shows aggregated counts, "detailed" shows per-module breakdown
 */
export const QuestionTypeBreakdown = memo(function QuestionTypeBreakdown({
  quiz,
  variant = "detailed",
}: QuestionTypeBreakdownProps) {
  const breakdown = getModuleQuestionTypeBreakdown(quiz);
  const moduleEntries = Object.entries(breakdown);

  if (moduleEntries.length === 0) {
    return (
      <Text fontSize="sm" color="gray.500">
        No question types configured
      </Text>
    );
  }

  if (variant === "compact") {
    // Show aggregated counts across all modules
    const aggregatedTypes: Record<string, number> = {};

    moduleEntries.forEach(([_, moduleTypes]) => {
      Object.entries(moduleTypes).forEach(([type, count]) => {
        aggregatedTypes[type] = (aggregatedTypes[type] || 0) + count;
      });
    });

    return (
      <HStack gap={2} flexWrap="wrap">
        {Object.entries(aggregatedTypes).map(([type, count]) => (
          <Badge key={type} variant="solid" size="sm">
            {formatQuestionTypeDisplay(type)}: {count}
          </Badge>
        ))}
      </HStack>
    );
  }

  return (
    <VStack align="stretch" gap={2}>
      {moduleEntries.map(([moduleId, moduleTypes]) => {
        const moduleName =
          (quiz.selected_modules as any)?.[moduleId]?.name ||
          `Module ${moduleId}`;

        return (
          <HStack key={moduleId} justify="space-between" align="flex-start">
            <Text fontSize="sm" fontWeight="medium" color="gray.700">
              {moduleName}:
            </Text>
            <VStack align="flex-end" gap={1}>
              {Object.entries(moduleTypes).map(([type, count]) => (
                <Badge key={type} variant="outline" size="sm">
                  {formatQuestionTypeDisplay(type)}: {count}
                </Badge>
              ))}
            </VStack>
          </HStack>
        );
      })}
    </VStack>
  );
});
