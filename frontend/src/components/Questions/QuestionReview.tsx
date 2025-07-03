import {
  Badge,
  Box,
  Button,
  Card,
  Fieldset,
  HStack,
  IconButton,
  Input,
  Skeleton,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { MdCancel, MdCheck, MdDelete, MdEdit, MdSave } from "react-icons/md";

import { type QuestionUpdateRequest, QuestionsService } from "@/client";
import { Field } from "@/components/ui/field";
import { Radio, RadioGroup } from "@/components/ui/radio";
import useCustomToast from "@/hooks/useCustomToast";
import {
  type LegacyQuestionPublic,
  convertToLegacyQuestion,
} from "@/utils/questionCompatibility";

interface QuestionReviewProps {
  quizId: string;
}

interface EditingQuestion {
  questionText: string;
  optionA: string;
  optionB: string;
  optionC: string;
  optionD: string;
  correctAnswer: string;
}

export function QuestionReview({ quizId }: QuestionReviewProps) {
  const { showErrorToast, showSuccessToast } = useCustomToast();
  const queryClient = useQueryClient();
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(
    null
  );
  const [editingData, setEditingData] = useState<EditingQuestion>({
    questionText: "",
    optionA: "",
    optionB: "",
    optionC: "",
    optionD: "",
    correctAnswer: "A",
  });
  const [filterView, setFilterView] = useState<"pending" | "all">("pending");

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
      });
      // Convert new polymorphic structure to legacy format for compatibility
      return response.map(convertToLegacyQuestion);
    },
  });

  // Filter questions based on current view
  const filteredQuestions = questions
    ? filterView === "pending"
      ? questions.filter((q) => !q.is_approved)
      : questions
    : [];

  // Calculate counts
  const pendingCount = questions
    ? questions.filter((q) => !q.is_approved).length
    : 0;
  const totalCount = questions ? questions.length : 0;

  // Approve question mutation
  const approveQuestionMutation = useMutation({
    mutationFn: async (questionId: string) => {
      return await QuestionsService.approveQuestion({
        quizId,
        questionId,
      });
    },
    onSuccess: (_, _questionId) => {
      showSuccessToast("Question approved");
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions"],
      });
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions", "stats"],
      });
    },
    onError: (error: any) => {
      const message = error?.body?.detail || "Failed to approve question";
      showErrorToast(message);
    },
  });

  // Update question mutation
  const updateQuestionMutation = useMutation({
    mutationFn: async ({
      questionId,
      data,
    }: {
      questionId: string;
      data: QuestionUpdateRequest;
    }) => {
      return await QuestionsService.updateQuestion({
        quizId,
        questionId,
        requestBody: data,
      });
    },
    onSuccess: () => {
      showSuccessToast("Question updated");
      setEditingQuestionId(null);
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions"],
      });
    },
    onError: (error: any) => {
      const message = error?.body?.detail || "Failed to update question";
      showErrorToast(message);
    },
  });

  // Delete question mutation
  const deleteQuestionMutation = useMutation({
    mutationFn: async (questionId: string) => {
      return await QuestionsService.deleteQuestion({
        quizId,
        questionId,
      });
    },
    onSuccess: () => {
      showSuccessToast("Question deleted");
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions"],
      });
      queryClient.invalidateQueries({
        queryKey: ["quiz", quizId, "questions", "stats"],
      });
    },
    onError: (error: any) => {
      const message = error?.body?.detail || "Failed to delete question";
      showErrorToast(message);
    },
  });

  const startEditing = (question: LegacyQuestionPublic) => {
    setEditingQuestionId(question.id);
    setEditingData({
      questionText: question.question_text,
      optionA: question.option_a,
      optionB: question.option_b,
      optionC: question.option_c,
      optionD: question.option_d,
      correctAnswer: question.correct_answer,
    });
  };

  const cancelEditing = () => {
    setEditingQuestionId(null);
    setEditingData({
      questionText: "",
      optionA: "",
      optionB: "",
      optionC: "",
      optionD: "",
      correctAnswer: "A",
    });
  };

  const saveEditing = () => {
    if (!editingQuestionId) return;

    const updateData: QuestionUpdateRequest = {
      question_data: {
        question_text: editingData.questionText,
        option_a: editingData.optionA,
        option_b: editingData.optionB,
        option_c: editingData.optionC,
        option_d: editingData.optionD,
        correct_answer: editingData.correctAnswer,
      },
    };

    updateQuestionMutation.mutate({
      questionId: editingQuestionId,
      data: updateData,
    });
  };

  if (isLoading) {
    return <QuestionReviewSkeleton />;
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
    );
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
    );
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
                  <>
                    <IconButton
                      size="sm"
                      colorScheme="green"
                      variant="outline"
                      onClick={saveEditing}
                      loading={updateQuestionMutation.isPending}
                    >
                      <MdSave />
                    </IconButton>
                    <IconButton
                      size="sm"
                      colorScheme="gray"
                      variant="outline"
                      onClick={cancelEditing}
                    >
                      <MdCancel />
                    </IconButton>
                  </>
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
              <VStack gap={4} align="stretch">
                <Field label="Question Text">
                  <Textarea
                    value={editingData.questionText}
                    onChange={(e) =>
                      setEditingData({
                        ...editingData,
                        questionText: e.target.value,
                      })
                    }
                    placeholder="Enter question text..."
                    rows={3}
                  />
                </Field>

                <Fieldset.Root>
                  <Fieldset.Legend>Answer Options</Fieldset.Legend>
                  <VStack gap={3} align="stretch">
                    <Field label="Option A">
                      <Input
                        value={editingData.optionA}
                        onChange={(e) =>
                          setEditingData({
                            ...editingData,
                            optionA: e.target.value,
                          })
                        }
                        placeholder="Enter option A..."
                      />
                    </Field>
                    <Field label="Option B">
                      <Input
                        value={editingData.optionB}
                        onChange={(e) =>
                          setEditingData({
                            ...editingData,
                            optionB: e.target.value,
                          })
                        }
                        placeholder="Enter option B..."
                      />
                    </Field>
                    <Field label="Option C">
                      <Input
                        value={editingData.optionC}
                        onChange={(e) =>
                          setEditingData({
                            ...editingData,
                            optionC: e.target.value,
                          })
                        }
                        placeholder="Enter option C..."
                      />
                    </Field>
                    <Field label="Option D">
                      <Input
                        value={editingData.optionD}
                        onChange={(e) =>
                          setEditingData({
                            ...editingData,
                            optionD: e.target.value,
                          })
                        }
                        placeholder="Enter option D..."
                      />
                    </Field>
                  </VStack>
                </Fieldset.Root>

                <Field label="Correct Answer">
                  <RadioGroup
                    value={editingData.correctAnswer}
                    onValueChange={(details) =>
                      setEditingData({
                        ...editingData,
                        correctAnswer: details.value,
                      })
                    }
                  >
                    <HStack gap={4}>
                      <Radio value="A">A</Radio>
                      <Radio value="B">B</Radio>
                      <Radio value="C">C</Radio>
                      <Radio value="D">D</Radio>
                    </HStack>
                  </RadioGroup>
                </Field>
              </VStack>
            ) : (
              <VStack gap={4} align="stretch">
                <Box>
                  <Text fontSize="md" fontWeight="medium" mb={2}>
                    {question.question_text}
                  </Text>
                </Box>

                <VStack gap={2} align="stretch">
                  {[
                    { key: "A", text: question.option_a },
                    { key: "B", text: question.option_b },
                    { key: "C", text: question.option_c },
                    { key: "D", text: question.option_d },
                  ].map((option) => (
                    <HStack
                      key={option.key}
                      p={3}
                      bg={
                        option.key === question.correct_answer
                          ? "green.50"
                          : "gray.50"
                      }
                      borderRadius="md"
                      border={
                        option.key === question.correct_answer
                          ? "2px solid"
                          : "1px solid"
                      }
                      borderColor={
                        option.key === question.correct_answer
                          ? "green.200"
                          : "gray.200"
                      }
                    >
                      <Badge
                        colorScheme={
                          option.key === question.correct_answer
                            ? "green"
                            : "gray"
                        }
                        variant="solid"
                        size="sm"
                      >
                        {option.key}
                      </Badge>
                      <Text flex={1}>{option.text}</Text>
                      {option.key === question.correct_answer && (
                        <Badge colorScheme="green" variant="subtle" size="sm">
                          Correct
                        </Badge>
                      )}
                    </HStack>
                  ))}
                </VStack>

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
                      }
                    )}
                  </Text>
                )}
              </VStack>
            )}
          </Card.Body>
        </Card.Root>
      ))}
    </VStack>
  );
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
  );
}
