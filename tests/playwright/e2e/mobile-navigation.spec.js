const { test, expect, devices } = require('@playwright/test');

test.describe('Mobile Navigation', () => {
  
  test('verify tab labels are visible on mobile Safari', async ({ browser }) => {
    // Create a mobile Safari context
    const context = await browser.newContext({
      ...devices['iPhone 13 Pro'],
      // Override user agent to specifically test Safari on iOS
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
    });
    
    const page = await context.newPage();
    
    // Navigate to the application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Wait for navigation to load
    await page.waitForSelector('.nav-tabs', { timeout: 10000 });
    
    // Find all navigation tabs
    const navTabs = await page.locator('.nav-tab').all();
    console.log(`Found ${navTabs.length} navigation tabs on mobile`);
    
    // Expected tabs with both icons and labels
    const expectedTabs = [
      { label: 'Assignments', icon: '📋' },
      { label: 'Roommates', icon: '👥' },
      { label: 'Chores', icon: '🧹' },
      { label: 'Laundry', icon: '🧺' },
      { label: 'Shopping List', icon: '🛒' },
      { label: 'Requests', icon: '🙋' },
      { label: 'Calendar Settings', icon: '📅' },
      { label: 'Authentication', icon: '🔐' }
    ];
    
    // Verify each tab has both icon and visible text label
    for (let i = 0; i < Math.min(navTabs.length, expectedTabs.length); i++) {
      const tab = navTabs[i];
      const expected = expectedTabs[i];
      
      // Check if tab icon is present
      const iconElement = tab.locator('.tab-icon');
      const iconExists = await iconElement.count() > 0;
      console.log(`Tab ${i}: Icon exists: ${iconExists}`);
      
      if (iconExists) {
        const iconText = await iconElement.textContent();
        console.log(`Tab ${i}: Icon text: "${iconText}"`);
        expect(iconText.trim()).toBe(expected.icon);
      }
      
      // Check if tab label is present and visible
      const labelElement = tab.locator('.tab-label');
      const labelExists = await labelElement.count() > 0;
      console.log(`Tab ${i}: Label exists: ${labelExists}`);
      
      if (labelExists) {
        const labelText = await labelElement.textContent();
        const isVisible = await labelElement.isVisible();
        console.log(`Tab ${i}: Label text: "${labelText}", Visible: ${isVisible}`);
        
        expect(labelText.trim()).toBe(expected.label);
        expect(isVisible).toBe(true);
      }
      
      // Verify the tab is structured correctly (icon above text)
      const tabStyles = await tab.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return {
          flexDirection: styles.flexDirection,
          textAlign: styles.textAlign,
          gap: styles.gap
        };
      });
      
      console.log(`Tab ${i}: Styles:`, tabStyles);
      expect(tabStyles.flexDirection).toBe('column');
      expect(tabStyles.textAlign).toBe('center');
    }
    
    // Take a mobile screenshot for verification
    await page.screenshot({ 
      path: 'tests/playwright/screenshots/mobile-navigation.png', 
      fullPage: true 
    });
    
    console.log('✅ Mobile navigation test completed successfully');
    
    await context.close();
  });
  
  test('verify mobile navigation responsiveness', async ({ browser }) => {
    // Test various mobile device sizes
    const devices_to_test = [
      { name: 'iPhone SE', ...devices['iPhone SE'] },
      { name: 'iPhone 13', ...devices['iPhone 13'] },
      { name: 'iPad Mini', ...devices['iPad Mini'] },
      { name: 'Samsung Galaxy S21', ...devices['Galaxy S21'] }
    ];
    
    for (const device of devices_to_test) {
      console.log(`Testing on ${device.name}...`);
      
      const context = await browser.newContext(device);
      const page = await context.newPage();
      
      await page.goto('http://localhost:3000');
      await page.waitForLoadState('networkidle');
      await page.waitForSelector('.nav-tabs', { timeout: 10000 });
      
      // Check if navigation tabs are responsive
      const navContainer = page.locator('.nav-container');
      const isVisible = await navContainer.isVisible();
      expect(isVisible).toBe(true);
      
      // Check if scroll buttons are present for narrow screens
      const scrollButtons = await page.locator('.nav-scroll-btn').count();
      console.log(`${device.name}: Scroll buttons count: ${scrollButtons}`);
      
      // Verify tabs have appropriate mobile styling
      const firstTab = page.locator('.nav-tab').first();
      const tabExists = await firstTab.count() > 0;
      
      if (tabExists) {
        const fontSize = await firstTab.evaluate(el => {
          return window.getComputedStyle(el).fontSize;
        });
        console.log(`${device.name}: Tab font size: ${fontSize}`);
        
        // Font size should be smaller on mobile (0.8rem = ~12.8px on most browsers)
        expect(parseFloat(fontSize)).toBeLessThan(16); // Less than 1rem
      }
      
      // Take device-specific screenshot
      await page.screenshot({ 
        path: `tests/playwright/screenshots/navigation-${device.name.toLowerCase().replace(/\s+/g, '-')}.png`,
        fullPage: true 
      });
      
      await context.close();
    }
    
    console.log('✅ Mobile responsiveness test completed successfully');
  });
  
  test('verify tab functionality on mobile', async ({ browser }) => {
    const context = await browser.newContext({
      ...devices['iPhone 13'],
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
    });
    
    const page = await context.newPage();
    
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.nav-tabs', { timeout: 10000 });
    
    // Test clicking on different tabs
    const tabsToTest = ['Roommates', 'Chores', 'Shopping List'];
    
    for (const tabName of tabsToTest) {
      console.log(`Testing ${tabName} tab click on mobile...`);
      
      // Find and click the tab by its label
      const tabSelector = `.nav-tab:has-text("${tabName}")`;
      const tabExists = await page.locator(tabSelector).count() > 0;
      
      if (tabExists) {
        await page.click(tabSelector);
        await page.waitForTimeout(1000);
        
        // Check if the tab is now active
        const isActive = await page.locator(`${tabSelector}.active`).count() > 0;
        console.log(`${tabName} tab is active: ${isActive}`);
        expect(isActive).toBe(true);
        
        // Check if main content changed
        const hasContent = await page.locator('.main-content').count() > 0;
        console.log(`${tabName} content loaded: ${hasContent}`);
        expect(hasContent).toBe(true);
        
        // Take screenshot of the active tab
        await page.screenshot({ 
          path: `tests/playwright/screenshots/mobile-${tabName.toLowerCase().replace(/\s+/g, '-')}-active.png` 
        });
      } else {
        console.log(`❌ ${tabName} tab not found on mobile`);
        throw new Error(`${tabName} tab not found on mobile`);
      }
    }
    
    console.log('✅ Mobile tab functionality test completed successfully');
    
    await context.close();
  });
  
});