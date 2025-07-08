export class AppError extends Error {
  constructor(
    message: string,
    public code?: string,
    public statusCode?: number,
  ) {
    super(message)
    this.name = "AppError"
  }
}

export class ApiError extends AppError {
  constructor(
    message: string,
    public statusCode: number,
    public code?: string,
  ) {
    super(message, code, statusCode)
    this.name = "ApiError"
  }
}

export class ValidationError extends AppError {
  constructor(
    message: string,
    public field?: string,
  ) {
    super(message, "VALIDATION_ERROR")
    this.name = "ValidationError"
  }
}
