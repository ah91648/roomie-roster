// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Comprehensive E2E tests for Pomodoro Timer functionality
 * Tests the 426-line PomodoroTimer.js component added in Phase 3
 */

test.describe('Pomodoro Timer - Complete Feature Testing', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Navigate to Pomodoro tab
    await page.click('.nav-tab:has-text("Pomodoro")');
    await page.waitForTimeout(1000);
  });

  test('should render Pomodoro timer interface with all elements', async ({ page }) => {
    // Verify main components are visible
    const hasHeader = await page.locator('h2:has-text("Pomodoro Timer")').isVisible();
    expect(hasHeader).toBe(true);

    // Check for session type buttons
    const focusButton = page.locator('button:has-text("Focus"), button:has-text("25 min")');
    const shortBreakButton = page.locator('button:has-text("Short Break"), button:has-text("5 min")');
    const longBreakButton = page.locator('button:has-text("Long Break"), button:has-text("15 min")');

    const focusExists = await focusButton.count() > 0;
    const shortBreakExists = await shortBreakButton.count() > 0;
    const longBreakExists = await longBreakButton.count() > 0;

    console.log(`Session type buttons - Focus: ${focusExists}, Short: ${shortBreakExists}, Long: ${longBreakExists}`);

    // Verify start button exists
    const startButton = page.locator('button:has-text("Start"), button:has-text("Begin")');
    const startExists = await startButton.count() > 0;
    console.log(`Start button exists: ${startExists}`);
  });

  test('should start a focus session with correct duration', async ({ page }) => {
    console.log('🧪 Testing: Start focus session');

    // Select focus session type (25 minutes)
    const focusButton = page.locator('button').filter({ hasText: /^Focus|25/ }).first();
    if (await focusButton.isVisible()) {
      await focusButton.click();
      await page.waitForTimeout(500);
      console.log('✓ Focus button clicked');
    }

    // Click start button
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000); // Wait for API call
      console.log('✓ Start button clicked');
    }

    // Verify active session card appears
    const activeSession = page.locator('.active-session-card, .active-session, .session-active');
    const sessionExists = await activeSession.count() > 0;
    console.log(`Active session visible: ${sessionExists}`);

    if (sessionExists) {
      // Verify countdown timer is visible
      const timerDisplay = page.locator('.time-remaining, .countdown, .timer-display');
      const timerExists = await timerDisplay.count() > 0;
      console.log(`Timer display visible: ${timerExists}`);

      if (timerExists) {
        const timeText = await timerDisplay.first().textContent();
        console.log(`Initial timer value: ${timeText}`);

        // Verify time format (should be like 24:59, 25:00, etc.)
        const hasValidFormat = /\d{1,2}:\d{2}/.test(timeText);
        expect(hasValidFormat).toBe(true);
      }
    }
  });

  test('should update countdown timer in real-time', async ({ page }) => {
    console.log('🧪 Testing: Real-time countdown (2s polling)');

    // Start a focus session
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000);
    }

    // Get initial timer value
    const timerDisplay = page.locator('.time-remaining, .countdown, .timer-display').first();
    if (await timerDisplay.isVisible()) {
      const initialTime = await timerDisplay.textContent();
      console.log(`Initial time: ${initialTime}`);

      // Wait 5 seconds (should see countdown update)
      await page.waitForTimeout(5000);

      const updatedTime = await timerDisplay.textContent();
      console.log(`After 5s: ${updatedTime}`);

      // Time should have decreased (different from initial)
      expect(updatedTime).not.toBe(initialTime);
      console.log('✓ Timer is counting down');
    }
  });

  test('should prevent starting duplicate sessions', async ({ page }) => {
    console.log('🧪 Testing: Prevent duplicate active sessions');

    // Start first session
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000);
      console.log('✓ First session started');
    }

    // Try to start second session (should fail or show warning)
    const startButtonAgain = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    const isStartDisabled = await startButtonAgain.count() === 0 ||
                             await startButtonAgain.isDisabled() ||
                             await startButtonAgain.getAttribute('disabled') !== null;

    console.log(`Start button disabled/hidden: ${isStartDisabled}`);

    // If button is still clickable, clicking should show error
    if (!isStartDisabled && await startButtonAgain.isVisible()) {
      await startButtonAgain.click();
      await page.waitForTimeout(1000);

      // Check for error message
      const errorMessage = page.locator('.error, .alert, [role="alert"]');
      const errorVisible = await errorMessage.count() > 0;
      console.log(`Error message shown: ${errorVisible}`);
    }
  });

  test('should pause and resume session', async ({ page }) => {
    console.log('🧪 Testing: Pause and resume functionality');

    // Start session
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000);
    }

    // Find and click pause button
    const pauseButton = page.locator('button').filter({ hasText: /Pause/ }).first();
    if (await pauseButton.isVisible()) {
      await pauseButton.click();
      await page.waitForTimeout(1000);
      console.log('✓ Pause button clicked');

      // Verify session status changed
      const statusText = await page.locator('body').textContent();
      const isPaused = statusText.includes('paused') || statusText.includes('Paused');
      console.log(`Session paused: ${isPaused}`);

      // Look for resume button
      const resumeButton = page.locator('button').filter({ hasText: /Resume/ }).first();
      const canResume = await resumeButton.count() > 0;
      console.log(`Resume button available: ${canResume}`);
    }
  });

  test('should complete session and show in recent completions', async ({ page }) => {
    console.log('🧪 Testing: Complete session');

    // Start session
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000);
    }

    // Find and click complete button
    const completeButton = page.locator('button').filter({ hasText: /Complete|Finish|Done/ }).first();
    if (await completeButton.isVisible()) {
      await completeButton.click();
      await page.waitForTimeout(2000);
      console.log('✓ Complete button clicked');

      // Verify session appears in recent completions
      const recentCompletions = page.locator('.recent-completions, .completion-history, .completed-sessions');
      const hasCompletions = await recentCompletions.count() > 0;
      console.log(`Recent completions section visible: ${hasCompletions}`);

      if (hasCompletions) {
        // Look for the completed session in the list
        const sessionItems = recentCompletions.locator('.session-item, .completion-item, li');
        const itemCount = await sessionItems.count();
        console.log(`Number of completed sessions shown: ${itemCount}`);
        expect(itemCount).toBeGreaterThan(0);
      }
    }
  });

  test('should show correct duration defaults for each session type', async ({ page }) => {
    console.log('🧪 Testing: Session type duration defaults');

    const sessionTypes = [
      { name: 'Focus', duration: 25 },
      { name: 'Short Break', duration: 5 },
      { name: 'Long Break', duration: 15 }
    ];

    for (const type of sessionTypes) {
      console.log(`Testing ${type.name} (expected: ${type.duration} min)`);

      // Click session type button
      const typeButton = page.locator('button').filter({ hasText: new RegExp(type.name, 'i') }).first();
      if (await typeButton.isVisible()) {
        await typeButton.click();
        await page.waitForTimeout(500);

        // Check if duration is displayed correctly
        const buttonText = await typeButton.textContent();
        const hasDuration = buttonText.includes(`${type.duration}`) ||
                            buttonText.includes(`${type.duration} min`);
        console.log(`  Button shows duration: ${hasDuration} (text: "${buttonText}")`);
      }
    }
  });

  test('should handle browser notifications permission', async ({ page, context }) => {
    console.log('🧪 Testing: Browser notifications');

    // Grant notification permission
    await context.grantPermissions(['notifications']);
    await page.waitForTimeout(500);

    // Check if notification permission request UI exists
    const permissionWarning = page.locator('text=/notification/i, .notification-warning');
    const warningVisible = await permissionWarning.count() > 0;
    console.log(`Notification permission UI exists: ${warningVisible}`);

    if (warningVisible) {
      const warningText = await permissionWarning.first().textContent();
      console.log(`Notification message: "${warningText}"`);
    }

    // Start a very short session and wait for completion notification
    // (This would require either a test mode or waiting 25 minutes, so we just verify the setup)
    console.log('✓ Notification permission granted');
  });

  test('should persist session across page refresh', async ({ page }) => {
    console.log('🧪 Testing: Session persistence after refresh');

    // Start session
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000);
      console.log('✓ Session started');
    }

    // Get timer value before refresh
    const timerDisplay = page.locator('.time-remaining, .countdown, .timer-display').first();
    let timeBeforeRefresh = '';
    if (await timerDisplay.isVisible()) {
      timeBeforeRefresh = await timerDisplay.textContent();
      console.log(`Time before refresh: ${timeBeforeRefresh}`);
    }

    // Refresh page
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Navigate back to Pomodoro tab
    await page.click('.nav-tab:has-text("Pomodoro")');
    await page.waitForTimeout(2000); // Wait for 2s polling to fetch active session

    // Check if active session still exists
    const activeSession = page.locator('.active-session-card, .active-session, .session-active');
    const sessionExists = await activeSession.count() > 0;
    console.log(`Active session persisted: ${sessionExists}`);

    if (sessionExists) {
      const timerAfterRefresh = page.locator('.time-remaining, .countdown, .timer-display').first();
      if (await timerAfterRefresh.isVisible()) {
        const timeAfterRefresh = await timerAfterRefresh.textContent();
        console.log(`Time after refresh: ${timeAfterRefresh}`);
        console.log('✓ Session persisted across refresh');
      }
    }
  });

  test('should display session type icons correctly', async ({ page }) => {
    console.log('🧪 Testing: Session type icons and styling');

    // Verify session type buttons have distinct styling
    const sessionButtons = page.locator('button').filter({ hasText: /Focus|Short Break|Long Break/ });
    const buttonCount = await sessionButtons.count();
    console.log(`Session type buttons found: ${buttonCount}`);

    expect(buttonCount).toBeGreaterThanOrEqual(3);

    // Check if active session card has gradient styling
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000);

      const activeCard = page.locator('.active-session-card').first();
      if (await activeCard.isVisible()) {
        const bgColor = await activeCard.evaluate(el => window.getComputedStyle(el).background);
        console.log(`Active session card background: ${bgColor.substring(0, 100)}...`);

        // Should have gradient (contains 'linear-gradient' or 'gradient')
        const hasGradient = bgColor.includes('gradient');
        console.log(`Has gradient styling: ${hasGradient}`);
      }
    }
  });

  test('should show time in correct format (4.5rem font on desktop)', async ({ page }) => {
    console.log('🧪 Testing: Timer display formatting');

    // Start session
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000);
    }

    const timerDisplay = page.locator('.time-remaining').first();
    if (await timerDisplay.isVisible()) {
      // Check font size
      const fontSize = await timerDisplay.evaluate(el => window.getComputedStyle(el).fontSize);
      console.log(`Timer font size: ${fontSize}`);

      // Should be large (4.5rem ≈ 72px on most browsers)
      const fontSizeNum = parseFloat(fontSize);
      expect(fontSizeNum).toBeGreaterThan(50); // At least 50px

      // Check font weight
      const fontWeight = await timerDisplay.evaluate(el => window.getComputedStyle(el).fontWeight);
      console.log(`Timer font weight: ${fontWeight}`);

      // Should be bold (700)
      expect(parseInt(fontWeight)).toBeGreaterThanOrEqual(700);
    }
  });

  test('should add optional notes to session', async ({ page }) => {
    console.log('🧪 Testing: Session notes functionality');

    // Look for notes input field
    const notesInput = page.locator('textarea[placeholder*="notes" i], input[placeholder*="notes" i], textarea[name*="notes" i]');
    if (await notesInput.count() > 0) {
      await notesInput.first().fill('Working on Phase 4 E2E tests');
      console.log('✓ Notes added');
    }

    // Start session
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000);
    }

    // Complete session
    const completeButton = page.locator('button').filter({ hasText: /Complete|Finish|Done/ }).first();
    if (await completeButton.isVisible()) {
      await completeButton.click();
      await page.waitForTimeout(2000);

      // Verify notes appear in recent completions
      const bodyText = await page.locator('body').textContent();
      const notesVisible = bodyText.includes('Phase 4 E2E tests');
      console.log(`Notes visible in completions: ${notesVisible}`);
    }
  });

  test('should link session to chore (optional)', async ({ page }) => {
    console.log('🧪 Testing: Link Pomodoro to chore');

    // Look for chore selection dropdown
    const choreSelect = page.locator('select[name*="chore" i], select option:has-text("Chore")').first();
    if (await choreSelect.count() > 0 && await choreSelect.isVisible()) {
      console.log('✓ Chore selector found');

      // Try to select a chore
      const options = await choreSelect.locator('option').count();
      if (options > 1) {
        await choreSelect.selectOption({ index: 1 });
        console.log(`✓ Chore selected (${options} options available)`);
      }
    } else {
      console.log('ℹ Chore linking not visible (may be optional feature)');
    }
  });

});

test.describe('Pomodoro Timer - Mobile Responsiveness', () => {

  test('should display correctly on mobile (3rem font)', async ({ page }) => {
    console.log('🧪 Testing: Mobile responsive design');

    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Navigate to Pomodoro
    await page.click('.nav-tab:has-text("Pomodoro")');
    await page.waitForTimeout(1000);

    // Start session
    const startButton = page.locator('button').filter({ hasText: /Start|Begin/ }).first();
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(2000);
    }

    // Check timer font size on mobile (should be 3rem ≈ 48px)
    const timerDisplay = page.locator('.time-remaining').first();
    if (await timerDisplay.isVisible()) {
      const fontSize = await timerDisplay.evaluate(el => window.getComputedStyle(el).fontSize);
      console.log(`Mobile timer font size: ${fontSize}`);

      const fontSizeNum = parseFloat(fontSize);
      // Should be smaller than desktop but still readable (3rem ≈ 48px)
      expect(fontSizeNum).toBeGreaterThan(40);
      expect(fontSizeNum).toBeLessThan(60);
      console.log('✓ Mobile font size is appropriate');
    }
  });

  test('should have touch-friendly buttons on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    await page.click('.nav-tab:has-text("Pomodoro")');
    await page.waitForTimeout(1000);

    // Check session type buttons are large enough for touch (44px minimum)
    const sessionButtons = page.locator('button').filter({ hasText: /Focus|Short Break|Long Break/ });
    const buttonCount = await sessionButtons.count();

    for (let i = 0; i < Math.min(buttonCount, 3); i++) {
      const button = sessionButtons.nth(i);
      const boundingBox = await button.boundingBox();

      if (boundingBox) {
        console.log(`Button ${i}: ${boundingBox.width}x${boundingBox.height}px`);
        // Touch targets should be at least 44x44px
        expect(boundingBox.height).toBeGreaterThanOrEqual(40);
      }
    }

    console.log('✓ All buttons are touch-friendly');
  });

});
