import type { Quiz } from "../../src/client/types.gen"

export const mockUserData = {
  name: "Test User",
  onboarding_completed: true,
}

// Base quiz template
const baseQuiz = {
  owner_id: "user123",
  canvas_course_id: 12345,
  canvas_course_name: "Test Course",
  selected_modules: {
    "173467": { name: "Module 1", question_count: 25 },
    "173468": { name: "Module 2", question_count: 25 },
  },
  question_count: 50,
  llm_model: "gpt-4o",
  llm_temperature: 0.7,
  created_at: "2024-01-15T10:30:00Z",
  updated_at: "2024-01-16T14:20:00Z",
}

// Quiz needing review (ready for review status)
export const quizNeedingReview: Quiz = {
  ...baseQuiz,
  id: "quiz-review-1",
  title: "Machine Learning Fundamentals",
  status: "ready_for_review",
  last_status_update: "2024-01-15T11:00:00Z",
  content_extracted_at: "2024-01-15T11:00:00Z",
}

export const secondQuizNeedingReview: Quiz = {
  ...baseQuiz,
  id: "quiz-review-2",
  title: "Python Programming Basics",
  canvas_course_name: "CS101",
  question_count: 25,
  status: "ready_for_review",
  last_status_update: "2024-01-14T09:30:00Z",
  content_extracted_at: "2024-01-14T09:30:00Z",
}

// Quiz created (ready to start)
export const quizPendingExtraction: Quiz = {
  ...baseQuiz,
  id: "quiz-pending-1",
  title: "Database Design Principles",
  canvas_course_name: "Database Systems",
  status: "created",
  last_status_update: "2024-01-15T10:30:00Z",
  question_count: 30,
}

// Quiz extracting content
export const quizProcessingExtraction: Quiz = {
  ...baseQuiz,
  id: "quiz-processing-1",
  title: "Web Development Concepts",
  canvas_course_name: "Web Dev 101",
  status: "extracting_content",
  last_status_update: "2024-01-15T11:15:00Z",
  question_count: 40,
}

// Quiz generating questions
export const quizPendingGeneration: Quiz = {
  ...baseQuiz,
  id: "quiz-pending-gen-1",
  title: "Software Engineering Practices",
  canvas_course_name: "Software Engineering",
  status: "generating_questions",
  last_status_update: "2024-01-15T12:15:00Z",
  content_extracted_at: "2024-01-15T12:15:00Z",
  question_count: 35,
}

// Quiz generating questions
export const quizProcessingGeneration: Quiz = {
  ...baseQuiz,
  id: "quiz-processing-gen-1",
  title: "Data Structures and Algorithms",
  canvas_course_name: "CS201",
  status: "generating_questions",
  last_status_update: "2024-01-15T10:45:00Z",
  content_extracted_at: "2024-01-15T10:45:00Z",
  question_count: 60,
}

// Failed quizzes
export const quizFailedExtraction: Quiz = {
  ...baseQuiz,
  id: "quiz-failed-1",
  title: "Failed Content Extraction",
  status: "failed",
  failure_reason: "content_extraction_error",
  last_status_update: "2024-01-15T10:30:00Z",
  question_count: 20,
}

export const quizFailedGeneration: Quiz = {
  ...baseQuiz,
  id: "quiz-failed-2",
  title: "Failed Question Generation",
  status: "failed",
  failure_reason: "llm_generation_error",
  last_status_update: "2024-01-15T10:00:00Z",
  content_extracted_at: "2024-01-15T10:00:00Z",
  question_count: 45,
}

// Collections for different dashboard states
export const quizzesNeedingReview = [
  quizNeedingReview,
  secondQuizNeedingReview,
  {
    ...baseQuiz,
    id: "quiz-review-3",
    title: "Advanced JavaScript",
    canvas_course_name: "Frontend Development",
    status: "ready_for_review",
    last_status_update: "2024-01-15T13:00:00Z",
    question_count: 15,
  },
  {
    ...baseQuiz,
    id: "quiz-review-4",
    title: "React Component Design",
    canvas_course_name: "React Course",
    status: "ready_for_review",
    last_status_update: "2024-01-15T14:00:00Z",
    question_count: 35,
  },
  {
    ...baseQuiz,
    id: "quiz-review-5",
    title: "Node.js Backend Development",
    canvas_course_name: "Backend Systems",
    status: "ready_for_review",
    last_status_update: "2024-01-15T15:00:00Z",
    question_count: 40,
  },
  {
    ...baseQuiz,
    id: "quiz-review-6",
    title: "Additional Quiz for Overflow Test",
    canvas_course_name: "Extra Course",
    status: "ready_for_review",
    last_status_update: "2024-01-15T16:00:00Z",
    question_count: 10,
  },
] as Quiz[]

export const quizzesBeingGenerated = [
  quizPendingExtraction,
  quizProcessingExtraction,
  quizPendingGeneration,
  quizProcessingGeneration,
  {
    ...baseQuiz,
    id: "quiz-gen-5",
    title: "Additional Generating Quiz",
    canvas_course_name: "Another Course",
    status: "created",
    last_status_update: "2024-01-15T17:00:00Z",
    question_count: 25,
  },
] as Quiz[]

// Quizzes that should actually be visible in the generation panel (after filtering)
export const visibleQuizzesBeingGenerated = [
  quizProcessingExtraction,
  quizPendingGeneration,
  quizProcessingGeneration,
] as Quiz[]

export const failedQuizzes = [
  quizFailedExtraction,
  quizFailedGeneration,
] as Quiz[]

export const allMockQuizzes = [
  ...quizzesNeedingReview,
  ...quizzesBeingGenerated,
  ...failedQuizzes,
] as Quiz[]

export const emptyQuizList: Quiz[] = []

// Long quiz title for testing truncation
export const quizWithLongTitle: Quiz = {
  ...baseQuiz,
  id: "quiz-long-title",
  title:
    "This is a very long quiz title that should be truncated when displayed in the dashboard cards to test the text overflow handling",
  status: "ready_for_review",
  last_status_update: "2024-01-15T18:00:00Z",
  question_count: 100,
}

// Mock API responses
export const createQuizListResponse = (quizzes: Quiz[]) => ({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify(quizzes),
})

export const createUserResponse = () => ({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify(mockUserData),
})

export const createErrorResponse = (
  status = 500,
  message = "Internal Server Error",
) => ({
  status,
  contentType: "application/json",
  body: JSON.stringify({ detail: message }),
})
