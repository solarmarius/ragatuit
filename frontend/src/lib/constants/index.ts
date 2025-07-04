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
