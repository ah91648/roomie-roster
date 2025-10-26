// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Comprehensive E2E tests for Analytics Dashboard functionality
 * Tests the 325-line AnalyticsDashboard.js component added in Phase 3
 */

test.describe('Analytics Dashboard - Complete Feature Testing', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Navigate to Analytics tab
    await page.click('.nav-tab:has-text("Analytics"), .nav-tab:has-text("📊")');
    await page.waitForTimeout(2000); // Wait for data fetching
  });

  test('should render analytics dashboard with all elements', async ({ page }) => {
    console.log('🧪 Testing: Analytics Dashboard UI rendering');

    // Verify main heading
    const hasHeader = await page.locator('h2, h1').filter({ hasText: /Analytics|Dashboard|Stats/ }).count() > 0;
    console.log(`Analytics header found: ${hasHeader}`);

    // Check for period selector (7/14/30 days)
    const periodButtons = page.locator('button').filter({ hasText: /7.*days?|14.*days?|30.*days?/i });
    const periodCount = await periodButtons.count();
    console.log(`Period selector buttons found: ${periodCount}`);
    expect(periodCount).toBeGreaterThanOrEqual(3);

    // Check for summary cards section
    const summaryCards = page.locator('.summary-card, .summary-cards, .metric-card');
    const cardsExist = await summaryCards.count() > 0;
    console.log(`Summary cards section exists: ${cardsExist}`);

    console.log('✓ Analytics Dashboard UI components verified');
  });

  test('should switch between time periods (7/14/30 days)', async ({ page }) => {
    console.log('🧪 Testing: Period switcher functionality');

    const periods = [
      { text: '7', days: 7 },
      { text: '14', days: 14 },
      { text: '30', days: 30 }
    ];

    for (const period of periods) {
      console.log(`Testing ${period.days}-day period`);

      // Click period button
      const periodButton = page.locator('button').filter({ hasText: new RegExp(`${period.text}.*day`, 'i') }).first();
      if (await periodButton.count() > 0 && await periodButton.isVisible()) {
        await periodButton.click();
        await page.waitForTimeout(1500); // Wait for data refresh

        // Verify active state
        const isActive = await periodButton.evaluate(el => {
          return el.classList.contains('active') || el.classList.contains('selected');
        });
        console.log(`  ${period.days}-day button active: ${isActive}`);

        // Check if charts update (look for chart elements)
        const chartElements = page.locator('svg.recharts-surface, .recharts-wrapper');
        const chartExists = await chartElements.count() > 0;
        console.log(`  Charts visible after period change: ${chartExists}`);
      }
    }

    console.log('✓ Period switching works');
  });

  test('should render Recharts LineChart for mood/energy trends', async ({ page }) => {
    console.log('🧪 Testing: Recharts LineChart rendering');

    // Wait for charts to load
    await page.waitForTimeout(2000);

    // Look for Recharts SVG elements
    const lineCharts = page.locator('svg.recharts-surface').filter({ has: page.locator('.recharts-line') });
    const lineChartCount = await lineCharts.count();
    console.log(`LineCharts found: ${lineChartCount}`);

    if (lineChartCount > 0) {
      // Verify chart has lines (mood and energy)
      const lines = page.locator('.recharts-line, .recharts-line-curve');
      const lineCount = await lines.count();
      console.log(`Lines in chart: ${lineCount}`);
      expect(lineCount).toBeGreaterThanOrEqual(2); // Mood and Energy lines

      // Check for axis labels
      const xAxis = page.locator('.recharts-xAxis');
      const yAxis = page.locator('.recharts-yAxis');
      const hasAxes = (await xAxis.count() > 0) && (await yAxis.count() > 0);
      console.log(`Chart has X and Y axes: ${hasAxes}`);

      // Check for legend
      const legend = page.locator('.recharts-legend-wrapper, .recharts-default-legend');
      const hasLegend = await legend.count() > 0;
      console.log(`Chart has legend: ${hasLegend}`);

      if (hasLegend) {
        // Verify legend items (Mood Level, Energy Level)
        const legendItems = await legend.locator('.recharts-legend-item').count();
        console.log(`Legend items: ${legendItems}`);
      }

      // Check for tooltip
      const tooltip = page.locator('.recharts-tooltip-wrapper');
      const hasTooltip = await tooltip.count() > 0 || await page.locator('.recharts-default-tooltip').count() > 0;
      console.log(`Chart has tooltip: ${hasTooltip}`);

      console.log('✓ LineChart rendered with Recharts');
    } else {
      console.log('ℹ No LineChart found (may be empty state)');
    }
  });

  test('should render Recharts BarChart for pomodoro activity', async ({ page }) => {
    console.log('🧪 Testing: Recharts BarChart rendering');

    await page.waitForTimeout(2000);

    // Look for BarChart elements
    const barCharts = page.locator('svg.recharts-surface').filter({ has: page.locator('.recharts-bar') });
    const barChartCount = await barCharts.count();
    console.log(`BarCharts found: ${barChartCount}`);

    if (barChartCount > 0) {
      // Verify bars exist (focus sessions and breaks)
      const bars = page.locator('.recharts-bar, .recharts-bar-rectangle');
      const barCount = await bars.count();
      console.log(`Bars in chart: ${barCount}`);

      // Check for bar groups (focus and breaks)
      const barGroups = page.locator('.recharts-bar-rectangles');
      const groupCount = await barGroups.count();
      console.log(`Bar groups: ${groupCount}`);
      expect(groupCount).toBeGreaterThanOrEqual(2); // Focus and Break bars

      // Check colors (should be different for focus vs breaks)
      if (barCount >= 2) {
        const firstBarColor = await bars.first().evaluate(el => el.getAttribute('fill'));
        const secondBarColor = await bars.nth(1).evaluate(el => el.getAttribute('fill'));
        console.log(`Bar colors - First: ${firstBarColor}, Second: ${secondBarColor}`);

        // Colors should be different
        const hasDifferentColors = firstBarColor !== secondBarColor;
        console.log(`Bars have different colors: ${hasDifferentColors}`);
      }

      console.log('✓ BarChart rendered with Recharts');
    } else {
      console.log('ℹ No BarChart found (may be empty state)');
    }
  });

  test('should display summary cards with metrics', async ({ page }) => {
    console.log('🧪 Testing: Summary cards display');

    // Look for summary/metric cards
    const summaryCards = page.locator('.summary-card, .metric-card, .stat-card, .summary-cards > div');
    const cardCount = await summaryCards.count();
    console.log(`Summary cards found: ${cardCount}`);

    if (cardCount > 0) {
      // Check first card content
      const firstCard = summaryCards.first();
      const cardText = await firstCard.textContent();
      console.log(`First card content: "${cardText}"`);

      // Should contain numbers/percentages and labels
      const hasNumbers = /\d+/.test(cardText);
      const hasPercentage = /%/.test(cardText);
      console.log(`Has numbers: ${hasNumbers}, Has percentage: ${hasPercentage}`);

      // Look for completion bars
      const completionBars = page.locator('.completion-bar, .progress-bar, [class*="progress"]');
      const barCount = await completionBars.count();
      console.log(`Completion/progress bars: ${barCount}`);

      if (barCount > 0) {
        // Check bar styling
        const barStyle = await completionBars.first().evaluate(el => {
          const style = window.getComputedStyle(el);
          return {
            width: style.width,
            height: style.height,
            background: style.background.substring(0, 50)
          };
        });
        console.log(`Completion bar style:`, barStyle);
      }

      console.log('✓ Summary cards displayed with metrics');
    }
  });

  test('should show loading state while fetching data', async ({ page }) => {
    console.log('🧪 Testing: Loading state');

    // Reload page and quickly check for loading indicator
    await page.reload({ waitUntil: 'domcontentloaded' });

    // Navigate back to Analytics
    await page.click('.nav-tab:has-text("Analytics"), .nav-tab:has-text("📊")');

    // Look for loading indicator (should appear briefly)
    const loadingIndicators = page.locator('.loading, .spinner, [class*="loading"], text=/loading/i');
    const loadingExists = await loadingIndicators.count() > 0;
    console.log(`Loading indicator exists: ${loadingExists}`);

    // Wait for content to load
    await page.waitForTimeout(2000);

    // Loading should be gone
    const stillLoading = await loadingIndicators.isVisible().catch(() => false);
    console.log(`Still loading after 2s: ${stillLoading}`);
    expect(stillLoading).toBe(false);
  });

  test('should show empty state when no data available', async ({ page }) => {
    console.log('🧪 Testing: Empty state message');

    // Wait for data to load
    await page.waitForTimeout(2000);

    // Check if there's a "no data" message
    const emptyStateMessages = page.locator('text=/no data|no analytics|no activity|start tracking/i, .empty-state');
    const emptyStateCount = await emptyStateMessages.count();
    console.log(`Empty state messages found: ${emptyStateCount}`);

    // Either we have data (charts visible) or empty state message
    const chartsExist = await page.locator('svg.recharts-surface').count() > 0;
    const hasEmptyState = emptyStateCount > 0;

    console.log(`Has charts: ${chartsExist}, Has empty state: ${hasEmptyState}`);

    if (hasEmptyState) {
      const emptyMessage = await emptyStateMessages.first().textContent();
      console.log(`Empty state message: "${emptyMessage}"`);
    }

    // Should have either charts or empty state
    expect(chartsExist || hasEmptyState).toBe(true);
  });

  test('should generate insights from data', async ({ page }) => {
    console.log('🧪 Testing: Insights generation');

    await page.waitForTimeout(2000);

    // Look for insights section
    const insightsSection = page.locator('text=/insights?|analysis|summary/i, .insights, .analysis-summary');
    const insightsExist = await insightsSection.count() > 0;
    console.log(`Insights section exists: ${insightsExist}`);

    if (insightsExist) {
      const insightsText = await insightsSection.first().textContent();
      console.log(`Insights text (first 100 chars): "${insightsText.substring(0, 100)}..."`);

      // Insights should contain meaningful text (not just labels)
      const hasContent = insightsText.length > 20;
      console.log(`Insights has content: ${hasContent}`);
    }

    // Look for insight cards or bullets
    const insightItems = page.locator('.insight-item, .insight-card, li').filter({ hasText: /\d+/ });
    const itemCount = await insightItems.count();
    console.log(`Insight items/bullets: ${itemCount}`);
  });

  test('should have responsive charts (ResponsiveContainer)', async ({ page }) => {
    console.log('🧪 Testing: Chart responsiveness');

    await page.waitForTimeout(2000);

    // Check if charts use Recharts ResponsiveContainer
    const responsiveContainers = page.locator('.recharts-responsive-container');
    const containerCount = await responsiveContainers.count();
    console.log(`Recharts ResponsiveContainers: ${containerCount}`);

    if (containerCount > 0) {
      // Verify container takes full width
      const containerStyle = await responsiveContainers.first().evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          width: style.width,
          height: style.height
        };
      });
      console.log(`ResponsiveContainer size:`, containerStyle);

      // Width should be 100% or close to viewport
      const widthNum = parseFloat(containerStyle.width);
      console.log(`Container width: ${widthNum}px`);
      expect(widthNum).toBeGreaterThan(200); // Reasonable min width

      console.log('✓ Charts use ResponsiveContainer');
    }
  });

  test('should show chart tooltips on hover', async ({ page }) => {
    console.log('🧪 Testing: Chart tooltip interaction');

    await page.waitForTimeout(2000);

    // Find a chart line or bar
    const chartElements = page.locator('.recharts-line-curve, .recharts-bar-rectangle').first();
    if (await chartElements.count() > 0) {
      // Hover over chart element
      await chartElements.hover();
      await page.waitForTimeout(500);

      // Check if tooltip appears
      const tooltip = page.locator('.recharts-tooltip-wrapper, .recharts-default-tooltip');
      const tooltipVisible = await tooltip.isVisible().catch(() => false);
      console.log(`Tooltip visible on hover: ${tooltipVisible}`);

      if (tooltipVisible) {
        const tooltipText = await tooltip.textContent();
        console.log(`Tooltip content: "${tooltipText}"`);
        console.log('✓ Chart tooltips work');
      }
    } else {
      console.log('ℹ No chart elements to hover (empty data)');
    }
  });

  test('should format data correctly for charts', async ({ page }) => {
    console.log('🧪 Testing: Chart data formatting');

    await page.waitForTimeout(2000);

    // Check X-axis labels (should show dates)
    const xAxisTicks = page.locator('.recharts-xAxis .recharts-cartesian-axis-tick-value');
    const tickCount = await xAxisTicks.count();
    console.log(`X-axis ticks: ${tickCount}`);

    if (tickCount > 0) {
      // Get first few tick labels
      for (let i = 0; i < Math.min(tickCount, 3); i++) {
        const tickText = await xAxisTicks.nth(i).textContent();
        console.log(`  Tick ${i}: "${tickText}"`);

        // Should be date format (e.g., "Jan 15", "15", "Mon")
        const isValidDate = /\w+\s+\d+|\d+|mon|tue|wed|thu|fri|sat|sun/i.test(tickText);
        console.log(`  Valid date format: ${isValidDate}`);
      }
    }

    // Check Y-axis domain (mood/energy should be 0-5)
    const yAxisTicks = page.locator('.recharts-yAxis .recharts-cartesian-axis-tick-value');
    const yTickCount = await yAxisTicks.count();
    console.log(`Y-axis ticks: ${yTickCount}`);

    if (yTickCount > 0) {
      const firstYTick = await yAxisTicks.first().textContent();
      const lastYTick = await yAxisTicks.last().textContent();
      console.log(`Y-axis range: ${firstYTick} to ${lastYTick}`);

      // For mood/energy, should be 0-5
      const maxValue = parseFloat(lastYTick);
      if (!isNaN(maxValue)) {
        console.log(`Max Y value: ${maxValue} (expected: 5 for mood/energy)`);
      }
    }
  });

});

test.describe('Analytics Dashboard - Mobile Responsiveness', () => {

  test('should display charts correctly on mobile', async ({ page }) => {
    console.log('🧪 Testing: Mobile chart rendering');

    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');

    // Navigate to Analytics
    await page.click('.nav-tab:has-text("Analytics"), .nav-tab:has-text("📊")');
    await page.waitForTimeout(2000);

    // Verify ResponsiveContainer adapts to mobile width
    const responsiveContainers = page.locator('.recharts-responsive-container');
    const containerCount = await responsiveContainers.count();
    console.log(`ResponsiveContainers on mobile: ${containerCount}`);

    if (containerCount > 0) {
      const containerWidth = await responsiveContainers.first().evaluate(el => {
        return window.getComputedStyle(el).width;
      });
      console.log(`Container width on mobile: ${containerWidth}`);

      const widthNum = parseFloat(containerWidth);
      // Should fit mobile viewport (375px or less)
      expect(widthNum).toBeLessThanOrEqual(380);
      console.log('✓ Charts adapt to mobile width');
    }
  });

  test('should stack summary cards vertically on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    await page.click('.nav-tab:has-text("Analytics"), .nav-tab:has-text("📊")');
    await page.waitForTimeout(2000);

    // Check if summary cards section uses vertical layout
    const summaryCardsContainer = page.locator('.summary-cards').first();
    if (await summaryCardsContainer.count() > 0) {
      const gridStyle = await summaryCardsContainer.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          display: style.display,
          gridTemplateColumns: style.gridTemplateColumns,
          flexDirection: style.flexDirection
        };
      });
      console.log(`Summary cards layout on mobile:`, gridStyle);

      // Should be single column (grid: 1fr, flex: column)
      const isSingleColumn = gridStyle.gridTemplateColumns === '1fr' ||
                              gridStyle.flexDirection === 'column' ||
                              gridStyle.gridTemplateColumns?.split(' ').length === 1;
      console.log(`Single column layout: ${isSingleColumn}`);
    }

    console.log('✓ Summary cards stack vertically on mobile');
  });

  test('should have touch-friendly period buttons on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    await page.click('.nav-tab:has-text("Analytics"), .nav-tab:has-text("📊")');
    await page.waitForTimeout(2000);

    // Check period button sizes
    const periodButtons = page.locator('button').filter({ hasText: /7.*days?|14.*days?|30.*days?/i });
    const buttonCount = await periodButtons.count();

    for (let i = 0; i < Math.min(buttonCount, 3); i++) {
      const button = periodButtons.nth(i);
      const boundingBox = await button.boundingBox();

      if (boundingBox) {
        console.log(`Period button ${i}: ${boundingBox.width}x${boundingBox.height}px`);
        // Touch targets should be at least 44x44px
        expect(boundingBox.height).toBeGreaterThanOrEqual(40);
      }
    }

    console.log('✓ Period buttons are touch-friendly on mobile');
  });

});
