import { expect, test } from "@playwright/test"
import {
  allMockQuizzes,
  createQuizListResponse,
  createUserResponse,
  emptyQuizList,
  quizzesBeingGenerated,
  quizzesNeedingReview,
} from "../fixtures/quiz-data"

test.describe("Dashboard Layout", () => {
  test.beforeEach(async ({ page }) => {
    // Mock the current user API call
    await page.route("**/api/v1/users/me", async (route) => {
      await route.fulfill(createUserResponse())
    })
  })

  test("should display dashboard header with welcome message and create button", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(allMockQuizzes))
    })

    await page.goto("/")

    // Check header elements
    await expect(page.getByText("Hi, Test User 👋🏼")).toBeVisible()
    await expect(
      page.getByText(
        "Welcome back! Here's an overview of your quizzes and helpful resources.",
      ),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Create New Quiz" }),
    ).toBeVisible()
  })

  test("should display three-panel grid layout", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(allMockQuizzes))
    })

    await page.goto("/")

    // Check that all three panels are present
    await expect(page.getByText("Quizzes Needing Review").first()).toBeVisible()
    await expect(
      page.getByText("Quizzes Being Generated").first(),
    ).toBeVisible()
    await expect(page.getByText("Help & Resources")).toBeVisible()
  })

  test("should handle empty quiz state correctly", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(emptyQuizList))
    })

    await page.goto("/")

    // Check empty states in panels
    await expect(page.getByText("No quizzes need review")).toBeVisible()
    await expect(page.getByText("No quizzes being generated")).toBeVisible()

    // Help panel should still be visible
    await expect(page.getByText("Help & Resources")).toBeVisible()
    await expect(page.getByText("About Rag@UiT")).toBeVisible()
  })

  test("should display loading states while fetching data", async ({
    page,
  }) => {
    // Delay the API response to test loading state
    await page.route("**/api/v1/quiz/", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      await route.fulfill(createQuizListResponse(allMockQuizzes))
    })

    await page.goto("/")

    // Check for skeleton loading elements (should be visible initially)
    await expect(page.locator(".chakra-skeleton").first()).toBeVisible()

    // Wait for data to load
    await expect(page.getByText("Quizzes Needing Review").first()).toBeVisible({
      timeout: 2000,
    })
  })

  test("should handle API error gracefully", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.abort("failed")
    })

    await page.goto("/")

    // Wait for error state to appear
    await expect(page.getByText("Error Loading Dashboard")).toBeVisible({
      timeout: 10000,
    })
    await expect(
      page.getByText(
        "There was an error loading your dashboard. Please try refreshing the page.",
      ),
    ).toBeVisible()
  })

  test("should navigate to create quiz page from header button", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(allMockQuizzes))
    })

    await page.goto("/")

    await page.getByRole("link", { name: "Create New Quiz" }).click()
    await expect(page).toHaveURL("/create-quiz")
  })

  test("should be responsive on tablet view", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(allMockQuizzes))
    })

    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto("/")

    // All panels should still be visible but in different layout
    await expect(page.getByText("Quizzes Needing Review").first()).toBeVisible()
    await expect(
      page.getByText("Quizzes Being Generated").first(),
    ).toBeVisible()
    await expect(page.getByText("Help & Resources")).toBeVisible()

    // Check responsive grid behavior (should have 2 columns on tablet)
    const gridContainer = page.locator('[data-testid="dashboard-grid"]')
    await expect(gridContainer).toBeVisible()
  })

  test("should be responsive on mobile view", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(allMockQuizzes))
    })

    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto("/")

    // All panels should be stacked vertically
    await expect(page.getByText("Quizzes Needing Review").first()).toBeVisible()
    await expect(
      page.getByText("Quizzes Being Generated").first(),
    ).toBeVisible()
    await expect(page.getByText("Help & Resources")).toBeVisible()
  })

  test("should display correct quiz counts in panel badges", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(allMockQuizzes))
    })

    await page.goto("/")

    // Check review panel badge (should show 6 quizzes needing review)
    const reviewBadge = page
      .locator('text="Quizzes Needing Review"')
      .locator("..")
      .locator('[data-testid="badge"]')
    await expect(reviewBadge).toContainText("6")

    // Check generation panel badge (should show 6 quizzes being generated - includes failed ones with pending status)
    const generationBadge = page
      .locator('text="Quizzes Being Generated"')
      .locator("..")
      .locator('[data-testid="badge"]')
    await expect(generationBadge).toContainText("6")
  })

  test("should handle mixed quiz states correctly", async ({ page }) => {
    // Create mixed dataset with some completed, some processing, some failed
    const mixedQuizzes = [
      ...quizzesNeedingReview.slice(0, 2), // 2 ready for review
      ...quizzesBeingGenerated.slice(0, 3), // 3 being generated
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(mixedQuizzes))
    })

    await page.goto("/")

    // Should show correct counts - use more specific selectors to avoid conflicts
    const reviewPanelBadge = page
      .locator('text="Quizzes Needing Review"')
      .locator("..")
      .getByTestId("badge")
    await expect(reviewPanelBadge).toContainText("2")

    const generationPanelBadge = page
      .locator('text="Quizzes Being Generated"')
      .locator("..")
      .getByTestId("badge")
    await expect(generationPanelBadge).toContainText("3")

    // Both panels should have content
    await expect(page.getByText("Machine Learning Fundamentals")).toBeVisible()
    await expect(page.getByText("Database Design Principles")).toBeVisible()
  })

  test("should maintain layout consistency with container spacing", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(allMockQuizzes))
    })

    await page.goto("/")

    // Check container has correct max width and padding
    const container = page.locator('[data-testid="dashboard-container"]')
    await expect(container).toHaveCSS("max-width", /6xl|1152px/)
    await expect(container).toHaveCSS("padding-top", /2rem|32px/)
    await expect(container).toHaveCSS("padding-bottom", /2rem|32px/)
  })
})
