// Verify the double-click quirk: click finish, wait for "Payment was
// successful", click finish again -> createInvoice should fire.
import { chromium, selectors } from 'playwright';
selectors.setTestIdAttribute('data-test');

const BASE = 'https://practicesoftwaretesting.com';
const EMAIL = 'customer@practicesoftwaretesting.com';
const PASS = 'welcome01';

const b = await chromium.launch();
const page = await b.newPage();
page.on('response', async (r) => {
  if (/invoice/i.test(r.url()) && r.request().method() !== 'GET') {
    console.log('INVOICE API:', r.status(), r.request().method(), r.url().slice(0, 120));
    try { const t = await r.text(); console.log('  body:', t.replace(/\s+/g, ' ').slice(0, 200)); } catch {}
  }
});

await page.goto(`${BASE}/auth/login`);
await page.getByTestId('email').fill(EMAIL);
await page.getByTestId('password').fill(PASS);
await page.getByTestId('login-submit').click();
await page.waitForURL(/account/, { timeout: 20000 });

await page.goto(BASE);
await page.getByTestId('product-name').first().waitFor({ state: 'visible', timeout: 20000 });
const cards = page.locator('[data-test^=product-]');
const n = Math.min(await cards.count(), 8);
for (let i = 0; i < n; i++) {
  await cards.nth(i).click();
  await page.waitForURL(/\/product\//, { timeout: 20000 });
  const btn = page.getByTestId('add-to-cart');
  if (await btn.isEnabled().catch(() => false)) { await btn.click(); break; }
  await page.goBack();
  await page.getByTestId('product-name').first().waitFor({ state: 'visible', timeout: 20000 });
}
await page.waitForTimeout(1500);

await page.goto(`${BASE}/checkout`);
await page.getByTestId('proceed-1').waitFor({ state: 'visible', timeout: 20000 });
await page.waitForTimeout(1500);
await page.getByTestId('proceed-1').click();
await page.getByTestId('proceed-2').waitFor({ state: 'visible', timeout: 20000 });
await page.waitForTimeout(800);
await page.getByTestId('proceed-2').click();
const country = page.getByTestId('country');
await country.waitFor({ state: 'visible', timeout: 20000 });
const opts = await country.evaluate((e) => Array.from(e.options).map((o) => o.value).filter(Boolean));
if (opts.includes('US')) await country.selectOption('US'); else await country.selectOption({ index: 1 });
await page.getByTestId('postal_code').fill('12345');
await page.getByTestId('house_number').fill('42');
await page.waitForTimeout(2500);
await page.getByTestId('proceed-3').click();
const pm = page.getByTestId('payment-method');
await pm.waitFor({ state: 'visible', timeout: 20000 });
await pm.selectOption('cash-on-delivery');
await page.waitForTimeout(1000);

// CLICK 1
await page.getByTestId('finish').click();
await page.getByText('Payment was successful').waitFor({ state: 'visible', timeout: 15000 });
console.log('click 1 done, payment validated');

// CLICK 2
await page.getByTestId('finish').click();
console.log('click 2 done');

const complete = page.getByTestId('checkout-complete');
await complete.waitFor({ state: 'visible', timeout: 25000 });
console.log('CHECKOUT-COMPLETE VISIBLE:', (await complete.textContent()).replace(/\s+/g, ' ').slice(0, 200));
console.log('cart badge:', await page.locator('[data-test=cart-quantity]').textContent().catch(() => '?'));
await b.close();
console.log('DOUBLE-CLICK QUIRK CONFIRMED');
