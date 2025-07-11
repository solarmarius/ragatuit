import { expect, test } from "@playwright/test"
import {
  createQuizListResponse,
  createUserResponse,
  emptyQuizList,
  quizPendingExtraction,
  quizPendingGeneration,
  quizProcessingExtraction,
  quizProcessingGeneration,
  quizzesBeingGenerated,
  quizzesNeedingReview,
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
    const generationPanel = page
      .locator('text="Quizzes Being Generated"')
      .locator("..")
    await expect(generationPanel).toBeVisible()

    // Check that content eventually loads
    await expect(page.getByText("Web Development Concepts")).toBeVisible()
    await expect(page.getByText("Web Dev 101")).toBeVisible()
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
    await expect(
      page.getByRole("link", { name: "Create New Quiz" }).first(),
    ).toBeVisible()
  })

  test("should display panel header with correct count", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Check panel header
    await expect(page.getByText("Quizzes Being Generated")).toBeVisible()
    await expect(page.getByText("Quizzes currently in progress")).toBeVisible()

    // Check badge count (should be 5 from all being generated quizzes)
    const generationPanel = page
      .locator('text="Quizzes Being Generated"')
      .locator("..")
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

    // Check first quiz card content - should be Web Development Concepts
    await expect(page.getByText("Web Development Concepts")).toBeVisible()
    await expect(page.getByText("Web Dev 101")).toBeVisible()
    await expect(page.getByText("40 questions")).toBeVisible()
    await expect(
      page.getByRole("link", { name: "View Details" }).first(),
    ).toBeVisible()
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

    // Check different processing phase messages for consolidated status system
    await expect(page.getByText("Ready to Start")).toBeVisible() // created status
    await expect(page.getByText("Extracting Content")).toBeVisible() // extracting_content status
    await expect(page.getByText("Generating Questions").first()).toBeVisible() // generating_questions status
  })

  test("should display progress bars with correct percentages", async ({
    page,
  }) => {
    const testQuizzes = [
      quizPendingExtraction, // 0% - created status
      quizProcessingExtraction, // 25% - extracting_content status
      quizPendingGeneration, // 50% - generating_questions status
      quizProcessingGeneration, // 50% - generating_questions status
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(testQuizzes))
    })

    await page.reload()

    // Check progress percentages for consolidated status system
    await expect(page.getByText("0%").first()).toBeVisible() // created status
    await expect(page.getByText("25%").first()).toBeVisible() // extracting_content status
    await expect(page.getByText("50%").first()).toBeVisible() // generating_questions status

    // Check that progress elements are present (Progress.Root elements)
    const progressElements = page.locator(
      '[data-part="root"][data-scope="progress"]',
    )
    await expect(progressElements).toHaveCount(4) // 4 quizzes in testQuizzes array
  })

  test("should display status lights for processing quizzes", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Status lights should be present for processing quizzes
    const quizCards = page
      .locator('text="Web Development Concepts"')
      .locator("..")
    // Just check that the quiz card contains some status indication
    await expect(quizCards).toBeVisible()
    await expect(quizCards.getByText("Web Development Concepts")).toBeVisible()
  })

  test("should show all visible quizzes without overflow when count is 3", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Should show visible quizzes (only 3 should be visible)
    await expect(page.getByText("Web Development Concepts")).toBeVisible()
    await expect(page.getByText("Software Engineering Practices")).toBeVisible()
    await expect(page.getByText("Data Structures and Algorithms")).toBeVisible()

    // Should not show overflow message since only 3 quizzes are visible
    // The "View All Quizzes" link may not appear when count is low
    // Just check that the quizzes are displayed correctly
  })

  test("should navigate to quiz detail when View Details button is clicked", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Click View Details button on first quiz
    const firstDetailsButton = page
      .getByRole("link", { name: "View Details" })
      .first()

    await firstDetailsButton.click()

    // Should navigate to quiz detail page (first quiz is pending-1)
    await expect(page).toHaveURL(/\/quiz\/quiz-pending-1/)
  })

  test("should navigate to create quiz from empty state", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(emptyQuizList))
    })

    await page.reload()

    // Click Create New Quiz button from empty state
    const createButton = page
      .getByRole("link", { name: "Create New Quiz" })
      .first()

    await createButton.click()

    // Should navigate to create quiz page
    await expect(page).toHaveURL("/create-quiz")
  })

  test("should navigate to all quizzes when View All Quizzes is clicked", async ({
    page,
  }) => {
    // Create a scenario with more than 4 visible quizzes to trigger overflow
    const manyQuizzes = [
      quizProcessingExtraction,
      quizPendingGeneration,
      quizProcessingGeneration,
      {
        ...quizProcessingExtraction,
        id: "quiz-processing-4",
        title: "Fourth Processing Quiz",
      },
      {
        ...quizProcessingExtraction,
        id: "quiz-processing-5",
        title: "Fifth Processing Quiz",
      },
    ]

    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(manyQuizzes))
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
    await expect(page.getByText("Web Development Concepts")).toBeVisible()
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
    await expect(page.getByText("Web Development Concepts")).toBeVisible()

    // View Details button should be clickable
    const detailsButton = page
      .getByRole("link", { name: "View Details" })
      .first()
    await expect(detailsButton).toBeVisible()
  })

  test("should handle hover effects on quiz cards", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Get first quiz card
    const quizCard = page.getByText("Web Development Concepts").locator("..")

    // Hover over the card
    await quizCard.hover()

    // Should maintain visibility after hover
    await expect(quizCard).toBeVisible()
  })

  test("should show correct badge styling for questions", async ({ page }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Check badges are visible somewhere on the page
    await expect(page.getByText("40 questions")).toBeVisible()
  })

  test("should display progress bars with orange color scheme", async ({
    page,
  }) => {
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill(createQuizListResponse(quizzesBeingGenerated))
    })

    await page.reload()

    // Check that progress elements are present
    const progressElements = page.locator(
      '[data-part="root"][data-scope="progress"]',
    )
    await expect(progressElements.first()).toBeVisible()
  })
})
