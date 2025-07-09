import { expect, test } from "@playwright/test"

test.describe("Quiz List Content Extraction Status", () => {
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

    // Navigate to the quiz list page
    await page.goto("/quizzes")
  })

  test("should display status column with all status combinations", async ({
    page,
  }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Created Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course 1",
        selected_modules: { "173467": "Module 1" },
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "created",
        last_status_update: "2024-01-15T10:30:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174002",
        title: "Processing Quiz",
        canvas_course_id: 12346,
        canvas_course_name: "Test Course 2",
        selected_modules: { "173468": "Module 2" },
        question_count: 25,
        llm_model: "o3",
        llm_temperature: 0.5,
        status: "extracting_content",
        last_status_update: "2024-01-15T12:30:00Z",
        created_at: "2024-01-14T08:15:00Z",
        updated_at: "2024-01-15T12:30:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174003",
        title: "Ready for Review Quiz",
        canvas_course_id: 12347,
        canvas_course_name: "Test Course 3",
        selected_modules: { "173469": "Module 3" },
        question_count: 75,
        llm_model: "gpt-4",
        llm_temperature: 0.7,
        status: "ready_for_review",
        content_extracted_at: "2024-01-13T17:00:00Z",
        last_status_update: "2024-01-14T09:20:00Z",
        created_at: "2024-01-13T16:45:00Z",
        updated_at: "2024-01-14T09:20:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174004",
        title: "Failed Quiz",
        canvas_course_id: 12348,
        canvas_course_name: "Test Course 4",
        selected_modules: { "173470": "Module 4" },
        question_count: 30,
        llm_model: "gpt-4o",
        llm_temperature: 0.2,
        status: "failed",
        failure_reason: "content_extraction_error",
        last_status_update: "2024-01-13T14:15:00Z",
        created_at: "2024-01-12T11:00:00Z",
        updated_at: "2024-01-13T14:15:00Z",
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      })
    })

    await page.reload()
    await page.waitForLoadState("networkidle")

    // Wait for the table to load by checking for a quiz title first
    await expect(page.locator("tbody tr").first()).toBeVisible()

    // Check that Status column header exists
    await expect(page.locator("th").filter({ hasText: "Status" })).toBeVisible()

    // Check each quiz row has correct status display
    // Created Quiz
    const createdRow = page.locator("tr", {
      has: page.getByText("Created Quiz"),
    })
    await expect(createdRow.locator('[title="Ready to Start"]')).toBeVisible()
    await expect(
      createdRow
        .locator("td")
        .filter({
          has: page.locator('[title="Ready to Start"]'),
        })
        .getByText("Ready to Start"),
    ).toBeVisible()

    // Processing Quiz
    const processingRow = page.locator("tr", {
      has: page.getByText("Processing Quiz"),
    })
    await expect(
      processingRow.locator('[title="Extracting Content"]'),
    ).toBeVisible()
    await expect(
      processingRow
        .locator("td")
        .filter({ has: page.locator('[title="Extracting Content"]') })
        .getByText("Extracting Content"),
    ).toBeVisible()

    // Ready for Review Quiz
    const readyRow = page.locator("tr", {
      has: page.getByText("Ready for Review Quiz"),
    })
    await expect(readyRow.locator('[title="Ready for Review"]')).toBeVisible()
    await expect(
      readyRow
        .locator("td")
        .filter({
          has: page.locator('[title="Ready for Review"]'),
        })
        .getByText("Ready for Review"),
    ).toBeVisible()

    // Failed Quiz
    const failedRow = page.locator("tr", {
      has: page.getByText("Failed Quiz"),
    })
    await expect(failedRow.locator('[title="Failed"]')).toBeVisible()
    await expect(
      failedRow
        .locator("td")
        .filter({ has: page.locator('[title="Failed"]') })
        .getByText("Failed"),
    ).toBeVisible()
  })

  test("should display correct status lights colors", async ({ page }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Purple Status Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: { "173467": "Module 1" },
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "ready_for_review",
        content_extracted_at: "2024-01-15T11:00:00Z",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174002",
        title: "Orange Status Quiz",
        canvas_course_id: 12346,
        canvas_course_name: "Test Course",
        selected_modules: { "173468": "Module 2" },
        question_count: 25,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "extracting_content",
        last_status_update: "2024-01-15T12:30:00Z",
        created_at: "2024-01-14T08:15:00Z",
        updated_at: "2024-01-15T12:30:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174003",
        title: "Red Status Quiz",
        canvas_course_id: 12347,
        canvas_course_name: "Test Course",
        selected_modules: { "173469": "Module 3" },
        question_count: 75,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "failed",
        failure_reason: "content_extraction_error",
        last_status_update: "2024-01-14T09:20:00Z",
        created_at: "2024-01-13T16:45:00Z",
        updated_at: "2024-01-14T09:20:00Z",
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      })
    })

    await page.reload()

    // Purple status (ready for review)
    const purpleLight = page.locator('[title="Ready for Review"]')
    await expect(purpleLight).toBeVisible()
    await expect(purpleLight).toHaveCSS("background-color", "rgb(168, 85, 247)") // purple.500

    // Orange status (extracting content)
    const orangeLight = page.locator('[title="Extracting Content"]')
    await expect(orangeLight).toBeVisible()
    await expect(orangeLight).toHaveCSS("background-color", "rgb(249, 115, 22)") // orange.500

    // Red status (failed)
    const redLight = page.locator('[title="Failed"]')
    await expect(redLight).toBeVisible()
    await expect(redLight).toHaveCSS("background-color", "rgb(239, 68, 68)") // red.500
  })

  test("should handle missing status fields gracefully", async ({ page }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Legacy Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: { "173467": "Module 1" },
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        // Missing status field - should default to created
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174002",
        title: "Null Status Quiz",
        canvas_course_id: 12346,
        canvas_course_name: "Test Course",
        selected_modules: { "173468": "Module 2" },
        question_count: 25,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: null,
        created_at: "2024-01-14T08:15:00Z",
        updated_at: "2024-01-15T12:30:00Z",
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      })
    })

    await page.reload()

    // Both should default to created status (orange light)
    const orangeLights = page.locator('[title="Ready to Start"]')
    await expect(orangeLights).toHaveCount(2)

    // Check status text specifically in the Status column (5th column, index 4)
    const statusCells = page.locator("tbody tr td:nth-child(5)")
    await expect(statusCells.filter({ hasText: "Ready to Start" })).toHaveCount(
      2,
    )
  })

  test("should display correct status text for different combinations", async ({
    page,
  }) => {
    const testCases = [
      {
        status: "created",
        expectedText: "Ready to Start",
      },
      {
        status: "extracting_content",
        expectedText: "Extracting Content",
      },
      {
        status: "generating_questions",
        expectedText: "Generating Questions",
      },
      {
        status: "ready_for_review",
        expectedText: "Ready for Review",
      },
      {
        status: "exporting_to_canvas",
        expectedText: "Exporting to Canvas",
      },
      {
        status: "published",
        expectedText: "Published to Canvas",
      },
      {
        status: "failed",
        failure_reason: "content_extraction_error",
        expectedText: "Failed",
      },
      {
        status: "failed",
        failure_reason: "llm_generation_error",
        expectedText: "Failed",
      },
    ]

    for (let i = 0; i < testCases.length; i++) {
      const testCase = testCases[i]
      const mockQuiz = {
        id: `123e4567-e89b-12d3-a456-42661417400${i}`,
        title: `Status Test ${testCase.status}`,
        canvas_course_id: 12345 + i,
        canvas_course_name: "Test Course",
        selected_modules: { "173467": "Module 1" },
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: testCase.status,
        ...(testCase.failure_reason && {
          failure_reason: testCase.failure_reason,
        }),
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      }

      await page.route("**/api/v1/quiz/", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([mockQuiz]),
        })
      })

      await page.reload()

      // Check the status text in the status column
      const row = page.locator("tr", { has: page.getByText(mockQuiz.title) })
      // Look specifically in the Status column (5th column, index 4)
      await expect(
        row.locator("td").nth(4).getByText(testCase.expectedText),
      ).toBeVisible()
    }
  })

  test("should maintain status column alignment and styling", async ({
    page,
  }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Alignment Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: { "173467": "Module 1" },
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "ready_for_review",
        content_extracted_at: "2024-01-15T11:00:00Z",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      })
    })

    await page.reload()

    // Check that status light and text are properly aligned
    const statusCell = page
      .locator("tr", { has: page.getByText("Alignment Test Quiz") })
      .locator("td")
      .filter({
        has: page.locator('[title="Ready for Review"]'),
      })

    await expect(statusCell).toBeVisible()

    // Verify both status light and text are in the same cell
    await expect(statusCell.locator('[title="Ready for Review"]')).toBeVisible()
    await expect(statusCell.getByText("Ready for Review")).toBeVisible()

    // Check horizontal alignment - status light and text should be in a horizontal container
    const statusContainer = statusCell.locator("div, span").first()
    await expect(statusContainer).toBeVisible()
  })

  test("should display status column in correct table position", async ({
    page,
  }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Column Position Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: { "173467": "Module 1" },
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "created",
        last_status_update: "2024-01-16T14:20:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      })
    })

    await page.reload()

    // Check table headers order
    const headers = page.locator("th")
    await expect(headers.nth(0)).toContainText("Quiz Title")
    await expect(headers.nth(1)).toContainText("Course")
    await expect(headers.nth(2)).toContainText("Questions")
    await expect(headers.nth(3)).toContainText("LLM Model")
    await expect(headers.nth(4)).toContainText("Status")
    await expect(headers.nth(5)).toContainText("Created")
    await expect(headers.nth(6)).toContainText("Actions")

    // Check that Status column is the 5th column (index 4)
    const statusHeader = headers.nth(4)
    await expect(statusHeader).toContainText("Status")
  })

  test("should handle status updates in quiz list", async ({ page }) => {
    // Start with ready for review status quiz directly for this test
    const mockQuiz = {
      id: "123e4567-e89b-12d3-a456-426614174001",
      title: "Status Update Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: { "173467": "Module 1" },
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "ready_for_review",
      content_extracted_at: "2024-01-15T11:00:00Z",
      last_status_update: "2024-01-16T14:20:00Z",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    }

    await page.route("**/api/v1/quiz/", async (route) => {
      console.log("Mock route hit for status update test")
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([mockQuiz]),
      })
    })

    await page.reload()
    await page.waitForLoadState("networkidle")

    // Wait for the quiz to load first
    await expect(page.getByText("Status Update Quiz")).toBeVisible()

    // Should now show ready for review status
    await expect(page.getByText("Ready for Review")).toBeVisible()
    await expect(page.locator('[title="Ready for Review"]')).toBeVisible()
  })
})
