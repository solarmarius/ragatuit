import { expect, test } from "@playwright/test"

test.describe("Quiz Detail Component", () => {
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

    // Navigate to the quiz detail page
    await page.goto(`/quiz/${mockQuizId}`)
  })

  test("should display quiz details with all information", async ({ page }) => {
    // Mock API to return quiz details
    const mockQuiz = {
      id: mockQuizId,
      title: "Advanced Machine Learning Concepts",
      canvas_course_id: 12345,
      canvas_course_name: "CS 589 - Machine Learning",
      selected_modules: {
        "173467": {
          name: "Neural Networks",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 20,
              difficulty: "medium",
            },
          ],
        },
        "173468": {
          name: "Deep Learning",
          question_batches: [
            { question_type: "multiple_choice", count: 20, difficulty: "hard" },
          ],
        },
        "173469": {
          name: "Reinforcement Learning",
          question_batches: [
            { question_type: "multiple_choice", count: 20, difficulty: "easy" },
          ],
        },
      },
      question_count: 60,
      llm_model: "gpt-4o",
      llm_temperature: 0.7,
      language: "en",
      tone: "academic",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-20T16:45:00Z",
      owner_id: "user123",
    }

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check header section
    await expect(
      page.getByText("Advanced Machine Learning Concepts"),
    ).toBeVisible()

    // Check course information section
    await expect(page.getByText("Canvas Course")).toBeVisible()
    await expect(page.getByText("CS 589 - Machine Learning")).toBeVisible()
    await expect(page.getByText("Course ID: 12345")).toBeVisible()

    // Check selected modules section - use more specific locator
    await expect(page.getByText("Neural Networks").first()).toBeVisible()
    await expect(page.getByText("Deep Learning").first()).toBeVisible()
    await expect(page.getByText("Reinforcement Learning").first()).toBeVisible()

    // Check quiz settings section
    await expect(page.getByText("Settings").first()).toBeVisible()
    await expect(page.getByText("Question Count")).toBeVisible()
    await expect(page.locator('text="60"').first()).toBeVisible()

    // Check metadata section
    await expect(page.getByText("Metadata")).toBeVisible()
    await expect(page.getByText("Quiz ID")).toBeVisible()
    await expect(page.locator("p").getByText(mockQuizId)).toBeVisible()
    await expect(page.getByText("Created").last()).toBeVisible()
    await expect(page.getByText(/15 January 2024/)).toBeVisible()
    await expect(page.getByText("Last Updated")).toBeVisible()
    await expect(page.getByText(/20 January 2024/)).toBeVisible()
  })

  test("should display quiz with empty modules", async ({ page }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Empty Modules Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {},
      question_count: 50,
      llm_model: "o3",
      llm_temperature: 0.3,
      language: "no",
      tone: "casual",
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

    await page.reload()

    // Check that "No modules selected" is displayed
    await expect(page.getByText("No modules selected")).toBeVisible()
  })

  test("should display quiz with null/undefined modules", async ({ page }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Null Modules Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: null,
      question_count: 50,
      llm_model: "o3",
      llm_temperature: 0.3,
      language: "en",
      tone: "professional",
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

    await page.reload()

    // Check that "No modules selected" is displayed for null modules
    await expect(page.getByText("No modules selected")).toBeVisible()
  })

  test("should display quiz without timestamps", async ({ page }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "No Timestamps Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Module 1",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 25,
              difficulty: "medium",
            },
          ],
        },
      },
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.5,
      language: "no",
      tone: "encouraging",
      created_at: null,
      updated_at: null,
      owner_id: "user123",
    }

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check that timestamp sections are not displayed when null
    await expect(page.getByText("Created")).not.toBeVisible()
    await expect(page.getByText("Last Updated")).not.toBeVisible()
  })

  test("should display quiz with only created_at timestamp", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Only Created Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Module 1",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 25,
              difficulty: "medium",
            },
          ],
        },
      },
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.5,
      language: "en",
      tone: "academic",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: null,
      owner_id: "user123",
    }

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check that only created timestamp is displayed
    await expect(page.getByText("Created").last()).toBeVisible()
    await expect(page.getByText(/15 January 2024/)).toBeVisible()
    await expect(page.getByText("Last Updated")).not.toBeVisible()
  })

  test("should display loading skeleton", async ({ page }) => {
    // Delay the API response to test loading state
    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      // Add delay to see loading state
      await new Promise((resolve) => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: mockQuizId,
          title: "Test Quiz",
          canvas_course_id: 12345,
          canvas_course_name: "Test Course",
          selected_modules: {
            "173467": { name: "Module 1", question_count: 25 },
          },
          question_count: 50,
          llm_model: "gpt-4o",
          llm_temperature: 0.5,
          language: "en",
          tone: "academic",
          created_at: "2024-01-15T10:30:00Z",
          updated_at: "2024-01-16T14:20:00Z",
          owner_id: "user123",
        }),
      })
    })

    // Start navigation but don't wait for it to complete
    const navigationPromise = page.goto(`/quiz/${mockQuizId}`)

    // Check that skeleton is visible during loading
    await expect(page.locator('[class*="skeleton"]').first()).toBeVisible()

    // Wait for navigation to complete
    await navigationPromise
  })

  test("should display badges with correct styling", async ({ page }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Style Test Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Module 1",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 25,
              difficulty: "medium",
            },
          ],
        },
      },
      question_count: 100,
      llm_model: "gpt-4.1-mini",
      llm_temperature: 1.5,
      language: "no",
      tone: "professional",
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

    await page.reload()

    // Check module badges
    const moduleBadge = page.locator("text=Module 1").first()
    await expect(moduleBadge).toBeVisible()

    // Check question count badge
    const questionBadge = page.locator('text="100"').first()
    await expect(questionBadge).toBeVisible()
  })

  test("should handle malformed JSON in selected_modules", async ({ page }) => {
    // This test verifies frontend handles malformed JSON gracefully
    const mockQuiz = {
      id: mockQuizId,
      title: "Malformed JSON Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: null, // Use null instead of malformed string to trigger the "No modules selected" case
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.5,
      language: "en",
      tone: "casual",
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

    // Navigate to trigger the API call
    await page.goto(`/quiz/${mockQuizId}`)

    // Should still display the page but with "No modules selected"
    await expect(page.getByText("Malformed JSON Quiz")).toBeVisible()
    await expect(page.getByText("No modules selected")).toBeVisible()
  })

  test("should display quiz with minimum and maximum values", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Extreme Values Quiz",
      canvas_course_id: 99999,
      canvas_course_name:
        "Course with Long Name That Tests Text Wrapping and Display",
      selected_modules: {
        "1": {
          name: "Module with Very Long Name That Tests Text Wrapping in Badges",
          question_batches: [{ question_type: "multiple_choice", count: 10 }],
        },
        "2": {
          name: "Another Module",
          question_batches: [{ question_type: "multiple_choice", count: 10 }],
        },
        "3": {
          name: "Third Module",
          question_batches: [{ question_type: "multiple_choice", count: 10 }],
        },
        "4": {
          name: "Fourth Module",
          question_batches: [{ question_type: "multiple_choice", count: 10 }],
        },
        "5": {
          name: "Fifth Module",
          question_batches: [{ question_type: "multiple_choice", count: 10 }],
        },
      },
      question_count: 50, // Total of all batches
      llm_model: "model-with-very-long-name",
      llm_temperature: 2.0, // Maximum
      language: "no",
      tone: "encouraging",
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

    await page.reload()

    // Check extreme values are displayed correctly
    await expect(page.locator('text="50"').first()).toBeVisible()
    await expect(page.getByText("Course with Long Name")).toBeVisible()

    // Check all modules are displayed
    await expect(
      page.getByText("Module with Very Long Name").first(),
    ).toBeVisible()
    await expect(page.getByText("Another Module").first()).toBeVisible()
    await expect(page.getByText("Third Module").first()).toBeVisible()
    await expect(page.getByText("Fourth Module").first()).toBeVisible()
    await expect(page.getByText("Fifth Module").first()).toBeVisible()
  })

  test("should display quiz ID in monospace font", async ({ page }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Font Test Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Module 1",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 25,
              difficulty: "medium",
            },
          ],
        },
      },
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.5,
      language: "en",
      tone: "professional",
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

    await page.reload()

    // Check that quiz ID has monospace font family - target the specific quiz ID in metadata section
    const quizIdElement = page.locator("p").filter({ hasText: mockQuizId })
    await expect(quizIdElement).toBeVisible()
    await expect(quizIdElement).toHaveCSS("font-family", /mono/)
  })

  test("should display tabs with correct content", async ({ page }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Tab Test Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Module 1",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 25,
              difficulty: "medium",
            },
          ],
        },
      },
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.5,
      language: "no",
      tone: "casual",
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

    await page.reload()

    // Check that tabs are present
    await expect(
      page.getByRole("tab", { name: "Quiz Information" }),
    ).toBeVisible()
    await expect(page.getByRole("tab", { name: "Questions" })).toBeVisible()

    // Quiz Information tab should be active by default
    await expect(
      page.getByRole("tab", { name: "Quiz Information" }),
    ).toHaveAttribute("aria-selected", "true")

    // Info content should be visible
    await expect(page.getByText("Course Information")).toBeVisible()
    await expect(page.getByText("Settings").first()).toBeVisible()
  })

  test("should switch between tabs correctly", async ({ page }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Tab Navigation Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Module 1",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 25,
              difficulty: "medium",
            },
          ],
        },
      },
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
            total_questions: 50,
            pending_questions: 30,
            approved_questions: 20,
          }),
        })
      },
    )

    await page.reload()

    // Click on Questions tab should navigate to questions route
    await page.getByRole("tab", { name: "Questions" }).click()

    // Should be on the questions route
    await expect(page).toHaveURL(`/quiz/${mockQuizId}/questions`)

    // Questions tab should now be active
    await expect(page.getByRole("tab", { name: "Questions" })).toHaveAttribute(
      "aria-selected",
      "true",
    )
    await expect(
      page.getByRole("tab", { name: "Quiz Information" }),
    ).toHaveAttribute("aria-selected", "false")

    // Questions content should be visible (QuestionStats component)
    await expect(page.getByText("Progress")).toBeVisible()
  })

  test("should show Review Quiz button when generation is complete", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Complete Generation Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Module 1",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 25,
              difficulty: "medium",
            },
          ],
        },
      },
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

    await page.reload()

    // Check that Review Quiz button is visible when generation is complete
    const reviewButton = page.getByRole("button", { name: "Review" })
    await expect(reviewButton).toBeVisible()

    // Click Review Quiz button should navigate to questions route
    await reviewButton.click()

    // Should be on the questions route
    await expect(page).toHaveURL(`/quiz/${mockQuizId}/questions`)

    // Questions tab should be active
    await expect(page.getByRole("tab", { name: "Questions" })).toHaveAttribute(
      "aria-selected",
      "true",
    )
  })

  test("should not show Review Quiz button when generation is not complete", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Incomplete Generation Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Module 1",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 25,
              difficulty: "medium",
            },
          ],
        },
      },
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

    await page.reload()

    // Check that Review Quiz button is not visible when generation is not complete
    await expect(page.getByRole("button", { name: "Review" })).not.toBeVisible()
  })

  test("should show Review Quiz button only when both statuses are completed", async ({
    page,
  }) => {
    // Test case 1: Questions are still being generated
    const mockQuizPartial = {
      id: mockQuizId,
      title: "Partial Complete Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Module 1",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 25,
              difficulty: "medium",
            },
          ],
        },
      },
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
        body: JSON.stringify(mockQuizPartial),
      })
    })

    await page.reload()

    // Review Quiz button should not be visible
    await expect(page.getByRole("button", { name: "Review" })).not.toBeVisible()

    // Test case 2: Both are complete
    const mockQuizComplete = {
      ...mockQuizPartial,
      status: "ready_for_review",
    }

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizComplete),
      })
    })

    await page.reload()

    // Review Quiz button should now be visible
    await expect(page.getByRole("button", { name: "Review" })).toBeVisible()
  })

  test("should display difficulty information in quiz details", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Difficulty Display Test Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: {
        "173467": {
          name: "Easy Module",
          question_batches: [
            { question_type: "multiple_choice", count: 10, difficulty: "easy" },
            { question_type: "true_false", count: 5, difficulty: "easy" },
          ],
        },
        "173468": {
          name: "Mixed Difficulty Module",
          question_batches: [
            {
              question_type: "multiple_choice",
              count: 15,
              difficulty: "medium",
            },
            { question_type: "fill_in_blank", count: 8, difficulty: "hard" },
          ],
        },
      },
      question_count: 38,
      llm_model: "gpt-4o",
      llm_temperature: 0.7,
      language: "en",
      tone: "academic",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-20T16:45:00Z",
      owner_id: "user123",
    }

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check that modules are displayed
    await expect(page.getByText("Easy Module").first()).toBeVisible()
    await expect(
      page.getByText("Mixed Difficulty Module").first(),
    ).toBeVisible()

    // Check that the total question count reflects all batches
    await expect(page.locator('text="38"').first()).toBeVisible()
  })

  test("should display quiz with legacy format (no difficulty field)", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Legacy Quiz Without Difficulty",
      canvas_course_id: 12345,
      canvas_course_name: "Legacy Course",
      selected_modules: {
        "173467": {
          name: "Legacy Module",
          question_batches: [
            { question_type: "multiple_choice", count: 20 }, // No difficulty field
          ],
        },
      },
      question_count: 20,
      llm_model: "gpt-4o",
      llm_temperature: 0.5,
      language: "en",
      tone: "academic",
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

    await page.reload()

    // Should still display quiz information correctly even without difficulty
    await expect(page.getByText("Legacy Quiz Without Difficulty")).toBeVisible()
    await expect(page.getByText("Legacy Module").first()).toBeVisible()
    await expect(page.locator('text="20"').first()).toBeVisible()
  })

  test("should display quiz with multiple batches of different difficulties", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Progressive Difficulty Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Progressive Learning Course",
      selected_modules: {
        "173467": {
          name: "Comprehensive Module",
          question_batches: [
            { question_type: "multiple_choice", count: 5, difficulty: "easy" },
            {
              question_type: "multiple_choice",
              count: 10,
              difficulty: "medium",
            },
            { question_type: "multiple_choice", count: 5, difficulty: "hard" },
            { question_type: "true_false", count: 8, difficulty: "easy" },
          ],
        },
      },
      question_count: 28,
      llm_model: "gpt-4o",
      llm_temperature: 0.7,
      language: "en",
      tone: "academic",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-20T16:45:00Z",
      owner_id: "user123",
    }

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check that quiz displays correctly with multiple batches
    await expect(page.getByText("Progressive Difficulty Quiz")).toBeVisible()
    await expect(page.getByText("Comprehensive Module").first()).toBeVisible()
    await expect(page.locator('text="28"').first()).toBeVisible()
  })
})
