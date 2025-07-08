# Component Patterns Documentation

This document outlines the reusable component patterns and design principles used throughout the Rag@UiT frontend application. These patterns ensure consistency, maintainability, and excellent developer experience.

## Table of Contents

1. [Design System Components](#design-system-components)
2. [Compound Components](#compound-components)
3. [Container/Presentation Pattern](#containerpresentation-pattern)
4. [State Management Patterns](#state-management-patterns)
5. [Error Handling Patterns](#error-handling-patterns)
6. [Loading State Patterns](#loading-state-patterns)
7. [Form Patterns](#form-patterns)
8. [List Management Patterns](#list-management-patterns)
9. [Modal and Dialog Patterns](#modal-and-dialog-patterns)
10. [Data Fetching Patterns](#data-fetching-patterns)

---

## Design System Components

### Base UI Components

Our design system extends Chakra UI with application-specific enhancements.

#### Enhanced Button Component

```tsx
// Location: /src/components/ui/button.tsx

interface ButtonProps extends ChakraButtonProps {
  loading?: boolean
  loadingText?: React.ReactNode
}

// Usage Examples
<Button loading={isSubmitting}>Submit</Button>
<Button loading={isCreating} loadingText="Creating...">Create Quiz</Button>
<Button colorScheme="blue" size="lg" onClick={handleClick}>Save Changes</Button>
```

**Key Features:**
- Extends Chakra UI Button with loading states
- Automatic disabled state during loading
- Flexible loading text or spinner only
- Maintains all Chakra UI props

#### Status Components

```tsx
// Status Light - Visual status indicator
<StatusLight
  extractionStatus="completed"
  generationStatus="processing"
/>

// Status Badge - Text-based status
<StatusBadge status="approved" variant="subtle" />

// Status Description - Detailed status text
<StatusDescription
  status="processing"
  message="Generating questions..."
/>
```

### Layout Components

#### EmptyState Component

```tsx
// Location: /src/components/common/EmptyState.tsx

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
}

// Usage Examples
<EmptyState title="No quizzes found" />

<EmptyState
  title="No questions available"
  description="Create your first quiz to get started"
  icon={<BookIcon size={48} />}
  action={<Button onClick={handleCreate}>Create Quiz</Button>}
/>
```

#### ErrorState Component

```tsx
// Consistent error display with optional retry
<ErrorState
  title="Failed to Load Questions"
  message="There was an error loading the questions for this quiz."
  showRetry={true}
  onRetry={refetch}
/>
```

---

## Compound Components

### Card Pattern

```tsx
// Chakra UI Card compound component pattern
<Card.Root>
  <Card.Header>
    <Card.Title>Quiz Details</Card.Title>
    <Card.Description>Review and manage your quiz</Card.Description>
  </Card.Header>
  <Card.Body>
    <QuizContent quiz={quiz} />
  </Card.Body>
  <Card.Footer>
    <Button>Edit Quiz</Button>
  </Card.Footer>
</Card.Root>
```

### Form Field Pattern

```tsx
// Location: /src/components/forms/FormField.tsx

<FormField
  label="Quiz Title"
  id="title"
  isRequired
  error={errors.title?.message}
>
  <Input
    id="title"
    placeholder="Enter quiz title"
    {...register('title', { required: 'Title is required' })}
  />
</FormField>
```

**Benefits:**
- Consistent label and error positioning
- Automatic accessibility attributes
- Reusable across all forms
- Integrated with form validation

---

## Container/Presentation Pattern

### Pattern Implementation

```tsx
// Container Component - Handles data and logic
function QuestionReviewContainer({ quizId }: { quizId: string }) {
  // Data fetching
  const { data: questions, isLoading, error } = useCanvasDataFetching(
    ['quiz', quizId, 'questions'],
    () => QuestionsService.getQuizQuestions({ quizId })
  )

  // State management
  const { editingId, startEditing, cancelEditing, isEditing } = useEditingState(
    (question) => question.id
  )

  // Mutations
  const updateMutation = useApiMutation(
    ({ questionId, data }) => QuestionsService.updateQuestion({ quizId, questionId, data }),
    {
      successMessage: "Question updated!",
      invalidateQueries: [['quiz', quizId, 'questions']],
      onSuccess: cancelEditing,
    }
  )

  // Loading and error states
  if (isLoading) return <QuestionReviewSkeleton />
  if (error) return <ErrorState title="Failed to load questions" />

  // Pass clean props to presentation component
  return (
    <QuestionReviewPresentation
      questions={questions}
      editingId={editingId}
      onStartEditing={startEditing}
      onCancelEditing={cancelEditing}
      onUpdateQuestion={updateMutation.mutate}
      isUpdating={updateMutation.isPending}
    />
  )
}

// Presentation Component - Pure UI rendering
interface QuestionReviewPresentationProps {
  questions: Question[]
  editingId: string | null
  onStartEditing: (question: Question) => void
  onCancelEditing: () => void
  onUpdateQuestion: (data: UpdateData) => void
  isUpdating: boolean
}

function QuestionReviewPresentation({
  questions,
  editingId,
  onStartEditing,
  onCancelEditing,
  onUpdateQuestion,
  isUpdating
}: QuestionReviewPresentationProps) {
  return (
    <VStack gap={4}>
      {questions.map(question => (
        <QuestionCard
          key={question.id}
          question={question}
          isEditing={editingId === question.id}
          onEdit={() => onStartEditing(question)}
          onCancel={onCancelEditing}
          onSave={onUpdateQuestion}
          isLoading={isUpdating}
        />
      ))}
    </VStack>
  )
}
```

**Benefits:**
- Clear separation of concerns
- Easy to test presentation logic
- Reusable presentation components
- Better performance optimization opportunities

---

## State Management Patterns

### Editing State Pattern

```tsx
// Using useEditingState hook for consistent list editing
function QuizList({ quizzes }: { quizzes: Quiz[] }) {
  const { editingId, startEditing, cancelEditing, isEditing } = useEditingState(
    (quiz: Quiz) => quiz.id
  )

  const updateMutation = useApiMutation(
    ({ quizId, data }) => QuizService.updateQuiz({ quizId, data }),
    {
      successMessage: "Quiz updated!",
      onSuccess: cancelEditing,
    }
  )

  return (
    <VStack gap={4}>
      {quizzes.map(quiz => (
        <Card.Root key={quiz.id}>
          <Card.Body>
            {isEditing(quiz) ? (
              <QuizEditForm
                quiz={quiz}
                onSave={(data) => updateMutation.mutate({ quizId: quiz.id, data })}
                onCancel={cancelEditing}
                isLoading={updateMutation.isPending}
              />
            ) : (
              <QuizDisplay
                quiz={quiz}
                onEdit={() => startEditing(quiz)}
              />
            )}
          </Card.Body>
        </Card.Root>
      ))}
    </VStack>
  )
}
```

### Filter State Pattern

```tsx
// Consistent filtering with URL state persistence
function QuestionReview({ quizId }: { quizId: string }) {
  const [filterView, setFilterView] = useState<"pending" | "all">("pending")

  const { data: questions } = useCanvasDataFetching(
    ['quiz', quizId, 'questions'],
    () => QuestionsService.getQuizQuestions({ quizId, approvedOnly: false })
  )

  const { filteredQuestions, pendingCount, totalCount } = useMemo(() => {
    if (!questions) return { filteredQuestions: [], pendingCount: 0, totalCount: 0 }

    const pending = questions.filter(q => !q.is_approved)
    const filtered = filterView === "pending" ? pending : questions

    return {
      filteredQuestions: filtered,
      pendingCount: pending.length,
      totalCount: questions.length,
    }
  }, [questions, filterView])

  return (
    <VStack gap={6}>
      {/* Filter Controls */}
      <HStack gap={3}>
        <Button
          variant={filterView === "pending" ? "solid" : "outline"}
          onClick={() => setFilterView("pending")}
        >
          Pending Approval ({pendingCount})
        </Button>
        <Button
          variant={filterView === "all" ? "solid" : "outline"}
          onClick={() => setFilterView("all")}
        >
          All Questions ({totalCount})
        </Button>
      </HStack>

      {/* Filtered Results */}
      <QuestionList questions={filteredQuestions} />
    </VStack>
  )
}
```

---

## Error Handling Patterns

### Centralized Error Handling

```tsx
// Using useErrorHandler for consistent error processing
function QuizManagement() {
  const { handleError } = useErrorHandler()

  const createMutation = useApiMutation(createQuiz, {
    successMessage: "Quiz created!",
    onError: handleError, // Centralized error handling
  })

  const deleteMutation = useApiMutation(deleteQuiz, {
    successMessage: "Quiz deleted!",
    onError: handleError,
  })

  // Manual error handling when needed
  const handleCustomOperation = async () => {
    try {
      await performCustomOperation()
    } catch (error) {
      handleError(error) // Consistent error processing
    }
  }

  return (
    <div>
      <Button onClick={() => createMutation.mutate(data)}>Create</Button>
      <Button onClick={() => deleteMutation.mutate(id)}>Delete</Button>
      <Button onClick={handleCustomOperation}>Custom Action</Button>
    </div>
  )
}
```

### Error Boundary Pattern

```tsx
// Feature-level error boundaries
function QuizFeature() {
  return (
    <ErrorBoundary fallback={<QuizErrorFallback />}>
      <QuizManagement />
    </ErrorBoundary>
  )
}

// Custom error fallback components
function QuizErrorFallback({ error, resetErrorBoundary }) {
  return (
    <Card.Root>
      <Card.Body>
        <ErrorState
          title="Quiz Feature Error"
          message="Something went wrong with the quiz functionality."
          action={
            <Button onClick={resetErrorBoundary}>
              Try Again
            </Button>
          }
        />
      </Card.Body>
    </Card.Root>
  )
}
```

---

## Loading State Patterns

### Skeleton Loading Pattern

```tsx
// Consistent skeleton components
function QuizListSkeleton() {
  return (
    <VStack gap={4}>
      {[1, 2, 3].map(i => (
        <Card.Root key={i}>
          <Card.Header>
            <HStack justify="space-between">
              <LoadingSkeleton
                height={UI_SIZES.SKELETON.HEIGHT.XL}
                width={UI_SIZES.SKELETON.WIDTH.TEXT_MD}
              />
              <LoadingSkeleton
                height={UI_SIZES.SKELETON.HEIGHT.XXL}
                width={UI_SIZES.SKELETON.WIDTH.SM}
              />
            </HStack>
          </Card.Header>
          <Card.Body>
            <LoadingSkeleton
              height={UI_SIZES.SKELETON.HEIGHT.LG}
              width={UI_SIZES.SKELETON.WIDTH.FULL}
              lines={3}
            />
          </Card.Body>
        </Card.Root>
      ))}
    </VStack>
  )
}

// Usage in container components
function QuizListContainer() {
  const { data: quizzes, isLoading, error } = useCanvasDataFetching(
    ['quizzes'],
    () => QuizService.getQuizzes()
  )

  if (isLoading) return <QuizListSkeleton />
  if (error) return <ErrorState />
  if (!quizzes?.length) return <EmptyState title="No quizzes found" />

  return <QuizList quizzes={quizzes} />
}
```

### Progressive Loading Pattern

```tsx
// Load critical content first, then secondary content
function QuizDashboard({ quizId }: { quizId: string }) {
  // Critical data - loads first
  const { data: quiz, isLoading: quizLoading } = useCanvasDataFetching(
    ['quiz', quizId],
    () => QuizService.getQuiz({ quizId }),
    { staleTime: 30000 }
  )

  // Secondary data - loads after quiz is available
  const { data: stats, isLoading: statsLoading } = useCanvasDataFetching(
    ['quiz', quizId, 'stats'],
    () => QuizService.getQuizStats({ quizId }),
    {
      enabled: !!quiz,
      staleTime: 60000
    }
  )

  return (
    <VStack gap={6}>
      {/* Critical content */}
      {quizLoading ? (
        <QuizHeaderSkeleton />
      ) : (
        <QuizHeader quiz={quiz} />
      )}

      {/* Secondary content */}
      {quiz && (
        <HStack gap={6}>
          <QuizDetails quiz={quiz} />
          {statsLoading ? (
            <StatsSkeleton />
          ) : (
            <QuizStats stats={stats} />
          )}
        </HStack>
      )}
    </VStack>
  )
}
```

---

## Form Patterns

### Form with Validation Pattern

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

// Schema definition
const quizSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  courseId: z.string().min(1, 'Course selection is required'),
})

type QuizFormData = z.infer<typeof quizSchema>

function QuizForm({ onSubmit, initialData }: QuizFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<QuizFormData>({
    resolver: zodResolver(quizSchema),
    defaultValues: initialData,
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <VStack gap={4}>
        <FormField
          label="Quiz Title"
          id="title"
          isRequired
          error={errors.title?.message}
        >
          <Input
            id="title"
            placeholder="Enter quiz title"
            {...register('title')}
          />
        </FormField>

        <FormField
          label="Description"
          id="description"
          error={errors.description?.message}
        >
          <Textarea
            id="description"
            placeholder="Enter description"
            {...register('description')}
          />
        </FormField>

        <FormField
          label="Course"
          id="courseId"
          isRequired
          error={errors.courseId?.message}
        >
          <Select {...register('courseId')}>
            <option value="">Select a course</option>
            {courses.map(course => (
              <option key={course.id} value={course.id}>
                {course.name}
              </option>
            ))}
          </Select>
        </FormField>

        <Button
          type="submit"
          loading={isSubmitting}
          colorScheme="blue"
          width="full"
        >
          Create Quiz
        </Button>
      </VStack>
    </form>
  )
}
```

### Multi-step Form Pattern

```tsx
// Multi-step form with progress tracking
function QuizCreationWizard() {
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<Partial<QuizData>>({})

  const updateFormData = (stepData: Partial<QuizData>) => {
    setFormData(prev => ({ ...prev, ...stepData }))
  }

  const nextStep = () => setCurrentStep(prev => Math.min(prev + 1, 3))
  const prevStep = () => setCurrentStep(prev => Math.max(prev - 1, 1))

  return (
    <Card.Root>
      <Card.Header>
        <ProgressSteps currentStep={currentStep} totalSteps={3} />
      </Card.Header>
      <Card.Body>
        {currentStep === 1 && (
          <CourseSelectionStep
            data={formData}
            onNext={(data) => {
              updateFormData(data)
              nextStep()
            }}
          />
        )}
        {currentStep === 2 && (
          <ModuleSelectionStep
            data={formData}
            onNext={(data) => {
              updateFormData(data)
              nextStep()
            }}
            onPrevious={prevStep}
          />
        )}
        {currentStep === 3 && (
          <QuizSettingsStep
            data={formData}
            onSubmit={handleCreateQuiz}
            onPrevious={prevStep}
          />
        )}
      </Card.Body>
    </Card.Root>
  )
}
```

---

## List Management Patterns

### Editable List Pattern

```tsx
function EditableQuestionList({ questions }: { questions: Question[] }) {
  const { editingId, startEditing, cancelEditing, isEditing } = useEditingState(
    (question: Question) => question.id
  )

  const updateMutation = useApiMutation(
    ({ questionId, data }) => QuestionsService.updateQuestion({ questionId, data }),
    {
      successMessage: "Question updated!",
      onSuccess: cancelEditing,
    }
  )

  const deleteMutation = useApiMutation(
    (questionId: string) => QuestionsService.deleteQuestion({ questionId }),
    {
      successMessage: "Question deleted!",
    }
  )

  return (
    <VStack gap={4}>
      {questions.map((question, index) => (
        <Card.Root key={question.id}>
          <Card.Header>
            <HStack justify="space-between">
              <Text>Question {index + 1}</Text>
              {!isEditing(question) && (
                <HStack gap={2}>
                  <IconButton
                    size="sm"
                    variant="outline"
                    onClick={() => startEditing(question)}
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="sm"
                    variant="outline"
                    colorScheme="red"
                    onClick={() => deleteMutation.mutate(question.id)}
                    loading={deleteMutation.isPending}
                  >
                    <DeleteIcon />
                  </IconButton>
                </HStack>
              )}
            </HStack>
          </Card.Header>
          <Card.Body>
            {isEditing(question) ? (
              <QuestionEditor
                question={question}
                onSave={(data) => updateMutation.mutate({
                  questionId: question.id,
                  data
                })}
                onCancel={cancelEditing}
                isLoading={updateMutation.isPending}
              />
            ) : (
              <QuestionDisplay question={question} />
            )}
          </Card.Body>
        </Card.Root>
      ))}
    </VStack>
  )
}
```

### Filterable List Pattern

```tsx
function FilterableQuizList() {
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<QuizStatus | "all">("all")

  const { data: quizzes, isLoading } = useCanvasDataFetching(
    ['quizzes'],
    () => QuizService.getQuizzes()
  )

  const filteredQuizzes = useMemo(() => {
    if (!quizzes) return []

    return quizzes.filter(quiz => {
      const matchesSearch = quiz.title.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesStatus = statusFilter === "all" || quiz.status === statusFilter

      return matchesSearch && matchesStatus
    })
  }, [quizzes, searchTerm, statusFilter])

  if (isLoading) return <QuizListSkeleton />

  return (
    <VStack gap={6}>
      {/* Filters */}
      <HStack gap={4} width="full">
        <Input
          placeholder="Search quizzes..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          flex={1}
        />
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as QuizStatus | "all")}
          width="200px"
        >
          <option value="all">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
        </Select>
      </HStack>

      {/* Results */}
      {filteredQuizzes.length === 0 ? (
        <EmptyState
          title="No quizzes found"
          description="Try adjusting your search or filters"
        />
      ) : (
        <VStack gap={4}>
          {filteredQuizzes.map(quiz => (
            <QuizCard key={quiz.id} quiz={quiz} />
          ))}
        </VStack>
      )}
    </VStack>
  )
}
```

---

## Modal and Dialog Patterns

### Confirmation Dialog Pattern

```tsx
function DeleteQuizButton({ quiz }: { quiz: Quiz }) {
  const deleteConfirmation = useDeleteConfirmation(
    () => QuizService.deleteQuiz({ quizId: quiz.id }),
    {
      successMessage: "Quiz deleted successfully!",
      invalidateQueries: [['quizzes']],
      onSuccess: () => navigate('/quizzes'),
    }
  )

  const { isOpen, openDialog, closeDialog, handleConfirm, isDeleting } = deleteConfirmation

  return (
    <>
      <Button
        variant="destructive"
        onClick={openDialog}
      >
        Delete Quiz
      </Button>

      <AlertDialog open={isOpen} onOpenChange={closeDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Quiz</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{quiz.title}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={closeDialog}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirm}
              disabled={isDeleting}
              colorScheme="red"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
```

### Form Modal Pattern

```tsx
function CreateQuizModal({ isOpen, onClose }: ModalProps) {
  const createMutation = useApiMutation(
    (data: QuizFormData) => QuizService.createQuiz(data),
    {
      successMessage: "Quiz created successfully!",
      invalidateQueries: [['quizzes']],
      onSuccess: (quiz) => {
        onClose()
        navigate(`/quiz/${quiz.id}`)
      },
    }
  )

  const handleSubmit = (data: QuizFormData) => {
    createMutation.mutate(data)
  }

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Content>
        <Dialog.Header>
          <Dialog.Title>Create New Quiz</Dialog.Title>
          <Dialog.CloseButton />
        </Dialog.Header>
        <Dialog.Body>
          <QuizForm
            onSubmit={handleSubmit}
            isLoading={createMutation.isPending}
          />
        </Dialog.Body>
      </Dialog.Content>
    </Dialog.Root>
  )
}
```

---

## Data Fetching Patterns

### Dependent Queries Pattern

```tsx
function QuizDetailPage({ quizId }: { quizId: string }) {
  // Primary data
  const { data: quiz, isLoading: quizLoading } = useCanvasDataFetching(
    ['quiz', quizId],
    () => QuizService.getQuiz({ quizId })
  )

  // Dependent data - only fetches when quiz is available
  const { data: questions, isLoading: questionsLoading } = useCanvasDataFetching(
    ['quiz', quizId, 'questions'],
    () => QuestionsService.getQuizQuestions({ quizId }),
    { enabled: !!quiz }
  )

  const { data: stats, isLoading: statsLoading } = useCanvasDataFetching(
    ['quiz', quizId, 'stats'],
    () => QuizService.getQuizStats({ quizId }),
    { enabled: !!quiz }
  )

  if (quizLoading) return <QuizDetailSkeleton />
  if (!quiz) return <NotFound />

  return (
    <VStack gap={6}>
      <QuizHeader quiz={quiz} />

      <HStack gap={6} align="start">
        <VStack flex={2}>
          {questionsLoading ? (
            <QuestionListSkeleton />
          ) : (
            <QuestionList questions={questions} />
          )}
        </VStack>

        <VStack flex={1}>
          {statsLoading ? (
            <StatsSkeleton />
          ) : (
            <QuizStats stats={stats} />
          )}
        </VStack>
      </HStack>
    </VStack>
  )
}
```

### Polling Pattern

```tsx
function QuizProcessingMonitor({ quizId }: { quizId: string }) {
  // Polls while quiz is processing
  const { data: quiz, isLoading } = useQuery({
    queryKey: ['quiz', quizId],
    queryFn: () => QuizService.getQuiz({ quizId }),
    refetchInterval: useQuizStatusPolling(5000), // Poll every 5 seconds
    staleTime: 0, // Always refetch when polling
  })

  const isProcessing = quiz?.status === 'processing' ||
                     quiz?.extraction_status === 'processing' ||
                     quiz?.generation_status === 'processing'

  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="semibold">Processing Status</Text>
          {isProcessing && <Spinner size="sm" />}
        </HStack>
      </Card.Header>
      <Card.Body>
        <VStack gap={3} align="start">
          <StatusItem
            label="Content Extraction"
            status={quiz?.extraction_status}
          />
          <StatusItem
            label="Question Generation"
            status={quiz?.generation_status}
          />
          <StatusItem
            label="Export to Canvas"
            status={quiz?.export_status}
          />
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
```

---

## Performance Optimization Patterns

### Memoization Pattern

```tsx
// Component memoization
const QuizCard = memo(function QuizCard({ quiz, onEdit, onDelete }: QuizCardProps) {
  const formattedDate = useFormattedDate(quiz.created_at, "short")

  const handleEdit = useCallback(() => {
    onEdit(quiz)
  }, [quiz, onEdit])

  const handleDelete = useCallback(() => {
    onDelete(quiz.id)
  }, [quiz.id, onDelete])

  return (
    <Card.Root>
      <Card.Header>
        <Text fontWeight="semibold">{quiz.title}</Text>
        <Text fontSize="sm" color="gray.600">{formattedDate}</Text>
      </Card.Header>
      <Card.Body>
        <HStack gap={2}>
          <Button size="sm" onClick={handleEdit}>Edit</Button>
          <Button size="sm" variant="destructive" onClick={handleDelete}>
            Delete
          </Button>
        </HStack>
      </Card.Body>
    </Card.Root>
  )
})

// Custom comparison for complex props
const QuizList = memo(function QuizList({ quizzes, onQuizUpdate }) {
  return (
    <VStack gap={4}>
      {quizzes.map(quiz => (
        <QuizCard
          key={quiz.id}
          quiz={quiz}
          onEdit={onQuizUpdate}
          onDelete={onQuizUpdate}
        />
      ))}
    </VStack>
  )
}, (prevProps, nextProps) => {
  // Custom comparison - only re-render if quiz count or IDs change
  return prevProps.quizzes.length === nextProps.quizzes.length &&
         prevProps.quizzes.every((quiz, index) =>
           quiz.id === nextProps.quizzes[index]?.id
         )
})
```

### Virtual Scrolling Pattern

```tsx
// For large lists (future enhancement)
import { FixedSizeList as List } from 'react-window'

function VirtualQuizList({ quizzes }: { quizzes: Quiz[] }) {
  const Row = ({ index, style }) => (
    <div style={style}>
      <QuizCard quiz={quizzes[index]} />
    </div>
  )

  return (
    <List
      height={600}
      itemCount={quizzes.length}
      itemSize={120}
      width="100%"
    >
      {Row}
    </List>
  )
}
```

---

## Testing Patterns

### Component Testing Pattern

```tsx
// Test utilities for component patterns
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { QuizCard } from '@/components/common/QuizCard'

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  )
}

test('QuizCard displays quiz information correctly', () => {
  const mockQuiz = {
    id: '1',
    title: 'Test Quiz',
    created_at: '2024-01-01T12:00:00Z',
    status: 'completed'
  }

  const onEdit = jest.fn()
  const onDelete = jest.fn()

  renderWithProviders(
    <QuizCard quiz={mockQuiz} onEdit={onEdit} onDelete={onDelete} />
  )

  expect(screen.getByText('Test Quiz')).toBeInTheDocument()
  expect(screen.getByText('1 Jan 2024, 12:00')).toBeInTheDocument()

  fireEvent.click(screen.getByText('Edit'))
  expect(onEdit).toHaveBeenCalledWith(mockQuiz)
})
```

### Hook Testing Pattern

```tsx
// Testing custom hook patterns
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
  expect(result.current.isEditing({ id: 'test-id' })).toBe(true)
  expect(result.current.isEditing({ id: 'other-id' })).toBe(false)

  // Cancel editing
  act(() => {
    result.current.cancelEditing()
  })

  expect(result.current.editingId).toBeNull()
})
```

---

## Migration Patterns

### Legacy to Modern Pattern Migration

```tsx
// Before: Class component with manual state management
class OldQuizList extends React.Component {
  state = {
    quizzes: [],
    loading: true,
    error: null,
    editingId: null
  }

  async componentDidMount() {
    try {
      const quizzes = await fetchQuizzes()
      this.setState({ quizzes, loading: false })
    } catch (error) {
      this.setState({ error, loading: false })
    }
  }

  render() {
    // Complex render logic
  }
}

// After: Functional component with custom hooks
function ModernQuizList() {
  const { data: quizzes, isLoading, error } = useCanvasDataFetching(
    ['quizzes'],
    () => QuizService.getQuizzes()
  )

  const { editingId, startEditing, cancelEditing, isEditing } = useEditingState(
    (quiz: Quiz) => quiz.id
  )

  if (isLoading) return <QuizListSkeleton />
  if (error) return <ErrorState />

  return <QuizList quizzes={quizzes} editingState={{ editingId, startEditing, cancelEditing, isEditing }} />
}
```

## Conclusion

These component patterns provide a solid foundation for building consistent, maintainable, and scalable React applications. They emphasize:

### Key Benefits

- **Consistency**: Standardized patterns across the application
- **Reusability**: Components and patterns can be reused across features
- **Maintainability**: Clear separation of concerns and well-defined interfaces
- **Performance**: Optimized with proper memoization and data fetching
- **Testing**: Easy to test with clear component boundaries
- **Developer Experience**: Intuitive APIs and comprehensive documentation

### Implementation Guidelines

1. **Start with simple patterns** and compose them for complex scenarios
2. **Follow the established conventions** for consistency
3. **Use TypeScript strictly** for better developer experience
4. **Test patterns in isolation** for easier debugging
5. **Document custom patterns** for team knowledge sharing
6. **Evolve patterns gradually** based on application needs

The patterns continue to evolve based on React ecosystem changes and application requirements while maintaining backward compatibility and clear migration paths.
