// Dump the payment-method container to learn how methods are selected,
// then finish checkout and capture checkout-complete.
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

// Log billing fields state before proceeding
for (const f of ['country','postal_code','house_number','street','city','state','first-name','last-name']) {
  const loc = page.getByTestId(f);
  if (await loc.count()) {
    const tag = await loc.evaluate((e) => e.tagName).catch(() => '?');
    const val = await loc.inputValue().catch(() => '');
    console.log(`BILLING ${f} <${tag}> = "${val}"`);
  }
}
await page.getByTestId('proceed-2').click();
await page.getByTestId('payment-method').waitFor({ state: 'visible', timeout: 20000 });
await page.waitForTimeout(1500);

// Dump payment-method container HTML
const pm = page.getByTestId('payment-method');
console.log('\nPAYMENT-METHOD HTML:\n', await pm.evaluate((e) => e.outerHTML));

// Also dump any element containing "payment" or method-like data-test attrs
const payIds = await page.evaluate(() =>
  Array.from(document.querySelectorAll('[data-test]'))
    .map((e) => e.getAttribute('data-test'))
    .filter((t) => /pay|bank|credit|cash|monthly/i.test(t))
);
console.log('PAYMENT-RELATED DATA-TEST IDS:', JSON.stringify(payIds));

await page.screenshot({ path: 'payment_step.tmp.png', fullPage: true });
await b.close();
console.log('PAYMENT DUMP DONE');
