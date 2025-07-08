import type { QueryKey } from "@tanstack/react-query"
import { useState } from "react"

import { useApiMutation } from "./useApiMutation"

interface UseDeleteConfirmationOptions {
  successMessage: string
  onSuccess?: () => void
  invalidateQueries?: QueryKey[]
}

/**
 * Hook for delete confirmation dialogs with consistent mutation handling.
 * Provides dialog state management and delete mutation with proper cleanup.
 */
export function useDeleteConfirmation(
  deleteFn: () => Promise<void>,
  options: UseDeleteConfirmationOptions,
) {
  const [isOpen, setIsOpen] = useState(false)

  const deleteMutation = useApiMutation(deleteFn, {
    successMessage: options.successMessage,
    invalidateQueries: options.invalidateQueries,
    onSuccess: () => {
      setIsOpen(false)
      options.onSuccess?.()
    },
  })

  const openDialog = () => setIsOpen(true)
  const closeDialog = () => setIsOpen(false)

  const handleConfirm = () => {
    deleteMutation.mutate(undefined)
  }

  return {
    isOpen,
    openDialog,
    closeDialog,
    handleConfirm,
    isDeleting: deleteMutation.isPending,
  }
}
