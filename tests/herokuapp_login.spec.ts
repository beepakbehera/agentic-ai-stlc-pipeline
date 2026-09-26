import { test, expect } from '@playwright/test';

/**
 * The Internet (Herokuapp) login validation - second demo site run.
 * Locators: #username, #password, button[type=submit], #flash,
 * .flash.success, .flash.error, a[href='/logout'].
 *
 * Valid user: tomsmith / SuperSecretPassword!
 */

const BASE = process.env.BASE_URL || 'https://the-internet.herokuapp.com';
const USER = 'tomsmith';
const PASS = 'SuperSecretPassword!';

async function login(page: any, username: string, password: string) {
  await page.goto(`${BASE}/login`);
  await page.fill('#username', username);
  await page.fill('#password', password);
  await page.click('button[type=submit]');
}

test.describe('Herokuapp login validation', () => {
  test('valid login lands on secure area with success flash', async ({ page }) => {
    await login(page, USER, PASS);
    await expect(page).toHaveURL(/\/secure/);
    await expect(page.locator('#flash.success')).toContainText('You logged into a secure area!');
    await expect(page.locator("a[href='/logout']")).toBeVisible();
  });

  test('logout returns to login page', async ({ page }) => {
    await login(page, USER, PASS);
    await expect(page).toHaveURL(/\/secure/);
    await page.click("a[href='/logout']");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('#username')).toBeVisible();
  });

  test('invalid username shows error flash', async ({ page }) => {
    await login(page, 'wrong_user', PASS);
    await expect(page.locator('#flash.error')).toContainText('Your username is invalid!');
  });

  test('invalid password shows error flash', async ({ page }) => {
    await login(page, USER, 'wrong_password');
    await expect(page.locator('#flash.error')).toContainText('Your password is invalid!');
  });

  test('error flash can be dismissed with close button', async ({ page }) => {
    await login(page, 'wrong_user', PASS);
    const flash = page.locator('#flash.error');
    await expect(flash).toBeVisible();
    await flash.locator('a.close, .close').first().click();
    await expect(page.locator('#flash.error')).not.toBeVisible();
  });

  test('login page loads within 10 seconds', async ({ page }, testInfo) => {
    const start = Date.now();
    await page.goto(`${BASE}/login`);
    await expect(page.locator('#username')).toBeVisible();
    const ms = Date.now() - start;
    testInfo.annotations.push({ type: 'load_ms', description: String(ms) });
    // 10s: herokuapp.com is a free-tier shared service with variable latency
    expect(ms).toBeLessThan(10000);
  });
});
