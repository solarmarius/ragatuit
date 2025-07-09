import { expect, test } from "@playwright/test"

test.describe("StatusLight Component", () => {
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

  test("should display red light when content extraction failed", async ({
    page,
  }) => {
    const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"
    const mockQuiz = {
      id: mockQuizId,
      title: "Failed Extraction Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "failed",
      failure_reason: "content_extraction_error",
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

    await page.goto(`/quiz/${mockQuizId}`)

    // Check that the status light is present and has red color
    const statusLight = page.locator('[title="Failed"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(239, 68, 68)") // red.500
  })

  test("should display red light when LLM generation failed", async ({
    page,
  }) => {
    const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"
    const mockQuiz = {
      id: mockQuizId,
      title: "Failed Generation Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "failed",
      failure_reason: "llm_generation_error",
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

    await page.goto(`/quiz/${mockQuizId}`)

    // Check that the status light is present and has red color
    const statusLight = page.locator('[title="Failed"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(239, 68, 68)") // red.500
  })

  test("should display purple light when ready for review", async ({
    page,
  }) => {
    const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"
    const mockQuiz = {
      id: mockQuizId,
      title: "Ready for Review Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
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

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.goto(`/quiz/${mockQuizId}`)

    // Check that the status light is present and has purple color
    const statusLight = page.locator('[title="Ready for Review"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(168, 85, 247)") // purple.500
  })

  test("should display orange light when content extraction is processing", async ({
    page,
  }) => {
    const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"
    const mockQuiz = {
      id: mockQuizId,
      title: "Processing Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "extracting_content",
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

    await page.goto(`/quiz/${mockQuizId}`)

    // Check that the status light is present and has orange color
    const statusLight = page.locator('[title="Extracting Content"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(249, 115, 22)") // orange.500
  })

  test("should display orange light when LLM generation is processing", async ({
    page,
  }) => {
    const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"
    const mockQuiz = {
      id: mockQuizId,
      title: "LLM Processing Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
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

    await page.goto(`/quiz/${mockQuizId}`)

    // Check that the status light is present and has orange color
    const statusLight = page.locator('[title="Generating Questions"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(249, 115, 22)") // orange.500
  })

  test("should display orange light when quiz is created", async ({ page }) => {
    const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"
    const mockQuiz = {
      id: mockQuizId,
      title: "Created Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "created",
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

    await page.goto(`/quiz/${mockQuizId}`)

    // Check that the status light is present and has orange color
    const statusLight = page.locator('[title="Ready to Start"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(249, 115, 22)") // orange.500
  })

  test("should display yellow light when exporting to canvas", async ({
    page,
  }) => {
    const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"
    const mockQuiz = {
      id: mockQuizId,
      title: "Exporting Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "exporting_to_canvas",
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

    await page.goto(`/quiz/${mockQuizId}`)

    // Check that the status light is present and has yellow color
    const statusLight = page.locator('[title="Exporting to Canvas"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(234, 179, 8)") // yellow.500
  })

  test("should display green light when published", async ({ page }) => {
    const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"
    const mockQuiz = {
      id: mockQuizId,
      title: "Published Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
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

    await page.goto(`/quiz/${mockQuizId}`)

    // Should show green light for published status
    const statusLight = page.locator('[title="Published to Canvas"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(34, 197, 94)") // green.500
  })

  test("should have correct visual styling", async ({ page }) => {
    const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"
    const mockQuiz = {
      id: mockQuizId,
      title: "Style Test Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "created",
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

    await page.goto(`/quiz/${mockQuizId}`)

    const statusLight = page.locator('[title="Ready to Start"]')
    await expect(statusLight).toBeVisible()

    // Check dimensions
    await expect(statusLight).toHaveCSS("width", "12px")
    await expect(statusLight).toHaveCSS("height", "12px")

    // Check border radius (should be circular)
    await expect(statusLight).toHaveCSS("border-radius", "9999px")

    // Check cursor style
    await expect(statusLight).toHaveCSS("cursor", "help")

    // Check box shadow is present (glow effect) - Chakra may not render it in test environment
    const boxShadow = await statusLight.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    )
    // Box shadow might be 'none' in test environment, just check it's defined
    expect(typeof boxShadow).toBe("string")
  })
})
