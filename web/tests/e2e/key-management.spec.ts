import { expect, test } from "@playwright/test";

test("provider button reverts to needs key when API key is cleared on main page", async ({ page }) => {
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
        body: JSON.stringify({}),
      });
      return;
    }
    await route.fulfill({ status: 200, body: JSON.stringify({ ok: true }) });
  });

  await page.goto("/");
  await expect(page.getByTestId("app-loaded")).toBeVisible();

  const mistralButton = page.getByRole("button", { name: /^Mistral/i });
  await expect(mistralButton).toContainText("(needs key)");

  const apiKeysToggle = page.getByTestId("api-keys-toggle");
  await apiKeysToggle.click();

  const mistralInput = page.locator('label', { hasText: /^Mistral/ }).locator('xpath=..').locator('input');

  await mistralInput.fill("test-key");
  await expect(mistralButton).not.toContainText("(needs key)");

  await mistralInput.fill("");
  await expect(mistralButton).toContainText("(needs key)");

  // Test with spaces
  await mistralInput.fill("   ");
  await expect(mistralButton).toContainText("(needs key)");
});

test("provider button reverts to needs key when API key is cleared on settings page", async ({ page }) => {
  await page.route("**/api/key-status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ exa: false, serper: false, tavily: false, firecrawl: false, mistral: false }),
    });
  });

  let savedState = {};
  await page.route("**/api/ui-state", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(savedState),
      });
      return;
    }
    savedState = route.request().postDataJSON();
    await route.fulfill({ status: 200, body: JSON.stringify({ ok: true }) });
  });

  await page.goto("/settings");

  const mistralInput = page.locator('label', { hasText: /^Mistral$/ }).locator('xpath=../../input');
  const localKeyIndicator = page.locator('div').filter({ has: page.locator('label', { hasText: /^Mistral$/ }) }).locator('text=Local key');

  await mistralInput.fill("test-key");
  await expect(localKeyIndicator).toBeVisible();

  await mistralInput.fill("");
  await expect(localKeyIndicator).not.toBeVisible();

  // Go back to home and check button
  await page.goto("/");
  await expect(page.getByTestId("app-loaded")).toBeVisible();
  const mistralButton = page.getByRole("button", { name: /^Mistral/i });
  await expect(mistralButton).toContainText("(needs key)");
});
