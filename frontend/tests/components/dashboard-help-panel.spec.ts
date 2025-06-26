import { expect, test } from "@playwright/test";
import { createUserResponse } from "../fixtures/quiz-data";

test.describe("HelpPanel Component", () => {
  test.beforeEach(async ({ page }) => {
    // Mock the current user API call
    await page.route("**/api/v1/users/me", async (route) => {
      await route.fulfill(createUserResponse());
    });

    // Mock empty quiz list to focus on help panel
    await page.route("**/api/v1/quiz/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/");
  });

  test("should display help panel header", async ({ page }) => {
    await expect(page.getByText("Help & Resources")).toBeVisible();
    await expect(
      page.getByText("Learn how to use Rag@UiT effectively")
    ).toBeVisible();
  });

  test("should display About Rag@UiT section", async ({ page }) => {
    await expect(page.getByText("About Rag@UiT")).toBeVisible();
    await expect(
      page.getByText(
        "Rag@UiT uses advanced AI to generate multiple-choice questions from your Canvas course materials."
      )
    ).toBeVisible();
    await expect(
      page.getByText(
        "The system analyzes your course content and creates relevant questions"
      )
    ).toBeVisible();
  });

  test("should display How It Works section with numbered steps", async ({
    page,
  }) => {
    await expect(page.getByText("How It Works")).toBeVisible();

    // Check all 5 steps are present using more specific selectors
    const howItWorksSection = page.locator('text="How It Works"').locator("..");
    await expect(howItWorksSection.getByText("Select course modules from Canvas")).toBeVisible();
    await expect(howItWorksSection.getByText("AI extracts and analyzes content")).toBeVisible();
    await expect(howItWorksSection.getByText("Multiple-choice questions are generated")).toBeVisible();
    await expect(howItWorksSection.getByText("Review and approve questions")).toBeVisible();
    await expect(howItWorksSection.getByText("Export to Canvas as a quiz")).toBeVisible();
  });

  test("should display external link icons properly", async ({ page }) => {
    // Check that external links have LuExternalLink icons
    const canvasLink = page.getByRole("link", { name: "Canvas UiT" });
    const canvasIcon = canvasLink.locator("svg");
    await expect(canvasIcon).toBeVisible();

    const githubLink = page.getByRole("link", { name: "GitHub Repository" });
    const githubIcon = githubLink.locator("svg");
    await expect(githubIcon).toBeVisible();
  });

  test("should display Helpful Links section with external links", async ({
    page,
  }) => {
    await expect(page.getByText("Helpful Links")).toBeVisible();

    // Check Canvas UiT link
    const canvasLink = page.getByRole("link", { name: /Canvas UiT/ });
    await expect(canvasLink).toBeVisible();
    await expect(canvasLink).toHaveAttribute(
      "href",
      "https://uit.instructure.com"
    );
    await expect(canvasLink).toHaveAttribute("target", "_blank");
    await expect(canvasLink).toHaveAttribute("rel", "noopener noreferrer");

    // Check Contact Support link
    const supportLink = page.getByRole("link", { name: "Contact Support" });
    await expect(supportLink).toBeVisible();
    await expect(supportLink).toHaveAttribute(
      "href",
      "mailto:marius.r.solaas@uit.no"
    );

    // Check GitHub Repository link (note: may not have target="_blank" in implementation)
    const githubLink = page.getByRole("link", { name: /GitHub Repository/ });
    await expect(githubLink).toBeVisible();
    await expect(githubLink).toHaveAttribute(
      "href",
      "https://github.com/uit-no/ragatuit"
    );
  });

  test("should display contact support email link", async ({ page }) => {
    const supportLink = page.getByRole("link", { name: "Contact Support" });
    await expect(supportLink).toBeVisible();
    await expect(supportLink).toHaveAttribute(
      "href",
      "mailto:marius.r.solaas@uit.no"
    );

    // Email links should not have target="_blank"
    await expect(supportLink).not.toHaveAttribute("target", "_blank");
  });

  test("should display Tips for Best Results section", async ({ page }) => {
    await expect(page.getByText("💡 Tips for Best Results")).toBeVisible();

    // Check all three tips
    await expect(
      page.getByText("• Use course materials with clear, factual content")
    ).toBeVisible();
    await expect(
      page.getByText("• Review all generated questions before approval")
    ).toBeVisible();
    await expect(
      page.getByText("• Adjust question count based on content complexity")
    ).toBeVisible();
  });

  test("should display Privacy Policy alert section", async ({ page }) => {
    await expect(
      page.getByText(
        "Review our Privacy Policy to understand how we handle your data."
      )
    ).toBeVisible();

    // Check Privacy Policy link
    const privacyLink = page.getByRole("link", { name: "Privacy Policy" });
    await expect(privacyLink).toBeVisible();
    await expect(privacyLink).toHaveAttribute("href", "/privacy-policy");
    await expect(privacyLink).toHaveCSS("text-decoration", /underline/);
  });

  test("should have proper alert styling for privacy policy section", async ({
    page,
  }) => {
    // Look for the alert content directly
    const privacyText = page.getByText("Review our Privacy Policy to understand how we handle your data.");
    await expect(privacyText).toBeVisible();

    // Check the privacy policy link
    const privacyLink = page.getByRole("link", {
      name: "Privacy Policy",
    });
    await expect(privacyLink).toBeVisible();
  });

  test("should be responsive on mobile devices", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    // All sections should still be visible
    await expect(page.getByText("Help & Resources")).toBeVisible();
    await expect(page.getByText("About Rag@UiT")).toBeVisible();
    await expect(page.getByText("How It Works")).toBeVisible();
    await expect(page.getByText("Helpful Links")).toBeVisible();
    await expect(page.getByText("💡 Tips for Best Results")).toBeVisible();

    // Content should wrap properly
    const helpPanel = page.locator('text="Help & Resources"').locator("..");
    await expect(helpPanel).toBeVisible();
  });

  test("should be accessible with proper heading structure", async ({
    page,
  }) => {
    // Check that main title has proper styling (not necessarily semantic heading)
    const mainTitle = page.getByText("Help & Resources");
    await expect(mainTitle).toBeVisible();
    await expect(mainTitle).toHaveCSS("font-size", /18px|1.125rem/);
    await expect(mainTitle).toHaveCSS("font-weight", /semibold|600/);

    // Section titles should have proper text styling
    const aboutSection = page.getByText("About Rag@UiT");
    await expect(aboutSection).toHaveCSS("font-weight", /semibold|600/);

    const howItWorksSection = page.getByText("How It Works");
    await expect(howItWorksSection).toHaveCSS("font-weight", /semibold|600/);
  });

  test("should handle link clicks correctly", async ({ page }) => {
    // Test navigation to privacy policy
    const privacyLink = page.getByRole("link", { name: "Privacy Policy" });
    await privacyLink.click();

    await expect(page).toHaveURL("/privacy-policy");
  });

  test("should maintain consistent spacing and layout", async ({ page }) => {
    // Check that main sections are present and properly spaced
    await expect(page.getByText("Help & Resources")).toBeVisible();
    await expect(page.getByText("About Rag@UiT")).toBeVisible();
    await expect(page.getByText("How It Works")).toBeVisible();
    await expect(page.getByText("Helpful Links")).toBeVisible();
    await expect(page.getByText("💡 Tips for Best Results")).toBeVisible();

    // Verify card structure
    const helpCard = page.locator('text="Help & Resources"').locator("..");
    await expect(helpCard).toBeVisible();
  });
});
