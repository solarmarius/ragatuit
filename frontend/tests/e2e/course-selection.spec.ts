import { expect, test } from "@playwright/test"

test.describe("Course Selection Feature", () => {
  // Mock API responses for different scenarios
  const mockCoursesResponse = [
    {
      id: 37823,
      name: "SB_ME_INF-0005 Praktisk kunstig intelligens",
    },
    {
      id: 37824,
      name: "SB_ME_INF-0006 Bruk av generativ KI",
    },
  ]

  const mockEmptyCoursesResponse: never[] = []

  test.beforeEach(async ({ page }) => {
    // Start from the authenticated dashboard
    await page.goto("/")
    await page.waitForLoadState("networkidle")
  })

  test("should navigate to quiz creation from dashboard", async ({ page }) => {
    // Find and click the "Create Quiz" button
    const createQuizButton = page.locator('button:has-text("Create Quiz")')
    await expect(createQuizButton).toBeVisible()
    await createQuizButton.click()

    // Should navigate to create-quiz route
    await expect(page).toHaveURL("/create-quiz")

    // Should show quiz creation wizard
    await expect(page.locator("text=Create New Quiz")).toBeVisible()
    await expect(page.locator("text=Step 1 of 3: Select Course")).toBeVisible()
  })

  test("should show course selection step correctly", async ({ page }) => {
    // Mock API to prevent loading state
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockCoursesResponse),
      })
    })

    await page.goto("/create-quiz")
    await page.waitForLoadState("networkidle")

    // Should show step 1 header
    await expect(page.locator("text=Select Course")).toBeVisible()
    await expect(
      page.locator("text=Select a course to create a quiz for"),
    ).toBeVisible()

    // Should show progress bar at 33% (step 1 of 3)
    const progressBar = page.locator('[role="progressbar"]')
    await expect(progressBar).toBeVisible()

    // Should show navigation buttons
    await expect(page.locator('button:has-text("Cancel")')).toBeVisible()
    await expect(page.locator('button:has-text("Next")')).toBeVisible()

    // Next button should be disabled initially (no course selected)
    await expect(page.locator('button:has-text("Next")')).toBeDisabled()
  })

  test("should load and display courses successfully", async ({ page }) => {
    // Mock successful API response
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockCoursesResponse),
      })
    })

    await page.goto("/create-quiz")

    // Should show loading state initially (but very briefly)
    // The loading state might be too fast to catch, so let's check final state
    await page.waitForLoadState("networkidle")

    // Should display the courses
    await expect(
      page.locator("text=SB_ME_INF-0005 Praktisk kunstig intelligens"),
    ).toBeVisible()
    await expect(
      page.locator("text=SB_ME_INF-0006 Bruk av generativ KI"),
    ).toBeVisible()

    // Should show course IDs
    await expect(page.locator("text=Course ID: 37823")).toBeVisible()
    await expect(page.locator("text=Course ID: 37824")).toBeVisible()

    // Should hide loading message
    await expect(page.locator("text=Loading your courses...")).not.toBeVisible()
  })

  test("should handle course selection and enable next button", async ({
    page,
  }) => {
    // Mock successful API response
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockCoursesResponse),
      })
    })

    await page.goto("/create-quiz")
    await page.waitForLoadState("networkidle")

    // Next button should be disabled initially
    const nextButton = page.locator('button:has-text("Next")')
    await expect(nextButton).toBeDisabled()

    // Click on first course card
    const firstCourse = page.locator(
      "text=SB_ME_INF-0005 Praktisk kunstig intelligens",
    )
    await firstCourse.click()

    // Should show selection confirmation
    await expect(
      page.locator("text=Selected:").locator("strong", {
        hasText: "SB_ME_INF-0005 Praktisk kunstig intelligens",
      }),
    ).toBeVisible()

    // Next button should now be enabled
    await expect(nextButton).toBeEnabled()

    // Check for visual indication that course is selected (blue background)
    const selectedCard = page.locator('[data-testid="course-card-37823"]')
    await expect(selectedCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)",
    ) // blue.50
  })

  test("should switch course selection correctly", async ({ page }) => {
    // Mock successful API response
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockCoursesResponse),
      })
    })

    await page.goto("/create-quiz")
    await page.waitForLoadState("networkidle")

    // Select first course
    await page
      .locator("text=SB_ME_INF-0005 Praktisk kunstig intelligens")
      .click()
    await expect(
      page.locator("text=Selected:").locator("strong", {
        hasText: "SB_ME_INF-0005 Praktisk kunstig intelligens",
      }),
    ).toBeVisible()

    // Select second course
    await page.locator("text=SB_ME_INF-0006 Bruk av generativ KI").click()

    // Should update selection
    await expect(
      page.locator("text=Selected:").locator("strong", {
        hasText: "SB_ME_INF-0006 Bruk av generativ KI",
      }),
    ).toBeVisible()

    // Should not show first course as selected anymore
    await expect(
      page.locator("text=Selected:").locator("strong", {
        hasText: "SB_ME_INF-0005 Praktisk kunstig intelligens",
      }),
    ).not.toBeVisible()

    // Check visual state - first should not be selected, second should be
    const firstCard = page.locator('[data-testid="course-card-37823"]')
    const secondCard = page.locator('[data-testid="course-card-37824"]')
    await expect(firstCard).toHaveCSS("background-color", "rgb(255, 255, 255)") // white
    await expect(secondCard).toHaveCSS("background-color", "rgb(239, 246, 255)") // blue.50
  })

  test("should proceed to next step when course is selected", async ({
    page,
  }) => {
    // Mock successful API response
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockCoursesResponse),
      })
    })

    await page.goto("/create-quiz")
    await page.waitForLoadState("networkidle")

    // Select a course
    await page
      .locator("text=SB_ME_INF-0005 Praktisk kunstig intelligens")
      .click()

    // Click Next
    await page.locator('button:has-text("Next")').click()

    // Should progress to step 2
    await expect(page.locator("text=Step 2 of 3: Select Modules")).toBeVisible()
    await expect(page.locator("text=Module selection step")).toBeVisible()

    // Should show selected course in step 2
    await expect(
      page.locator(
        "text=Selected course: SB_ME_INF-0005 Praktisk kunstig intelligens",
      ),
    ).toBeVisible()

    // Should show Previous button now
    await expect(page.locator('button:has-text("Previous")')).toBeVisible()
  })

  test("should handle no teacher courses scenario", async ({ page }) => {
    // Mock empty response
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockEmptyCoursesResponse),
      })
    })

    await page.goto("/create-quiz")
    await page.waitForLoadState("networkidle")

    // Should show no courses message
    await expect(page.locator("text=No teacher courses found")).toBeVisible()
    await expect(
      page.locator(
        "text=You don't have any courses where you are enrolled as a teacher",
      ),
    ).toBeVisible()

    // Next button should remain disabled
    await expect(page.locator('button:has-text("Next")')).toBeDisabled()
  })

  test("should handle API error gracefully", async ({ page }) => {
    // Mock error response (use 500 to test generic error handling without auth redirect)
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Canvas API temporarily unavailable" }),
      })
    })

    await page.goto("/create-quiz")
    await page.waitForLoadState("networkidle")

    // Verify we're still on the create-quiz page (not redirected to login)
    await expect(page).toHaveURL("/create-quiz")

    // Should show error message (with longer timeout for reEtries)
    await expect(page.locator("text=Failed to load courses")).toBeVisible({
      timeout: 10000,
    })
    await expect(
      page.locator(
        "text=There was an error loading your Canvas courses. Please try again or",
      ),
    ).toBeVisible()

    // Next button should remain disabled
    await expect(page.locator('button:has-text("Next")')).toBeDisabled()
  })

  test("should cancel quiz creation", async ({ page }) => {
    await page.goto("/create-quiz")

    // Click Cancel button
    await page.locator('button:has-text("Cancel")').click()

    // Should navigate back to dashboard
    await expect(page).toHaveURL("/")
    await expect(page.locator("text=Hi,")).toBeVisible() // Dashboard greeting
  })

  test("should maintain course selection state across steps", async ({
    page,
  }) => {
    // Mock successful API response
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockCoursesResponse),
      })
    })

    await page.goto("/create-quiz")
    await page.waitForLoadState("networkidle")

    // Select course
    await page
      .locator("text=SB_ME_INF-0005 Praktisk kunstig intelligens")
      .click()

    // Go to step 2
    await page.locator('button:has-text("Next")').click()

    // Go to step 3
    await page.locator('button:has-text("Next")').click()
    await expect(page.locator("text=Step 3 of 3")).toBeVisible()

    // Go back to step 1
    await page.locator('button:has-text("Previous")').click()
    await page.locator('button:has-text("Previous")').click()

    // Course should still be selected
    await expect(
      page.locator("text=Selected:").locator("strong", {
        hasText: "SB_ME_INF-0005 Praktisk kunstig intelligens",
      }),
    ).toBeVisible()
  })

  test("should show correct sidebar state during quiz creation", async ({
    page,
  }) => {
    await page.goto("/create-quiz")

    // Sidebar should be visible and "Quizzes" should be active
    const sidebar = page.locator('[data-testid="sidebar"]')
    await expect(sidebar).toBeVisible()

    // Quizzes link should be highlighted/active (white background)
    const quizzesLink = page.locator('a[href="/quiz"] > div')
    await expect(quizzesLink).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    )
  })
})
