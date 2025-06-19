import { test as setup } from "@playwright/test";

const authFile = "playwright/.auth/user.json";

setup("authenticate", async ({ page }) => {
  // Mock successful authentication by setting up the necessary tokens/cookies
  // This simulates a successful Canvas OAuth flow without actually going through it

  // Navigate to the app
  await page.goto("/");

  // Add authentication cookies/localStorage to simulate logged-in state
  await page.evaluate(() => {
    // Mock authentication tokens in localStorage - use the correct token name
    localStorage.setItem('access_token', 'mock_access_token_12345');
    localStorage.setItem('user_data', JSON.stringify({
      id: 'test_user_123',
      name: 'Test User',
      email: 'test@example.com'
    }));
  });

  // Reload to ensure the auth state is recognized
  await page.reload();

  // Wait for the authenticated page to load
  await page.waitForLoadState("networkidle");

  // Save signed-in state to 'playwright/.auth/user.json'
  await page.context().storageState({ path: authFile });
});
