import { test, expect } from '@playwright/test';

test('User Settings component should handle user input and display correct information', async ({ page }) => {
    await page.goto('/user-settings');

    const inputField = page.locator('input[name="username"]');
    await inputField.fill('testuser');

    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();

    const displayedUsername = page.locator('.username-display');
    await expect(displayedUsername).toHaveText('testuser');
});
