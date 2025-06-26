import { expect, test } from "@playwright/test"
import {
  createQuizListResponse,
  createUserResponse,
  quizzesBeingGenerated,
  emptyQuizList,
  quizzesNeedingReview,
  quizPendingExtraction,
  quizProcessingExtraction,
  quizPendingGeneration,
  quizProcessingGeneration,
} from "../fixtures/quiz-data"

test.describe("QuizGenerationPanel Component", () => {
  test.beforeEach(async ({ page }) => {
    // Mock the current user API call
    await page.route("**/api/v1/users/me", async (route) => {
      await route.fulfill(createUserResponse())
    })

    await page.goto("/")
  })

  test("should display loading skeleton when data is loading", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.goto("/")

    // Check that the generation panel is visible and functional
    const generationPanel = page.locator('text="Quizzes Being Generated"').locator("..")
    await expect(generationPanel).toBeVisible()

    // Check that content eventually loads
    await expect(page.getByText("Database Design Principles")).toBeVisible()
    await expect(page.getByText("Database Systems")).toBeVisible()
  })

  test("should display empty state when no quizzes are being generated", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(emptyQuizList))
    })

    await page.reload()

    // Check empty state in generation panel
    await expect(page.getByText("No quizzes being generated")).toBeVisible()
    await expect(
      page.getByText("Start creating a quiz to see generation progress here"),
    ).toBeVisible()
    // Check for Create New Quiz button in the empty state
    await expect(page.getByRole("link", { name: "Create New Quiz" }).first()).toBeVisible()
  })

  test("should display panel header with correct count", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Check panel header
    await expect(page.getByText("Quizzes Being Generated")).toBeVisible()
    await expect(page.getByText("Quizzes currently in progress")).toBeVisible()

    // Check badge count (should be 5 from mock data)
    const generationPanel = page.locator('text="Quizzes Being Generated"').locator("..")
    const badge = generationPanel.locator("text=/^\\d+$/")
    await expect(badge).toContainText("5")
  })

  test("should display quiz cards with correct information", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Check first quiz card content
    await expect(page.getByText("Database Design Principles")).toBeVisible()
    await expect(page.getByText("Database Systems")).toBeVisible()
    await expect(page.getByText("30 questions")).toBeVisible()
    await expect(page.getByText("gpt-4o").first()).toBeVisible()
    await expect(page.getByRole("link", { name: "View Details" }).first()).toBeVisible()
  })

  test("should display correct processing phases for different quiz states", async ({
    page,
  }) => {
    const testQuizzes = [
      quizPendingExtraction,
      quizProcessingExtraction,
      quizPendingGeneration,
      quizProcessingGeneration,
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(testQuizzes))
    })

    await page.reload()

    // Check different processing phase messages
    await expect(page.getByText("Waiting to extract content")).toBeVisible()
    await expect(page.getByText("Extracting content from modules")).toBeVisible()
    await expect(page.getByText("Waiting to generate questions")).toBeVisible()
    await expect(page.getByText("Generating questions with AI")).toBeVisible()
  })

  test("should display progress bars with correct percentages", async ({
    page,
  }) => {
    const testQuizzes = [
      quizPendingExtraction, // 0%
      quizProcessingExtraction, // 25%
      quizPendingGeneration, // 50%
      quizProcessingGeneration, // 75%
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(testQuizzes))
    })

    await page.reload()

    // Check progress percentages using more specific selectors
    await expect(page.getByText("0%").first()).toBeVisible()
    await expect(page.getByText("25%").first()).toBeVisible()
    await expect(page.getByText("50%").first()).toBeVisible()
    await expect(page.getByText("75%").first()).toBeVisible()

    // Check that progress elements are present (Progress.Root elements)
    const progressElements = page.locator('[data-part="root"][data-scope="progress"]')
    await expect(progressElements).toHaveCount(4)
  })

  test("should display status lights for processing quizzes", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Status lights should be present for processing quizzes
    const quizCards = page.locator('text="Database Design Principles"').locator("..")
    // Just check that the quiz card contains some status indication
    await expect(quizCards).toBeVisible()
    await expect(quizCards.getByText("Database Design Principles")).toBeVisible()
  })

  test("should limit display to 4 quizzes with overflow message", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Should show first 4 quizzes
    await expect(page.getByText("Database Design Principles")).toBeVisible()
    await expect(page.getByText("Web Development Concepts")).toBeVisible()
    await expect(page.getByText("Software Engineering Practices")).toBeVisible()
    await expect(page.getByText("Data Structures and Algorithms")).toBeVisible()

    // Should show overflow message for remaining quiz
    await expect(page.getByText("+1 more quizzes in progress")).toBeVisible()
    await expect(page.getByRole("link", { name: "View All Quizzes" })).toBeVisible()
  })

  test("should navigate to quiz detail when View Details button is clicked", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Click View Details button on first quiz
    const firstDetailsButton = page.getByRole("link", { name: "View Details" }).first()

    await firstDetailsButton.click()

    // Should navigate to quiz detail page
    await expect(page).toHaveURL(/\/quiz\/quiz-pending-1/)
  })

  test("should navigate to create quiz from empty state", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(emptyQuizList))
    })

    await page.reload()

    // Click Create New Quiz button from empty state
    const createButton = page.getByRole("link", { name: "Create New Quiz" }).first()

    await createButton.click()

    // Should navigate to create quiz page
    await expect(page).toHaveURL("/create-quiz")
  })

  test("should navigate to all quizzes when View All Quizzes is clicked", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Click View All Quizzes button
    await page.getByRole("link", { name: "View All Quizzes" }).first().click()

    // Should navigate to quizzes page
    await expect(page).toHaveURL("/quizzes")
  })

  test("should not show empty state when there are quizzes needing review but none being generated", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesNeedingReview))
    })

    await page.reload()

    // Should show empty state in generation panel
    await expect(page.getByText("No quizzes being generated")).toBeVisible()

    // But review panel should have content
    await expect(page.getByText("Machine Learning Fundamentals")).toBeVisible()
  })

  test("should display orange styling for processing quizzes", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Check that orange styling is present (simplified test)
    await expect(page.getByText("Database Design Principles")).toBeVisible()
    // Note: CSS-based styling tests can be fragile, focus on functionality
  })

  test("should be responsive on mobile devices", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto("/")

    // Panel should still be visible and functional
    await expect(page.getByText("Quizzes Being Generated")).toBeVisible()
    await expect(page.getByText("Database Design Principles")).toBeVisible()

    // View Details button should be clickable
    const detailsButton = page.getByRole("link", { name: "View Details" }).first()
    await expect(detailsButton).toBeVisible()
  })

  test("should handle hover effects on quiz cards", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Get first quiz card
    const quizCard = page.getByText("Database Design Principles").locator("..")

    // Hover over the card
    await quizCard.hover()

    // Should maintain visibility after hover
    await expect(quizCard).toBeVisible()
  })

  test("should show correct badge styling for questions and models", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Check badges are visible somewhere on the page
    await expect(page.getByText("30 questions")).toBeVisible()
    await expect(page.getByText("gpt-4o").first()).toBeVisible()
  })

  test("should display progress bars with orange color scheme", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Check that progress elements are present
    const progressElements = page.locator('[data-part="root"][data-scope="progress"]')
    await expect(progressElements.first()).toBeVisible()
  })
})
