// Complete checkout end-to-end: fill required billing fields (country!),
// select payment method from the payment-method <select>, click finish,
// and capture checkout-complete.
import { chromium, selectors } from 'playwright';
selectors.setTestIdAttribute('data-test');

const BASE = 'https://practicesoftwaretesting.com';
const EMAIL = 'customer@practicesoftwaretesting.com';
const PASS = 'welcome01';

const b = await chromium.launch();
const page = await b.newPage();
page.on('console', (m) => {
  if (m.type() === 'error' && /cart_items|Unauthorized/.test(m.text())) return;
  if (m.type() === 'error') console.log('  CONSOLE ERR:', m.text().slice(0, 160));
});

await page.goto(`${BASE}/auth/login`);
await page.getByTestId('email').fill(EMAIL);
await page.getByTestId('password').fill(PASS);
await page.getByTestId('login-submit').click();
await page.waitForURL(/account/, { timeout: 20000 });
console.log('LOGIN OK');

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
await page.waitForTimeout(1000);

// Fill required billing fields: country select + postal code
const country = page.getByTestId('country');
console.log('country value before:', await country.inputValue());
if (!(await country.inputValue())) {
  const opts = await country.evaluate((e) => Array.from(e.options).map((o) => o.text + '|' + o.value));
  console.log('country options (first 8):', JSON.stringify(opts.slice(0, 8)));
  await country.selectOption({ index: 1 });
}
for (const f of ['postal_code', 'house_number', 'state']) {
  const loc = page.getByTestId(f);
  if (await loc.count() && !(await loc.inputValue())) await loc.fill('12345');
}
console.log('country value after:', await country.inputValue());

await page.getByTestId('proceed-2').click();
await page.getByTestId('payment-method').waitFor({ state: 'visible', timeout: 20000 });
await page.waitForTimeout(1000);

// Payment step: it's a SELECT
const pm = page.getByTestId('payment-method');
const pmOpts = await pm.evaluate((e) => Array.from(e.options).map((o) => o.text + '|' + o.value));
console.log('payment-method options:', JSON.stringify(pmOpts));
const payValue = pmOpts.length > 1 ? (await pm.locator('option').nth(1).getAttribute('value')) : '';
console.log('selecting payment value:', payValue);
await pm.selectOption(payValue);
await page.waitForTimeout(1000);

const finish = page.getByTestId('finish');
console.log('finish enabled:', await finish.isEnabled());
await finish.click();
await page.waitForTimeout(4000);

const complete = page.getByTestId('checkout-complete');
console.log('checkout-complete count:', await complete.count());
if (await complete.count()) {
  console.log('CHECKOUT-COMPLETE TEXT:', (await complete.textContent()).replace(/\s+/g, ' ').slice(0, 500));
} else {
  const ids = await page.evaluate(() => Array.from(document.querySelectorAll('[data-test]')).map((e) => e.getAttribute('data-test')));
  console.log('DATA-TEST on final page:', JSON.stringify(ids));
}
console.log('FINAL URL:', page.url());
await page.screenshot({ path: 'checkout_done.tmp.png', fullPage: true });
await b.close();
console.log('DONE');
