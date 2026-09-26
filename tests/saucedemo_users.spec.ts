import { test, expect } from '@playwright/test';

/**
 * Agentic STLC validation suite - saucedemo.com
 * Covers all accepted user personas + negative login scenario.
 * Locators match the real DOM: #user-name, #password, #login-button,
 * .login_credentials, [data-test=error], .inventory_list, etc.
 */

const USERS = [
  { name: 'standard_user', expect: 'inventory', delay: false },
  { name: 'locked_out_user', expect: 'locked', delay: false },
  { name: 'problem_user', expect: 'inventory', delay: false },
  { name: 'performance_glitch_user', expect: 'inventory', delay: true },
  { name: 'error_user', expect: 'inventory', delay: false },
  { name: 'visual_user', expect: 'inventory', delay: false },
];

const PASSWORD = 'secret_sauce';
const BASE_URL = process.env.BASE_URL || 'https://www.saucedemo.com/';

async function login(page: any, username: string, password: string) {
  await page.goto(BASE_URL);
  await page.fill('#user-name', username);
  await page.fill('#password', password);
  await page.click('#login-button');
}

test.describe('Saucedemo login - all user personas', () => {
  for (const u of USERS) {
    test(`login as ${u.name}`, async ({ page }, testInfo) => {
      const start = Date.now();
      await login(page, u.name, PASSWORD);

      if (u.expect === 'locked') {
        // locked_out_user must be blocked with the epic sadface error
        const err = page.locator('[data-test=error]');
        await expect(err).toBeVisible();
        await expect(err).toContainText('locked out');
        await expect(page).not.toHaveURL(/inventory/);
      } else {
        await expect(page).toHaveURL(/inventory/, { timeout: u.delay ? 20000 : 10000 });
        await expect(page.locator('.inventory_list')).toBeVisible();
        const elapsed = Date.now() - start;
        if (u.delay) {
          // performance_glitch_user: login takes noticeably longer
          testInfo.annotations.push({ type: 'login_ms', description: String(elapsed) });
          expect(elapsed).toBeGreaterThan(1000);
        }
        // standard_user gets the full journey; others stop at inventory check
        if (u.name === 'standard_user') {
          await page.locator('.inventory_item button').first().click();
          await expect(page.locator('.shopping_cart_badge')).toHaveText('1');
          await page.click('.shopping_cart_link');
          await page.click('[data-test=checkout]');
          await page.fill('#first-name', 'Deepak');
          await page.fill('#last-name', 'Behera');
          await page.fill('#postal-code', '560001');
          await page.click('#continue');
          await page.click('#finish');
          await expect(page.locator('.complete-header')).toContainText('Thank you');
        }
        if (u.name === 'problem_user') {
          // Known app defect: first product image is broken
          const img = page.locator('.inventory_item_img img').first();
          const natural = await img.evaluate((el: HTMLImageElement) => el.naturalWidth);
          testInfo.annotations.push({ type: 'first_image_natural_width', description: String(natural) });
        }
      }
    });
  }

  test('invalid credentials show epic sadface error', async ({ page }) => {
    await login(page, 'standard_user', 'wrong_password');
    const err = page.locator('[data-test=error]');
    await expect(err).toBeVisible();
    await expect(err).toContainText('Username and password do not match');
  });

  test('error banner can be dismissed with close button', async ({ page }) => {
    await login(page, 'standard_user', 'wrong_password');
    await page.click('[data-test=error] button');
    await expect(page.locator('[data-test=error]')).not.toBeVisible();
  });
});
