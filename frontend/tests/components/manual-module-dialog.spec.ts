import { expect, test } from "@playwright/test"

test.describe("ManualModuleDialog Component - Basic UI Tests", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to create quiz page and get to manual module dialog
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

    // Navigate to module selection
    await page.waitForTimeout(1000)
    await page.waitForSelector('[data-testid="course-card-37823"]', { timeout: 5000 })
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    // Open manual module dialog
    await page.waitForSelector('[data-testid="add-manual-module-card"]', { timeout: 5000 })
    await page.click('[data-testid="add-manual-module-card"]')

    await page.waitForSelector('[role="dialog"]', { timeout: 5000 })
  })

  test("should display initial method selection step", async ({ page }) => {
    // Check dialog title
    await expect(page.locator("text=Add Manual Module").first()).toBeVisible()

    // Check method selection prompt
    await expect(
      page.locator("text=How would you like to add content for this module?").first()
    ).toBeVisible()

    // Check both method options are visible
    await expect(page.locator("button:has-text('Upload PDF File')")).toBeVisible()
    await expect(page.locator("button:has-text('Enter Text Content')")).toBeVisible()

    // Check footer buttons
    await expect(page.locator("button:has-text('Cancel')").first()).toBeVisible()
    await expect(page.locator("button:has-text('Back')")).not.toBeVisible()
  })

  test("should navigate to file upload step when PDF option is selected", async ({ page }) => {
    // Select PDF upload method
    await page.getByRole('button', { name: 'Upload PDF File' }).click()

    // Check dialog title changes
    await expect(page.locator("text=Upload PDF File").first()).toBeVisible()

    // Check module name input appears
    await expect(page.locator('input[placeholder*="Enter"]')).toBeVisible()
    await expect(page.locator("text=Module Name")).toBeVisible()

    // Check file upload zone appears
    await expect(page.locator("text=Upload PDF File").first()).toBeVisible()

    // Check footer buttons
    await expect(page.locator("button:has-text('Back')")).toBeVisible()
    await expect(page.locator("button:has-text('Cancel')").first()).toBeVisible()
    await expect(page.locator("button:has-text('Process Content')")).toBeVisible()
  })

  test("should navigate to text input step when text option is selected", async ({ page }) => {
    // Select text input method
    await page.getByRole('button', { name: 'Enter Text Content' }).click()

    // Check dialog title changes
    await expect(page.getByRole('heading', { name: 'Enter Text Content' })).toBeVisible()

    // Check module name input appears
    await expect(page.locator('input[placeholder*="Enter"]')).toBeVisible()

    // Check text editor appears
    await expect(page.locator("textarea")).toBeVisible()

    // Check footer buttons
    await expect(page.locator("button:has-text('Back')")).toBeVisible()
    await expect(page.locator("button:has-text('Cancel')").first()).toBeVisible()
    await expect(page.locator("button:has-text('Process Content')")).toBeVisible()
  })

  test("should handle back navigation from file upload step", async ({ page }) => {
    // Navigate to file upload step
    await page.getByRole('button', { name: 'Upload PDF File' }).click()
    await expect(page.locator("text=Upload PDF File").first()).toBeVisible()

    // Go back to method selection
    await page.click("button:has-text('Back')")
    await expect(page.locator("text=Add Manual Module").first()).toBeVisible()
    await expect(
      page.locator("text=How would you like to add content for this module?").first()
    ).toBeVisible()
  })

  test("should handle back navigation from text input step", async ({ page }) => {
    // Navigate to text input step
    await page.getByRole('button', { name: 'Enter Text Content' }).click()
    await expect(page.getByRole('heading', { name: 'Enter Text Content' })).toBeVisible()

    // Go back to method selection
    await page.click("button:has-text('Back')")
    await expect(page.locator("text=Add Manual Module").first()).toBeVisible()
    await expect(
      page.locator("text=How would you like to add content for this module?").first()
    ).toBeVisible()
  })

  test("should have cancel button available", async ({ page }) => {
    // Check that cancel button is visible and enabled
    await expect(page.locator("button:has-text('Cancel')").first()).toBeVisible()
    await expect(page.locator("button:has-text('Cancel')").first()).toBeEnabled()
  })

  test("should show required field indicators", async ({ page }) => {
    // Navigate to text input step
    await page.getByRole('button', { name: 'Enter Text Content' }).click()

    // Check required asterisk is shown for module name
    await expect(page.locator("text=*")).toBeVisible()
  })

  test("should handle text input in module name field", async ({ page }) => {
    // Navigate to text input step
    await page.getByRole('button', { name: 'Enter Text Content' }).click()

    // Fill module name
    const nameInput = page.locator('input[placeholder*="Enter"]')
    await nameInput.fill("Test Module Name")

    // Verify the input has the value
    await expect(nameInput).toHaveValue("Test Module Name")
  })

  test("should handle text input in content area", async ({ page }) => {
    // Navigate to text input step
    await page.getByRole('button', { name: 'Enter Text Content' }).click()

    // Fill text content
    const textarea = page.locator("textarea")
    await textarea.fill("This is test content for the manual module.")

    // Verify the textarea has the value
    await expect(textarea).toHaveValue("This is test content for the manual module.")
  })

  test("should show word count in text editor", async ({ page }) => {
    // Navigate to text input step
    await page.getByRole('button', { name: 'Enter Text Content' }).click()

    // Initially should show 0 words
    await expect(page.locator("text=0 words")).toBeVisible()

    // Add some text
    const textarea = page.locator("textarea")
    await textarea.fill("Hello world test")

    // Should update word count
    await expect(page.locator("text=3 words")).toBeVisible()
  })

  test("should disable process button when form is incomplete", async ({ page }) => {
    // Navigate to text input step
    await page.getByRole('button', { name: 'Enter Text Content' }).click()

    // Process button should be disabled initially
    const processButton = page.locator("button:has-text('Process Content')")
    await expect(processButton).toBeDisabled()

    // Fill only module name
    await page.fill('input[placeholder*="Enter"]', "Test Module")

    // Should still be disabled (no content)
    await expect(processButton).toBeDisabled()

    // Add content
    await page.fill("textarea", "Test content")

    // Should now be enabled
    await expect(processButton).toBeEnabled()
  })

  test("should show form elements in text input step", async ({ page }) => {
    // Navigate to text input step
    await page.getByRole('button', { name: 'Enter Text Content' }).click()

    // Check that form elements are present
    await expect(page.locator('input[placeholder*="Enter"]')).toBeVisible()
    await expect(page.locator("textarea")).toBeVisible()
    await expect(page.locator("button:has-text('Process Content')")).toBeVisible()

    // Fill some data to verify functionality
    await page.fill('input[placeholder*="Enter"]', "Test Module")
    await page.fill("textarea", "Test content")

    // Data should be in the form
    await expect(page.locator('input[placeholder*="Enter"]')).toHaveValue("Test Module")
    await expect(page.locator("textarea")).toHaveValue("Test content")
  })
})
