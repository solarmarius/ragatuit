import { expect, test } from "@playwright/test"

test.describe("Complete Module Selection Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Mock the authentication to avoid login flow
    await page.addInitScript(() => {
      localStorage.setItem("auth-token", "mock-jwt-token")
    })

    // Mock courses API
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        json: [
          {
            id: 37823,
            name: "SB_ME_INF-0005 Praktisk kunstig intelligens",
          },
          {
            id: 37824,
            name: "SB_ME_INF-0006 Bruk av generativ KI",
          },
        ],
      })
    })

    // Mock modules API for course 37823
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
            {
              id: 173470,
              name: "Module 1",
            },
            {
              id: 173471,
              name: "Module 2",
            },
          ],
        })
      },
    )

    // Mock modules API for course 37824
    await page.route(
      "**/api/v1/canvas/courses/37824/modules",
      async (route) => {
        await route.fulfill({
          json: [
            {
              id: 273467,
              name: "Introduction",
            },
            {
              id: 273468,
              name: "Advanced Topics",
            },
          ],
        })
      },
    )

    // Mock user profile API
    await page.route("**/api/v1/users/me", async (route) => {
      await route.fulfill({
        json: {
          name: "Test Teacher",
          onboarding_completed: true,
        },
      })
    })
  })

  test("complete end-to-end quiz creation flow with module selection", async ({
    page,
  }) => {
    // Navigate to create quiz page
    await page.goto("/create-quiz")

    // Step 1: Course Selection
    await expect(page.locator("text=Step 1 of 3: Select Course")).toBeVisible()

    // Wait for courses to load
    await page.waitForSelector('[data-testid="course-card-37823"]')

    // Verify courses are displayed
    await expect(
      page.locator("text=SB_ME_INF-0005 Praktisk kunstig intelligens"),
    ).toBeVisible()
    await expect(
      page.locator("text=SB_ME_INF-0006 Bruk av generativ KI"),
    ).toBeVisible()

    // Select first course
    await page.click('[data-testid="course-card-37823"]')

    // Verify course selection feedback
    await expect(
      page.locator(
        "text=Selected: SB_ME_INF-0005 Praktisk kunstig intelligens",
      ),
    ).toBeVisible()

    // Next button should be enabled
    await expect(page.locator("button:has-text('Next')")).toBeEnabled()

    // Go to next step
    await page.click("button:has-text('Next')")

    // Step 2: Module Selection
    await expect(page.locator("text=Step 2 of 3: Select Modules")).toBeVisible()

    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Verify all modules are displayed
    await expect(page.locator("text=Templates")).toBeVisible()
    await expect(page.locator("text=Ressurssider for studenter")).toBeVisible()
    await expect(
      page.locator("text=Hjelperessurser for underviser"),
    ).toBeVisible()
    await expect(page.locator("text=Module 1")).toBeVisible()
    await expect(page.locator("text=Module 2")).toBeVisible()

    // Initially Next button should be disabled (no modules selected)
    await expect(page.locator("button:has-text('Next')")).toBeDisabled()

    // Select multiple modules
    await page.click('[data-testid="module-card-173468"]') // Ressurssider for studenter
    await page.click('[data-testid="module-card-173470"]') // Module 1
    await page.click('[data-testid="module-card-173471"]') // Module 2

    // Verify selection feedback
    await expect(
      page.locator("text=Selected 3 modules for quiz generation"),
    ).toBeVisible()

    // Next button should now be enabled
    await expect(page.locator("button:has-text('Next')")).toBeEnabled()

    // Test deselection
    await page.click('[data-testid="module-card-173471"]') // Deselect Module 2
    await expect(
      page.locator("text=Selected 2 modules for quiz generation"),
    ).toBeVisible()

    // Re-select the module
    await page.click('[data-testid="module-card-173471"]') // Re-select Module 2
    await expect(
      page.locator("text=Selected 3 modules for quiz generation"),
    ).toBeVisible()

    // Go to next step
    await page.click("button:has-text('Next')")

    // Step 3: Quiz Settings (placeholder)
    await expect(page.locator("text=Step 3 of 3: Quiz Settings")).toBeVisible()
    await expect(
      page.locator("text=Quiz settings step - Coming soon"),
    ).toBeVisible()

    // Test navigation back to module selection
    await page.click("button:has-text('Previous')")

    // Should be back on module selection with state preserved
    await expect(page.locator("text=Step 2 of 3: Select Modules")).toBeVisible()
    await expect(
      page.locator("text=Selected 3 modules for quiz generation"),
    ).toBeVisible()

    // Verify the correct modules are still selected
    const selectedCard1 = page.locator('[data-testid="module-card-173468"]')
    const selectedCard2 = page.locator('[data-testid="module-card-173470"]')
    const selectedCard3 = page.locator('[data-testid="module-card-173471"]')
    const unselectedCard1 = page.locator('[data-testid="module-card-173467"]')
    const unselectedCard2 = page.locator('[data-testid="module-card-173469"]')

    // Check visual feedback for selected modules
    await expect(selectedCard1).toHaveCSS(
      "background-color",
      "rgb(219, 234, 254)",
    )
    await expect(selectedCard2).toHaveCSS(
      "background-color",
      "rgb(219, 234, 254)",
    )
    await expect(selectedCard3).toHaveCSS(
      "background-color",
      "rgb(219, 234, 254)",
    )
    await expect(unselectedCard1).not.toHaveCSS(
      "background-color",
      "rgb(219, 234, 254)",
    )
    await expect(unselectedCard2).not.toHaveCSS(
      "background-color",
      "rgb(219, 234, 254)",
    )
  })

  test("changing course should reset module selection", async ({ page }) => {
    // Navigate to create quiz page
    await page.goto("/create-quiz")

    // Select first course
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    // Select some modules from first course
    await page.waitForSelector('[data-testid="module-card-173467"]')
    await page.click('[data-testid="module-card-173467"]')
    await page.click('[data-testid="module-card-173468"]')

    await expect(
      page.locator("text=Selected 2 modules for quiz generation"),
    ).toBeVisible()

    // Go back to course selection
    await page.click("button:has-text('Previous')")

    // Select different course
    await page.click('[data-testid="course-card-37824"]')
    await page.click("button:has-text('Next')")

    // Should show modules from new course
    await page.waitForSelector('[data-testid="module-card-273467"]')
    await expect(page.locator("text=Introduction")).toBeVisible()
    await expect(page.locator("text=Advanced Topics")).toBeVisible()

    // Previous module selection should be reset
    await expect(page.locator("text=Selected")).not.toBeVisible()

    // Next button should be disabled since no modules are selected
    await expect(page.locator("button:has-text('Next')")).toBeDisabled()
  })

  test("handle course with no modules", async ({ page }) => {
    // Mock empty modules response
    await page.route(
      "**/api/v1/canvas/courses/37823/modules",
      async (route) => {
        await route.fulfill({
          json: [],
        })
      },
    )

    await page.goto("/create-quiz")

    // Select course
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    // Should show no modules message
    await expect(page.locator("text=No modules found")).toBeVisible()
    await expect(
      page.locator("text=This course doesn't have any modules yet"),
    ).toBeVisible()

    // Next button should be disabled
    await expect(page.locator("button:has-text('Next')")).toBeDisabled()
  })

  test("handle module API errors", async ({ page }) => {
    // Mock API error
    await page.route(
      "**/api/v1/canvas/courses/37823/modules",
      async (route) => {
        await route.fulfill({
          status: 403,
          json: { detail: "You don't have access to this course." },
        })
      },
    )

    await page.goto("/create-quiz")

    // Select course
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    // Should show error message
    await expect(
      page.locator("text=Failed to load course modules"),
    ).toBeVisible()
    await expect(
      page.locator(
        "text=There was an error loading the modules for this course",
      ),
    ).toBeVisible()

    // Next button should be disabled
    await expect(page.locator("button:has-text('Next')")).toBeDisabled()
  })

  test("progress bar updates correctly through the flow", async ({ page }) => {
    await page.goto("/create-quiz")

    // Step 1 - Progress should be 33.33%
    const progressBar = page.locator('[role="progressbar"]')
    await expect(progressBar).toHaveAttribute(
      "aria-valuenow",
      "33.333333333333336",
    )

    // Select course and go to step 2
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    // Step 2 - Progress should be 66.67%
    await expect(progressBar).toHaveAttribute(
      "aria-valuenow",
      "66.66666666666667",
    )

    // Select modules and go to step 3
    await page.waitForSelector('[data-testid="module-card-173467"]')
    await page.click('[data-testid="module-card-173467"]')
    await page.click("button:has-text('Next')")

    // Step 3 - Progress should be 100%
    await expect(progressBar).toHaveAttribute("aria-valuenow", "100")
  })

  test("cancel button works from any step", async ({ page }) => {
    await page.goto("/create-quiz")

    // Test cancel from step 1
    await page.click("button:has-text('Cancel')")
    await expect(page).toHaveURL("/")

    // Go back to create quiz
    await page.goto("/create-quiz")

    // Go to step 2
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    // Test cancel from step 2
    await page.click("button:has-text('Cancel')")
    await expect(page).toHaveURL("/")

    // Go back and proceed to step 3
    await page.goto("/create-quiz")
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")
    await page.waitForSelector('[data-testid="module-card-173467"]')
    await page.click('[data-testid="module-card-173467"]')
    await page.click("button:has-text('Next')")

    // Test cancel from step 3
    await page.click("button:has-text('Cancel')")
    await expect(page).toHaveURL("/")
  })

  test("keyboard navigation works for module selection", async ({ page }) => {
    await page.goto("/create-quiz")

    // Navigate to module selection
    await page.waitForSelector('[data-testid="course-card-37823"]')
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    // Wait for modules to load
    await page.waitForSelector('[data-testid="module-card-173467"]')

    // Use keyboard to navigate and select
    await page.keyboard.press("Tab") // Focus on first module
    await page.keyboard.press("Space") // Select first module

    // Verify selection
    await expect(
      page.locator("text=Selected 1 module for quiz generation"),
    ).toBeVisible()

    // Navigate to next module and select
    await page.keyboard.press("Tab")
    await page.keyboard.press("Space")

    // Verify updated selection
    await expect(
      page.locator("text=Selected 2 modules for quiz generation"),
    ).toBeVisible()
  })
})
