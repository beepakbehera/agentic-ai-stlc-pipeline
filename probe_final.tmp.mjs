// Verify the full corrected checkout flow end-to-end.
import { chromium, selectors } from 'playwright';
selectors.setTestIdAttribute('data-test');

const BASE = 'https://practicesoftwaretesting.com';
const EMAIL = 'customer@practicesoftwaretesting.com';
const PASS = 'welcome01';

const b = await chromium.launch();
const page = await b.newPage();

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

// Step 1: cart
await page.getByTestId('proceed-1').click();
await page.getByTestId('proceed-2').waitFor({ state: 'visible', timeout: 20000 });
await page.waitForTimeout(800);

// Step 2: login pane (already logged in)
await page.getByTestId('proceed-2').click();

// Step 3: address pane — country select should now be VISIBLE
const country = page.getByTestId('country');
await country.waitFor({ state: 'visible', timeout: 20000 });
console.log('country visible now: true');
const opts = await country.evaluate((e) => Array.from(e.options).map((o) => o.value).filter(Boolean));
console.log('country has', opts.length, 'options; picking United States if present');
if (opts.includes('US')) await country.selectOption('US');
else await country.selectOption({ index: 1 });

await page.getByTestId('postal_code').fill('12345');
await page.getByTestId('house_number').fill('42');
// postcode lookup autofills street/city/state (debounced 300ms, faker driver)
await page.waitForTimeout(2500);
for (const f of ['street', 'city', 'state']) {
  let v = await page.getByTestId(f).inputValue().catch(() => '');
  if (!v) { await page.getByTestId(f).fill('Test ' + f).catch(() => {}); v = await page.getByTestId(f).inputValue(); }
  console.log(`${f} = "${v}"`);
}

const p3 = page.getByTestId('proceed-3');
console.log('proceed-3 enabled:', await p3.isEnabled());
await p3.click();

// Step 4: payment pane
const pm = page.getByTestId('payment-method');
await pm.waitFor({ state: 'visible', timeout: 20000 });
const pmOpts = await pm.evaluate((e) => Array.from(e.options).map((o) => o.text + '|' + o.value));
console.log('payment-method options:', JSON.stringify(pmOpts));
await pm.selectOption({ index: 1 });
await page.waitForTimeout(500);

const finish = page.getByTestId('finish');
console.log('finish enabled:', await finish.isEnabled());
await finish.click();

// Step 5: confirmation
const complete = page.getByTestId('checkout-complete');
await complete.waitFor({ state: 'visible', timeout: 25000 });
console.log('CHECKOUT-COMPLETE TEXT:', (await complete.textContent()).replace(/\s+/g, ' ').slice(0, 400));
console.log('FINAL URL:', page.url());
await page.screenshot({ path: 'checkout_success.tmp.png', fullPage: true });
await b.close();
console.log('FULL FLOW VERIFIED');
