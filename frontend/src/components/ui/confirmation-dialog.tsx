import { Button, ButtonGroup, Text } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"

import { type ApiError } from "@/client"
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

interface ConfirmationDialogProps {
  triggerButtonText: string
  triggerButtonSize?: "xs" | "sm" | "md" | "lg"
  triggerButtonProps?: Record<string, unknown>
  title: string
  message: string
  confirmButtonText?: string
  successMessage?: string
  mutationFn: () => Promise<unknown>
  onSuccess?: () => void
  invalidateQueries?: string[][]
}

const ConfirmationDialog = ({
  triggerButtonText,
  triggerButtonSize = "md",
  triggerButtonProps = {},
  title,
  message,
  confirmButtonText = "Confirm",
  successMessage = "Action completed successfully",
  mutationFn,
  onSuccess,
  invalidateQueries = [],
}: ConfirmationDialogProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const { handleError } = useErrorHandler()
  const {
    handleSubmit,
    formState: { isSubmitting },
  } = useForm()

  const mutation = useMutation({
    mutationFn,
    onSuccess: () => {
      showSuccessToast(successMessage)
      setIsOpen(false)

      // Invalidate specified queries
      invalidateQueries.forEach((queryKey) => {
        queryClient.invalidateQueries({ queryKey })
      })

      // Call custom onSuccess handler
      onSuccess?.()
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const onSubmit = async () => {
    mutation.mutate()
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      role="alertdialog"
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button
          variant="solid"
          colorPalette="red"
          size={triggerButtonSize}
          {...triggerButtonProps}
        >
          {triggerButtonText}
        </Button>
      </DialogTrigger>

      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogCloseTrigger />
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4} dangerouslySetInnerHTML={{ __html: message }} />
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
                {confirmButtonText}
              </Button>
            </ButtonGroup>
          </DialogFooter>
        </form>
      </DialogContent>
    </DialogRoot>
  )
}

export default ConfirmationDialog
