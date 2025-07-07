import { useState, useCallback } from 'react'

/**
 * Hook for managing editing state of items in a list.
 * Provides methods to start/cancel editing with proper typing.
 */
export function useEditingState<T>(getId: (item: T) => string) {
  const [editingId, setEditingId] = useState<string | null>(null)

  const startEditing = useCallback((item: T) => {
    setEditingId(getId(item))
  }, [getId])

  const cancelEditing = useCallback(() => {
    setEditingId(null)
  }, [])

  const isEditing = useCallback((item: T) => {
    return editingId === getId(item)
  }, [editingId, getId])

  return {
    editingId,
    startEditing,
    cancelEditing,
    isEditing,
  }
}
