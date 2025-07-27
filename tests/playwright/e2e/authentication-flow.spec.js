const { test, expect } = require('@playwright/test');

test.describe('Google Authentication Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('http://localhost:3000');
    
    // Wait for app to load
    await page.waitForSelector('.app-header');
  });

  test('should display authentication setup when not configured', async ({ page }) => {
    // Navigate to authentication tab
    await page.click('button:has-text("🔐 Authentication")');
    
    // Should show authentication setup page
    await expect(page.locator('h2:has-text("🔐 Google Authentication Setup")')).toBeVisible();
    
    // Should show setup progress
    await expect(page.locator('.setup-progress')).toBeVisible();
    
    // Should show Google API dependencies status
    await expect(page.locator('.step:has-text("Google API Dependencies")')).toBeVisible();
  });

  test('should display auth status correctly', async ({ page }) => {
    // Test auth status endpoint
    const response = await page.request.get('http://localhost:5000/api/auth/status');
    expect(response.ok()).toBeTruthy();
    
    const status = await response.json();
    expect(status).toHaveProperty('google_api_available');
    expect(status).toHaveProperty('credentials_configured');
    expect(status).toHaveProperty('total_users');
  });

  test('should show login button when configured but not authenticated', async ({ page }) => {
    // Mock auth service as configured
    await page.route('**/api/auth/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          google_api_available: true,
          credentials_configured: true,
          total_users: 0
        })
      });
    });
    
    // Reload page to pick up mocked status
    await page.reload();
    
    // Should show Google login button in header
    await expect(page.locator('button:has-text("Sign in with Google")')).toBeVisible();
  });

  test('should handle login button click', async ({ page }) => {
    // Mock configured authentication
    await page.route('**/api/auth/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          google_api_available: true,
          credentials_configured: true,
          total_users: 0
        })
      });
    });

    // Mock Google login initiation
    await page.route('**/api/auth/google-login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          auth_url: 'https://accounts.google.com/oauth/authorize?client_id=test',
          state: 'test-state-token'
        })
      });
    });

    await page.reload();
    
    // Click login button - this should redirect to Google OAuth
    const [newPage] = await Promise.all([
      page.waitForEvent('popup'),
      page.click('button:has-text("Sign in with Google")')
    ]);
    
    // Should open OAuth popup (mocked)
    expect(newPage.url()).toContain('accounts.google.com');
  });

  test('should display user profile when authenticated', async ({ page }) => {
    // Mock authenticated state
    await page.route('**/api/auth/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          google_api_available: true,
          credentials_configured: true,
          total_users: 1
        })
      });
    });

    // Mock user profile
    await page.route('**/api/auth/profile', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            google_id: 'test123',
            email: 'test@example.com',
            name: 'Test User',
            picture: 'https://example.com/avatar.jpg',
            roommate: {
              id: 1,
              name: 'Christine'
            }
          }
        })
      });
    });

    await page.reload();
    
    // Should show user profile in header instead of login button
    await expect(page.locator('.user-profile-compact')).toBeVisible();
    await expect(page.locator('text=Test User')).toBeVisible();
    await expect(page.locator('text=Christine')).toBeVisible();
  });

  test('should show roommate selector for new users', async ({ page }) => {
    // Mock authenticated but unlinked user
    await page.route('**/api/auth/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          google_api_available: true,
          credentials_configured: true,
          total_users: 1
        })
      });
    });

    await page.route('**/api/auth/profile', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            google_id: 'test123',
            email: 'test@example.com',
            name: 'Test User',
            picture: 'https://example.com/avatar.jpg'
            // No roommate linked
          }
        })
      });
    });

    // Mock roommates list
    await page.route('**/api/roommates', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 1, name: 'Christine', current_cycle_points: 3, google_id: null },
          { id: 2, name: 'Angel', current_cycle_points: 8, google_id: null },
          { id: 3, name: 'Joss', current_cycle_points: 0, google_id: null },
          { id: 4, name: 'Alexis', current_cycle_points: 8, google_id: null }
        ])
      });
    });

    await page.reload();
    
    // Should show roommate selector modal
    await expect(page.locator('.modal-overlay')).toBeVisible();
    await expect(page.locator('.roommate-selector')).toBeVisible();
    await expect(page.locator('h2:has-text("Link Your Account")')).toBeVisible();
    
    // Should show available roommates
    await expect(page.locator('.roommate-option:has-text("Christine")')).toBeVisible();
    await expect(page.locator('.roommate-option:has-text("Angel")')).toBeVisible();
    await expect(page.locator('.roommate-option:has-text("Joss")')).toBeVisible();
    await expect(page.locator('.roommate-option:has-text("Alexis")')).toBeVisible();
  });

  test('should handle roommate linking', async ({ page }) => {
    // Mock authenticated but unlinked user
    await page.route('**/api/auth/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          google_api_available: true,
          credentials_configured: true,
          total_users: 1
        })
      });
    });

    await page.route('**/api/auth/profile', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            google_id: 'test123',
            email: 'test@example.com',
            name: 'Test User',
            picture: 'https://example.com/avatar.jpg'
          }
        })
      });
    });

    await page.route('**/api/roommates', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 1, name: 'Christine', current_cycle_points: 3, google_id: null },
          { id: 2, name: 'Angel', current_cycle_points: 8, google_id: null }
        ])
      });
    });

    // Mock successful linking
    await page.route('**/api/auth/link-roommate', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            google_id: 'test123',
            email: 'test@example.com',
            name: 'Test User',
            picture: 'https://example.com/avatar.jpg',
            roommate: {
              id: 1,
              name: 'Christine'
            }
          },
          message: 'Successfully linked to roommate'
        })
      });
    });

    await page.reload();
    
    // Select a roommate
    await page.click('.roommate-option:has-text("Christine")');
    
    // Should show selection
    await expect(page.locator('.roommate-option.selected:has-text("Christine")')).toBeVisible();
    
    // Click link button
    await page.click('button:has-text("Link Account")');
    
    // Should handle the linking (in real test, modal would close)
    await expect(page.locator('button:has-text("Linking...")')).toBeVisible();
  });

  test('should handle logout', async ({ page }) => {
    // Mock authenticated user
    await page.route('**/api/auth/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          google_api_available: true,
          credentials_configured: true,
          total_users: 1
        })
      });
    });

    await page.route('**/api/auth/profile', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            google_id: 'test123',
            email: 'test@example.com',
            name: 'Test User',
            picture: 'https://example.com/avatar.jpg',
            roommate: {
              id: 1,
              name: 'Christine'
            }
          }
        })
      });
    });

    // Mock logout endpoint
    await page.route('**/api/auth/logout', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Successfully logged out'
        })
      });
    });

    await page.reload();
    
    // Should show user profile
    await expect(page.locator('.user-profile-compact')).toBeVisible();
    
    // Click on user profile settings
    await page.click('.user-actions-compact button');
    
    // Note: In a more complete test, we would navigate to a full profile page
    // and test the logout button there, but this tests the basic interaction
  });

  test('should handle authentication errors gracefully', async ({ page }) => {
    // Mock auth service error
    await page.route('**/api/auth/status', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Authentication service unavailable'
        })
      });
    });

    await page.reload();
    
    // Should still show basic UI without crashing
    await expect(page.locator('.app-header')).toBeVisible();
    
    // Navigate to auth tab to see error handling
    await page.click('button:has-text("🔐 Authentication")');
    
    // Should show some form of error or fallback state
    await expect(page.locator('.auth-setup')).toBeVisible();
  });

  test('should maintain authentication state across page refreshes', async ({ page }) => {
    // Mock persistent authentication
    await page.route('**/api/auth/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          google_api_available: true,
          credentials_configured: true,
          total_users: 1
        })
      });
    });

    await page.route('**/api/auth/profile', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            google_id: 'test123',
            email: 'test@example.com',
            name: 'Test User',
            roommate: {
              id: 1,
              name: 'Christine'
            }
          }
        })
      });
    });

    await page.reload();
    
    // Should show authenticated state
    await expect(page.locator('.user-profile-compact')).toBeVisible();
    
    // Refresh page
    await page.reload();
    
    // Should maintain authenticated state
    await expect(page.locator('.user-profile-compact')).toBeVisible();
    await expect(page.locator('text=Test User')).toBeVisible();
  });

});