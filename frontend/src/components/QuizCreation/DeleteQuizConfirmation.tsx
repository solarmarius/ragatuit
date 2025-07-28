import { Button, ButtonGroup, Text } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { useForm } from "react-hook-form"

import { type ApiError, QuizService } from "@/client"
import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useCustomToast, useErrorHandler } from "@/hooks/common"

interface DeleteQuizConfirmationProps {
  quizId: string
  quizTitle: string
}

const DeleteQuizConfirmation = ({
  quizId,
  quizTitle,
}: DeleteQuizConfirmationProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { showSuccessToast } = useCustomToast()
  const { handleError } = useErrorHandler()
  const {
    handleSubmit,
    formState: { isSubmitting },
  } = useForm()

  const mutation = useMutation({
    mutationFn: () => QuizService.deleteQuizEndpoint({ quizId }),
    onSuccess: () => {
      showSuccessToast("Quiz deleted successfully")
      setIsOpen(false)
      // Invalidate quizzes list and navigate back to quizzes page
      queryClient.invalidateQueries({ queryKey: ["quizzes"] })
      navigate({ to: "/quizzes" })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const onSubmit = async () => {
    mutation.mutate()
  }

  return (
    <>
      <DialogRoot
        size={{ base: "xs", md: "md" }}
        role="alertdialog"
        placement="center"
        open={isOpen}
        onOpenChange={({ open }) => setIsOpen(open)}
      >
        <DialogTrigger asChild>
          <Button variant="solid" colorPalette="red" size="sm">
            Delete
          </Button>
        </DialogTrigger>

        <DialogContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            <DialogCloseTrigger />
            <DialogHeader>
              <DialogTitle>Delete Quiz</DialogTitle>
            </DialogHeader>
            <DialogBody>
              <Text mb={4}>
                Are you sure you want to delete the quiz{" "}
                <strong>"{quizTitle}"</strong>?
              </Text>

              <Text fontWeight="semibold" color="red.500">
                This action cannot be undone.
              </Text>
            </DialogBody>

            <DialogFooter gap={2}>
              <ButtonGroup>
                <DialogActionTrigger asChild>
                  <Button
                    variant="subtle"
                    colorPalette="gray"
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                </DialogActionTrigger>
                <Button
                  variant="solid"
                  colorPalette="red"
                  type="submit"
                  loading={isSubmitting}
                >
                  Delete Quiz
                </Button>
              </ButtonGroup>
            </DialogFooter>
          </form>
        </DialogContent>
      </DialogRoot>
    </>
  )
}

export default DeleteQuizConfirmation
