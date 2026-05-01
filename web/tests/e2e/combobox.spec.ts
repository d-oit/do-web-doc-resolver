import { test, expect } from "@playwright/test";

test.describe("ProfileCombobox Keyboard Navigation", () => {
  test.beforeEach(async ({ page }) => {
    // Mock key-status and history to avoid external calls
    await page.route("**/api/key-status", (route) => route.fulfill({ body: JSON.stringify({}) }));
    await page.route("**/api/history", (route) => route.fulfill({ body: JSON.stringify({ entries: [] }) }));
    await page.route("**/api/ui-state", (route) => route.fulfill({ body: JSON.stringify({}) }));

    await page.goto("/");
    await expect(page.getByTestId("app-loaded")).toBeVisible();
  });

  test("should open dropdown on Enter", async ({ page }) => {
    const trigger = page.locator("button[aria-haspopup='listbox']").first();
    await trigger.focus();
    await page.keyboard.press("Enter");

    await expect(page.locator("[role='listbox']")).toBeVisible();
    await expect(trigger).toHaveAttribute("aria-expanded", "true");
  });

  test("should navigate options with ArrowDown/ArrowUp", async ({ page }) => {
    const trigger = page.locator("button[aria-haspopup='listbox']").first();
    await trigger.focus();
    await page.keyboard.press("Enter"); // Open

    await expect(page.locator("[role='listbox']")).toBeVisible();

    // First option (Free) should be active by default if value is free
    const firstOption = page.locator("[role='option']").first();
    await expect(firstOption).toHaveClass(/bg-accent/);

    await page.keyboard.press("ArrowDown");
    const secondOption = page.locator("[role='option']").nth(1);
    await expect(secondOption).toHaveClass(/bg-accent/);

    await page.keyboard.press("ArrowUp");
    await expect(firstOption).toHaveClass(/bg-accent/);
  });

  test("should select option on Enter", async ({ page }) => {
    const trigger = page.locator("button[aria-haspopup='listbox']").first();
    await trigger.focus();
    await page.keyboard.press("Enter"); // Open
    await page.keyboard.press("ArrowDown"); // Second option
    await page.keyboard.press("Enter");

    // Wait for the dropdown to close
    await expect(page.locator("[role='listbox']")).toBeHidden();
  });

  test("should handle Home and End keys", async ({ page }) => {
    const trigger = page.locator("button[aria-haspopup='listbox']").first();
    await trigger.focus();
    await page.keyboard.press("Enter");

    await expect(page.locator("[role='listbox']")).toBeVisible();

    await page.keyboard.press("End");
    const lastOption = page.locator("[role='option']").last();
    await expect(lastOption).toHaveClass(/bg-accent/);

    await page.keyboard.press("Home");
    const firstOption = page.locator("[role='option']").first();
    await expect(firstOption).toHaveClass(/bg-accent/);
  });
});
