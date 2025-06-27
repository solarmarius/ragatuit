import { expect, test } from "@playwright/test";

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
      });
    });

    // Navigate to the quiz list page
    await page.goto("/quizzes");
  });

  test("should display status column with all status combinations", async ({
    page,
  }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Pending Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course 1",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        content_extraction_status: "pending",
        llm_generation_status: "pending",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174002",
        title: "Processing Quiz",
        canvas_course_id: 12346,
        canvas_course_name: "Test Course 2",
        selected_modules: '{"173468": "Module 2"}',
        question_count: 25,
        llm_model: "o3",
        llm_temperature: 0.5,
        content_extraction_status: "processing",
        llm_generation_status: "pending",
        created_at: "2024-01-14T08:15:00Z",
        updated_at: "2024-01-15T12:30:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174003",
        title: "Completed Quiz",
        canvas_course_id: 12347,
        canvas_course_name: "Test Course 3",
        selected_modules: '{"173469": "Module 3"}',
        question_count: 75,
        llm_model: "gpt-4",
        llm_temperature: 0.7,
        content_extraction_status: "completed",
        llm_generation_status: "completed",
        created_at: "2024-01-13T16:45:00Z",
        updated_at: "2024-01-14T09:20:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174004",
        title: "Failed Quiz",
        canvas_course_id: 12348,
        canvas_course_name: "Test Course 4",
        selected_modules: '{"173470": "Module 4"}',
        question_count: 30,
        llm_model: "gpt-4o",
        llm_temperature: 0.2,
        content_extraction_status: "failed",
        llm_generation_status: "pending",
        created_at: "2024-01-12T11:00:00Z",
        updated_at: "2024-01-13T14:15:00Z",
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      });
    });

    await page.reload();

    // Check that Status column header exists
    await expect(page.getByText("Status")).toBeVisible();

    // Check each quiz row has correct status display
    // Pending Quiz
    const pendingRow = page.locator("tr", {
      has: page.getByText("Pending Quiz"),
    });
    await expect(
      pendingRow.locator('[title="Waiting to generate questions"]')
    ).toBeVisible();
    await expect(
      pendingRow
        .locator("td")
        .filter({
          has: page.locator('[title="Waiting to generate questions"]'),
        })
        .getByText("Pending")
    ).toBeVisible();

    // Processing Quiz
    const processingRow = page.locator("tr", {
      has: page.getByText("Processing Quiz"),
    });
    await expect(
      processingRow.locator('[title="Generating questions..."]')
    ).toBeVisible();
    await expect(
      processingRow
        .locator("td")
        .filter({ has: page.locator('[title="Generating questions..."]') })
        .getByText("Processing")
    ).toBeVisible();

    // Completed Quiz
    const completedRow = page.locator("tr", {
      has: page.getByText("Completed Quiz"),
    });
    await expect(
      completedRow.locator('[title="Questions generated successfully"]')
    ).toBeVisible();
    await expect(
      completedRow
        .locator("td")
        .filter({
          has: page.locator('[title="Questions generated successfully"]'),
        })
        .getByText("Complete")
    ).toBeVisible();

    // Failed Quiz
    const failedRow = page.locator("tr", {
      has: page.getByText("Failed Quiz"),
    });
    await expect(
      failedRow.locator('[title="Generation failed"]')
    ).toBeVisible();
    await expect(
      failedRow
        .locator("td")
        .filter({ has: page.locator('[title="Generation failed"]') })
        .getByText("Failed")
    ).toBeVisible();
  });

  test("should display correct status lights colors", async ({ page }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Green Status Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        content_extraction_status: "completed",
        llm_generation_status: "completed",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174002",
        title: "Orange Status Quiz",
        canvas_course_id: 12346,
        canvas_course_name: "Test Course",
        selected_modules: '{"173468": "Module 2"}',
        question_count: 25,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        content_extraction_status: "processing",
        llm_generation_status: "pending",
        created_at: "2024-01-14T08:15:00Z",
        updated_at: "2024-01-15T12:30:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174003",
        title: "Red Status Quiz",
        canvas_course_id: 12347,
        canvas_course_name: "Test Course",
        selected_modules: '{"173469": "Module 3"}',
        question_count: 75,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        content_extraction_status: "failed",
        llm_generation_status: "pending",
        created_at: "2024-01-13T16:45:00Z",
        updated_at: "2024-01-14T09:20:00Z",
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      });
    });

    await page.reload();

    // Green status (completed)
    const greenLight = page.locator(
      '[title="Questions generated successfully"]'
    );
    await expect(greenLight).toBeVisible();
    await expect(greenLight).toHaveCSS("background-color", "rgb(34, 197, 94)"); // green.500

    // Orange status (processing)
    const orangeLight = page.locator('[title="Generating questions..."]');
    await expect(orangeLight).toBeVisible();
    await expect(orangeLight).toHaveCSS(
      "background-color",
      "rgb(249, 115, 22)"
    ); // orange.500

    // Red status (failed)
    const redLight = page.locator('[title="Generation failed"]');
    await expect(redLight).toBeVisible();
    await expect(redLight).toHaveCSS("background-color", "rgb(239, 68, 68)"); // red.500
  });

  test("should handle missing status fields gracefully", async ({ page }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Legacy Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        // Missing content_extraction_status and llm_generation_status
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
      {
        id: "123e4567-e89b-12d3-a456-426614174002",
        title: "Null Status Quiz",
        canvas_course_id: 12346,
        canvas_course_name: "Test Course",
        selected_modules: '{"173468": "Module 2"}',
        question_count: 25,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        content_extraction_status: null,
        llm_generation_status: null,
        created_at: "2024-01-14T08:15:00Z",
        updated_at: "2024-01-15T12:30:00Z",
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      });
    });

    await page.reload();

    // Both should default to pending status (orange light)
    const orangeLights = page.locator(
      '[title="Waiting to generate questions"]'
    );
    await expect(orangeLights).toHaveCount(2);

    // Check status text specifically in the Status column (5th column, index 4)
    const statusCells = page.locator("tbody tr td:nth-child(5)");
    await expect(statusCells.filter({ hasText: "Pending" })).toHaveCount(2);
  });

  test("should display correct status text for different combinations", async ({
    page,
  }) => {
    const testCases = [
      {
        extraction: "pending",
        generation: "pending",
        expectedText: "Pending",
      },
      {
        extraction: "processing",
        generation: "pending",
        expectedText: "Processing",
      },
      {
        extraction: "completed",
        generation: "pending",
        expectedText: "Pending",
      },
      {
        extraction: "completed",
        generation: "processing",
        expectedText: "Processing",
      },
      {
        extraction: "completed",
        generation: "completed",
        expectedText: "Complete",
      },
      {
        extraction: "failed",
        generation: "pending",
        expectedText: "Failed",
      },
      {
        extraction: "completed",
        generation: "failed",
        expectedText: "Failed",
      },
    ];

    for (let i = 0; i < testCases.length; i++) {
      const testCase = testCases[i];
      const mockQuiz = {
        id: `123e4567-e89b-12d3-a456-42661417400${i}`,
        title: `Status Test ${testCase.extraction}-${testCase.generation}`,
        canvas_course_id: 12345 + i,
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
      };

      await page.route("**/api/v1/quiz/", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([mockQuiz]),
        });
      });

      await page.reload();

      // Check the status text in the status column
      const row = page.locator("tr", { has: page.getByText(mockQuiz.title) });
      // Look specifically in the Status column (5th column, index 4)
      await expect(
        row.locator("td").nth(4).getByText(testCase.expectedText)
      ).toBeVisible();
    }
  });

  test("should maintain status column alignment and styling", async ({
    page,
  }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Alignment Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: '{"173467": "Module 1"}',
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.3,
        content_extraction_status: "completed",
        llm_generation_status: "completed",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      });
    });

    await page.reload();

    // Check that status light and text are properly aligned
    const statusCell = page
      .locator("tr", { has: page.getByText("Alignment Test Quiz") })
      .locator("td")
      .filter({
        has: page.locator('[title="Questions generated successfully"]'),
      });

    await expect(statusCell).toBeVisible();

    // Verify both status light and text are in the same cell
    await expect(
      statusCell.locator('[title="Questions generated successfully"]')
    ).toBeVisible();
    await expect(statusCell.getByText("Complete")).toBeVisible();

    // Check horizontal alignment - status light and text should be in a horizontal container
    const statusContainer = statusCell.locator("div, span").first();
    await expect(statusContainer).toBeVisible();
  });

  test("should display status column in correct table position", async ({
    page,
  }) => {
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174001",
        title: "Column Position Quiz",
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
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      });
    });

    await page.reload();

    // Check table headers order
    const headers = page.locator("th");
    await expect(headers.nth(0)).toContainText("Quiz Title");
    await expect(headers.nth(1)).toContainText("Course");
    await expect(headers.nth(2)).toContainText("Questions");
    await expect(headers.nth(3)).toContainText("LLM Model");
    await expect(headers.nth(4)).toContainText("Status");
    await expect(headers.nth(5)).toContainText("Created");
    await expect(headers.nth(6)).toContainText("Actions");

    // Check that Status column is the 5th column (index 4)
    const statusHeader = headers.nth(4);
    await expect(statusHeader).toContainText("Status");
  });

  test("should handle status updates in quiz list", async ({ page }) => {
    let callCount = 0;
    const responses = [
      // First call: quiz with processing status
      [
        {
          id: "123e4567-e89b-12d3-a456-426614174001",
          title: "Status Update Quiz",
          canvas_course_id: 12345,
          canvas_course_name: "Test Course",
          selected_modules: '{"173467": "Module 1"}',
          question_count: 50,
          llm_model: "gpt-4o",
          llm_temperature: 0.3,
          content_extraction_status: "processing",
          llm_generation_status: "pending",
          created_at: "2024-01-15T10:30:00Z",
          updated_at: "2024-01-16T14:20:00Z",
          owner_id: "user123",
        },
      ],
      // Second call: quiz with completed status
      [
        {
          id: "123e4567-e89b-12d3-a456-426614174001",
          title: "Status Update Quiz",
          canvas_course_id: 12345,
          canvas_course_name: "Test Course",
          selected_modules: '{"173467": "Module 1"}',
          question_count: 50,
          llm_model: "gpt-4o",
          llm_temperature: 0.3,
          content_extraction_status: "completed",
          llm_generation_status: "completed",
          created_at: "2024-01-15T10:30:00Z",
          updated_at: "2024-01-16T14:20:00Z",
          owner_id: "user123",
        },
      ],
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      const response = responses[Math.min(callCount, responses.length - 1)];
      callCount++;

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(response),
      });
    });

    await page.reload();
    await page.waitForLoadState("networkidle");

    // Should now show completed status
    await expect(page.getByText("Complete")).toBeVisible();
    await expect(
      page.locator('[title="Questions generated successfully"]')
    ).toBeVisible();
  });
});
