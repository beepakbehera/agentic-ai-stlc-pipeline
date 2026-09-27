// Admin probe: login, locate user management, unlock customer@ account.
import { chromium, selectors } from 'playwright';
selectors.setTestIdAttribute('data-test');

const BASE = 'https://practicesoftwaretesting.com';
const ADMIN = 'admin@practicesoftwaretesting.com';
const PASS = 'welcome01';

const b = await chromium.launch();
const page = await b.newPage();

await page.goto(`${BASE}/auth/login`);
await page.getByTestId('email').fill(ADMIN);
await page.getByTestId('password').fill(PASS);
await page.getByTestId('login-submit').click();
await page.waitForURL(/dashboard|account/, { timeout: 20000 });
console.log('ADMIN LOGIN OK, url:', page.url());

const ids = await page.evaluate(() => Array.from(document.querySelectorAll('[data-test]')).map((e) => e.getAttribute('data-test')));
console.log('DATA-TEST on dashboard:', JSON.stringify(ids));

// Try to reach an admin users section
for (const path of ['/admin/users', '/admin/products', '/admin/accounts']) {
  await page.goto(`${BASE}${path}`);
  await page.waitForTimeout(2000);
  const h = (await page.locator('h1, h3, h2').first().textContent().catch(() => '')).trim();
  console.log(`${path} -> h="${h}" url=${page.url()}`);
  if (/user|admin/i.test(h)) {
    const ids2 = await page.evaluate(() => Array.from(document.querySelectorAll('[data-test]')).map((e) => e.getAttribute('data-test')));
    console.log('  DATA-TEST:', JSON.stringify(ids2.slice(0, 60)));
    break;
  }
}
await page.screenshot({ path: 'admin_probe.tmp.png', fullPage: true });
await b.close();
console.log('DONE');
