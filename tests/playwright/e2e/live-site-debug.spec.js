const { test, expect } = require('@playwright/test');

test.describe('Live Site Debug Analysis', () => {
  
  test('debug current live site state', async ({ page }) => {
    await page.goto('https://roomie-roster.onrender.com/');
    await page.waitForLoadState('networkidle');
    
    // Check if the footer has the version update
    const footerExists = await page.locator('.app-footer').count() > 0;
    console.log('Footer exists:', footerExists);
    
    if (footerExists) {
      const footerText = await page.locator('.app-footer p').textContent();
      console.log('Footer text:', footerText);
      
      const hasVersionUpdate = footerText && footerText.includes('v2.0');
      console.log('Has v2.0 update:', hasVersionUpdate);
    }
    
    // Take full page screenshot
    await page.screenshot({ path: 'live-site-current-state.png', fullPage: true });
    
    // Check what's actually loaded in the browser
    const pageInfo = await page.evaluate(() => {
      return {
        title: document.title,
        hasReactRoot: !!document.getElementById('root'),
        scriptTags: Array.from(document.querySelectorAll('script')).map(s => s.src).filter(s => s),
        linkTags: Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(l => l.href),
        bodyContent: document.body.innerHTML.length,
        hasNavTabs: document.querySelectorAll('.nav-tab').length,
        allClassNames: Array.from(new Set(Array.from(document.querySelectorAll('*')).map(el => el.className).filter(c => c))).slice(0, 20)
      };
    });
    
    console.log('Page info:', JSON.stringify(pageInfo, null, 2));
    
    // Check if React has loaded properly
    const reactLoaded = await page.evaluate(() => {
      return window.React !== undefined;
    });
    console.log('React loaded:', reactLoaded);
    
    // Check network requests
    const requests = [];
    page.on('request', request => {
      requests.push({
        url: request.url(),
        method: request.method(),
        resourceType: request.resourceType()
      });
    });
    
    // Reload to capture network requests
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Filter for JS and CSS files
    const staticFiles = requests.filter(req => 
      req.resourceType === 'script' || 
      req.resourceType === 'stylesheet' ||
      req.url.includes('.js') || 
      req.url.includes('.css')
    );
    
    console.log('Static files loaded:', staticFiles.map(f => f.url));
    
    // Check if the main JS bundle contains our components
    const mainJsUrls = staticFiles.filter(f => f.url.includes('main.') && f.url.includes('.js'));
    console.log('Main JS files:', mainJsUrls);
    
    // Test direct access to a component that should exist
    const laundryTabExists = await page.locator('.nav-tab').filter({ hasText: 'Laundry' }).count() > 0;
    const requestsTabExists = await page.locator('.nav-tab').filter({ hasText: 'Requests' }).count() > 0;
    const authTabExists = await page.locator('.nav-tab').filter({ hasText: 'Authentication' }).count() > 0;
    
    console.log('Component checks:');
    console.log('- Laundry tab exists:', laundryTabExists);
    console.log('- Requests tab exists:', requestsTabExists);
    console.log('- Authentication tab exists:', authTabExists);
    
    // Check console errors
    const consoleMessages = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleMessages.push(msg.text());
      }
    });
    
    console.log('Console errors:', consoleMessages);
  });
  
  test('check build timestamp and version', async ({ page }) => {
    // Check if we can detect build information
    const response = await page.request.get('https://roomie-roster.onrender.com/');
    const html = await response.text();
    
    // Look for build artifacts in HTML
    const jsFiles = html.match(/\/static\/js\/main\.[a-f0-9]+\.js/g) || [];
    const cssFiles = html.match(/\/static\/css\/main\.[a-f0-9]+\.css/g) || [];
    
    console.log('JS files in HTML:', jsFiles);
    console.log('CSS files in HTML:', cssFiles);
    
    // Compare with our local build
    const expectedJsFile = 'main.d0ec73d3.js';
    const expectedCssFile = 'main.641d6efc.css';
    
    const hasExpectedJs = html.includes(expectedJsFile);
    const hasExpectedCss = html.includes(expectedCssFile);
    
    console.log('Expected JS file present:', hasExpectedJs);
    console.log('Expected CSS file present:', hasExpectedCss);
    
    if (!hasExpectedJs) {
      console.log('❌ Build files don\'t match - deployment not updated');
    } else {
      console.log('✅ Build files match - deployment should be updated');
    }
  });
  
});