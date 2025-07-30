import { Box, Card, SimpleGrid, Text, VStack } from "@chakra-ui/react"
import { memo } from "react"

import { QUESTION_TYPES, QUESTION_TYPE_LABELS } from "@/lib/constants"

interface QuestionTypeSelectorProps {
  /** Callback when a question type is selected */
  onSelectType: (questionType: string) => void
  /** Whether the selection process is loading */
  isLoading?: boolean
}

/**
 * Question type selector component that displays all available question types
 * as selectable cards. This is the first step in the manual question creation workflow.
 *
 * @example
 * ```tsx
 * <QuestionTypeSelector
 *   onSelectType={(type) => setSelectedType(type)}
 *   isLoading={false}
 * />
 * ```
 */
export const QuestionTypeSelector = memo(function QuestionTypeSelector({
  onSelectType,
  isLoading = false,
}: QuestionTypeSelectorProps) {
  // Define question types with descriptions for better UX
  const questionTypeOptions = [
    {
      type: QUESTION_TYPES.MULTIPLE_CHOICE,
      label: QUESTION_TYPE_LABELS.multiple_choice,
      description: "Choose the correct answer from 4 options (A, B, C, D)",
      icon: "📝",
    },
    {
      type: QUESTION_TYPES.TRUE_FALSE,
      label: QUESTION_TYPE_LABELS.true_false,
      description: "Simple true or false statements",
      icon: "✓✗",
    },
    {
      type: QUESTION_TYPES.FILL_IN_BLANK,
      label: QUESTION_TYPE_LABELS.fill_in_blank,
      description: "Complete sentences with missing words",
      icon: "📄",
    },
    {
      type: QUESTION_TYPES.MATCHING,
      label: QUESTION_TYPE_LABELS.matching,
      description: "Match questions to their correct answers",
      icon: "🔗",
    },
    {
      type: QUESTION_TYPES.CATEGORIZATION,
      label: QUESTION_TYPE_LABELS.categorization,
      description: "Group items into appropriate categories",
      icon: "📊",
    },
  ]

  return (
    <VStack gap={6} align="stretch">
      <Box>
        <Text fontSize="xl" fontWeight="bold" mb={2}>
          Select Question Type
        </Text>
        <Text color="gray.600">
          Choose the type of question you want to create.
        </Text>
      </Box>

      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
        {questionTypeOptions.map((option) => (
          <Card.Root
            key={option.type}
            variant="outline"
            cursor="pointer"
            transition="all 0.2s"
            _hover={{
              borderColor: "blue.300",
              shadow: "md",
            }}
            onClick={() => !isLoading && onSelectType(option.type)}
            opacity={isLoading ? 0.6 : 1}
          >
            <Card.Body p={4}>
              <VStack gap={3} align="center" textAlign="center">
                <Text fontSize="2xl" role="img" aria-label={option.label}>
                  {option.icon}
                </Text>
                <Text fontWeight="semibold" fontSize="md">
                  {option.label}
                </Text>
                <Text fontSize="sm" color="gray.600" lineHeight="1.4">
                  {option.description}
                </Text>
              </VStack>
            </Card.Body>
          </Card.Root>
        ))}
      </SimpleGrid>

      <Box>
        <Text fontSize="sm" color="gray.500" textAlign="center">
          All question types support real-time validation and will be added to
          your quiz in pending status for review.
        </Text>
      </Box>
    </VStack>
  )
})
