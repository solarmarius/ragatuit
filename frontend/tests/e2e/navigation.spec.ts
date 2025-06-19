import { test, expect } from '@playwright/test';

test('navigation works correctly', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.click('text=About');
    await expect(page).toHaveURL('http://localhost:3000/about');
    await page.click('text=Home');
    await expect(page).toHaveURL('http://localhost:3000/');
});
