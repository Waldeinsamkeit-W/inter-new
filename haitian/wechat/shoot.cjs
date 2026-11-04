// 把 build_images.py 生成的 HTML 卡片截成 PNG。
// 用法：node shoot.cjs jobs.json
// jobs.json：[{ "html": 绝对路径, "out": 绝对路径, "width": CSS 宽度, "height": 可选（不填则按 #card 实际高度截） }]
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await chromium.launch();
  for (const job of jobs) {
    const page = await browser.newPage({
      viewport: { width: job.width, height: job.height || 1000 },
      deviceScaleFactor: job.scale || 2, // 卡片 420 CSS 像素 × 2.571 = 1080 像素宽，公众号推荐宽度
    });
    await page.goto('file://' + job.html);
    await page.evaluate(() => document.fonts.ready);
    const card = await page.$('#card');
    await card.screenshot({ path: job.out });
    await page.close();
    console.log('ok', job.out.split('/').pop());
  }
  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
