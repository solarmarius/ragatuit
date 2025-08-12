import { useNavigate } from "@tanstack/react-router"

import { QuizService } from "@/client"
import ConfirmationDialog from "@/components/ui/confirmation-dialog"

interface DeleteQuizConfirmationProps {
  quizId: string
  quizTitle: string
}

const DeleteQuizConfirmation = ({
  quizId,
  quizTitle,
}: DeleteQuizConfirmationProps) => {
  const navigate = useNavigate()

  const handleSuccess = () => {
    navigate({ to: "/quizzes" })
  }

  return (
    <ConfirmationDialog
      triggerButtonText="Delete"
      triggerButtonSize="sm"
      title="Delete Quiz"
      message={`Are you sure you want to delete the quiz <strong>"${quizTitle}"</strong>?<br/><br/><span style="font-weight: 600; color: #E53E3E;">This action cannot be undone.</span>`}
      confirmButtonText="Delete Quiz"
      successMessage="Quiz deleted successfully"
      mutationFn={() => QuizService.deleteQuizEndpoint({ quizId })}
      onSuccess={handleSuccess}
      invalidateQueries={[["quizzes"]]}
    />
  )
}

export default DeleteQuizConfirmation
