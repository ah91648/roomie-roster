#!/usr/bin/env node
/**
 * Build verification script for RoomieRoster frontend
 *
 * This script verifies that the production build is valid and optimized.
 * Run after: npm run build
 *
 * Checks:
 * - Build directory exists
 * - Critical files present (index.html, static assets)
 * - Bundle size within acceptable limits
 * - No source maps in production build (security)
 * - Asset optimization
 */

const fs = require('fs');
const path = require('path');

// Color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  blue: '\x1b[34m'
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function success(message) {
  log(`✅ ${message}`, colors.green);
}

function warning(message) {
  log(`⚠️  ${message}`, colors.yellow);
}

function error(message) {
  log(`❌ ${message}`, colors.red);
}

function header(message) {
  log(`\n${message}`, colors.blue);
  log('='.repeat(60), colors.blue);
}

// Get file size in human-readable format
function getFileSize(filepath) {
  const stats = fs.statSync(filepath);
  const sizeInKB = stats.size / 1024;
  const sizeInMB = sizeInKB / 1024;

  if (sizeInMB >= 1) {
    return `${sizeInMB.toFixed(2)} MB`;
  } else {
    return `${sizeInKB.toFixed(2)} KB`;
  }
}

// Get directory size
function getDirectorySize(dirPath) {
  let totalSize = 0;

  function traverse(currentPath) {
    const files = fs.readdirSync(currentPath);

    files.forEach(file => {
      const filePath = path.join(currentPath, file);
      const stats = fs.statSync(filePath);

      if (stats.isDirectory()) {
        traverse(filePath);
      } else {
        totalSize += stats.size;
      }
    });
  }

  traverse(dirPath);
  return totalSize;
}

// Main verification function
function verifyBuild() {
  header('RoomieRoster Frontend Build Verification');

  const buildDir = path.join(__dirname, '..', 'build');
  let hasErrors = false;
  let hasWarnings = false;

  // Check 1: Build directory exists
  header('1. Checking Build Directory');
  if (!fs.existsSync(buildDir)) {
    error('Build directory not found');
    error(`Expected: ${buildDir}`);
    error('Run: npm run build');
    return 1;
  }
  success('Build directory exists');

  // Check 2: Critical files
  header('2. Checking Critical Files');
  const criticalFiles = [
    'index.html',
    'static/js',
    'static/css'
  ];

  criticalFiles.forEach(file => {
    const filePath = path.join(buildDir, file);
    if (fs.existsSync(filePath)) {
      success(`Found: ${file}`);
    } else {
      error(`Missing: ${file}`);
      hasErrors = true;
    }
  });

  // Check 3: Bundle sizes
  header('3. Analyzing Bundle Sizes');

  const jsDir = path.join(buildDir, 'static', 'js');
  if (fs.existsSync(jsDir)) {
    const jsFiles = fs.readdirSync(jsDir).filter(f => f.endsWith('.js') && !f.endsWith('.map'));

    jsFiles.forEach(file => {
      const filePath = path.join(jsDir, file);
      const size = getFileSize(filePath);

      // Main bundle should be under 500KB for good performance
      const sizeInKB = fs.statSync(filePath).size / 1024;

      if (file.includes('main')) {
        if (sizeInKB > 500) {
          warning(`Main bundle size: ${size} (recommend < 500KB)`);
          warning('Consider code splitting or lazy loading');
          hasWarnings = true;
        } else if (sizeInKB > 300) {
          warning(`Main bundle size: ${size} (good, but could be better)`);
          hasWarnings = true;
        } else {
          success(`Main bundle size: ${size} (excellent)`);
        }
      } else {
        log(`  ${file}: ${size}`);
      }
    });

    // Total JS size
    const totalJSSize = jsFiles.reduce((total, file) => {
      return total + fs.statSync(path.join(jsDir, file)).size;
    }, 0);

    const totalJSKB = totalJSSize / 1024;
    log(`\nTotal JavaScript: ${(totalJSKB / 1024).toFixed(2)} MB`);

    if (totalJSKB > 1024) { // > 1MB
      warning(`Total JS size is large (${(totalJSKB / 1024).toFixed(2)} MB)`);
      warning('Consider: code splitting, lazy loading Recharts, tree shaking');
      hasWarnings = true;
    }
  }

  // Check 4: Source maps (should NOT be present in production)
  header('4. Checking for Source Maps');

  const sourceMapFiles = [];
  function findSourceMaps(dir) {
    const files = fs.readdirSync(dir);
    files.forEach(file => {
      const filePath = path.join(dir, file);
      if (fs.statSync(filePath).isDirectory()) {
        findSourceMaps(filePath);
      } else if (file.endsWith('.map')) {
        sourceMapFiles.push(path.relative(buildDir, filePath));
      }
    });
  }

  findSourceMaps(buildDir);

  if (sourceMapFiles.length > 0) {
    warning(`Found ${sourceMapFiles.length} source map file(s):`);
    sourceMapFiles.forEach(file => log(`  - ${file}`));
    warning('Source maps expose code structure - should be disabled in production');
    warning('Check: GENERATE_SOURCEMAP=false in build script');
    hasWarnings = true;
  } else {
    success('No source maps found (good for production)');
  }

  // Check 5: index.html validation
  header('5. Validating index.html');

  const indexPath = path.join(buildDir, 'index.html');
  const indexContent = fs.readFileSync(indexPath, 'utf8');

  // Check for asset references
  if (indexContent.includes('/static/js/main')) {
    success('JavaScript bundle referenced');
  } else {
    error('Main JavaScript bundle not found in index.html');
    hasErrors = true;
  }

  if (indexContent.includes('/static/css/main')) {
    success('CSS bundle referenced');
  } else {
    warning('Main CSS bundle not found in index.html');
    hasWarnings = true;
  }

  // Check for React root
  if (indexContent.includes('id="root"')) {
    success('React root element present');
  } else {
    error('React root element (#root) not found');
    hasErrors = true;
  }

  // Check 6: Overall build size
  header('6. Overall Build Size');

  const totalSize = getDirectorySize(buildDir);
  const totalMB = totalSize / (1024 * 1024);

  log(`Total build size: ${totalMB.toFixed(2)} MB`);

  if (totalMB > 10) {
    warning('Build size is large (> 10MB)');
    warning('Consider: image optimization, code splitting, asset cleanup');
    hasWarnings = true;
  } else if (totalMB > 5) {
    warning(`Build size is acceptable (${totalMB.toFixed(2)} MB)`);
  } else {
    success(`Build size is good (${totalMB.toFixed(2)} MB)`);
  }

  // Summary
  header('Verification Summary');

  if (hasErrors) {
    error('BUILD VERIFICATION FAILED');
    error('Fix errors above before deploying');
    return 1;
  } else if (hasWarnings) {
    warning('BUILD VERIFICATION PASSED WITH WARNINGS');
    warning('Consider addressing warnings for optimal performance');
    return 0;
  } else {
    success('BUILD VERIFICATION PASSED');
    success('Build is ready for production deployment');
    return 0;
  }
}

// Run verification
const exitCode = verifyBuild();
process.exit(exitCode);
