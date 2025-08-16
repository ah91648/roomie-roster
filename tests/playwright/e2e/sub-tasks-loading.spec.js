const { test, expect } = require('@playwright/test');

test.describe('Sub-tasks Loading', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the chores page
    await page.goto('http://localhost:3000');
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should not hang when loading sub-tasks', async ({ page }) => {
    // Look for a chore with a "Manage Sub-tasks" button
    const manageSubTasksButton = page.locator('button:has-text("Manage Sub-tasks")').first();
    
    // Check if the button exists
    if (await manageSubTasksButton.count() === 0) {
      console.log('No "Manage Sub-tasks" button found, skipping test');
      return;
    }

    // Click the "Manage Sub-tasks" button
    await manageSubTasksButton.click();

    // Wait for the sub-tasks section to appear
    await page.waitForSelector('.sub-chore-manager', { timeout: 5000 });

    // Check that loading doesn't hang for more than 15 seconds
    const loadingMessage = page.locator('.loading');
    
    // If loading message appears, it should disappear within 15 seconds
    if (await loadingMessage.count() > 0) {
      // Wait for loading to complete or timeout
      await expect(loadingMessage).toBeHidden({ timeout: 15000 });
    }

    // Verify that either sub-tasks are loaded or an error message is shown
    const subTasksContent = page.locator('.sub-chores-list, .no-sub-chores, .error-message');
    await expect(subTasksContent).toBeVisible({ timeout: 2000 });

    // Ensure no infinite loading state
    await expect(loadingMessage).toHaveCount(0);
  });

  test('should show error message if loading takes too long', async ({ page }) => {
    // Mock a slow API response to test timeout behavior
    await page.route('**/api/chores/*/sub-chores', async route => {
      // Delay the response by 12 seconds to trigger timeout
      await new Promise(resolve => setTimeout(resolve, 12000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    // Look for a chore with a "Manage Sub-tasks" button
    const manageSubTasksButton = page.locator('button:has-text("Manage Sub-tasks")').first();
    
    if (await manageSubTasksButton.count() === 0) {
      console.log('No "Manage Sub-tasks" button found, skipping test');
      return;
    }

    // Click the "Manage Sub-tasks" button
    await manageSubTasksButton.click();

    // Wait for the sub-tasks section to appear
    await page.waitForSelector('.sub-chore-manager', { timeout: 5000 });

    // Should show loading initially
    const loadingMessage = page.locator('.loading');
    await expect(loadingMessage).toBeVisible();

    // Should show timeout error message within 15 seconds
    const timeoutError = page.locator('text=Loading sub-tasks is taking longer than expected');
    await expect(timeoutError).toBeVisible({ timeout: 15000 });

    // Loading message should be gone
    await expect(loadingMessage).toBeHidden();
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Mock a network error
    await page.route('**/api/chores/*/sub-chores', async route => {
      await route.abort('failed');
    });

    // Look for a chore with a "Manage Sub-tasks" button
    const manageSubTasksButton = page.locator('button:has-text("Manage Sub-tasks")').first();
    
    if (await manageSubTasksButton.count() === 0) {
      console.log('No "Manage Sub-tasks" button found, skipping test');
      return;
    }

    // Click the "Manage Sub-tasks" button
    await manageSubTasksButton.click();

    // Wait for the sub-tasks section to appear
    await page.waitForSelector('.sub-chore-manager', { timeout: 5000 });

    // Should show error message for network failure
    const errorMessage = page.locator('.error-message');
    await expect(errorMessage).toBeVisible({ timeout: 10000 });

    // Loading message should be gone
    const loadingMessage = page.locator('.loading');
    await expect(loadingMessage).toBeHidden();
  });

  test('should allow retrying after error', async ({ page }) => {
    let requestCount = 0;
    
    // Mock first request to fail, second to succeed
    await page.route('**/api/chores/*/sub-chores', async route => {
      requestCount++;
      if (requestCount === 1) {
        await route.abort('failed');
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 1, name: 'Test sub-task' }
          ])
        });
      }
    });

    // Look for a chore with a "Manage Sub-tasks" button
    const manageSubTasksButton = page.locator('button:has-text("Manage Sub-tasks")').first();
    
    if (await manageSubTasksButton.count() === 0) {
      console.log('No "Manage Sub-tasks" button found, skipping test');
      return;
    }

    // Click the "Manage Sub-tasks" button
    await manageSubTasksButton.click();

    // Wait for error message
    const errorMessage = page.locator('.error-message');
    await expect(errorMessage).toBeVisible({ timeout: 10000 });

    // Hide sub-tasks and try again (retry mechanism)
    const hideButton = page.locator('button:has-text("Hide Sub-tasks")');
    await hideButton.click();

    // Click again to retry
    await manageSubTasksButton.click();

    // This time it should succeed
    await page.waitForSelector('.sub-chores-list', { timeout: 10000 });
    
    // Should show sub-tasks content
    const subTasksList = page.locator('.sub-chores-list');
    await expect(subTasksList).toBeVisible();

    // Error message should be gone
    await expect(errorMessage).toBeHidden();
  });

  test('should show retry button and allow retrying after timeout', async ({ page }) => {
    // Mock a slow API response that times out
    await page.route('**/api/chores/*/sub-chores', async route => {
      await new Promise(resolve => setTimeout(resolve, 10000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    const manageSubTasksButton = page.locator('button:has-text("Manage Sub-tasks")').first();
    
    if (await manageSubTasksButton.count() === 0) {
      console.log('No "Manage Sub-tasks" button found, skipping test');
      return;
    }

    await manageSubTasksButton.click();
    await page.waitForSelector('.sub-chore-manager', { timeout: 5000 });

    // Wait for timeout error
    const errorMessage = page.locator('.error-message');
    await expect(errorMessage).toBeVisible({ timeout: 15000 });

    // Check that retry button is present
    const retryButton = page.locator('button:has-text("Try Again")');
    await expect(retryButton).toBeVisible();

    // Mock successful response for retry
    await page.unroute('**/api/chores/*/sub-chores');
    await page.route('**/api/chores/*/sub-chores', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 1, name: 'Test sub-task' }
        ])
      });
    });

    // Click retry button
    await retryButton.click();

    // Should show loading during retry
    const loadingMessage = page.locator('.loading');
    await expect(loadingMessage).toBeVisible();

    // Should eventually show sub-tasks
    const subTasksList = page.locator('.sub-chores-list');
    await expect(subTasksList).toBeVisible({ timeout: 10000 });

    // Error message should be gone
    await expect(errorMessage).toBeHidden();
  });
});