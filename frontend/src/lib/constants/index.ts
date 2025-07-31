// =============================================================================
// API Constants
// =============================================================================

export const API_ROUTES = {
  AUTH: {
    LOGIN_CANVAS: "/api/v1/auth/login/canvas",
    LOGOUT_CANVAS: "/api/v1/auth/logout/canvas",
  },
  USERS: {
    ME: "/api/v1/users/me",
  },
  QUIZ: {
    USER_QUIZZES: "/api/v1/quiz/user",
  },
} as const

export const QUERY_KEYS = {
  CURRENT_USER: ["currentUser"],
  USER_QUIZZES: ["user-quizzes"],
} as const

// =============================================================================
// Application Constants
// =============================================================================

export const STORAGE_KEYS = {
  ACCESS_TOKEN: "access_token",
  ONBOARDING_COMPLETED: "onboarding_completed",
} as const

export const QUESTION_TYPES = {
  MULTIPLE_CHOICE: "multiple_choice",
  FILL_IN_BLANK: "fill_in_blank",
  MATCHING: "matching",
  CATEGORIZATION: "categorization",
  TRUE_FALSE: "true_false",
} as const

export const QUESTION_TYPE_LABELS = {
  multiple_choice: "Multiple Choice",
  fill_in_blank: "Fill in the Blank",
  matching: "Matching",
  categorization: "Categorization",
  true_false: "True/False",
} as const

export const QUESTION_DIFFICULTIES = {
  EASY: "easy",
  MEDIUM: "medium",
  HARD: "hard",
} as const

export const QUESTION_DIFFICULTY_LABELS = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
} as const

export const QUESTION_DIFFICULTY_DESCRIPTIONS = {
  easy: "Basic recall and simple comprehension",
  medium: "Application and moderate problem-solving",
  hard: "Complex analysis and critical thinking",
} as const

export const QUIZ_LANGUAGES = {
  ENGLISH: "en",
  NORWEGIAN: "no",
} as const

export const QUIZ_LANGUAGE_LABELS = {
  en: "English",
  no: "Norwegian",
} as const

export const QUIZ_TONES = {
  ACADEMIC: "academic",
  CASUAL: "casual",
  ENCOURAGING: "encouraging",
  PROFESSIONAL: "professional",
} as const

export const QUIZ_TONE_LABELS = {
  academic: "Formal/Academic",
  casual: "Casual/Conversational",
  encouraging: "Friendly/Encouraging",
  professional: "Professional/Business",
} as const

export const QUIZ_STATUS = {
  CREATED: "created",
  EXTRACTING_CONTENT: "extracting_content",
  GENERATING_QUESTIONS: "generating_questions",
  READY_FOR_REVIEW: "ready_for_review",
  READY_FOR_REVIEW_PARTIAL: "ready_for_review_partial",
  EXPORTING_TO_CANVAS: "exporting_to_canvas",
  PUBLISHED: "published",
  FAILED: "failed",
} as const

export const FAILURE_REASON = {
  CONTENT_EXTRACTION_ERROR: "content_extraction_error",
  NO_CONTENT_FOUND: "no_content_found",
  LLM_GENERATION_ERROR: "llm_generation_error",
  NO_QUESTIONS_GENERATED: "no_questions_generated",
  CANVAS_EXPORT_ERROR: "canvas_export_error",
  NETWORK_ERROR: "network_error",
  VALIDATION_ERROR: "validation_error",
} as const

// =============================================================================
// UI Constants
// =============================================================================

export const UI_SIZES = {
  // Common spacing
  SPACING: {
    XS: "2px",
    SM: "4px",
    MD: "8px",
    LG: "16px",
    XL: "24px",
    XXL: "32px",
  },

  // Loading skeleton dimensions
  SKELETON: {
    HEIGHT: {
      SM: "12px",
      MD: "16px",
      LG: "20px",
      XL: "24px",
      XXL: "36px",
    },
    WIDTH: {
      XS: "30px",
      SM: "40px",
      MD: "60px",
      LG: "80px",
      XL: "100px",
      XXL: "120px",
      FULL: "100%",
      TEXT_SM: "100px",
      TEXT_MD: "150px",
      TEXT_LG: "200px",
      TEXT_XL: "300px",
    },
  },

  // Component sizes
  PANEL: {
    MAX_ITEMS: 4,
    CARD_HEIGHT: "80px",
    PROGRESS_HEIGHT: "6px",
  },

  // Container widths
  CONTAINER: {
    MAX_WIDTH: "6xl",
  },
} as const

export const UI_COLORS = {
  STATUS: {
    CREATED: "orange",
    EXTRACTING_CONTENT: "orange",
    GENERATING_QUESTIONS: "orange",
    READY_FOR_REVIEW: "purple",
    READY_FOR_REVIEW_PARTIAL: "purple",
    EXPORTING_TO_CANVAS: "yellow",
    PUBLISHED: "green",
    FAILED: "red",
  },
  BORDER: {
    ORANGE: "orange.200",
    PURPLE: "purple.200",
    YELLOW: "yellow.200",
    GREEN: "green.200",
    RED: "red.200",
  },
  BACKGROUND: {
    ORANGE: "orange.50",
    PURPLE: "purple.50",
    YELLOW: "yellow.50",
    GREEN: "green.50",
    RED: "red.50",
  },
} as const

export const UI_TEXT = {
  EMPTY_STATES: {
    NO_QUIZZES: "No quizzes found",
    NO_QUIZZES_GENERATING: "No quizzes being generated",
    NO_QUIZZES_REVIEW: "No quizzes ready for review",
  },
  ACTIONS: {
    CREATE_QUIZ: "Create New Quiz",
    CREATE_FIRST_QUIZ: "Create Your First Quiz",
    VIEW_DETAILS: "View Details",
    VIEW_ALL: "View All Quizzes",
  },
  STATUS: {
    CREATED: "Ready to Start",
    EXTRACTING_CONTENT: "Extracting Content",
    GENERATING_QUESTIONS: "Generating Questions",
    READY_FOR_REVIEW: "Ready for Review",
    READY_FOR_REVIEW_PARTIAL: "Partial Success - Ready for Review",
    EXPORTING_TO_CANVAS: "Exporting to Canvas",
    PUBLISHED: "Published to Canvas",
    FAILED: "Failed",
  },
  FAILURE_MESSAGES: {
    [FAILURE_REASON.CANVAS_EXPORT_ERROR]: {
      TITLE: "Export to Canvas Failed",
      MESSAGE:
        "There was an error exporting your quiz to Canvas. Your questions are shown below and you can try exporting again.",
    },
    [FAILURE_REASON.CONTENT_EXTRACTION_ERROR]: {
      TITLE: "Content Extraction Failed",
      MESSAGE:
        "Unable to extract content from the selected Canvas modules. Please check your module selection and try again.",
    },
    [FAILURE_REASON.NO_CONTENT_FOUND]: {
      TITLE: "No Content Found",
      MESSAGE:
        "No content was found in the selected Canvas modules. Please select different modules or check if the modules contain content.",
    },
    [FAILURE_REASON.LLM_GENERATION_ERROR]: {
      TITLE: "Question Generation Failed",
      MESSAGE:
        "Unable to generate questions from the extracted content. Please try again or adjust your quiz settings.",
    },
    [FAILURE_REASON.NO_QUESTIONS_GENERATED]: {
      TITLE: "No Questions Generated",
      MESSAGE:
        "No questions could be generated from the available content. Please try with different content or adjust your quiz settings.",
    },
    [FAILURE_REASON.NETWORK_ERROR]: {
      TITLE: "Network Error",
      MESSAGE:
        "A network error occurred while processing your quiz. Please check your connection and try again.",
    },
    [FAILURE_REASON.VALIDATION_ERROR]: {
      TITLE: "Validation Error",
      MESSAGE:
        "There was a validation error while processing your quiz. Please check your quiz settings and try again.",
    },
    GENERIC: {
      TITLE: "Quiz Processing Failed",
      MESSAGE:
        "An error occurred while processing your quiz. Please try again or contact support if the problem persists.",
    },
  },
} as const

// =============================================================================
// Validation Constants
// =============================================================================

export const VALIDATION = {
  QUIZ: {
    MIN_TITLE_LENGTH: 1,
    MAX_TITLE_LENGTH: 255,
    MIN_QUESTIONS: 1,
    MAX_QUESTIONS: 100,
  },
  API: {
    REQUEST_TIMEOUT: 120000, // 2 minutes
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000, // 1 second
  },
} as const

// =============================================================================
// Question Batch Validation Constants
// =============================================================================

export const VALIDATION_RULES = {
  MAX_BATCHES_PER_MODULE: 4,
  MIN_QUESTIONS_PER_BATCH: 1,
  MAX_QUESTIONS_PER_BATCH: 20,
} as const

export const VALIDATION_MESSAGES = {
  MAX_BATCHES: "Maximum 4 question batches per module",
  DUPLICATE_TYPES: "Cannot have duplicate question types in the same module",
  DUPLICATE_COMBINATIONS:
    "Cannot have duplicate question type and difficulty combinations",
  INVALID_COUNT: "Question count must be between 1 and 20",
  NO_BATCHES: "Each module must have at least one question batch",
} as const

export const QUESTION_BATCH_DEFAULTS = {
  DEFAULT_QUESTION_TYPE: QUESTION_TYPES.MULTIPLE_CHOICE,
  DEFAULT_QUESTION_COUNT: 10,
  DEFAULT_DIFFICULTY: QUESTION_DIFFICULTIES.MEDIUM,
} as const

// =============================================================================
// Feature Flags
// =============================================================================

export const FEATURES = {
  ONBOARDING_ENABLED: true,
  ANALYTICS_ENABLED: false,
  DEV_TOOLS_ENABLED: process.env.NODE_ENV === "development",
} as const
