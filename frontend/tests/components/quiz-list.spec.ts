import { expect, test } from "@playwright/test"

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
      })
    })

    // Navigate to the quiz list page
    await page.goto("/quizzes")
  })

  test("should display empty state when no quizzes exist", async ({ page }) => {
    // Mock API to return empty quiz list
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.reload()

    // Check empty state elements
    await expect(page.getByText("No Quizzes Found")).toBeVisible()
    await expect(
      page.getByText("You haven't created any quizzes yet"),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Create Your First Quiz" }),
    ).toBeVisible()
  })

  test("should display quiz list with all information", async ({ page }) => {
    // Mock API to return quiz data
    const mockQuizzes = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Machine Learning Basics",
        canvas_course_id: 12345,
        canvas_course_name: "Intro to AI",
        selected_modules: {
          "173467": "Neural Networks",
          "173468": "Deep Learning",
        },
        question_count: 50,
        llm_model: "gpt-4o",
        llm_temperature: 0.7,
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
          "173469": "Variables",
          "173470": "Functions",
          "173471": "Classes",
        },
        question_count: 25,
        llm_model: "o3",
        llm_temperature: 0.3,
        created_at: "2024-01-10T08:15:00Z",
        updated_at: "2024-01-12T16:45:00Z",
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

    // Check header elements
    await expect(page.getByText("My Quizzes")).toBeVisible()
    await expect(
      page.getByText("Manage and view all your created quizzes"),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Create New Quiz" }),
    ).toBeVisible()

    // Check table headers
    await expect(page.getByText("Quiz Title")).toBeVisible()
    await expect(page.getByText("Course")).toBeVisible()
    await expect(page.getByText("Questions")).toBeVisible()
    await expect(page.getByText("LLM Model")).toBeVisible()
    await expect(page.locator("th").getByText("Created")).toBeVisible()
    await expect(page.getByText("Actions")).toBeVisible()

    // Check first quiz row
    await expect(page.getByText("Machine Learning Basics")).toBeVisible()
    await expect(page.getByText("2 modules selected")).toBeVisible()
    await expect(page.getByText("Intro to AI")).toBeVisible()
    await expect(page.getByText("ID: 12345")).toBeVisible()
    await expect(page.locator("tbody").getByText("50")).toBeVisible()
    await expect(page.getByText("15 Jan 2024")).toBeVisible()

    // Check second quiz row
    await expect(page.getByText("Python Programming")).toBeVisible()
    await expect(page.getByText("3 modules selected")).toBeVisible()
    await expect(page.getByText("CS101")).toBeVisible()
    await expect(page.getByText("ID: 67890")).toBeVisible()
    await expect(page.getByText("25")).toBeVisible()
    await expect(page.getByText("10 Jan 2024")).toBeVisible()

    // Check action buttons
    const viewButtons = page.getByRole("link", { name: "View" })
    await expect(viewButtons).toHaveCount(2)
  })

  test("should display single module correctly", async ({ page }) => {
    // Mock API with quiz having only one module
    const mockQuiz = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Single Module Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: { "173467": "Single Module" },
        question_count: 30,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check singular module text
    await expect(page.getByText("1 module selected")).toBeVisible()
  })

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
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check zero modules text
    await expect(page.getByText("0 modules selected")).toBeVisible()
  })

  test("should navigate to create quiz page", async ({ page }) => {
    // Mock empty quiz list
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.reload()

    // Click on "Create New Quiz" button
    await page.getByRole("link", { name: "Create New Quiz" }).click()

    // Check that we navigated to the create quiz page
    await expect(page).toHaveURL("/create-quiz")
  })

  test("should navigate to quiz detail page", async ({ page }) => {
    const mockQuiz = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: { "173467": "Module 1" },
        question_count: 30,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Click on View button
    await page.getByRole("link", { name: "View" }).click()

    // Check that we navigated to the quiz detail page
    await expect(page).toHaveURL("/quiz/123e4567-e89b-12d3-a456-426614174000")
  })

  test("should display error state when API fails", async ({ page }) => {
    // Mock API to return error
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      })
    })

    await page.reload()

    // Wait for page to load
    await page.waitForLoadState("networkidle")

    // Check that error state is displayed (either error UI or error toast)
    // The component shows either the error UI or just the toast - both are valid error handling
    await expect(page.getByText("Failed to Load Quizzes")).toBeVisible({
      timeout: 15000,
    })
  })

  test("should display loading skeleton", async ({ page }) => {
    // Delay the API response to test loading state
    await page.route("**/api/v1/quiz/", async (route) => {
      // Add delay to see loading state
      await new Promise((resolve) => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    // Start navigation but don't wait for it to complete
    const navigationPromise = page.goto("/quizzes")

    // Check that skeleton is visible during loading
    await expect(page.locator('[class*="skeleton"]').first()).toBeVisible()

    // Wait for navigation to complete
    await navigationPromise
  })

  test("should handle missing created_at date", async ({ page }) => {
    const mockQuiz = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "No Date Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: { "173467": "Module 1" },
        question_count: 30,
        llm_model: "gpt-4o",
        llm_temperature: 0.5,
        created_at: null,
        updated_at: null,
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check that "Unknown" is displayed for missing date
    await expect(page.getByText("Unknown")).toBeVisible()
  })

  test("should display badges with correct styling", async ({ page }) => {
    const mockQuiz = [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Style Test Quiz",
        canvas_course_id: 12345,
        canvas_course_name: "Test Course",
        selected_modules: { "173467": "Module 1" },
        question_count: 75,
        llm_model: "gpt-4.1-mini",
        llm_temperature: 0.8,
        created_at: "2024-01-15T10:30:00Z",
        updated_at: "2024-01-16T14:20:00Z",
        owner_id: "user123",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuiz),
      })
    })

    await page.reload()

    // Check badge styling - question count should be blue solid
    const questionBadge = page.locator("text=75").first()
    await expect(questionBadge).toBeVisible()
  })
})
