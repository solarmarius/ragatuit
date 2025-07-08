import { useCallback, useState } from "react"

/**
 * Hook for managing editing state of items in a list.
 * Provides methods to start/cancel editing with proper typing.
 * Tracks which item is currently being edited using a unique identifier.
 *
 * @template T - Type of items being edited
 *
 * @param getId - Function that extracts a unique identifier from an item
 *
 * @returns Object containing editing state and control methods
 * @returns {string | null} returns.editingId - ID of the currently editing item, or null
 * @returns {function} returns.startEditing - Function to start editing an item
 * @returns {function} returns.cancelEditing - Function to cancel editing
 * @returns {function} returns.isEditing - Function to check if a specific item is being edited
 *
 * @example
 * ```tsx
 * // Basic usage with quiz items
 * const { editingId, startEditing, cancelEditing, isEditing } = useEditingState(
 *   (quiz: Quiz) => quiz.id
 * )
 *
 * // In component render
 * return (
 *   <div>
 *     {quizzes.map(quiz => (
 *       <div key={quiz.id}>
 *         {isEditing(quiz) ? (
 *           <QuizEditForm
 *             quiz={quiz}
 *             onSave={() => cancelEditing()}
 *             onCancel={cancelEditing}
 *           />
 *         ) : (
 *           <QuizDisplayCard
 *             quiz={quiz}
 *             onEdit={() => startEditing(quiz)}
 *           />
 *         )}
 *       </div>
 *     ))}
 *   </div>
 * )
 *
 * // Usage with custom ID extraction
 * const { startEditing, cancelEditing, isEditing } = useEditingState(
 *   (question: Question) => `${question.quiz_id}-${question.id}`
 * )
 *
 * // Conditional rendering based on editing state
 * const isCurrentlyEditing = isEditing(question)
 * ```
 */
export function useEditingState<T>(getId: (item: T) => string) {
  const [editingId, setEditingId] = useState<string | null>(null)

  const startEditing = useCallback(
    (item: T) => {
      setEditingId(getId(item))
    },
    [getId],
  )

  const cancelEditing = useCallback(() => {
    setEditingId(null)
  }, [])

  const isEditing = useCallback(
    (item: T) => {
      return editingId === getId(item)
    },
    [editingId, getId],
  )

  return {
    editingId,
    startEditing,
    cancelEditing,
    isEditing,
  }
}
