export const queryKeys = {
  auth: {
    currentUser: () => ["auth", "currentUser"] as const,
  },
  quizzes: {
    all: () => ["quizzes"] as const,
    userQuizzes: () => ["quizzes", "user"] as const,
    detail: (id: string) => ["quizzes", "detail", id] as const,
  },
  questions: {
    all: () => ["questions"] as const,
    byQuiz: (quizId: string) => ["questions", "quiz", quizId] as const,
    detail: (id: string) => ["questions", "detail", id] as const,
  },
} as const
