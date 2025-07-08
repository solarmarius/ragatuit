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
 * Combines dialog state with useApiMutation for standardized delete operations.
 *
 * @param deleteFn - Async function that performs the delete operation
 * @param options - Configuration options for the delete operation
 * @param options.successMessage - Message to display on successful deletion
 * @param options.onSuccess - Optional callback to execute after successful deletion
 * @param options.invalidateQueries - Array of query keys to invalidate after deletion
 *
 * @returns Object containing dialog state and control methods
 * @returns {boolean} returns.isOpen - Whether the confirmation dialog is open
 * @returns {function} returns.openDialog - Function to open the confirmation dialog
 * @returns {function} returns.closeDialog - Function to close the confirmation dialog
 * @returns {function} returns.handleConfirm - Function to confirm and execute the deletion
 * @returns {boolean} returns.isDeleting - Whether the deletion is in progress
 *
 * @example
 * ```tsx
 * // Basic usage for deleting a quiz
 * const deleteConfirmation = useDeleteConfirmation(
 *   () => QuizzesService.deleteQuiz(quizId),
 *   {
 *     successMessage: "Quiz deleted successfully!",
 *     invalidateQueries: [['quizzes']],
 *   }
 * )
 *
 * // Usage with custom success callback
 * const deleteConfirmation = useDeleteConfirmation(
 *   () => QuizzesService.deleteQuiz(quizId),
 *   {
 *     successMessage: "Quiz deleted successfully!",
 *     invalidateQueries: [['quizzes'], ['quiz', quizId]],
 *     onSuccess: () => {
 *       navigate('/quizzes')
 *     }
 *   }
 * )
 *
 * // In component JSX
 * const { isOpen, openDialog, closeDialog, handleConfirm, isDeleting } = deleteConfirmation
 *
 * return (
 *   <>
 *     <Button onClick={openDialog} variant="destructive">
 *       Delete Quiz
 *     </Button>
 *
 *     <AlertDialog open={isOpen} onOpenChange={closeDialog}>
 *       <AlertDialogContent>
 *         <AlertDialogHeader>
 *           <AlertDialogTitle>Are you sure?</AlertDialogTitle>
 *         </AlertDialogHeader>
 *         <AlertDialogFooter>
 *           <AlertDialogCancel onClick={closeDialog}>Cancel</AlertDialogCancel>
 *           <AlertDialogAction onClick={handleConfirm} disabled={isDeleting}>
 *             {isDeleting ? 'Deleting...' : 'Delete'}
 *           </AlertDialogAction>
 *         </AlertDialogFooter>
 *       </AlertDialogContent>
 *     </AlertDialog>
 *   </>
 * )
 * ```
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
