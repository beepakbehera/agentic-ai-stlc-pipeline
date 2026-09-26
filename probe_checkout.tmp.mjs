// Probe the Toolshop checkout flow to see why proceed-1 is disabled.
// Logs cart badge state after add-to-cart, then inspects /checkout step 1.
import { chromium, selectors } from 'playwright';
selectors.setTestIdAttribute('data-test'); // site uses data-test, not data-testid

const BASE = 'https://practicesoftwaretesting.com';
const EMAIL = 'customer@practicesoftwaretesting.com';
const PASS = 'welcome01';

const b = await chromium.launch();
const page = await b.newPage();
page.on('console', (m) => console.log('CONSOLE:', m.type().slice(0, 5), m.text().slice(0, 200)));
page.on('response', async (r) => {
  const u = r.url();
  if (/\/api\/|cart|invoice|order/i.test(u) && r.request().method() !== 'GET') {
    console.log('HTTP', r.status(), r.request().method(), u.slice(0, 120));
    try { const t = await r.text(); if (t) console.log('  body:', t.replace(/\s+/g, ' ').slice(0, 300)); } catch {}
  }
});

// Login
await page.goto(`${BASE}/auth/login`);
await page.getByTestId('email').fill(EMAIL);
await page.getByTestId('password').fill(PASS);
await page.getByTestId('login-submit').click();
await page.waitForURL(/account/, { timeout: 20000 });
console.log('LOGIN OK');

// Open first product and add to cart
await page.goto(BASE);
await page.getByTestId('product-name').first().waitFor({ state: 'visible', timeout: 20000 });
const cards = page.locator('[data-test^=product-]');
const n = Math.min(await cards.count(), 8);
let added = false;
for (let i = 0; i < n; i++) {
  await cards.nth(i).click();
  await page.waitForURL(/\/product\//, { timeout: 20000 });
  const btn = page.getByTestId('add-to-cart');
  if (await btn.isEnabled().catch(() => false)) {
    console.log('PRODUCT:', await page.getByTestId('product-name').textContent());
    await btn.click();
    added = true;
    break;
  }
  await page.goBack();
  await page.getByTestId('product-name').first().waitFor({ state: 'visible', timeout: 20000 });
}
if (!added) { console.log('NO IN-STOCK PRODUCT FOUND'); process.exit(1); }
await page.waitForTimeout(1500);

// Cart badge state on this page
for (const sel of ['[data-test=cart-badge]', '.fa-cart-shopping', '.badge', 'header .badge']) {
  const loc = page.locator(sel);
  const cnt = await loc.count();
  if (cnt) console.log(`BADGE ${sel} count=${cnt} text="${(await loc.first().textContent()).trim()}"`);
}
const cartUrlProbe = page.url();
console.log('URL after add:', cartUrlProbe);

// Go straight to /checkout
await page.goto(`${BASE}/checkout`);
await page.waitForTimeout(2500);
console.log('CHECKOUT URL:', page.url());
console.log('CHECKOUT H1:', (await page.locator('h1, h3').first().textContent().catch(() => 'n/a'))?.trim());

const p1 = page.getByTestId('proceed-1');
console.log('proceed-1 count:', await p1.count());
if (await p1.count()) {
  console.log('proceed-1 enabled:', await p1.isEnabled());
  console.log('proceed-1 visible:', await p1.isVisible());
  const cls = await p1.getAttribute('class');
  console.log('proceed-1 class:', cls);
}
// Dump the step-1 (cart table) area to see if cart items are rendered
const table = page.locator('[data-test=cart-table], table').first();
console.log('cart table count:', await table.count());
if (await table.count()) {
  console.log('CART TABLE:\n', (await table.textContent()).replace(/\s+/g, ' ').slice(0, 600));
} else {
  const body = (await page.locator('main, .container').first().textContent().catch(() => '')).replace(/\s+/g, ' ');
  console.log('PAGE TEXT:', body.slice(0, 800));
}
await page.screenshot({ path: '/tmp/checkout_step1.png', fullPage: true });
await b.close();
console.log('PROBE DONE');
