import { memo } from "react"

import type { QuestionResponse } from "@/client"
import { QUESTION_TYPES } from "@/lib/constants"
import { CategorizationDisplay } from "./CategorizationDisplay"
import { FillInBlankDisplay } from "./FillInBlankDisplay"
import { MCQDisplay } from "./MCQDisplay"
import { MatchingDisplay } from "./MatchingDisplay"
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
    case QUESTION_TYPES.FILL_IN_BLANK:
      return <FillInBlankDisplay {...commonProps} />
    case QUESTION_TYPES.MATCHING:
      return <MatchingDisplay {...commonProps} />
    case QUESTION_TYPES.CATEGORIZATION:
      return <CategorizationDisplay {...commonProps} />
    default:
      return <UnsupportedDisplay questionType={question.question_type} />
  }
})
