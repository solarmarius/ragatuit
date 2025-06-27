import { expect, test } from "@playwright/test"

test.describe("QuestionStats Component", () => {
  const mockQuizId = "123e4567-e89b-12d3-a456-426614174000"

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

    // Mock the quiz details API with default values
    await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: mockQuizId,
          title: "Test Quiz",
          canvas_course_id: 12345,
          canvas_course_name: "Test Course",
          selected_modules: '{"173467": "Module 1"}',
          question_count: 50,
          llm_model: "gpt-4o",
          llm_temperature: 0.5,
          content_extraction_status: "completed",
          llm_generation_status: "completed",
          export_status: "not_started",
          created_at: "2024-01-15T10:30:00Z",
          updated_at: "2024-01-16T14:20:00Z",
          owner_id: "user123",
        }),
      })
    })

    // Mock questions API (empty by default)
    await page.route(
      `**/api/v1/quiz/${mockQuizId}/questions`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      },
    )
  })

  // Helper function to navigate to questions tab where QuestionStats is displayed
  async function navigateToQuestionsTab(page: any) {
    await page.goto(`/quiz/${mockQuizId}`)
    await page.getByRole("tab", { name: "Questions" }).click()
  }

  test.describe("Loading State", () => {
    test("should display skeleton while stats are loading", async ({
      page,
    }) => {
      // Delay the stats response to see loading state
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await new Promise((resolve) => setTimeout(resolve, 500))
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 10, approved: 5, pending: 5 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      // Check that skeleton elements exist
      await expect(page.locator('[class*="skeleton"]').first()).toBeAttached()
    })
  })

  test.describe("Error State", () => {
    test("should display error message when stats API fails", async ({
      page,
    }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 500,
            contentType: "application/json",
            body: JSON.stringify({ detail: "Internal server error" }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      // Check for error state in the card body
      await expect(
        page.getByText("Failed to load question statistics"),
      ).toBeAttached({ timeout: 10000 })
    })
  })

  test.describe("Basic Stats Display", () => {
    test("should display progress with partial approval", async ({ page }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 20, approved: 8, pending: 12 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      // Check stats display
      await expect(page.getByText("8 of 20")).toBeAttached()
      await expect(page.getByText("40%")).toBeAttached()
      await expect(page.getByText("Question Review Progress")).toBeAttached()
    })

    test("should display correct percentage for various ratios", async ({
      page,
    }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 3, approved: 1, pending: 2 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      // 1 of 3 = 33.33%, should round to 33%
      await expect(page.getByText("1 of 3")).toBeAttached()
      await expect(page.getByText("33%")).toBeAttached()
    })

    test("should show 0% when no questions approved", async ({ page }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 10, approved: 0, pending: 10 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      await expect(page.getByText("0 of 10")).toBeAttached()
      await expect(page.getByText("0%")).toBeAttached()
    })
  })

  test.describe("Empty State", () => {
    test("should display message when no questions exist", async ({ page }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 0, approved: 0, pending: 0 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      // Check for the specific empty state text from QuestionStats component
      await expect(
        page.getByText(
          "Questions will appear here once generation is complete",
        ),
      ).toBeAttached()
    })

    test("should show 0% progress when no questions exist", async ({
      page,
    }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 0, approved: 0, pending: 0 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      await expect(page.getByText("0 of 0")).toBeAttached()
      await expect(page.getByText("0%")).toBeAttached()
    })
  })

  test.describe("All Questions Approved State", () => {
    test("should show success message and Post to Canvas button when all approved", async ({
      page,
    }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 5, approved: 5, pending: 0 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      await expect(
        page.getByText("All questions have been reviewed and approved!"),
      ).toBeAttached()
      await expect(page.getByText("Post to Canvas")).toBeAttached()
      await expect(page.getByText("100%")).toBeAttached()
    })

    test("should show export completed state with timestamp", async ({
      page,
    }) => {
      // Update quiz mock to have completed export status
      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: mockQuizId,
            title: "Test Quiz",
            canvas_course_id: 12345,
            canvas_course_name: "Test Course",
            selected_modules: '{"173467": "Module 1"}',
            question_count: 50,
            llm_model: "gpt-4o",
            llm_temperature: 0.5,
            content_extraction_status: "completed",
            llm_generation_status: "completed",
            export_status: "completed",
            exported_at: "2024-01-20T15:30:00Z",
            created_at: "2024-01-15T10:30:00Z",
            updated_at: "2024-01-16T14:20:00Z",
            owner_id: "user123",
          }),
        })
      })

      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 3, approved: 3, pending: 0 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      await expect(
        page.getByText("Quiz has been successfully exported to Canvas!"),
      ).toBeAttached()
      await expect(page.getByText("Exported on")).toBeAttached()
      await expect(page.getByText("20 January 2024")).toBeAttached()

      // Should not show Post to Canvas button
      await expect(page.getByText("Post to Canvas")).not.toBeAttached()
    })
  })

  test.describe("Canvas Export Functionality", () => {
    test("should handle successful export", async ({ page }) => {
      let exportCalled = false

      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 2, approved: 2, pending: 0 }),
          })
        },
      )

      await page.route(`**/api/v1/quiz/${mockQuizId}/export`, async (route) => {
        exportCalled = true
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ message: "Quiz export started" }),
        })
      })

      await navigateToQuestionsTab(page)

      const exportButton = page.getByText("Post to Canvas")
      await expect(exportButton).toBeAttached()

      await exportButton.click()

      // Verify the API was called
      expect(exportCalled).toBe(true)
    })

    test("should show loading state during export", async ({ page }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 1, approved: 1, pending: 0 }),
          })
        },
      )

      // Delay export response to see loading state
      await page.route(`**/api/v1/quiz/${mockQuizId}/export`, async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 200))
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ message: "Quiz export started" }),
        })
      })

      await navigateToQuestionsTab(page)

      const exportButton = page.getByText("Post to Canvas")
      await exportButton.click()

      // Button should show loading state - check if button is disabled during loading
      await expect(exportButton).toBeDisabled()
    })

    test("should handle export error", async ({ page }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 1, approved: 1, pending: 0 }),
          })
        },
      )

      await page.route(`**/api/v1/quiz/${mockQuizId}/export`, async (route) => {
        await route.fulfill({
          status: 400,
          contentType: "application/json",
          body: JSON.stringify({
            body: { detail: "Export failed: Canvas API error" },
          }),
        })
      })

      await navigateToQuestionsTab(page)

      const exportButton = page.getByText("Post to Canvas")
      await expect(exportButton).toBeAttached()
      await exportButton.click()

      // Should eventually show error state (button should be clickable again)
      await expect(exportButton).toBeEnabled({ timeout: 10000 })
    })

    test("should show processing status when export is in progress", async ({
      page,
    }) => {
      // Mock quiz with processing export status
      await page.route(`**/api/v1/quiz/${mockQuizId}`, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: mockQuizId,
            title: "Test Quiz",
            canvas_course_id: 12345,
            canvas_course_name: "Test Course",
            selected_modules: '{"173467": "Module 1"}',
            question_count: 50,
            llm_model: "gpt-4o",
            llm_temperature: 0.5,
            content_extraction_status: "completed",
            llm_generation_status: "completed",
            export_status: "processing",
            created_at: "2024-01-15T10:30:00Z",
            updated_at: "2024-01-16T14:20:00Z",
            owner_id: "user123",
          }),
        })
      })

      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 1, approved: 1, pending: 0 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      const exportButton = page.getByText("Post to Canvas")
      await expect(exportButton).toBeAttached()

      // Button should be in loading state due to processing status
      await expect(exportButton).toBeDisabled()
    })
  })

  test.describe("Progress Calculation Edge Cases", () => {
    test("should handle 100% approval correctly", async ({ page }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 15, approved: 15, pending: 0 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      await expect(page.getByText("15 of 15")).toBeAttached()
      await expect(page.getByText("100%")).toBeAttached()
    })

    test("should handle rounding for complex percentages", async ({ page }) => {
      await page.route(
        `**/api/v1/quiz/${mockQuizId}/questions/stats`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ total: 7, approved: 2, pending: 5 }),
          })
        },
      )

      await navigateToQuestionsTab(page)

      // 2/7 = 28.57%, should round to 29%
      await expect(page.getByText("2 of 7")).toBeAttached()
      await expect(page.getByText("29%")).toBeAttached()
    })
  })
})
