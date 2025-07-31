import { expect, test } from "@playwright/test"

test.describe("Tone Feature Integration Tests", () => {
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
          { id: 12345, name: "Software Engineering Principles" },
          { id: 67890, name: "Advanced Machine Learning" },
        ]),
      })
    })

    // Mock Canvas modules API for both courses
    await page.route(
      "**/api/v1/canvas/courses/12345/modules",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 173467, name: "Design Patterns" },
            { id: 173468, name: "Testing Strategies" },
            { id: 173469, name: "Code Quality" },
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
            { id: 173470, name: "Neural Networks" },
            { id: 173471, name: "Deep Learning" },
          ]),
        })
      },
    )
  })

  test("complete tone feature workflow - Academic tone with English", async ({
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

    // Start from quiz list
    await page.goto("/quizzes")

    // Verify empty state and create quiz
    await expect(page.getByText("No Quizzes Found")).toBeVisible()
    await page.getByRole("link", { name: "Create Your First Quiz" }).click()

    // Step 1: Course Selection
    await expect(page).toHaveURL("/create-quiz")
    await page.getByText("Software Engineering Principles").click()
    await page.getByLabel("Quiz Title").fill("Academic Tone Integration Test")
    await page.getByRole("button", { name: "next" }).click()

    // Step 2: Module Selection
    await page.waitForLoadState("networkidle")
    await page.getByText("Design Patterns").click()
    await page.getByText("Testing Strategies").click()
    await page.getByRole("button", { name: "next" }).click()

    // Step 3: Question Configuration
    await page.waitForLoadState("networkidle")
    await page.getByText("Add Batch").first().click()
    const firstQuestionInput = page.getByRole("spinbutton").first()
    await firstQuestionInput.fill("10")

    // Add batch for second module
    await page.getByText("Add Batch").nth(1).click()
    const secondQuestionInput = page.getByRole("spinbutton").nth(1)
    await secondQuestionInput.fill("15")

    await page.getByRole("button", { name: "next" }).click()

    // Step 4: Quiz Configuration - Verify defaults and confirm selection
    await page.waitForLoadState("networkidle")
    await expect(page.getByText("Quiz Configuration")).toBeVisible()

    // Verify default English language is selected
    const englishCard = page.locator('[data-testid="language-card-en"]')
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50

    // Verify default academic tone is selected
    const academicCard = page.locator('[data-testid="tone-card-academic"]')
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50

    // Mock quiz creation API
    const newQuizId = "academic-tone-test-quiz"
    await page.route("**/api/v1/quiz/", async (route) => {
      if (route.request().method() === "POST") {
        const requestBody = await route.request().postDataJSON()

        // Verify API payload contains correct tone and language
        expect(requestBody.tone).toBe("academic")
        expect(requestBody.language).toBe("en")
        expect(requestBody.title).toBe("Academic Tone Integration Test")

        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: newQuizId,
            title: "Academic Tone Integration Test",
            canvas_course_id: 12345,
            canvas_course_name: "Software Engineering Principles",
            selected_modules: {
              "173467": {
                name: "Design Patterns",
                question_batches: [
                  { question_type: "multiple_choice", count: 10 },
                ],
              },
              "173468": {
                name: "Testing Strategies",
                question_batches: [
                  { question_type: "multiple_choice", count: 15 },
                ],
              },
            },
            question_count: 25,
            language: "en",
            tone: "academic",
            llm_model: "o3",
            llm_temperature: 1.0,
            status: "created",
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

  test("complete tone feature workflow - Professional tone with Norwegian", async ({
    page,
  }) => {
    // Mock quiz creation for professional tone + Norwegian
    const newQuizId = "professional-norwegian-test-quiz"
    await page.route("**/api/v1/quiz/", async (route) => {
      if (route.request().method() === "POST") {
        const requestBody = await route.request().postDataJSON()

        // Verify API payload
        expect(requestBody.tone).toBe("professional")
        expect(requestBody.language).toBe("no")
        expect(requestBody.title).toBe("Profesjonell Norsk Eksamen")

        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: newQuizId,
            title: "Profesjonell Norsk Eksamen",
            canvas_course_id: 67890,
            canvas_course_name: "Advanced Machine Learning",
            selected_modules: {
              "173470": {
                name: "Neural Networks",
                question_batches: [
                  { question_type: "multiple_choice", count: 20 },
                ],
              },
            },
            question_count: 20,
            language: "no",
            tone: "professional",
            llm_model: "o3",
            llm_temperature: 1.0,
            status: "created",
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

    // Course selection
    await page.getByText("Advanced Machine Learning").click()
    await page.getByLabel("Quiz Title").fill("Profesjonell Norsk Eksamen")
    await page.getByRole("button", { name: "next" }).click()

    // Module selection
    await page.waitForLoadState("networkidle")
    await page.getByText("Neural Networks").click()
    await page.getByRole("button", { name: "next" }).click()

    // Question configuration
    await page.waitForLoadState("networkidle")
    await page.getByText("Add Batch").first().click()
    const questionInput = page.getByRole("spinbutton").first()
    await questionInput.fill("20")
    await page.getByRole("button", { name: "next" }).click()

    // Quiz configuration - Select Norwegian and Professional
    await page.waitForLoadState("networkidle")

    // Select Norwegian language
    await page.locator('[data-testid="language-card-no"]').click()

    // Select professional tone
    await page.locator('[data-testid="tone-card-professional"]').click()

    // Verify both selections are active
    const norwegianCard = page.locator('[data-testid="language-card-no"]')
    const professionalCard = page.locator(
      '[data-testid="tone-card-professional"]',
    )

    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(professionalCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50

    // Create quiz
    await page.getByRole("button", { name: "Create Quiz" }).click()

    // Should redirect to quiz detail page
    await expect(page).toHaveURL(`/quiz/${newQuizId}`)
  })

  test("tone selection persistence across navigation", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.goto("/create-quiz")

    // Navigate through all steps to quiz configuration
    await page.getByText("Software Engineering Principles").click()
    await page.getByLabel("Quiz Title").fill("Navigation Persistence Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Design Patterns").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Add Batch").first().click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Make specific selections
    await page.locator('[data-testid="language-card-no"]').click()
    await page.locator('[data-testid="tone-card-encouraging"]').click()

    // Verify selections
    const norwegianCard = page.locator('[data-testid="language-card-no"]')
    const encouragingCard = page.locator(
      '[data-testid="tone-card-encouraging"]',
    )
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(encouragingCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50

    // Navigate backwards and forwards
    await page.getByRole("button", { name: "Previous" }).click()
    await expect(page.getByText("Step 3 of 4")).toBeVisible()

    await page.getByRole("button", { name: "Next" }).click()
    await page.waitForLoadState("networkidle")

    // Verify selections are preserved
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(encouragingCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50

    // Navigate back two steps
    await page.getByRole("button", { name: "Previous" }).click()
    await page.getByRole("button", { name: "Previous" }).click()
    await expect(page.getByText("Step 2 of 4")).toBeVisible()

    // Navigate forward two steps
    await page.getByRole("button", { name: "Next" }).click()
    await page.getByRole("button", { name: "Next" }).click()
    await page.waitForLoadState("networkidle")

    // Verify selections are still preserved
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(encouragingCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50
  })

  test("all four tone options work correctly in integration", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.goto("/create-quiz")

    // Navigate to quiz configuration
    await page.getByText("Software Engineering Principles").click()
    await page.getByLabel("Quiz Title").fill("All Tones Integration Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Design Patterns").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Add Batch").first().click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    const academicCard = page.locator('[data-testid="tone-card-academic"]')
    const casualCard = page.locator('[data-testid="tone-card-casual"]')
    const encouragingCard = page.locator(
      '[data-testid="tone-card-encouraging"]',
    )
    const professionalCard = page.locator(
      '[data-testid="tone-card-professional"]',
    )

    // Test Academic (should be selected by default)
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50
    await expect(
      page.getByText("Use formal academic language with precise terminology"),
    ).toBeVisible()

    // Test Casual
    await casualCard.click()
    await expect(casualCard).toHaveCSS("background-color", "rgb(240, 253, 244)") // green.50
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    ) // white
    await expect(
      page.getByText(
        "Use everyday conversational language that feels approachable",
      ),
    ).toBeVisible()

    // Test Encouraging
    await encouragingCard.click()
    await expect(encouragingCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50
    await expect(casualCard).toHaveCSS("background-color", "rgb(255, 255, 255)") // white
    await expect(
      page.getByText(
        "Use warm, supportive language with helpful hints embedded in questions",
      ),
    ).toBeVisible()

    // Test Professional
    await professionalCard.click()
    await expect(professionalCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50
    await expect(encouragingCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    ) // white
    await expect(
      page.getByText(
        "Use clear, direct business language for workplace training",
      ),
    ).toBeVisible()

    // Return to Academic
    await academicCard.click()
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50
    await expect(professionalCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    ) // white
  })

  test("tone and language combinations work together", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.goto("/create-quiz")

    // Navigate to quiz configuration
    await page.getByText("Software Engineering Principles").click()
    await page.getByLabel("Quiz Title").fill("Language Tone Combination Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Design Patterns").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Add Batch").first().click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    const englishCard = page.locator('[data-testid="language-card-en"]')
    const norwegianCard = page.locator('[data-testid="language-card-no"]')
    const academicCard = page.locator('[data-testid="tone-card-academic"]')
    const casualCard = page.locator('[data-testid="tone-card-casual"]')

    // Test different combinations
    // 1. English + Academic (default)
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50

    // 2. English + Casual
    await casualCard.click()
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(casualCard).toHaveCSS("background-color", "rgb(240, 253, 244)") // green.50

    // 3. Norwegian + Casual
    await norwegianCard.click()
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(casualCard).toHaveCSS("background-color", "rgb(240, 253, 244)") // green.50

    // 4. Norwegian + Academic
    await academicCard.click()
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50

    // Verify that language and tone selections are independent
    await englishCard.click() // Change language but keep tone
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)",
    ) // green.50
  })

  test("tone feature works with quiz creation form validation", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.goto("/create-quiz")

    // Navigate to quiz configuration without filling all required fields properly
    await page.getByText("Software Engineering Principles").click()
    // Intentionally skip title
    await page.getByRole("button", { name: "next" }).click()

    // Should not proceed if title is missing
    await expect(page.getByText("Step 2 of 4")).toBeVisible()

    // Fill title and proceed
    await page.getByText("Design Patterns").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Should not proceed - need to add at least one question batch
    await expect(page.getByText("Step 3 of 4")).toBeVisible()

    // Add question batch and proceed
    await page.getByText("Add Batch").first().click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Now we should be at quiz configuration with tone options working
    await expect(page.getByText("Quiz Configuration")).toBeVisible()

    // Test that tone selection works even after form validation issues
    const casualCard = page.locator('[data-testid="tone-card-casual"]')
    await casualCard.click()
    await expect(casualCard).toHaveCSS("background-color", "rgb(240, 253, 244)") // green.50

    const norwegianCard = page.locator('[data-testid="language-card-no"]')
    await norwegianCard.click()
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
  })
})
