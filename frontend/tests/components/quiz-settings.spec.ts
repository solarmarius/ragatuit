import { expect, test } from "@playwright/test";

test.describe("QuizSettingsStep Component", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to create quiz page
    await page.goto("/create-quiz");

    // Mock the courses API
    await page.route("**/api/v1/canvas/courses", async (route) => {
      await route.fulfill({
        json: [
          {
            id: 37823,
            name: "Test Course for Quiz Settings",
          },
        ],
      });
    });

    // Mock the modules API
    await page.route(
      "**/api/v1/canvas/courses/37823/modules",
      async (route) => {
        await route.fulfill({
          json: [
            {
              id: 173467,
              name: "Test Module 1",
            },
            {
              id: 173468,
              name: "Test Module 2",
            },
          ],
        });
      }
    );

    // Navigate to quiz settings step
    await page.waitForSelector('[data-testid="course-card-37823"]');
    await page.click('[data-testid="course-card-37823"]');
    await page.getByLabel("Quiz Title").fill("Settings Test Quiz");
    await page.click("button:has-text('Next')");
    await page.waitForLoadState("networkidle");
    await page.click('[data-testid="module-card-173467"]');
    await page.click("button:has-text('Next')");
    await page.waitForLoadState("networkidle");
    await page.getByText("Add Batch").first().click();
    await page.click("button:has-text('Next')");
    await page.waitForLoadState("networkidle");
  });

  test("should display both language and tone selection sections", async ({
    page,
  }) => {
    // Check that both sections are visible
    await expect(page.getByText("Quiz Language")).toBeVisible();
    await expect(page.getByText("Tone of Voice")).toBeVisible();

    // Check section descriptions
    await expect(
      page.getByText("Select the language for question generation")
    ).toBeVisible();
    await expect(
      page.getByText("Select the tone for question generation")
    ).toBeVisible();
  });

  test("should show correct default selections", async ({ page }) => {
    // English should be selected by default (blue background)
    const englishCard = page.locator('[data-testid="language-card-en"]');
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)"
    ); // blue.50

    // Academic tone should be selected by default (green background)
    const academicCard = page.locator('[data-testid="tone-card-academic"]');
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)"
    ); // green.50

    // Other options should not be selected (white background)
    const norwegianCard = page.locator('[data-testid="language-card-no"]');
    const casualCard = page.locator('[data-testid="tone-card-casual"]');
    const encouragingCard = page.locator(
      '[data-testid="tone-card-encouraging"]'
    );
    const professionalCard = page.locator(
      '[data-testid="tone-card-professional"]'
    );

    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
    await expect(casualCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
    await expect(encouragingCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
    await expect(professionalCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
  });

  test("should allow switching between language options", async ({ page }) => {
    const englishCard = page.locator('[data-testid="language-card-en"]');
    const norwegianCard = page.locator('[data-testid="language-card-no"]');

    // Initially English should be selected
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)"
    ); // blue.50
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white

    // Click Norwegian
    await norwegianCard.click();

    // Norwegian should now be selected, English deselected
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)"
    ); // blue.50
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white

    // Switch back to English
    await englishCard.click();

    // English should be selected again
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)"
    ); // blue.50
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
  });

  test("should allow switching between all tone options", async ({ page }) => {
    const academicCard = page.locator('[data-testid="tone-card-academic"]');
    const casualCard = page.locator('[data-testid="tone-card-casual"]');
    const encouragingCard = page.locator(
      '[data-testid="tone-card-encouraging"]'
    );
    const professionalCard = page.locator(
      '[data-testid="tone-card-professional"]'
    );

    // Initially academic should be selected
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)"
    ); // green.50

    // Test switching to casual
    await casualCard.click();
    await expect(casualCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)"
    ); // green.50
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white

    // Test switching to encouraging
    await encouragingCard.click();
    await expect(encouragingCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)"
    ); // green.50
    await expect(casualCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white

    // Test switching to professional
    await professionalCard.click();
    await expect(professionalCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)"
    ); // green.50
    await expect(encouragingCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white

    // Switch back to academic
    await academicCard.click();
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)"
    ); // green.50
    await expect(professionalCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
  });

  test("should display correct language option labels and descriptions", async ({
    page,
  }) => {
    // Check English option
    await expect(page.getByText("English").first()).toBeVisible();
    await expect(page.getByText("Generate questions in English")).toBeVisible();

    // Check Norwegian option
    await expect(page.getByText("Norwegian").first()).toBeVisible();
    await expect(
      page.getByText("Generate questions in Norwegian (Norsk)")
    ).toBeVisible();
  });

  test("should display correct tone option labels and descriptions", async ({
    page,
  }) => {
    // Check Academic tone
    await expect(page.getByText("Academic").first()).toBeVisible();
    await expect(
      page.getByText("Use formal academic language with precise terminology")
    ).toBeVisible();

    // Check Casual tone
    await expect(page.getByText("Casual")).toBeVisible();
    await expect(
      page.getByText(
        "Use everyday conversational language that feels approachable"
      )
    ).toBeVisible();

    // Check Encouraging tone
    await expect(page.getByText("Encouraging")).toBeVisible();
    await expect(
      page.getByText(
        "Use warm, supportive language with helpful hints embedded in questions"
      )
    ).toBeVisible();

    // Check Professional tone
    await expect(page.getByText("Professional")).toBeVisible();
    await expect(
      page.getByText(
        "Use clear, direct business language for workplace training"
      )
    ).toBeVisible();
  });

  test("should show visual feedback for language selection", async ({
    page,
  }) => {
    const englishCard = page.locator('[data-testid="language-card-en"]');
    const norwegianCard = page.locator('[data-testid="language-card-no"]');

    // Test English card styling (initially selected)
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)"
    ); // blue.50
    await expect(englishCard).toHaveCSS("border-color", "rgb(59, 130, 246)"); // blue.500

    // Test Norwegian card styling (initially unselected)
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
    await expect(norwegianCard).toHaveCSS("border-color", "rgb(228, 228, 231)"); // gray.200

    // Select Norwegian and test styling change
    await norwegianCard.click();
    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)"
    ); // blue.50
    await expect(norwegianCard).toHaveCSS("border-color", "rgb(163, 207, 255)"); // blue.500
    await expect(englishCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
  });

  test("should show visual feedback for tone selection", async ({ page }) => {
    const academicCard = page.locator('[data-testid="tone-card-academic"]');
    const casualCard = page.locator('[data-testid="tone-card-casual"]');

    // Test academic card styling (initially selected)
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)"
    ); // green.50
    await expect(academicCard).toHaveCSS("border-color", "rgb(34, 197, 94)"); // green.500

    // Test casual card styling (initially unselected)
    await expect(casualCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
    await expect(casualCard).toHaveCSS("border-color", "rgb(228, 228, 231)"); // gray.200

    // Select casual and test styling change
    await casualCard.click();
    await expect(casualCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)"
    ); // green.50
    await expect(casualCard).toHaveCSS("border-color", "rgb(134, 239, 172)"); // green.500
    await expect(academicCard).toHaveCSS(
      "background-color",
      "rgb(255, 255, 255)"
    ); // white
  });

  test("should maintain selections when form is manipulated", async ({
    page,
  }) => {
    // Make selections
    await page.locator('[data-testid="language-card-no"]').click();
    await page.locator('[data-testid="tone-card-encouraging"]').click();

    // Verify selections are maintained after some page interaction
    await page.keyboard.press("Tab"); // Navigate with keyboard
    await page.waitForTimeout(100);

    const norwegianCard = page.locator('[data-testid="language-card-no"]');
    const encouragingCard = page.locator(
      '[data-testid="tone-card-encouraging"]'
    );

    await expect(norwegianCard).toHaveCSS(
      "background-color",
      "rgb(239, 246, 255)"
    ); // blue.50
    await expect(encouragingCard).toHaveCSS(
      "background-color",
      "rgb(240, 253, 244)"
    ); // green.50
  });

  test("should display step information correctly", async ({ page }) => {
    // Check that we're on step 4 of 4
    await expect(page.getByText("Step 4 of 4")).toBeVisible();
    await expect(page.getByText("Quiz Configuration")).toBeVisible();

    // Check progress bar (should be at 100% for step 4 of 4)
    const progressBar = page.locator('[role="progressbar"]');
    await expect(progressBar).toHaveAttribute("aria-valuenow", "100");
  });
});
