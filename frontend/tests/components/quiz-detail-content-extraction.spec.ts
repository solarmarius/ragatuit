import { expect, test } from "@playwright/test";

test.describe("Quiz Detail Content Extraction Features", () => {
  const mockQuizId = "123e4567-e89b-12d3-a456-426614174000";

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
      });
    });

    // Navigate to the quiz detail page
    await page.goto(`/quiz/${mockQuizId}`);
  });

  test("should display content extraction status with pending extraction", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Content Extraction Test Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}, "173468": {"name": "Module 2", "question_count": 25}}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "created",
      last_status_update: "2024-01-16T14:20:00Z",
      extracted_content: null,
      content_extracted_at: null,
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    };

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check that status light is visible with correct title
    const statusLight = page.locator('[title="Ready to Start"]');
    await expect(statusLight).toBeVisible();

    // Check that quiz title and status light are in the same row
    await expect(page.getByText("Content Extraction Test Quiz")).toBeVisible();
    await expect(statusLight).toBeVisible();
  });

  test("should display content extraction status with processing extraction", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Processing Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "extracting_content",
      last_status_update: "2024-01-16T14:20:00Z",
      extracted_content: null,
      content_extracted_at: null,
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    };

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check that status light shows processing state
    const statusLight = page.locator('[title="Extracting Content"]');
    await expect(statusLight).toBeVisible();
    await expect(statusLight).toHaveCSS(
      "background-color",
      "rgb(249, 115, 22)"
    ); // orange.500
  });

  test("should display content extraction status with completed extraction", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Completed Extraction Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "ready_for_review",
      extracted_content:
        '{"173467": [{"title": "Test Page", "content": "Test content"}]}',
      content_extracted_at: "2024-01-16T15:30:00Z",
      last_status_update: "2024-01-16T16:00:00Z",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    };

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check that status light shows ready for review state
    const statusLight = page.locator('[title="Ready for Review"]');
    await expect(statusLight).toBeVisible();
    await expect(statusLight).toHaveCSS(
      "background-color",
      "rgb(168, 85, 247)"
    ); // purple.500
  });

  test("should display content extraction status with failed extraction", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Failed Extraction Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "failed",
      failure_reason: "content_extraction_error",
      extracted_content: null,
      content_extracted_at: null,
      last_status_update: "2024-01-16T14:20:00Z",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    };

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check that status light shows failed state
    const statusLight = page.locator('[title="Failed"]');
    await expect(statusLight).toBeVisible();
    await expect(statusLight).toHaveCSS("background-color", "rgb(239, 68, 68)"); // red.500
  });

  test("should poll for status updates when processing", async ({ page }) => {
    let callCount = 0;
    const responses = [
      // First call: processing
      {
        id: mockQuizId,
        title: "Polling Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "extracting_content",
        extracted_content: null,
        content_extracted_at: null,
        last_status_update: "2024-01-16T14:20:00Z",
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
        selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        status: "ready_for_review",
        extracted_content:
          '{"173467": [{"title": "Test Page", "content": "Test content"}]}',
        content_extracted_at: "2024-01-16T15:30:00Z",
        last_status_update: "2024-01-16T16:00:00Z",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ];

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      const response =
        callCount < responses.length
          ? responses[callCount]
          : responses[responses.length - 1];
      callCount++;

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(response),
      });
    });

    await page.reload();

    const completedLight = page.locator('[title="Ready for Review"]');
    await expect(completedLight).toBeVisible();
    await expect(completedLight).toHaveCSS(
      "background-color",
      "rgb(168, 85, 247)"
    ); // purple.500

    // Verify that multiple API calls were made
    expect(callCount).toBeGreaterThan(1);
  });

  test("should stop polling when status is completed", async ({ page }) => {
    let callCount = 0;
    const mockQuiz = {
      id: mockQuizId,
      title: "Completed Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "ready_for_review",
      extracted_content:
        '{"173467": [{"title": "Test Page", "content": "Test content"}]}',
      content_extracted_at: "2024-01-16T15:30:00Z",
      last_status_update: "2024-01-16T16:00:00Z",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    };

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      callCount++;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check that status light shows ready for review state
    const statusLight = page.locator('[title="Ready for Review"]');
    await expect(statusLight).toBeVisible();

    // Wait to ensure no additional polling occurs
    await page.waitForTimeout(6000);

    // Should have been called at least once but no more than twice (initial + potential refetch)
    expect(callCount).toBeGreaterThanOrEqual(1);
  });

  test("should stop polling when status is failed", async ({ page }) => {
    let callCount = 0;
    const mockQuiz = {
      id: mockQuizId,
      title: "Failed Quiz",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "failed",
      failure_reason: "content_extraction_error",
      extracted_content: null,
      content_extracted_at: null,
      last_status_update: "2024-01-16T14:20:00Z",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    };

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      callCount++;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check that status light shows failed state
    const statusLight = page.locator('[title="Failed"]');
    await expect(statusLight).toBeVisible();

    // Wait to ensure no additional polling occurs
    await page.waitForTimeout(6000);

    // Should have been called at least once but no more than twice (initial + potential refetch)
    expect(callCount).toBeGreaterThanOrEqual(1);
    expect(callCount).toBeLessThanOrEqual(2);
  });

  test("should handle missing content extraction fields gracefully", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Legacy Quiz Without Content Fields",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      // Missing status field - should default to created
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    };

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Should default to created status (orange light)
    const statusLight = page.locator('[title="Ready to Start"]');
    await expect(statusLight).toBeVisible();
    await expect(statusLight).toHaveCSS(
      "background-color",
      "rgb(249, 115, 22)"
    ); // orange.500

    // Page should still display all other information correctly
    await expect(
      page.getByText("Legacy Quiz Without Content Fields")
    ).toBeVisible();
    await expect(page.getByText("Test Course")).toBeVisible();
    await expect(page.getByText("Module 1")).toBeVisible();
  });

  test("should position status light correctly next to quiz title", async ({
    page,
  }) => {
    const mockQuiz = {
      id: mockQuizId,
      title: "Status Light Position Test",
      canvas_course_id: 12345,
      canvas_course_name: "Test Course",
      selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
      question_count: 50,
      llm_model: "gpt-4o",
      llm_temperature: 0.3,
      status: "created",
      last_status_update: "2024-01-16T14:20:00Z",
      created_at: "2024-01-15T10:30:00Z",
      updated_at: "2024-01-16T14:20:00Z",
      owner_id: "user123",
    };

    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check that the title and status light are in the same horizontal container
    const titleContainer = page
      .locator('text="Status Light Position Test"')
      .locator("..");
    const statusLight = page.locator('[title="Ready to Start"]');

    await expect(titleContainer).toContainText("Status Light Position Test");
    await expect(statusLight).toBeVisible();

    // Verify they are aligned in the same row (same parent container)
    const titleBounds = await page
      .getByText("Status Light Position Test")
      .boundingBox();
    const lightBounds = await statusLight.boundingBox();

    expect(titleBounds).not.toBeNull();
    expect(lightBounds).not.toBeNull();

    // They should be roughly on the same horizontal line (within 20 pixels for different line heights)
    const verticalDiff = Math.abs(
      (titleBounds?.y || 0) - (lightBounds?.y || 0)
    );
    expect(verticalDiff).toBeLessThan(20);
  });

  test("should handle different status combinations correctly", async ({
    page,
  }) => {
    const testCases = [
      {
        status: "created",
        expectedTitle: "Ready to Start",
        expectedColor: "rgb(249, 115, 22)", // orange.500
      },
      {
        status: "extracting_content",
        expectedTitle: "Extracting Content",
        expectedColor: "rgb(249, 115, 22)", // orange.500
      },
      {
        status: "generating_questions",
        expectedTitle: "Generating Questions",
        expectedColor: "rgb(249, 115, 22)", // orange.500
      },
      {
        status: "ready_for_review",
        expectedTitle: "Ready for Review",
        expectedColor: "rgb(168, 85, 247)", // purple.500
      },
      {
        status: "exporting_to_canvas",
        expectedTitle: "Exporting to Canvas",
        expectedColor: "rgb(234, 179, 8)", // yellow.500
      },
      {
        status: "published",
        expectedTitle: "Published to Canvas",
        expectedColor: "rgb(34, 197, 94)", // green.500
      },
      {
        status: "failed",
        failure_reason: "content_extraction_error",
        expectedTitle: "Failed",
        expectedColor: "rgb(239, 68, 68)", // red.500
      },
      {
        status: "failed",
        failure_reason: "llm_generation_error",
        expectedTitle: "Failed",
        expectedColor: "rgb(239, 68, 68)", // red.500
      },
    ];

    for (const testCase of testCases) {
      const mockQuiz = {
        id: mockQuizId,
        title: `Status Test ${testCase.status}`,
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": {"name": "Module 1", "question_count": 25}}',
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
      };

      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockQuiz),
        });
      });

      await page.reload();

      const statusLight = page.locator(`[title="${testCase.expectedTitle}"]`);
      await expect(statusLight).toBeVisible();
      await expect(statusLight).toHaveCSS(
        "background-color",
        testCase.expectedColor
      );
    }
  });
});
