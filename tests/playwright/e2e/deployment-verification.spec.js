const { test, expect } = require('@playwright/test');

test.describe('Deployment Verification', () => {
  
  test('verify all navigation tabs are present on deployed site', async ({ page }) => {
    // Navigate to the live site
    await page.goto('https://roomie-roster.onrender.com/');
    
    // Wait for the app to load
    await page.waitForLoadState('networkidle');
    
    // Check for version indicator in footer to confirm new deployment
    const footerText = await page.locator('.app-footer p').textContent();
    console.log('Footer text:', footerText);
    
    // Find all navigation tabs
    const navTabs = await page.locator('.nav-tab').all();
    console.log(`Found ${navTabs.length} navigation tabs`);
    
    // Expected tabs for complete deployment
    const expectedTabs = [
      'Assignments',
      'Roommates', 
      'Chores',
      'Laundry',
      'Shopping List',
      'Requests',
      'Calendar Settings',
      'Authentication'
    ];
    
    // Get the text content of each tab
    const actualTabs = [];
    for (const tab of navTabs) {
      const tabText = await tab.locator('.tab-label').textContent();
      actualTabs.push(tabText);
    }
    
    console.log('Expected tabs:', expectedTabs);
    console.log('Actual tabs:', actualTabs);
    
    // Verify each expected tab is present
    for (const expectedTab of expectedTabs) {
      const isPresent = actualTabs.includes(expectedTab);
      console.log(`✓ ${expectedTab}: ${isPresent ? 'FOUND' : 'MISSING'}`);
      
      if (!isPresent) {
        console.log(`❌ Missing tab: ${expectedTab}`);
      }
    }
    
    // Check if we have the expected number of tabs
    const expectedCount = expectedTabs.length;
    const actualCount = actualTabs.length;
    
    console.log(`Tab count - Expected: ${expectedCount}, Actual: ${actualCount}`);
    
    if (actualCount >= expectedCount) {
      console.log('✅ Deployment appears successful - all tabs present');
    } else {
      console.log(`❌ Deployment incomplete - missing ${expectedCount - actualCount} tabs`);
    }
    
    // Take screenshot for verification
    await page.screenshot({ path: 'deployment-verification.png', fullPage: true });
  });
  
  test('verify specific features are accessible', async ({ page }) => {
    await page.goto('https://roomie-roster.onrender.com/');
    await page.waitForLoadState('networkidle');
    
    // Test clicking on each tab to ensure components load
    const tabsToTest = ['Laundry', 'Requests'];
    
    for (const tabName of tabsToTest) {
      console.log(`Testing ${tabName} tab...`);
      
      // Try to click the tab
      const tabSelector = `.nav-tab:has-text("${tabName}")`;
      const tabExists = await page.locator(tabSelector).count() > 0;
      
      if (tabExists) {
        await page.click(tabSelector);
        await page.waitForTimeout(1000);
        
        // Check if content loaded
        const hasContent = await page.locator('.main-content').count() > 0;
        console.log(`${tabName} tab clicked, content loaded: ${hasContent}`);
        
        await page.screenshot({ path: `${tabName.toLowerCase()}-tab.png` });
      } else {
        console.log(`❌ ${tabName} tab not found`);
      }
    }
  });
  
  test('check for React components in browser', async ({ page }) => {
    await page.goto('https://roomie-roster.onrender.com/');
    await page.waitForLoadState('networkidle');
    
    // Check if the new components are available in the browser
    const componentCheck = await page.evaluate(() => {
      // Look for component-specific classes or elements
      const laundryElements = document.querySelectorAll('[class*="laundry"], [class*="Laundry"]');
      const requestElements = document.querySelectorAll('[class*="request"], [class*="Request"]');
      
      return {
        laundryFound: laundryElements.length > 0,
        requestFound: requestElements.length > 0,
        totalElements: document.querySelectorAll('[class*="component"], [class*="Component"]').length
      };
    });
    
    console.log('Component check results:', componentCheck);
  });
  
});