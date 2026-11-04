// Render the 20 full-article pages in pages.html to 1080 x 1440 PNGs (3:4).
//
// Usage: node render-pages.js <output-dir> [font-css]
//   font-css: optional local @font-face stylesheet for Noto Sans SC / Noto Serif SC.
// Prints any page whose content overflows its fixed height.
const { chromium } = require('playwright');
const path = require('path');

const out = process.argv[2];
const fontCss = process.argv[3];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1200 }, deviceScaleFactor: 2.4 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('file://' + path.join(__dirname, 'pages.html'));
  if (fontCss) await page.addStyleTag({ path: fontCss });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);

  const overflow = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.page')).map((pg, i) => {
      const body = pg.querySelector('.body') || pg;
      const over = Math.max(body.scrollHeight - body.clientHeight, pg.scrollHeight - pg.clientHeight);
      return over > 0 ? `page ${i + 1} overflows by ${over}px` : null;
    }).filter(Boolean));
  if (overflow.length) console.log(overflow.join('\n'));

  // Show one page at a time at the top-left corner so every crop lands on exact pixels.
  // Playwright rounds clips to whole CSS px, so zoom the 400 x 533.33 page to exactly 450 x 600 and shoot at 2.4x.
  await page.addStyleTag({ content: 'body{padding:0!important;display:block!important}.page{display:none!important;zoom:1.125}.page.solo{display:flex!important}' });
  const n = await page.locator('.page').count();
  for (let i = 0; i < n; i++) {
    await page.evaluate((k) => document.querySelectorAll('.page').forEach((pg, j) => pg.classList.toggle('solo', j === k)), i);
    await page.screenshot({ path: path.join(out, String(i + 1).padStart(2, '0') + '.png'), clip: { x: 0, y: 0, width: 450, height: 600 } }); // 450 x 600 at 2.4x = 1080 x 1440
  }
  if (errors.length) console.error('page errors:', errors);
  await browser.close();
  console.log('rendered', n, 'pages');
})();
