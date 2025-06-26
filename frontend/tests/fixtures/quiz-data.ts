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
  selected_modules: '{"173467": "Module 1", "173468": "Module 2"}',
  question_count: 50,
  llm_model: "gpt-4o",
  llm_temperature: 0.7,
  created_at: "2024-01-15T10:30:00Z",
  updated_at: "2024-01-16T14:20:00Z",
}

// Quiz needing review (both statuses completed)
export const quizNeedingReview: Quiz = {
  ...baseQuiz,
  id: "quiz-review-1",
  title: "Machine Learning Fundamentals",
  content_extraction_status: "completed",
  llm_generation_status: "completed",
  content_extracted_at: "2024-01-15T11:00:00Z",
}

export const secondQuizNeedingReview: Quiz = {
  ...baseQuiz,
  id: "quiz-review-2",
  title: "Python Programming Basics",
  canvas_course_name: "CS101",
  question_count: 25,
  content_extraction_status: "completed",
  llm_generation_status: "completed",
  content_extracted_at: "2024-01-14T09:30:00Z",
}

// Quiz being generated (pending content extraction)
export const quizPendingExtraction: Quiz = {
  ...baseQuiz,
  id: "quiz-pending-1",
  title: "Database Design Principles",
  canvas_course_name: "Database Systems",
  content_extraction_status: "pending",
  llm_generation_status: "pending",
  question_count: 30,
}

// Quiz with processing content extraction
export const quizProcessingExtraction: Quiz = {
  ...baseQuiz,
  id: "quiz-processing-1",
  title: "Web Development Concepts",
  canvas_course_name: "Web Dev 101",
  content_extraction_status: "processing",
  llm_generation_status: "pending",
  question_count: 40,
}

// Quiz pending LLM generation (extraction completed)
export const quizPendingGeneration: Quiz = {
  ...baseQuiz,
  id: "quiz-pending-gen-1",
  title: "Software Engineering Practices",
  canvas_course_name: "Software Engineering",
  content_extraction_status: "completed",
  llm_generation_status: "pending",
  content_extracted_at: "2024-01-15T12:15:00Z",
  question_count: 35,
}

// Quiz with processing LLM generation
export const quizProcessingGeneration: Quiz = {
  ...baseQuiz,
  id: "quiz-processing-gen-1",
  title: "Data Structures and Algorithms",
  canvas_course_name: "CS201",
  content_extraction_status: "completed",
  llm_generation_status: "processing",
  content_extracted_at: "2024-01-15T10:45:00Z",
  question_count: 60,
}

// Failed quizzes
export const quizFailedExtraction: Quiz = {
  ...baseQuiz,
  id: "quiz-failed-1",
  title: "Failed Content Extraction",
  content_extraction_status: "failed",
  llm_generation_status: "pending",
  question_count: 20,
}

export const quizFailedGeneration: Quiz = {
  ...baseQuiz,
  id: "quiz-failed-2",
  title: "Failed Question Generation",
  content_extraction_status: "completed",
  llm_generation_status: "failed",
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
    content_extraction_status: "completed",
    llm_generation_status: "completed",
    question_count: 15,
  },
  {
    ...baseQuiz,
    id: "quiz-review-4",
    title: "React Component Design",
    canvas_course_name: "React Course",
    content_extraction_status: "completed",
    llm_generation_status: "completed",
    question_count: 35,
  },
  {
    ...baseQuiz,
    id: "quiz-review-5",
    title: "Node.js Backend Development",
    canvas_course_name: "Backend Systems",
    content_extraction_status: "completed",
    llm_generation_status: "completed",
    question_count: 40,
  },
  {
    ...baseQuiz,
    id: "quiz-review-6",
    title: "Additional Quiz for Overflow Test",
    canvas_course_name: "Extra Course",
    content_extraction_status: "completed",
    llm_generation_status: "completed",
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
    content_extraction_status: "pending",
    llm_generation_status: "pending",
    question_count: 25,
  },
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
  content_extraction_status: "completed",
  llm_generation_status: "completed",
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
