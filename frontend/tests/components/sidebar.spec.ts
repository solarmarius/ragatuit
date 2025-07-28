import { expect, test } from "@playwright/test"

test.describe("Sidebar Component", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
  })

  test("should render sidebar with logo and navigation items", async ({
    page,
  }) => {
    // Check if sidebar is visible
    const sidebar = page.locator('[data-testid="sidebar"]').first()
    await expect(sidebar).toBeVisible()

    // Check if logo is present and links to home
    const logoLink = page.locator('a[href="/"]').first()
    await expect(logoLink).toBeVisible()

    const logo = logoLink.locator("img")
    await expect(logo).toBeVisible()
    await expect(logo).toHaveAttribute("src", "/assets/images/raguitlogov4.svg")
  })

  test("should display all navigation items", async ({ page }) => {
    // Check Dashboard link
    const dashboardLink = page.locator('a[href="/"]').nth(1)
    await expect(dashboardLink).toBeVisible()
    await expect(dashboardLink).toContainText("Dashboard")

    // Check Quizzes link
    const quizzesLink = page.locator('a[href="/quizzes"]')
    await expect(quizzesLink).toBeVisible()
    await expect(quizzesLink).toContainText("Quizzes")

    // Check Settings link
    const settingsLink = page.locator('a[href="/settings"]')
    await expect(settingsLink).toBeVisible()
    await expect(settingsLink).toContainText("Settings")
  })

  test("should highlight active navigation item", async ({ page }) => {
    // Dashboard should be active on home page
    const dashboardLink = page.locator('a[href="/"]').nth(1)
    const activeElement = dashboardLink.locator("div")
    await expect(activeElement).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    )
    await expect(activeElement).toHaveCSS("color", "rgb(1, 51, 67)")
  })

  test("should navigate to different pages when clicking navigation items", async ({
    page,
  }) => {
    // Click on Settings
    const settingsLink = page.locator('a[href="/settings"]')
    await settingsLink.click()

    await expect(page).toHaveURL("/settings")

    // Settings should now be active
    const activeElement = settingsLink.locator("div")
    await expect(activeElement).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)",
    )
  })

  test("should render logout button", async ({ page }) => {
    const logoutButton = page.locator('button:has-text("Log out")')
    await expect(logoutButton).toBeVisible()
    await expect(logoutButton).toHaveText("Log out")
  })

  test("should trigger logout when logout button is clicked", async ({
    page,
  }) => {
    // Mock the logout functionality
    await page.route("**/logout", (route) => route.fulfill({ status: 200 }))

    const logoutButton = page.locator('button:has-text("Log out")')
    await logoutButton.click()

    // Should redirect to login page after logout
    await expect(page).toHaveURL("/login")
  })

  test("should have correct styling and layout", async ({ page }) => {
    const sidebar = page.locator('[data-testid="sidebar"]').first()

    // Check background color (might be converted to RGB)
    const bgColor = await sidebar.evaluate(
      (el) => getComputedStyle(el).backgroundColor,
    )
    expect(bgColor).toMatch(/rgb\(1,\s?51,\s?67\)|#013343/)

    // Check positioning
    await expect(sidebar).toHaveCSS("position", "sticky")
    await expect(sidebar).toHaveCSS("top", "0px")

    // Check minimum width
    await expect(sidebar).toHaveCSS("min-width", "150px")

    // Check height (should be full viewport height or equivalent in px)
    const height = await sidebar.evaluate((el) => getComputedStyle(el).height)
    expect(height).toMatch(/^(100vh|720px)$/)
  })

  test("should show hover effects on navigation items", async ({ page }) => {
    const quizzesLink = page.locator('a[href="/quizzes"]')
    const flexElement = quizzesLink.locator("div")

    // Hover over quizzes link
    await quizzesLink.hover()

    // Check hover state (background should change) - allow some time for hover effect
    await page.waitForTimeout(100)
    const bgColor = await flexElement.evaluate(
      (el) => getComputedStyle(el).backgroundColor,
    )
    expect(bgColor).toMatch(/rgb\(49,\s?65,\s?89\)|#314159/)
  })
})
