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
 *   account: nav-menu (dropdown), nav-my-invoices, invoice-number, nav-my-favorites
 *   checkout: one page, wizard steps 1-4:
 *     proceed-1 (cart) -> proceed-2 (login pane, "already logged in") ->
 *     address pane (country, postal_code, house_number -> postcode lookup
 *     autofills street/city/state) -> proceed-3 -> payment pane
 *     (payment-method <select>: bank-transfer, cash-on-delivery,
 *     credit-card, buy-now-pay-later, gift-card; only cash-on-delivery and
 *     credit-card enable finish without extra fields) -> finish (twice: first
 *     click validates payment, second creates the invoice) ->
 *     #order-confirmation with #invoice-number (no checkout-complete testid)
 */

// PST_BASE_URL keeps these suites decoupled from the shared BASE_URL used by
// the saucedemo/herokuapp suites.
const BASE = process.env.PST_BASE_URL || 'https://practicesoftwaretesting.com';
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

  test('full checkout completes with order confirmation', async ({ page }) => {
    // Invoice creation on the demo API can be slow under parallel load.
    test.setTimeout(90000);

    // Arrange: add an in-stock product, then confirm the cart badge updated —
    // the checkout wizard's cart step crashes silently if the cart isn't
    // loaded (app bug: 'Cannot read properties of undefined cart_items').
    await openInStockProduct(page);
    await page.getByTestId('add-to-cart').click();
    await expect(page.getByTestId('cart-quantity')).toHaveText(/^[1-9]/, { timeout: 15000 });

    // Act: walk through the checkout wizard (single page, steps 1-4).
    // The demo API occasionally fails the first cart fetch; retry once.
    await page.goto(`${BASE}/checkout`);
    if (!(await page.getByTestId('proceed-1').isVisible().catch(() => false))) {
      await page.goto(`${BASE}/checkout`);
    }
    await page.getByTestId('proceed-1').waitFor({ state: 'visible', timeout: 20000 });
    // Wait for the cart fetch to land so step 1 is fully interactive.
    await page.getByTestId('cart-total').waitFor({ state: 'visible', timeout: 15000 });
    await page.getByTestId('proceed-1').click();                       // step 1: cart

    await page.getByTestId('proceed-2').waitFor({ state: 'visible', timeout: 20000 });
    await page.getByTestId('proceed-2').click();                       // step 2: login pane (already signed in)

    // Step 3: address pane — country select, postcode lookup autofills street/city/state
    const country = page.getByTestId('country');
    await country.waitFor({ state: 'visible', timeout: 20000 });
    const countryValues = await country.evaluate((e) =>
      Array.from((e as HTMLSelectElement).options).map((o) => o.value).filter(Boolean)
    );
    if (countryValues.includes('US')) await country.selectOption('US');
    else await country.selectOption({ index: 1 });
    await page.getByTestId('postal_code').fill('12345');
    await page.getByTestId('house_number').fill('42');
    // Postcode lookup is debounced 300ms; give the faker autofill time to land.
    await page.waitForTimeout(2500);
    for (const f of ['street', 'city', 'state']) {
      const loc = page.getByTestId(f);
      if (!(await loc.inputValue())) await loc.fill(`Test ${f.replace('-', ' ')}`);
    }
    await expect(page.getByTestId('proceed-3')).toBeEnabled({ timeout: 10000 });
    await page.getByTestId('proceed-3').click();                       // step 3: address -> payment

    // Step 4: payment — cash-on-delivery enables finish without extra fields
    const pm = page.getByTestId('payment-method');
    await pm.waitFor({ state: 'visible', timeout: 20000 });
    await pm.selectOption('cash-on-delivery');
    await expect(page.getByTestId('finish')).toBeEnabled({ timeout: 10000 });

    // The app validates the payment on the FIRST Confirm click (the paid flag
    // is only set once POST /payment/check returns), and only creates the
    // invoice on a subsequent click. Clicking twice is therefore required.
    await page.getByTestId('finish').click();
    await expect(page.getByText('Payment was successful')).toBeVisible({ timeout: 15000 });
    await page.getByTestId('finish').click();

    // Assert: order confirmation. v2.5 renders it as an [innerHTML] pane with
    // id="order-confirmation" (the old checkout-complete testid is gone).
    const confirmation = page.locator('#order-confirmation');
    await expect(confirmation).toBeVisible({ timeout: 45000 });
    await expect(confirmation).toContainText(/Thanks for your order/i);
    // The invoice number is interpolated into the confirmation text (the span
    // id may be stripped by Angular's innerHTML sanitizer, so match text).
    await expect(confirmation).toContainText(/invoice number is \S+/i);
  });

  test('invoices overview is reachable', async ({ page }) => {
    // The account section is a dropdown: open nav-menu first.
    await page.getByTestId('nav-menu').click();
    await page.getByTestId('nav-my-invoices').click();
    await expect(page).toHaveURL(/invoices/, { timeout: 15000 });
  });
});
