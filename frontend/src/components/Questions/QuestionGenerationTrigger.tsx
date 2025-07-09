import { Box, Button, Card, HStack, Text, VStack } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { MdAutoAwesome } from "react-icons/md"

import { type GenerationRequest, QuestionsService, type Quiz } from "@/client"
import { useCustomToast, useErrorHandler } from "@/hooks/common"
import { QUIZ_STATUS } from "@/lib/constants"

interface QuestionGenerationTriggerProps {
  quiz: Quiz
}

export function QuestionGenerationTrigger({
  quiz,
}: QuestionGenerationTriggerProps) {
  const { showSuccessToast } = useCustomToast()
  const { handleError } = useErrorHandler()
  const queryClient = useQueryClient()

  const triggerGenerationMutation = useMutation({
    mutationFn: async () => {
      if (!quiz.id) {
        throw new Error("Quiz ID is required")
      }

      const generationRequest: GenerationRequest = {
        quiz_id: quiz.id,
        question_type: "multiple_choice",
        target_count: quiz.question_count || 10,
        difficulty: null,
        tags: null,
        custom_instructions: null,
        provider_name: null,
        workflow_name: null,
        template_name: null,
      }

      return await QuestionsService.generateQuestions({
        quizId: quiz.id,
        requestBody: generationRequest,
      })
    },
    onSuccess: () => {
      showSuccessToast("Question generation started")
      queryClient.invalidateQueries({ queryKey: ["quiz", quiz.id] })
    },
    onError: handleError,
  })

  // Don't show if quiz ID is missing
  if (!quiz.id) {
    return null
  }

  // Only show if LLM generation has failed and user can retry
  if (
    quiz.status !== QUIZ_STATUS.FAILED ||
    (quiz.failure_reason !== "llm_generation_error" &&
      quiz.failure_reason !== "no_questions_generated")
  ) {
    return null
  }

  return (
    <Card.Root>
      <Card.Body>
        <VStack gap={4} align="stretch">
          <Box textAlign="center">
            <Text fontSize="xl" fontWeight="bold" mb={2}>
              Question Generation Failed
            </Text>
            <Text color="gray.600" mb={4}>
              The previous question generation attempt failed. Click below to
              retry generating {quiz.question_count} multiple-choice questions.
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
            Retry Question Generation
          </Button>
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
