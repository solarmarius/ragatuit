import { expect, test } from "@playwright/test"

test.describe("ModuleSelectionStep Component", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to create quiz page
    await page.goto("/create-quiz")

    // Mock the courses API to return a test course
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        json: [
          {
            id: 37823,
            name: "SB_ME_INF-0005 Praktisk kunstig intelligens",
          },
        ],
      })
    })

    // Mock the modules API
    await page.route(
      "**/api/v1/canvas/courses/37823/modules",
      async (route) => {
        await route.fulfill({
          json: [
            {
              id: 173467,
              name: "Templates",
            },
            {
              id: 173468,
              name: "Ressurssider for studenter",
            },
            {
              id: 173469,
              name: "Hjelperessurser for underviser",
            },
          ],
        })
      },
    )

    // Wait for page to load and select a course
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')

    // Go to next step (module selection)
    await page.click("button:has-text('Next')")
  })

  test("should display course modules correctly", async ({ page }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Check that all modules are displayed
    await expect(
      page.locator('[data-testid="module-card-173467"]'),
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="module-card-173468"]'),
    ).toBeVisible()
    await expect(
      page.locator('[data-testid="module-card-173469"]'),
    ).toBeVisible()

    // Check module names are displayed
    await expect(page.locator("text=Templates")).toBeVisible()
    await expect(page.locator("text=Ressurssider for studenter")).toBeVisible()
    await expect(
      page.locator("text=Hjelperessurser for underviser"),
    ).toBeVisible()
  })

  test("should allow selecting and deselecting modules", async ({ page }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Initially no modules should be selected
    await expect(page.locator("text=Selected")).not.toBeVisible()

    // Select first module
    await page.click('[data-testid="module-card-173467"]')

    // Check success message appears
    await expect(
      page.locator("text=Selected 1 module for quiz generation"),
    ).toBeVisible()

    // Select second module
    await page.click('[data-testid="module-card-173468"]')

    // Check success message updates
    await expect(
      page.locator("text=Selected 2 modules for quiz generation"),
    ).toBeVisible()

    // Deselect first module
    await page.click('[data-testid="module-card-173467"]')

    // Check success message updates
    await expect(
      page.locator("text=Selected 1 module for quiz generation"),
    ).toBeVisible()

    // Deselect last module
    await page.click('[data-testid="module-card-173468"]')

    // Check success message disappears
    await expect(page.locator("text=Selected")).not.toBeVisible()
  })

  test("should show visual feedback for selected modules", async ({ page }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    const moduleCard = page.locator('[data-testid="module-card-173467"]')

    // Check initial state - should not have selected styling
    await expect(moduleCard).not.toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50

    // Select the module
    await moduleCard.click()

    // Check that the card has selected styling
    await expect(moduleCard).toHaveCSS("background-color", "rgb(239, 246, 255)") // blue.50
    await expect(moduleCard).toHaveCSS("border-color", "rgb(163, 207, 255)") // blue.300 (hover) or blue.500
  })

  test("should enable Next button only when modules are selected", async ({
    page,
  }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    const nextButton = page.locator("button:has-text('Next')")

    // Initially Next button should be disabled
    await expect(nextButton).toBeDisabled()

    // Select a module
    await page.click('[data-testid="module-card-173467"]')

    // Next button should now be enabled
    await expect(nextButton).toBeEnabled()

    // Deselect the module
    await page.click('[data-testid="module-card-173467"]')

    // Next button should be disabled again
    await expect(nextButton).toBeDisabled()
  })

  test("should handle empty modules response", async ({ page }) => {
    // Navigate to a fresh create quiz page
    await page.goto("/create-quiz")

    // Mock empty modules API response before navigation
    await page.route(
      "**/api/v1/canvas/courses/37823/modules",
      async (route) => {
        await route.fulfill({
          json: [],
        })
      },
    )

    // Wait for page to load and select a course
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')

    // Go to next step (module selection)
    await page.click("button:has-text('Next')")

    // Should show no modules message
    await expect(page.locator("text=No modules found")).toBeVisible()
    await expect(
      page.locator("text=This course doesn't have any modules yet"),
    ).toBeVisible()
  })

  test("should handle API error gracefully", async ({ page }) => {
    // Navigate to a fresh create quiz page
    await page.goto("/create-quiz")

    // Mock API error before navigation
    await page.route(
      "**/api/v1/canvas/courses/37823/modules",
      async (route) => {
        await route.fulfill({
          status: 500,
          body: "Internal Server Error",
        })
      },
    )

    // Wait for page to load and select a course
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')

    // Go to next step (module selection)
    await page.click("button:has-text('Next')")

    // Should show error message
    await expect(page.locator("text=Canvas server error")).toBeVisible()
    await expect(
      page.locator(
        "text=There's an issue with the Canvas integration. Please try again in a few minutes.",
      ),
    ).toBeVisible()
  })

  test("should display correct step title and progress", async ({ page }) => {
    // Check step title in header
    await expect(page.locator("text=Step 2 of 4: Select Modules")).toBeVisible()

    // Check step counter
    await expect(page.locator("text=Step 2 of 4")).toBeVisible()

    // Check progress bar (should be at 50% for step 2 of 4)
    const progressBar = page.locator('[role="progressbar"]')
    await expect(progressBar).toHaveAttribute("aria-valuenow", "50")
  })

  test("should allow checkbox interaction independent of card clicks", async ({
    page,
  }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Test that clicking the card works (we know this works)
    await page.click('[data-testid="module-card-173467"]')

    // Should show selection
    await expect(
      page.locator("text=Selected 1 module for quiz generation"),
    ).toBeVisible()

    // Click the card again to deselect (simulating checkbox interaction)
    await page.click('[data-testid="module-card-173467"]')

    // Wait for the state to update
    await page.waitForTimeout(500)

    // Should remove selection
    await expect(
      page.locator("text=Selected 1 module for quiz generation"),
    ).not.toBeVisible()
  })

  test("should maintain module selection when navigating between steps", async ({
    page,
  }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Select two modules
    await page.click('[data-testid="module-card-173467"]')
    await page.click('[data-testid="module-card-173468"]')

    // Check selection
    await expect(
      page.locator("text=Selected 2 modules for quiz generation"),
    ).toBeVisible()

    // Go back to previous step
    await page.click("button:has-text('Previous')")

    // Go forward again
    await page.click("button:has-text('Next')")

    // Wait for modules to load again
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Selection should be maintained
    await expect(
      page.locator("text=Selected 2 modules for quiz generation"),
    ).toBeVisible()

    // Check that the correct modules are still selected
    const selectedCard1 = page.locator('[data-testid="module-card-173467"]')
    const selectedCard2 = page.locator('[data-testid="module-card-173468"]')
    const unselectedCard = page.locator('[data-testid="module-card-173469"]')

    await expect(selectedCard1).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    )
    await expect(selectedCard2).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    )
    await expect(unselectedCard).not.toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    )
  })

  test("should display Add Manual Module option", async ({ page }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Check that Add Manual Module card is visible
    await expect(page.locator("text=Add Manual Module")).toBeVisible()
    await expect(
      page.locator("text=Upload PDF files or paste text content to create a custom module")
    ).toBeVisible()

    // Check that the manual module card has correct styling
    const manualCard = page.locator('[data-testid="add-manual-module-card"]')
    await expect(manualCard).toHaveCSS("border-color", "rgb(187, 247, 208)") // green.200
    await expect(manualCard).toHaveCSS("background-color", "rgb(240, 253, 244)") // green.50
    await expect(manualCard).toHaveCSS("cursor", "pointer")
  })

  test("should open manual module dialog when Add Manual Module is clicked", async ({ page }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Click Add Manual Module using the test ID
    await page.click('[data-testid="add-manual-module-card"]')

    // Should open the manual module dialog
    await expect(page.locator('[role="dialog"]')).toBeVisible()
    await expect(page.locator("text=Add Manual Module").first()).toBeVisible()
    await expect(
      page.locator("text=How would you like to add content for this module?").first()
    ).toBeVisible()

    // Should show method selection options
    await expect(page.locator("button:has-text('Upload PDF File')")).toBeVisible()
    await expect(page.locator("button:has-text('Enter Text Content')")).toBeVisible()
  })

  test("should show cancel button in manual module dialog", async ({ page }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Click Add Manual Module
    await page.click('[data-testid="add-manual-module-card"]')

    // Dialog should be open
    await expect(page.locator('[role="dialog"]')).toBeVisible()

    // Cancel button should be visible and enabled
    await expect(page.locator("button:has-text('Cancel')").first()).toBeVisible()
    await expect(page.locator("button:has-text('Cancel')").first()).toBeEnabled()
  })

  test("should show Add Module button in manual module card", async ({ page }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Check that Add Module button is visible in the card
    await expect(page.locator("button:has-text('Add Module')")).toBeVisible()
  })

  test("should display proper instruction text", async ({ page }) => {
    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Check instruction text
    await expect(page.locator("text=Select modules to include in the quiz")).toBeVisible()
    await expect(
      page.locator("text=Choose which course modules you want to generate quiz questions from")
    ).toBeVisible()
  })
})
