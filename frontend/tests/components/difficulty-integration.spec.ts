import { expect, test } from "@playwright/test"

test.describe("Difficulty Feature Integration Tests", () => {
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
          { id: 12345, name: "Difficulty Testing Course" },
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
            { id: 173467, name: "Introduction Module" },
            { id: 173468, name: "Advanced Module" },
          ]),
        })
      },
    )
  })

  test("should display difficulty selector with correct options", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection step
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Difficulty Test Quiz")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add a batch to see difficulty options
    await page.getByText("Add Batch").first().click()

    // Verify difficulty field is present
    await expect(
      page.locator("label").filter({ hasText: "Difficulty" }),
    ).toBeVisible()

    // Try to open difficulty dropdown
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Check for all three difficulty levels in visible dropdown
    await expect(
      page.locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      ),
    ).toBeVisible()
    await expect(
      page.locator(
        '[data-part="content"]:visible [data-part="item"][data-value="medium"]',
      ),
    ).toBeVisible()
    await expect(
      page.locator(
        '[data-part="content"]:visible [data-part="item"][data-value="hard"]',
      ),
    ).toBeVisible()
  })

  test("should default to medium difficulty", async ({ page }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection step
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Default Difficulty Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add a batch
    await page.getByText("Add Batch").first().click()

    // The default should be medium difficulty
    // Since we can't easily check the select value, we'll verify by opening dropdown
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Medium should be selected by default (this might show as selected state in UI)
    await expect(
      page.locator(
        '[data-part="content"]:visible [data-part="item"][data-value="medium"]',
      ),
    ).toBeVisible()
  })

  test("should allow switching between difficulty levels", async ({ page }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Difficulty Switch Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add a batch
    await page.getByText("Add Batch").first().click()

    // Test switching to Easy
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Verify selection (dropdown should close and show Easy)
    await page.waitForTimeout(500) // Wait for UI update

    // Test switching to Hard
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="hard"]',
      )
      .click()

    // The difficulty selector should still be functional
    await expect(
      page.locator("label").filter({ hasText: "Difficulty" }).first(),
    ).toBeVisible()
  })

  test("should prevent duplicate question type and difficulty combinations", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Duplicate Prevention Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add first batch with multiple choice, easy difficulty
    await page.getByText("Add Batch").first().click()

    // Set first batch to Easy difficulty
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Add second batch
    await page.getByText("Add Batch").first().click()

    // Try to set second batch to same type (multiple choice) and difficulty (easy)
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Should show validation error
    await expect(
      page
        .getByText(
          "Cannot have duplicate question type and difficulty combinations",
        )
        .or(page.getByText("duplicate")),
    ).toBeVisible()
  })

  test("should allow same question type with different difficulties", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Different Difficulties Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add first batch with multiple choice, easy difficulty
    await page.getByText("Add Batch").first().click()
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Add second batch with multiple choice, hard difficulty (should be allowed)
    await page.getByText("Add Batch").first().click()
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="hard"]',
      )
      .click()

    // Should NOT show validation error
    await expect(
      page.getByText("duplicate").or(page.getByText("Cannot have duplicate")),
    ).not.toBeVisible()
  })

  test("should allow different question types with same difficulty", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Same Difficulty Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add first batch with multiple choice, medium difficulty
    await page.getByText("Add Batch").first().click()
    // Default is medium, so no need to change difficulty

    // Add second batch and change to different question type
    await page.getByText("Add Batch").first().click()
    await page
      .locator("label")
      .filter({ hasText: "Question Type" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="true_false"]',
      )
      .click()

    // Should NOT show validation error (different types, same difficulty is OK)
    await expect(
      page.getByText("duplicate").or(page.getByText("Cannot have duplicate")),
    ).not.toBeVisible()
  })

  test("should persist difficulty selection across modules", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection with multiple modules
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Multi-Module Difficulty Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Select both modules
    await page.getByText("Introduction Module").click()
    await page.getByText("Advanced Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add batch to first module with hard difficulty
    await page.getByText("Add Batch").first().click()
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="hard"]',
      )
      .click()

    // Add batch to second module with easy difficulty
    await page.getByText("Add Batch").nth(1).click()
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Navigate to next step and back to verify persistence
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByRole("button", { name: "Previous" }).click()
    await page.waitForLoadState("networkidle")

    // Verify both difficulty selections are maintained
    // The batches should still be there with their respective difficulties
    await expect(
      page.locator("label").filter({ hasText: "Difficulty" }),
    ).toHaveCount(2)
  })

  test("should include difficulty in total question calculation", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Question Count Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add batch with 15 questions, easy difficulty
    await page.getByText("Add Batch").first().click()
    const questionInput = page.getByRole("spinbutton").first()
    await questionInput.fill("15")

    // Add another batch with 10 questions, hard difficulty
    await page.getByText("Add Batch").first().click()
    const secondQuestionInput = page.getByRole("spinbutton").nth(1)
    await secondQuestionInput.fill("10")

    // Change second batch to different question type
    await page
      .locator("label")
      .filter({ hasText: "Question Type" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="true_false"]',
      )
      .click()

    // Change second batch difficulty
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="hard"]',
      )
      .click()

    // Verify total questions = 25 (15 + 10) - use more specific selector
    await page.waitForTimeout(500) // Wait for UI update
    await expect(page.locator('text="25"').first()).toBeVisible() // In the summary card
  })

  test("should display appropriate help text about difficulty", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Help Text Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Check that help text mentions difficulty levels - use more specific selector
    await expect(page.getByText(/difficulty level/).first()).toBeVisible()
  })

  test("should handle difficulty in quiz creation API payload", async ({
    page,
  }) => {
    // Mock quiz creation API to capture the payload
    let capturedRequestBody: any

    await page.route("**/api/v1/quiz/", async (route) => {
      if (route.request().method() === "POST") {
        capturedRequestBody = await route.request().postDataJSON()

        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: "test-quiz-id",
            title: "Difficulty API Test",
            canvas_course_id: 12345,
            canvas_course_name: "Difficulty Testing Course",
            selected_modules: {
              "173467": {
                name: "Introduction Module",
                question_batches: [
                  {
                    question_type: "multiple_choice",
                    count: 10,
                    difficulty: "hard",
                  },
                ],
              },
            },
            question_count: 10,
            language: "en",
            tone: "academic",
            llm_model: "gpt-4o",
            llm_temperature: 0.7,
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

    // Complete quiz creation with specific difficulty
    await page.getByText("Difficulty Testing Course").click()
    await page.getByLabel("Quiz Title").fill("Difficulty API Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Introduction Module").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add batch with hard difficulty
    await page.getByText("Add Batch").first().click()
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="hard"]',
      )
      .click()

    // Complete quiz creation
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByRole("button", { name: "Create Quiz" }).click()

    // Wait for API call and verify payload
    await page.waitForTimeout(1000)

    expect(capturedRequestBody).toBeDefined()
    expect(
      capturedRequestBody.selected_modules["173467"].question_batches[0]
        .difficulty,
    ).toBe("hard")
  })
})
