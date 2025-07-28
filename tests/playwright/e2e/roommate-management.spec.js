// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Roommate Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Navigate to roommates tab
    await page.click('text=Roommates');
    await page.waitForSelector('.roommate-manager');
  });

  test('should display roommate management interface', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Manage Roommates');
    await expect(page.locator('input[placeholder="Enter roommate name"]')).toBeVisible();
    await expect(page.locator('button', { hasText: 'Add Roommate' })).toBeVisible();
  });

  test('should add a new roommate', async ({ page }) => {
    const roommateNameInput = page.locator('input[placeholder="Enter roommate name"]');
    const addButton = page.locator('button', { hasText: 'Add Roommate' });
    
    // Add a new roommate
    await roommateNameInput.fill('Test User');
    await addButton.click();
    
    // Wait for the roommate to appear
    await page.waitForSelector('.roommate-card');
    
    // Verify the roommate was added
    await expect(page.locator('.roommate-name')).toContainText('Test User');
    await expect(page.locator('.roommate-points')).toContainText('Current Cycle Points: 0');
    
    // Verify the input was cleared
    await expect(roommateNameInput).toHaveValue('');
  });

  test('should edit roommate name', async ({ page }) => {
    // First add a roommate
    await page.fill('input[placeholder="Enter roommate name"]', 'Original Name');
    await page.click('button', { hasText: 'Add Roommate' });
    await page.waitForSelector('.roommate-card');
    
    // Click edit button
    await page.click('button', { hasText: 'Edit' });
    
    // Edit the name
    const editInput = page.locator('.edit-mode input');
    await editInput.clear();
    await editInput.fill('Updated Name');
    await page.click('button', { hasText: 'Save' }');
    
    // Verify the name was updated
    await expect(page.locator('.roommate-name')).toContainText('Updated Name');
  });

  test('should delete a roommate', async ({ page }) => {
    // First add a roommate
    await page.fill('input[placeholder="Enter roommate name"]', 'To Delete');
    await page.click('button', { hasText: 'Add Roommate' });
    await page.waitForSelector('.roommate-card');
    
    // Handle the confirmation dialog
    page.on('dialog', dialog => dialog.accept());
    
    // Click delete button
    await page.click('button', { hasText: 'Delete' }');
    
    // Wait for the roommate to be removed
    await page.waitForFunction(() => {
      const cards = document.querySelectorAll('.roommate-card');
      return Array.from(cards).every(card => !card.textContent.includes('To Delete'));
    });
    
    // Verify the roommate was deleted
    await expect(page.locator('.roommate-card')).not.toContainText('To Delete');
  });

  test('should display empty state when no roommates', async ({ page }) => {
    // Check if there are any existing roommates and delete them
    const deleteButtons = page.locator('button', { hasText: 'Delete' });
    const count = await deleteButtons.count();
    
    page.on('dialog', dialog => dialog.accept());
    
    for (let i = 0; i < count; i++) {
      await deleteButtons.first().click();
      await page.waitForTimeout(500);
    }
    
    // Verify empty state
    await expect(page.locator('.empty-state')).toContainText('No roommates added yet');
  });

  test('should validate empty roommate name', async ({ page }) => {
    const addButton = page.locator('button', { hasText: 'Add Roommate' });
    
    // Try to add empty name
    await addButton.click();
    
    // Should not add anything (form validation should prevent it)
    const roommateCards = page.locator('.roommate-card');
    const initialCount = await roommateCards.count();
    
    // Add whitespace only
    await page.fill('input[placeholder="Enter roommate name"]', '   ');
    await addButton.click();
    
    // Should still have the same number of cards
    await expect(roommateCards).toHaveCount(initialCount);
  });
});