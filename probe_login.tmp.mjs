// Dump the login page state to see why the form isn't rendering.
import { chromium } from 'playwright';

const BASE = 'https://practicesoftwaretesting.com';

const b = await chromium.launch();
const page = await b.newPage();
page.on('response', (r) => {
  if (/\/api\//.test(r.url())) console.log('HTTP', r.status(), r.request().method(), r.url().slice(0, 140));
});

await page.goto(`${BASE}/auth/login`, { waitUntil: 'networkidle', timeout: 60000 }).catch((e) => console.log('GOTO ERR:', e.message));
await page.waitForTimeout(3000);
console.log('URL:', page.url());
console.log('TITLE:', await page.title());
const body = (await page.locator('body').textContent().catch(() => '')).replace(/\s+/g, ' ');
console.log('BODY TEXT:', body.slice(0, 1000));
console.log('--- data-test attrs on page:');
const ids = await page.evaluate(() => Array.from(document.querySelectorAll('[data-test]')).map((e) => e.getAttribute('data-test')));
console.log(JSON.stringify(ids));
console.log('--- inputs:', await page.evaluate(() => Array.from(document.querySelectorAll('input')).map((i) => i.type + ':' + i.name + ':' + i.id)));
await page.screenshot({ path: 'login_probe.tmp.png', fullPage: true });
await b.close();
