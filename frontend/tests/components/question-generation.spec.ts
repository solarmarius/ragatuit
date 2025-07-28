import { expect, test } from "@playwright/test"

test.describe("Question Generation Components", () => {
  const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"

  test.beforeEach(async ({ page }) => {
    // Mock the current user API call
    await page.route("**/api/v1/users/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          name: "Test User",
          onboarding_completed: true,
        }),
      })
    })
  })

  test.describe("QuestionGenerationTrigger", () => {
    test("should show trigger button when generation failed", async ({
      page,
    }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        status: "failed",
        failure_reason: "llm_generation_error",
        last_status_update: "2024-01-16T14:20:00Z",
        content_extracted_at: "2024-01-15T11:00:00Z",
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

      await page.goto(`/quiz/${mockQuizId}`)

      // Check trigger button is visible
      const triggerButton = page.getByRole("button", {
        name: /Retry Question Generation/i,
      })
      await expect(triggerButton).toBeVisible()
      await expect(triggerButton).toContainText("Retry Question Generation")
    })

    test("should not show trigger button when generation is in progress", async ({
      page,
    }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        status: "generating_questions",
        last_status_update: "2024-01-16T14:20:00Z",
        content_extracted_at: "2024-01-15T11:00:00Z",
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

      await page.goto(`/quiz/${mockQuizId}`)

      // Trigger button should not be visible
      await expect(
        page.getByRole("button", { name: /Generate Questions/i }),
      ).not.toBeVisible()
    })
  })

  test.describe("QuestionStats", () => {
    test("should display question statistics", async ({ page }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        status: "ready_for_review",
        last_status_update: "2024-01-16T14:20:00Z",
        content_extracted_at: "2024-01-15T11:00:00Z",
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

      // Mock question stats API
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              total: 50,
              pending: 30,
              approved: 20,
            }),
          })
        },
      )

      // Go directly to questions route
      await page.goto(`/quiz/${mockQuizId}/questions`)

      // Check statistics are displayed
      await expect(page.getByText("Progress")).toBeVisible()
      await expect(page.getByText("20 of 50")).toBeVisible()
    })

    test("should show progress bar with correct percentage", async ({
      page,
    }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        status: "ready_for_review",
        last_status_update: "2024-01-16T14:20:00Z",
        content_extracted_at: "2024-01-15T11:00:00Z",
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

      // Mock question stats API - 40% approved (20/50)
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              total: 50,
              pending: 30,
              approved: 20,
            }),
          })
        },
      )

      await page.goto(`/quiz/${mockQuizId}`)
      await page.getByRole("tab", { name: "Questions" }).click()

      // Check progress bar shows 40%
      await expect(page.getByText("40%")).toBeVisible()

      // Check progress bar visual
      const progressBar = page.getByRole("progressbar")
      await expect(progressBar).toBeVisible()
      await expect(progressBar).toHaveAttribute("aria-valuenow", "40")
    })

    test("should show loading state for stats", async ({ page }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        status: "ready_for_review",
        last_status_update: "2024-01-16T14:20:00Z",
        content_extracted_at: "2024-01-15T11:00:00Z",
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

      // Mock question stats API with delay
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await new Promise((resolve) => setTimeout(resolve, 500))
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              total: 50,
              pending: 30,
              approved: 20,
            }),
          })
        },
      )

      // Go directly to questions route to trigger loading
      await page.goto(`/quiz/${mockQuizId}/questions`)

      // Check skeleton loader is visible
      await expect(page.locator('[class*="skeleton"]').first()).toBeVisible()
    })

    test("should handle stats API error", async ({ page }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        status: "ready_for_review",
        last_status_update: "2024-01-16T14:20:00Z",
        content_extracted_at: "2024-01-15T11:00:00Z",
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

      // Mock question stats API to fail
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 500,
            contentType: "application/json",
            body: JSON.stringify({ detail: "Failed to load statistics" }),
          })
        },
      )

      await page.goto(`/quiz/${mockQuizId}`)
      await page.getByRole("tab", { name: "Questions" }).click()

      // Check error message - wait longer and check for actual error text that appears
      await expect(
        page.getByText("Failed to load question statistics"),
      ).toBeVisible({ timeout: 10000 })
    })

    test("should show zero state correctly", async ({ page }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        status: "ready_for_review",
        last_status_update: "2024-01-16T14:20:00Z",
        content_extracted_at: "2024-01-15T11:00:00Z",
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

      // Mock question stats API with zero questions
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              total: 0,
              pending: 0,
              approved: 0,
            }),
          })
        },
      )

      await page.goto(`/quiz/${mockQuizId}`)
      await page.getByRole("tab", { name: "Questions" }).click()

      // Check zero state
      await expect(
        page.getByText(
          "No questions generated yet. Questions will appear here once generation is complete.",
        ),
      ).toBeVisible()
      await expect(page.getByText("0 of 0")).toBeVisible()
    })

    test("should show all approved state", async ({ page }) => {
      const mockQuiz = {
        id: mockQuizId,
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        status: "ready_for_review",
        last_status_update: "2024-01-16T14:20:00Z",
        content_extracted_at: "2024-01-15T11:00:00Z",
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

      // Mock question stats API - all approved
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              total: 50,
              pending: 0,
              approved: 50,
            }),
          })
        },
      )

      await page.goto(`/quiz/${mockQuizId}`)
      await page.getByRole("tab", { name: "Questions" }).click()

      // Check 100% progress
      await expect(page.getByText("100%")).toBeVisible()
      await expect(page.getByText("50 of 50")).toBeVisible()

      // Progress bar should show complete
      const progressBar = page.getByRole("progressbar")
      await expect(progressBar).toHaveAttribute("aria-valuenow", "100")
    })
  })
})
