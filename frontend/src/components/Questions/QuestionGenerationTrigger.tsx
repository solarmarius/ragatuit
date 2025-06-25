import { Box, Button, Card, HStack, Text, VStack } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { MdAutoAwesome } from "react-icons/md"

import { type Quiz, QuizService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"

interface QuestionGenerationTriggerProps {
  quiz: Quiz
}

export function QuestionGenerationTrigger({
  quiz,
}: QuestionGenerationTriggerProps) {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const queryClient = useQueryClient()

  const triggerGenerationMutation = useMutation({
    mutationFn: async () => {
      return await QuizService.triggerQuestionGeneration({ quizId: quiz.id })
    },
    onSuccess: () => {
      showSuccessToast("Question generation started")
      queryClient.invalidateQueries({ queryKey: ["quiz", quiz.id] })
    },
    onError: (error: any) => {
      const message =
        error?.body?.detail || "Failed to start question generation"
      showErrorToast(message)
    },
  })

  // Don't show if content extraction isn't completed
  if (quiz.content_extraction_status !== "completed") {
    return null
  }

  // Don't show if generation is already processing or completed
  if (
    quiz.llm_generation_status === "processing" ||
    quiz.llm_generation_status === "completed"
  ) {
    return null
  }

  return (
    <Card.Root>
      <Card.Body>
        <VStack gap={4} align="stretch">
          <Box textAlign="center">
            <Text fontSize="xl" fontWeight="bold" mb={2}>
              Ready to Generate Questions
            </Text>
            <Text color="gray.600" mb={4}>
              Content extraction is complete. Click below to start generating{" "}
              {quiz.question_count} multiple-choice questions.
            </Text>
          </Box>

          <Box
            p={4}
            bg="blue.50"
            borderRadius="md"
            border="1px solid"
            borderColor="blue.200"
          >
            <VStack gap={2}>
              <Text fontSize="sm" fontWeight="medium" color="blue.700">
                Generation Settings
              </Text>
              <HStack gap={4} fontSize="sm" color="blue.600">
                <Text>Questions: {quiz.question_count}</Text>
                <Text>Model: {quiz.llm_model}</Text>
                <Text>Temperature: {quiz.llm_temperature}</Text>
              </HStack>
            </VStack>
          </Box>

          <Button
            size="lg"
            colorScheme="blue"
            onClick={() => triggerGenerationMutation.mutate()}
            loading={triggerGenerationMutation.isPending}
            width="100%"
          >
            <MdAutoAwesome />
            Generate Questions
          </Button>

          {quiz.llm_generation_status === "failed" && (
            <Box
              p={3}
              bg="red.50"
              borderRadius="md"
              border="1px solid"
              borderColor="red.200"
            >
              <Text fontSize="sm" color="red.700" textAlign="center">
                Previous generation attempt failed. Click "Generate Questions"
                to retry.
              </Text>
            </Box>
          )}
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
