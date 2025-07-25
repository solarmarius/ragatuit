# Frontend API Usage Patterns

This document outlines how frontend components interact with the backend API after the polymorphic question system migration.

## Overview

The frontend has been migrated to work with the new polymorphic question API while maintaining backward compatibility through a compatibility layer in `/src/utils/questionCompatibility.ts`.

## API Service Structure

### Question API (QuestionsService)
The new question endpoints use polymorphic structure with separate service:

- **Base Path**: `/api/v1/questions/`
- **Authentication**: JWT Bearer token required
- **Response Format**: Polymorphic with `question_type` and `question_data`

### Quiz API (QuizService)
Quiz management endpoints remain largely unchanged:

- **Base Path**: `/api/v1/quiz/`
- **Authentication**: JWT Bearer token required

## Component API Usage Patterns

### 1. QuestionReview Component
**File**: `/src/components/Questions/QuestionReview.tsx`

#### Data Fetching
```typescript
const { data: questions } = useQuery({
  queryKey: ["quiz", quizId, "questions"],
  queryFn: async () => {
    const response = await QuestionsService.getQuizQuestions({
      quizId,
      approvedOnly: false // Get all questions for review
    })
    // Convert new polymorphic structure to legacy format for compatibility
    return response.map(convertToLegacyQuestion)
  },
})
```

#### Question Operations
```typescript
// Approve Question
const approveQuestionMutation = useMutation({
  mutationFn: async (questionId: string) => {
    return await QuestionsService.approveQuestion({
      quizId,
      questionId,
    })
  },
})

// Update Question
const updateQuestionMutation = useMutation({
  mutationFn: async ({ questionId, data }) => {
    return await QuestionsService.updateQuestion({
      quizId,
      questionId,
      requestBody: {
        question_data: {
          question_text: data.questionText,
          option_a: data.optionA,
          // ... other MCQ fields
        },
      },
    })
  },
})

// Delete Question
const deleteQuestionMutation = useMutation({
  mutationFn: async (questionId: string) => {
    return await QuestionsService.deleteQuestion({
      quizId,
      questionId,
    })
  },
})
```

#### Key Changes from Legacy:
- **Endpoint**: `/quiz/{id}/questions` → `/questions/{quiz_id}`
- **Update Payload**: Flat MCQ fields → Nested `question_data` object
- **Response**: Converted to legacy format via `convertToLegacyQuestion()`

### 2. QuestionGenerationTrigger Component
**File**: `/src/components/Questions/QuestionGenerationTrigger.tsx`

#### Generation Request
```typescript
const triggerGenerationMutation = useMutation({
  mutationFn: async () => {
    const generationRequest: GenerationRequest = {
      quiz_id: quiz.id,
      question_type: "multiple_choice",
      target_count: quiz.question_count || 10,
      difficulty: null,
      tags: null,
      custom_instructions: null,
      provider_name: null,
      workflow_name: null,
      template_name: null,
    }

    return await QuestionsService.generateQuestions({
      quizId: quiz.id,
      requestBody: generationRequest
    })
  },
})
```

#### Key Changes from Legacy:
- **Endpoint**: `/quiz/{id}/generate-questions` → `/questions/{quiz_id}/generate`
- **Payload**: Simple trigger → Full `GenerationRequest` object
- **Response**: Enhanced with generation metadata and statistics

### 3. QuestionStats Component
**File**: `/src/components/Questions/QuestionStats.tsx`

#### Statistics Fetching
```typescript
const { data: stats } = useQuery({
  queryKey: ["quiz", quiz.id, "questions", "stats"],
  queryFn: async () => {
    const fullStats = await QuestionsService.getQuestionStatistics({
      quizId: quiz.id
    })
    // Convert to legacy format for compatibility
    return {
      total: fullStats.total_questions,
      approved: fullStats.approved_questions,
    }
  },
})
```

#### Key Changes from Legacy:
- **Endpoint**: `/quiz/{id}/questions/stats` → `/questions/{quiz_id}/statistics`
- **Response**: Enhanced statistics with type breakdown and approval rates
- **Compatibility**: Converted to simple `{total, approved}` format

### 4. Quiz Detail Page
**File**: `/src/routes/_layout/quiz.$id.tsx`

#### Quiz Data Fetching
```typescript
const { data: quiz } = useQuery({
  queryKey: ["quiz", id],
  queryFn: async () => {
    return await QuizService.getQuiz({ quizId: id })
  },
  refetchInterval: (query) => {
    // Poll every 5 seconds if any status is pending or processing
    const data = query?.state?.data
    if (data) {
      const extractionStatus = data.content_extraction_status || "pending"
      const generationStatus = data.llm_generation_status || "pending"
      const exportStatus = data.export_status || "pending"

      if (["pending", "processing"].includes(extractionStatus) ||
          ["pending", "processing"].includes(generationStatus) ||
          ["pending", "processing"].includes(exportStatus)) {
        return 5000 // Poll every 5 seconds
      }
    }
    return false // Stop polling
  },
})
```

#### Content Extraction Retry
```typescript
const retryExtractionMutation = useMutation({
  mutationFn: async () => {
    return await QuizService.triggerContentExtraction({ quizId: id })
  },
})
```

## Data Transformation Patterns

### Compatibility Layer
**File**: `/src/utils/questionCompatibility.ts`

#### Legacy to Polymorphic Conversion
```typescript
// Convert old flat structure to new polymorphic format
export function convertFromLegacyQuestion(
  legacyQuestion: LegacyQuestionPublic
): QuestionResponse {
  return {
    id: legacyQuestion.id,
    quiz_id: legacyQuestion.quiz_id,
    question_type: "multiple_choice",
    question_data: {
      question_text: legacyQuestion.question_text,
      option_a: legacyQuestion.option_a,
      option_b: legacyQuestion.option_b,
      option_c: legacyQuestion.option_c,
      option_d: legacyQuestion.option_d,
      correct_answer: legacyQuestion.correct_answer,
    },
    // ... other fields
  }
}
```

#### Polymorphic to Legacy Conversion
```typescript
// Convert new polymorphic structure to legacy flat format
export function convertToLegacyQuestion(
  question: QuestionResponse
): LegacyQuestionPublic {
  const mcqData = extractMCQData(question)

  return {
    id: question.id,
    quiz_id: question.quiz_id,
    question_text: mcqData.question_text,
    option_a: mcqData.option_a,
    option_b: mcqData.option_b,
    option_c: mcqData.option_c,
    option_d: mcqData.option_d,
    correct_answer: mcqData.correct_answer,
    is_approved: question.is_approved,
    // ... other fields
  }
}
```

## Query Key Patterns

### Consistent Query Keys
The frontend uses consistent query key patterns for caching and invalidation:

```typescript
// Quiz queries
["quiz", quizId]                           // Single quiz
["quiz"]                                   // All user quizzes

// Question queries
["quiz", quizId, "questions"]              // All questions for quiz
["quiz", quizId, "questions", "stats"]     // Question statistics
["question", questionId]                   // Single question (if needed)
```

### Cache Invalidation Strategy
```typescript
// After question operations, invalidate related queries
queryClient.invalidateQueries({
  queryKey: ["quiz", quizId, "questions"],
})
queryClient.invalidateQueries({
  queryKey: ["quiz", quizId, "questions", "stats"],
})
```

## Error Handling Patterns

### Consistent Error Processing
```typescript
const mutation = useMutation({
  mutationFn: async (data) => {
    return await ApiService.someOperation(data)
  },
  onError: (error: any) => {
    const message = error?.body?.detail || "Operation failed"
    showErrorToast(message)
  },
})
```

### API Error Structure
The backend returns errors in this format:
```typescript
{
  body: {
    detail: "Human-readable error message"
  },
  status: 400|401|403|404|500
}
```

## Background Operations

### Polling for Status Updates
```typescript
refetchInterval: (query) => {
  const data = query?.state?.data
  if (data?.some_status === "processing") {
    return 5000 // Poll every 5 seconds
  }
  return false // Stop polling when complete
},
refetchIntervalInBackground: false // Only poll when tab is active
```

### Background Task Triggers
```typescript
// Quiz creation triggers background content extraction
const createQuizMutation = useMutation({
  mutationFn: async (quizData) => {
    return await QuizService.createNewQuiz({ requestBody: quizData })
  },
  onSuccess: (quiz) => {
    // Background content extraction started automatically
    // Poll quiz status to track progress
    queryClient.invalidateQueries({ queryKey: ["quiz", quiz.id] })
  },
})
```

## Migration Notes

### Current State
- ✅ **Core components migrated**: QuestionReview, QuestionGenerationTrigger, QuestionStats
- ✅ **Compatibility layer active**: Automatic conversion between old/new formats
- ✅ **Build successful**: No TypeScript errors
- ✅ **API endpoints updated**: Using new polymorphic question endpoints

### Future Improvements
1. **Remove compatibility layer** once confident in new system
2. **Direct polymorphic usage** in components (skip legacy conversion)
3. **Enhanced error handling** for new question types
4. **Type safety improvements** with stronger typing for question_data

### Breaking Changes Handled
- ✅ Question API endpoint paths
- ✅ Question data structure (flat → polymorphic)
- ✅ Generation API payload structure
- ✅ Statistics response format
- ✅ Method name changes (e.g., `approveQuizQuestion` → `approveQuestion`)

This migration maintains full backward compatibility while enabling the frontend to work with the new polymorphic question system.
