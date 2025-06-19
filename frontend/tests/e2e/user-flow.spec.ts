import { test, expect } from "@playwright/test";

test("user flow", async ({ page }) => {
  await page.goto("http://localhost:3000");

  await page.click("text=Login");
  await page.fill('input[name="username"]', "testuser");
  await page.fill('input[name="password"]', "password123");
  await page.click("text=Submit");

  await expect(page).toHaveURL("http://localhost:3000/dashboard");
  await expect(page.locator("h1")).toHaveText("Welcome, testuser");

  await page.click("text=Settings");
  await expect(page).toHaveURL("http://localhost:3000/settings");
  await expect(page.locator("h1")).toHaveText("User Settings");

  await page.click("text=Logout");
  await expect(page).toHaveURL("http://localhost:3000");
});
