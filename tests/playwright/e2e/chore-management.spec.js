// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Chore Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Navigate to chores tab
    await page.click('text=Chores');
    await page.waitForSelector('.chore-manager');
  });

  test('should display chore management interface', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Manage Chores');
    await expect(page.locator('button', { hasText: 'Add New Chore' })).toBeVisible();
  });

  test('should show add chore form when button clicked', async ({ page }) => {
    await page.click('button', { hasText: 'Add New Chore' });
    
    await expect(page.locator('.chore-form')).toBeVisible();
    await expect(page.locator('h3')).toContainText('Add New Chore');
    await expect(page.locator('input[name="name"]')).toBeVisible();
    await expect(page.locator('select[name="frequency"]')).toBeVisible();
    await expect(page.locator('select[name="type"]')).toBeVisible();
    await expect(page.locator('input[name="points"]')).toBeVisible();
  });

  test('should add a new random chore', async ({ page }) => {
    // Open add form
    await page.click('button', { hasText: 'Add New Chore' });
    
    // Fill out the form
    await page.fill('input[name="name"]', 'Test Random Chore');
    await page.selectOption('select[name="frequency"]', 'weekly');
    await page.selectOption('select[name="type"]', 'random');
    await page.fill('input[name="points"]', '8');
    
    // Submit the form
    await page.click('button[type="submit"]');
    
    // Wait for the chore to appear
    await page.waitForSelector('.chore-card');
    
    // Verify the chore was added
    await expect(page.locator('.chore-name')).toContainText('Test Random Chore');
    await expect(page.locator('.chore-type-badge.random')).toBeVisible();
    await expect(page.locator('.value')).toContainText('Weekly');
    await expect(page.locator('.value')).toContainText('8');
  });

  test('should add a new predefined chore', async ({ page }) => {
    // Open add form
    await page.click('button', { hasText: 'Add New Chore' });
    
    // Fill out the form
    await page.fill('input[name="name"]', 'Test Predefined Chore');
    await page.selectOption('select[name="frequency"]', 'bi-weekly');
    await page.selectOption('select[name="type"]', 'predefined');
    await page.fill('input[name="points"]', '12');
    
    // Submit the form
    await page.click('button[type="submit"]');
    
    // Wait for the chore to appear
    await page.waitForSelector('.chore-card');
    
    // Verify the chore was added
    await expect(page.locator('.chore-name')).toContainText('Test Predefined Chore');
    await expect(page.locator('.chore-type-badge.predefined')).toBeVisible();
    await expect(page.locator('.value')).toContainText('Bi-weekly');
    await expect(page.locator('.value')).toContainText('12');
  });

  test('should edit an existing chore', async ({ page }) => {
    // First add a chore
    await page.click('button', { hasText: 'Add New Chore' });
    await page.fill('input[name="name"]', 'Original Chore');
    await page.selectOption('select[name="frequency"]', 'daily');
    await page.selectOption('select[name="type"]', 'random');
    await page.fill('input[name="points"]', '5');
    await page.click('button[type="submit"]');
    
    // Wait for the chore to appear
    await page.waitForSelector('.chore-card');
    
    // Click edit button
    await page.click('.chore-actions button', { hasText: 'Edit' });
    
    // Verify form is pre-filled
    await expect(page.locator('input[name="name"]')).toHaveValue('Original Chore');
    await expect(page.locator('h3')).toContainText('Edit Chore');
    
    // Update the chore
    await page.fill('input[name="name"]', 'Updated Chore');
    await page.selectOption('select[name="frequency"]', 'weekly');
    await page.fill('input[name="points"]', '10');
    
    // Submit the update
    await page.click('button[type="submit"]');
    
    // Verify the chore was updated
    await expect(page.locator('.chore-name')).toContainText('Updated Chore');
    await expect(page.locator('.value')).toContainText('Weekly');
    await expect(page.locator('.value')).toContainText('10');
  });

  test('should delete a chore', async ({ page }) => {
    // First add a chore
    await page.click('button', { hasText: 'Add New Chore' });
    await page.fill('input[name="name"]', 'Chore to Delete');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.chore-card');
    
    // Handle the confirmation dialog
    page.on('dialog', dialog => dialog.accept());
    
    // Click delete button
    await page.click('.chore-actions button', { hasText: 'Delete' });
    
    // Wait for the chore to be removed
    await page.waitForFunction(() => {
      const cards = document.querySelectorAll('.chore-card');
      return Array.from(cards).every(card => !card.textContent.includes('Chore to Delete'));
    });
    
    // Verify the chore was deleted
    await expect(page.locator('.chore-card')).not.toContainText('Chore to Delete');
  });

  test('should cancel add/edit form', async ({ page }) => {
    // Open add form
    await page.click('button', { hasText: 'Add New Chore' });
    await expect(page.locator('.chore-form')).toBeVisible();
    
    // Fill some data
    await page.fill('input[name="name"]', 'Test Chore');
    
    // Cancel the form
    await page.click('button', { hasText: 'Cancel' });
    
    // Verify form is hidden
    await expect(page.locator('.chore-form')).not.toBeVisible();
  });

  test('should validate required fields', async ({ page }) => {
    // Open add form
    await page.click('button', { hasText: 'Add New Chore' });
    
    // Try to submit empty form
    await page.click('button[type="submit"]');
    
    // Form should still be visible (validation prevents submission)
    await expect(page.locator('.chore-form')).toBeVisible();
    
    // Fill only name and try again
    await page.fill('input[name="name"]', 'Test');
    await page.fill('input[name="points"]', '0'); // Invalid points
    
    // Should still show validation error for points
    const pointsInput = page.locator('input[name="points"]');
    await expect(pointsInput).toHaveAttribute('min', '1');
  });

  test('should display chore statistics', async ({ page }) => {
    // Add some chores first
    const chores = [
      { name: 'Random Chore 1', type: 'random' },
      { name: 'Random Chore 2', type: 'random' },
      { name: 'Predefined Chore 1', type: 'predefined' },
    ];
    
    for (const chore of chores) {
      await page.click('button', { hasText: 'Add New Chore' });
      await page.fill('input[name="name"]', chore.name);
      await page.selectOption('select[name="type"]', chore.type);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(500);
    }
    
    // Check statistics
    await expect(page.locator('.stats')).toContainText('Total Chores: 8'); // 5 initial + 3 added
    await expect(page.locator('.stats')).toContainText('Predefined: 3'); // 2 initial + 1 added
    await expect(page.locator('.stats')).toContainText('Random: 5'); // 3 initial + 2 added
  });
});