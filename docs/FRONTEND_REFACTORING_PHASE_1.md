# Frontend Refactoring Implementation Plan

## Overview
This document provides a step-by-step implementation plan for refactoring the React TypeScript frontend application. Each step is designed to be atomic, testable, and safe to implement without breaking the application.

## Pre-Refactoring Checklist

### 1. Create Feature Branch
```bash
git checkout -b feature/frontend-refactoring
```

### 2. Initial Type Check
```bash
cd frontend
npx tsc --noEmit
```
Ensure no existing TypeScript errors before starting.

### 3. Run Initial Tests
```bash
npm run lint
npm run build
```

## Phase 1: Foundation & Infrastructure (Steps 1-10)

### Step 1: Create New Directory Structure
**Goal:** Establish the new folder structure without moving existing files yet.

**Actions:**
- CREATE: `src/lib/` directory
- CREATE: `src/lib/api/` directory
- CREATE: `src/lib/auth/` directory
- CREATE: `src/lib/constants/` directory
- CREATE: `src/lib/errors/` directory
- CREATE: `src/lib/utils/` directory
- CREATE: `src/hooks/api/` directory
- CREATE: `src/hooks/auth/` directory
- CREATE: `src/hooks/common/` directory
- CREATE: `src/providers/` directory
- CREATE: `src/services/` directory
- CREATE: `src/stores/` directory
- CREATE: `src/components/common/` directory
- CREATE: `src/components/forms/` directory
- CREATE: `src/components/layout/` directory
- CREATE: `src/components/questions/display/` directory
- CREATE: `src/components/questions/editors/` directory
- CREATE: `src/components/questions/shared/` directory

**Code changes:**
```bash
# Create directory structure
mkdir -p src/lib/{api,auth,constants,errors,utils}
mkdir -p src/hooks/{api,auth,common}
mkdir -p src/providers src/services src/stores
mkdir -p src/components/{common,forms,layout}
mkdir -p src/components/questions/{display,editors,shared}
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** New directories created, no TypeScript errors, application still works normally.

---

### Step 2: Create Constants File
**Goal:** Centralize application constants to improve maintainability.

**Actions:**
- CREATE: `src/lib/constants/index.ts`

**Code changes:**
```typescript
// src/lib/constants/index.ts
export const API_ROUTES = {
  AUTH: {
    LOGIN_CANVAS: '/api/v1/auth/login/canvas',
    LOGOUT_CANVAS: '/api/v1/auth/logout/canvas',
  },
  USERS: {
    ME: '/api/v1/users/me',
  },
  QUIZ: {
    USER_QUIZZES: '/api/v1/quiz/user',
  },
} as const

export const QUERY_KEYS = {
  CURRENT_USER: ['currentUser'],
  USER_QUIZZES: ['user-quizzes'],
} as const

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  ONBOARDING_COMPLETED: 'onboarding_completed',
} as const

export const QUESTION_TYPES = {
  MULTIPLE_CHOICE: 'multiple_choice',
  TRUE_FALSE: 'true_false',
  SHORT_ANSWER: 'short_answer',
  ESSAY: 'essay',
  FILL_IN_BLANK: 'fill_in_blank',
} as const

export const PROCESSING_STATUSES = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Constants file created, no TypeScript errors.

---

### Step 3: Create Error Handling Utilities
**Goal:** Centralize error handling patterns.

**Actions:**
- CREATE: `src/lib/errors/index.ts`
- CREATE: `src/lib/errors/ApiError.ts`
- CREATE: `src/lib/errors/ErrorBoundary.tsx`

**Code changes:**
```typescript
// src/lib/errors/ApiError.ts
export class AppError extends Error {
  constructor(
    message: string,
    public code?: string,
    public statusCode?: number,
  ) {
    super(message)
    this.name = 'AppError'
  }
}

export class ApiError extends AppError {
  constructor(
    message: string,
    public statusCode: number,
    public code?: string,
  ) {
    super(message, code, statusCode)
    this.name = 'ApiError'
  }
}

export class ValidationError extends AppError {
  constructor(
    message: string,
    public field?: string,
  ) {
    super(message, 'VALIDATION_ERROR')
    this.name = 'ValidationError'
  }
}
```

```typescript
// src/lib/errors/ErrorBoundary.tsx
import { Box, Button, Text, VStack } from '@chakra-ui/react'
import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary'
import type { ReactNode } from 'react'

interface ErrorFallbackProps {
  error: Error
  resetErrorBoundary: () => void
}

function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  return (
    <Box
      role="alert"
      p={6}
      bg="red.50"
      borderRadius="md"
      border="1px solid"
      borderColor="red.200"
    >
      <VStack gap={4} align="start">
        <Text fontSize="lg" fontWeight="bold" color="red.700">
          Something went wrong
        </Text>
        <Text color="red.600" fontSize="sm">
          {error.message}
        </Text>
        <Button
          onClick={resetErrorBoundary}
          colorScheme="red"
          size="sm"
          variant="outline"
        >
          Try again
        </Button>
      </VStack>
    </Box>
  )
}

interface ErrorBoundaryProps {
  children: ReactNode
  onError?: (error: Error, errorInfo: { componentStack: string }) => void
}

export function ErrorBoundary({ children, onError }: ErrorBoundaryProps) {
  return (
    <ReactErrorBoundary
      FallbackComponent={ErrorFallback}
      onError={onError}
    >
      {children}
    </ReactErrorBoundary>
  )
}
```

```typescript
// src/lib/errors/index.ts
export * from './ApiError'
export * from './ErrorBoundary'
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Error handling utilities created, no TypeScript errors.

---

### Step 4: Create API Utilities
**Goal:** Centralize API configuration and utilities.

**Actions:**
- CREATE: `src/lib/api/index.ts`
- CREATE: `src/lib/api/client.ts`
- CREATE: `src/lib/api/queryKeys.ts`

**Code changes:**
```typescript
// src/lib/api/client.ts
import { OpenAPI } from '@/client'
import { STORAGE_KEYS } from '@/lib/constants'

export const configureApiClient = () => {
  OpenAPI.BASE = import.meta.env.VITE_API_URL
  OpenAPI.TOKEN = async () => {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) || ''
  }
}

export const isAuthenticated = (): boolean => {
  return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) !== null
}

export const clearAuthToken = (): void => {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
}

export const setAuthToken = (token: string): void => {
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token)
}
```

```typescript
// src/lib/api/queryKeys.ts
export const queryKeys = {
  auth: {
    currentUser: () => ['auth', 'currentUser'] as const,
  },
  quizzes: {
    all: () => ['quizzes'] as const,
    userQuizzes: () => ['quizzes', 'user'] as const,
    detail: (id: string) => ['quizzes', 'detail', id] as const,
  },
  questions: {
    all: () => ['questions'] as const,
    byQuiz: (quizId: string) => ['questions', 'quiz', quizId] as const,
    detail: (id: string) => ['questions', 'detail', id] as const,
  },
} as const
```

```typescript
// src/lib/api/index.ts
export * from './client'
export * from './queryKeys'
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** API utilities created, no TypeScript errors.

---

### Step 5: Create Authentication Hook
**Goal:** Centralize authentication logic into a dedicated hook.

**Actions:**
- CREATE: `src/hooks/auth/useAuth.ts`
- CREATE: `src/hooks/auth/index.ts`

**Code changes:**
```typescript
// src/hooks/auth/useAuth.ts
import { AuthService, type UserPublic, UsersService } from '@/client'
import { queryKeys } from '@/lib/api'
import { clearAuthToken, isAuthenticated } from '@/lib/api/client'
import { STORAGE_KEYS } from '@/lib/constants'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

export function useAuth() {
  const navigate = useNavigate()

  const { data: user, isLoading, error } = useQuery<UserPublic | null, Error>({
    queryKey: queryKeys.auth.currentUser(),
    queryFn: UsersService.readUserMe,
    enabled: isAuthenticated(),
  })

  const initiateCanvasLogin = () => {
    window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/login/canvas`
  }

  const logout = async () => {
    try {
      await AuthService.logoutCanvas()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearAuthToken()
      navigate({ to: '/login' })
    }
  }

  return {
    user,
    isLoading,
    error,
    isAuthenticated: isAuthenticated(),
    initiateCanvasLogin,
    logout,
  }
}
```

```typescript
// src/hooks/auth/index.ts
export * from './useAuth'
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Authentication hook created, no TypeScript errors.

---

### Step 6: Create Quiz API Hook
**Goal:** Centralize quiz-related API calls.

**Actions:**
- CREATE: `src/hooks/api/useQuizzes.ts`
- CREATE: `src/hooks/api/index.ts`

**Code changes:**
```typescript
// src/hooks/api/useQuizzes.ts
import { QuizService } from '@/client'
import { queryKeys } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'

export function useUserQuizzes() {
  return useQuery({
    queryKey: queryKeys.quizzes.userQuizzes(),
    queryFn: QuizService.getUserQuizzesEndpoint,
  })
}

export function useQuizDetail(quizId: string) {
  return useQuery({
    queryKey: queryKeys.quizzes.detail(quizId),
    queryFn: () => QuizService.getQuizByIdEndpoint({ quizId }),
    enabled: !!quizId,
  })
}
```

```typescript
// src/hooks/api/index.ts
export * from './useQuizzes'
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Quiz hooks created, no TypeScript errors.

---

### Step 7: Create Utility Functions
**Goal:** Centralize utility functions and move existing utils.

**Actions:**
- CREATE: `src/lib/utils/index.ts`
- CREATE: `src/lib/utils/quiz.ts`
- CREATE: `src/lib/utils/time.ts`

**Code changes:**
```typescript
// src/lib/utils/quiz.ts
import type { Quiz } from '@/client/types.gen'
import { PROCESSING_STATUSES } from '@/lib/constants'

export function getQuizzesBeingGenerated(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
    const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

    return (
      extractionStatus === PROCESSING_STATUSES.PROCESSING ||
      generationStatus === PROCESSING_STATUSES.PROCESSING ||
      (extractionStatus === PROCESSING_STATUSES.COMPLETED &&
       generationStatus === PROCESSING_STATUSES.PENDING)
    )
  })
}

export function getQuizzesNeedingReview(quizzes: Quiz[]): Quiz[] {
  return quizzes.filter((quiz) => {
    const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
    const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

    return (
      extractionStatus === PROCESSING_STATUSES.COMPLETED &&
      generationStatus === PROCESSING_STATUSES.COMPLETED
    )
  })
}

export function getQuizProcessingPhase(quiz: Quiz): string {
  const extractionStatus = quiz.content_extraction_status || PROCESSING_STATUSES.PENDING
  const generationStatus = quiz.llm_generation_status || PROCESSING_STATUSES.PENDING

  if (extractionStatus === PROCESSING_STATUSES.FAILED || generationStatus === PROCESSING_STATUSES.FAILED) {
    return 'Failed'
  }

  if (extractionStatus === PROCESSING_STATUSES.COMPLETED && generationStatus === PROCESSING_STATUSES.COMPLETED) {
    return 'Complete'
  }

  if (extractionStatus === PROCESSING_STATUSES.PROCESSING) {
    return 'Extracting content...'
  }

  if (generationStatus === PROCESSING_STATUSES.PROCESSING) {
    return 'Generating questions...'
  }

  if (extractionStatus === PROCESSING_STATUSES.COMPLETED && generationStatus === PROCESSING_STATUSES.PENDING) {
    return 'Ready for generation'
  }

  return 'Pending'
}
```

```typescript
// src/lib/utils/time.ts
export function formatDate(date: string | Date, locale = 'en-GB'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date

  if (isNaN(dateObj.getTime())) {
    return 'Invalid date'
  }

  return dateObj.toLocaleDateString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(date: string | Date, locale = 'en-GB'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date

  if (isNaN(dateObj.getTime())) {
    return 'Invalid date'
  }

  return dateObj.toLocaleString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
```

```typescript
// src/lib/utils/index.ts
export * from './quiz'
export * from './time'
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Utility functions created, no TypeScript errors.

---

### Step 8: Update Main App Configuration
**Goal:** Use the new API client configuration in the main app.

**Actions:**
- MODIFY: `src/main.tsx`

**Code changes:**
```typescript
// src/main.tsx
import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { RouterProvider, createRouter } from "@tanstack/react-router"
import React, { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { routeTree } from "./routeTree.gen"

import { ApiError } from "./client"
import { CustomProvider } from "./components/ui/provider"
import { configureApiClient, clearAuthToken } from "./lib/api/client"

// Configure API client
configureApiClient()

const handleApiError = (error: Error) => {
  if (error instanceof ApiError && error.status === 401) {
    clearAuthToken()
    window.location.href = "/login"
  }
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

const router = createRouter({ routeTree })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <CustomProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </CustomProvider>
  </StrictMode>,
)
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Main app updated to use new API client configuration, no TypeScript errors.

---

### Step 9: Update Authentication Hook Usage
**Goal:** Replace the old authentication hook with the new one.

**Actions:**
- MODIFY: `src/routes/_layout.tsx`
- MODIFY: `src/routes/_layout/index.tsx`
- MODIFY: `src/components/Common/Sidebar.tsx`

**Code changes:**
```typescript
// src/routes/_layout.tsx
import { Flex } from "@chakra-ui/react"
import { Outlet, createFileRoute, redirect } from "@tanstack/react-router"

import Sidebar from "@/components/Common/Sidebar"
import { isAuthenticated } from "@/lib/api/client"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    if (!isAuthenticated()) {
      throw redirect({
        to: "/login",
      })
    }
  },
})

function Layout() {
  return (
    <Flex direction="column" h="100vh">
      <Flex flex="1" overflow="hidden">
        <Sidebar />
        <Flex flex="1" direction="column" p={4} overflowY="auto">
          <Outlet />
        </Flex>
      </Flex>
    </Flex>
  )
}

export default Layout
```

```typescript
// src/routes/_layout/index.tsx
import {
  Box,
  Container,
  HStack,
  SimpleGrid,
  Text,
  VStack,
} from "@chakra-ui/react"
import { Link as RouterLink, createFileRoute } from "@tanstack/react-router"

import { HelpPanel } from "@/components/Dashboard/HelpPanel"
import { QuizGenerationPanel } from "@/components/Dashboard/QuizGenerationPanel"
import { QuizReviewPanel } from "@/components/Dashboard/QuizReviewPanel"
import { OnboardingModal } from "@/components/Onboarding/OnboardingModal"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/auth"
import { useUserQuizzes } from "@/hooks/api"
import useCustomToast from "@/hooks/useCustomToast"
import { useOnboarding } from "@/hooks/useOnboarding"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const { showErrorToast } = useCustomToast()
  const {
    currentStep,
    isOpen,
    nextStep,
    previousStep,
    markOnboardingCompleted,
    skipOnboarding,
  } = useOnboarding()

  const {
    data: quizzes,
    isLoading,
    error,
  } = useUserQuizzes()

  if (error) {
    showErrorToast("Failed to load quizzes")
    return (
      <Container maxW="6xl" py={8}>
        <VStack gap={6} align="stretch">
          <Box>
            <Text fontSize="3xl" fontWeight="bold" color="red.500">
              Error Loading Dashboard
            </Text>
            <Text color="gray.600">
              There was an error loading your dashboard. Please try refreshing
              the page.
            </Text>
          </Box>
        </VStack>
      </Container>
    )
  }

  return (
    <>
      <Container maxW="6xl" py={8} data-testid="dashboard-container">
        <VStack gap={6} align="stretch">
          {/* Header */}
          <HStack justify="space-between" align="center">
            <Box>
              <Text fontSize="3xl" fontWeight="bold">
                Hi, {currentUser?.name} 👋🏼
              </Text>
              <Text color="gray.600">
                Welcome back! Here's an overview of your quizzes and helpful
                resources.
              </Text>
            </Box>
            <Button asChild>
              <RouterLink to="/create-quiz">Create New Quiz</RouterLink>
            </Button>
          </HStack>

          {/* Dashboard Panels */}
          <SimpleGrid
            columns={{ base: 1, md: 2, lg: 3 }}
            gap={6}
            data-testid="dashboard-grid"
          >
            <QuizReviewPanel quizzes={quizzes || []} isLoading={isLoading} />
            <QuizGenerationPanel
              quizzes={quizzes || []}
              isLoading={isLoading}
            />
            <HelpPanel />
          </SimpleGrid>
        </VStack>
      </Container>

      <OnboardingModal
        isOpen={isOpen}
        currentStep={currentStep}
        onNext={nextStep}
        onPrevious={previousStep}
        onComplete={markOnboardingCompleted}
        onSkip={skipOnboarding}
      />
    </>
  )
}
```

```typescript
// src/components/Common/Sidebar.tsx
import { Box, Button, Flex, Image } from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"

import Logo from "/assets/images/logo.svg"

import { useAuth } from "@/hooks/auth"
import SidebarItems from "./SidebarItems"

const Sidebar = () => {
  const { logout } = useAuth()

  const handleLogout = async () => {
    logout()
  }

  return (
    <>
      <Box
        position="sticky"
        bg="#013343"
        top={0}
        minW="150px"
        h="100vh"
        pl={4}
        data-testid="sidebar"
      >
        <Flex direction="column" w="100%" h="100%" alignItems="center">
          <Link to="/">
            <Image src={Logo} maxW="130px" p={2} />
          </Link>
          <Box w="100%">
            <SidebarItems />
          </Box>
          <Button onClick={handleLogout} w="90%" mt={4} colorPalette="blue">
            Log out
          </Button>
        </Flex>
      </Box>
    </>
  )
}

export default Sidebar
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Authentication hook usage updated, no TypeScript errors, login/logout should still work.

---

### Step 10: Update Quiz List Component
**Goal:** Use the new quiz hook in the quiz list component.

**Actions:**
- MODIFY: `src/routes/_layout/quizzes.tsx`
- MODIFY: `src/components/Dashboard/QuizGenerationPanel.tsx`
- MODIFY: `src/components/Dashboard/QuizReviewPanel.tsx`

**Code changes:**
```typescript
// src/routes/_layout/quizzes.tsx
import {
  Badge,
  Box,
  Card,
  Container,
  HStack,
  Skeleton,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react"
import { Link as RouterLink, createFileRoute } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import { useUserQuizzes } from "@/hooks/api"
import { formatDate } from "@/lib/utils"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/quizzes")({
  component: QuizList,
})

function QuizList() {
  const { showErrorToast } = useCustomToast()

  const {
    data: quizzes,
    isLoading,
    error,
  } = useUserQuizzes()

  if (isLoading) {
    return <QuizListSkeleton />
  }

  if (error) {
    showErrorToast("Failed to load quizzes")
    return (
      <Container maxW="6xl" py={8}>
        <Card.Root>
          <Card.Body>
            <VStack gap={4}>
              <Text fontSize="xl" fontWeight="bold" color="red.500">
                Failed to Load Quizzes
              </Text>
              <Text color="gray.600">
                There was an error loading your quizzes. Please try again.
              </Text>
            </VStack>
          </Card.Body>
        </Card.Root>
      </Container>
    )
  }

  return (
    <Container maxW="6xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <Box>
            <Text fontSize="3xl" fontWeight="bold">
              My Quizzes
            </Text>
            <Text color="gray.600">
              Manage and view all your created quizzes
            </Text>
          </Box>
          <Button asChild>
            <RouterLink to="/create-quiz">Create New Quiz</RouterLink>
          </Button>
        </HStack>

        {/* Quizzes Table */}
        {!quizzes || quizzes.length === 0 ? (
          <Card.Root>
            <Card.Body textAlign="center" py={12}>
              <VStack gap={4}>
                <Text fontSize="lg" fontWeight="semibold" color="gray.600">
                  No Quizzes Found
                </Text>
                <Text color="gray.500">
                  You haven't created any quizzes yet. Get started by creating
                  your first quiz.
                </Text>
                <Button asChild mt={4}>
                  <RouterLink to="/create-quiz">
                    Create Your First Quiz
                  </RouterLink>
                </Button>
              </VStack>
            </Card.Body>
          </Card.Root>
        ) : (
          <Card.Root>
            <Card.Body p={0}>
              <Table.Root>
                <Table.Header>
                  <Table.Row>
                    <Table.ColumnHeader>Quiz Title</Table.ColumnHeader>
                    <Table.ColumnHeader>Course</Table.ColumnHeader>
                    <Table.ColumnHeader>Questions</Table.ColumnHeader>
                    <Table.ColumnHeader>LLM Model</Table.ColumnHeader>
                    <Table.ColumnHeader>Status</Table.ColumnHeader>
                    <Table.ColumnHeader>Created</Table.ColumnHeader>
                    <Table.ColumnHeader>Actions</Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {quizzes.map((quiz) => {
                    // Get selected modules for display (already an object from API)
                    const selectedModules = quiz.selected_modules || {}
                    const moduleCount = Object.keys(selectedModules).length

                    return (
                      <Table.Row key={quiz.id}>
                        <Table.Cell>
                          <VStack align="start" gap={1}>
                            <Text fontWeight="medium">{quiz.title}</Text>
                            <Text fontSize="sm" color="gray.500">
                              {moduleCount} module{moduleCount !== 1 ? "s" : ""}{" "}
                              selected
                            </Text>
                          </VStack>
                        </Table.Cell>
                        <Table.Cell>
                          <VStack align="start" gap={1}>
                            <Text>{quiz.canvas_course_name}</Text>
                            <Text fontSize="sm" color="gray.500">
                              ID: {quiz.canvas_course_id}
                            </Text>
                          </VStack>
                        </Table.Cell>
                        <Table.Cell>
                          <Badge variant="solid" colorScheme="blue">
                            {quiz.question_count}
                          </Badge>
                        </Table.Cell>
                        <Table.Cell>
                          <Badge variant="outline" colorScheme="purple">
                            {quiz.llm_model}
                          </Badge>
                        </Table.Cell>
                        <Table.Cell>
                          <HStack gap={2} align="center">
                            <StatusLight
                              extractionStatus={
                                quiz.content_extraction_status || "pending"
                              }
                              generationStatus={
                                quiz.llm_generation_status || "pending"
                              }
                            />
                            <Text fontSize="sm" color="gray.600">
                              {(() => {
                                const extractionStatus =
                                  quiz.content_extraction_status || "pending"
                                const generationStatus =
                                  quiz.llm_generation_status || "pending"

                                if (
                                  extractionStatus === "failed" ||
                                  generationStatus === "failed"
                                ) {
                                  return "Failed"
                                }

                                if (
                                  extractionStatus === "completed" &&
                                  generationStatus === "completed"
                                ) {
                                  return "Complete"
                                }

                                if (
                                  extractionStatus === "processing" ||
                                  generationStatus === "processing"
                                ) {
                                  return "Processing"
                                }

                                return "Pending"
                              })()}
                            </Text>
                          </HStack>
                        </Table.Cell>
                        <Table.Cell>
                          <Text fontSize="sm">
                            {quiz.created_at
                              ? formatDate(quiz.created_at)
                              : "Unknown"}
                          </Text>
                        </Table.Cell>
                        <Table.Cell>
                          <HStack gap={2}>
                            <Button size="sm" variant="outline" asChild>
                              <RouterLink to={`/quiz/${quiz.id}`}>
                                View
                              </RouterLink>
                            </Button>
                          </HStack>
                        </Table.Cell>
                      </Table.Row>
                    )
                  })}
                </Table.Body>
              </Table.Root>
            </Card.Body>
          </Card.Root>
        )}
      </VStack>
    </Container>
  )
}

function QuizListSkeleton() {
  return (
    <Container maxW="6xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header Skeleton */}
        <HStack justify="space-between" align="center">
          <Box>
            <Skeleton height="36px" width="200px" mb={2} />
            <Skeleton height="20px" width="300px" />
          </Box>
          <Skeleton height="40px" width="150px" />
        </HStack>

        {/* Table Skeleton */}
        <Card.Root>
          <Card.Body p={0}>
            <VStack gap={4} p={6}>
              {[1, 2, 3, 4, 5].map((i) => (
                <HStack key={i} justify="space-between" width="100%">
                  <Skeleton height="20px" width="200px" />
                  <Skeleton height="20px" width="150px" />
                  <Skeleton height="20px" width="60px" />
                  <Skeleton height="20px" width="80px" />
                  <Skeleton height="20px" width="100px" />
                  <Skeleton height="32px" width="60px" />
                </HStack>
              ))}
            </VStack>
          </Card.Body>
        </Card.Root>
      </VStack>
    </Container>
  )
}
```

```typescript
// src/components/Dashboard/QuizGenerationPanel.tsx
import {
  Badge,
  Box,
  Card,
  HStack,
  Progress,
  Skeleton,
  Text,
  VStack,
} from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"

import type { Quiz } from "@/client/types.gen"
import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import { getQuizProcessingPhase, getQuizzesBeingGenerated } from "@/lib/utils"

interface QuizGenerationPanelProps {
  quizzes: Quiz[]
  isLoading: boolean
}

export function QuizGenerationPanel({
  quizzes,
  isLoading,
}: QuizGenerationPanelProps) {
  const generatingQuizzes = getQuizzesBeingGenerated(quizzes)

  if (isLoading) {
    return <QuizGenerationPanelSkeleton />
  }

  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <Text fontSize="lg" fontWeight="semibold">
            Quizzes Being Generated
          </Text>
          <Badge variant="outline" colorScheme="orange" data-testid="badge">
            {generatingQuizzes.length}
          </Badge>
        </HStack>
        <Text fontSize="sm" color="gray.600">
          Quizzes currently in progress
        </Text>
      </Card.Header>
      <Card.Body>
        {generatingQuizzes.length === 0 ? (
          <Box textAlign="center" py={6}>
            <Text fontSize="sm" color="gray.500" mb={2}>
              No quizzes being generated
            </Text>
            <Text fontSize="sm" color="gray.400">
              Start creating a quiz to see generation progress here
            </Text>
            <Button size="sm" variant="outline" asChild mt={4}>
              <RouterLink to="/create-quiz">Create New Quiz</RouterLink>
            </Button>
          </Box>
        ) : (
          <VStack gap={4} align="stretch">
            {generatingQuizzes.slice(0, 4).map((quiz) => {
              const processingPhase = getQuizProcessingPhase(quiz)

              // Calculate progress percentage
              const extractionStatus =
                quiz.content_extraction_status || "pending"
              const generationStatus = quiz.llm_generation_status || "pending"

              let progressPercentage = 0
              if (extractionStatus === "completed") {
                progressPercentage = 50
              }
              if (generationStatus === "completed") {
                progressPercentage = 100
              }
              if (extractionStatus === "processing") {
                progressPercentage = 25
              }
              if (generationStatus === "processing") {
                progressPercentage = 75
              }

              return (
                <Box
                  key={quiz.id}
                  p={4}
                  border="1px solid"
                  borderColor="orange.200"
                  borderRadius="md"
                  bg="orange.50"
                  _hover={{ bg: "orange.100" }}
                  transition="background-color 0.2s"
                >
                  <VStack align="stretch" gap={3}>
                    <HStack justify="space-between" align="start">
                      <VStack align="start" gap={1} flex={1}>
                        <Text
                          fontWeight="medium"
                          fontSize="sm"
                          lineHeight="tight"
                        >
                          {quiz.title}
                        </Text>
                        <Text fontSize="xs" color="gray.600">
                          {quiz.canvas_course_name}
                        </Text>
                      </VStack>
                      <HStack gap={2}>
                        <StatusLight
                          extractionStatus={
                            quiz.content_extraction_status || "pending"
                          }
                          generationStatus={
                            quiz.llm_generation_status || "pending"
                          }
                        />
                      </HStack>
                    </HStack>

                    <Box>
                      <HStack justify="space-between" mb={2}>
                        <Text
                          fontSize="xs"
                          color="gray.700"
                          fontWeight="medium"
                        >
                          {processingPhase}
                        </Text>
                        <Text fontSize="xs" color="gray.600">
                          {progressPercentage}%
                        </Text>
                      </HStack>
                      <Progress.Root
                        value={progressPercentage}
                        size="sm"
                        colorPalette="orange"
                      >
                        <Progress.Track>
                          <Progress.Range />
                        </Progress.Track>
                      </Progress.Root>
                    </Box>

                    <HStack justify="space-between" align="center">
                      <HStack gap={2}>
                        <Badge variant="solid" colorScheme="blue" size="sm">
                          {quiz.question_count} questions
                        </Badge>
                        {quiz.llm_model && (
                          <Badge
                            variant="outline"
                            colorScheme="purple"
                            size="sm"
                          >
                            {quiz.llm_model}
                          </Badge>
                        )}
                      </HStack>

                      <Button size="sm" variant="outline" asChild>
                        <RouterLink
                          to="/quiz/$id"
                          params={{ id: quiz.id || "" }}
                        >
                          View Details
                        </RouterLink>
                      </Button>
                    </HStack>
                  </VStack>
                </Box>
              )
            })}

            {generatingQuizzes.length > 4 && (
              <Box textAlign="center" pt={2}>
                <Text fontSize="sm" color="gray.500">
                  +{generatingQuizzes.length - 4} more quizzes in progress
                </Text>
                <Button size="sm" variant="ghost" asChild mt={2}>
                  <RouterLink to="/quizzes">View All Quizzes</RouterLink>
                </Button>
              </Box>
            )}
          </VStack>
        )}
      </Card.Body>
    </Card.Root>
  )
}

function QuizGenerationPanelSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <Skeleton height="24px" width="180px" />
          <Skeleton height="20px" width="30px" />
        </HStack>
        <Skeleton height="16px" width="200px" mt={2} />
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          {[1, 2].map((i) => (
            <Box
              key={i}
              p={4}
              border="1px solid"
              borderColor="orange.200"
              borderRadius="md"
              bg="orange.50"
            >
              <VStack align="stretch" gap={3}>
                <HStack justify="space-between" align="start">
                  <VStack align="start" gap={1} flex={1}>
                    <Skeleton height="16px" width="140px" />
                    <Skeleton height="12px" width="100px" />
                  </VStack>
                  <Skeleton height="12px" width="12px" borderRadius="full" />
                </HStack>

                <Box>
                  <HStack justify="space-between" mb={2}>
                    <Skeleton height="12px" width="120px" />
                    <Skeleton height="12px" width="30px" />
                  </HStack>
                  <Skeleton height="6px" width="100%" />
                </Box>

                <HStack justify="space-between" align="center">
                  <HStack gap={2}>
                    <Skeleton height="20px" width="80px" />
                    <Skeleton height="20px" width="60px" />
                  </HStack>
                  <Skeleton height="24px" width="80px" />
                </HStack>
              </VStack>
            </Box>
          ))}
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Quiz components updated to use new utilities, no TypeScript errors, dashboard should work normally.

---

## Checkpoint: Foundation Phase Complete

At this point, you should have:
- ✅ New directory structure created
- ✅ Constants centralized
- ✅ Error handling utilities in place
- ✅ API client refactored
- ✅ Authentication hook updated
- ✅ Quiz hooks created
- ✅ Utility functions organized
- ✅ All components updated to use new hooks/utilities

**Test the application:**
1. Run `npm run build` - should succeed
2. Run `npm run lint` - should pass
3. Test login/logout functionality
4. Test dashboard loading
5. Test quiz list page
6. Verify all existing functionality still works

**Continue to Phase 2 when ready:** The next phase will focus on component refactoring and breaking down large components into smaller, more manageable pieces.

---

## Phase 2: Component Refactoring (Steps 11-20)

### Step 11: Create Question Display Component Structure
**Goal:** Break down the large QuestionDisplay component into smaller, focused components.

**Actions:**
- CREATE: `src/components/questions/display/QuestionDisplay.tsx`
- CREATE: `src/components/questions/display/MCQDisplay.tsx`
- CREATE: `src/components/questions/display/TrueFalseDisplay.tsx`
- CREATE: `src/components/questions/display/ShortAnswerDisplay.tsx`
- CREATE: `src/components/questions/display/EssayDisplay.tsx`
- CREATE: `src/components/questions/display/FillInBlankDisplay.tsx`
- CREATE: `src/components/questions/display/UnsupportedDisplay.tsx`
- CREATE: `src/components/questions/display/ErrorDisplay.tsx`
- CREATE: `src/components/questions/display/index.ts`

**Code changes:**
```typescript
// src/components/questions/display/QuestionDisplay.tsx
import type { QuestionResponse } from "@/client"
import { QUESTION_TYPES } from "@/lib/constants"
import { MCQDisplay } from "./MCQDisplay"
import { TrueFalseDisplay } from "./TrueFalseDisplay"
import { ShortAnswerDisplay } from "./ShortAnswerDisplay"
import { EssayDisplay } from "./EssayDisplay"
import { FillInBlankDisplay } from "./FillInBlankDisplay"
import { UnsupportedDisplay } from "./UnsupportedDisplay"

interface QuestionDisplayProps {
  question: QuestionResponse
  showCorrectAnswer?: boolean
  showExplanation?: boolean
}

export function QuestionDisplay({
  question,
  showCorrectAnswer = false,
  showExplanation = false,
}: QuestionDisplayProps) {
  const commonProps = {
    question,
    showCorrectAnswer,
    showExplanation,
  }

  switch (question.question_type) {
    case QUESTION_TYPES.MULTIPLE_CHOICE:
      return <MCQDisplay {...commonProps} />
    case QUESTION_TYPES.TRUE_FALSE:
      return <TrueFalseDisplay {...commonProps} />
    case QUESTION_TYPES.SHORT_ANSWER:
      return <ShortAnswerDisplay {...commonProps} />
    case QUESTION_TYPES.ESSAY:
      return <EssayDisplay {...commonProps} />
    case QUESTION_TYPES.FILL_IN_BLANK:
      return <FillInBlankDisplay {...commonProps} />
    default:
      return <UnsupportedDisplay questionType={question.question_type} />
  }
}
```

Continue with the remaining steps in this manner...

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Question display components created, no TypeScript errors.

**Note:** This plan continues for approximately 50+ more steps covering all aspects of the refactoring. Would you like me to continue with the complete implementation plan, or would you prefer to start with these first 10 steps and proceed incrementally?

---

## Next Steps Preview

The remaining phases will cover:
- **Phase 2 (Steps 11-20):** Component refactoring and breaking down large components
- **Phase 3 (Steps 21-30):** Performance optimizations and memoization
- **Phase 4 (Steps 31-40):** Code splitting and lazy loading
- **Phase 5 (Steps 41-50):** Testing improvements and cleanup
- **Phase 6 (Steps 51-60):** Final optimizations and documentation

Each step will follow the same detailed format with explicit file changes, type checking, and expected outcomes.
