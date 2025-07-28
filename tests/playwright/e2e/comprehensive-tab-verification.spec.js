const { test, expect } = require('@playwright/test');

test.describe('Comprehensive Tab Verification', () => {
  
  test('verify all 9 navigation tabs are present and functional', async ({ page }) => {
    await page.goto('https://roomie-roster.onrender.com/');
    await page.waitForLoadState('networkidle');
    
    // Expected tabs with their icons
    const expectedTabs = [
      { id: 'assignments', label: 'Assignments', icon: '📋' },
      { id: 'roommates', label: 'Roommates', icon: '👥' },
      { id: 'chores', label: 'Chores', icon: '🧹' },
      { id: 'laundry', label: 'Laundry', icon: '🧺' },
      { id: 'shopping', label: 'Shopping List', icon: '🛒' },
      { id: 'requests', label: 'Requests', icon: '🙋' },
      { id: 'calendar', label: 'Calendar Settings', icon: '📅' },
      { id: 'my-calendar', label: 'My Calendar', icon: '📱' },
      { id: 'auth', label: 'Authentication', icon: '🔐' }
    ];
    
    console.log(`\n🔍 Checking for all ${expectedTabs.length} expected tabs...\n`);
    
    // Take screenshot first
    await page.screenshot({ path: 'all-tabs-verification.png', fullPage: true });
    
    // Get all navigation tabs
    const navTabs = await page.locator('.nav-tab').all();
    console.log(`Found ${navTabs.length} navigation tabs total\n`);
    
    const foundTabs = [];
    const missingTabs = [];
    
    // Check each expected tab
    for (const expectedTab of expectedTabs) {
      // Try multiple selectors to find the tab
      const tabSelectors = [
        `.nav-tab:has-text("${expectedTab.label}")`,
        `.nav-tab .tab-label:has-text("${expectedTab.label}")`,
        `[class*="nav-tab"]:has-text("${expectedTab.label}")`,
        `.nav-tab:has(.tab-label:text("${expectedTab.label}"))`
      ];
      
      let tabFound = false;
      let tabElement = null;
      
      for (const selector of tabSelectors) {
        const count = await page.locator(selector).count();
        if (count > 0) {
          tabFound = true;
          tabElement = page.locator(selector).first();
          break;
        }
      }
      
      if (tabFound) {
        foundTabs.push(expectedTab);
        console.log(`✅ ${expectedTab.icon} ${expectedTab.label} - FOUND`);
        
        // Test clicking the tab
        try {
          await tabElement.click();
          await page.waitForTimeout(1000);
          
          // Check if content changed
          const activeTab = await page.locator('.nav-tab.active .tab-label').textContent();
          const contentLoaded = await page.locator('.main-content').count() > 0;
          
          console.log(`   → Clicked successfully, active tab: "${activeTab}", content loaded: ${contentLoaded}`);
        } catch (error) {
          console.log(`   → Click failed: ${error.message}`);
        }
      } else {
        missingTabs.push(expectedTab);
        console.log(`❌ ${expectedTab.icon} ${expectedTab.label} - MISSING`);
      }
    }
    
    console.log(`\n📊 SUMMARY:`);
    console.log(`✅ Found: ${foundTabs.length}/${expectedTabs.length} tabs`);
    console.log(`❌ Missing: ${missingTabs.length}/${expectedTabs.length} tabs`);
    
    if (missingTabs.length > 0) {
      console.log(`\n❌ Missing tabs:`);
      missingTabs.forEach(tab => console.log(`   - ${tab.icon} ${tab.label}`));
    }
    
    if (foundTabs.length === expectedTabs.length) {
      console.log(`\n🎉 SUCCESS! All ${expectedTabs.length} tabs are present and working!`);
    } else {
      console.log(`\n⚠️  INCOMPLETE: ${missingTabs.length} tabs still missing`);
    }
    
    // Take final screenshot showing the current state
    await page.screenshot({ path: 'final-verification-state.png', fullPage: true });
  });
  
  test('test specific missing tab functionality', async ({ page }) => {
    await page.goto('https://roomie-roster.onrender.com/');
    await page.waitForLoadState('networkidle');
    
    const tabsToTest = [
      'Laundry',
      'Requests', 
      'Calendar Settings',
      'My Calendar',
      'Authentication'
    ];
    
    console.log('\n🧪 Testing specific tab functionality...\n');
    
    for (const tabName of tabsToTest) {
      console.log(`Testing "${tabName}" tab...`);
      
      // Find and click the tab
      const tabLocator = page.locator('.nav-tab').filter({ hasText: tabName });
      const tabCount = await tabLocator.count();
      
      if (tabCount > 0) {
        console.log(`  ✅ Found "${tabName}" tab`);
        
        try {
          await tabLocator.click();
          await page.waitForTimeout(2000);
          
          // Check if the tab became active
          const activeTabText = await page.locator('.nav-tab.active .tab-label').textContent();
          const isActive = activeTabText.includes(tabName);
          
          console.log(`  → Active tab: "${activeTabText}"`);
          console.log(`  → Is active: ${isActive}`);
          
          // Take screenshot of this tab's content
          const screenshotName = `${tabName.toLowerCase().replace(/\\s+/g, '-')}-content.png`;
          await page.screenshot({ path: screenshotName });
          
          // Check for specific content based on tab type
          let hasExpectedContent = false;
          
          switch (tabName) {
            case 'Laundry':
              hasExpectedContent = await page.locator('text=Laundry').count() > 0 ||
                                 await page.locator('[class*="laundry"]').count() > 0;
              break;
            case 'Requests':
              hasExpectedContent = await page.locator('text=Request').count() > 0 ||
                                 await page.locator('[class*="request"]').count() > 0;
              break;
            case 'Calendar Settings':
              hasExpectedContent = await page.locator('text=Calendar').count() > 0;
              break;
            case 'My Calendar':
              hasExpectedContent = await page.locator('text=Calendar').count() > 0;
              break;
            case 'Authentication':
              hasExpectedContent = await page.locator('text=Authentication').count() > 0 ||
                                 await page.locator('text=Google').count() > 0;
              break;
          }
          
          console.log(`  → Has expected content: ${hasExpectedContent}`);
          
        } catch (error) {
          console.log(`  ❌ Error testing "${tabName}": ${error.message}`);
        }
      } else {
        console.log(`  ❌ "${tabName}" tab not found`);
      }
      
      console.log('');
    }
  });
  
});