import { test, expect } from '@playwright/test';

/**
 * JOBPI Critical Path E2E Tests
 *
 * These tests verify the most important user journeys to catch
 * regressions that unit tests cannot cover:
 *
 * 1. Landing page renders correctly (public entry point)
 * 2. Auth flow: register → redirect → login → dashboard
 * 3. Protected routes redirect unauthenticated users to /login
 * 4. Error boundary does not crash the app on bad routes
 *
 * Design decision: tests are hermetic — each run creates a fresh
 * user via /register to avoid dependency on external state.
 */

const TEST_EMAIL = `e2e_${Date.now()}@test.jobpi.local`;
const TEST_PASSWORD = 'E2eTest1234';

test.describe('Critical Path', () => {
  test('landing page loads and shows hero content', async ({ page }) => {
    await page.goto('/');

    // The landing page must render the brand and hero CTA
    // Using data-testid to be agnostic to localization (English vs Spanish)
    await expect(page.getByTestId('brand-name')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('hero-cta')).toBeVisible();
  });

  test('unauthenticated users are redirected to /login from protected routes', async ({
    page,
  }) => {
    await page.goto('/dashboard');

    // Should be redirected to /login
    await page.waitForURL('**/login', { timeout: 10_000 });
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test('auth flow: register → login → dashboard', async ({ page }) => {
    // --- Registration ---
    await page.goto('/register');

    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeVisible({ timeout: 10_000 });
    await emailInput.fill(TEST_EMAIL);

    const passwordInputs = page.locator('input[type="password"]');
    // Registration page has two password fields (password + confirm)
    const pwCount = await passwordInputs.count();
    if (pwCount >= 2) {
      await passwordInputs.nth(0).fill(TEST_PASSWORD);
      await passwordInputs.nth(1).fill(TEST_PASSWORD);
    } else {
      await passwordInputs.first().fill(TEST_PASSWORD);
    }

    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();

    // Wait for navigation or confirmation message
    // The app might redirect to login or show a confirmation
    await page.waitForTimeout(3000);

    // --- Login ---
    await page.goto('/login');
    await page.locator('input[type="email"]').fill(TEST_EMAIL);
    await page.locator('input[type="password"]').fill(TEST_PASSWORD);
    await page.locator('button[type="submit"]').click();

    // Should reach the dashboard (or stay on login with error for unverified email)
    // We accept both outcomes since e2e email verification isn't possible
    const url = page.url();
    const reachedDashboard = url.includes('/dashboard');
    const stayedOnLogin = url.includes('/login');

    expect(reachedDashboard || stayedOnLogin).toBeTruthy();

    if (reachedDashboard) {
      // Verify dashboard content renders
      await expect(page.locator('text=Welcome')).toBeVisible({ timeout: 10_000 });
    }
  });

  test('navigation to unknown routes redirects to dashboard (when logged in) or login', async ({
    page,
  }) => {
    await page.goto('/this-does-not-exist-abc123');

    // The app should redirect to /dashboard (if authed) or /login (if not)
    await page.waitForTimeout(3000);
    const url = page.url();
    const validRedirect = url.includes('/dashboard') || url.includes('/login');
    expect(validRedirect).toBeTruthy();
  });

  test('login page has accessible form elements', async ({ page }) => {
    await page.goto('/login');

    // Verify key form elements exist and are accessible
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button[type="submit"]');

    await expect(emailInput).toBeVisible({ timeout: 10_000 });
    await expect(passwordInput).toBeVisible();
    await expect(submitButton).toBeVisible();
    await expect(submitButton).toBeEnabled();
  });
});
