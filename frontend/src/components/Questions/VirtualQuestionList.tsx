import {
  Badge,
  Card,
  HStack,
  IconButton,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Suspense, lazy, memo, useCallback, useEffect, useRef } from "react";
import { MdCheck, MdDelete, MdEdit } from "react-icons/md";

import type { QuestionResponse, QuestionUpdateRequest } from "@/client";
import { LoadingSkeleton } from "../Common";
import { QuestionDisplay } from "./display";

// Lazy load the editor to improve performance
const QuestionEditor = lazy(() =>
  import("./editors").then((module) => ({ default: module.QuestionEditor }))
);

/**
 * Props for VirtualQuestionList component
 */
interface VirtualQuestionListProps {
  /** Array of questions to display */
  questions: QuestionResponse[];
  /** ID of the currently editing question */
  editingId: string | null;
  /** Function to start editing a question */
  startEditing: (question: QuestionResponse) => void;
  /** Function to cancel editing */
  cancelEditing: () => void;
  /** Function to check if a question is being edited */
  isEditing: (question: QuestionResponse) => boolean;
  /** Function to get save callback for a specific question */
  getSaveCallback: (id: string) => (data: QuestionUpdateRequest) => void;
  /** Function to handle approving a question */
  onApproveQuestion: (id: string) => void;
  /** Function to handle deleting a question */
  onDeleteQuestion: (id: string) => void;
  /** Loading state for update mutation */
  isUpdateLoading: boolean;
  /** Loading state for approve mutation */
  isApproveLoading: boolean;
  /** Loading state for delete mutation */
  isDeleteLoading: boolean;
}

/**
 * Height estimates for different question types in pixels
 */
const QUESTION_HEIGHT_ESTIMATES = {
  display: {
    multiple_choice: 250,
    matching: 400,
    fill_in_blank: 300,
    categorization: 450,
    default: 300,
  },
  edit: {
    multiple_choice: 700,
    matching: 1200,
    fill_in_blank: 800,
    categorization: 1000,
    default: 800,
  },
};

/**
 * Memoized component for rendering approval timestamp
 */
const ApprovalTimestamp = memo(({ approvedAt }: { approvedAt: string }) => {
  const date = new Date(approvedAt);
  const formattedDate = date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <Text fontSize="sm" color="gray.600">
      Approved on {formattedDate}
    </Text>
  );
});
ApprovalTimestamp.displayName = "ApprovalTimestamp";

/**
 * Virtual question list component that efficiently renders large lists of questions
 * using TanStack Virtual for virtualization
 */
export const VirtualQuestionList = memo(
  ({
    questions,
    editingId,
    startEditing,
    cancelEditing,
    isEditing,
    getSaveCallback,
    onApproveQuestion,
    onDeleteQuestion,
    isUpdateLoading,
    isApproveLoading,
    isDeleteLoading,
  }: VirtualQuestionListProps) => {
    const parentRef = useRef<HTMLDivElement>(null);
    const scrollElementRef = useRef<HTMLElement | null>(null);

    // Find the scrollable parent element
    useEffect(() => {
      if (parentRef.current) {
        // Look for the parent with overflowY: auto (the layout container)
        let element = parentRef.current.parentElement;
        while (element) {
          const style = window.getComputedStyle(element);
          if (
            style.overflowY === "auto" ||
            style.overflowY === "scroll" ||
            style.overflow === "auto"
          ) {
            scrollElementRef.current = element;
            break;
          }
          element = element.parentElement;
        }
      }
    }, []);

    // Estimate the size of each item based on question type and edit state
    const estimateSize = useCallback(
      (index: number) => {
        const question = questions[index];
        if (!question) return 300;

        const isEditMode = question.id === editingId;
        const type = question.question_type || "default";
        const heights = isEditMode
          ? QUESTION_HEIGHT_ESTIMATES.edit
          : QUESTION_HEIGHT_ESTIMATES.display;

        // Get height for specific type or use default
        const baseHeight =
          heights[type as keyof typeof heights] || heights.default;

        // Add gap (24px = gap-6)
        return baseHeight + 24;
      },
      [questions, editingId]
    );

    // Initialize virtualizer
    const virtualizer = useVirtualizer({
      count: questions.length,
      getScrollElement: () => scrollElementRef.current,
      estimateSize,
      overscan: 3,
      gap: 24,
    });

    // Trigger remeasurement when editingId changes
    useEffect(() => {
      virtualizer.measure();
    }, [editingId, virtualizer]);

    const virtualItems = virtualizer.getVirtualItems();

    return (
      <div ref={parentRef} style={{ width: "100%" }}>
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: "100%",
            position: "relative",
          }}
        >
          {virtualItems.map((virtualItem) => {
            const question = questions[virtualItem.index];
            const questionIndex = virtualItem.index;

            // Custom ref callback to always re-measure element
            const setRef = (el: HTMLDivElement | null) => {
              if (el) {
                virtualizer.measureElement(el);
              }
            };

            return (
              <div
                key={virtualItem.key}
                data-index={virtualItem.index}
                ref={setRef}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  transform: `translateY(${virtualItem.start - virtualizer.options.scrollMargin}px)`,
                }}
              >
                <Card.Root>
                  <Card.Header>
                    <HStack justify="space-between" align="center">
                      <HStack gap={3}>
                        <Text fontSize="lg" fontWeight="semibold">
                          Question {questionIndex + 1}
                        </Text>
                        {question.is_approved && (
                          <Badge colorScheme="green" variant="subtle">
                            Approved
                          </Badge>
                        )}
                      </HStack>
                      <HStack gap={2}>
                        {isEditing(question) ? (
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
                              onClick={() => onApproveQuestion(question.id)}
                              loading={isApproveLoading}
                              disabled={question.is_approved}
                            >
                              <MdCheck />
                            </IconButton>
                            <IconButton
                              size="sm"
                              colorScheme="red"
                              variant="outline"
                              onClick={() => onDeleteQuestion(question.id)}
                              loading={isDeleteLoading}
                            >
                              <MdDelete />
                            </IconButton>
                          </>
                        )}
                      </HStack>
                    </HStack>
                  </Card.Header>
                  <Card.Body>
                    {isEditing(question) ? (
                      <Suspense
                        fallback={
                          <VStack gap={4} align="stretch">
                            <LoadingSkeleton height="40px" />
                            <LoadingSkeleton height="200px" />
                            <LoadingSkeleton height="40px" width="150px" />
                          </VStack>
                        }
                      >
                        <QuestionEditor
                          question={question}
                          onSave={getSaveCallback(question.id)}
                          onCancel={cancelEditing}
                          isLoading={isUpdateLoading}
                        />
                      </Suspense>
                    ) : (
                      <VStack gap={4} align="stretch">
                        <QuestionDisplay
                          question={question}
                          showCorrectAnswer={true}
                          showExplanation={false}
                        />

                        {question.approved_at && (
                          <ApprovalTimestamp
                            approvedAt={question.approved_at}
                          />
                        )}
                      </VStack>
                    )}
                  </Card.Body>
                </Card.Root>
              </div>
            );
          })}
        </div>
      </div>
    );
  }
);

VirtualQuestionList.displayName = "VirtualQuestionList";
