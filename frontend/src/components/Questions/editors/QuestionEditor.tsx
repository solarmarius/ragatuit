import { memo } from "react";

import type { QuestionResponse, QuestionUpdateRequest } from "@/client";
import { QUESTION_TYPES } from "@/lib/constants";
import { FillInBlankEditor } from "./FillInBlankEditor";
import { MCQEditor } from "./MCQEditor";
import { UnsupportedEditor } from "./UnsupportedEditor";

interface QuestionEditorProps {
  question: QuestionResponse;
  onSave: (updateData: QuestionUpdateRequest) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export const QuestionEditor = memo(function QuestionEditor({
  question,
  onSave,
  onCancel,
  isLoading = false,
}: QuestionEditorProps) {
  const commonProps = {
    question,
    onSave,
    onCancel,
    isLoading,
  };

  switch (question.question_type) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return <MCQEditor {...commonProps} />;
    case QUESTION_TYPES.FILL_IN_BLANK:
      return <FillInBlankEditor {...commonProps} />;
    default:
      return (
        <UnsupportedEditor
          questionType={question.question_type}
          onCancel={onCancel}
        />
      );
  }
});
