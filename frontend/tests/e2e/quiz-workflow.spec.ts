import { expect, test } from "@playwright/test"

test.describe("Quiz Workflow End-to-End", () => {
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

    // Mock Canvas courses API
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { id: 12345, name: "Machine Learning Fundamentals" },
          { id: 67890, name: "Advanced Data Structures" },
        ]),
      })
    })

    // Mock Canvas modules API
    await page.route(
      "**/api/v1/canvas/courses/12345/modules",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 173467, name: "Introduction to Neural Networks" },
            { id: 173468, name: "Deep Learning Concepts" },
            { id: 173469, name: "Convolutional Neural Networks" },
          ]),
        })
      },
    )

    await page.route(
      "**/api/v1/canvas/courses/67890/modules",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 173470, name: "Binary Trees" },
            { id: 173471, name: "Graph Algorithms" },
          ]),
        })
      },
    )
  })

  test("complete quiz creation and viewing workflow", async ({ page }) => {
    // Mock empty quiz list initially
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    // Start at quiz list page
    await page.goto("/quizzes")

    // Verify empty state
    await expect(page.getByText("No Quizzes Found")).toBeVisible()

    // Click create quiz button
    await page.getByRole("link", { name: "Create Your First Quiz" }).click()

    // Verify we're on create quiz page
    await expect(page).toHaveURL("/create-quiz")
    await expect(page.getByText("Create New Quiz")).toBeVisible()

    // Step 1: Select course
    await expect(page.getByText("Select Course")).toBeVisible()
    await page.getByText("Machine Learning Fundamentals").click()

    // Wait for course selection to be processed - quiz title should appear
    await page.waitForTimeout(500)

    // Fill in quiz title (appears after course selection)
    await page.getByLabel("Quiz Title").fill("My ML Quiz")

    // Set up modules API mock specifically for the selected course before navigating
    await page.route(
      "**/api/v1/canvas/courses/12345/modules",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 173467, name: "Introduction to Neural Networks" },
            { id: 173468, name: "Deep Learning Concepts" },
            { id: 173469, name: "Convolutional Neural Networks" },
          ]),
        })
      },
    )

    // next to next step (modules)
    await page.getByRole("button", { name: "next" }).click()

    // Step 2: Select modules - wait for modules to load and be visible
    await page.waitForLoadState("networkidle")
    await expect(
      page.getByText("Introduction to Neural Networks"),
    ).toBeVisible()
    await page.getByText("Introduction to Neural Networks").click()
    await page.getByText("Deep Learning Concepts").click()

    // Wait for module selection to be processed and next button to be enabled
    await page.waitForTimeout(500)

    // next to next step (quiz settings)
    await page.getByRole("button", { name: "next" }).click()

    // Step 3: Quiz settings - wait for page to load
    await page.waitForLoadState("networkidle")
    await expect(page.getByText("Quiz Settings")).toBeVisible()

    // Adjust question count - use placeholder text to find the input
    const questionCountInput = page.getByPlaceholder(
      "Enter number of questions",
    )
    await questionCountInput.fill("50")

    // Click on "Advanced settings" tab to access LLM model and temperature
    await page.getByText("Advanced Settings").click()

    // Select different model - use exact display text from dropdown
    await page.getByRole("combobox").click()
    await page.getByRole("option", { name: "GPT-4o" }).click()

    // Adjust temperature
    const slider = page.locator('[data-part="thumb"]').first() // or be more specific if multiple sliders
    await slider.focus()
    await page.keyboard.press("Home") // Go to minimum (0)
    // Calculate how many steps to reach 0.7 (step=0.1, so 7 steps from 0)
    for (let i = 0; i < 7; i++) {
      await page.keyboard.press("ArrowRight")
    }

    // Mock quiz creation API
    const newQuizId = "123e4567-e89b-12d3-a456-426614174000"
    await page.route("**/api/v1/quiz/", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: newQuizId,
            title: "My ML Quiz",
            canvas_course_id: 12345,
            canvas_course_name: "Machine Learning Fundamentals",
            selected_modules: {
              "173467": "Introduction to Neural Networks",
              "173468": "Deep Learning Concepts",
            },
            question_count: 50,
            llm_model: "gpt-4o",
            llm_temperature: 0.7,
            created_at: "2024-01-15T10:30:00Z",
            updated_at: "2024-01-15T10:30:00Z",
            owner_id: "user123",
          }),
        })
      }
    })

    // Submit form to create quiz
    await page.getByRole("button", { name: "Create Quiz" }).click()

    // Should redirect to quiz detail page
    await expect(page).toHaveURL(`/quiz/${newQuizId}`)

    // Mock quiz detail API
    await page.route(`**/api/v1/quiz/${newQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: newQuizId,
          title: "My ML Quiz",
          canvas_course_id: 12345,
          canvas_course_name: "Machine Learning Fundamentals",
          selected_modules: {
            "173467": "Introduction to Neural Networks",
            "173468": "Deep Learning Concepts",
          },
          question_count: 50,
          llm_model: "gpt-4o",
          llm_temperature: 0.7,
          created_at: "2024-01-15T10:30:00Z",
          updated_at: "2024-01-15T10:30:00Z",
          owner_id: "user123",
        }),
      })
    })

    // Verify quiz details are displayed
    await expect(page.getByText("My ML Quiz")).toBeVisible()
    await expect(page.getByText("Machine Learning Fundamentals")).toBeVisible()
    await expect(
      page.getByText("Introduction to Neural Networks"),
    ).toBeVisible()
    await expect(page.getByText("Deep Learning Concepts")).toBeVisible()
    await expect(page.locator("span").getByText("50").first()).toBeVisible()
    await expect(page.getByText("gpt-4o")).toBeVisible()
    await expect(page.getByText("0.7")).toBeVisible()
  })

  test("navigate from quiz list to quiz detail", async ({ page }) => {
    const quizId = "123e4567-e89b-12d3-a456-426614174000"

    // Mock quiz list with one quiz
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: quizId,
            title: "Existing Quiz",
            canvas_course_id: 12345,
            canvas_course_name: "Test Course",
            selected_modules: { "173467": "Module 1", "173468": "Module 2" },
            question_count: 75,
            llm_model: "o3",
            llm_temperature: 0.3,
            created_at: "2024-01-15T10:30:00Z",
            updated_at: "2024-01-16T14:20:00Z",
            owner_id: "user123",
          },
        ]),
      })
    })

    // Mock quiz detail API
    await page.route(`**/api/v1/quiz/${quizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: quizId,
          title: "Existing Quiz",
          canvas_course_id: 12345,
          canvas_course_name: "Test Course",
          selected_modules: {
            "173467": "Module 1",
            "173468": "Module 2",
          },
          question_count: 75,
          llm_model: "o3",
          llm_temperature: 0.3,
          created_at: "2024-01-15T10:30:00Z",
          updated_at: "2024-01-16T14:20:00Z",
          owner_id: "user123",
        }),
      })
    })

    // Start at quiz list
    await page.goto("/quizzes")

    // Verify quiz is listed
    await expect(page.getByText("Existing Quiz")).toBeVisible()
    await expect(page.getByText("2 modules selected")).toBeVisible()

    // Click view button
    await page.getByRole("link", { name: "View" }).click()

    // Verify navigation to detail page
    await expect(page).toHaveURL(`/quiz/${quizId}`)

    // Verify quiz details
    await expect(page.getByText("Existing Quiz")).toBeVisible()
    await expect(page.getByText("Module 1")).toBeVisible()
    await expect(page.getByText("Module 2")).toBeVisible()
    await expect(page.locator("span").getByText("75").first()).toBeVisible()
  })

  test("quiz list pagination and sorting", async ({ page }) => {
    // Mock large list of quizzes
    const mockQuizzes = Array.from({ length: 25 }, (_, i) => ({
      id: `quiz-${i}`,
      title: `Quiz ${i + 1}`,
      canvas_course_id: 12345 + i,
      canvas_course_name: `Course ${i + 1}`,
      selected_modules: `{"${173467 + i}": "Module ${i + 1}"}`,
      question_count: 50 + i,
      llm_model: i % 2 === 0 ? "gpt-4o" : "o3",
      llm_temperature: 0.3 + i * 0.1,
      created_at: new Date(2024, 0, i + 1, 10, 30).toISOString(),
      updated_at: new Date(2024, 0, i + 2, 14, 20).toISOString(),
      owner_id: "user123",
    }))

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQuizzes),
      })
    })

    await page.goto("/quizzes")

    // Verify multiple quizzes are displayed
    await expect(page.getByText("Quiz 1", { exact: true })).toBeVisible()
    await expect(page.getByText("Quiz 25")).toBeVisible()
  })

  test("responsive behavior on mobile viewport", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    const quizId = "123e4567-e89b-12d3-a456-426614174000"

    // Mock quiz list
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: quizId,
            title: "Mobile Test Quiz",
            canvas_course_id: 12345,
            canvas_course_name: "Mobile Test Course",
            selected_modules: { "173467": "Mobile Module" },
            question_count: 50,
            llm_model: "gpt-4o",
            llm_temperature: 0.5,
            created_at: "2024-01-15T10:30:00Z",
            updated_at: "2024-01-16T14:20:00Z",
            owner_id: "user123",
          },
        ]),
      })
    })

    await page.goto("/quizzes")

    // Verify content is still visible on mobile
    await expect(page.getByText("My Quizzes")).toBeVisible()
    await expect(page.getByText("Mobile Test Quiz")).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Create New Quiz" }),
    ).toBeVisible()

    // Test navigation still works
    await page.getByRole("link", { name: "View" }).click()
    await expect(page).toHaveURL(`/quiz/${quizId}`)
  })

  test("keyboard navigation and accessibility", async ({ page }) => {
    const quizId = "123e4567-e89b-12d3-a456-426614174000"

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: quizId,
            title: "Keyboard Test Quiz",
            canvas_course_id: 12345,
            canvas_course_name: "Test Course",
            selected_modules: { "173467": "Module 1" },
            question_count: 50,
            llm_model: "gpt-4o",
            llm_temperature: 0.5,
            created_at: "2024-01-15T10:30:00Z",
            updated_at: "2024-01-16T14:20:00Z",
            owner_id: "user123",
          },
        ]),
      })
    })

    await page.goto("/quizzes")

    // Test keyboard navigation
    await page.keyboard.press("Tab") // Should focus on first interactive element
    await page.keyboard.press("Tab") // Navigate to next element

    // Test that Enter key works on focused elements
    const createButton = page.getByRole("link", { name: "Create New Quiz" })
    await createButton.focus()
    await page.keyboard.press("Enter")

    // Should navigate to create quiz page
    await expect(page).toHaveURL("/create-quiz")
  })
})
