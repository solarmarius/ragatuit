import {
  Badge,
  Box,
  Button,
  Card,
  HStack,
  IconButton,
  Skeleton,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { MdCheck, MdDelete, MdEdit } from "react-icons/md"

import {
  type QuestionResponse,
  type QuestionUpdateRequest,
  QuestionsService,
} from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import { QuestionDisplay } from "./display"
import { QuestionEditor } from "./QuestionEditor"

interface QuestionReviewProps {
  quizId: string
}

export function QuestionReview({ quizId }: QuestionReviewProps) {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(
    null,
  )
  const [filterView, setFilterView] = useState<"pending" | "all">("pending")

  // Fetch questions
  const {
    data: questions,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["quiz", quizId, "questions"],
    queryFn: async () => {
      const response = await QuestionsService.getQuizQuestions({
        quizId,
        approvedOnly: false, // Get all questions for review
      })
      return response
    },
  })

  // Filter questions based on current view
  const filteredQuestions = questions
    ? filterView === "pending"
      ? questions.filter((q) => !q.is_approved)
      : questions
    : []

  // Calculate counts
  const pendingCount = questions
    ? questions.filter((q) => !q.is_approved).length
    : 0
  const totalCount = questions ? questions.length : 0

  // Approve question mutation
  const approveQuestionMutation = useMutation({
    mutationFn: async (questionId: string) => {
      return await QuestionsService.approveQuestion({
        quizId,
        questionId,
      })
    },
    onSuccess: (_, _questionId) => {
      showSuccessToast("Question approved")
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions"],
      })
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions", "stats"],
      })
    },
    onError: (error: any) => {
      const message = error?.body?.detail || "Failed to approve question"
      showErrorToast(message)
    },
  })

  // Update question mutation
  const updateQuestionMutation = useMutation({
    mutationFn: async ({
      questionId,
      data,
    }: {
      questionId: string
      data: QuestionUpdateRequest
    }) => {
      return await QuestionsService.updateQuestion({
        quizId,
        questionId,
        requestBody: data,
      })
    },
    onSuccess: () => {
      showSuccessToast("Question updated")
      setEditingQuestionId(null)
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions"],
      })
    },
    onError: (error: any) => {
      const message = error?.body?.detail || "Failed to update question"
      showErrorToast(message)
    },
  })

  // Delete question mutation
  const deleteQuestionMutation = useMutation({
    mutationFn: async (questionId: string) => {
      return await QuestionsService.deleteQuestion({
        quizId,
        questionId,
      })
    },
    onSuccess: () => {
      showSuccessToast("Question deleted")
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions"],
      })
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions", "stats"],
      })
    },
    onError: (error: any) => {
      const message = error?.body?.detail || "Failed to delete question"
      showErrorToast(message)
    },
  })

  const startEditing = (question: QuestionResponse) => {
    setEditingQuestionId(question.id)
  }

  const cancelEditing = () => {
    setEditingQuestionId(null)
  }

  const handleSaveQuestion = (updateData: QuestionUpdateRequest) => {
    if (!editingQuestionId) return

    updateQuestionMutation.mutate({
      questionId: editingQuestionId,
      data: updateData,
    })
  }

  if (isLoading) {
    return <QuestionReviewSkeleton />
  }

  if (error || !questions) {
    return (
      <Card.Root>
        <Card.Body>
          <VStack gap={4}>
            <Text fontSize="xl" fontWeight="bold" color="red.500">
              Failed to Load Questions
            </Text>
            <Text color="gray.600">
              There was an error loading the questions for this quiz.
            </Text>
          </VStack>
        </Card.Body>
      </Card.Root>
    )
  }

  if (!questions || questions.length === 0) {
    return (
      <Card.Root>
        <Card.Body>
          <VStack gap={4}>
            <Text fontSize="xl" fontWeight="bold" color="gray.500">
              No Questions Generated Yet
            </Text>
            <Text color="gray.600">
              Questions will appear here once the generation process is
              complete.
            </Text>
          </VStack>
        </Card.Body>
      </Card.Root>
    )
  }

  return (
    <VStack gap={6} align="stretch">
      <Box>
        <Text fontSize="2xl" fontWeight="bold" mb={2}>
          Review Questions
        </Text>
        <Text color="gray.600">
          Review and approve each question individually. You can edit any
          question before approving it.
        </Text>
      </Box>

      {/* Filter Toggle Buttons */}
      <HStack gap={3}>
        <Button
          variant={filterView === "pending" ? "solid" : "outline"}
          colorPalette="blue"
          size="sm"
          onClick={() => setFilterView("pending")}
        >
          Pending Approval ({pendingCount})
        </Button>
        <Button
          variant={filterView === "all" ? "solid" : "outline"}
          colorPalette="blue"
          size="sm"
          onClick={() => setFilterView("all")}
        >
          All Questions ({totalCount})
        </Button>
      </HStack>

      {/* Empty state for filtered view */}
      {filteredQuestions.length === 0 && (
        <Card.Root>
          <Card.Body>
            <VStack gap={4}>
              <Text fontSize="xl" fontWeight="bold" color="gray.500">
                {filterView === "pending"
                  ? "No Pending Questions"
                  : "No Questions Found"}
              </Text>
              <Text color="gray.600">
                {filterView === "pending"
                  ? 'All questions have been approved! Switch to "All Questions" to see them.'
                  : "No questions match the current filter."}
              </Text>
            </VStack>
          </Card.Body>
        </Card.Root>
      )}

      {filteredQuestions.map((question, index) => (
        <Card.Root key={question.id}>
          <Card.Header>
            <HStack justify="space-between" align="center">
              <HStack gap={3}>
                <Text fontSize="lg" fontWeight="semibold">
                  Question {index + 1}
                </Text>
                {question.is_approved && (
                  <Badge colorScheme="green" variant="subtle">
                    Approved
                  </Badge>
                )}
              </HStack>
              <HStack gap={2}>
                {editingQuestionId === question.id ? (
                  <></>
                ) : (
                  <>
                    <IconButton
                      size="sm"
                      colorScheme="blue"
                      variant="outline"
                      onClick={() => startEditing(question)}
                      disabled={question.is_approved}
                    >
                      <MdEdit />
                    </IconButton>
                    <IconButton
                      size="sm"
                      colorScheme="green"
                      variant="outline"
                      onClick={() =>
                        approveQuestionMutation.mutate(question.id)
                      }
                      loading={approveQuestionMutation.isPending}
                      disabled={question.is_approved}
                    >
                      <MdCheck />
                    </IconButton>
                    <IconButton
                      size="sm"
                      colorScheme="red"
                      variant="outline"
                      onClick={() => deleteQuestionMutation.mutate(question.id)}
                      loading={deleteQuestionMutation.isPending}
                    >
                      <MdDelete />
                    </IconButton>
                  </>
                )}
              </HStack>
            </HStack>
          </Card.Header>
          <Card.Body>
            {editingQuestionId === question.id ? (
              <QuestionEditor
                question={question}
                onSave={handleSaveQuestion}
                onCancel={cancelEditing}
                isLoading={updateQuestionMutation.isPending}
              />
            ) : (
              <VStack gap={4} align="stretch">
                <QuestionDisplay
                  question={question}
                  showCorrectAnswer={true}
                  showExplanation={false}
                />

                {question.approved_at && (
                  <Text fontSize="sm" color="gray.600">
                    Approved on{" "}
                    {new Date(question.approved_at).toLocaleDateString(
                      "en-GB",
                      {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      },
                    )}
                  </Text>
                )}
              </VStack>
            )}
          </Card.Body>
        </Card.Root>
      ))}
    </VStack>
  )
}

function QuestionReviewSkeleton() {
  return (
    <VStack gap={6} align="stretch">
      <Box>
        <Skeleton height="32px" width="200px" mb={2} />
        <Skeleton height="20px" width="400px" />
      </Box>

      {[1, 2, 3].map((i) => (
        <Card.Root key={i}>
          <Card.Header>
            <HStack justify="space-between">
              <Skeleton height="24px" width="120px" />
              <HStack gap={2}>
                <Skeleton height="32px" width="40px" />
                <Skeleton height="32px" width="40px" />
                <Skeleton height="32px" width="40px" />
              </HStack>
            </HStack>
          </Card.Header>
          <Card.Body>
            <VStack gap={4} align="stretch">
              <Skeleton height="20px" width="100%" />
              <VStack gap={2} align="stretch">
                {[1, 2, 3, 4].map((j) => (
                  <Skeleton key={j} height="40px" width="100%" />
                ))}
              </VStack>
            </VStack>
          </Card.Body>
        </Card.Root>
      ))}
    </VStack>
  )
}
