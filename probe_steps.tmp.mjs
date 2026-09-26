// Walk through the Toolshop checkout steps, dumping state after each click,
// to map the exact flow: which button belongs to which step, payment radio
// values, and what checkout-complete looks like.
import { chromium, selectors } from 'playwright';
selectors.setTestIdAttribute('data-test');

const BASE = 'https://practicesoftwaretesting.com';
const EMAIL = 'customer@practicesoftwaretesting.com';
const PASS = 'welcome01';

const b = await chromium.launch();
const page = await b.newPage();
page.on('console', (m) => {
  if (m.type() === 'error' && /cart_items|Unauthorized/.test(m.text())) return; // noise
  if (m.type() === 'error') console.log('  CONSOLE ERR:', m.text().slice(0, 160));
});

async function dump(step) {
  const url = page.url();
  const h = (await page.locator('h1, h3').first().textContent().catch(() => 'n/a'))?.trim();
  const ids = await page.evaluate(() =>
    Array.from(document.querySelectorAll('[data-test]')).map((e) => e.getAttribute('data-test'))
  );
  console.log(`\n===== ${step} =====`);
  console.log('URL:', url);
  console.log('HEADING:', h);
  console.log('DATA-TEST:', JSON.stringify(ids));
  // Which step markers are visible?
  for (const t of ['proceed-1','proceed-2','proceed-3','proceed-4','finish','checkout-complete']) {
    const loc = page.getByTestId(t);
    if (await loc.count()) {
      const vis = await loc.first().isVisible();
      const en = await loc.first().isEnabled().catch(() => '?');
      console.log(`  ${t}: visible=${vis} enabled=${en}`);
    }
  }
  const radios = await page.evaluate(() =>
    Array.from(document.querySelectorAll('input[type=radio]')).map((r) => r.value)
  );
  if (radios.length) console.log('  RADIOS:', JSON.stringify(radios));
}

// Login
await page.goto(`${BASE}/auth/login`);
await page.getByTestId('email').fill(EMAIL);
await page.getByTestId('password').fill(PASS);
await page.getByTestId('login-submit').click();
await page.waitForURL(/account/, { timeout: 20000 });
console.log('LOGIN OK');

// Add in-stock product
await page.goto(BASE);
await page.getByTestId('product-name').first().waitFor({ state: 'visible', timeout: 20000 });
const cards = page.locator('[data-test^=product-]');
const n = Math.min(await cards.count(), 8);
for (let i = 0; i < n; i++) {
  await cards.nth(i).click();
  await page.waitForURL(/\/product\//, { timeout: 20000 });
  const btn = page.getByTestId('add-to-cart');
  if (await btn.isEnabled().catch(() => false)) {
    await btn.click();
    console.log('ADDED:', (await page.getByTestId('product-name').textContent()).trim());
    break;
  }
  await page.goBack();
  await page.getByTestId('product-name').first().waitFor({ state: 'visible', timeout: 20000 });
}
await page.waitForTimeout(1500);

// Checkout
await page.goto(`${BASE}/checkout`);
await page.getByTestId('proceed-1').waitFor({ state: 'visible', timeout: 20000 });
await page.waitForTimeout(2000);
await dump('STEP 1 (cart)');

await page.getByTestId('proceed-1').click();
await page.waitForTimeout(2500);
await dump('AFTER proceed-1');

// If a billing form appears, fill it
if (await page.getByTestId('first-name').count()) {
  const fields = ['first-name','last-name','street','city','state','country','postcode','phone'];
  for (const f of fields) {
    const loc = page.getByTestId(f);
    if (await loc.count()) {
      const val = await loc.inputValue();
      console.log(`  field ${f}: current="${val}"`);
      if (!val) await loc.fill('Test').catch(() => {});
    }
  }
  // country may be a select
  const country = page.getByTestId('country');
  if (await country.count() && !(await country.inputValue())) {
    await country.selectOption({ index: 1 }).catch(() => {});
  }
}
await page.waitForTimeout(500);
await dump('AFTER filling billing (if present)');

// Click the step-2 proceed button
const p2 = page.getByTestId('proceed-2');
if (await p2.count() && (await p2.isEnabled())) {
  await p2.click();
  await page.waitForTimeout(2500);
  await dump('AFTER proceed-2');
}

// Payment step: pick a radio if present
const radio = page.locator('input[type=radio]');
if (await radio.count()) {
  await radio.first().check().catch(() => {});
  console.log('checked radio:', await radio.first().inputValue());
}
const p3 = page.getByTestId('proceed-3');
if (await p3.count() && (await p3.isEnabled())) {
  await p3.click();
  await page.waitForTimeout(2500);
  await dump('AFTER proceed-3');
}

const radio2 = page.locator('input[type=radio]');
if (await radio2.count() && !(await radio2.first().isChecked())) {
  await radio2.first().check().catch(() => {});
}
const p4 = page.getByTestId('proceed-4');
if (await p4.count()) {
  console.log('proceed-4 enabled:', await p4.isEnabled());
  await p4.click().catch((e) => console.log('proceed-4 click failed:', e.message.split('\n')[0]));
  await page.waitForTimeout(3000);
  await dump('AFTER proceed-4');
}

// Look for any final button
const fin = page.locator('[data-test=finish], [data-test=proceed-5]');
if (await fin.count()) {
  await fin.first().click().catch((e) => console.log('finish click failed:', e.message.split('\n')[0]));
  await page.waitForTimeout(3000);
  await dump('AFTER finish');
}

const complete = page.getByTestId('checkout-complete');
if (await complete.count()) {
  console.log('\n*** CHECKOUT-COMPLETE TEXT:', (await complete.textContent()).replace(/\s+/g, ' ').slice(0, 400));
} else {
  console.log('\n*** checkout-complete NOT found');
}
await page.screenshot({ path: 'checkout_final.tmp.png', fullPage: true });
await b.close();
console.log('WALK DONE');
