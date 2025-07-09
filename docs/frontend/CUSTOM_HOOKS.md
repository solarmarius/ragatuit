# Custom Hooks Documentation

This document provides comprehensive documentation for all custom React hooks in the Rag@UiT frontend application. These hooks encapsulate reusable logic and provide consistent patterns for common operations.

## Table of Contents

1. [API & Data Management](#api--data-management)
   - [useApiMutation](#useapimutation)
   - [useCanvasDataFetching](#usecanvasdatafetching)
2. [State Management](#state-management)
   - [useEditingState](#useeditingstate)
   - [useDeleteConfirmation](#usedeleteconfirmation)
3. [Polling & Real-time Updates](#polling--real-time-updates)
   - [useConditionalPolling](#useconditionalpolling)
   - [useQuizStatusPolling](#usequizstatuspolling)
4. [User Interface](#user-interface)
   - [useCustomToast](#usecustomtoast)
   - [useFormattedDate](#useformatteddate)
5. [Error Handling](#error-handling)
   - [useErrorHandler](#useerrorhandler)
6. [Application Features](#application-features)
   - [useOnboarding](#useonboarding)

---

## Status System Notes

The application uses a **consolidated status system** with a single `status` field instead of separate status fields. Quiz status values are:
- `created` - Quiz created, ready to start
- `extracting_content` - Extracting content from Canvas
- `generating_questions` - AI generating questions
- `ready_for_review` - Ready for user review
- `exporting_to_canvas` - Exporting to Canvas
- `published` - Successfully published
- `failed` - Process failed (see `failure_reason` for details)

When using polling hooks, check `quiz.status` instead of separate extraction/generation/export status fields.

---

## API & Data Management

### useApiMutation

**Purpose**: Enhanced TanStack Query mutation with standardized success/error handling, toast notifications, and query invalidation.

**Location**: `/src/hooks/common/useApiMutation.ts`

#### Interface

```typescript
interface UseApiMutationOptions<TData, TVariables> {
  successMessage?: string
  invalidateQueries?: QueryKey[]
  onSuccess?: (data: TData, variables: TVariables) => void
  onError?: (error: unknown) => void
}

function useApiMutation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options?: UseApiMutationOptions<TData, TVariables>
)
```

#### Features

- **Automatic Success Toast**: Shows success message when mutation completes
- **Query Invalidation**: Automatically invalidates specified queries on success
- **Error Handling**: Uses centralized error handler unless custom handler provided
- **Type Safety**: Full TypeScript support with generics

#### Usage Examples

```tsx
// Basic usage with success message
const createQuizMutation = useApiMutation(
  (data: CreateQuizData) => QuizzesService.createQuiz(data),
  {
    successMessage: "Quiz created successfully!",
    invalidateQueries: [['quizzes']],
  }
)

// Usage with custom callbacks
const updateQuizMutation = useApiMutation(
  (data: UpdateQuizData) => QuizzesService.updateQuiz(data),
  {
    successMessage: "Quiz updated successfully!",
    invalidateQueries: [['quizzes'], ['quiz', data.id]],
    onSuccess: (data, variables) => {
      console.log('Quiz updated:', data)
      navigate(`/quiz/${data.id}`)
    },
    onError: (error) => {
      console.error('Update failed:', error)
      // Custom error handling
    }
  }
)

// Trigger mutation
const handleSubmit = (formData) => {
  createQuizMutation.mutate(formData)
}
```

#### Best Practices

1. **Always provide success messages** for user feedback
2. **Invalidate related queries** to keep UI in sync
3. **Use custom onSuccess callbacks** for navigation or additional UI updates
4. **Provide onError callbacks** only when you need custom error handling

---

### useCanvasDataFetching

**Purpose**: Consistent Canvas API data fetching with standardized retry logic, error handling, and caching behavior.

**Location**: `/src/hooks/common/useCanvasDataFetching.ts`

#### Interface

```typescript
interface UseCanvasDataFetchingOptions {
  enabled?: boolean
  staleTime?: number
  retry?: number
  retryDelay?: number
}

function useCanvasDataFetching<T>(
  queryKey: QueryKey,
  queryFn: () => Promise<T>,
  options?: UseCanvasDataFetchingOptions
)
```

#### Features

- **Canvas-specific Defaults**: Optimized settings for Canvas API behavior
- **Automatic Error Handling**: Centralized error processing
- **Configurable Retry Logic**: Customizable retry attempts and delays
- **Smart Caching**: 30-second stale time by default

#### Usage Examples

```tsx
// Basic usage for fetching Canvas courses
const { data: courses, isLoading, error } = useCanvasDataFetching(
  ['canvas', 'courses'],
  () => CanvasService.getCourses(),
  {
    staleTime: 60000, // 1 minute
    retry: 2
  }
)

// Conditional fetching based on user state
const { data: modules, isLoading } = useCanvasDataFetching(
  ['canvas', 'modules', courseId],
  () => CanvasService.getModules(courseId),
  {
    enabled: !!courseId && !!user?.canvas_tokens,
    staleTime: 120000, // 2 minutes
  }
)

// Custom retry configuration for unstable endpoints
const { data: assignments } = useCanvasDataFetching(
  ['canvas', 'assignments', courseId],
  () => CanvasService.getAssignments(courseId),
  {
    retry: 3,
    retryDelay: 2000,
    staleTime: 300000, // 5 minutes
  }
)
```

#### Best Practices

1. **Use descriptive query keys** that include all dependencies
2. **Set appropriate stale times** based on data volatility
3. **Enable conditional fetching** to avoid unnecessary requests
4. **Configure retry logic** based on endpoint reliability

---

## State Management

### useEditingState

**Purpose**: Manages editing state for items in a list, providing methods to start/cancel editing with proper typing.

**Location**: `/src/hooks/common/useEditingState.ts`

#### Interface

```typescript
function useEditingState<T>(getId: (item: T) => string): {
  editingId: string | null
  startEditing: (item: T) => void
  cancelEditing: () => void
  isEditing: (item: T) => boolean
}
```

#### Features

- **Type-safe Item Management**: Generic type support for any item type
- **Unique ID Extraction**: Flexible ID extraction function
- **Simple State Management**: Single editing item at a time
- **Optimized Performance**: Memoized callbacks to prevent re-renders

#### Usage Examples

```tsx
// Basic usage with quiz items
const { editingId, startEditing, cancelEditing, isEditing } = useEditingState(
  (quiz: Quiz) => quiz.id
)

// In component render
return (
  <div>
    {quizzes.map(quiz => (
      <div key={quiz.id}>
        {isEditing(quiz) ? (
          <QuizEditForm
            quiz={quiz}
            onSave={() => cancelEditing()}
            onCancel={cancelEditing}
          />
        ) : (
          <QuizDisplayCard
            quiz={quiz}
            onEdit={() => startEditing(quiz)}
          />
        )}
      </div>
    ))}
  </div>
)

// Usage with custom ID extraction
const { startEditing, cancelEditing, isEditing } = useEditingState(
  (question: Question) => `${question.quiz_id}-${question.id}`
)

// Conditional rendering based on editing state
const isCurrentlyEditing = isEditing(question)
```

#### Best Practices

1. **Use stable ID extraction functions** to prevent unnecessary re-renders
2. **Only allow one item to be edited at a time** for better UX
3. **Provide clear save/cancel options** in edit mode
4. **Reset editing state** after successful saves

---

### useDeleteConfirmation

**Purpose**: Handles delete confirmation dialogs with consistent mutation handling, combining dialog state with API mutations.

**Location**: `/src/hooks/common/useDeleteConfirmation.ts`

#### Interface

```typescript
interface UseDeleteConfirmationOptions {
  successMessage: string
  onSuccess?: () => void
  invalidateQueries?: QueryKey[]
}

function useDeleteConfirmation(
  deleteFn: () => Promise<void>,
  options: UseDeleteConfirmationOptions
): {
  isOpen: boolean
  openDialog: () => void
  closeDialog: () => void
  handleConfirm: () => void
  isDeleting: boolean
}
```

#### Features

- **Integrated Dialog State**: Manages confirmation dialog open/close state
- **API Mutation Handling**: Uses useApiMutation for consistent error handling
- **Automatic Cleanup**: Closes dialog on successful deletion
- **Loading States**: Provides loading state for delete operations

#### Usage Examples

```tsx
// Basic usage for deleting a quiz
const deleteConfirmation = useDeleteConfirmation(
  () => QuizzesService.deleteQuiz(quizId),
  {
    successMessage: "Quiz deleted successfully!",
    invalidateQueries: [['quizzes']],
  }
)

// Usage with custom success callback
const deleteConfirmation = useDeleteConfirmation(
  () => QuizzesService.deleteQuiz(quizId),
  {
    successMessage: "Quiz deleted successfully!",
    invalidateQueries: [['quizzes'], ['quiz', quizId]],
    onSuccess: () => {
      navigate('/quizzes')
    }
  }
)

// In component JSX
const { isOpen, openDialog, closeDialog, handleConfirm, isDeleting } = deleteConfirmation

return (
  <>
    <Button onClick={openDialog} variant="destructive">
      Delete Quiz
    </Button>

    <AlertDialog open={isOpen} onOpenChange={closeDialog}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Are you sure?</AlertDialogTitle>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={closeDialog}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isDeleting}>
            {isDeleting ? 'Deleting...' : 'Delete'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </>
)
```

#### Best Practices

1. **Always require confirmation** for destructive operations
2. **Provide clear success messages** for user feedback
3. **Navigate away** after deletion if the current view becomes invalid
4. **Show loading states** during deletion operations

---

## Polling & Real-time Updates

### useConditionalPolling

**Purpose**: Creates conditional polling functions based on data state, designed to work with TanStack Query's refetchInterval.

**Location**: `/src/hooks/common/useConditionalPolling.ts`

#### Interface

```typescript
function useConditionalPolling<T>(
  shouldPoll: (data: T | undefined) => boolean,
  interval?: number
): (query: { state: { data?: T } }) => number | false
```

#### Features

- **Conditional Logic**: Only polls when specific conditions are met
- **TanStack Query Integration**: Works seamlessly with refetchInterval
- **Customizable Intervals**: Configurable polling frequency
- **Type-safe Conditions**: Strongly typed condition functions

#### Usage Examples

```tsx
// Basic usage with custom condition
const pollWhileProcessing = useConditionalPolling(
  (data: QuizData) => data?.status === 'processing',
  3000 // Poll every 3 seconds
)

const { data: quiz } = useQuery({
  queryKey: ['quiz', quizId],
  queryFn: () => QuizzesService.getQuiz(quizId),
  refetchInterval: pollWhileProcessing,
})

// Usage with multiple conditions
const pollWhileAnyProcessing = useConditionalPolling(
  (data: QuizData) => {
    return data?.status === 'extracting_content' ||
           data?.status === 'generating_questions' ||
           data?.status === 'exporting_to_canvas'
  },
  2000
)
```

#### Best Practices

1. **Use specific conditions** to avoid unnecessary polling
2. **Set reasonable intervals** to balance responsiveness and performance
3. **Consider server load** when setting polling frequency
4. **Stop polling** when conditions are no longer met

---

### useQuizStatusPolling

**Purpose**: Predefined polling condition for quiz processing status, polling while any status is pending or processing.

**Location**: `/src/hooks/common/useConditionalPolling.ts`

#### Interface

```typescript
function useQuizStatusPolling(interval?: number): (query: any) => number | false
```

#### Features

- **Quiz-specific Logic**: Checks content extraction, LLM generation, and export status
- **Multiple Status Tracking**: Monitors all processing phases
- **Predefined Conditions**: No need to implement custom polling logic

#### Usage Examples

```tsx
// Use with quiz queries to poll while processing
const { data: quiz, isLoading } = useQuery({
  queryKey: ['quiz', quizId],
  queryFn: () => QuizzesService.getQuiz(quizId),
  refetchInterval: useQuizStatusPolling(3000), // Poll every 3 seconds
})

// Custom interval for different polling needs
const { data: quizProgress } = useQuery({
  queryKey: ['quiz', 'progress', quizId],
  queryFn: () => QuizzesService.getQuizProgress(quizId),
  refetchInterval: useQuizStatusPolling(10000), // Poll every 10 seconds
})
```

#### Best Practices

1. **Use for quiz-related queries** where status updates are important
2. **Set appropriate intervals** based on expected processing time
3. **Consider using with other quiz hooks** for comprehensive status management

---

## User Interface

### useCustomToast

**Purpose**: Provides standardized toast notifications with consistent styling and behavior.

**Location**: `/src/hooks/common/useCustomToast.ts`

#### Interface

```typescript
function useCustomToast(): {
  showSuccessToast: (description: string) => void
  showErrorToast: (description: string) => void
}
```

#### Features

- **Consistent Styling**: Predefined success and error toast styles
- **Simple API**: Just provide the message, styling is handled automatically
- **Integration with Chakra UI**: Uses Chakra's toast system under the hood

#### Usage Examples

```tsx
const { showSuccessToast, showErrorToast } = useCustomToast()

// Show success notification
const handleSuccess = () => {
  showSuccessToast("Quiz created successfully!")
}

// Show error notification
const handleError = () => {
  showErrorToast("Failed to create quiz. Please try again.")
}

// Usage in async functions
const handleSubmit = async (data: FormData) => {
  try {
    await submitForm(data)
    showSuccessToast("Form submitted successfully!")
  } catch (error) {
    showErrorToast("Failed to submit form. Please try again.")
  }
}
```

#### Best Practices

1. **Use descriptive messages** that help users understand what happened
2. **Provide actionable error messages** when possible
3. **Keep messages concise** but informative
4. **Use success toasts** to confirm important actions

---

### useFormattedDate

**Purpose**: Provides memoized date formatting with multiple predefined formats and safe error handling.

**Location**: `/src/hooks/common/useFormattedDate.ts`

#### Interface

```typescript
type DateFormat = "default" | "short" | "long" | "time-only"

function useFormattedDate(
  date: string | Date | null | undefined,
  format?: DateFormat,
  locale?: string
): string | null
```

#### Features

- **Multiple Formats**: Default, short, long, and time-only formats
- **Memoized Performance**: Prevents unnecessary recalculations
- **Safe Error Handling**: Returns null for invalid dates
- **Locale Support**: Customizable locale (defaults to en-GB)

#### Usage Examples

```tsx
// Basic usage with default format
const formattedDate = useFormattedDate(quiz.created_at)
// Result: "12 January 2024, 14:30"

// Using different formats
const shortDate = useFormattedDate(quiz.created_at, "short")
// Result: "12 Jan 2024, 14:30"

const longDate = useFormattedDate(quiz.created_at, "long")
// Result: "12 January 2024, 14:30:45"

const timeOnly = useFormattedDate(quiz.created_at, "time-only")
// Result: "14:30"

// Using custom locale
const usDate = useFormattedDate(quiz.created_at, "default", "en-US")
// Result: "January 12, 2024, 02:30 PM"

// Safe handling of null/undefined dates
const safeDate = useFormattedDate(null) // Returns null
const invalidDate = useFormattedDate("invalid-date") // Returns null

// Usage in components
return (
  <div>
    <p>Created: {useFormattedDate(quiz.created_at)}</p>
    <p>Updated: {useFormattedDate(quiz.updated_at, "short")}</p>
    <p>Time: {useFormattedDate(quiz.created_at, "time-only")}</p>
  </div>
)
```

#### Best Practices

1. **Choose appropriate formats** for different contexts
2. **Use consistent locale** across the application
3. **Handle null dates gracefully** with fallback UI
4. **Consider user timezone preferences** for future enhancements

---

## Error Handling

### useErrorHandler

**Purpose**: Provides standardized error processing and user notification through toast messages.

**Location**: `/src/hooks/common/useErrorHandler.ts`

#### Interface

```typescript
function useErrorHandler(): {
  handleError: (error: ApiError | Error | unknown) => void
}
```

#### Features

- **Multiple Error Types**: Handles ApiError, Error, and unknown error types
- **Centralized Processing**: Consistent error message extraction
- **User-friendly Messages**: Converts technical errors to user-friendly messages
- **Toast Integration**: Automatically shows error toasts

#### Usage Examples

```tsx
// Basic usage in a mutation
const { handleError } = useErrorHandler()

const createQuizMutation = useMutation({
  mutationFn: createQuiz,
  onError: (error) => {
    handleError(error) // Displays appropriate error toast
  }
})

// Usage in async functions
const { handleError } = useErrorHandler()

const handleSubmit = async (data: FormData) => {
  try {
    await submitForm(data)
  } catch (error) {
    handleError(error) // Automatically shows error toast
  }
}

// Usage with different error types
const { handleError } = useErrorHandler()

// Handles ApiError with detailed messages
handleError(new ApiError('API request failed', 400))

// Handles generic Error objects
handleError(new Error('Something went wrong'))

// Handles unknown error types with fallbacks
handleError('String error message')
handleError({ message: 'Custom error object' })
```

#### Best Practices

1. **Use consistently** across all error scenarios
2. **Don't handle errors manually** unless you need custom behavior
3. **Let the hook process** error details for user-friendly messages
4. **Consider logging** errors for debugging in development

---

## Application Features

### useOnboarding

**Purpose**: Manages the application onboarding workflow, handling state, navigation, and completion tracking.

**Location**: `/src/hooks/common/useOnboarding.ts`

#### Interface

```typescript
function useOnboarding(): {
  currentStep: number
  isOpen: boolean
  isOnboardingCompleted: boolean
  startOnboarding: () => void
  nextStep: () => void
  previousStep: () => void
  markOnboardingCompleted: () => void
  skipOnboarding: () => void
  setIsOpen: (open: boolean) => void
  isLoading: boolean
}
```

#### Features

- **Multi-step Workflow**: Manages 3-step onboarding process
- **Automatic Triggering**: Shows onboarding for new users
- **Progress Tracking**: Tracks current step and completion status
- **API Integration**: Updates user completion status on server

#### Usage Examples

```tsx
const {
  currentStep,
  isOpen,
  isOnboardingCompleted,
  startOnboarding,
  nextStep,
  previousStep,
  markOnboardingCompleted,
  skipOnboarding,
  setIsOpen,
  isLoading
} = useOnboarding()

// Start onboarding manually
if (!isOnboardingCompleted) {
  startOnboarding()
}

// Navigate through steps
if (currentStep < 3) {
  nextStep()
}

// Complete onboarding
markOnboardingCompleted()

// Onboarding modal component
return (
  <Modal open={isOpen} onOpenChange={setIsOpen}>
    <ModalContent>
      {currentStep === 1 && <WelcomeStep onNext={nextStep} />}
      {currentStep === 2 && (
        <FeaturesStep onNext={nextStep} onPrevious={previousStep} />
      )}
      {currentStep === 3 && (
        <CompleteStep
          onComplete={markOnboardingCompleted}
          onSkip={skipOnboarding}
          isLoading={isLoading}
        />
      )}
    </ModalContent>
  </Modal>
)
```

#### Best Practices

1. **Keep onboarding concise** and focused on key features
2. **Allow skipping** for experienced users
3. **Track completion** to avoid showing repeatedly
4. **Make it dismissible** but encourage completion

---

## Hook Composition Patterns

### Combining Multiple Hooks

```tsx
// Common pattern: combining data fetching with state management
function useQuizManagement(quizId: string) {
  // Data fetching
  const { data: quiz, isLoading } = useCanvasDataFetching(
    ['quiz', quizId],
    () => QuizService.getQuiz({ quizId })
  )

  // State management
  const { isEditing, startEditing, cancelEditing } = useEditingState(
    (quiz: Quiz) => quiz.id
  )

  // API mutations
  const updateMutation = useApiMutation(
    (data) => QuizService.updateQuiz({ quizId, data }),
    {
      successMessage: "Quiz updated!",
      invalidateQueries: [['quiz', quizId]],
      onSuccess: cancelEditing,
    }
  )

  // Delete confirmation
  const deleteConfirmation = useDeleteConfirmation(
    () => QuizService.deleteQuiz({ quizId }),
    {
      successMessage: "Quiz deleted!",
      invalidateQueries: [['quizzes']],
    }
  )

  return {
    quiz,
    isLoading,
    isEditing,
    startEditing,
    cancelEditing,
    updateQuiz: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    deleteConfirmation,
  }
}
```

### Error Handling Pattern

```tsx
// Centralized error handling across multiple operations
function useQuizOperations(quizId: string) {
  const { handleError } = useErrorHandler()
  const { showSuccessToast } = useCustomToast()

  const operations = {
    create: useApiMutation(createQuiz, {
      successMessage: "Quiz created!",
      onError: handleError,
    }),
    update: useApiMutation(updateQuiz, {
      successMessage: "Quiz updated!",
      onError: handleError,
    }),
    delete: useApiMutation(deleteQuiz, {
      successMessage: "Quiz deleted!",
      onError: handleError,
    }),
  }

  return operations
}
```

## Testing Custom Hooks

### Basic Hook Testing

```tsx
import { renderHook, act } from '@testing-library/react'
import { useEditingState } from '@/hooks/common'

test('useEditingState manages editing state correctly', () => {
  const { result } = renderHook(() =>
    useEditingState((item: { id: string }) => item.id)
  )

  // Initial state
  expect(result.current.editingId).toBeNull()

  // Start editing
  act(() => {
    result.current.startEditing({ id: 'test-id' })
  })

  expect(result.current.editingId).toBe('test-id')

  // Cancel editing
  act(() => {
    result.current.cancelEditing()
  })

  expect(result.current.editingId).toBeNull()
})
```

### Testing with TanStack Query

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { useApiMutation } from '@/hooks/common'

test('useApiMutation handles success correctly', async () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })

  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )

  const mockMutationFn = jest.fn().mockResolvedValue({ id: 'test' })

  const { result } = renderHook(
    () => useApiMutation(mockMutationFn, {
      successMessage: "Success!",
    }),
    { wrapper }
  )

  act(() => {
    result.current.mutate({ test: 'data' })
  })

  await waitFor(() => {
    expect(result.current.isSuccess).toBe(true)
  })

  expect(mockMutationFn).toHaveBeenCalledWith({ test: 'data' })
})
```

## Migration Guide

### From Direct TanStack Query to Custom Hooks

```tsx
// Before: Direct TanStack Query usage
const createQuizMutation = useMutation({
  mutationFn: createQuiz,
  onSuccess: () => {
    toast.success("Quiz created!")
    queryClient.invalidateQueries(['quizzes'])
  },
  onError: (error) => {
    toast.error(error.message)
  }
})

// After: Using custom hook
const createQuizMutation = useApiMutation(createQuiz, {
  successMessage: "Quiz created!",
  invalidateQueries: [['quizzes']],
})
```

### From Component State to Custom Hooks

```tsx
// Before: Managing state in component
const [editingId, setEditingId] = useState(null)
const [isDeleting, setIsDeleting] = useState(false)

const startEditing = (id) => setEditingId(id)
const cancelEditing = () => setEditingId(null)

// After: Using custom hooks
const { editingId, startEditing, cancelEditing, isEditing } = useEditingState(
  (item) => item.id
)

const deleteConfirmation = useDeleteConfirmation(
  () => deleteItem(id),
  {
    successMessage: "Item deleted!",
    invalidateQueries: [['items']],
  }
)
```

## Conclusion

The custom hooks system in Rag@UiT provides a robust foundation for building consistent, maintainable React applications. Each hook serves a specific purpose while working together to create a cohesive development experience.

### Key Benefits

- **Consistency**: Standardized patterns across the application
- **Reusability**: Hooks can be used in multiple components
- **Type Safety**: Full TypeScript support with proper generics
- **Performance**: Optimized with proper memoization
- **Testing**: Easy to test in isolation
- **Maintainability**: Centralized logic for common operations

### Best Practices Summary

1. **Use the right hook for the job** - each hook has a specific purpose
2. **Combine hooks when needed** - create higher-order hooks for complex scenarios
3. **Follow the established patterns** - consistency is key
4. **Test hooks in isolation** - easier debugging and maintenance
5. **Document custom combinations** - help other developers understand complex logic

The hooks continue to evolve based on application needs while maintaining backward compatibility and clear upgrade paths.
