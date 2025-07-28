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

    // Wait for module selection to be processed and next button to be enabled
    await page.waitForTimeout(500)

    // next to next step (Questions per Module)
    await page.getByRole("button", { name: "next" }).click()

    // Step 3: Configure Question Types per Module - wait for page to load
    await page.waitForLoadState("networkidle")
    await expect(
      page.getByRole("heading", {
        name: "Configure Question Types per Module",
      }),
    ).toBeVisible()

    // Add question batch for first module
    await page.getByText("Add Batch").first().click()

    // Verify default question type is selected and adjust count
    const questionInputs = page.getByRole("spinbutton")
    await expect(questionInputs.first()).toHaveValue("10")
    await questionInputs.first().fill("15")

    // next to next step (quiz settings)
    await page.getByRole("button", { name: "next" }).click()

    // Step 4: Quiz configuration - wait for page to load
    await page.waitForLoadState("networkidle")
    await expect(page.getByText("Quiz Configuration")).toBeVisible()

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
              "173467": {
                name: "Introduction to Neural Networks",
                question_batches: [
                  { question_type: "multiple_choice", count: 15 },
                ],
              },
            },
            question_count: 15,
            llm_model: "o3",
            llm_temperature: 1.0,
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
            "173467": {
              name: "Introduction to Neural Networks",
              question_batches: [
                { question_type: "multiple_choice", count: 15 },
              ],
            },
          },
          question_count: 15,
          llm_model: "o3",
          llm_temperature: 1.0,
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
      page.getByText("Introduction to Neural Networks").first(),
    ).toBeVisible()
    await expect(page.locator("span").getByText("15").first()).toBeVisible()
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
            selected_modules: {
              "173467": {
                name: "Module 1",
                question_batches: [
                  { question_type: "multiple_choice", count: 25 },
                ],
              },
              "173468": {
                name: "Module 2",
                question_batches: [
                  { question_type: "multiple_choice", count: 25 },
                ],
              },
            },
            question_count: 50,
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
            "173467": {
              name: "Module 1",
              question_batches: [
                { question_type: "multiple_choice", count: 25 },
              ],
            },
            "173468": {
              name: "Module 2",
              question_batches: [
                { question_type: "multiple_choice", count: 25 },
              ],
            },
          },
          question_count: 50,
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
    await expect(page.getByText("Module 1").first()).toBeVisible()
    await expect(page.getByText("Module 2").first()).toBeVisible()
    await expect(page.locator("span").getByText("50").first()).toBeVisible()
  })

  test("quiz list pagination and sorting", async ({ page }) => {
    // Mock large list of quizzes
    const mockQuizzes = Array.from({ length: 25 }, (_, i) => ({
      id: `quiz-${i}`,
      title: `Quiz ${i + 1}`,
      canvas_course_id: 12345 + i,
      canvas_course_name: `Course ${i + 1}`,
      selected_modules: {
        [`${173467 + i}`]: {
          name: `Module ${i + 1}`,
          question_batches: [{ question_type: "multiple_choice", count: 25 }],
        },
      },
      question_count: 25,
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
    await expect(page.getByText("Quiz 25", { exact: true })).toBeVisible()
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
            selected_modules: {
              "173467": {
                name: "Mobile Module",
                question_batches: [
                  { question_type: "multiple_choice", count: 25 },
                ],
              },
            },
            question_count: 25,
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
            selected_modules: {
              "173467": {
                name: "Module 1",
                question_batches: [
                  { question_type: "multiple_choice", count: 25 },
                ],
              },
            },
            question_count: 25,
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

  // Norwegian Language Feature Tests for Quiz Workflow

  test("complete quiz creation with Norwegian language selection", async ({
    page,
  }) => {
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

    // Click create quiz button
    await page.getByRole("link", { name: "Create Your First Quiz" }).click()

    // Verify we're on create quiz page
    await expect(page).toHaveURL("/create-quiz")

    // Step 1: Select course
    await page.getByText("Machine Learning Fundamentals").click()
    await page.getByLabel("Quiz Title").fill("Norsk ML Quiz")

    // Go to step 2 (modules)
    await page.getByRole("button", { name: "next" }).click()

    // Step 2: Select modules
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction to Neural Networks").click()

    // Go to step 3 (questions per module)
    await page.getByRole("button", { name: "next" }).click()

    // Step 3: Configure Question Types per Module
    await page.waitForLoadState("networkidle")
    await expect(
      page.getByRole("heading", {
        name: "Configure Question Types per Module",
      }),
    ).toBeVisible()

    // Add question batch for the single module
    await page.getByText("Add Batch").first().click()
    const questionInputs = page.getByRole("spinbutton")
    await questionInputs.first().fill("15")

    // Go to step 4 (quiz settings)
    await page.getByRole("button", { name: "next" }).click()

    // Step 4: Quiz Configuration with Norwegian language
    await page.waitForLoadState("networkidle")
    await expect(page.getByText("Quiz Configuration")).toBeVisible()

    // Select Norwegian language
    await expect(page.getByText("Quiz Language")).toBeVisible()
    await page.locator('[data-testid="language-card-no"]').click()

    // Verify Norwegian is selected
    const norwegianCard = page.locator('[data-testid="language-card-no"]')
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50 selected state

    // Mock quiz creation API with Norwegian language
    const newQuizId = "123e4567-e89b-12d3-a456-426614174000"
    await page.route("**/api/v1/quiz/", async (route) => {
      if (route.request().method() === "POST") {
        const requestBody = await route.request().postDataJSON()

        // Verify Norwegian language is included in request
        expect(requestBody.language).toBe("no")

        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: newQuizId,
            title: "Norsk ML Quiz",
            canvas_course_id: 12345,
            canvas_course_name: "Machine Learning Fundamentals",
            selected_modules: {
              "173467": {
                name: "Introduction to Neural Networks",
                question_batches: [
                  { question_type: "multiple_choice", count: 15 },
                ],
              },
            },
            question_count: 15,
            language: "no",
            llm_model: "o3",
            llm_temperature: 1.0,
            created_at: "2024-01-15T10:30:00Z",
            updated_at: "2024-01-15T10:30:00Z",
            owner_id: "user123",
          }),
        })
      }
    })

    // Create quiz
    await page.getByRole("button", { name: "Create Quiz" }).click()

    // Should redirect to quiz detail page
    await expect(page).toHaveURL(`/quiz/${newQuizId}`)
  })

  test("quiz configuration shows default English selection", async ({
    page,
  }) => {
    // Mock the necessary APIs
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.goto("/create-quiz")

    // Step 1: Select course
    await page.getByText("Machine Learning Fundamentals").click()
    await page.getByLabel("Quiz Title").fill("English Quiz")
    await page.getByRole("button", { name: "next" }).click()

    // Step 2: Select modules
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction to Neural Networks").click()
    await page.getByRole("button", { name: "next" }).click()

    // Step 3: Questions per Module
    await page.waitForLoadState("networkidle")
    await expect(
      page.getByRole("heading", {
        name: "Configure Question Types per Module",
      }),
    ).toBeVisible()

    // Add question batch to enable next button
    await page.getByText("Add Batch").first().click()

    await page.getByRole("button", { name: "next" }).click()

    // Step 4: Quiz Configuration - verify English is selected by default
    await page.waitForLoadState("networkidle")
    await expect(page.getByText("Quiz Configuration")).toBeVisible()
    await expect(page.getByText("Quiz Language")).toBeVisible()

    // English should be selected by default (blue background)
    const englishCard = page.locator('[data-testid="language-card-en"]')
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50

    // Norwegian should not be selected (white background)
    const norwegianCard = page.locator('[data-testid="language-card-no"]')
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    ) // white
  })

  test("language selection switching between English and Norwegian", async ({
    page,
  }) => {
    // Mock APIs
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.goto("/create-quiz")

    // Navigate to quiz configuration step
    await page.getByText("Machine Learning Fundamentals").click()
    await page.getByLabel("Quiz Title").fill("Language Test Quiz")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction to Neural Networks").click()
    await page.getByRole("button", { name: "next" }).click()

    // Step 3: Questions per Module
    await page.waitForLoadState("networkidle")
    await expect(
      page.getByRole("heading", {
        name: "Configure Question Types per Module",
      }),
    ).toBeVisible()

    // Add question batch to enable next button
    await page.getByText("Add Batch").first().click()

    await page.getByRole("button", { name: "next" }).click()

    // Step 4: Quiz Configuration
    await page.waitForLoadState("networkidle")

    const englishCard = page.locator('[data-testid="language-card-en"]')
    const norwegianCard = page.locator('[data-testid="language-card-no"]')

    // Initially English should be selected
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    ) // white

    // Click Norwegian
    await page.locator('[data-testid="language-card-no"]').click()

    // Norwegian should now be selected, English deselected
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    ) // white

    // Switch back to English
    await page.locator('[data-testid="language-card-en"]').click()

    // English should be selected again
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    ) // white
  })

  test("language selection is preserved when navigating between steps", async ({
    page,
  }) => {
    // Mock APIs
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.goto("/create-quiz")

    // Navigate to quiz configuration and select Norwegian
    await page.getByText("Machine Learning Fundamentals").click()
    await page.getByLabel("Quiz Title").fill("Navigation Test Quiz")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction to Neural Networks").click()
    await page.getByRole("button", { name: "next" }).click()

    // Step 3: Questions per Module
    await page.waitForLoadState("networkidle")
    await expect(
      page.getByRole("heading", {
        name: "Configure Question Types per Module",
      }),
    ).toBeVisible()

    // Add question batch to enable next button
    await page.getByText("Add Batch").first().click()

    await page.getByRole("button", { name: "next" }).click()

    // Step 4: Quiz Configuration
    await page.waitForLoadState("networkidle")

    // Select Norwegian language
    await page.locator('[data-testid="language-card-no"]').click()
    const norwegianCard = page.locator('[data-testid="language-card-no"]')
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50

    // Go back to step 3
    await page.getByRole("button", { name: "Previous" }).click()
    await expect(
      page.getByText("Step 3 of 4: Configure Question Types"),
    ).toBeVisible()

    // Go back to step 4
    await page.getByRole("button", { name: "Next" }).click()
    await page.waitForLoadState("networkidle")

    // Norwegian should still be selected
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
  })

  test("create quiz with Norwegian language and verify API payload", async ({
    page,
  }) => {
    // Mock quiz creation to verify Norwegian language in payload
    let capturedRequestBody: any

    await page.route("**/api/v1/quiz/", async (route) => {
      if (route.request().method() === "POST") {
        capturedRequestBody = await route.request().postDataJSON()

        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: "test-quiz-id",
            title: "Norsk Test Quiz",
            canvas_course_id: 12345,
            canvas_course_name: "Machine Learning Fundamentals",
            selected_modules: {
              "173467": {
                name: "Introduction to Neural Networks",
                question_batches: [
                  { question_type: "multiple_choice", count: 20 },
                ],
              },
            },
            question_count: 20,
            language: "no",
            llm_model: "o3",
            llm_temperature: 1.0,
            created_at: "2024-01-15T10:30:00Z",
            updated_at: "2024-01-15T10:30:00Z",
            owner_id: "user123",
          }),
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      }
    })

    await page.goto("/create-quiz")

    // Complete quiz creation with Norwegian
    await page.getByText("Machine Learning Fundamentals").click()
    await page.getByLabel("Quiz Title").fill("Norsk Test Quiz")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction to Neural Networks").click()
    await page.getByRole("button", { name: "next" }).click()

    // Step 3: Questions per Module - set question count
    await page.waitForLoadState("networkidle")
    await expect(
      page.getByRole("heading", {
        name: "Configure Question Types per Module",
      }),
    ).toBeVisible()

    // Add question batch for the module
    await page.getByText("Add Batch").first().click()
    const questionInputs = page.getByRole("spinbutton")

    // Update the question count (max allowed is 20)
    await questionInputs.first().fill("20")

    // Verify the value was set correctly
    await expect(questionInputs.first()).toHaveValue("20")

    // Wait for the form to update
    await page.waitForTimeout(200)

    await page.getByRole("button", { name: "next" }).click()

    // Step 4: Quiz Configuration - select Norwegian
    await page.waitForLoadState("networkidle")
    await page.locator('[data-testid="language-card-no"]').click()

    // Create quiz
    await page.getByRole("button", { name: "Create Quiz" }).click()

    // Wait for API call and verify payload
    await page.waitForTimeout(500)

    expect(capturedRequestBody).toBeDefined()
    expect(capturedRequestBody.language).toBe("no")
    expect(capturedRequestBody.title).toBe("Norsk Test Quiz")
    expect(capturedRequestBody.selected_modules).toEqual({
      "173467": {
        name: "Introduction to Neural Networks",
        question_batches: [{ question_type: "multiple_choice", count: 20 }],
      },
    })
  })
})
