import { test, expect } from '@playwright/test';

test.describe('History Search Clear', () => {
  test.beforeEach(async ({ page }) => {
    // Need to set a history entry first or just open the panel
    await page.goto('/');
    // Open history panel
    const historyToggle = page.getByTestId('app-loaded').getByRole('button', { name: /History/i });
    await historyToggle.click();
  });

  test('should show clear button when typing in search', async ({ page }) => {
    const searchInput = page.getByPlaceholder('Search history...');
    await searchInput.fill('test');

    const clearButton = page.getByLabel('Clear search');
    await expect(clearButton).toBeVisible();
  });

  test('should clear search and refocus input when clicking clear button', async ({ page }) => {
    const searchInput = page.getByPlaceholder('Search history...');
    await searchInput.fill('test');

    const clearButton = page.getByLabel('Clear search');
    await clearButton.click();

    await expect(searchInput).toHaveValue('');
    await expect(searchInput).toBeFocused();
    await expect(clearButton).not.toBeVisible();
  });
});
