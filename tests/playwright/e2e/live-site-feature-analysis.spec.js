const { test, expect } = require('@playwright/test');

test.describe('Live Site Feature Analysis', () => {
  
  test('analyze deployed site tabs and features', async ({ page }) => {
    // Navigate to the live site
    await page.goto('https://roomie-roster.onrender.com/');
    
    // Wait for the app to load
    await page.waitForLoadState('networkidle');
    
    // Take a screenshot for reference
    await page.screenshot({ path: 'live-site-navigation.png', fullPage: true });
    
    // Find all navigation tabs
    const navTabs = await page.locator('.nav-tab').all();
    console.log(`Found ${navTabs.length} navigation tabs`);
    
    // Get the text content of each tab
    const tabTexts = [];
    for (const tab of navTabs) {
      const tabText = await tab.locator('.tab-label').textContent();
      tabTexts.push(tabText);
      console.log(`Tab found: ${tabText}`);
    }
    
    // Expected tabs based on App.js
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
    
    console.log('Expected tabs:', expectedTabs);
    console.log('Found tabs:', tabTexts);
    
    // Check which tabs are missing
    const missingTabs = expectedTabs.filter(tab => !tabTexts.includes(tab));
    console.log('Missing tabs:', missingTabs);
    
    // Check for each expected tab
    for (const expectedTab of expectedTabs) {
      const isPresent = tabTexts.includes(expectedTab);
      console.log(`${expectedTab}: ${isPresent ? 'PRESENT' : 'MISSING'}`);
    }
    
    // Check if tabs are hidden or styled differently
    await page.locator('.nav-tabs').screenshot({ path: 'nav-tabs-area.png' });
    
    // Check the DOM structure for hidden tabs
    const allTabElements = await page.locator('[class*="nav-tab"], [class*="tab"]').all();
    console.log(`Total tab-like elements found: ${allTabElements.length}`);
    
    // Check for CSS that might be hiding tabs
    const hiddenTabs = await page.locator('.nav-tab[style*="display: none"], .nav-tab.hidden').all();
    console.log(`Hidden tabs found: ${hiddenTabs.length}`);
    
    // Check browser console for errors
    const consoleMessages = [];
    page.on('console', msg => {
      consoleMessages.push(`${msg.type()}: ${msg.text()}`);
    });
    
    // Reload to capture console messages
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    console.log('Console messages:', consoleMessages);
    
    // Try clicking on different areas to see if more tabs appear
    await page.click('.app-nav');
    await page.waitForTimeout(1000);
    
    // Check tabs again after interaction
    const newNavTabs = await page.locator('.nav-tab').all();
    console.log(`Tabs after interaction: ${newNavTabs.length}`);
  });
  
  test('check backend API endpoints', async ({ page }) => {
    // Test if additional API endpoints are available
    const endpoints = [
      '/api/health',
      '/api/laundry-slots',
      '/api/requests'
    ];
    
    for (const endpoint of endpoints) {
      try {
        const response = await page.request.get(`https://roomie-roster.onrender.com${endpoint}`);
        console.log(`${endpoint}: ${response.status()} ${response.statusText()}`);
      } catch (error) {
        console.log(`${endpoint}: ERROR - ${error.message}`);
      }
    }
  });
  
  test('compare with expected frontend build', async ({ page }) => {
    await page.goto('https://roomie-roster.onrender.com/');
    await page.waitForLoadState('networkidle');
    
    // Check if React components are loaded properly
    const hasReactRoot = await page.locator('#root').count() > 0;
    console.log('React root element present:', hasReactRoot);
    
    // Check for component classes that should exist
    const expectedComponents = [
      'LaundryScheduler',
      'RequestManager'
    ];
    
    for (const component of expectedComponents) {
      // Check if component files are included in the build
      const hasComponent = await page.evaluate((componentName) => {
        return window[componentName] !== undefined || 
               document.querySelector(`[class*="${componentName}"]`) !== null;
      }, component);
      console.log(`${component} available:`, hasComponent);
    }
    
    // Check the build timestamp or version
    const buildInfo = await page.evaluate(() => {
      return {
        reactVersion: window.React?.version,
        buildTimestamp: document.querySelector('meta[name="build-timestamp"]')?.content,
        lastModified: document.lastModified
      };
    });
    console.log('Build info:', buildInfo);
  });
  
});