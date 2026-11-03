// 长图分段截图：每段一个视口高度，滚动截图，交给 build_long_image.py 拼接。
// 用法：node shoot_long.cjs <html> <输出目录> <CSS 宽度> <缩放倍数>
// 一次截超长整页在 Chromium 里会超出纹理上限，所以分段。
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [html, outdir, width, scale] = process.argv.slice(2);
  const W = Number(width), S = Number(scale), SEG = 2400;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: SEG }, deviceScaleFactor: S });
  await page.goto('file://' + html);
  await page.evaluate(() => document.fonts.ready);
  const height = await page.evaluate(() => Math.ceil(document.documentElement.scrollHeight));
  // 可以切分的位置：每节开头、每张图开头（CSS 像素）
  const breaks = await page.evaluate(() =>
    [...document.querySelectorAll('[data-break]')].map((el) => ({
      y: Math.round(el.getBoundingClientRect().top + window.scrollY),
      kind: el.getAttribute('data-break'),
    })));
  const segs = [];
  for (let y = 0; y < height; y += SEG) {
    await page.evaluate((v) => window.scrollTo(0, v), y);
    await page.waitForTimeout(60);
    const sy = await page.evaluate(() => window.scrollY);
    const file = path.join(outdir, `seg_${String(segs.length).padStart(2, '0')}.png`);
    await page.screenshot({ path: file });
    segs.push({ file, y: sy });
  }
  fs.writeFileSync(path.join(outdir, 'meta.json'), JSON.stringify({ height, width: W, scale: S, segs, breaks }));
  await browser.close();
  console.log('segments', segs.length, 'height', height);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
