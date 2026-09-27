// Full checkout solo with invoice API call logging.
import { chromium, selectors } from 'playwright';
selectors.setTestIdAttribute('data-test');

const BASE = 'https://practicesoftwaretesting.com';
const EMAIL = 'customer@practicesoftwaretesting.com';
const PASS = 'welcome01';

const b = await chromium.launch();
const page = await b.newPage();
page.on('console', (m) => {
  if (m.type() === 'error' && /cart_items|Unauthorized/.test(m.text())) return;
  if (m.type() === 'error') console.log('  CONSOLE ERR:', m.text().slice(0, 200));
});
page.on('request', (r) => {
  if (/invoice|order|payment/i.test(r.url())) console.log('REQ', r.method(), r.url().slice(0, 120));
});
page.on('response', async (r) => {
  if (/invoice|order|payment/i.test(r.url()) && r.request().method() !== 'GET') {
    console.log('RES', r.status(), r.request().method(), r.url().slice(0, 120));
    try { const t = await r.text(); if (t) console.log('  body:', t.replace(/\s+/g, ' ').slice(0, 300)); } catch {}
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
console.log('finish enabled:', await page.getByTestId('finish').isEnabled());
await page.getByTestId('finish').click();

// Watch what happens for up to 45s: does checkout-complete appear?
for (let t = 0; t < 9; t++) {
  await page.waitForTimeout(5000);
  const completeCount = await page.getByTestId('checkout-complete').count();
  const cartBadge = await page.locator('[data-test=cart-quantity]').textContent().catch(() => '?');
  const successText = await page.getByText('Payment was successful').count();
  console.log(`t=${(t + 1) * 5}s checkout-complete=${completeCount} cart-badge=${cartBadge} success-text=${successText} url=${page.url()}`);
  if (completeCount > 0) break;
}
const complete = page.getByTestId('checkout-complete');
if (await complete.count()) {
  console.log('COMPLETE TEXT:', (await complete.textContent()).replace(/\s+/g, ' ').slice(0, 300));
}
await page.screenshot({ path: 'invoice_probe.tmp.png', fullPage: true });
await b.close();
console.log('DONE');
