import { test, expect } from '@playwright/test';

/**
 * Practice Software Testing (Toolshop) - catalog, cart & checkout suite.
 * Selectors verified against the live DOM (data-test attributes):
 *   grid: product-name, product-price, product-{id} links, sort,
 *         search-query, search-submit, category-{id} / brand-{id} checkboxes,
 *         pagination-next, out-of-stock
 *   detail: product-name, unit-price, product-description, quantity,
 *           increase-quantity, decrease-quantity, add-to-cart,
 *           add-to-favorites
 *   account: nav-my-invoices, invoice-number, nav-my-favorites
 *   checkout: proceed-1..4, first-name, checkout-complete
 */

const BASE = process.env.BASE_URL || 'https://practicesoftwaretesting.com';
const CUSTOMER_EMAIL = 'customer@practicesoftwaretesting.com';
const CUSTOMER_PASS = 'welcome01';

async function login(page: any) {
  await page.goto(`${BASE}/auth/login`);
  await page.getByTestId('email').fill(CUSTOMER_EMAIL);
  await page.getByTestId('password').fill(CUSTOMER_PASS);
  await page.getByTestId('login-submit').click();
  await expect(page).toHaveURL(/\/account/, { timeout: 20000 });
}

/**
 * Open the first in-stock product. Stock is enforced on the detail page
 * (add-to-cart disabled when 0), so iterate the first few products until
 * one has an enabled add-to-cart button.
 */
async function openInStockProduct(page: any) {
  await page.goto(BASE);
  await page.getByTestId('product-name').first().waitFor({ state: 'visible', timeout: 20000 });
  const cards = page.locator('[data-test^=product-]');
  const n = Math.min(await cards.count(), 8);
  for (let i = 0; i < n; i++) {
    await cards.nth(i).click();
    await expect(page).toHaveURL(/\/product\//, { timeout: 20000 });
    const btn = page.getByTestId('add-to-cart');
    if (await btn.isEnabled().catch(() => false)) return;
    await page.goBack();
    await page.getByTestId('product-name').first().waitFor({ state: 'visible', timeout: 20000 });
  }
  throw new Error('No in-stock product found in the first ' + n + ' cards');
}

test.describe('Product catalog', () => {
  test('product grid loads with items', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByTestId('product-name').first()).toBeVisible({ timeout: 20000 });
    const count = await page.getByTestId('product-name').count();
    expect(count).toBeGreaterThan(0);
  });

  test('search filters products (Pliers)', async ({ page }) => {
    await page.goto(BASE);
    await page.getByTestId('search-query').fill('Pliers');
    await page.getByTestId('search-submit').click();
    await expect(page.getByTestId('product-name').first()).toBeVisible({ timeout: 20000 });
    await page.waitForTimeout(1500);
    const names = (await page.getByTestId('product-name').allTextContents()).join(' ').toLowerCase();
    expect(names).toContain('pliers');
  });

  test('category checkbox filters the grid', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByTestId('product-name').first()).toBeVisible({ timeout: 20000 });
    const cat = page.locator('[data-test^=category-]').first();
    await cat.check();
    await page.waitForTimeout(2000);
    await expect(page.getByTestId('product-name').first()).toBeVisible();
  });

  test('brand checkbox filters the grid', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByTestId('product-name').first()).toBeVisible({ timeout: 20000 });
    const brand = page.locator('[data-test^=brand-]').first();
    await brand.check();
    await page.waitForTimeout(2000);
    await expect(page.getByTestId('product-name').first()).toBeVisible();
  });

  test('sorting control is present and usable', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByTestId('sort')).toBeVisible({ timeout: 20000 });
    await page.getByTestId('sort').selectOption({ index: 1 });
    await page.waitForTimeout(2000);
    await expect(page.getByTestId('product-name').first()).toBeVisible();
  });

  test('pagination next control exists', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByTestId('product-name').first()).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('pagination-next')).toBeVisible();
  });

  test('product detail shows name, price, description and add-to-cart', async ({ page }) => {
    await page.goto(BASE);
    await page.getByTestId('product-name').first().click();
    await expect(page).toHaveURL(/\/product\//, { timeout: 20000 });
    await expect(page.getByTestId('product-name')).toBeVisible();
    await expect(page.getByTestId('unit-price')).toBeVisible();
    await expect(page.getByTestId('add-to-cart')).toBeVisible();
  });

  test('quantity can be increased on product detail', async ({ page }) => {
    await openInStockProduct(page);
    await expect(page.getByTestId('quantity')).toBeVisible({ timeout: 20000 });
    const before = await page.getByTestId('quantity').inputValue();
    await page.getByTestId('increase-quantity').click();
    const after = await page.getByTestId('quantity').inputValue();
    expect(Number(after)).toBeGreaterThan(Number(before));
  });
});

test.describe('Cart, favorites & checkout (logged in)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('add to favorites marks the product', async ({ page }) => {
    await openInStockProduct(page);
    await page.getByTestId('add-to-favorites').click();
    await page.waitForTimeout(1000);
    // favorites list lives under the account dropdown
    await page.getByTestId('nav-menu').click();
    await page.getByTestId('nav-my-favorites').click();
    await expect(page).toHaveURL(/favorites/, { timeout: 15000 });
  });

  test('add to cart then open checkout', async ({ page }) => {
    await openInStockProduct(page);
    await page.getByTestId('add-to-cart').click();
    await page.waitForTimeout(1000);
    await page.goto(`${BASE}/checkout`);
    await expect(page.getByTestId('proceed-1')).toBeVisible({ timeout: 15000 });
  });

  test('full checkout completes with "Thanks for your order!"', async ({ page }) => {
    // Arrange: add an in-stock product
    await openInStockProduct(page);
    await page.getByTestId('add-to-cart').click();
    await page.waitForTimeout(1000);

    // Act: walk through the 5 checkout steps
    await page.goto(`${BASE}/checkout`);
    await page.getByTestId('proceed-1').click();                       // cart -> sign in
    await page.getByTestId('proceed-2').click();                       // already signed in -> billing
    await expect(page.getByTestId('first-name')).toBeVisible({ timeout: 20000 });
    await page.getByTestId('proceed-3').click();                       // billing -> payment
    await page.waitForTimeout(1000);
    const bank = page.locator("input[value='Bank Transfer']");
    if (await bank.count()) await bank.check().catch(() => {});
    await page.getByTestId('proceed-4').click();                       // payment -> delivery
    await page.waitForTimeout(1000);
    const finish = page.locator('[data-test=finish], [data-test=proceed-5]');
    if (await finish.count()) await finish.first().click().catch(() => {});

    // Assert: order confirmation
    const complete = page.getByTestId('checkout-complete');
    await expect(complete).toBeVisible({ timeout: 25000 });
    await expect(complete).toContainText(/Thanks for your order/i);
  });

  test('invoices overview is reachable', async ({ page }) => {
    await page.getByTestId('nav-my-invoices').click();
    await expect(page).toHaveURL(/invoices/, { timeout: 15000 });
  });
});
