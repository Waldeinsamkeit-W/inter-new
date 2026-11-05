/*
 * 把 article.md 转成可直接粘贴到公众号编辑器的 HTML（全部内联样式）。用法：
 *   node build.cjs                      # 输出 ../wechat.html（图片以 base64 内嵌，单文件即可使用）
 *   node build.cjs --fragment out.html  # 输出不含 <html>/<head> 的片段（用于在线预览页）
 *
 * 公众号编辑器会丢弃 <style> 和 class，只保留元素上的 style 属性，所以正文里的每个元素都写内联样式。
 * 列表用“悬挂缩进的段落”实现，避免不同客户端对 <ul>/<ol> 的渲染差异。
 */
const fs = require('fs');
const path = require('path');
const { marked } = require('marked');

const ROOT = path.join(__dirname, '..');
const md = fs.readFileSync(path.join(ROOT, 'article.md'), 'utf8');

const T = {
  ink: '#2b3340', strong: '#1b2330', brand: '#184f95', muted: '#8a909a', line: '#e4e7ec',
  tint: '#f2f6fb', warm: '#fdf3ec', warmInk: '#9a3d12',
};
const P = `margin:0 0 18px;font-size:16px;line-height:1.85;color:${T.ink};letter-spacing:0.5px;text-align:justify;`;
const P_CALLOUT = `margin:0;font-size:15px;line-height:1.8;color:${T.ink};letter-spacing:0.5px;text-align:left;`;
const P_LEAD = `margin:0;font-size:15px;line-height:1.8;color:#5a6372;letter-spacing:0.5px;text-align:justify;`;

function dataUri(file) {
  const buf = fs.readFileSync(path.join(ROOT, file));
  return 'data:image/png;base64,' + buf.toString('base64');
}

let quoteCount = 0;
const renderer = {
  heading(text, level) {
    if (level === 1) return ''; // 标题在公众号后台单独填写
    if (level === 2) {
      return `<section style="margin:44px 0 22px;padding-bottom:10px;border-bottom:1px solid ${T.line};"><span style="font-size:20px;line-height:1.5;font-weight:bold;color:${T.brand};letter-spacing:0.5px;">${text}</span></section>`;
    }
    return `<section style="margin:30px 0 14px;"><span style="font-size:17px;line-height:1.6;font-weight:bold;color:${T.strong};letter-spacing:0.5px;">${text}</span></section>`;
  },
  paragraph(text) {
    if (text.startsWith('<section data-img')) return text;
    return `<p style="${P}">${text}</p>`;
  },
  strong(text) {
    return `<strong style="font-weight:bold;color:${T.brand};">${text}</strong>`;
  },
  em(text) {
    return `<span style="font-size:13px;line-height:1.7;color:${T.muted};">${text}</span>`;
  },
  codespan(text) {
    return `<span style="background:${T.tint};padding:0 4px;border-radius:3px;">${text}</span>`;
  },
  code(code, lang) {
    const lines = code.split('\n').map((l) => l.replace(/&/g, '&amp;').replace(/</g, '&lt;')).join('<br>');
    return `<section style="margin:4px 0 20px;padding:14px 16px;background:${T.tint};border-radius:6px;text-align:center;"><span style="font-size:15px;line-height:1.9;font-weight:bold;color:${T.strong};letter-spacing:0.3px;">${lines}</span></section>`;
  },
  blockquote(quote) {
    quoteCount += 1;
    if (quoteCount === 1) {
      const inner = quote.split(`style="${P}"`).join(`style="${P_LEAD}"`);
      return `<section style="margin:0 0 28px;padding:16px 18px;background:#f6f7f9;border-radius:6px;">${inner}</section>`;
    }
    const inner = quote.split(`style="${P}"`).join(`style="${P_CALLOUT}"`);
    return `<section style="margin:8px 0 24px;padding:16px 18px;background:${T.warm};border-radius:6px;">${inner}</section>`;
  },
  list(body, ordered, start) {
    const items = body.split('\u0000').filter((s) => s.trim());
    return `<section style="margin:0 0 18px;">${items.map((t, i) => {
      const box = t.startsWith('☐');
      const marker = box ? '' : ordered ? `${(start || 1) + i}. ` : '• ';
      const indent = box ? '0' : ordered ? '1.4em' : '1.1em';
      return `<p style="margin:0 0 10px;font-size:16px;line-height:1.85;color:${T.ink};letter-spacing:0.5px;text-align:justify;padding-left:${indent};text-indent:-${indent};">${marker}${t}</p>`;
    }).join('')}</section>`;
  },
  listitem(text) {
    return '\u0000' + text.replace(/<p style="[^"]*">|<\/p>/g, '');
  },
  table(header, body) {
    return `<section style="margin:4px 0 22px;overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:14px;line-height:1.6;color:${T.ink};"><thead>${header}</thead><tbody>${body}</tbody></table></section>`;
  },
  tablerow(content) {
    // 第一列是简短的类别名时不换行，手机上更好读；长文本照常换行
    const first = (content.match(/^<(?:td|th)[^>]*>(.*?)<\/(?:td|th)>/) || [, ''])[1].replace(/<[^>]+>/g, '');
    if (first.length > 6) return `<tr>${content}</tr>`;
    return `<tr>${content.replace(/^<(td|th) style="/, '<$1 style="white-space:nowrap;')}</tr>`;
  },
  tablecell(content, flags) {
    if (flags.header) {
      return `<th style="background:${T.brand};color:#ffffff;font-weight:bold;padding:8px 10px;border:1px solid ${T.brand};text-align:left;">${content}</th>`;
    }
    return `<td style="padding:8px 10px;border:1px solid ${T.line};vertical-align:top;">${content}</td>`;
  },
  image(href, title, text) {
    return `<section data-img="1" style="margin:24px 0 26px;text-align:center;"><img src="${dataUri(href)}" alt="${text}" style="width:100%;max-width:100%;height:auto;display:block;margin:0 auto;"></section>`;
  },
  hr() {
    return `<section style="margin:32px auto;width:40px;border-top:2px solid ${T.line};"></section>`;
  },
};

marked.use({ renderer, gfm: true, mangle: false, headerIds: false });

const title = (md.match(/^#\s+(.+)$/m) || [, '估值模型全攻略'])[1];
// 中文标点后的加粗收尾需要一个空格才能被 Markdown 识别，渲染时去掉这个空格
const body = marked.parse(md).replace(/([。：；！？，])<\/strong> /g, '$1</strong>');
const DIGEST = 'PE、PB、EV/EBITDA、DCF 到底怎么选、怎么用？用一个贯穿全文的案例，讲透主流估值模型的原理、适用场景、实操步骤和常见陷阱，附 Excel 建模技巧与公式速查卡。';

const chromeCss = `
:root{--bg:#e9edf2;--panel:#ffffff;--ink:#1b2330;--ink2:#566070;--line:#d5dbe3;--accent:#184f95;--accent-ink:#ffffff;--ok:#0f7a45;--edge:rgba(16,24,40,.08);--paper:#ffffff;--paper-ink:#2b3340}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0f141b;--panel:#18202b;--ink:#e8edf3;--ink2:#a7b1bf;--line:#2a3442;--accent:#86b6ef;--accent-ink:#0b1320;--ok:#4cc38a;--edge:rgba(255,255,255,.10);color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f141b;--panel:#18202b;--ink:#e8edf3;--ink2:#a7b1bf;--line:#2a3442;--accent:#86b6ef;--accent-ink:#0b1320;--ok:#4cc38a;--edge:rgba(255,255,255,.10);color-scheme:dark}
body{background:var(--bg);color:var(--ink);margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Noto Sans SC","Microsoft YaHei",sans-serif}
.wrap{max-width:720px;margin:0 auto;padding-block:20px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:16px}
.bar{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;display:flex;flex-direction:column;gap:14px}
.bar h1{font-size:18px;line-height:1.4;margin:0;text-wrap:balance}
.bar p{margin:0;font-size:14px;color:var(--ink2);line-height:1.65}
.actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.btn{font:inherit;font-size:15px;font-weight:600;background:var(--accent);color:var(--accent-ink);border:0;border-radius:8px;padding:10px 16px;cursor:pointer}
.btn.ghost{background:transparent;color:var(--accent);box-shadow:inset 0 0 0 1px var(--line)}
.btn:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
.status{font-size:14px;color:var(--ok);min-height:1.2em}
details{border-top:1px solid var(--line);padding-top:12px}
summary{cursor:pointer;font-size:14px;font-weight:600}
details ol{margin:10px 0 0;padding-left:20px;font-size:14px;color:var(--ink2);line-height:1.75}
.digest{margin-top:10px;font-size:14px;line-height:1.7;color:var(--ink);background:var(--bg);border-radius:8px;padding:10px 12px}
.covers{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px}
.covers figure{margin:0;flex:1 1 220px;min-width:0}
.covers img{width:100%;display:block;border-radius:6px}
.covers figcaption{font-size:13px;color:var(--ink2);margin-top:6px}
.paper{background:var(--paper);color:var(--paper-ink);border-radius:12px;box-shadow:0 0 0 1px var(--edge);padding:28px 20px 36px;min-width:0}
.wx-title{font-size:22px;line-height:1.45;font-weight:700;color:#1b2330;margin:0 0 8px;text-wrap:balance}
.wx-meta{font-size:13px;color:#8a909a;margin:0 0 26px}
@media (max-width:480px){.paper{padding:22px 14px 30px}}
@media (prefers-reduced-motion: reduce){*{transition:none!important}}`;

function shell(coverSrc, squareSrc) {
  return `
<div class="wrap">
  <section class="bar" aria-label="发布工具">
    <h1>公众号排版预览</h1>
    <p>下面白色区域就是排好版的正文。点“复制正文”，再到公众号后台的编辑器里粘贴即可，字号、颜色和表格都会保留。标题、摘要和封面在后台单独填写。</p>
    <div class="actions">
      <button class="btn" id="copy-body" type="button">复制正文</button>
      <button class="btn ghost" id="copy-digest" type="button">复制摘要</button>
      <span class="status" id="status" role="status" aria-live="polite"></span>
    </div>
    <details>
      <summary>发布步骤</summary>
      <ol>
        <li>在公众号后台新建图文，标题填写：${title}</li>
        <li>点击上方“复制正文”，在正文编辑区粘贴。</li>
        <li>检查配图。如果某张图粘贴后不显示或保存时报错，删掉它，在原位置上传仓库 images 文件夹里同编号的图片（fig01～fig13）。</li>
        <li>上传封面：头图用 cover.png（2.35:1），分享卡片用 cover-square.png（1:1）。</li>
        <li>粘贴摘要，预览到手机上通读一遍再群发。</li>
      </ol>
    </details>
    <details>
      <summary>摘要和封面</summary>
      <div class="digest" id="digest">${DIGEST}</div>
      <div class="covers">
        <figure><img src="${coverSrc}" alt="封面头图"><figcaption>头图 cover.png，2.35:1</figcaption></figure>
        <figure style="flex:0 1 160px"><img src="${squareSrc}" alt="方形封面"><figcaption>方形 cover-square.png，1:1</figcaption></figure>
      </div>
    </details>
  </section>
  <article class="paper">
    <h2 class="wx-title">${title}</h2>
    <p class="wx-meta">正文预览 · 手机上约 677px 宽</p>
    <section id="wx-article" style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;color:${T.ink};">${body}</section>
  </article>
</div>
<script>
(function(){
  var statusEl=document.getElementById('status');
  function say(msg){statusEl.textContent=msg;}
  function selectNode(node){var r=document.createRange();r.selectNodeContents(node);var s=window.getSelection();s.removeAllRanges();s.addRange(r);return s;}
  function legacyCopy(node){var s=selectNode(node);var ok=false;try{ok=document.execCommand('copy');}catch(e){}if(ok){s.removeAllRanges();}return ok;}
  document.getElementById('copy-body').addEventListener('click',function(){
    var node=document.getElementById('wx-article');
    if(legacyCopy(node)){say('已复制正文，去公众号编辑器粘贴吧');return;}
    if(navigator.clipboard&&window.ClipboardItem){
      var item=new ClipboardItem({'text/html':new Blob([node.innerHTML],{type:'text/html'}),'text/plain':new Blob([node.innerText],{type:'text/plain'})});
      navigator.clipboard.write([item]).then(function(){say('已复制正文，去公众号编辑器粘贴吧');},function(){selectNode(node);say('已选中正文，请按 Ctrl+C（Mac 用 ⌘+C）复制');});
      return;
    }
    selectNode(node);say('已选中正文，请按 Ctrl+C（Mac 用 ⌘+C）复制');
  });
  document.getElementById('copy-digest').addEventListener('click',function(){
    var el=document.getElementById('digest');var text=el.textContent;
    function fallback(){el.closest('details').open=true;selectNode(el);say('已选中摘要，请按 Ctrl+C（Mac 用 ⌘+C）复制');}
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(function(){say('已复制摘要');},fallback);}else{fallback();}
  });
})();
</script>`;
}

const args = process.argv.slice(2);
const cover = dataUri('images/cover.png');
const square = dataUri('images/cover-square.png');
const head = `<title>估值模型全攻略</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n<style>${chromeCss}</style>`;

if (args[0] === '--fragment') {
  const out = args[1];
  fs.writeFileSync(out, head + shell(cover, square));
  console.log('fragment →', out, (fs.statSync(out).size / 1e6).toFixed(2) + ' MB');
} else {
  const out = path.join(ROOT, 'wechat.html');
  fs.writeFileSync(out, `<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n${head}\n</head>\n<body>${shell(cover, square)}\n</body>\n</html>\n`);
  console.log('wechat.html →', out, (fs.statSync(out).size / 1e6).toFixed(2) + ' MB');
}
