// Log ALL requests + JS errors after clicking finish, to find the invoice call.
import { chromium, selectors } from 'playwright';
selectors.setTestIdAttribute('data-test');

const BASE = 'https://practicesoftwaretesting.com';
const EMAIL = 'customer@practicesoftwaretesting.com';
const PASS = 'welcome01';

const b = await chromium.launch();
const page = await b.newPage();
page.on('console', (m) => {
  if (m.type() === 'error') console.log('CONSOLE ERR:', m.text().slice(0, 400));
  if (m.type() === 'warning') console.log('CONSOLE WARN:', m.text().slice(0, 200));
});
page.on('pageerror', (e) => console.log('PAGE ERROR:', e.message.slice(0, 400)));

let startedLogging = false;
page.on('request', (r) => {
  if (!startedLogging) return;
  console.log('REQ', r.method(), r.url().slice(0, 140));
});
page.on('response', (r) => {
  if (!startedLogging) return;
  if (r.url().includes('api.')) console.log('RES', r.status(), r.request().method(), r.url().slice(0, 140));
});
page.on('requestfailed', (r) => {
  if (startedLogging) console.log('FAILED', r.method(), r.url().slice(0, 140), r.failure()?.errorText);
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

console.log('--- CLICKING FINISH, logging all traffic ---');
startedLogging = true;
await page.getByTestId('finish').click();
await page.waitForTimeout(20000);

console.log('checkout-complete count:', await page.getByTestId('checkout-complete').count());
console.log('cart badge:', await page.locator('[data-test=cart-quantity]').textContent().catch(() => '?'));
const pane = await page.evaluate(() => document.querySelector('.wizard-content, .card, app-checkout')?.textContent?.replace(/\s+/g, ' ').slice(0, 400) || 'n/a');
console.log('PANE TEXT:', pane);
await page.screenshot({ path: 'allnet.tmp.png', fullPage: true });
await b.close();
console.log('DONE');
