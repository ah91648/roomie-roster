// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Comprehensive Feature Testing - Pain Points Discovery', () => {
  let issues = [];

  function logIssue(category, severity, description, details = '') {
    issues.push({
      category,
      severity, // 'critical', 'major', 'minor'
      description,
      details,
      timestamp: new Date().toISOString()
    });
    console.log(`🐛 [${severity.toUpperCase()}] ${category}: ${description}`);
    if (details) console.log(`   Details: ${details}`);
  }

  test.beforeEach(async ({ page }) => {
    issues = [];
    
    // Navigate to the app
    try {
      await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000); // Allow app to fully load
    } catch (error) {
      logIssue('Navigation', 'critical', 'Failed to load application', error.message);
      throw error;
    }
  });

  test.afterEach(async ({ page }) => {
    // Print summary of issues found
    console.log('\n📊 ISSUES SUMMARY:');
    const criticalIssues = issues.filter(i => i.severity === 'critical');
    const majorIssues = issues.filter(i => i.severity === 'major');
    const minorIssues = issues.filter(i => i.severity === 'minor');
    
    console.log(`🔴 Critical: ${criticalIssues.length}`);
    console.log(`🟡 Major: ${majorIssues.length}`);
    console.log(`🟢 Minor: ${minorIssues.length}`);
    
    if (issues.length > 0) {
      console.log('\nDetailed Issues:');
      issues.forEach(issue => {
        console.log(`- [${issue.severity}] ${issue.category}: ${issue.description}`);
        if (issue.details) console.log(`  ${issue.details}`);
      });
    }
  });

  test('should test roommate management thoroughly', async ({ page }) => {
    console.log('🧪 Testing Roommate Management...');
    
    // Navigate to Roommates tab
    try {
      await page.click('[data-tab="roommates"]');
      await page.waitForTimeout(1000);
    } catch (error) {
      logIssue('Navigation', 'major', 'Cannot access Roommates tab', error.message);
      return;
    }

    // Test adding a roommate
    try {
      const roommateCountBefore = await page.locator('.roommate-item').count();
      
      await page.fill('input[placeholder*="name" i]', 'Stress Test User');
      await page.click('button:has-text("Add Roommate")');
      await page.waitForTimeout(1000);
      
      const roommateCountAfter = await page.locator('.roommate-item').count();
      if (roommateCountAfter <= roommateCountBefore) {
        logIssue('Roommate Management', 'major', 'Roommate not added successfully');
      }
    } catch (error) {
      logIssue('Roommate Management', 'major', 'Cannot add roommate', error.message);
    }

    // Test adding roommate with empty name
    try {
      await page.fill('input[placeholder*="name" i]', '');
      await page.click('button:has-text("Add Roommate")');
      await page.waitForTimeout(500);
      
      // Check if there's proper validation
      const errorVisible = await page.locator('.error, .alert, [role="alert"]').isVisible().catch(() => false);
      if (!errorVisible) {
        logIssue('Validation', 'minor', 'No validation error shown for empty roommate name');
      }
    } catch (error) {
      logIssue('Validation', 'minor', 'Error testing empty roommate validation', error.message);
    }

    // Test roommate with very long name
    try {
      const longName = 'A'.repeat(100);
      await page.fill('input[placeholder*="name" i]', longName);
      await page.click('button:has-text("Add Roommate")');
      await page.waitForTimeout(1000);
      
      // Check if UI handles long names gracefully
      const longNameVisible = await page.locator(`text=${longName.substring(0, 20)}`).isVisible().catch(() => false);
      if (longNameVisible) {
        // Check if the name overflows container
        const nameElement = page.locator('.roommate-name').first();
        const isOverflowing = await nameElement.evaluate(el => el.scrollWidth > el.clientWidth).catch(() => false);
        if (isOverflowing) {
          logIssue('UI/UX', 'minor', 'Long roommate names cause UI overflow');
        }
      }
    } catch (error) {
      logIssue('Edge Cases', 'minor', 'Error testing long roommate names', error.message);
    }
  });

  test('should test chore management features comprehensively', async ({ page }) => {
    console.log('🧪 Testing Chore Management...');
    
    // Navigate to Chores tab
    try {
      await page.click('[data-tab="chores"]');
      await page.waitForTimeout(1000);
    } catch (error) {
      logIssue('Navigation', 'major', 'Cannot access Chores tab', error.message);
      return;
    }

    // Test adding a new chore
    try {
      const choreCountBefore = await page.locator('.chore-item').count();
      
      await page.fill('input[placeholder*="chore" i]', 'Test Deep Clean Kitchen');
      
      // Try to set frequency
      const frequencySelect = page.locator('select[name*="frequency" i], select:has(option:text("Weekly"))');
      if (await frequencySelect.isVisible()) {
        await frequencySelect.selectOption('weekly');
      }
      
      // Try to set type
      const typeSelect = page.locator('select[name*="type" i], select:has(option:text("Random"))');
      if (await typeSelect.isVisible()) {
        await typeSelect.selectOption('random');
      }
      
      // Try to set points
      const pointsInput = page.locator('input[type="number"], input[placeholder*="points" i]');
      if (await pointsInput.isVisible()) {
        await pointsInput.fill('15');
      }
      
      await page.click('button:has-text("Add Chore")');
      await page.waitForTimeout(1000);
      
      const choreCountAfter = await page.locator('.chore-item').count();
      if (choreCountAfter <= choreCountBefore) {
        logIssue('Chore Management', 'major', 'Chore not added successfully');
      }
    } catch (error) {
      logIssue('Chore Management', 'major', 'Cannot add chore', error.message);
    }

    // Test editing an existing chore
    try {
      const firstChore = page.locator('.chore-item').first();
      const editButton = firstChore.locator('button:has-text("Edit"), .edit-button, [title*="edit" i]');
      
      if (await editButton.isVisible()) {
        await editButton.click();
        await page.waitForTimeout(500);
        
        // Try to modify the chore name
        const editInput = page.locator('input[value], .edit-mode input').first();
        if (await editInput.isVisible()) {
          await editInput.clear();
          await editInput.fill('Modified Chore Name');
          
          const saveButton = page.locator('button:has-text("Save"), .save-button');
          if (await saveButton.isVisible()) {
            await saveButton.click();
            await page.waitForTimeout(1000);
            
            // Verify the change
            const updatedText = await page.locator('text=Modified Chore Name').isVisible();
            if (!updatedText) {
              logIssue('Chore Management', 'major', 'Chore edit not saved properly');
            }
          } else {
            logIssue('UI/UX', 'major', 'No save button found for chore editing');
          }
        } else {
          logIssue('UI/UX', 'major', 'Cannot find edit input field for chores');
        }
      } else {
        logIssue('UI/UX', 'minor', 'No edit button found for chores');
      }
    } catch (error) {
      logIssue('Chore Management', 'major', 'Cannot edit chore', error.message);
    }

    // Test chore with invalid points
    try {
      await page.fill('input[placeholder*="chore" i]', 'Invalid Points Test');
      const pointsInput = page.locator('input[type="number"], input[placeholder*="points" i]');
      if (await pointsInput.isVisible()) {
        await pointsInput.fill('-5'); // Negative points
        await page.click('button:has-text("Add Chore")');
        await page.waitForTimeout(500);
        
        const errorVisible = await page.locator('.error, .alert, [role="alert"]').isVisible().catch(() => false);
        if (!errorVisible) {
          logIssue('Validation', 'minor', 'No validation for negative chore points');
        }
      }
    } catch (error) {
      logIssue('Validation', 'minor', 'Error testing invalid chore points', error.message);
    }
  });

  test('should test shopping list functionality thoroughly', async ({ page }) => {
    console.log('🧪 Testing Shopping List...');
    
    // Navigate to Shopping List tab
    try {
      await page.click('[data-tab="shopping-list"]');
      await page.waitForTimeout(1000);
    } catch (error) {
      logIssue('Navigation', 'major', 'Cannot access Shopping List tab', error.message);
      return;
    }

    // Test adding shopping list items
    try {
      const itemCountBefore = await page.locator('.shopping-item, .list-item').count();
      
      await page.fill('input[placeholder*="item" i], input[placeholder*="add" i]', 'Test Groceries');
      
      // Try to set price if available
      const priceInput = page.locator('input[type="number"], input[placeholder*="price" i], input[placeholder*="$" i]');
      if (await priceInput.isVisible()) {
        await priceInput.fill('12.99');
      }
      
      await page.click('button:has-text("Add"), button:has-text("Add Item")');
      await page.waitForTimeout(1000);
      
      const itemCountAfter = await page.locator('.shopping-item, .list-item').count();
      if (itemCountAfter <= itemCountBefore) {
        logIssue('Shopping List', 'major', 'Shopping list item not added successfully');
      }
    } catch (error) {
      logIssue('Shopping List', 'major', 'Cannot add shopping list item', error.message);
    }

    // Test marking item as purchased
    try {
      const firstItem = page.locator('.shopping-item, .list-item').first();
      const purchaseButton = firstItem.locator('button:has-text("Purchase"), button:has-text("Buy"), .purchase-button, input[type="checkbox"]');
      
      if (await purchaseButton.isVisible()) {
        await purchaseButton.click();
        await page.waitForTimeout(1000);
        
        // Check if item shows as purchased
        const isPurchased = await firstItem.locator('.purchased, .completed, [data-purchased="true"]').isVisible().catch(() => false);
        if (!isPurchased) {
          logIssue('Shopping List', 'major', 'Item purchase status not reflected in UI');
        }
      } else {
        logIssue('UI/UX', 'minor', 'No purchase button found for shopping list items');
      }
    } catch (error) {
      logIssue('Shopping List', 'major', 'Cannot mark item as purchased', error.message);
    }

    // Test adding item with very high price
    try {
      await page.fill('input[placeholder*="item" i], input[placeholder*="add" i]', 'Expensive Test Item');
      const priceInput = page.locator('input[type="number"], input[placeholder*="price" i], input[placeholder*="$" i]');
      if (await priceInput.isVisible()) {
        await priceInput.fill('999999.99');
        await page.click('button:has-text("Add"), button:has-text("Add Item")');
        await page.waitForTimeout(1000);
        
        // Check if high price displays correctly
        const priceDisplay = await page.locator('text=/\\$999,?999\\.99/').isVisible().catch(() => false);
        if (!priceDisplay) {
          logIssue('UI/UX', 'minor', 'High prices may not display correctly');
        }
      }
    } catch (error) {
      logIssue('Edge Cases', 'minor', 'Error testing high price items', error.message);
    }
  });

  test('should test laundry scheduling functionality', async ({ page }) => {
    console.log('🧪 Testing Laundry Scheduling...');
    
    // Navigate to Laundry tab
    try {
      await page.click('[data-tab="laundry"]');
      await page.waitForTimeout(1000);
    } catch (error) {
      logIssue('Navigation', 'major', 'Cannot access Laundry tab', error.message);
      return;
    }

    // Test scheduling laundry
    try {
      const scheduleButton = page.locator('button:has-text("Schedule"), button:has-text("Book"), button:has-text("Add")');
      if (await scheduleButton.isVisible()) {
        await scheduleButton.click();
        await page.waitForTimeout(1000);
        
        // Try to select a date
        const dateInput = page.locator('input[type="date"], input[type="datetime-local"]');
        if (await dateInput.isVisible()) {
          const tomorrow = new Date();
          tomorrow.setDate(tomorrow.getDate() + 1);
          const dateString = tomorrow.toISOString().split('T')[0];
          await dateInput.fill(dateString);
        }
        
        // Try to select time slot
        const timeSelect = page.locator('select:has(option:text("AM")), select:has(option:text("PM")), select[name*="time" i]');
        if (await timeSelect.isVisible()) {
          await timeSelect.selectOption({ index: 1 });
        }
        
        // Try to select machine type
        const machineSelect = page.locator('select:has(option:text("Washer")), select:has(option:text("Dryer")), select[name*="machine" i]');
        if (await machineSelect.isVisible()) {
          await machineSelect.selectOption({ index: 0 });
        }
        
        const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Book"), button:has-text("Schedule")');
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(1000);
          
          // Check if booking appears in schedule
          const bookingExists = await page.locator('.scheduled-item, .booking-item, .laundry-slot').isVisible().catch(() => false);
          if (!bookingExists) {
            logIssue('Laundry Scheduling', 'major', 'Laundry booking not created successfully');
          }
        } else {
          logIssue('UI/UX', 'major', 'No confirm button found for laundry booking');
        }
      } else {
        logIssue('UI/UX', 'minor', 'No schedule button found for laundry');
      }
    } catch (error) {
      logIssue('Laundry Scheduling', 'major', 'Cannot schedule laundry', error.message);
    }

    // Test double booking prevention
    try {
      // Try to book the same time slot again
      const scheduleButton = page.locator('button:has-text("Schedule"), button:has-text("Book"), button:has-text("Add")');
      if (await scheduleButton.isVisible()) {
        await scheduleButton.click();
        await page.waitForTimeout(500);
        
        // Use same time slot as before
        const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Book"), button:has-text("Schedule")');
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
          await page.waitForTimeout(1000);
          
          // Should show error or prevent booking
          const errorVisible = await page.locator('.error, .alert, [role="alert"]').isVisible().catch(() => false);
          if (!errorVisible) {
            logIssue('Business Logic', 'major', 'No validation to prevent double booking laundry slots');
          }
        }
      }
    } catch (error) {
      logIssue('Business Logic', 'minor', 'Error testing double booking prevention', error.message);
    }
  });

  test('should test assignment and cycle functionality', async ({ page }) => {
    console.log('🧪 Testing Assignment and Cycle Management...');
    
    // Navigate to Assignments tab
    try {
      await page.click('[data-tab="assignments"]');
      await page.waitForTimeout(1000);
    } catch (error) {
      logIssue('Navigation', 'major', 'Cannot access Assignments tab', error.message);
      return;
    }

    // Test generating new assignments
    try {
      const assignButton = page.locator('button:has-text("Assign"), button:has-text("Generate")');
      if (await assignButton.isVisible()) {
        await assignButton.click();
        await page.waitForTimeout(2000);
        
        // Check if assignments appear
        const assignmentsExist = await page.locator('.assignment-item, .chore-assignment').isVisible().catch(() => false);
        if (!assignmentsExist) {
          logIssue('Assignment Logic', 'major', 'No assignments generated or displayed');
        }
      } else {
        logIssue('UI/UX', 'minor', 'No assign button found');
      }
    } catch (error) {
      logIssue('Assignment Logic', 'major', 'Cannot generate assignments', error.message);
    }

    // Test cycle reset
    try {
      const resetButton = page.locator('button:has-text("Reset"), button:has-text("New Cycle")');
      if (await resetButton.isVisible()) {
        await resetButton.click();
        await page.waitForTimeout(1000);
        
        // Should show confirmation or reset immediately
        const confirmDialog = await page.locator('.modal, .dialog, .confirm').isVisible().catch(() => false);
        if (confirmDialog) {
          const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Yes")');
          if (await confirmButton.isVisible()) {
            await confirmButton.click();
            await page.waitForTimeout(1000);
          }
        }
        
        // Check if cycle was reset (assignments should be cleared)
        const assignmentsStillExist = await page.locator('.assignment-item, .chore-assignment').isVisible().catch(() => false);
        if (assignmentsStillExist) {
          logIssue('Cycle Management', 'minor', 'Assignments may not be cleared after cycle reset');
        }
      } else {
        logIssue('UI/UX', 'minor', 'No reset cycle button found');
      }
    } catch (error) {
      logIssue('Cycle Management', 'major', 'Cannot reset cycle', error.message);
    }
  });

  test('should test mobile responsiveness and navigation', async ({ page }) => {
    console.log('🧪 Testing Mobile Responsiveness...');
    
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);

    // Test tab navigation on mobile
    const tabs = ['roommates', 'chores', 'shopping-list', 'laundry', 'assignments'];
    
    for (const tab of tabs) {
      try {
        const tabElement = page.locator(`[data-tab="${tab}"]`);
        if (await tabElement.isVisible()) {
          await tabElement.click();
          await page.waitForTimeout(500);
          
          // Check if tab content is visible
          const contentVisible = await page.locator('.tab-content, .main-content').isVisible().catch(() => false);
          if (!contentVisible) {
            logIssue('Mobile UI', 'major', `Tab content not visible for ${tab} on mobile`);
          }
        } else {
          logIssue('Mobile UI', 'major', `Tab ${tab} not visible on mobile`);
        }
      } catch (error) {
        logIssue('Mobile UI', 'major', `Cannot navigate to ${tab} tab on mobile`, error.message);
      }
    }

    // Test if buttons are appropriately sized for touch
    try {
      const buttons = await page.locator('button').all();
      for (let i = 0; i < Math.min(buttons.length, 5); i++) {
        const button = buttons[i];
        const boundingBox = await button.boundingBox();
        if (boundingBox && (boundingBox.width < 44 || boundingBox.height < 44)) {
          logIssue('Mobile UI', 'minor', 'Button may be too small for touch interaction');
          break;
        }
      }
    } catch (error) {
      logIssue('Mobile UI', 'minor', 'Cannot check button sizes', error.message);
    }
  });

  test('should test error handling and edge cases', async ({ page }) => {
    console.log('🧪 Testing Error Handling...');
    
    // Test network error handling by intercepting API calls
    await page.route('**/api/**', route => {
      if (route.request().url().includes('/roommates')) {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal Server Error' })
        });
      } else {
        route.continue();
      }
    });

    try {
      await page.click('[data-tab="roommates"]');
      await page.waitForTimeout(1000);
      
      await page.fill('input[placeholder*="name" i]', 'Error Test User');
      await page.click('button:has-text("Add Roommate")');
      await page.waitForTimeout(2000);
      
      // Should show error message
      const errorVisible = await page.locator('.error, .alert, [role="alert"]').isVisible().catch(() => false);
      if (!errorVisible) {
        logIssue('Error Handling', 'major', 'No error message shown for API failures');
      }
    } catch (error) {
      logIssue('Error Handling', 'minor', 'Error testing API error handling', error.message);
    }

    // Reset route interception
    await page.unroute('**/api/**');
  });
});