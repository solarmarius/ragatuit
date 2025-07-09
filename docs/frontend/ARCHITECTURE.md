# Frontend Architecture Documentation

## Overview

The Rag@UiT frontend is a modern React application built with TypeScript, leveraging a modular and scalable architecture. The codebase has undergone comprehensive refactoring to establish clear separation of concerns, reusable patterns, and excellent developer experience.

## Technology Stack

- **Framework**: React 18
- **Language**: TypeScript (strict mode)
- **Routing**: TanStack Router (file-based routing)
- **State Management**: TanStack Query (server state) + React Context (local state)
- **UI Library**: Chakra UI
- **Build Tool**: Vite
- **Testing**: Playwright (E2E), Vitest (unit tests)
- **Linting**: Biome
- **Package Manager**: npm

## Project Structure

```
src/
├── components/           # Reusable UI components
│   ├── common/          # Generic shared components
│   ├── ui/             # Base design system components
│   ├── Questions/      # Question-related components
│   ├── QuizCreation/   # Quiz creation workflow
│   ├── dashboard/      # Dashboard-specific components
│   ├── forms/          # Form-related components
│   └── layout/         # Layout components
├── hooks/              # Custom React hooks
│   ├── common/         # Reusable hooks
│   ├── api/           # API-specific hooks
│   └── auth/          # Authentication hooks
├── lib/               # Utility libraries
│   ├── api/           # API client configuration
│   ├── constants/     # Application constants
│   ├── utils/         # Utility functions
│   └── errors/        # Error handling utilities
├── routes/            # File-based routing
├── types/             # TypeScript type definitions
└── theme/             # UI theme configuration
```

## Architecture Principles

### 1. **Component Organization**

Components are organized by feature and complexity:

- **`/components/ui/`**: Base design system components that extend Chakra UI
- **`/components/common/`**: Reusable components used across features
- **`/components/[feature]/`**: Feature-specific components (Questions, QuizCreation, etc.)

### 2. **Custom Hooks Architecture**

The custom hooks system provides standardized patterns for common operations:

#### Core Hooks (`/hooks/common/`)

1. **`useApiMutation`**: Standardized API mutations with toast notifications
2. **`useCanvasDataFetching`**: Canvas API data fetching with retry logic
3. **`useConditionalPolling`**: Conditional polling based on data state
4. **`useCustomToast`**: Centralized toast notification system
5. **`useDeleteConfirmation`**: Complete delete confirmation flow management
6. **`useEditingState`**: Generic editing state management
7. **`useErrorHandler`**: Consistent error handling across components
8. **`useFormattedDate`**: Standardized date formatting
9. **`useOnboarding`**: Onboarding workflow management

#### Benefits

- **Consistency**: All API operations follow the same patterns
- **Reusability**: Hooks can be used across different components
- **Type Safety**: Full TypeScript support with proper generics
- **Error Handling**: Centralized error management with user-friendly messages
- **Performance**: Optimized with proper memoization and dependency management

### 3. **Type Safety**

The application maintains 100% type safety:

- **No `any` types**: All code uses proper TypeScript types
- **Comprehensive interfaces**: All component props are fully typed
- **API client**: Auto-generated types from backend OpenAPI specification
- **Runtime validation**: Type guards for external data

### 4. **State Management Strategy**

#### Server State
- **TanStack Query**: Manages all server-side data
- **Automatic caching**: Smart caching with proper invalidation
- **Background updates**: Automatic refetching and synchronization
- **Optimistic updates**: Immediate UI updates with rollback on failure

#### Local State
- **React Context**: For application-wide state (auth, theme)
- **useState/useReducer**: For component-local state
- **Custom hooks**: For reusable stateful logic

### 5. **Component Patterns**

#### Container/Presentation Pattern
```tsx
// Container component handles data fetching and state
function QuestionReviewContainer({ quizId }: { quizId: string }) {
  const { data, isLoading, error } = useCanvasDataFetching(
    ['quiz', quizId, 'questions'],
    () => QuestionsService.getQuizQuestions({ quizId })
  )

  if (isLoading) return <QuestionReviewSkeleton />
  if (error) return <ErrorState />

  return <QuestionReview questions={data} onUpdate={handleUpdate} />
}

// Presentation component focuses on UI rendering
function QuestionReview({ questions, onUpdate }) {
  // Pure UI logic
}
```

#### Compound Component Pattern
```tsx
// For complex components with multiple parts
<Card.Root>
  <Card.Header>
    <Card.Title>Question Review</Card.Title>
  </Card.Header>
  <Card.Body>
    <QuestionDisplay question={question} />
  </Card.Body>
</Card.Root>
```

#### Render Props Pattern
```tsx
// For flexible component composition
<DataProvider queryKey={['quiz', id]}>
  {({ data, isLoading, error }) => (
    <QuizDisplay data={data} loading={isLoading} error={error} />
  )}
</DataProvider>
```

## Data Flow Architecture

### 1. **API Integration**

```
Frontend → API Client → Backend → Database
    ↑                              ↓
    ← TanStack Query ← Response ←
```

#### Auto-generated API Client
- Generated from backend OpenAPI specification
- Type-safe API calls with proper error handling
- Automatic request/response serialization

#### Query Management
```tsx
// Declarative data fetching
const { data: quiz, isLoading } = useQuery({
  queryKey: ['quiz', quizId],
  queryFn: () => QuizService.getQuiz({ quizId }),
  staleTime: 30000,
})

// Optimistic mutations
const updateQuiz = useApiMutation(
  (data) => QuizService.updateQuiz({ quizId, data }),
  {
    successMessage: "Quiz updated successfully!",
    invalidateQueries: [['quiz', quizId], ['quizzes']],
  }
)
```

### 2. **Component Communication**

#### Parent-Child Communication
- Props for data down
- Callbacks for events up
- Context for deeply nested data

#### Sibling Communication
- Shared state in common parent
- Global state via Context
- Server state via TanStack Query

#### Cross-Feature Communication
- URL state for navigation data
- Global context for user preferences
- Event system for decoupled features

## Performance Optimization

### 1. **Memoization Strategy**

#### Component Memoization
```tsx
// Expensive components wrapped with memo
export const QuestionDisplay = memo(function QuestionDisplay({ question }) {
  // Component implementation
})

// Custom comparison for complex props
export const QuizList = memo(QuizListComponent, (prevProps, nextProps) => {
  return prevProps.quizzes.length === nextProps.quizzes.length
})
```

#### Hook Memoization
```tsx
function useQuizProcessing(quiz) {
  // Memoized calculations
  const processingStatus = useMemo(() => {
    return calculateProcessingStatus(quiz)
  }, [quiz.status])

  // Memoized callbacks
  const handleStatusUpdate = useCallback((newStatus) => {
    updateQuizStatus(quiz.id, newStatus)
  }, [quiz.id])

  return { processingStatus, handleStatusUpdate }
}
```

### 2. **Loading States**

#### Skeleton Components
```tsx
// Consistent loading experience
function QuizListSkeleton() {
  return (
    <VStack gap={4}>
      {[1, 2, 3].map(i => (
        <LoadingSkeleton
          key={i}
          height={UI_SIZES.SKELETON.HEIGHT.LG}
          width={UI_SIZES.SKELETON.WIDTH.FULL}
        />
      ))}
    </VStack>
  )
}
```

#### Progressive Loading
- Critical content loads first
- Secondary content loads progressively
- Graceful degradation for slow connections

### 3. **Bundle Optimization**

#### Code Splitting
```tsx
// Route-level splitting
const LazyQuizDetail = lazy(() => import('./routes/quiz.$id'))

// Component-level splitting for heavy components
const LazyQuestionEditor = lazy(() => import('./components/Questions/editors'))
```

#### Tree Shaking
- ES modules for all code
- Selective imports from large libraries
- Dead code elimination

## Error Handling Architecture

### 1. **Error Boundaries**

```tsx
// Global error boundary
<ErrorBoundary fallback={<GlobalErrorFallback />}>
  <Router />
</ErrorBoundary>

// Feature-specific error boundaries
<ErrorBoundary fallback={<QuizErrorFallback />}>
  <QuizManagement />
</ErrorBoundary>
```

### 2. **API Error Handling**

```tsx
// Centralized error handling
const { handleError } = useErrorHandler()

// Consistent error processing
try {
  await apiCall()
} catch (error) {
  handleError(error) // Shows appropriate toast message
}
```

### 3. **Graceful Degradation**

- Fallback UI for failed components
- Retry mechanisms for transient failures
- Offline support for critical features

## Testing Architecture

### 1. **Testing Strategy**

#### Unit Tests
- Custom hooks testing with React Testing Library
- Utility function testing
- Component behavior testing

#### Integration Tests
- Component integration with hooks
- API integration testing
- State management testing

#### End-to-End Tests
- Complete user workflows
- Cross-browser compatibility
- Mobile responsiveness

### 2. **Test Organization**

```
tests/
├── components/          # Component-specific tests
├── e2e/                # End-to-end workflows
├── fixtures/           # Test data
└── auth.setup.ts       # Authentication setup
```

### 3. **Testing Patterns**

```tsx
// Page Object Model for E2E tests
class QuizCreationPage {
  async selectCourse(courseName: string) {
    await this.page.getByRole('combobox', { name: 'Course' }).click()
    await this.page.getByRole('option', { name: courseName }).click()
  }

  async createQuiz(quizData: QuizData) {
    await this.fillQuizForm(quizData)
    await this.submitForm()
    await this.waitForCreation()
  }
}
```

## Development Guidelines

### 1. **Code Standards**

- **TypeScript strict mode**: No implicit any, strict null checks
- **ESLint + Prettier**: Consistent code formatting
- **Component naming**: PascalCase for components, camelCase for functions
- **File naming**: kebab-case for files, PascalCase for components

### 2. **Component Guidelines**

#### Props Interface
```tsx
// Always define props interface
interface QuizCardProps {
  quiz: Quiz
  onEdit?: (quiz: Quiz) => void
  showActions?: boolean
}

// Use descriptive prop names
<QuizCard
  quiz={quiz}
  onEdit={handleEdit}
  showActions={canEditQuiz}
/>
```

#### Component Structure
```tsx
// Consistent component structure
export function QuizCard({ quiz, onEdit, showActions = true }: QuizCardProps) {
  // Hooks at the top
  const { formatDate } = useFormattedDate()
  const { showToast } = useCustomToast()

  // Event handlers
  const handleEdit = useCallback(() => {
    onEdit?.(quiz)
  }, [quiz, onEdit])

  // Early returns for loading/error states
  if (!quiz) return null

  // Main render
  return (
    <Card.Root>
      {/* Component JSX */}
    </Card.Root>
  )
}
```

### 3. **Hook Guidelines**

#### Custom Hook Structure
```tsx
// Consistent hook naming and structure
function useQuizManagement(initialQuiz?: Quiz) {
  // State declarations
  const [isEditing, setIsEditing] = useState(false)

  // External hooks
  const { showToast } = useCustomToast()

  // Mutations
  const updateMutation = useApiMutation(updateQuiz, {
    successMessage: "Quiz updated!",
    onSuccess: () => setIsEditing(false),
  })

  // Memoized values
  const quizStatus = useMemo(() =>
    calculateQuizStatus(quiz), [quiz]
  )

  // Callbacks
  const handleEdit = useCallback(() => {
    setIsEditing(true)
  }, [])

  // Return object
  return {
    quiz,
    isEditing,
    quizStatus,
    handleEdit,
    updateQuiz: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
  }
}
```

## Migration and Evolution

### 1. **Legacy Code Migration**

- Gradual migration from old patterns to new architecture
- Coexistence of old and new patterns during transition
- Clear migration path for each component type

### 2. **Future Enhancements**

#### Planned Improvements
- **React Server Components**: For better SSR performance
- **Suspense**: For better loading state management
- **Concurrent Features**: For better user experience
- **PWA Features**: For offline functionality

#### Scalability Considerations
- **Micro-frontends**: For team independence
- **Module Federation**: For shared components
- **State Management**: Potential Zustand/Redux migration for complex state

## Conclusion

The Rag@UiT frontend architecture provides a solid foundation for building maintainable, scalable, and performant React applications. The refactored codebase emphasizes developer experience, type safety, and reusability while maintaining excellent performance and user experience.

Key architectural benefits:
- **Type Safety**: 100% TypeScript coverage with strict mode
- **Reusability**: Comprehensive custom hooks and component library
- **Performance**: Optimized with memoization and code splitting
- **Maintainability**: Clear patterns and documentation
- **Scalability**: Modular architecture for team growth
- **Developer Experience**: Excellent tooling and development workflow

The architecture continues to evolve based on project needs while maintaining backward compatibility and clear migration paths.
