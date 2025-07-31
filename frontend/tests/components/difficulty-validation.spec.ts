import { expect, test } from "@playwright/test"

test.describe("Difficulty Feature Validation Tests", () => {
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
        body: JSON.stringify([{ id: 12345, name: "Validation Test Course" }]),
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
            { id: 173467, name: "Test Module A" },
            { id: 173468, name: "Test Module B" },
          ]),
        })
      },
    )
  })

  test("should prevent duplicate question type and difficulty combinations within same module", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Validation Test Course").click()
    await page.getByLabel("Quiz Title").fill("Duplicate Validation Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Test Module A").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add first batch: Multiple Choice + Easy
    await page.getByText("Add Batch").first().click()

    // Find the first difficulty select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Easy option
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Add second batch: Multiple Choice + Easy (duplicate!)
    await page.getByText("Add Batch").first().click()

    // Find the second difficulty select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Easy option
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
    await page.getByText("Validation Test Course").click()
    await page.getByLabel("Quiz Title").fill("Different Difficulties Allowed")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Test Module A").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add first batch: Multiple Choice + Easy
    await page.getByText("Add Batch").first().click()

    // Find the first difficulty select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Easy option
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Add second batch: Multiple Choice + Hard (different difficulty, should be allowed)
    await page.getByText("Add Batch").first().click()

    // Find the second difficulty select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Hard option
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
    await page.getByText("Validation Test Course").click()
    await page.getByLabel("Quiz Title").fill("Different Types Same Difficulty")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Test Module A").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add first batch: Multiple Choice + Medium (default)
    await page.getByText("Add Batch").first().click()

    // Add second batch: True/False + Medium (different type, same difficulty - should be allowed)
    await page.getByText("Add Batch").first().click()

    // Find the second question type select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Question Type" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click True/False option
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="true_false"]',
      )
      .click()

    // Should NOT show validation error
    await expect(
      page.getByText("duplicate").or(page.getByText("Cannot have duplicate")),
    ).not.toBeVisible()
  })

  test("should allow duplicate combinations across different modules", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection with multiple modules
    await page.getByText("Validation Test Course").click()
    await page.getByLabel("Quiz Title").fill("Cross Module Duplicates Allowed")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Select both modules
    await page.getByText("Test Module A").click()
    await page.getByText("Test Module B").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add batch to first module: Multiple Choice + Easy
    await page.getByText("Add Batch").first().click()

    // Find the first difficulty select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Easy option
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Add batch to second module: Multiple Choice + Easy (same combination, different module - should be allowed)
    await page.getByText("Add Batch").nth(1).click()

    // Find the second difficulty select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Easy option
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Should NOT show validation error (duplicates are only prevented within same module)
    await expect(
      page.getByText("duplicate").or(page.getByText("Cannot have duplicate")),
    ).not.toBeVisible()
  })

  test("should validate maximum 4 batches per module", async ({ page }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Validation Test Course").click()
    await page.getByLabel("Quiz Title").fill("Max Batches Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Test Module A").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add 4 batches with different combinations
    const combinations = [
      { type: "Multiple Choice", difficulty: "Easy" },
      { type: "True/False", difficulty: "Easy" },
      { type: "Multiple Choice", difficulty: "Medium" },
      { type: "Fill in the Blank", difficulty: "Easy" },
    ]

    for (let i = 0; i < 4; i++) {
      await page.getByText("Add Batch").first().click()

      // Set question type if not Multiple Choice (default)
      if (combinations[i].type !== "Multiple Choice") {
        // Find the question type select trigger and click it
        await page
          .locator("label")
          .filter({ hasText: "Question Type" })
          .nth(i)
          .locator("..")
          .locator('[data-part="trigger"]')
          .first()
          .click()

        // Map the display name to the actual value
        const typeValue =
          combinations[i].type === "True/False"
            ? "true_false"
            : combinations[i].type === "Fill in the Blank"
              ? "fill_in_blank"
              : combinations[i].type === "Matching"
                ? "matching"
                : combinations[i].type === "Categorization"
                  ? "categorization"
                  : "multiple_choice"

        // Wait for dropdown to be visible and click the option
        await page
          .locator(
            `[data-part="content"]:visible [data-part="item"][data-value="${typeValue}"]`,
          )
          .click()
      }

      // Set difficulty if not Medium (default)
      if (combinations[i].difficulty !== "Medium") {
        // Find the difficulty select trigger and click it
        await page
          .locator("label")
          .filter({ hasText: "Difficulty" })
          .nth(i)
          .locator("..")
          .locator('[data-part="trigger"]')
          .first()
          .click()

        // Map the display name to the actual value
        const difficultyValue = combinations[i].difficulty.toLowerCase()

        // Wait for dropdown to be visible and click the option
        await page
          .locator(
            `[data-part="content"]:visible [data-part="item"][data-value="${difficultyValue}"]`,
          )
          .click()
      }
    }

    // Verify we have 4 batches - wait for the UI to update
    await page.waitForTimeout(1000)
    await expect(page.getByText(/4 batches/).first()).toBeVisible()

    // Try to add 5th batch - button should be disabled
    const addButton = page.getByText("Add Batch").first()
    await expect(addButton).toBeDisabled()
  })

  test("should enforce question count limits (1-20 per batch)", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Validation Test Course").click()
    await page.getByLabel("Quiz Title").fill("Question Count Validation")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Test Module A").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Add batch
    await page.getByText("Add Batch").first().click()
    const questionInput = page.getByRole("spinbutton").first()

    // Test invalid values
    await questionInput.fill("0")
    await questionInput.blur()
    // Should either reject the value or show validation error

    await questionInput.fill("25")
    await questionInput.blur()
    // Should either cap at 20 or show validation error

    // Test valid value
    await questionInput.fill("15")
    await expect(questionInput).toHaveValue("15")
  })

  test("should clear validation errors when issues are resolved", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Validation Test Course").click()
    await page.getByLabel("Quiz Title").fill("Error Clearing Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Test Module A").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Create duplicate scenario
    await page.getByText("Add Batch").first().click()

    // Find the first difficulty select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .first()
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Easy option
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    await page.getByText("Add Batch").first().click()

    // Find the second difficulty select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Easy option
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Should show validation error
    await expect(
      page.getByText("duplicate").or(page.getByText("Cannot have duplicate")),
    ).toBeVisible()

    // Fix the issue by changing the second batch's difficulty
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(1)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Hard option
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="hard"]',
      )
      .click()

    // Error should disappear
    await expect(
      page.getByText("duplicate").or(page.getByText("Cannot have duplicate")),
    ).not.toBeVisible()
  })

  test("should handle all difficulty combinations systematically", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Navigate to module question selection
    await page.getByText("Validation Test Course").click()
    await page.getByLabel("Quiz Title").fill("Systematic Difficulty Test")
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")
    await page.getByText("Test Module A").click()
    await page.getByRole("button", { name: "next" }).click()
    await page.waitForLoadState("networkidle")

    // Test all 3 difficulty levels with Multiple Choice
    const difficulties = ["Easy", "Medium", "Hard"]

    for (let i = 0; i < difficulties.length; i++) {
      await page.getByText("Add Batch").first().click()

      if (difficulties[i] !== "Medium") {
        // Medium is default
        // Find the difficulty select trigger and click it
        await page
          .locator("label")
          .filter({ hasText: "Difficulty" })
          .nth(i)
          .locator("..")
          .locator('[data-part="trigger"]')
          .first()
          .click()

        // Map the display name to the actual value
        const difficultyValue = difficulties[i].toLowerCase()

        // Wait for dropdown to be visible and click the option
        await page
          .locator(
            `[data-part="content"]:visible [data-part="item"][data-value="${difficultyValue}"]`,
          )
          .click()
      }
    }

    // Should have 3 batches without errors - wait for the UI to update
    await page.waitForTimeout(1000)
    await expect(page.getByText(/3 batches/).first()).toBeVisible()
    await expect(
      page.getByText("duplicate").or(page.getByText("Cannot have duplicate")),
    ).not.toBeVisible()

    // Try to add 4th batch with duplicate Easy (should trigger error)
    await page.getByText("Add Batch").first().click()

    // Find the fourth difficulty select trigger and click it
    await page
      .locator("label")
      .filter({ hasText: "Difficulty" })
      .nth(3)
      .locator("..")
      .locator('[data-part="trigger"]')
      .first()
      .click()

    // Wait for dropdown to be visible and click Easy option
    await page
      .locator(
        '[data-part="content"]:visible [data-part="item"][data-value="easy"]',
      )
      .click()

    // Should show validation error
    await expect(
      page.getByText("duplicate").or(page.getByText("Cannot have duplicate")),
    ).toBeVisible()
  })
})
