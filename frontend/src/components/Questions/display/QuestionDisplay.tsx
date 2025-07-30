import { memo } from "react"

import type { QuestionResponse } from "@/client"
import { QUESTION_TYPES } from "@/lib/constants"
import { CategorizationDisplay } from "./CategorizationDisplay"
import { FillInBlankDisplay } from "./FillInBlankDisplay"
import { MCQDisplay } from "./MCQDisplay"
import { MatchingDisplay } from "./MatchingDisplay"
import { TrueFalseDisplay } from "./TrueFalseDisplay"
import { UnsupportedDisplay } from "./UnsupportedDisplay"

interface QuestionDisplayProps {
  question: QuestionResponse
  showCorrectAnswer?: boolean
  showExplanation?: boolean
}

export const QuestionDisplay = memo(function QuestionDisplay({
  question,
  showCorrectAnswer = false,
}: QuestionDisplayProps) {
  const commonProps = {
    question,
    showCorrectAnswer,
  }

  switch (question.question_type) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return <MCQDisplay {...commonProps} />
    case QUESTION_TYPES.FILL_IN_BLANK:
      return <FillInBlankDisplay {...commonProps} />
    case QUESTION_TYPES.MATCHING:
      return <MatchingDisplay {...commonProps} />
    case QUESTION_TYPES.CATEGORIZATION:
      return <CategorizationDisplay {...commonProps} />
    case QUESTION_TYPES.TRUE_FALSE:
      return <TrueFalseDisplay {...commonProps} />
    default:
      return <UnsupportedDisplay questionType={question.question_type} />
  }
})
