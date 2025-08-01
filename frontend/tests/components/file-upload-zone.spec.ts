import { expect, test } from "@playwright/test"

test.describe("FileUploadZone Component - Basic UI Tests", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to create quiz page and get to manual module creation
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

    // Wait and navigate to module selection
    await page.waitForTimeout(1000)
    await page.waitForSelector('[data-testid="course-card-37823"]', { timeout: 5000 })
    await page.click('[data-testid="course-card-37823"]')
    await page.click("button:has-text('Next')")

    // Wait for the Add Manual Module card and click it
    await page.waitForSelector('[data-testid="add-manual-module-card"]', { timeout: 5000 })
    await page.click('[data-testid="add-manual-module-card"]')

    // Wait for dialog and select file upload method
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 })
    await page.getByRole('button', { name: 'Upload PDF File' }).click()
  })

  test("should display file upload UI elements", async ({ page }) => {
    // Check basic file upload elements are present
    await expect(page.locator("text=Upload PDF Files").first()).toBeVisible()
    await expect(page.locator("text=Module Name")).toBeVisible()
    await expect(page.locator('input[placeholder*="Enter"]')).toBeVisible()

    // Check process button exists (should be disabled initially)
    await expect(page.locator("button:has-text('Process Content')")).toBeVisible()
  })

  test("should show module name as required field", async ({ page }) => {
    // Check that required asterisk is shown
    await expect(page.locator("text=*")).toBeVisible()

    // Check module name input is present
    const nameInput = page.locator('input[placeholder*="Enter"]')
    await expect(nameInput).toBeVisible()
  })

  test("should handle basic text input in module name", async ({ page }) => {
    // Fill module name
    const nameInput = page.locator('input[placeholder*="Enter"]')
    await nameInput.fill("Test Module Name")

    // Verify the input has the value
    await expect(nameInput).toHaveValue("Test Module Name")
  })

  test("should display upload instructions", async ({ page }) => {
    // Check upload instructions are visible
    await expect(page.locator("text=Click to upload or drag and drop")).toBeVisible()
    await expect(page.locator("text=PDF files only")).toBeVisible()
  })

  test("should have dialog navigation buttons", async ({ page }) => {
    // Check that navigation buttons exist
    await expect(page.locator("button:has-text('Back')")).toBeVisible()
    await expect(page.locator("button:has-text('Cancel')").first()).toBeVisible()
    await expect(page.locator("button:has-text('Process Content')")).toBeVisible()
  })

  test("should show cancel button", async ({ page }) => {
    // Just check that cancel button is visible (functionality tested in other tests)
    await expect(page.locator("button:has-text('Cancel')").first()).toBeVisible()
  })

  test("should allow going back to method selection", async ({ page }) => {
    // Click back
    await page.click("button:has-text('Back')")

    // Should be back at method selection
    await expect(page.locator("text=How would you like to add content")).toBeVisible()
    await expect(page.locator("button:has-text('Upload PDF File')")).toBeVisible()
    await expect(page.locator("button:has-text('Enter Text Content')")).toBeVisible()
  })

  test("should disable process button when form is incomplete", async ({ page }) => {
    // Process button should be disabled initially
    const processButton = page.locator("button:has-text('Process Content')")
    await expect(processButton).toBeDisabled()

    // Fill only module name
    await page.fill('input[placeholder*="Enter"]', "Test Module")

    // Should still be disabled (no file selected)
    await expect(processButton).toBeDisabled()
  })
})
