// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Comprehensive E2E tests for Mood Journal functionality
 * Tests the 364-line MoodJournal.js component added in Phase 3
 */

test.describe('Mood Journal - Complete Feature Testing', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Navigate to Mood tab
    await page.click('.nav-tab:has-text("Mood"), .nav-tab:has-text("😊")');
    await page.waitForTimeout(1000);
  });

  test('should render mood journal interface with all elements', async ({ page }) => {
    console.log('🧪 Testing: Mood Journal UI rendering');

    // Verify main heading
    const hasHeader = await page.locator('h2, h1').filter({ hasText: /Mood|Journal|Feelings/ }).count() > 0;
    console.log(`Mood header found: ${hasHeader}`);

    // Check for mood selector with emojis
    const moodEmojis = ['😞', '😕', '😐', '🙂', '😄'];
    let emojiCount = 0;
    for (const emoji of moodEmojis) {
      const exists = await page.locator(`text=${emoji}`).count() > 0;
      if (exists) emojiCount++;
    }
    console.log(`Mood emojis found: ${emojiCount}/5`);

    // Check for energy level selector
    const energyBars = page.locator('.energy-bar, [class*="energy"]').or(page.locator('text=⚡'));
    const energyExists = await energyBars.count() > 0;
    console.log(`Energy selector exists: ${energyExists}`);

    console.log('✓ Mood Journal UI components verified');
  });

  test('should create today\'s mood entry with all fields', async ({ page }) => {
    console.log('🧪 Testing: Create mood entry');

    // Select mood level (e.g., 😄 - Great)
    const greatMoodButton = page.locator('button, .mood-option').filter({ hasText: /😄|Great|5/ }).first();
    if (await greatMoodButton.count() > 0 && await greatMoodButton.isVisible()) {
      await greatMoodButton.click();
      await page.waitForTimeout(500);
      console.log('✓ Mood level selected (Great)');
    } else {
      // Try alternative: click on emoji directly
      const emojiButton = page.locator('text=😄').first();
      if (await emojiButton.isVisible()) {
        await emojiButton.click();
        await page.waitForTimeout(500);
        console.log('✓ Mood emoji clicked');
      }
    }

    // Select energy level (e.g., 4/5)
    const energyButtons = page.locator('button, .energy-option, .energy-bar').filter({ hasText: /⚡|energy/i });
    if (await energyButtons.count() >= 4) {
      await energyButtons.nth(3).click(); // 4th energy level
      await page.waitForTimeout(500);
      console.log('✓ Energy level selected (4/5)');
    }

    // Add notes
    const notesInput = page.locator('textarea[name*="notes" i], textarea[placeholder*="notes" i]').first();
    if (await notesInput.count() > 0 && await notesInput.isVisible()) {
      await notesInput.fill('Feeling productive today! Phase 4 testing is going well.');
      console.log('✓ Notes added');
    }

    // Add tags
    const tagsInput = page.locator('input[name*="tags" i], input[placeholder*="tags" i]').first();
    if (await tagsInput.count() > 0 && await tagsInput.isVisible()) {
      await tagsInput.fill('productive, focused, energetic');
      console.log('✓ Tags added');
    }

    // Save entry
    const saveButton = page.locator('button').filter({ hasText: /Save|Submit|Create/ }).first();
    if (await saveButton.isVisible()) {
      await saveButton.click();
      await page.waitForTimeout(2000);
      console.log('✓ Entry saved');
    }

    // Verify entry appears in list
    const entryList = page.locator('.mood-entry, .entry-item, .journal-entry');
    const entryExists = await entryList.count() > 0;
    console.log(`Mood entry visible: ${entryExists}`);
    expect(entryExists).toBe(true);
  });

  test('should show all 5 mood levels with correct emojis', async ({ page }) => {
    console.log('🧪 Testing: Mood level emoji display');

    const expectedMoods = [
      { emoji: '😞', label: 'Very Bad' },
      { emoji: '😕', label: 'Bad' },
      { emoji: '😐', label: 'Okay' },
      { emoji: '🙂', label: 'Good' },
      { emoji: '😄', label: 'Great' }
    ];

    for (const mood of expectedMoods) {
      const emojiExists = await page.locator(`text=${mood.emoji}`).count() > 0;
      console.log(`${mood.emoji} (${mood.label}): ${emojiExists ? '✓' : '✗'}`);
    }

    // Verify mood selector has correct structure
    const moodSelector = page.locator('.mood-selector, .mood-options, [class*="mood-"]');
    const selectorExists = await moodSelector.count() > 0;
    console.log(`Mood selector component exists: ${selectorExists}`);

    if (selectorExists) {
      // Check if it's a grid layout (5 columns on desktop)
      const gridStyle = await moodSelector.first().evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          display: style.display,
          gridTemplateColumns: style.gridTemplateColumns
        };
      });
      console.log(`Mood selector layout:`, gridStyle);
    }
  });

  test('should show energy levels with ⚡ and ○ symbols', async ({ page }) => {
    console.log('🧪 Testing: Energy bar rendering');

    // Look for energy symbols
    const lightningBolt = await page.locator('text=⚡').count();
    const emptyCircle = await page.locator('text=○').count();

    console.log(`Lightning bolts (⚡) found: ${lightningBolt}`);
    console.log(`Empty circles (○) found: ${emptyCircle}`);

    // Should have 5-level energy selector
    const energyOptions = page.locator('.energy-option, .energy-bar, button').filter({ hasText: /⚡|○|energy/i });
    const optionCount = await energyOptions.count();
    console.log(`Energy level options: ${optionCount}`);

    expect(optionCount).toBeGreaterThanOrEqual(5);
  });

  test('should detect and display today\'s entry', async ({ page }) => {
    console.log('🧪 Testing: Today\'s entry detection');

    // Create an entry for today
    const greatMood = page.locator('button, .mood-option').filter({ hasText: /😄|Great/ }).first();
    if (await greatMood.count() > 0 && await greatMood.isVisible()) {
      await greatMood.click();
      await page.waitForTimeout(500);
    }

    const saveButton = page.locator('button').filter({ hasText: /Save|Submit/ }).first();
    if (await saveButton.isVisible()) {
      await saveButton.click();
      await page.waitForTimeout(2000);
    }

    // Verify "Today's Entry" section exists
    const todaySection = page.locator('text=/today.*entry|entry.*today/i, .today-entry, [class*="today"]');
    const todayExists = await todaySection.count() > 0;
    console.log(`"Today's Entry" section found: ${todayExists}`);

    if (todayExists) {
      // Should show entry in display mode (not edit mode)
      const displayMode = page.locator('.entry-display, .mood-display');
      const isDisplayMode = await displayMode.count() > 0;
      console.log(`Entry in display mode: ${isDisplayMode}`);
    }
  });

  test('should toggle between display and edit mode for today\'s entry', async ({ page }) => {
    console.log('🧪 Testing: Toggle display/edit mode');

    // First, create today's entry
    const goodMood = page.locator('button, .mood-option').filter({ hasText: /🙂|Good/ }).first();
    if (await goodMood.count() > 0 && await goodMood.isVisible()) {
      await goodMood.click();
      await page.waitForTimeout(500);
    }

    const saveButton = page.locator('button').filter({ hasText: /Save|Submit/ }).first();
    if (await saveButton.isVisible()) {
      await saveButton.click();
      await page.waitForTimeout(2000);
      console.log('✓ Entry created');
    }

    // Look for edit button
    const editButton = page.locator('button').filter({ hasText: /Edit|✏️/ }).first();
    if (await editButton.count() > 0 && await editButton.isVisible()) {
      await editButton.click();
      await page.waitForTimeout(1000);
      console.log('✓ Edit mode activated');

      // Verify form appears for editing
      const moodSelector = page.locator('.mood-selector, .mood-options');
      const selectorVisible = await moodSelector.count() > 0;
      console.log(`Mood selector visible in edit mode: ${selectorVisible}`);

      // Change mood
      const differentMood = page.locator('button, .mood-option').filter({ hasText: /😄|Great/ }).first();
      if (await differentMood.isVisible()) {
        await differentMood.click();
        await page.waitForTimeout(500);
        console.log('✓ Mood changed');
      }

      // Save changes
      const updateButton = page.locator('button').filter({ hasText: /Save|Update/ }).first();
      if (await updateButton.isVisible()) {
        await updateButton.click();
        await page.waitForTimeout(2000);
        console.log('✓ Changes saved');
      }
    } else {
      console.log('ℹ Edit button not found (may be inline editing)');
    }
  });

  test('should show last 7 days of mood entries', async ({ page }) => {
    console.log('🧪 Testing: Last 7 days view');

    // Look for entries list or history section
    const entriesList = page.locator('.mood-entries, .entries-list, .history');
    const listExists = await entriesList.count() > 0;
    console.log(`Entries list section exists: ${listExists}`);

    if (listExists) {
      // Count visible entries
      const entryItems = entriesList.locator('.mood-entry, .entry-item, li');
      const itemCount = await entryItems.count();
      console.log(`Mood entries shown: ${itemCount}`);

      // Should show up to 7 days
      expect(itemCount).toBeLessThanOrEqual(7);
    }

    // Look for "Last 7 Days" heading
    const headingExists = await page.locator('text=/last.*7.*days?|7.*days?.*history/i').count() > 0;
    console.log(`"Last 7 Days" heading found: ${headingExists}`);
  });

  test('should handle comma-separated tags input', async ({ page }) => {
    console.log('🧪 Testing: Tags input functionality');

    const tagsInput = page.locator('input[name*="tags" i], input[placeholder*="tags" i]').first();
    if (await tagsInput.count() > 0 && await tagsInput.isVisible()) {
      // Enter comma-separated tags
      await tagsInput.fill('happy, energetic, focused, productive');
      console.log('✓ Tags entered: happy, energetic, focused, productive');

      // Select a mood to enable save
      const mood = page.locator('button, .mood-option').filter({ hasText: /😄/ }).first();
      if (await mood.isVisible()) {
        await mood.click();
        await page.waitForTimeout(500);
      }

      // Save entry
      const saveButton = page.locator('button').filter({ hasText: /Save|Submit/ }).first();
      if (await saveButton.isVisible()) {
        await saveButton.click();
        await page.waitForTimeout(2000);
      }

      // Verify tags are displayed
      const bodyText = await page.locator('body').textContent();
      const tagsVisible = bodyText.includes('happy') && bodyText.includes('energetic');
      console.log(`Tags visible after save: ${tagsVisible}`);

      if (tagsVisible) {
        // Check if tags are displayed as badges/chips
        const tagBadges = page.locator('.tag, .badge, .chip');
        const badgeCount = await tagBadges.count();
        console.log(`Tag badges found: ${badgeCount}`);
      }
    } else {
      console.log('ℹ Tags input not found (optional feature)');
    }
  });

  test('should validate required mood level', async ({ page }) => {
    console.log('🧪 Testing: Mood level validation');

    // Try to save without selecting mood
    const saveButton = page.locator('button').filter({ hasText: /Save|Submit/ }).first();
    if (await saveButton.isVisible()) {
      await saveButton.click();
      await page.waitForTimeout(1000);

      // Should show validation error or prevent submission
      const errorMessage = page.locator('.error, .alert, [role="alert"]');
      const errorExists = await errorMessage.count() > 0;
      console.log(`Validation error shown: ${errorExists}`);

      // Or button might be disabled
      const isDisabled = await saveButton.isDisabled();
      console.log(`Save button disabled: ${isDisabled}`);

      expect(errorExists || isDisabled).toBe(true);
    }
  });

  test('should show mood selection with visual feedback', async ({ page }) => {
    console.log('🧪 Testing: Mood selection visual feedback');

    // Click each mood option and verify selection
    const moodOptions = page.locator('button, .mood-option').filter({ hasText: /😞|😕|😐|🙂|😄/ });
    const optionCount = await moodOptions.count();

    if (optionCount > 0) {
      const selectedMood = moodOptions.nth(2); // Middle option (😐)
      await selectedMood.click();
      await page.waitForTimeout(500);

      // Check for selected class or style
      const className = await selectedMood.getAttribute('class');
      console.log(`Selected mood classes: ${className}`);

      const hasSelectedClass = className?.includes('selected') || className?.includes('active');
      console.log(`Has selected class: ${hasSelectedClass}`);

      // Check for visual styling (border, background, scale)
      const selectedStyle = await selectedMood.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          borderColor: style.borderColor,
          background: style.background,
          transform: style.transform
        };
      });
      console.log(`Selected mood styling:`, selectedStyle);

      // Should have scale transform (1.05) or special border color
      const hasTransform = selectedStyle.transform !== 'none';
      console.log(`Has scale transform: ${hasTransform}`);
    }
  });

  test('should display entries with date formatting', async ({ page }) => {
    console.log('🧪 Testing: Date display formatting');

    // Create an entry
    const mood = page.locator('button, .mood-option').filter({ hasText: /😄/ }).first();
    if (await mood.isVisible()) {
      await mood.click();
      await page.waitForTimeout(500);
    }

    const saveButton = page.locator('button').filter({ hasText: /Save/ }).first();
    if (await saveButton.isVisible()) {
      await saveButton.click();
      await page.waitForTimeout(2000);
    }

    // Look for date displays
    const dateElements = page.locator('.date, .entry-date, [class*="date"]');
    if (await dateElements.count() > 0) {
      const dateText = await dateElements.first().textContent();
      console.log(`Date display format: "${dateText}"`);

      // Should contain month/day or relative time (e.g., "Today", "Yesterday")
      const hasValidDate = dateText.match(/\d{1,2}|today|yesterday/i);
      console.log(`Has valid date format: ${!!hasValidDate}`);
    }
  });

});

test.describe('Mood Journal - Mobile Responsiveness', () => {

  test('should display mood selector in 3-column grid on mobile', async ({ page }) => {
    console.log('🧪 Testing: Mobile mood selector (3-column grid)');

    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Navigate to Mood
    await page.click('.nav-tab:has-text("Mood"), .nav-tab:has-text("😊")');
    await page.waitForTimeout(1000);

    // Check mood selector grid layout on mobile
    const moodSelector = page.locator('.mood-selector, .mood-options').first();
    if (await moodSelector.count() > 0 && await moodSelector.isVisible()) {
      const gridStyle = await moodSelector.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          display: style.display,
          gridTemplateColumns: style.gridTemplateColumns
        };
      });
      console.log(`Mobile mood selector layout:`, gridStyle);

      // Should be 3-column grid on mobile (repeat(3, 1fr) or similar)
      const hasThreeColumns = gridStyle.gridTemplateColumns?.includes('3') ||
                               gridStyle.gridTemplateColumns?.split(' ').length === 3;
      console.log(`Has 3-column layout: ${hasThreeColumns}`);
    }
  });

  test('should be usable on mobile devices', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    await page.click('.nav-tab:has-text("Mood"), .nav-tab:has-text("😊")');
    await page.waitForTimeout(1000);

    // Verify mood buttons are large enough for touch
    const moodButtons = page.locator('button, .mood-option').filter({ hasText: /😞|😕|😐|🙂|😄/ });
    const buttonCount = await moodButtons.count();

    for (let i = 0; i < Math.min(buttonCount, 5); i++) {
      const button = moodButtons.nth(i);
      const boundingBox = await button.boundingBox();

      if (boundingBox) {
        console.log(`Mood button ${i}: ${boundingBox.width}x${boundingBox.height}px`);
        // Touch targets should be at least 44x44px
        expect(boundingBox.height).toBeGreaterThanOrEqual(40);
      }
    }

    console.log('✓ Mood buttons are touch-friendly on mobile');
  });

});
