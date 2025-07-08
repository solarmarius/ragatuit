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
  TRUE_FALSE: "true_false",
  SHORT_ANSWER: "short_answer",
  ESSAY: "essay",
  FILL_IN_BLANK: "fill_in_blank",
} as const

export const PROCESSING_STATUSES = {
  PENDING: "pending",
  PROCESSING: "processing",
  COMPLETED: "completed",
  FAILED: "failed",
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
    PENDING: "orange",
    PROCESSING: "orange",
    COMPLETED: "green",
    FAILED: "red",
  },
  BORDER: {
    PROCESSING: "orange.200",
    SUCCESS: "green.200",
    ERROR: "red.200",
  },
  BACKGROUND: {
    PROCESSING: "orange.50",
    SUCCESS: "green.50",
    ERROR: "red.50",
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
    READY_FOR_REVIEW: "Ready for Review",
    PROCESSING: "Processing",
    PENDING: "Pending",
    FAILED: "Failed",
    COMPLETE: "Complete",
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
// Feature Flags
// =============================================================================

export const FEATURES = {
  ONBOARDING_ENABLED: true,
  ANALYTICS_ENABLED: false,
  DEV_TOOLS_ENABLED: process.env.NODE_ENV === "development",
} as const
