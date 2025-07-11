import { memo } from "react"

import type { QuestionResponse } from "@/client"
import { QUESTION_TYPES } from "@/lib/constants"
import { FillInBlankDisplay } from "./FillInBlankDisplay"
import { MCQDisplay } from "./MCQDisplay"
import { ShortAnswerDisplay } from "./ShortAnswerDisplay"
import { UnsupportedDisplay } from "./UnsupportedDisplay"

interface QuestionDisplayProps {
  question: QuestionResponse
  showCorrectAnswer?: boolean
  showExplanation?: boolean
}

export const QuestionDisplay = memo(function QuestionDisplay({
  question,
  showCorrectAnswer = false,
  showExplanation = false,
}: QuestionDisplayProps) {
  const commonProps = {
    question,
    showCorrectAnswer,
    showExplanation,
  }

  switch (question.question_type) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return <MCQDisplay {...commonProps} />
    case QUESTION_TYPES.SHORT_ANSWER:
      return <ShortAnswerDisplay {...commonProps} />
    case QUESTION_TYPES.FILL_IN_BLANK:
      return <FillInBlankDisplay {...commonProps} />
    default:
      return <UnsupportedDisplay questionType={question.question_type} />
  }
})
