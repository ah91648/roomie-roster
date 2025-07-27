// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Laundry Scheduling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // First ensure we have some roommates for testing
    await page.click('text=Roommates');
    await page.waitForSelector('.roommate-manager');
    
    // Add test roommates if they don't exist
    const roommateCards = await page.locator('.roommate-card').count();
    if (roommateCards === 0) {
      await page.fill('input[placeholder="Enter roommate name"]', 'Test Roommate 1');
      await page.click('button', { hasText: 'Add Roommate' });
      await page.waitForSelector('.roommate-card');
      
      await page.fill('input[placeholder="Enter roommate name"]', 'Test Roommate 2');
      await page.click('button', { hasText: 'Add Roommate' });
      await page.waitForTimeout(500);
    }
    
    // Navigate to laundry tab
    await page.click('text=Laundry');
    await page.waitForSelector('.laundry-scheduler');
  });

  test('should display laundry scheduler interface', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('🧺 Laundry Schedule');
    await expect(page.locator('button', { hasText: 'Schedule Laundry' })).toBeVisible();
    await expect(page.locator('button', { hasText: 'Refresh' })).toBeVisible();
    
    // Check for filters
    await expect(page.locator('input[type="date"]')).toBeVisible();
    await expect(page.locator('select')).toHaveCount(3); // roommate, status, and other filters
  });

  test('should show form when Schedule Laundry is clicked', async ({ page }) => {
    await page.click('button', { hasText: 'Schedule Laundry' });
    
    // Wait for form to appear
    await page.waitForSelector('.laundry-form');
    
    // Check form elements
    await expect(page.locator('h3')).toContainText('Schedule New Laundry');
    await expect(page.locator('select[name="roommate_id"]')).toBeVisible();
    await expect(page.locator('input[name="date"]')).toBeVisible();
    await expect(page.locator('select[name="time_slot"]')).toBeVisible();
    await expect(page.locator('select[name="machine_type"]')).toBeVisible();
    await expect(page.locator('select[name="load_type"]')).toBeVisible();
    await expect(page.locator('input[name="estimated_loads"]')).toBeVisible();
    await expect(page.locator('textarea[name="notes"]')).toBeVisible();
  });

  test('should create a new laundry slot', async ({ page }) => {
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    
    // Fill out the form
    await page.selectOption('select[name="roommate_id"]', { index: 1 }); // Select first available roommate
    
    // Set date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowString = tomorrow.toISOString().split('T')[0];
    await page.fill('input[name="date"]', tomorrowString);
    
    await page.selectOption('select[name="time_slot"]', '10:00-12:00');
    await page.selectOption('select[name="machine_type"]', 'washer');
    await page.selectOption('select[name="load_type"]', 'darks');
    await page.fill('input[name="estimated_loads"]', '2');
    await page.fill('textarea[name="notes"]', 'Test laundry session');
    
    // Submit the form
    await page.click('button[type="submit"]');
    
    // Wait for the slot to appear
    await page.waitForSelector('.laundry-slot-card');
    
    // Verify the slot was created
    await expect(page.locator('.laundry-slot-card')).toContainText('10:00-12:00');
    await expect(page.locator('.laundry-slot-card')).toContainText('darks');
    await expect(page.locator('.laundry-slot-card')).toContainText('2 estimated');
    await expect(page.locator('.laundry-slot-card')).toContainText('Test laundry session');
    
    // Check that form is hidden after successful creation
    await expect(page.locator('.laundry-form')).not.toBeVisible();
  });

  test('should show validation error for incomplete form', async ({ page }) => {
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    
    // Try to submit without filling required fields
    await page.click('button[type="submit"]');
    
    // Check for error message
    await expect(page.locator('.error')).toContainText('Please fill in all required fields');
  });

  test('should detect and show conflict for overlapping time slots', async ({ page }) => {
    // Create first laundry slot
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowString = tomorrow.toISOString().split('T')[0];
    
    await page.selectOption('select[name="roommate_id"]', { index: 1 });
    await page.fill('input[name="date"]', tomorrowString);
    await page.selectOption('select[name="time_slot"]', '14:00-16:00');
    await page.selectOption('select[name="machine_type"]', 'washer');
    await page.selectOption('select[name="load_type"]', 'lights');
    await page.click('button[type="submit"]');
    
    await page.waitForSelector('.laundry-slot-card');
    
    // Try to create another slot with the same time/machine
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    
    await page.selectOption('select[name="roommate_id"]', { index: 2 }); // Different roommate
    await page.fill('input[name="date"]', tomorrowString);
    await page.selectOption('select[name="time_slot"]', '14:00-16:00'); // Same time
    await page.selectOption('select[name="machine_type"]', 'washer'); // Same machine
    await page.selectOption('select[name="load_type"]', 'darks');
    await page.click('button[type="submit"]');
    
    // Check for conflict error
    await expect(page.locator('.error')).toContainText('Time slot conflict');
  });

  test('should edit an existing laundry slot', async ({ page }) => {
    // Create a laundry slot first
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowString = tomorrow.toISOString().split('T')[0];
    
    await page.selectOption('select[name="roommate_id"]', { index: 1 });
    await page.fill('input[name="date"]', tomorrowString);
    await page.selectOption('select[name="time_slot"]', '08:00-10:00');
    await page.selectOption('select[name="machine_type"]', 'washer');
    await page.selectOption('select[name="load_type"]', 'mixed');
    await page.click('button[type="submit"]');
    
    await page.waitForSelector('.laundry-slot-card');
    
    // Click edit button
    await page.click('button', { hasText: 'Edit' });
    await page.waitForSelector('.laundry-form');
    
    // Verify form is pre-filled with existing data
    await expect(page.locator('input[name="date"]')).toHaveValue(tomorrowString);
    await expect(page.locator('select[name="time_slot"]')).toHaveValue('08:00-10:00');
    
    // Edit the load type
    await page.selectOption('select[name="load_type"]', 'delicates');
    await page.fill('textarea[name="notes"]', 'Updated notes');
    
    // Submit the edit
    await page.click('button[type="submit"]');
    
    // Verify the changes
    await expect(page.locator('.laundry-slot-card')).toContainText('delicates');
    await expect(page.locator('.laundry-slot-card')).toContainText('Updated notes');
  });

  test('should complete a laundry slot', async ({ page }) => {
    // Create a laundry slot first
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    
    const today = new Date().toISOString().split('T')[0];
    
    await page.selectOption('select[name="roommate_id"]', { index: 1 });
    await page.fill('input[name="date"]', today);
    await page.selectOption('select[name="time_slot"]', '16:00-18:00');
    await page.selectOption('select[name="machine_type"]', 'washer');
    await page.selectOption('select[name="load_type"]', 'towels');
    await page.click('button[type="submit"]');
    
    await page.waitForSelector('.laundry-slot-card');
    
    // Complete the slot - need to handle the browser dialogs
    page.on('dialog', dialog => {
      if (dialog.message().includes('How many loads')) {
        dialog.accept('3');
      } else if (dialog.message().includes('completion notes')) {
        dialog.accept('All done!');
      }
    });
    
    await page.click('button', { hasText: 'Complete' });
    
    // Wait for status to update
    await page.waitForTimeout(1000);
    
    // Verify the slot is marked as completed
    await expect(page.locator('.status-badge')).toContainText('completed');
    await expect(page.locator('.laundry-slot-card')).toContainText('3 completed');
  });

  test('should delete a laundry slot', async ({ page }) => {
    // Create a laundry slot first
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowString = tomorrow.toISOString().split('T')[0];
    
    await page.selectOption('select[name="roommate_id"]', { index: 1 });
    await page.fill('input[name="date"]', tomorrowString);
    await page.selectOption('select[name="time_slot"]', '20:00-22:00');
    await page.selectOption('select[name="machine_type"]', 'dryer');
    await page.selectOption('select[name="load_type"]', 'bedding');
    await page.click('button[type="submit"]');
    
    await page.waitForSelector('.laundry-slot-card');
    
    // Handle confirmation dialog
    page.on('dialog', dialog => dialog.accept());
    
    // Delete the slot
    await page.click('button', { hasText: 'Delete' });
    
    // Verify the slot is removed
    await page.waitForTimeout(1000);
    await expect(page.locator('.laundry-slot-card')).not.toBeVisible();
  });

  test('should filter laundry slots by date', async ({ page }) => {
    // Create slots for different dates
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    const todayString = today.toISOString().split('T')[0];
    const tomorrowString = tomorrow.toISOString().split('T')[0];
    
    // Create slot for today
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    await page.selectOption('select[name="roommate_id"]', { index: 1 });
    await page.fill('input[name="date"]', todayString);
    await page.selectOption('select[name="time_slot"]', '06:00-08:00');
    await page.selectOption('select[name="machine_type"]', 'washer');
    await page.selectOption('select[name="load_type"]', 'lights');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.laundry-slot-card');
    
    // Create slot for tomorrow
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    await page.selectOption('select[name="roommate_id"]', { index: 1 });
    await page.fill('input[name="date"]', tomorrowString);
    await page.selectOption('select[name="time_slot"]', '08:00-10:00');
    await page.selectOption('select[name="machine_type"]', 'washer');
    await page.selectOption('select[name="load_type"]', 'darks');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);
    
    // Should show both slots initially
    await expect(page.locator('.laundry-slot-card')).toHaveCount(2);
    
    // Filter by tomorrow's date
    const dateFilter = page.locator('.filters input[type="date"]');
    await dateFilter.fill(tomorrowString);
    await page.waitForTimeout(500);
    
    // Should only show tomorrow's slot
    await expect(page.locator('.laundry-slot-card')).toHaveCount(1);
    await expect(page.locator('.laundry-slot-card')).toContainText('darks');
  });

  test('should display schedule summary stats', async ({ page }) => {
    // Create a few laundry slots
    await page.click('button', { hasText: 'Schedule Laundry' });
    await page.waitForSelector('.laundry-form');
    
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowString = tomorrow.toISOString().split('T')[0];
    
    await page.selectOption('select[name="roommate_id"]', { index: 1 });
    await page.fill('input[name="date"]', tomorrowString);
    await page.selectOption('select[name="time_slot"]', '12:00-14:00');
    await page.selectOption('select[name="machine_type"]', 'washer');
    await page.selectOption('select[name="load_type"]', 'mixed');
    await page.fill('input[name="estimated_loads"]', '3');
    await page.click('button[type="submit"]');
    
    await page.waitForSelector('.laundry-slot-card');
    
    // Check schedule summary
    await expect(page.locator('.laundry-stats')).toBeVisible();
    await expect(page.locator('.stat-item')).toContainText('1'); // 1 scheduled
    await expect(page.locator('.stat-item')).toContainText('3'); // 3 total loads
  });
});