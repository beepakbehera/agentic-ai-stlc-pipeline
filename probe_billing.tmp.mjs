// Dump the billing pane structure after opening the address step,
// with visibility info for each control, to find why country is hidden.
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
await page.getByTestId('proceed-1').click();
await page.getByTestId('proceed-2').waitFor({ state: 'visible', timeout: 20000 });
await page.waitForTimeout(1500);

// Visibility of each interesting control
for (const f of ['country','postal_code','house_number','street','city','state','proceed-2','postcode-lookup-hint','first-name','last-name']) {
  const loc = page.getByTestId(f);
  const cnt = await loc.count();
  if (!cnt) { console.log(`${f}: NOT IN DOM`); continue; }
  for (let k = 0; k < cnt; k++) {
    const vis = await loc.nth(k).isVisible().catch(() => '?');
    const box = await loc.nth(k).boundingBox().catch(() => null);
    console.log(`${f}[${k}]: visible=${vis} box=${box ? 'yes' : 'null'}`);
  }
}

// Dump the pane that contains proceed-2 (the active step pane)
const paneHtml = await page.evaluate(() => {
  const p2 = document.querySelector('[data-test=proceed-2]');
  let pane = p2;
  for (let i = 0; i < 6 && pane; i++) {
    pane = pane.parentElement;
    if (pane && pane.querySelector('[data-test=country]')) break;
  }
  return pane ? pane.outerHTML : 'PANE NOT FOUND';
});
console.log('\nBILLING PANE HTML (trimmed):\n', paneHtml.replace(/\s+/g, ' ').slice(0, 3000));
await page.screenshot({ path: 'billing_pane.tmp.png', fullPage: true });
await b.close();
console.log('DONE');
