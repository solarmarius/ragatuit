import { test, expect } from '@playwright/test';

test('Button renders correctly', async ({ page }) => {
    await page.goto('/'); // Adjust the URL as needed
    const button = await page.locator('button'); // Adjust the selector as needed
    await expect(button).toBeVisible();
});

test('Button functionality', async ({ page }) => {
    await page.goto('/'); // Adjust the URL as needed
    const button = await page.locator('button'); // Adjust the selector as needed
    await button.click();
    // Add assertions to verify the expected outcome after the click
});

test('Button accepts props', async ({ page }) => {
    await page.goto('/'); // Adjust the URL as needed
    const button = await page.locator('button'); // Adjust the selector as needed
    await expect(button).toHaveText('Expected Button Text'); // Adjust the expected text as needed
});
