import { expect, test } from "@playwright/test"
import { createUserResponse } from "../fixtures/quiz-data"

test.describe("Manual Question Addition Feature", () => {
  const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"

  test.beforeEach(async ({ page }) => {
    // Mock the current user API call
    await page.route("**/api/v1/users/me", async (route) => {
      await route.fulfill(createUserResponse())
    })
  })

  test.describe("Add Question Button Visibility", () => {
    test("should show Add Question button in ready_for_review status", async ({
      page,
    }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Ready for Review Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 15,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "ready_for_review",
        content_extracted_at: "2024-01-15T11:00:00Z",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      }

      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockQuiz),
        })
      })

      // Mock empty questions response
      await page.route(`**/api/v1/questions/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      })

      // Mock question stats response
      await page.route(`**/api/v1/questions/${mockQuizId}/stats`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            total_questions: 0,
            approved_questions: 0,
            approval_percentage: 0,
          }),
        })
      })

      await page.goto(`/quiz/${mockQuizId}/questions`)

      // Check that Add Question button is visible
      const addQuestionButton = page.getByRole("button", { name: "Add Question" })
      await expect(addQuestionButton).toBeVisible()
      await expect(addQuestionButton).toHaveCSS("background-color", /rgb\(34, 197, 94\)|rgb\(22, 163, 74\)/) // green color
    })

    test("should show Add Question button in ready_for_review_partial status", async ({
      page,
    }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Partial Review Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 8,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "ready_for_review_partial",
        content_extracted_at: "2024-01-15T11:00:00Z",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      }

      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockQuiz),
        })
      })

      // Mock questions and stats
      await page.route(`**/api/v1/questions/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      })

      await page.route(`**/api/v1/questions/${mockQuizId}/stats`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            total_questions: 0,
            approved_questions: 0,
            approval_percentage: 0,
          }),
        })
      })

      await page.goto(`/quiz/${mockQuizId}/questions`)

      // Check that Add Question button is visible
      await expect(page.getByRole("button", { name: "Add Question" })).toBeVisible()
    })

    test("should hide Add Question button in published status", async ({
      page,
    }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Published Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 20,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "published",
        content_extracted_at: "2024-01-15T11:00:00Z",
        exported_at: "2024-01-16T15:00:00Z",
        last_status_update: "2024-01-16T15:00:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T15:00:00Z",
        owner_id: "user123",
      }

      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockQuiz),
        })
      })

      // Mock questions and stats for published quiz
      await page.route(`**/api/v1/questions/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      })

      await page.route(`**/api/v1/questions/${mockQuizId}/stats`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            total_questions: 20,
            approved_questions: 20,
            approval_percentage: 100,
          }),
        })
      })

      await page.goto(`/quiz/${mockQuizId}/questions`)

      // Check that Add Question button is NOT visible
      await expect(page.getByRole("button", { name: "Add Question" })).not.toBeVisible()
    })

    test("should hide Add Question button in generating_questions status", async ({
      page,
    }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Generating Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 25,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "generating_questions",
        content_extracted_at: "2024-01-15T11:00:00Z",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      }

      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockQuiz),
        })
      })

      await page.goto(`/quiz/${mockQuizId}/questions`)

      // Check that Add Question button is NOT visible
      await expect(page.getByRole("button", { name: "Add Question" })).not.toBeVisible()
    })
  })

  test.describe("Question Type Selection Dialog", () => {
    test.beforeEach(async ({ page }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Ready for Review Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 15,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "ready_for_review",
        content_extracted_at: "2024-01-15T11:00:00Z",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      }

      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockQuiz),
        })
      })

      // Mock questions and stats
      await page.route(`**/api/v1/questions/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      })

      await page.route(`**/api/v1/questions/${mockQuizId}/stats`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            total_questions: 0,
            approved_questions: 0,
            approval_percentage: 0,
          }),
        })
      })

      await page.goto(`/quiz/${mockQuizId}/questions`)
    })

    test("should open dialog when Add Question button is clicked", async ({
      page,
    }) => {
      const addQuestionButton = page.getByRole("button", { name: "Add Question" })
      await addQuestionButton.click()

      // Check that dialog opens with correct title
      await expect(page.getByRole("dialog")).toBeVisible()
      await expect(page.getByRole("heading", { name: "Add Question" })).toBeVisible()
    })

    test("should display all 5 question types in selection step", async ({
      page,
    }) => {
      const addQuestionButton = page.getByRole("button", { name: "Add Question" })
      await addQuestionButton.click()

      // Check that all question type cards are visible
      await expect(page.getByText("Multiple Choice")).toBeVisible()
      await expect(page.getByText("True/False")).toBeVisible()
      await expect(page.getByText("Fill in the Blank")).toBeVisible()
      await expect(page.getByText("Matching")).toBeVisible()
      await expect(page.getByText("Categorization")).toBeVisible()

      // Check descriptions are present
      await expect(page.getByText("Choose the correct answer from 4 options")).toBeVisible()
      await expect(page.getByText("Simple true or false statements")).toBeVisible()
      await expect(page.getByText("Complete sentences with missing words")).toBeVisible()
    })

    test("should show question type selection instructions", async ({ page }) => {
      const addQuestionButton = page.getByRole("button", { name: "Add Question" })
      await addQuestionButton.click()

      await expect(page.getByText("Select Question Type")).toBeVisible()
      await expect(page.getByText("Choose the type of question you want to create.")).toBeVisible()
      await expect(page.getByText("All question types support real-time validation")).toBeVisible()
    })

    test("should proceed to question creation when type is selected", async ({
      page,
    }) => {
      const addQuestionButton = page.getByRole("button", { name: "Add Question" })
      await addQuestionButton.click()

      // Click on Multiple Choice option
      await page.getByText("Multiple Choice").click()

      // Should navigate to question creation step
      await expect(page.getByRole("heading", { name: "Create Multiple Choice Question" })).toBeVisible()
      await expect(page.getByText("← Back to Question Types")).toBeVisible()
    })

    test("should allow navigation back to question type selection", async ({
      page,
    }) => {
      const addQuestionButton = page.getByRole("button", { name: "Add Question" })
      await addQuestionButton.click()

      // Select a question type
      await page.getByText("True/False").click()

      // Should be on creation step
      await expect(page.getByRole("heading", { name: "Create True False Question" })).toBeVisible()

      // Click back button
      await page.getByRole("button", { name: "← Back to Question Types" }).click()

      // Should be back to type selection
      await expect(page.getByRole("heading", { name: "Add Question" })).toBeVisible()
      await expect(page.getByText("Select Question Type")).toBeVisible()
    })

    test("should close dialog when close button is clicked", async ({ page }) => {
      const addQuestionButton = page.getByRole("button", { name: "Add Question" })
      await addQuestionButton.click()

      // Dialog should be open
      await expect(page.getByRole("dialog")).toBeVisible()

      // Click close button
      await page.getByRole("button", { name: "Close" }).click()

      // Dialog should be closed
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })
  })

  test.describe("Question Creation Workflow", () => {
    test.beforeEach(async ({ page }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Ready for Review Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 15,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "ready_for_review",
        content_extracted_at: "2024-01-15T11:00:00Z",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      }

      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockQuiz),
        })
      })

      // Mock questions and stats
      await page.route(`**/api/v1/questions/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      })

      await page.route(`**/api/v1/questions/${mockQuizId}/stats`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            total_questions: 0,
            approved_questions: 0,
            approval_percentage: 0,
          }),
        })
      })

      await page.goto(`/quiz/${mockQuizId}/questions`)
    })

    test("should display Multiple Choice question form with all required fields", async ({
      page,
    }) => {
      // Open dialog and select MCQ
      await page.getByRole("button", { name: "Add Question" }).click()
      await page.getByText("Multiple Choice").click()

      // Wait for form to render and check if basic elements are present
      await expect(page.getByText("Question Text")).toBeVisible()
      await expect(page.getByText("Option A")).toBeVisible()
      await expect(page.getByText("Option B")).toBeVisible()
      await expect(page.getByText("Option C")).toBeVisible()
      await expect(page.getByText("Option D")).toBeVisible()
      await expect(page.getByText("Correct Answer")).toBeVisible()
      await expect(page.getByText("Explanation")).toBeVisible()

      // Check for form inputs (using more flexible selectors)
      await expect(page.locator('textarea[placeholder*="question text"]')).toBeVisible()
      await expect(page.locator('input[placeholder*="option A"]')).toBeVisible()
      await expect(page.locator('input[placeholder*="option B"]')).toBeVisible()
      await expect(page.locator('input[placeholder*="option C"]')).toBeVisible()
      await expect(page.locator('input[placeholder*="option D"]')).toBeVisible()

      // Check radio buttons for correct answer
      await expect(page.getByRole("radio", { name: "A" })).toBeVisible()
      await expect(page.getByRole("radio", { name: "B" })).toBeVisible()
      await expect(page.getByRole("radio", { name: "C" })).toBeVisible()
      await expect(page.getByRole("radio", { name: "D" })).toBeVisible()
    })

    test("should display True/False question form with required fields", async ({
      page,
    }) => {
      // Open dialog and select True/False
      await page.getByRole("button", { name: "Add Question" }).click()
      await page.getByText("True/False").click()

      // Check True/False form fields using text content
      await expect(page.getByText("Question Text")).toBeVisible()
      await expect(page.getByText("Correct Answer")).toBeVisible()
      await expect(page.getByText("Explanation")).toBeVisible()

      // Check for form inputs - True/False should have question text field
      await expect(page.locator('textarea').first()).toBeVisible()

      // Check radio buttons for true/false
      await expect(page.getByRole("radio", { name: "True" })).toBeVisible()
      await expect(page.getByRole("radio", { name: "False" })).toBeVisible()
    })

    test("should validate required fields before allowing save", async ({
      page,
    }) => {
      // Open dialog and select MCQ
      await page.getByRole("button", { name: "Add Question" }).click()
      await page.getByText("Multiple Choice").click()

      // Try to save without filling required fields
      const saveButton = page.getByRole("button", { name: "Save Changes" })
      await expect(saveButton).toBeDisabled() // Should be disabled when form is not dirty or invalid
    })

    test("should enable save button when all required fields are filled", async ({
      page,
    }) => {
      // Open dialog and select MCQ
      await page.getByRole("button", { name: "Add Question" }).click()
      await page.getByText("Multiple Choice").click()

      // Fill all required fields using more flexible selectors
      await page.locator('textarea[placeholder*="question text"]').fill("What is the capital of France?")
      await page.locator('input[placeholder*="option A"]').fill("London")
      await page.locator('input[placeholder*="option B"]').fill("Berlin")
      await page.locator('input[placeholder*="option C"]').fill("Paris")
      await page.locator('input[placeholder*="option D"]').fill("Madrid")
      await page.getByRole("radio", { name: "C" }).click({ force: true })

      // Save button should be enabled after filling required fields
      const saveButton = page.getByRole("button", { name: "Save Changes" })
      await expect(saveButton).toBeEnabled()
    })

    test("should successfully create question and close dialog", async ({
      page,
    }) => {
      // Mock successful question creation
      await page.route(`**/api/v1/questions/${mockQuizId}`, async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify({
              id: "new-question-id",
              quiz_id: mockQuizId,
              question_type: "multiple_choice",
              question_data: {
                question_text: "What is the capital of France?",
                option_a: "London",
                option_b: "Berlin",
                option_c: "Paris",
                option_d: "Madrid",
                correct_answer: "C",
                explanation: null,
              },
              difficulty: "medium",
              tags: [],
              is_approved: false,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }),
          })
        } else {
          // GET request
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify([]),
          })
        }
      })

      // Open dialog and select MCQ
      await page.getByRole("button", { name: "Add Question" }).click()
      await page.getByText("Multiple Choice").click()

      // Fill form using flexible selectors
      await page.locator('textarea[placeholder*="question text"]').fill("What is the capital of France?")
      await page.locator('input[placeholder*="option A"]').fill("London")
      await page.locator('input[placeholder*="option B"]').fill("Berlin")
      await page.locator('input[placeholder*="option C"]').fill("Paris")
      await page.locator('input[placeholder*="option D"]').fill("Madrid")
      await page.getByRole("radio", { name: "C" }).click({ force: true })

      // Save question
      await page.getByRole("button", { name: "Save Changes" }).click()

      // Dialog should close automatically on successful creation
      await expect(page.getByRole("dialog")).not.toBeVisible()
    })

    test("should handle API errors gracefully", async ({ page }) => {
      // Mock API error
      await page.route(`**/api/v1/questions/${mockQuizId}`, async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 400,
            contentType: "application/json",
            body: JSON.stringify({
              detail: "Validation error: Question text is required",
            }),
          })
        } else {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify([]),
          })
        }
      })

      // Open dialog and select MCQ
      await page.getByRole("button", { name: "Add Question" }).click()
      await page.getByText("Multiple Choice").click()

      // Fill form using flexible selectors
      await page.locator('textarea[placeholder*="question text"]').fill("What is the capital of France?")
      await page.locator('input[placeholder*="option A"]').fill("London")
      await page.locator('input[placeholder*="option B"]').fill("Berlin")
      await page.locator('input[placeholder*="option C"]').fill("Paris")
      await page.locator('input[placeholder*="option D"]').fill("Madrid")
      await page.getByRole("radio", { name: "C" }).click({ force: true })

      // Try to save - should show error
      await page.getByRole("button", { name: "Save Changes" }).click()

      // Dialog should remain open on error
      await expect(page.getByRole("dialog")).toBeVisible()
    })
  })

  test.describe("Responsive Design", () => {
    test("should work properly on mobile devices", async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 })

      const mockQuiz = {
        id: mockQuizId,
        title: "Mobile Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 10,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "ready_for_review",
        content_extracted_at: "2024-01-15T11:00:00Z",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      }

      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockQuiz),
        })
      })

      await page.route(`**/api/v1/questions/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      })

      await page.route(`**/api/v1/questions/${mockQuizId}/stats`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            total_questions: 0,
            approved_questions: 0,
            approval_percentage: 0,
          }),
        })
      })

      await page.goto(`/quiz/${mockQuizId}/questions`)

      // Add Question button should be visible on mobile
      await expect(page.getByRole("button", { name: "Add Question" })).toBeVisible()

      // Open dialog
      await page.getByRole("button", { name: "Add Question" }).click()

      // Dialog should be full-screen on mobile
      await expect(page.getByRole("dialog")).toBeVisible()

      // Question type cards should stack properly on mobile
      await expect(page.getByText("Multiple Choice")).toBeVisible()
      await expect(page.getByText("True/False")).toBeVisible()
    })
  })

  test.describe("Accessibility", () => {
    test("should have proper ARIA labels and roles", async ({ page }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Accessibility Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 10,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "ready_for_review",
        content_extracted_at: "2024-01-15T11:00:00Z",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      }

      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockQuiz),
        })
      })

      await page.route(`**/api/v1/questions/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      })

      await page.route(`**/api/v1/questions/${mockQuizId}/stats`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            total_questions: 0,
            approved_questions: 0,
            approval_percentage: 0,
          }),
        })
      })

      await page.goto(`/quiz/${mockQuizId}/questions`)

      // Check button has proper role and is accessible
      const addButton = page.getByRole("button", { name: "Add Question" })
      await expect(addButton).toBeVisible()

      // Open dialog
      await addButton.click()

      // Check dialog has proper role
      await expect(page.getByRole("dialog")).toBeVisible()

      // Check heading structure
      await expect(page.getByRole("heading", { name: "Add Question" })).toBeVisible()

      // Select a question type to check form accessibility
      await page.getByText("Multiple Choice").click()

      // Check form labels and inputs are present
      await expect(page.getByText("Question Text")).toBeVisible()
      await expect(page.getByText("Option A")).toBeVisible()
      await expect(page.locator('textarea[placeholder*="question text"]')).toBeVisible()
      await expect(page.locator('input[placeholder*="option A"]')).toBeVisible()

      // Check radio group has proper labels
      await expect(page.getByRole("radiogroup")).toBeVisible()
    })
  })
})
