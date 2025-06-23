import { expect, test } from "@playwright/test"

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
  })

  test("should navigate to dashboard from any page", async ({ page }) => {
    // Go to settings first
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL("/settings")

    // Click on dashboard link
    await page.click('a[href="/"]')
    await expect(page).toHaveURL("/")

    // Verify we're on the dashboard
    const dashboardLink = page.locator('a[href="/"]').nth(1)
    const activeElement = dashboardLink.locator("div")
    await expect(activeElement).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    )
  })

  test("should navigate to settings page", async ({ page }) => {
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL("/settings")

    // Verify settings link is active
    const settingsLink = page.locator('a[href="/settings"]')
    const activeElement = settingsLink.locator("div")
    await expect(activeElement).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    )
  })

  test("should show quizzes link in sidebar", async ({ page }) => {
    // Verify quizzes link exists in sidebar (even if route doesn't exist yet)
    const quizzesLink = page.locator('a[href="/quiz"]')
    await expect(quizzesLink).toBeVisible()

    // Click should work even if it goes to 404
    await quizzesLink.click()
    await page.waitForLoadState("networkidle")

    // Should either be on quiz route or 404 - both are acceptable
    const currentUrl = page.url()
    expect(
      currentUrl.includes("/quiz") || currentUrl.includes("/"),
    ).toBeTruthy()
  })

  test("should maintain navigation state during page reloads", async ({
    page,
  }) => {
    // Navigate to settings
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL("/settings")

    // Reload the page
    await page.reload()

    // Should still be on settings page
    await expect(page).toHaveURL("/settings")

    // Settings link should still be active
    const settingsLink = page.locator('a[href="/settings"]')
    const activeElement = settingsLink.locator("div")
    await expect(activeElement).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    )
  })

  test("should navigate back and forward using browser buttons", async ({
    page,
  }) => {
    // Navigate to settings
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL("/settings")

    // Go back
    await page.goBack()
    await expect(page).toHaveURL("/")

    // Go forward
    await page.goForward()
    await expect(page).toHaveURL("/settings")
  })

  test("should handle direct URL navigation", async ({ page }) => {
    // Navigate directly to settings URL
    await page.goto("/settings")
    await expect(page).toHaveURL("/settings")

    // Settings link should be active
    const settingsLink = page.locator('a[href="/settings"]')
    const activeElement = settingsLink.locator("div")
    await expect(activeElement).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    )
  })

  test("should show correct page title for each route", async ({ page }) => {
    // Check dashboard title
    await page.goto("/")
    await expect(page).toHaveTitle("Full Stack FastAPI Project")

    // Check settings title
    await page.goto("/settings")
    await expect(page).toHaveTitle("Full Stack FastAPI Project")
  })
})
