import { test, expect } from "@playwright/test";

async function mockAppState(page: import("@playwright/test").Page): Promise<void> {
  await page.route("**/api/key-status", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ exa: false, serper: false, tavily: false, firecrawl: false, mistral: false }) });
  });
  await page.route("**/api/ui-state", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ sidebarCollapsed: false, showApiKeys: false, showAdvanced: false, activeProfile: "free", selectedProviders: [], maxChars: 8000, skipCache: false, deepResearch: false }) });
    } else {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
  });
}

async function waitForApp(page: import("@playwright/test").Page): Promise<void> {
  await mockAppState(page);
  await page.goto("/");
  await expect(page.getByTestId("app-loaded")).toBeVisible({ timeout: 10000 });
}

async function ensureSidebarOpen(page: import("@playwright/test").Page): Promise<void> {
  const menuButton = page.getByRole("button", { name: "Open menu" });
  if (await menuButton.isVisible()) {
    // We are in mobile/tablet view
    const backdrop = page.getByTestId("mobile-backdrop");
    if (!(await backdrop.isVisible())) {
      await menuButton.click();
      await expect(backdrop).toBeVisible({ timeout: 10000 });
    }
  }
}

async function ensureSidebarClosed(page: import("@playwright/test").Page): Promise<void> {
  const backdrop = page.getByTestId("mobile-backdrop");
  if (await backdrop.isVisible()) {
    // Sidebar is open, click backdrop to close it
    await backdrop.click({ force: true });
    await expect(backdrop).toBeHidden({ timeout: 10000 });
  }
}

function historyPanel(page: import("@playwright/test").Page) {
  return page.locator("#history-panel");
}

test.describe("History Panel", () => {
  test("history panel is collapsed by default", async ({ page }) => {
    await waitForApp(page);
    await ensureSidebarOpen(page);
    await expect(page.getByRole("button", { name: /History/ })).toBeVisible();
    await expect(page.locator("input[placeholder*='Search history']")).toBeHidden();
  });
  test("clicking History toggle opens the panel", async ({ page }) => {
    await waitForApp(page);
    await ensureSidebarOpen(page);
    await page.getByRole("button", { name: /History/ }).click();
    await expect(page.locator("input[placeholder*='Search history']")).toBeVisible();
  });
});

test.describe("History Entry Creation", () => {
  test("resolution creates history entry", async ({ page }) => {
    await page.route("**/api/resolve", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ markdown: "Test Result", provider: "jina" }) }));
    await page.route("**/api/history**", async (route) => {
      if (route.request().method() === "POST") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true, id: "1" }) });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ entries: [{ id: "1", query: "https://example.com", result: "Test Result", provider: "jina", timestamp: Date.now(), charCount: 11, resolveTime: 100 }] }) });
    });
    await waitForApp(page);
    await page.locator("input[placeholder*='URL']").fill("https://example.com");
    await page.getByRole("button", { name: "Fetch" }).click();

    // Result textarea should eventually appear
    await ensureSidebarClosed(page);
    await page.getByRole("button", { name: "Raw" }).click();
    await expect(page.getByTestId("result-textarea")).toContainText("Test Result");

    await ensureSidebarOpen(page);
    await page.getByRole("button", { name: /History/ }).click();
    await expect(historyPanel(page).locator("text=https://example.com")).toBeVisible();
  });
});

test.describe("History Search", () => {
  test("search input filters history entries", async ({ page }) => {
    await page.route("**/api/history**", async (route) => {
      const allEntries = [{ id: "1", query: "rust", result: "R", provider: "jina", timestamp: Date.now(), charCount: 1, resolveTime: 1 }, { id: "2", query: "python", result: "P", provider: "jina", timestamp: Date.now(), charCount: 1, resolveTime: 1 }];
      const q = new URL(route.request().url()).searchParams.get("q");
      const entries = q ? allEntries.filter(e => e.query.includes(q)) : allEntries;
      return route.fulfill({ status: 200, body: JSON.stringify({ entries }) });
    });
    await waitForApp(page);
    await ensureSidebarOpen(page);
    await page.getByRole("button", { name: /History/ }).click();
    await expect(page.locator("text=rust")).toBeVisible();
    await page.locator("input[placeholder*='Search history']").fill("rust");
    await expect(page.locator("text=rust")).toBeVisible();
    await expect(page.locator("text=python")).toBeHidden();
  });
});

test.describe("History Delete", () => {
  test("delete button requires confirmation", async ({ page }) => {
    let entries = [{ id: "1", query: "delete-me", result: "C", provider: "jina", timestamp: Date.now(), charCount: 1, resolveTime: 1 }];
    await page.route("**/api/history*", async (route) => {
      if (route.request().method() === "DELETE") entries = [];
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ entries }) });
    });
    await waitForApp(page);
    await ensureSidebarOpen(page);
    await page.getByRole("button", { name: /History/ }).click();
    await expect(page.locator("text=delete-me")).toBeVisible();
    const btn = page.getByLabel("Delete delete-me");
    await btn.scrollIntoViewIfNeeded();
    await btn.click({ force: true });
    await page.getByRole("button", { name: /Confirm delete/ }).click();
    await expect(page.locator("text=delete-me")).toBeHidden();
  });
});

test.describe("History Load", () => {
  test("clicking entry loads it into form", async ({ page }) => {
    await page.route("**/api/resolve", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ markdown: "Previous", provider: "jina" }) }));
    await page.route("**/api/history**", async (route) => {
      return route.fulfill({ status: 200, body: JSON.stringify({ entries: [{ id: "1", query: "https://previous.com", result: "Previous", provider: "jina", timestamp: Date.now(), charCount: 8, resolveTime: 1 }] }) });
    });
    await waitForApp(page);
    await ensureSidebarOpen(page);
    await page.getByRole("button", { name: /History/ }).click();
    await page.locator("button").filter({ hasText: "https://previous.com" }).click();

    // Sidebar should close automatically when loading from history
    const menuButton = page.getByRole("button", { name: "Open menu" });
    if (await menuButton.isVisible()) {
        await expect(page.getByTestId("mobile-backdrop")).toBeHidden({ timeout: 10000 });
    }

    await expect(page.locator("input[placeholder*='URL']")).toHaveValue("https://previous.com");
    await page.getByRole("button", { name: "Raw" }).click();
    await expect(page.getByTestId("result-textarea")).toContainText("Previous");
  });
});

test.describe("History Persistence", () => {
  test("history persists across page reloads", async ({ page }) => {
    await page.route("**/api/history**", async (route) => {
      return route.fulfill({ status: 200, body: JSON.stringify({ entries: [{ id: "1", query: "persist", result: "C", provider: "jina", timestamp: Date.now(), charCount: 1, resolveTime: 1 }] }) });
    });
    await waitForApp(page);
    await ensureSidebarOpen(page);
    await page.getByRole("button", { name: /History/ }).click();
    await expect(page.locator("text=persist")).toBeVisible();
    await page.reload();
    await expect(page.getByTestId("app-loaded")).toBeVisible();
    await ensureSidebarOpen(page);
    await page.getByRole("button", { name: /History/ }).click();
    await expect(page.locator("text=persist")).toBeVisible();
  });
});

test.describe("History Accessibility", () => {
  test("history toggle has correct aria attributes", async ({ page }) => {
    await waitForApp(page);
    await ensureSidebarOpen(page);
    const toggle = page.getByRole("button", { name: /History/ });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
  });
  test("history panel has correct id for aria-controls", async ({ page }) => {
    await waitForApp(page);
    await ensureSidebarOpen(page);
    const toggle = page.getByRole("button", { name: /History/ });
    await expect(toggle).toHaveAttribute("aria-controls", "history-panel");
    await toggle.click();
    await expect(page.locator("#history-panel")).toBeVisible();
  });
});
