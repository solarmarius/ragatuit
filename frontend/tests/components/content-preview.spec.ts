import { expect, test } from "@playwright/test"

test.describe("ContentPreview Component - Basic UI Tests", () => {
  test.beforeEach(async ({ page }) => {
    // Mock successful manual module creation to test preview step
    await page.route("**/api/v1/quiz/manual-modules/upload", async (route) => {
      await route.fulfill({
        json: {
          module_id: "manual_test123",
          name: "Test Preview Module",
          content_preview: "This is a test content preview that demonstrates how the processed text will appear to users. It includes multiple sentences to test the layout and formatting of the preview component.",
          full_content: "Full test content...",
          word_count: 1250,
          processing_metadata: {
            processing_time: 1.4,
            source: "manual_text",
          },
        },
      })
    })

    // Navigate to create quiz page and get to preview step
    await page.goto("/create-quiz")

    // Mock the courses API
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        json: [
          {
            id: 37823,
            name: "Test Course",
          },
        ],
      })
    })

    // Mock the modules API
    await page.route("**/api/v1/canvas/courses/37823/modules", async (route) => {
      await route.fulfill({
        json: [
          {
            id: 173467,
            name: "Test Module",
          },
        ],
      })
    })

    // Navigate to manual module creation and process content
    await page.waitForTimeout(1000)
    await page.waitForSelector('[data-testid="course-card-37823"]', { timeout: 5000 })
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    await page.waitForSelector('[data-testid="add-manual-module-card"]', { timeout: 5000 })
    await page.click('[data-testid="add-manual-module-card"]')

    await page.waitForSelector('[role="dialog"]', { timeout: 5000 })
    await page.getByRole('button', { name: 'Enter Text Content' }).click()

    // Fill form and process
    await page.fill('input[placeholder*="Enter"]', "Test Preview Module")
    await page.fill("textarea", "This is test content for previewing functionality")
    await page.click("button:has-text('Process Content')")

    // Wait for preview step
    await page.waitForSelector("text=Review Content", { timeout: 10000 })
  })

  test("should display content preview header", async ({ page }) => {
    await expect(page.getByText("Content Preview", { exact: true }).first()).toBeVisible()
  })

  test("should display word count", async ({ page }) => {
    await expect(page.locator("text=Word Count")).toBeVisible()
    await expect(page.locator("text=1,250")).toBeVisible()
  })

  test("should display preview content", async ({ page }) => {
    await expect(
      page.locator("text=This is a test content preview").first()
    ).toBeVisible()
  })

  test("should show Add Module button in preview step", async ({ page }) => {
    // Use more specific locator for the button in the dialog
    const dialogAddButton = page.locator('[role="dialog"] button:has-text("Add Module")')
    await expect(dialogAddButton).toBeVisible()
    await expect(dialogAddButton).toBeEnabled()
  })

  test("should allow going back from preview", async ({ page }) => {
    // Click back button
    await page.click("button:has-text('Back')")

    // Should return to text input step - use heading locator to avoid duplication
    await expect(page.getByRole('heading', { name: 'Enter Text Content' })).toBeVisible()
    await expect(page.locator("textarea")).toBeVisible()
  })

  test("should handle Add Module action", async ({ page }) => {
    // Click Add Module in the dialog
    const dialogAddButton = page.locator('[role="dialog"] button:has-text("Add Module")')
    await dialogAddButton.click()

    // Dialog should close
    await expect(page.locator('[role="dialog"]')).not.toBeVisible()
  })

  test("should display content with proper styling", async ({ page }) => {
    // Check that content area is visible
    const contentText = page.locator("text=This is a test content preview").first()
    await expect(contentText).toBeVisible()
  })

  test("should show dialog title as Review Content", async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Review Content' })).toBeVisible()
  })

  test("should have cancel button available", async ({ page }) => {
    await expect(page.locator("button:has-text('Cancel')").first()).toBeVisible()
    await expect(page.locator("button:has-text('Cancel')").first()).toBeEnabled()
  })
})

test.describe("ContentPreview Component - Word Count Formatting", () => {
  test("should format large numbers with commas", async ({ page }) => {
    // Mock API response with large word count
    await page.route("**/api/v1/quiz/manual-modules/upload", async (route) => {
      await route.fulfill({
        json: {
          module_id: "manual_large123",
          name: "Large Content Test",
          content_preview: "This is a preview of a very large document.",
          full_content: "Full large content...",
          word_count: 12345,
          processing_metadata: {},
        },
      })
    })

    // Navigate and process content
    await page.goto("/create-quiz")

    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({ json: [{ id: 37823, name: "Test Course" }] })
    })

    await page.route("**/api/v1/canvas/courses/37823/modules", async (route) => {
      await route.fulfill({ json: [{ id: 173467, name: "Test Module" }] })
    })

    await page.waitForTimeout(1000)
    await page.waitForSelector('[data-testid="course-card-37823"]', { timeout: 5000 })
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    await page.waitForSelector('[data-testid="add-manual-module-card"]', { timeout: 5000 })
    await page.click('[data-testid="add-manual-module-card"]')

    await page.waitForSelector('[role="dialog"]', { timeout: 5000 })
    await page.getByRole('button', { name: 'Enter Text Content' }).click()

    await page.fill('input[placeholder*="Enter"]', "Large Content Test")
    await page.fill("textarea", "This is content for large number testing")
    await page.click("button:has-text('Process Content')")

    await page.waitForSelector("text=Review Content", { timeout: 10000 })

    // Check that large word count is properly formatted with commas
    await expect(page.locator("text=12,345")).toBeVisible()
  })
})
