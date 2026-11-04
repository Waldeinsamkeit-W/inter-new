// Render the six explainer posters in posters.html to 1080px-wide PNGs.
//
// Usage: node render-posters.js <output-dir> [font-css]
//   font-css: optional local @font-face stylesheet for Noto Sans SC / Noto Serif SC.
//             Without it the page falls back to whatever Chinese fonts are installed.
const { chromium } = require('playwright');
const path = require('path');

const out = process.argv[2];
const fontCss = process.argv[3];
const names = ['01-logic', '02-trace', '03-derivation', '04-indirect', '05-bridge-shop', '06-bridge-full'];

(async () => {
  const browser = await chromium.launch();
  // 400 CSS px * 2.7 = 1080 px wide images.
  const page = await browser.newPage({ viewport: { width: 480, height: 1200 }, deviceScaleFactor: 2.7 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('file://' + path.join(__dirname, 'posters.html'));
  if (fontCss) await page.addStyleTag({ path: fontCss });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  for (let i = 0; i < names.length; i++) {
    const el = page.locator('#p' + (i + 1));
    await el.screenshot({ path: path.join(out, names[i] + '.png') });
  }
  if (errors.length) console.error('page errors:', errors);
  await browser.close();
})();
