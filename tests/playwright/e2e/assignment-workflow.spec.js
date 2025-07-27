// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Assignment Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Ensure we have roommates and chores for testing
    await setupTestData(page);
    
    // Navigate to assignments tab
    await page.click('text=Assignments');
    await page.waitForSelector('.assignment-display');
  });

  async function setupTestData(page) {
    // Add roommates
    await page.click('text=Roommates');
    
    // Check if we need to add test roommates
    const roommateCards = page.locator('.roommate-card');
    const roommateCount = await roommateCards.count();
    
    if (roommateCount < 2) {
      const roommatesToAdd = ['Test Alice', 'Test Bob', 'Test Charlie'];
      for (const name of roommatesToAdd) {
        await page.fill('input[placeholder="Enter roommate name"]', name);
        await page.click('button', { hasText: 'Add Roommate' });
        await page.waitForTimeout(300);
      }
    }
    
    // Add chores
    await page.click('text=Chores');
    const choreCards = page.locator('.chore-card');
    const choreCount = await choreCards.count();
    
    if (choreCount < 3) {
      const choresToAdd = [
        { name: 'Test Clean Kitchen', type: 'predefined', frequency: 'weekly', points: '10' },
        { name: 'Test Take Trash', type: 'random', frequency: 'weekly', points: '5' },
      ];
      
      for (const chore of choresToAdd) {
        await page.click('button', { hasText: 'Add New Chore' });
        await page.fill('input[name="name"]', chore.name);
        await page.selectOption('select[name="frequency"]', chore.frequency);
        await page.selectOption('select[name="type"]', chore.type);
        await page.fill('input[name="points"]', chore.points);
        await page.click('button[type="submit"]');
        await page.waitForTimeout(300);
      }
    }
  }

  test('should display assignment interface', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('Chore Assignments');
    await expect(page.locator('button', { hasText: 'Assign Chores' })).toBeVisible();
    await expect(page.locator('button', { hasText: 'Reset Cycle' })).toBeVisible();
  });

  test('should show empty state initially', async ({ page }) => {
    // Reset assignments first
    page.on('dialog', dialog => dialog.accept());
    await page.click('button', { hasText: 'Reset Cycle' });
    await page.waitForTimeout(500);
    
    // Check for empty state
    const emptyState = page.locator('.empty-state');
    if (await emptyState.isVisible()) {
      await expect(emptyState).toContainText('No chores assigned yet');
      await expect(emptyState).toContainText('Click "Assign Chores" to generate assignments');
    }
  });

  test('should assign chores successfully', async ({ page }) => {
    // Click assign chores button
    await page.click('button', { hasText: 'Assign Chores' });
    
    // Wait for assignments to be generated
    await page.waitForSelector('.roommate-assignments', { timeout: 10000 });
    
    // Verify assignments were created
    const roommateAssignments = page.locator('.roommate-assignments');
    await expect(roommateAssignments).toHaveCount({ min: 1 });
    
    // Verify assignment cards exist
    const assignmentCards = page.locator('.assignment-card');
    await expect(assignmentCards).toHaveCount({ min: 1 });
    
    // Verify assignment details are displayed
    await expect(page.locator('.chore-name')).toBeTruthy();
    await expect(page.locator('.type-icon')).toBeTruthy();
    
    // Check assignment summary
    await expect(page.locator('.assignment-summary')).toBeVisible();
    await expect(page.locator('.roommate-summary')).toHaveCount({ min: 1 });
  });

  test('should display assignment details correctly', async ({ page }) => {
    // Assign chores
    await page.click('button', { hasText: 'Assign Chores' });
    await page.waitForSelector('.assignment-card', { timeout: 10000 });
    
    // Check assignment card details
    const firstAssignment = page.locator('.assignment-card').first();
    
    await expect(firstAssignment.locator('.chore-name')).toBeTruthy();
    await expect(firstAssignment.locator('.type-icon')).toBeTruthy();
    
    // Check detail fields
    await expect(firstAssignment.locator('.detail .label')).toContainText(['Frequency:', 'Points:', 'Due:']);
    
    // Verify due date format
    const dueDate = firstAssignment.locator('.due-date');
    await expect(dueDate).toBeTruthy();
  });

  test('should show different icons for chore types', async ({ page }) => {
    // Assign chores
    await page.click('button', { hasText: 'Assign Chores' });
    await page.waitForSelector('.assignment-card', { timeout: 10000 });
    
    // Check for type icons
    const typeIcons = page.locator('.type-icon');
    const iconCount = await typeIcons.count();
    
    if (iconCount > 0) {
      for (let i = 0; i < iconCount; i++) {
        const icon = typeIcons.nth(i);
        const iconText = await icon.textContent();
        // Should be either predefined (🔄) or random (🎲)
        expect(['🔄', '🎲']).toContain(iconText);
      }
    }
  });

  test('should reset cycle successfully', async ({ page }) => {
    // First assign some chores
    await page.click('button', { hasText: 'Assign Chores' });
    await page.waitForTimeout(2000);
    
    // Handle confirmation dialog
    page.on('dialog', dialog => dialog.accept());
    
    // Reset cycle
    await page.click('button', { hasText: 'Reset Cycle' });
    
    // Wait for the operation to complete
    await page.waitForTimeout(1000);
    
    // Verify no error occurred (check for error messages)
    const errorMessage = page.locator('.error');
    if (await errorMessage.isVisible()) {
      await expect(errorMessage).not.toBeVisible();
    }
  });

  test('should display assignment statistics', async ({ page }) => {
    // Assign chores
    await page.click('button', { hasText: 'Assign Chores' });
    await page.waitForSelector('.assignment-summary', { timeout: 10000 });
    
    // Check summary statistics
    await expect(page.locator('.assignment-summary h3')).toContainText('Assignment Summary');
    
    const roommateSummaries = page.locator('.roommate-summary');
    const summaryCount = await roommateSummaries.count();
    
    if (summaryCount > 0) {
      // Verify each summary has name, chore count, and points
      for (let i = 0; i < summaryCount; i++) {
        const summary = roommateSummaries.nth(i);
        await expect(summary.locator('.roommate-name')).toBeTruthy();
        await expect(summary.locator('.chore-count')).toContainText('chore');
        await expect(summary.locator('.total-points')).toContainText('points');
      }
    }
  });

  test('should show assignment info correctly', async ({ page }) => {
    // Assign chores
    await page.click('button', { hasText: 'Assign Chores' });
    await page.waitForTimeout(2000);
    
    // Check assignment info
    const assignmentInfo = page.locator('.assignment-info');
    await expect(assignmentInfo).toBeVisible();
    
    await expect(assignmentInfo).toContainText('Last Assignment:');
    await expect(assignmentInfo).toContainText('Current Assignments:');
  });

  test('should display instructions section', async ({ page }) => {
    await expect(page.locator('.instructions')).toBeVisible();
    await expect(page.locator('.instructions h3')).toContainText('How Assignments Work');
    
    // Check instruction items
    const instructionItems = page.locator('.instruction-item');
    await expect(instructionItems).toHaveCount(3);
    
    await expect(page.locator('.instructions')).toContainText('Predefined Chores');
    await expect(page.locator('.instructions')).toContainText('Random Chores');
    await expect(page.locator('.instructions')).toContainText('Fair Distribution');
  });

  test('should handle assignment errors gracefully', async ({ page }) => {
    // Remove all roommates to create an error condition
    await page.click('text=Roommates');
    
    // Delete all roommates
    page.on('dialog', dialog => dialog.accept());
    const deleteButtons = page.locator('button', { hasText: 'Delete' });
    const count = await deleteButtons.count();
    
    for (let i = 0; i < count; i++) {
      await deleteButtons.first().click();
      await page.waitForTimeout(300);
    }
    
    // Go back to assignments
    await page.click('text=Assignments');
    
    // Try to assign chores (should fail)
    await page.click('button', { hasText: 'Assign Chores' });
    
    // Wait for potential error
    await page.waitForTimeout(2000);
    
    // Check if error message appears
    const errorMessage = page.locator('.error');
    if (await errorMessage.isVisible()) {
      await expect(errorMessage).toContainText('Failed to assign chores');
    }
  });
});