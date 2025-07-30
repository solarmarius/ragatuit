import { memo, useCallback } from "react";

import type {
  QuestionCreateRequest,
  QuestionResponse,
  QuestionType,
  QuestionUpdateRequest,
} from "@/client";
import { QuestionEditor } from "@/components/Questions/editors/QuestionEditor";
import { QUESTION_TYPES } from "@/lib/constants";

interface ManualQuestionCreatorProps {
  /** The selected question type */
  questionType: string;
  /** Quiz ID for the question */
  quizId: string;
  /** Callback when question is saved */
  onSave: (questionData: QuestionCreateRequest) => void;
  /** Callback when creation is canceled */
  onCancel: () => void;
  /** Whether the save operation is loading */
  isLoading?: boolean;
}

/**
 * Wrapper component that adapts existing question editors for manual question creation.
 * This component hides tags and difficulty fields, setting appropriate defaults,
 * and transforms the form data for API submission.
 *
 * @example
 * ```tsx
 * <ManualQuestionCreator
 *   questionType={QUESTION_TYPES.MULTIPLE_CHOICE}
 *   quizId="quiz-123"
 *   onSave={(data) => createQuestion(data)}
 *   onCancel={() => setStep('type-selection')}
 *   isLoading={mutation.isPending}
 * />
 * ```
 */
export const ManualQuestionCreator = memo(function ManualQuestionCreator({
  questionType,
  quizId,
  onSave,
  onCancel,
  isLoading = false,
}: ManualQuestionCreatorProps) {
  // Transform the update request to a create request
  const handleSave = useCallback(
    (updateData: QuestionUpdateRequest) => {
      if (!updateData.question_data) {
        console.error("No question data provided");
        return;
      }

      // Transform to create request format with defaults
      const createData: QuestionCreateRequest = {
        quiz_id: quizId,
        question_type: questionType as any, // Type assertion needed for polymorphic types
        question_data: updateData.question_data,
        difficulty: "medium", // Default difficulty as specified in requirements
        tags: [], // Empty tags array as specified in requirements
      };

      onSave(createData);
    },
    [questionType, quizId, onSave]
  );

  // Create a mock question response object for the editor
  // This allows us to reuse existing editor components without modification
  const mockQuestion: QuestionResponse = {
    id: "temp-id", // Temporary ID for editor compatibility
    quiz_id: quizId,
    question_type: questionType as QuestionType,
    question_data: getDefaultQuestionData(questionType),
    difficulty: "medium",
    tags: [],
    is_approved: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  return (
    <QuestionEditor
      question={mockQuestion}
      onSave={handleSave}
      onCancel={onCancel}
      isLoading={isLoading}
    />
  );
});

/**
 * Provides default question data based on question type.
 * This ensures the editor has valid initial state.
 */
function getDefaultQuestionData(questionType: string): Record<string, any> {
  switch (questionType) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return {
        question_text: "",
        option_a: "",
        option_b: "",
        option_c: "",
        option_d: "",
        correct_answer: "A",
        explanation: null,
      };

    case QUESTION_TYPES.TRUE_FALSE:
      return {
        question_text: "",
        correct_answer: true,
        explanation: null,
      };

    case QUESTION_TYPES.FILL_IN_BLANK:
      return {
        question_text: "",
        blanks: [],
        explanation: null,
      };

    case QUESTION_TYPES.MATCHING:
      return {
        question_text: "",
        pairs: [
          { question: "", answer: "" },
          { question: "", answer: "" },
          { question: "", answer: "" },
        ],
        distractors: [],
        explanation: null,
      };

    case QUESTION_TYPES.CATEGORIZATION: {
      // Create item IDs first so we can reference them in categories
      const item1Id = crypto.randomUUID();
      const item2Id = crypto.randomUUID();
      const item3Id = crypto.randomUUID();
      const item4Id = crypto.randomUUID();
      const item5Id = crypto.randomUUID();
      const item6Id = crypto.randomUUID();

      return {
        question_text: "",
        categories: [
          {
            id: crypto.randomUUID(),
            name: "",
            correct_items: [item1Id, item2Id, item3Id],
          },
          {
            id: crypto.randomUUID(),
            name: "",
            correct_items: [item4Id, item5Id, item6Id],
          },
        ],
        items: [
          { id: item1Id, text: "" },
          { id: item2Id, text: "" },
          { id: item3Id, text: "" },
          { id: item4Id, text: "" },
          { id: item5Id, text: "" },
          { id: item6Id, text: "" },
        ],
        distractors: [],
        explanation: null,
      };
    }

    default:
      return {
        question_text: "",
        explanation: null,
      };
  }
}
