// Inspect the payment pane after selecting a method: dump HTML, check for
// extra required controls, and test each payment option's effect on finish.
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

const paneHtml = await page.evaluate(() => {
  const sel = document.querySelector('[data-test=payment-method]');
  let pane = sel;
  for (let i = 0; i < 6 && pane; i++) {
    pane = pane.parentElement;
    if (pane && pane.querySelector('[data-test=finish]')) break;
  }
  return pane ? pane.outerHTML : 'PANE NOT FOUND';
});
console.log('PAYMENT PANE HTML:\n', paneHtml.replace(/\s+/g, ' ').slice(0, 4000));

// Try each non-empty option; check finish enabled after each
const values = await pm.evaluate((e) => Array.from(e.options).map((o) => o.value).filter(Boolean));
for (const v of values) {
  await pm.selectOption(v);
  await page.waitForTimeout(1200);
  const finEnabled = await page.getByTestId('finish').isEnabled().catch(() => '?');
  const finHtml = await page.getByTestId('finish').evaluate((e) => e.outerHTML).catch(() => '?');
  console.log(`option "${v}": finish enabled=${finEnabled} html=${finHtml}`);
}

// List every form control in the whole document that is visible and enabled-state
const controls = await page.evaluate(() =>
  Array.from(document.querySelectorAll('input, select, textarea')).map((e) => ({
    tag: e.tagName, type: e.type || '', test: e.getAttribute('data-test'), visible: !!(e.offsetParent || e.getClientRects().length), checked: e.checked, disabled: e.disabled
  }))
);
console.log('ALL CONTROLS:', JSON.stringify(controls, null, 1));
await page.screenshot({ path: 'pay_pane.tmp.png', fullPage: true });
await b.close();
console.log('DONE');
