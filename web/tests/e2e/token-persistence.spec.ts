import { test, expect, Page } from "@playwright/test";

test.describe.configure({ mode: 'serial' });

async function openSidebarIfMobile(page: Page) {
  const isMobile = (page.viewportSize()?.width || 0) < 1024;
  if (isMobile) {
    const backdrop = page.locator("div.fixed.inset-0.bg-black\\/80");
    if (!(await backdrop.isVisible())) {
      const menuButton = page.getByRole("button", { name: "Open menu" });
      await menuButton.click();
      await expect(backdrop).toBeVisible();
    }
  }
}

async function closeSidebarIfMobile(page: Page) {
  const isMobile = (page.viewportSize()?.width || 0) < 1024;
  if (isMobile) {
    await page.evaluate(() => {
      if ((window as any).__WDR_INTERNAL_STATE_SETTERS__) {
        (window as any).__WDR_INTERNAL_STATE_SETTERS__.setMobileMenuOpen(false);
      }
    });
    const backdrop = page.locator("div.fixed.inset-0.bg-black\\/80");
    await expect(backdrop).toBeHidden();
  }
}

test("token limit slider persists value across refresh", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("app-loaded")).toBeVisible({ timeout: 15000 });
  await openSidebarIfMobile(page);

  const slider = page.locator('aside input[type="range"]').first();
  const label = page.locator('aside span.text-accent').first();

  await slider.waitFor({ state: "visible" });
  await slider.fill("4000");

  await expect(label).toHaveText(/4k/i);
  await page.waitForTimeout(500);

  await page.reload();
  await expect(page.getByTestId("app-loaded")).toBeVisible({ timeout: 15000 });
  await openSidebarIfMobile(page);

  await expect(label).toHaveText(/4k/i);
  await expect(slider).toHaveValue("4000");
});

test("token limit slider persists value across navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("app-loaded")).toBeVisible({ timeout: 15000 });
  await openSidebarIfMobile(page);

  const slider = page.locator('aside input[type="range"]').first();
  const label = page.locator('aside span.text-accent').first();

  await slider.waitFor({ state: "visible" });
  await slider.fill("12000");
  await expect(label).toHaveText(/12k/i);

  await page.waitForTimeout(500);

  await closeSidebarIfMobile(page);
  await page.click('a[href="/help"]');
  await expect(page).toHaveURL(/\/help/);

  await page.click('text=← Back');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByTestId("app-loaded")).toBeVisible({ timeout: 15000 });
  await openSidebarIfMobile(page);

  await expect(label).toHaveText(/12k/i);
  await expect(slider).toHaveValue("12000");
});

test("programmatic changes are reflected in UI", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("app-loaded")).toBeVisible({ timeout: 15000 });
  await openSidebarIfMobile(page);

  const slider = page.locator('aside input[type="range"]').first();
  const label = page.locator('aside span.text-accent').first();

  await page.evaluate(() => {
    if ((window as any).__WDR_INTERNAL_STATE_SETTERS__) {
      (window as any).__WDR_INTERNAL_STATE_SETTERS__.setMaxChars(25000);
    }
  });

  await expect(label).toHaveText(/25k/i);
  await expect(slider).toHaveValue("25000");
});
