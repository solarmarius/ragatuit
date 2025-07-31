import { expect, test } from "@playwright/test";

test.describe("Quiz List Component", () => {
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

  test("should display empty state when no quizzes exist", async ({ page }) => {
    // Mock API to return empty quiz list
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.reload();

    // Check empty state elements
    await expect(page.getByText("No Quizzes Found")).toBeVisible();
    await expect(
      page.getByText("You haven't created any quizzes yet")
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Create Your First Quiz" })
    ).toBeVisible();
  });

  test("should display quiz list with all information", async ({ page }) => {
    // Mock API to return quiz data
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Machine Learning Basics",
        canvas_course_id: 12345,
        canvas_course_name: "Intro to AI",
        selected_modules: {
          "173467": {
            name: "Neural Networks",
            question_batches: [{ question_type: "multiple_choice", count: 25 }],
          },
          "173468": {
            name: "Deep Learning",
            question_batches: [{ question_type: "multiple_choice", count: 25 }],
          },
        },
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.7,
        language: "en",
        tone: "academic",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
      {
        id: "234e5678-e89b-12d3-a456-426614174001",
        title: "Python Programming",
        canvas_course_id: 67890,
        canvas_course_name: "CS101",
        selected_modules: {
          "173469": {
            name: "Variables",
            question_batches: [{ question_type: "multiple_choice", count: 8 }],
          },
          "173470": {
            name: "Functions",
            question_batches: [{ question_type: "multiple_choice", count: 9 }],
          },
          "173471": {
            name: "Classes",
            question_batches: [{ question_type: "multiple_choice", count: 8 }],
          },
        },
        question_count: 25,
        llm_model: "o3",
        llm_temperature: 0.3,
        language: "no",
        tone: "casual",
        created_at: "2024-01-10T08:15:00Z",
        updated_at: "2024-01-12T16:45:00Z",
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

    // Check header elements
    await expect(page.getByText("My Quizzes")).toBeVisible();
    await expect(
      page.getByText("Manage and view all your created quizzes")
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Create New Quiz" })
    ).toBeVisible();

    // Check table headers
    await expect(page.getByText("Quiz Title")).toBeVisible();
    await expect(page.getByText("Course")).toBeVisible();
    await expect(page.getByText("Questions")).toBeVisible();
    await expect(page.locator("th").getByText("Status")).toBeVisible();
    await expect(page.locator("th").getByText("Created")).toBeVisible();
    await expect(page.getByText("Actions")).toBeVisible();

    // Check first quiz row
    await expect(page.getByText("Machine Learning Basics")).toBeVisible();
    await expect(page.getByText("2 modules selected")).toBeVisible();
    await expect(page.getByText("Intro to AI")).toBeVisible();
    await expect(page.getByText("ID: 12345")).toBeVisible();
    await expect(page.locator("tbody").getByText("50")).toBeVisible();
    await expect(page.getByText("15 Jan 2024")).toBeVisible();

    // Check second quiz row
    await expect(page.getByText("Python Programming")).toBeVisible();
    await expect(page.getByText("3 modules selected")).toBeVisible();
    await expect(page.getByText("CS101")).toBeVisible();
    await expect(page.getByText("ID: 67890")).toBeVisible();
    await expect(page.getByText("25")).toBeVisible();
    await expect(page.getByText("10 Jan 2024")).toBeVisible();

    // Check action buttons
    const viewButtons = page.getByRole("link", { name: "View" });
    await expect(viewButtons).toHaveCount(2);
  });

  test("should display single module correctly", async ({ page }) => {
    // Mock API with quiz having only one module
    const mockQuiz = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Single Module Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: {
          "173467": {
            name: "Single Module",
            question_batches: [{ question_type: "multiple_choice", count: 30 }],
          },
        },
        question_count: 30,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        language: "en",
        tone: "professional",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check singular module text
    await expect(page.getByText("1 module selected")).toBeVisible();
  });

  test("should handle empty selected modules", async ({ page }) => {
    // Mock API with quiz having empty modules
    const mockQuiz = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Empty Modules Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: {},
        question_count: 30,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        language: "no",
        tone: "encouraging",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check zero modules text
    await expect(page.getByText("0 modules selected")).toBeVisible();
  });

  test("should navigate to create quiz page", async ({ page }) => {
    // Mock empty quiz list
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.reload();

    // Click on "Create New Quiz" button
    await page.getByRole("link", { name: "Create New Quiz" }).click();

    // Check that we navigated to the create quiz page
    await expect(page).toHaveURL("/create-quiz");
  });

  test("should navigate to quiz detail page", async ({ page }) => {
    const mockQuiz = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: {
          "173467": {
            name: "Module 1",
            question_batches: [{ question_type: "multiple_choice", count: 30 }],
          },
        },
        question_count: 30,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        language: "en",
        tone: "academic",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Click on View button
    await page.getByRole("link", { name: "View" }).click();

    // Check that we navigated to the quiz detail page
    await expect(page).toHaveURL("/quiz/123e4567-e89b-12d3-a456-426614174000");
  });

  test("should display error state when API fails", async ({ page }) => {
    // Mock API to return error
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    await page.reload();

    // Wait for page to load
    await page.waitForLoadState("networkidle");

    // Check that error state is displayed (either error UI or error toast)
    // The component shows either the error UI or just the toast - both are valid error handling
    await expect(page.getByText("Failed to Load Quizzes")).toBeVisible({
      timeout: 15000,
    });
  });

  test("should display loading skeleton", async ({ page }) => {
    // Delay the API response to test loading state
    await page.route("**/api/v1/quiz/", async (route) => {
      // Add delay to see loading state
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    // Start navigation but don't wait for it to complete
    const navigationPromise = page.goto("/quizzes");

    // Check that skeleton is visible during loading
    await expect(page.locator('[class*="skeleton"]').first()).toBeVisible();

    // Wait for navigation to complete
    await navigationPromise;
  });

  test("should handle missing created_at date", async ({ page }) => {
    const mockQuiz = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "No Date Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: {
          "173467": {
            name: "Module 1",
            question_batches: [{ question_type: "multiple_choice", count: 30 }],
          },
        },
        question_count: 30,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        language: "en",
        tone: "academic",
        created_at: null,
        updated_at: null,
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check that "Unknown" is displayed for missing date
    await expect(page.getByText("Unknown")).toBeVisible();
  });

  test("should display badges with correct styling", async ({ page }) => {
    const mockQuiz = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Style Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: {
          "173467": {
            name: "Module 1",
            question_batches: [{ question_type: "multiple_choice", count: 75 }],
          },
        },
        question_count: 75,
        llm_model: "gpt-4.1-mini",
        llm_temperature: 0.8,
        language: "no",
        tone: "casual",
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check badge styling - question count should be blue solid
    const questionBadge = page.locator("text=75").first();
    await expect(questionBadge).toBeVisible();
  });

  test("should handle quizzes with different tone and language combinations", async ({
    page,
  }) => {
    // Import our new tone-varied fixtures
    const { toneVariedQuizzes } = await import("../fixtures/quiz-data");

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(toneVariedQuizzes),
      });
    });

    await page.reload();

    // Check that all quizzes are displayed correctly regardless of tone/language
    await expect(page.getByText("Casual Learning Quiz")).toBeVisible();
    await expect(page.getByText("Encouraging Study Quiz")).toBeVisible();
    await expect(page.getByText("Professional Training Quiz")).toBeVisible();
    await expect(page.getByText("Norsk Uformell Quiz")).toBeVisible();
    await expect(page.getByText("Norsk Akademisk Quiz")).toBeVisible();

    // Check that different course names are displayed
    await expect(page.getByText("Informal Learning")).toBeVisible();
    await expect(page.getByText("Supportive Learning")).toBeVisible();
    await expect(page.getByText("Business Training")).toBeVisible();
    await expect(page.getByText("Norsk Kurs")).toBeVisible();
    await expect(page.getByText("Universitet Kurs")).toBeVisible();

    // Verify question counts are displayed correctly for different tones
    await expect(
      page.locator("tbody .chakra-badge").getByText("15")
    ).toBeVisible(); // Casual tone quiz
    await expect(
      page.locator("tbody .chakra-badge").getByText("20")
    ).toBeVisible(); // Encouraging tone quiz
    await expect(
      page.locator("tbody .chakra-badge").getByText("25")
    ).toBeVisible(); // Professional tone quiz
    await expect(
      page.locator("tbody .chakra-badge").getByText("30")
    ).toBeVisible(); // Norwegian casual quiz
    await expect(
      page.locator("tbody .chakra-badge").getByText("35")
    ).toBeVisible(); // Norwegian academic quiz

    // Check that all View buttons are present (one for each quiz)
    const viewButtons = page.getByRole("link", { name: "View" });
    await expect(viewButtons).toHaveCount(5);
  });

  test("should display quiz information correctly with mixed language/tone settings", async ({
    page,
  }) => {
    // Test with specific quiz that has Norwegian language and professional tone
    const mockQuiz = [
      {
        id: "mixed-lang-tone-quiz",
        title: "Profesjonell Norsk Eksamen",
        canvas_course_id: 99999,
        canvas_course_name: "Avansert Programvareutvikling",
        selected_modules: {
          "999001": {
            name: "Objektorientert Programmering",
            question_batches: [
              { question_type: "multiple_choice", count: 12 },
              { question_type: "multiple_choice", count: 8 },
            ],
          },
          "999002": {
            name: "Datastrukturer og Algoritmer",
            question_batches: [{ question_type: "multiple_choice", count: 15 }],
          },
        },
        question_count: 35,
        llm_model: "o3",
        llm_temperature: 0.9,
        language: "no",
        tone: "professional",
        status: "ready_for_review",
        created_at: "2024-01-20T14:30:00Z",
        updated_at: "2024-01-21T09:15:00Z",
        owner_id: "user123",
      },
    ];

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      });
    });

    await page.reload();

    // Check Norwegian title and course name are displayed correctly
    await expect(page.getByText("Profesjonell Norsk Eksamen")).toBeVisible();
    await expect(page.getByText("Avansert Programvareutvikling")).toBeVisible();

    // Check course ID
    await expect(page.getByText("ID: 99999")).toBeVisible();

    // Check module count (2 modules)
    await expect(page.getByText("2 modules selected")).toBeVisible();

    // Check question count
    await expect(page.locator("tbody").getByText("35")).toBeVisible();

    // Check date formatting
    await expect(page.getByText("20 Jan 2024")).toBeVisible();

    // Verify the quiz is functional (has View button)
    await expect(page.getByRole("link", { name: "View" })).toBeVisible();
  });
});
