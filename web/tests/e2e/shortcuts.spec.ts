import { test, expect } from "@playwright/test";

async function mockAppState(page: import("@playwright/test").Page): Promise<void> {
  await page.route("**/api/key-status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ exa: false, serper: false, tavily: false, firecrawl: false, mistral: false }),
    });
  });

  await page.route("**/api/ui-state", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sidebarCollapsed: false,
          showApiKeys: false,
          showAdvanced: false,
          activeProfile: "free",
          selectedProviders: [],
          maxChars: 8000,
          skipCache: false,
          deepResearch: false,
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });
}

test.describe("Keyboard Shortcuts UX", () => {
  test("allows opening the modal via the Shortcuts header button and traps focus", async ({ page }) => {
    await mockAppState(page);
    await page.goto("/");
    await expect(page.getByTestId("app-loaded")).toBeVisible();

    // Click the Shortcuts button in the main header
    const shortcutsButton = page.getByRole("button", { name: "Show keyboard shortcuts" });
    await expect(shortcutsButton).toBeVisible();
    await shortcutsButton.click();

    // Modal should open
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute("aria-modal", "true");

    // Close button should be focused automatically
    const closeButton = page.getByRole("button", { name: "Close shortcuts" });
    await expect(closeButton).toBeFocused();

    // Focus trap test: pressing tab should wrap focus back to the close button as it is the only focusable element in the modal
    await page.keyboard.press("Tab");
    await expect(closeButton).toBeFocused();

    // Close modal
    await closeButton.click();
    await expect(dialog).toBeHidden();

    // Focus should be restored back to the Shortcuts button in the header
    await expect(shortcutsButton).toBeFocused();
  });
});
