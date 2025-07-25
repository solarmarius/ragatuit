// This file is auto-generated by @hey-api/openapi-ts

import type { CancelablePromise } from "./core/CancelablePromise"
import { OpenAPI } from "./core/OpenAPI"
import { request as __request } from "./core/request"
import type {
  AuthLoginCanvasResponse,
  AuthAuthCanvasResponse,
  AuthLogoutCanvasResponse,
  CanvasGetCoursesResponse,
  CanvasGetCourseModulesData,
  CanvasGetCourseModulesResponse,
  CanvasGetModuleItemsData,
  CanvasGetModuleItemsResponse,
  CanvasGetPageContentData,
  CanvasGetPageContentResponse,
  CanvasGetFileInfoData,
  CanvasGetFileInfoResponse,
  QuestionsGetQuizQuestionsData,
  QuestionsGetQuizQuestionsResponse,
  QuestionsCreateQuestionData,
  QuestionsCreateQuestionResponse,
  QuestionsGetQuestionData,
  QuestionsGetQuestionResponse,
  QuestionsUpdateQuestionData,
  QuestionsUpdateQuestionResponse,
  QuestionsDeleteQuestionData,
  QuestionsDeleteQuestionResponse,
  QuestionsApproveQuestionData,
  QuestionsApproveQuestionResponse,
  QuizGetUserQuizzesEndpointResponse,
  QuizCreateNewQuizData,
  QuizCreateNewQuizResponse,
  QuizGetQuizData,
  QuizGetQuizResponse,
  QuizDeleteQuizEndpointData,
  QuizDeleteQuizEndpointResponse,
  QuizTriggerContentExtractionData,
  QuizTriggerContentExtractionResponse,
  QuizTriggerQuestionGenerationData,
  QuizTriggerQuestionGenerationResponse,
  QuizGetQuizQuestionStatsData,
  QuizGetQuizQuestionStatsResponse,
  QuizExportQuizToCanvasData,
  QuizExportQuizToCanvasResponse,
  UsersReadUserMeResponse,
  UsersDeleteUserMeResponse,
  UsersUpdateUserMeData,
  UsersUpdateUserMeResponse,
  UtilsHealthCheckResponse,
} from "./types.gen"

export class AuthService {
  /**
   * Login Canvas
   * Initiate Canvas OAuth2 authentication flow.
   *
   * Generates a Canvas OAuth2 authorization URL with a secure state parameter
   * and redirects the user to Canvas for authentication.
   *
   * **Flow:**
   * 1. Generates a secure random state parameter for CSRF protection
   * 2. Validates the Canvas base URL configuration
   * 3. Constructs OAuth2 authorization URL with required parameters
   * 4. Redirects user to Canvas login page
   *
   * **Returns:**
   * RedirectResponse: 307 redirect to Canvas OAuth2 authorization endpoint
   *
   * **Raises:**
   * HTTPException: 400 if Canvas base URL is invalid or malformed
   *
   * **Example:**
   * GET /api/v1/auth/login/canvas
   * -> Redirects to: https://canvas.example.com/login/oauth2/auth?client_id=...&state=...
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public static loginCanvas(): CancelablePromise<AuthLoginCanvasResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/auth/login/canvas",
    })
  }

  /**
   * Auth Canvas
   * Handle Canvas OAuth2 callback and complete authentication.
   *
   * Processes the OAuth2 authorization code returned by Canvas, exchanges it
   * for access/refresh tokens, and creates or updates the user account.
   *
   * **Parameters:**
   * session (SessionDep): Database session for user operations
   * request (Request): HTTP request containing OAuth2 callback parameters
   *
   * **Query Parameters:**
   * code (str): Authorization code from Canvas OAuth2 flow
   * state (str): State parameter for CSRF protection (currently not validated)
   *
   * **Flow:**
   * 1. Extracts authorization code from callback URL
   * 2. Exchanges code for Canvas access/refresh tokens
   * 3. Retrieves Canvas user information
   * 4. Creates new user or updates existing user tokens
   * 5. Generates JWT session token for the application
   * 6. Redirects to frontend with success token
   *
   * **Returns:**
   * RedirectResponse: Redirect to frontend login success page with JWT token
   *
   * **Raises:**
   * HTTPException: 400 if authorization code missing or Canvas returns error
   * HTTPException: 503 if unable to connect to Canvas
   *
   * **Example:**
   * GET /api/v1/auth/callback/canvas?code=abc123&state=xyz789
   * -> Redirects to: http://localhost:5173/login/success?token=jwt_token
   *
   * **Error Handling:**
   * On any error, redirects to frontend login page with error message
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public static authCanvas(): CancelablePromise<AuthAuthCanvasResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/auth/callback/canvas",
    })
  }

  /**
   * Logout Canvas
   * Logout user and revoke Canvas tokens.
   *
   * Safely logs out the authenticated user by revoking their Canvas access token
   * and clearing all stored authentication data from the database.
   *
   * **Parameters:**
   * current_user (CurrentUser): Authenticated user from JWT token
   * session (SessionDep): Database session for token cleanup
   *
   * **Flow:**
   * 1. Retrieves and decrypts user's Canvas access token
   * 2. Attempts to revoke token on Canvas side (gracefully handles failures)
   * 3. Clears all user tokens from database
   * 4. Returns success confirmation
   *
   * **Returns:**
   * dict: Success message confirming logout completion
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Error Handling:**
   * - Canvas token revocation failures are logged but don't prevent logout
   * - Network errors to Canvas are handled gracefully
   * - Database token cleanup always proceeds regardless of Canvas API status
   *
   * **Example:**
   * DELETE /api/v1/auth/logout
   * Authorization: Bearer jwt_token
   * -> {"message": "Canvas account disconnected successfully"}
   * @returns string Successful Response
   * @throws ApiError
   */
  public static logoutCanvas(): CancelablePromise<AuthLogoutCanvasResponse> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/auth/logout",
    })
  }
}

export class CanvasService {
  /**
   * Get Courses
   * Fetch Canvas courses where the current user has teacher enrollment.
   *
   * Returns a list of courses where the authenticated user is enrolled as a teacher.
   * This endpoint filters courses to only include those where the user can create quizzes.
   *
   * **Returns:**
   * List[CanvasCourse]: List of courses with id and name only
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 401 if Canvas token is invalid or expired
   * HTTPException: 503 if unable to connect to Canvas
   * HTTPException: 500 if Canvas API returns unexpected data
   *
   * **Example Response:**
   * [
   * {"id": 37823, "name": "SB_ME_INF-0005 Praktisk kunstig intelligens"},
   * {"id": 37824, "name": "SB_ME_INF-0006 Bruk av generativ KI"}
   * ]
   * @returns CanvasCourse Successful Response
   * @throws ApiError
   */
  public static getCourses(): CancelablePromise<CanvasGetCoursesResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/canvas/courses",
    })
  }

  /**
   * Get Course Modules
   * Fetch Canvas modules for a specific course.
   *
   * Returns a list of modules where the authenticated user has access.
   * This endpoint fetches modules to allow teachers to select content for quiz generation.
   *
   * **Parameters:**
   * course_id (int): The Canvas course ID to fetch modules from
   *
   * **Returns:**
   * List[CanvasModule]: List of modules with id and name only
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 401 if Canvas token is invalid or expired
   * HTTPException: 403 if user doesn't have access to the course
   * HTTPException: 503 if unable to connect to Canvas
   * HTTPException: 500 if Canvas API returns unexpected data
   *
   * **Example Response:**
   * [
   * {"id": 173467, "name": "Templates"},
   * {"id": 173468, "name": "Ressurssider for studenter"}
   * ]
   * @param data The data for the request.
   * @param data.courseId
   * @returns CanvasModule Successful Response
   * @throws ApiError
   */
  public static getCourseModules(
    data: CanvasGetCourseModulesData,
  ): CancelablePromise<CanvasGetCourseModulesResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/canvas/courses/{course_id}/modules",
      path: {
        course_id: data.courseId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Get Module Items
   * Fetch items within a specific Canvas module.
   *
   * Returns a list of module items (pages, assignments, files, etc.) for content extraction.
   * This endpoint fetches items to allow content processing for quiz generation.
   *
   * **Parameters:**
   * course_id (int): The Canvas course ID
   * module_id (int): The Canvas module ID to fetch items from
   *
   * **Returns:**
   * List[dict]: List of module items with type, title, and Canvas metadata
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 401 if Canvas token is invalid or expired
   * HTTPException: 403 if user doesn't have access to the course/module
   * HTTPException: 503 if unable to connect to Canvas
   * HTTPException: 500 if Canvas API returns unexpected data
   *
   * **Example Response:**
   * [
   * {
   * "id": 123456,
   * "title": "Introduction to AI",
   * "type": "Page",
   * "html_url": "https://canvas.../pages/intro",
   * "page_url": "intro",
   * "url": "https://canvas.../api/v1/courses/123/pages/intro"
   * }
   * ]
   * @param data The data for the request.
   * @param data.courseId
   * @param data.moduleId
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public static getModuleItems(
    data: CanvasGetModuleItemsData,
  ): CancelablePromise<CanvasGetModuleItemsResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/canvas/courses/{course_id}/modules/{module_id}/items",
      path: {
        course_id: data.courseId,
        module_id: data.moduleId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Get Page Content
   * Fetch content of a specific Canvas page.
   *
   * Returns the full HTML content of a Canvas page for content extraction and processing.
   * This endpoint is used to get the actual page content for quiz question generation.
   *
   * **Parameters:**
   * course_id (int): The Canvas course ID
   * page_url (str): The Canvas page URL slug (e.g., "introduction-to-ai")
   *
   * **Returns:**
   * dict: Page content with title, body, and metadata
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 401 if Canvas token is invalid or expired
   * HTTPException: 403 if user doesn't have access to the course/page
   * HTTPException: 404 if page not found
   * HTTPException: 503 if unable to connect to Canvas
   * HTTPException: 500 if Canvas API returns unexpected data
   *
   * **Example Response:**
   * {
   * "title": "Introduction to AI",
   * "body": "<h1>Introduction</h1><p>Artificial Intelligence is...</p>",
   * "url": "introduction-to-ai",
   * "created_at": "2023-01-01T12:00:00Z",
   * "updated_at": "2023-01-02T12:00:00Z"
   * }
   * @param data The data for the request.
   * @param data.courseId
   * @param data.pageUrl
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public static getPageContent(
    data: CanvasGetPageContentData,
  ): CancelablePromise<CanvasGetPageContentResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/canvas/courses/{course_id}/pages/{page_url}",
      path: {
        course_id: data.courseId,
        page_url: data.pageUrl,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Get File Info
   * Fetch metadata and download URL for a specific Canvas file.
   *
   * Returns file information including the download URL needed to retrieve file content.
   * This endpoint is used to get file metadata before downloading for content extraction.
   *
   * **Parameters:**
   * course_id (int): The Canvas course ID
   * file_id (int): The Canvas file ID
   *
   * **Returns:**
   * dict: File metadata including download URL, size, content-type, etc.
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 401 if Canvas token is invalid or expired
   * HTTPException: 403 if user doesn't have access to the file
   * HTTPException: 404 if file not found
   * HTTPException: 503 if unable to connect to Canvas
   * HTTPException: 500 if Canvas API returns unexpected data
   *
   * **Example Response:**
   * {
   * "id": 3611093,
   * "display_name": "linear_algebra_in_4_pages.pdf",
   * "filename": "linear_algebra_in_4_pages.pdf",
   * "content-type": "application/pdf",
   * "url": "https://canvas.../files/3611093/download?download_frd=1&verifier=...",
   * "size": 258646,
   * "created_at": "2025-06-25T06:24:29Z",
   * "updated_at": "2025-06-25T06:24:29Z"
   * }
   * @param data The data for the request.
   * @param data.courseId
   * @param data.fileId
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public static getFileInfo(
    data: CanvasGetFileInfoData,
  ): CancelablePromise<CanvasGetFileInfoResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/canvas/courses/{course_id}/files/{file_id}",
      path: {
        course_id: data.courseId,
        file_id: data.fileId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }
}

export class QuestionsService {
  /**
   * Get Quiz Questions
   * Retrieve questions for a quiz with filtering support.
   *
   * **Parameters:**
   * quiz_id: Quiz identifier
   * question_type: Filter by question type (optional)
   * approved_only: Only return approved questions
   * limit: Maximum number of questions to return
   * offset: Number of questions to skip for pagination
   *
   * **Returns:**
   * List of questions with formatted display data
   * @param data The data for the request.
   * @param data.quizId
   * @param data.questionType Filter by question type
   * @param data.approvedOnly Only return approved questions
   * @param data.limit Maximum questions to return
   * @param data.offset Number of questions to skip
   * @returns QuestionResponse Successful Response
   * @throws ApiError
   */
  public static getQuizQuestions(
    data: QuestionsGetQuizQuestionsData,
  ): CancelablePromise<QuestionsGetQuizQuestionsResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/questions/{quiz_id}",
      path: {
        quiz_id: data.quizId,
      },
      query: {
        question_type: data.questionType,
        approved_only: data.approvedOnly,
        limit: data.limit,
        offset: data.offset,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Create Question
   * Create a new question for a quiz.
   *
   * **Parameters:**
   * quiz_id: Quiz identifier
   * question_request: Question creation data
   *
   * **Returns:**
   * Created question with formatted display data
   * @param data The data for the request.
   * @param data.quizId
   * @param data.requestBody
   * @returns QuestionResponse Successful Response
   * @throws ApiError
   */
  public static createQuestion(
    data: QuestionsCreateQuestionData,
  ): CancelablePromise<QuestionsCreateQuestionResponse> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/questions/{quiz_id}",
      path: {
        quiz_id: data.quizId,
      },
      body: data.requestBody,
      mediaType: "application/json",
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Get Question
   * Retrieve a specific question by ID.
   *
   * **Parameters:**
   * quiz_id: Quiz identifier
   * question_id: Question identifier
   *
   * **Returns:**
   * Question with formatted display data
   * @param data The data for the request.
   * @param data.quizId
   * @param data.questionId
   * @returns QuestionResponse Successful Response
   * @throws ApiError
   */
  public static getQuestion(
    data: QuestionsGetQuestionData,
  ): CancelablePromise<QuestionsGetQuestionResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/questions/{quiz_id}/{question_id}",
      path: {
        quiz_id: data.quizId,
        question_id: data.questionId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Update Question
   * Update a question.
   *
   * **Parameters:**
   * quiz_id: Quiz identifier
   * question_id: Question identifier
   * question_update: Question update data
   *
   * **Returns:**
   * Updated question with formatted display data
   * @param data The data for the request.
   * @param data.quizId
   * @param data.questionId
   * @param data.requestBody
   * @returns QuestionResponse Successful Response
   * @throws ApiError
   */
  public static updateQuestion(
    data: QuestionsUpdateQuestionData,
  ): CancelablePromise<QuestionsUpdateQuestionResponse> {
    return __request(OpenAPI, {
      method: "PUT",
      url: "/api/v1/questions/{quiz_id}/{question_id}",
      path: {
        quiz_id: data.quizId,
        question_id: data.questionId,
      },
      body: data.requestBody,
      mediaType: "application/json",
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Delete Question
   * Delete a question from the quiz.
   *
   * **Parameters:**
   * quiz_id: Quiz identifier
   * question_id: Question identifier
   *
   * **Returns:**
   * Confirmation message
   * @param data The data for the request.
   * @param data.quizId
   * @param data.questionId
   * @returns string Successful Response
   * @throws ApiError
   */
  public static deleteQuestion(
    data: QuestionsDeleteQuestionData,
  ): CancelablePromise<QuestionsDeleteQuestionResponse> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/questions/{quiz_id}/{question_id}",
      path: {
        quiz_id: data.quizId,
        question_id: data.questionId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Approve Question
   * Approve a question for inclusion in the final quiz.
   *
   * **Parameters:**
   * quiz_id: Quiz identifier
   * question_id: Question identifier
   *
   * **Returns:**
   * Approved question with formatted display data
   * @param data The data for the request.
   * @param data.quizId
   * @param data.questionId
   * @returns QuestionResponse Successful Response
   * @throws ApiError
   */
  public static approveQuestion(
    data: QuestionsApproveQuestionData,
  ): CancelablePromise<QuestionsApproveQuestionResponse> {
    return __request(OpenAPI, {
      method: "PUT",
      url: "/api/v1/questions/{quiz_id}/{question_id}/approve",
      path: {
        quiz_id: data.quizId,
        question_id: data.questionId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }
}

export class QuizService {
  /**
   * Get User Quizzes Endpoint
   * Retrieve all quizzes created by the authenticated user.
   *
   * Returns a list of all quizzes owned by the current user, ordered by creation date
   * (most recent first). Each quiz includes full details including settings and metadata.
   *
   * **Returns:**
   * List[Quiz]: List of quiz objects owned by the user
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 500 if database operation fails
   *
   * **Example Response:**
   * ```json
   * [
   * {
   * "id": "12345678-1234-5678-9abc-123456789abc",
   * "owner_id": "87654321-4321-8765-cba9-987654321abc",
   * "canvas_course_id": 12345,
   * "canvas_course_name": "Introduction to AI",
   * "selected_modules": {
   * "173467": {
   * "name": "Machine Learning Basics",
   * "question_batches": [
   * {"question_type": "multiple_choice", "count": 30},
   * {"question_type": "fill_in_blank", "count": 20}
   * ]
   * }
   * },
   * "title": "AI Fundamentals Quiz",
   * "llm_model": "gpt-4o",
   * "llm_temperature": 1,
   * "created_at": "2023-01-01T12:00:00Z",
   * "updated_at": "2023-01-01T12:00:00Z"
   * }
   * ]
   * ```
   * @returns Quiz Successful Response
   * @throws ApiError
   */
  public static getUserQuizzesEndpoint(): CancelablePromise<QuizGetUserQuizzesEndpointResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/quiz/",
    })
  }

  /**
   * Create New Quiz
   * Create a new quiz with the specified settings.
   *
   * Creates a quiz with Canvas course integration, module selection, and LLM configuration.
   * The quiz is associated with the authenticated user as the owner.
   *
   * **Parameters:**
   * quiz_data (QuizCreate): Quiz creation data including:
   * - canvas_course_id: Canvas course ID
   * - canvas_course_name: Canvas course name
   * - selected_modules: Dict mapping module IDs to ModuleSelection with question_batches
   * - title: Quiz title
   * - llm_model: LLM model to use (default "o3")
   * - llm_temperature: LLM temperature setting (0.0-2.0, default 1)
   *
   * **Returns:**
   * Quiz: The created quiz object with generated UUID and timestamps
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 400 if quiz data is invalid
   * HTTPException: 500 if database operation fails
   *
   * **Example Request:**
   * ```json
   * {
   * "canvas_course_id": 12345,
   * "canvas_course_name": "Introduction to AI",
   * "selected_modules": {
   * "173467": {
   * "name": "Machine Learning Basics",
   * "question_batches": [
   * {"question_type": "multiple_choice", "count": 30},
   * {"question_type": "fill_in_blank", "count": 20}
   * ]
   * }
   * },
   * "title": "AI Fundamentals Quiz",
   * "llm_model": "gpt-4o",
   * "llm_temperature": 1
   * }
   * ```
   * @param data The data for the request.
   * @param data.requestBody
   * @returns Quiz Successful Response
   * @throws ApiError
   */
  public static createNewQuiz(
    data: QuizCreateNewQuizData,
  ): CancelablePromise<QuizCreateNewQuizResponse> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/quiz/",
      body: data.requestBody,
      mediaType: "application/json",
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Get Quiz
   * Retrieve a quiz by its ID.
   *
   * Returns the quiz details if the authenticated user is the owner.
   * Includes all quiz settings, Canvas course information, and selected modules.
   *
   * **Parameters:**
   * quiz_id (UUID): The UUID of the quiz to retrieve
   *
   * **Returns:**
   * Quiz: The quiz object with all details
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 404 if quiz not found or user doesn't own it
   * HTTPException: 500 if database operation fails
   *
   * **Example Response:**
   * ```json
   * {
   * "id": "12345678-1234-5678-9abc-123456789abc",
   * "owner_id": "87654321-4321-8765-cba9-987654321abc",
   * "canvas_course_id": 12345,
   * "canvas_course_name": "Introduction to AI",
   * "selected_modules": {
   * "173467": {
   * "name": "Machine Learning Basics",
   * "question_batches": [
   * {"question_type": "multiple_choice", "count": 30},
   * {"question_type": "fill_in_blank", "count": 20}
   * ]
   * }
   * },
   * "title": "AI Fundamentals Quiz",
   * "llm_model": "gpt-4o",
   * "llm_temperature": 1,
   * "created_at": "2023-01-01T12:00:00Z",
   * "updated_at": "2023-01-01T12:00:00Z"
   * }
   * ```
   * @param data The data for the request.
   * @param data.quizId
   * @returns Quiz Successful Response
   * @throws ApiError
   */
  public static getQuiz(
    data: QuizGetQuizData,
  ): CancelablePromise<QuizGetQuizResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/quiz/{quiz_id}",
      path: {
        quiz_id: data.quizId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Delete Quiz Endpoint
   * Delete a quiz by its ID.
   *
   * **⚠️ DESTRUCTIVE OPERATION ⚠️**
   *
   * Permanently removes a quiz and all its associated data from the system.
   * This action cannot be undone. Only the quiz owner can delete their own quizzes.
   *
   * **Parameters:**
   * quiz_id (UUID): The UUID of the quiz to delete
   *
   * **Returns:**
   * Message: Confirmation message that the quiz was deleted
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 404 if quiz not found or user doesn't own it
   * HTTPException: 500 if database operation fails
   *
   * **Usage:**
   * DELETE /api/v1/quiz/{quiz_id}
   * Authorization: Bearer <jwt_token>
   *
   * **Example Response:**
   * ```json
   * {
   * "message": "Quiz deleted successfully"
   * }
   * ```
   *
   * **Data Removed:**
   * - Quiz record and all settings
   * - Extracted content data
   * - Quiz metadata and timestamps
   * - Progress tracking information
   *
   * **Security:**
   * - Only quiz owners can delete their own quizzes
   * - Ownership verification prevents unauthorized deletions
   * - Comprehensive audit logging for deletion events
   *
   * **Note:**
   * This operation is permanent. The quiz cannot be recovered after deletion.
   * @param data The data for the request.
   * @param data.quizId
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public static deleteQuizEndpoint(
    data: QuizDeleteQuizEndpointData,
  ): CancelablePromise<QuizDeleteQuizEndpointResponse> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/quiz/{quiz_id}",
      path: {
        quiz_id: data.quizId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Trigger Content Extraction
   * Manually trigger content extraction for a quiz.
   *
   * This endpoint allows users to retry content extraction if it failed
   * or trigger extraction manually. It can be called multiple times.
   *
   * **Parameters:**
   * quiz_id (UUID): The UUID of the quiz to extract content for
   *
   * **Returns:**
   * dict: Status message indicating extraction has been triggered
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 404 if quiz not found or user doesn't own it
   * HTTPException: 409 if extraction already in progress
   * HTTPException: 500 if unable to trigger extraction
   * @param data The data for the request.
   * @param data.quizId
   * @returns string Successful Response
   * @throws ApiError
   */
  public static triggerContentExtraction(
    data: QuizTriggerContentExtractionData,
  ): CancelablePromise<QuizTriggerContentExtractionResponse> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/quiz/{quiz_id}/extract-content",
      path: {
        quiz_id: data.quizId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Trigger Question Generation
   * Manually trigger question generation for a quiz.
   *
   * This endpoint allows users to trigger question generation after content
   * extraction is complete. It uses the quiz's existing LLM settings.
   *
   * **Parameters:**
   * quiz_id (UUID): The UUID of the quiz to generate questions for
   *
   * **Returns:**
   * dict: Status message indicating generation has been triggered
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 404 if quiz not found or user doesn't own it
   * HTTPException: 400 if content extraction not completed
   * HTTPException: 409 if question generation already in progress
   * HTTPException: 500 if unable to trigger generation
   * @param data The data for the request.
   * @param data.quizId
   * @returns string Successful Response
   * @throws ApiError
   */
  public static triggerQuestionGeneration(
    data: QuizTriggerQuestionGenerationData,
  ): CancelablePromise<QuizTriggerQuestionGenerationResponse> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/quiz/{quiz_id}/generate-questions",
      path: {
        quiz_id: data.quizId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Get Quiz Question Stats
   * Get question statistics for a quiz.
   *
   * Returns the total number of questions and approved questions for the quiz.
   *
   * **Parameters:**
   * quiz_id (UUID): The UUID of the quiz to get stats for
   *
   * **Returns:**
   * dict: Dictionary with 'total' and 'approved' question counts
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 404 if quiz not found or user doesn't own it
   * HTTPException: 500 if database operation fails
   * @param data The data for the request.
   * @param data.quizId
   * @returns number Successful Response
   * @throws ApiError
   */
  public static getQuizQuestionStats(
    data: QuizGetQuizQuestionStatsData,
  ): CancelablePromise<QuizGetQuizQuestionStatsResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/quiz/{quiz_id}/questions/stats",
      path: {
        quiz_id: data.quizId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }

  /**
   * Export Quiz To Canvas
   * Export a quiz to Canvas LMS.
   *
   * Triggers background export of the quiz to Canvas. Only the quiz owner can export
   * their own quizzes. The export process runs asynchronously and the quiz status
   * can be checked via the quiz detail endpoint.
   *
   * **Parameters:**
   * quiz_id (UUID): The UUID of the quiz to export
   *
   * **Returns:**
   * dict: Export initiation status message
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Raises:**
   * HTTPException: 404 if quiz not found or user doesn't own it
   * HTTPException: 400 if quiz has no approved questions
   * HTTPException: 409 if export already in progress or completed
   * HTTPException: 500 if unable to start export
   *
   * **Example Response:**
   * ```json
   * {
   * "message": "Quiz export started"
   * }
   * ```
   *
   * **Usage:**
   * After calling this endpoint, poll the quiz detail endpoint to check
   * the export_status field for progress updates.
   * @param data The data for the request.
   * @param data.quizId
   * @returns string Successful Response
   * @throws ApiError
   */
  public static exportQuizToCanvas(
    data: QuizExportQuizToCanvasData,
  ): CancelablePromise<QuizExportQuizToCanvasResponse> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/quiz/{quiz_id}/export",
      path: {
        quiz_id: data.quizId,
      },
      errors: {
        422: "Validation Error",
      },
    })
  }
}

export class UsersService {
  /**
   * Read User Me
   * Get current user profile information.
   *
   * Returns the authenticated user's public profile data including their name
   * and Canvas information. This endpoint provides user data for displaying
   * in the frontend interface.
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Parameters:**
   * current_user (CurrentUser): Authenticated user from JWT token validation
   *
   * **Returns:**
   * UserPublic: User's public profile information (excludes sensitive data)
   *
   * **Response Model:**
   * - name (str): User's display name from Canvas
   * - Additional public fields as defined in UserPublic schema
   *
   * **Usage:**
   * GET /api/v1/auth/users/me
   * Authorization: Bearer <jwt_token>
   *
   * **Example Response:**
   * {
   * "name": "John Doe"
   * }
   *
   * **Security:**
   * - Only returns public user information (no tokens or sensitive data)
   * - Requires valid authentication to access
   * - User can only access their own profile information
   *
   * **Frontend Integration:**
   * Used by frontend to display user information in navigation, profile sections,
   * and user settings pages.
   * @returns UserPublic Successful Response
   * @throws ApiError
   */
  public static readUserMe(): CancelablePromise<UsersReadUserMeResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/users/me",
    })
  }

  /**
   * Delete User Me
   * Delete user account while preserving quiz data for research purposes.
   *
   * **⚠️ DESTRUCTIVE OPERATION ⚠️**
   *
   * This endpoint permanently removes the user's account from the system,
   * including all Canvas OAuth tokens and user data. Associated quizzes and
   * questions are anonymized (owner_id set to NULL) and soft-deleted to
   * preserve data for research while removing personal identification.
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Parameters:**
   * session (SessionDep): Database session for the deletion transaction
   * current_user (CurrentUser): Authenticated user from JWT token validation
   *
   * **Returns:**
   * None: 204 No Content response
   *
   * **Usage:**
   * DELETE /api/v1/auth/users/me
   * Authorization: Bearer <jwt_token>
   *
   * **Data Handling:**
   * - **User account**: Permanently deleted (hard delete)
   * - **Quizzes**: Anonymized (owner_id = NULL) and soft-deleted for research
   * - **Questions**: Soft-deleted along with quiz cascade
   * - **Canvas tokens**: Permanently removed
   *
   * **Privacy Protection:**
   * - User PII completely removed (GDPR compliant)
   * - Quiz/question data anonymized but preserved
   * - No way to trace data back to original user
   *
   * **Research Benefits:**
   * - Preserves question generation patterns
   * - Maintains dataset for LLM improvement
   * - Enables usage analytics without user identification
   *
   * **Side Effects:**
   * - All JWT tokens for this user become invalid immediately
   * - User must re-authenticate with Canvas to create a new account
   * - Canvas connection is severed (tokens are deleted)
   * - User loses access to all application features
   * - Associated quizzes become anonymous and unavailable to users
   *
   * **Security:**
   * - Users can only delete their own account
   * - Requires active authentication (prevents accidental deletion)
   * - Immediate token invalidation prevents further access
   * - Complete anonymization ensures privacy compliance
   *
   * **Recovery:**
   * - No account recovery possible after deletion
   * - User can create new account by authenticating with Canvas again
   * - Previous quiz data will not be accessible (anonymized)
   * @returns unknown Successful Response
   * @throws ApiError
   */
  public static deleteUserMe(): CancelablePromise<UsersDeleteUserMeResponse> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/users/me",
    })
  }

  /**
   * Update User Me
   * Update current user's profile information.
   *
   * Allows authenticated users to modify their profile data such as display name.
   * Only updates fields provided in the request body, leaving other fields unchanged.
   *
   * **Authentication:**
   * Requires valid JWT token in Authorization header
   *
   * **Parameters:**
   * session (SessionDep): Database session for the update transaction
   * user_in (UserUpdateMe): Updated user data (only provided fields are changed)
   * current_user (CurrentUser): Authenticated user from JWT token validation
   *
   * **Request Body (UserUpdateMe):**
   * - name (str, optional): New display name for the user
   *
   * **Returns:**
   * UserPublic: Updated user profile with new information
   *
   * **Usage:**
   * PATCH /api/v1/auth/users/me
   * Authorization: Bearer <jwt_token>
   * Content-Type: application/json
   *
   * {
   * "name": "New Display Name"
   * }
   *
   * **Example Response:**
   * {
   * "name": "New Display Name"
   * }
   *
   * **Behavior:**
   * - Partial updates: Only provided fields are modified
   * - Validation: Input validated against UserUpdateMe schema
   * - Database: Changes are committed immediately
   * - Response: Returns updated user information
   *
   * **Security:**
   * - Users can only update their own profile
   * - Sensitive fields (tokens, Canvas ID) cannot be modified
   * - Input validation prevents malicious data
   *
   * **Error Handling:**
   * - Validation errors return 422 with details
   * - Authentication errors return 401/403
   * - Database errors return 500
   * @param data The data for the request.
   * @param data.requestBody
   * @returns UserPublic Successful Response
   * @throws ApiError
   */
  public static updateUserMe(
    data: UsersUpdateUserMeData,
  ): CancelablePromise<UsersUpdateUserMeResponse> {
    return __request(OpenAPI, {
      method: "PATCH",
      url: "/api/v1/users/me",
      body: data.requestBody,
      mediaType: "application/json",
      errors: {
        422: "Validation Error",
      },
    })
  }
}

export class UtilsService {
  /**
   * Health Check
   * Simple health check endpoint.
   *
   * Returns True if the API is running and responsive.
   * Used for monitoring and load balancer health checks.
   * @returns boolean Successful Response
   * @throws ApiError
   */
  public static healthCheck(): CancelablePromise<UtilsHealthCheckResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/utils/health-check/",
    })
  }
}
