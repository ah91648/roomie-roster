// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Google Calendar Integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Navigate to calendar settings tab
    await page.click('text=Calendar Settings');
    await page.waitForSelector('.calendar-settings');
  });

  test('should display calendar settings interface', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('📅 Google Calendar Integration');
    await expect(page.locator('button', { hasText: 'Refresh' })).toBeVisible();
    
    // Check for setup progress section
    await expect(page.locator('.setup-progress')).toBeVisible();
    await expect(page.locator('h3')).toContainText('Setup Progress');
    
    // Check for current status section
    await expect(page.locator('.current-status')).toBeVisible();
    await expect(page.locator('h3')).toContainText('Current Status');
  });

  test('should show setup progress steps', async ({ page }) => {
    // Check that all setup steps are visible
    const steps = page.locator('.progress-steps .step');
    await expect(steps).toHaveCount(4);
    
    // Check step labels
    await expect(steps.nth(0)).toContainText('Google API Dependencies');
    await expect(steps.nth(1)).toContainText('Credentials Uploaded');
    await expect(steps.nth(2)).toContainText('OAuth Authentication');
    await expect(steps.nth(3)).toContainText('Configuration Complete');
    
    // Each step should have an indicator
    const indicators = page.locator('.step-indicator');
    await expect(indicators).toHaveCount(4);
  });

  test('should show appropriate setup step based on configuration status', async ({ page }) => {
    // The setup content should show based on current configuration
    const setupContent = page.locator('.setup-content .setup-step');
    await expect(setupContent).toBeVisible();
    
    // Should show either dependencies missing, credentials upload, OAuth, or settings
    const stepTitle = setupContent.locator('h3');
    await expect(stepTitle).toBeVisible();
  });

  test('should show dependencies missing step when Google API is not available', async ({ page }) => {
    // This test assumes Google API dependencies are not installed in test environment
    const setupStep = page.locator('.setup-step');
    
    // Look for the dependencies missing step
    const warningIcon = page.locator('h3:has-text("⚠️ Missing Dependencies")');
    if (await warningIcon.isVisible()) {
      await expect(setupStep).toContainText('Google Calendar API dependencies are not installed');
      await expect(setupStep).toContainText('pip install -r requirements.txt');
    }
  });

  test('should show credentials upload step when dependencies are available but no credentials', async ({ page }) => {
    // Skip if dependencies are missing
    const dependenciesStep = page.locator('h3:has-text("Missing Dependencies")');
    if (await dependenciesStep.isVisible()) {
      test.skip();
    }
    
    const uploadStep = page.locator('h3:has-text("Upload Google API Credentials")');
    if (await uploadStep.isVisible()) {
      await expect(page.locator('.setup-step')).toContainText('Google Cloud Console');
      await expect(page.locator('.setup-step')).toContainText('Enable the Google Calendar API');
      await expect(page.locator('.setup-step')).toContainText('Create credentials');
      
      // Check for file upload button
      await expect(page.locator('label', { hasText: 'Upload Credentials JSON' })).toBeVisible();
    }
  });

  test('should show OAuth step when credentials are uploaded but not authenticated', async ({ page }) => {
    const oauthStep = page.locator('h3:has-text("Authorize Access")');
    if (await oauthStep.isVisible()) {
      await expect(page.locator('.setup-step')).toContainText('authorize RoomieRoster to access your Google Calendar');
      await expect(page.locator('button', { hasText: 'Authorize Google Calendar Access' })).toBeVisible();
    }
  });

  test('should show configuration step when fully set up', async ({ page }) => {
    const configStep = page.locator('h3:has-text("Configure Calendar Settings")');
    if (await configStep.isVisible()) {
      // Check for main enable checkbox
      await expect(page.locator('input[type="checkbox"][name="enabled"]')).toBeVisible();
      
      // When enabled, should show additional settings
      const enableCheckbox = page.locator('input[type="checkbox"][name="enabled"]');
      if (await enableCheckbox.isChecked()) {
        await expect(page.locator('select[name="default_calendar_id"]')).toBeVisible();
        await expect(page.locator('.reminder-settings')).toBeVisible();
        await expect(page.locator('input[type="checkbox"][name="reminder_settings.laundry_reminders"]')).toBeVisible();
        await expect(page.locator('input[type="checkbox"][name="reminder_settings.chore_reminders"]')).toBeVisible();
      }
    }
  });

  test('should toggle calendar integration on and off', async ({ page }) => {
    const configStep = page.locator('h3:has-text("Configure Calendar Settings")');
    if (!(await configStep.isVisible())) {
      test.skip();
    }
    
    const enableCheckbox = page.locator('input[type="checkbox"][name="enabled"]');
    const initialState = await enableCheckbox.isChecked();
    
    // Toggle the checkbox
    await enableCheckbox.click();
    
    // Verify the state changed
    await expect(enableCheckbox).toBeChecked(!initialState);
    
    if (!initialState) {
      // If we enabled it, additional settings should appear
      await expect(page.locator('select[name="default_calendar_id"]')).toBeVisible();
      await expect(page.locator('.reminder-settings')).toBeVisible();
    }
  });

  test('should save calendar configuration', async ({ page }) => {
    const configStep = page.locator('h3:has-text("Configure Calendar Settings")');
    if (!(await configStep.isVisible())) {
      test.skip();
    }
    
    // Enable calendar integration
    const enableCheckbox = page.locator('input[type="checkbox"][name="enabled"]');
    if (!(await enableCheckbox.isChecked())) {
      await enableCheckbox.click();
    }
    
    // Configure settings (if calendar dropdown has options)
    const calendarSelect = page.locator('select[name="default_calendar_id"]');
    const options = await calendarSelect.locator('option').count();
    if (options > 1) {
      await calendarSelect.selectOption({ index: 1 });
    }
    
    // Enable laundry reminders
    const laundryReminders = page.locator('input[type="checkbox"][name="reminder_settings.laundry_reminders"]');
    if (!(await laundryReminders.isChecked())) {
      await laundryReminders.click();
    }
    
    // Save configuration
    const saveButton = page.locator('button', { hasText: 'Save Configuration' });
    await saveButton.click();
    
    // Should not show error
    await expect(page.locator('.error')).not.toBeVisible();
  });

  test('should manage reminder times', async ({ page }) => {
    const configStep = page.locator('h3:has-text("Configure Calendar Settings")');
    if (!(await configStep.isVisible())) {
      test.skip();
    }
    
    // Enable calendar integration to see reminder settings
    const enableCheckbox = page.locator('input[type="checkbox"][name="enabled"]');
    if (!(await enableCheckbox.isChecked())) {
      await enableCheckbox.click();
    }
    
    // Check reminder minutes section
    const reminderMinutes = page.locator('.reminder-minutes');
    await expect(reminderMinutes).toBeVisible();
    
    // Should have default reminder times
    const reminderInputs = reminderMinutes.locator('input[type="number"]');
    const initialCount = await reminderInputs.count();
    expect(initialCount).toBeGreaterThan(0);
    
    // Add a new reminder time
    await page.click('button', { hasText: 'Add Reminder Time' });
    
    // Should have one more reminder input
    await expect(reminderMinutes.locator('input[type="number"]')).toHaveCount(initialCount + 1);
    
    // Remove a reminder time (if there are multiple)
    if (initialCount > 1) {
      const removeButtons = reminderMinutes.locator('button', { hasText: 'Remove' });
      await removeButtons.first().click();
      
      // Should have one less reminder input
      await expect(reminderMinutes.locator('input[type="number"]')).toHaveCount(initialCount);
    }
  });

  test('should display current integration status', async ({ page }) => {
    const statusSection = page.locator('.current-status');
    await expect(statusSection).toBeVisible();
    
    // Should show status items
    const statusItems = statusSection.locator('.status-item');
    await expect(statusItems).toHaveCount(3);
    
    // Check status labels
    await expect(statusItems.nth(0)).toContainText('Integration Enabled:');
    await expect(statusItems.nth(1)).toContainText('Default Calendar:');
    await expect(statusItems.nth(2)).toContainText('Laundry Reminders:');
    
    // Each status item should have a value
    const statusValues = statusSection.locator('.status-value');
    await expect(statusValues).toHaveCount(3);
  });

  test('should handle refresh action', async ({ page }) => {
    const refreshButton = page.locator('button', { hasText: 'Refresh' });
    await expect(refreshButton).toBeVisible();
    
    // Click refresh and wait for reload
    await refreshButton.click();
    await page.waitForLoadState('networkidle');
    
    // Page should still be on calendar settings
    await expect(page.locator('.calendar-settings')).toBeVisible();
    await expect(page.locator('h2')).toContainText('📅 Google Calendar Integration');
  });

  test('should show danger zone with reset option', async ({ page }) => {
    const configStep = page.locator('h3:has-text("Configure Calendar Settings")');
    if (!(await configStep.isVisible())) {
      test.skip();
    }
    
    const dangerZone = page.locator('.danger-zone');
    await expect(dangerZone).toBeVisible();
    await expect(dangerZone.locator('h4')).toContainText('Danger Zone');
    await expect(dangerZone.locator('button', { hasText: 'Reset Integration' })).toBeVisible();
    await expect(dangerZone).toContainText('remove all Google Calendar credentials');
  });

  test('should handle reset integration with confirmation', async ({ page }) => {
    const configStep = page.locator('h3:has-text("Configure Calendar Settings")');
    if (!(await configStep.isVisible())) {
      test.skip();
    }
    
    // Handle confirmation dialog by dismissing it
    page.on('dialog', dialog => dialog.dismiss());
    
    const resetButton = page.locator('button', { hasText: 'Reset Integration' });
    await resetButton.click();
    
    // Should still be on the same step since we dismissed the confirmation
    await expect(configStep).toBeVisible();
  });

  test('should validate file upload for credentials', async ({ page }) => {
    const uploadStep = page.locator('h3:has-text("Upload Google API Credentials")');
    if (!(await uploadStep.isVisible())) {
      test.skip();
    }
    
    // The file input should be hidden but present
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toHaveAttribute('style', /display:\s*none/);
    await expect(fileInput).toHaveAttribute('accept', '.json');
    
    // The label should be visible
    const uploadLabel = page.locator('label[for="credentials-upload"]');
    await expect(uploadLabel).toBeVisible();
    await expect(uploadLabel).toContainText('Upload Credentials JSON');
  });

  test('should show OAuth instructions when auth URL is generated', async ({ page }) => {
    const oauthStep = page.locator('h3:has-text("Authorize Access")');
    if (!(await oauthStep.isVisible())) {
      test.skip();
    }
    
    const authButton = page.locator('button', { hasText: 'Authorize Google Calendar Access' });
    
    // Mock the OAuth URL generation (in real test, this would trigger API call)
    // For now, just check that clicking the button doesn't cause errors
    await authButton.click();
    
    // Check that the button is still visible (may show loading state)
    await expect(authButton).toBeVisible();
  });
});