import { memo } from "react"

import type { QuestionResponse } from "@/client"
import { QUESTION_TYPES } from "@/lib/constants"
import { MCQDisplay } from "./MCQDisplay"
import { TrueFalseDisplay } from "./TrueFalseDisplay"
import { ShortAnswerDisplay } from "./ShortAnswerDisplay"
import { EssayDisplay } from "./EssayDisplay"
import { FillInBlankDisplay } from "./FillInBlankDisplay"
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
    case QUESTION_TYPES.TRUE_FALSE:
      return <TrueFalseDisplay {...commonProps} />
    case QUESTION_TYPES.SHORT_ANSWER:
      return <ShortAnswerDisplay {...commonProps} />
    case QUESTION_TYPES.ESSAY:
      return <EssayDisplay {...commonProps} />
    case QUESTION_TYPES.FILL_IN_BLANK:
      return <FillInBlankDisplay {...commonProps} />
    default:
      return <UnsupportedDisplay questionType={question.question_type} />
  }
})
