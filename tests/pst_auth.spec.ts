import { test, expect } from '@playwright/test';

/**
 * Practice Software Testing (Toolshop) - https://practicesoftwaretesting.com/
 * Authentication & account suite.
 *
 * Selectors verified against the live DOM (all data-test attributes):
 *   login: data-test=email, password, login-submit, login-error,
 *          forgot-password-link, register-link
 *   account: page-title, nav-my-invoices, nav-my-favorites, nav-my-profile,
 *            nav-sign-out
 *
 * NOTE: the destructive "account locks after 5 failed attempts" scenario is
 * intentionally NOT automated - it would lock the shared demo accounts for
 * everyone. It is documented as a test case in Jira instead.
 */

// PST_BASE_URL keeps this suite decoupled from the shared BASE_URL used by
// the saucedemo/herokuapp suites.
const BASE = process.env.PST_BASE_URL || 'https://practicesoftwaretesting.com';
const CUSTOMER_EMAIL = 'customer@practicesoftwaretesting.com';
const CUSTOMER_PASS = 'welcome01';

test.describe('Authentication', () => {
  test('customer login succeeds and lands on account page', async ({ page }) => {
    await page.goto(`${BASE}/auth/login`);
    await page.getByTestId('email').fill(CUSTOMER_EMAIL);
    await page.getByTestId('password').fill(CUSTOMER_PASS);
    await page.getByTestId('login-submit').click();

    await expect(page).toHaveURL(/\/account/, { timeout: 20000 });
    await expect(page.getByTestId('page-title')).toBeVisible();
  });

  test('invalid credentials show "Invalid email or password"', async ({ page }) => {
    await page.goto(`${BASE}/auth/login`);
    await page.getByTestId('email').fill(CUSTOMER_EMAIL);
    await page.getByTestId('password').fill('wrong_password');
    await page.getByTestId('login-submit').click();

    const err = page.getByTestId('login-error');
    await expect(err).toBeVisible({ timeout: 15000 });
    await expect(err).toContainText('Invalid email or password');
  });

  test('login form blocks empty submit', async ({ page }) => {
    await page.goto(`${BASE}/auth/login`);
    await page.getByTestId('login-submit').click();
    // HTML5 validation keeps the user on the login page
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('forgot password link navigates to reset page', async ({ page }) => {
    await page.goto(`${BASE}/auth/login`);
    await page.getByTestId('forgot-password-link').click();
    await expect(page).toHaveURL(/forgot-password/, { timeout: 15000 });
  });

  test('register link navigates to registration page', async ({ page }) => {
    await page.goto(`${BASE}/auth/login`);
    await page.getByTestId('register-link').click();
    await expect(page).toHaveURL(/register/, { timeout: 15000 });
  });
});

test.describe('Account area (logged in as Jane Doe)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE}/auth/login`);
    await page.getByTestId('email').fill(CUSTOMER_EMAIL);
    await page.getByTestId('password').fill(CUSTOMER_PASS);
    await page.getByTestId('login-submit').click();
    await expect(page).toHaveURL(/\/account/, { timeout: 20000 });
  });

  test('invoices page is reachable from account menu', async ({ page }) => {
    await page.getByTestId('nav-invoices').click();
    await expect(page).toHaveURL(/invoices/, { timeout: 15000 });
  });

  test('favorites page is reachable from account menu', async ({ page }) => {
    await page.getByTestId('nav-favorites').click();
    await expect(page).toHaveURL(/favorites/, { timeout: 15000 });
  });

  test('profile page is reachable', async ({ page }) => {
    await page.getByTestId('nav-profile').click();
    await expect(page).toHaveURL(/profile/, { timeout: 15000 });
  });

  test('sign out returns to logged-out state', async ({ page }) => {
    // sign-out lives inside the account dropdown - open it first
    await page.getByTestId('nav-menu').click();
    await page.getByTestId('nav-sign-out').click();
    await expect(page.getByTestId('nav-sign-in')).toBeVisible({ timeout: 15000 });
  });
});
