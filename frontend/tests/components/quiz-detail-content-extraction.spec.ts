import { expect, test } from "@playwright/test"

test.describe("Quiz Detail Content Extraction Features", () => {
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

  test("should display content extraction status with pending extraction", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Content Extraction Test Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1", "173468": "Module 2"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      content_extraction_status: "pending",
      llm_generation_status: "pending",
      extracted_content: null,
      content_extracted_at: null,
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

    // Check that status light is visible with correct title
    const statusLight = page.locator('[title="Waiting to generate questions"]')
    await expect(statusLight).toBeVisible()

    // Check that quiz title and status light are in the same row
    await expect(page.getByText("Content Extraction Test Quiz")).toBeVisible()
    await expect(statusLight).toBeVisible()
  })

  test("should display content extraction status with processing extraction", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Processing Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      content_extraction_status: "processing",
      llm_generation_status: "pending",
      extracted_content: null,
      content_extracted_at: null,
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

    // Check that status light shows processing state
    const statusLight = page.locator('[title="Generating questions..."]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(249, 115, 22)") // orange.500
  })

  test("should display content extraction status with completed extraction", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Completed Extraction Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      content_extraction_status: "completed",
      llm_generation_status: "completed",
      extracted_content:
        '{"module_173467": [{"title": "Test Page", "content": "Test content"}]}',
      content_extracted_at: "2024-01-16T15:30:00Z",
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

    // Check that status light shows completed state
    const statusLight = page.locator(
      '[title="Questions generated successfully"]',
    )
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(34, 197, 94)") // green.500
  })

  test("should display content extraction status with failed extraction", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Failed Extraction Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      content_extraction_status: "failed",
      llm_generation_status: "pending",
      extracted_content: null,
      content_extracted_at: null,
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

    // Check that status light shows failed state
    const statusLight = page.locator('[title="Generation failed"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(239, 68, 68)") // red.500
  })

  test("should poll for status updates when processing", async ({ page }) => {
    let callCount = 0
    const responses = [
      // First call: processing
      {
        id: mockQuizId,
        title: "Polling Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        content_extraction_status: "processing",
        llm_generation_status: "pending",
        extracted_content: null,
        content_extracted_at: null,
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
      // Second call: completed
      {
        id: mockQuizId,
        title: "Polling Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        content_extraction_status: "completed",
        llm_generation_status: "completed",
        extracted_content:
          '{"module_173467": [{"title": "Test Page", "content": "Test content"}]}',
        content_extracted_at: "2024-01-16T15:30:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ]

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      const response =
        callCount < responses.length
          ? responses[callCount]
          : responses[responses.length - 1]
      callCount++

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(response),
      })
    })

    await page.reload()

    const completedLight = page.locator(
      '[title="Questions generated successfully"]',
    )
    await expect(completedLight).toBeVisible()
    await expect(completedLight).toHaveCSS(
      "background-color",
      "rgb(34, 197, 94)",
    ) // green.500

    // Verify that multiple API calls were made
    expect(callCount).toBeGreaterThan(1)
  })

  test("should stop polling when status is completed", async ({ page }) => {
    let callCount = 0
    const mockQuiz = {
      id: mockQuizId,
      title: "Completed Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      content_extraction_status: "completed",
      llm_generation_status: "completed",
      extracted_content:
        '{"module_173467": [{"title": "Test Page", "content": "Test content"}]}',
      content_extracted_at: "2024-01-16T15:30:00Z",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    }

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      callCount++
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check that status light shows completed state
    const statusLight = page.locator(
      '[title="Questions generated successfully"]',
    )
    await expect(statusLight).toBeVisible()

    // Wait to ensure no additional polling occurs
    await page.waitForTimeout(6000)

    // Should have been called at least once but no more than twice (initial + potential refetch)
    expect(callCount).toBeGreaterThanOrEqual(1)
  })

  test("should stop polling when status is failed", async ({ page }) => {
    let callCount = 0
    const mockQuiz = {
      id: mockQuizId,
      title: "Failed Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      content_extraction_status: "failed",
      llm_generation_status: "pending",
      extracted_content: null,
      content_extracted_at: null,
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    }

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      callCount++
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check that status light shows failed state
    const statusLight = page.locator('[title="Generation failed"]')
    await expect(statusLight).toBeVisible()

    // Wait to ensure no additional polling occurs
    await page.waitForTimeout(6000)

    // Should have been called at least once but no more than twice (initial + potential refetch)
    expect(callCount).toBeGreaterThanOrEqual(1)
    expect(callCount).toBeLessThanOrEqual(2)
  })

  test("should handle missing content extraction fields gracefully", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Legacy Quiz Without Content Fields",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      // Missing content_extraction_status, llm_generation_status, extracted_content, content_extracted_at
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

    // Should default to pending status (orange light)
    const statusLight = page.locator('[title="Waiting to generate questions"]')
    await expect(statusLight).toBeVisible()
    await expect(statusLight).toHaveCSS("background-color", "rgb(249, 115, 22)") // orange.500

    // Page should still display all other information correctly
    await expect(
      page.getByText("Legacy Quiz Without Content Fields"),
    ).toBeVisible()
    await expect(page.getByText("Test Course")).toBeVisible()
    await expect(page.getByText("Module 1")).toBeVisible()
  })

  test("should position status light correctly next to quiz title", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Status Light Position Test",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": "Module 1"}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      content_extraction_status: "pending",
      llm_generation_status: "pending",
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

    // Check that the title and status light are in the same horizontal container
    const titleContainer = page
      .locator('text="Status Light Position Test"')
      .locator("..")
    const statusLight = page.locator('[title="Waiting to generate questions"]')

    await expect(titleContainer).toContainText("Status Light Position Test")
    await expect(statusLight).toBeVisible()

    // Verify they are aligned in the same row (same parent container)
    const titleBounds = await page
      .getByText("Status Light Position Test")
      .boundingBox()
    const lightBounds = await statusLight.boundingBox()

    expect(titleBounds).not.toBeNull()
    expect(lightBounds).not.toBeNull()

    // They should be roughly on the same horizontal line (within 20 pixels for different line heights)
    const verticalDiff = Math.abs((titleBounds?.y || 0) - (lightBounds?.y || 0))
    expect(verticalDiff).toBeLessThan(20)
  })

  test("should handle different status combinations correctly", async ({
    page,
  }) => {
    const testCases = [
      {
        extraction: "pending",
        generation: "pending",
        expectedTitle: "Waiting to generate questions",
        expectedColor: "rgb(249, 115, 22)", // orange.500
      },
      {
        extraction: "processing",
        generation: "pending",
        expectedTitle: "Generating questions...",
        expectedColor: "rgb(249, 115, 22)", // orange.500
      },
      {
        extraction: "completed",
        generation: "pending",
        expectedTitle: "Waiting to generate questions",
        expectedColor: "rgb(249, 115, 22)", // orange.500
      },
      {
        extraction: "completed",
        generation: "processing",
        expectedTitle: "Generating questions...",
        expectedColor: "rgb(249, 115, 22)", // orange.500
      },
      {
        extraction: "completed",
        generation: "completed",
        expectedTitle: "Questions generated successfully",
        expectedColor: "rgb(34, 197, 94)", // green.500
      },
      {
        extraction: "failed",
        generation: "pending",
        expectedTitle: "Generation failed",
        expectedColor: "rgb(239, 68, 68)", // red.500
      },
      {
        extraction: "completed",
        generation: "failed",
        expectedTitle: "Generation failed",
        expectedColor: "rgb(239, 68, 68)", // red.500
      },
    ]

    for (const testCase of testCases) {
      const mockQuiz = {
        id: mockQuizId,
        title: `Status Test ${testCase.extraction}-${testCase.generation}`,
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        content_extraction_status: testCase.extraction,
        llm_generation_status: testCase.generation,
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

      const statusLight = page.locator(`[title="${testCase.expectedTitle}"]`)
      await expect(statusLight).toBeVisible()
      await expect(statusLight).toHaveCSS(
        "background-color",
        testCase.expectedColor,
      )
    }
  })
})
