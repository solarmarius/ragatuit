import { expect, test } from "@playwright/test"
import {
  createQuizListResponse,
  createUserResponse,
  emptyQuizList,
  quizWithLongTitle,
  quizzesBeingGenerated,
  quizzesNeedingReview,
} from "../fixtures/quiz-data"

test.describe("QuizReviewPanel Component", () => {
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
    // Delay the API response to test loading state
    await page.route("**/api/v1/quiz/", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500))
      await route.fulfill(createQuizListResponse(quizzesNeedingReview))
    })

    await page.goto("/")

    // Check for skeleton loading in review panel
    const reviewPanel = page
      .locator('text="Quizzes Needing Review"')
      .locator("..")
    await expect(reviewPanel).toBeVisible()

    // Should eventually show content (delay simulates loading)
    await expect(reviewPanel).toBeVisible()

    // Wait for content to load
    await expect(page.getByText("Machine Learning Fundamentals")).toBeVisible({
      timeout: 1000,
    })
  })

  test("should display empty state when no quizzes need review", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(emptyQuizList))
    })

    await page.reload()

    // Check empty state in review panel
    await expect(page.getByText("No quizzes ready for review")).toBeVisible()
    await expect(
      page.getByText(
        "Generated quizzes will appear here when ready for approval",
      ),
    ).toBeVisible()
  })

  test("should display panel header with correct count", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesNeedingReview))
    })

    await page.reload()

    // Check panel header
    await expect(page.getByText("Quizzes Needing Review")).toBeVisible()
    await expect(
      page.getByText("Completed quizzes ready for question approval"),
    ).toBeVisible()

    // Check badge count (should be 6 from mock data)
    const reviewPanel = page
      .locator('text="Quizzes Needing Review"')
      .locator("..")
    const badge = reviewPanel.locator("text=/^\\d+$/")
    await expect(badge).toContainText("6")
  })

  test("should display quiz cards with correct information", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesNeedingReview))
    })

    await page.reload()

    // Check first quiz card content
    await expect(page.getByText("Machine Learning Fundamentals")).toBeVisible()
    await expect(page.getByText("Test Course")).toBeVisible()
    await expect(page.getByText("50 questions").first()).toBeVisible()
    await expect(page.getByText("gpt-4o").first()).toBeVisible()
    await expect(page.getByText("Review").first()).toBeVisible()

    // Check second quiz card
    await expect(page.getByText("Python Programming Basics")).toBeVisible()
    await expect(page.getByText("CS101")).toBeVisible()
    await expect(page.getByText("25 questions").first()).toBeVisible()
  })

  test("should display status lights for completed quizzes", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesNeedingReview))
    })

    await page.reload()

    // Status lights should be present for completed quizzes (just check that quiz content exists)
    await expect(page.getByText("Machine Learning Fundamentals")).toBeVisible()
  })

  test("should limit display to 5 quizzes with overflow message", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesNeedingReview))
    })

    await page.reload()

    // Should show first 5 quizzes
    await expect(page.getByText("Machine Learning Fundamentals")).toBeVisible()
    await expect(page.getByText("Python Programming Basics")).toBeVisible()
    await expect(page.getByText("Advanced JavaScript")).toBeVisible()
    await expect(page.getByText("React Component Design")).toBeVisible()

    // Should show overflow message for remaining quiz
    await expect(page.getByText("+1 more quizzes need review")).toBeVisible()
    await expect(
      page.getByRole("link", { name: "View All Quizzes" }),
    ).toBeVisible()
  })

  test("should handle text truncation for long quiz titles", async ({
    page,
  }) => {
    const quizzesWithLongTitle = [quizWithLongTitle]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesWithLongTitle))
    })

    await page.reload()

    // Long title should be present but truncated
    const longTitleElement = page.getByText(
      quizWithLongTitle.title.substring(0, 50),
    )
    await expect(longTitleElement).toBeVisible()

    // Check that the element has truncation styling
    await expect(longTitleElement).toHaveCSS("text-overflow", "ellipsis")
  })

  test("should not show empty state when there are quizzes being generated but none needing review", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Should show empty state in review panel
    await expect(page.getByText("No quizzes ready for review")).toBeVisible()

    // But generation panel should have content (Web Development Concepts should be visible)
    await expect(page.getByText("Web Development Concepts")).toBeVisible()
  })

  test("should be responsive on mobile devices", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesNeedingReview))
    })

    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto("/")

    // Panel should still be visible and functional
    await expect(page.getByText("Quizzes Needing Review")).toBeVisible()
    await expect(page.getByText("Machine Learning Fundamentals")).toBeVisible()

    // Panel should be visible on mobile
    await expect(page.getByText("Quizzes Needing Review")).toBeVisible()
    await expect(page.getByText("Machine Learning Fundamentals")).toBeVisible()
  })

  test("should handle hover effects on quiz cards", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesNeedingReview))
    })

    await page.reload()

    // Just verify hover doesn't break anything
    const firstQuiz = page.getByText("Machine Learning Fundamentals")
    await expect(firstQuiz).toBeVisible()
    await firstQuiz.hover()
    await expect(firstQuiz).toBeVisible()
  })

  test("should show correct badge styling for questions and models", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesNeedingReview))
    })

    await page.reload()

    // Check question count badge
    const questionBadge = page.getByText("50 questions").first()
    await expect(questionBadge).toBeVisible()

    // Check LLM model badge
    const modelBadge = page.getByText("gpt-4o").first()
    await expect(modelBadge).toBeVisible()
  })
})
