/*
 * 生成文章配图（PNG）。用法：
 *   npm install          # 安装字体与依赖（Playwright 需另行安装）
 *   python3 model.py     # 先算出案例数据 model.json
 *   node figures.cjs     # 输出到 ../images/
 *   node figures.cjs fig08   # 只重画名字里含 fig08 的图
 *
 * 配图按 560px 宽设计、3 倍像素导出（1680px 宽），手机上缩放后文字仍然清晰。
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const OUT = path.join(__dirname, '..', 'images');
const CACHE = path.join(__dirname, '.cache');
const FONT_DIR = path.join(__dirname, 'node_modules', '@fontsource', 'noto-sans-sc');
const M = JSON.parse(fs.readFileSync(path.join(__dirname, 'model.json'), 'utf8'));

const W = 560;
const C = {
  ink: '#1b2330', ink2: '#4f5866', muted: '#7d8591', grid: '#e4e7ec', axis: '#c3c8d0',
  panel: '#f4f6f9', brand: '#184f95',
  blue: '#2a78d6', blue50: '#eaf2fc', orange: '#eb6834', orange50: '#fdefe8',
  aqua: '#1baf7a', aqua50: '#e6f6ef', yellow: '#eda100', yellow50: '#fdf4dc',
  red: '#e34948', slate: '#52606f',
};
const RAMP = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95'];

const f2 = (x) => x.toFixed(2);
const f1 = (x) => x.toFixed(1);
const pct = (x, d = 1) => (x * 100).toFixed(d) + '%';

function page(body, { width = W, extraCss = '' } = {}) {
  const fonts = [400, 500, 700, 900]
    .map((w) => `<link rel="stylesheet" href="${path.join(FONT_DIR, w + '.css')}">`).join('\n');
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">${fonts}
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;font-family:'Noto Sans SC',sans-serif;color:${C.ink};-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.fig{width:${width}px;padding:30px 26px 22px;background:#fff}
.hd{margin-bottom:20px}
.no{font-size:15px;font-weight:700;color:${C.brand};letter-spacing:.1em}
.hd h1{font-size:27px;font-weight:900;line-height:1.3;margin-top:4px;text-wrap:balance}
.hd p{font-size:17px;color:${C.ink2};margin-top:6px;line-height:1.55}
.ft{margin-top:18px;padding-top:12px;border-top:1px solid ${C.grid};font-size:14px;color:${C.muted};line-height:1.65}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:15px;color:${C.ink2};margin-bottom:12px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
svg text{font-family:'Noto Sans SC',sans-serif}
${extraCss}
</style></head><body>${body}</body></html>`;
}

function frame(no, title, sub, inner, foot) {
  return `<div class="fig"><div class="hd"><div class="no">${no}</div><h1>${title}</h1>${sub ? `<p>${sub}</p>` : ''}</div>${inner}${foot ? `<div class="ft">${foot}</div>` : ''}</div>`;
}

/* ---------- 图1 估值方法全景 ---------- */
function fig01() {
  const cards = [
    ['相对估值', C.blue, C.blue50, '跟同类比，贵还是便宜？', ['PE', 'PB', 'PS', 'EV/EBITDA', '先例交易'], '有足够多可比公司的行业', '对应评估准则中的市场法'],
    ['绝对估值', C.orange, C.orange50, '未来的现金流，今天值多少？', ['DCF', 'DDM', '剩余收益模型'], '现金流可以预测的公司', '对应评估准则中的收益法'],
    ['资产基础法', C.aqua, C.aqua50, '把家当拆开卖，值多少？', ['NAV', '重置成本', '清算价值'], '资产驱动型公司、困境企业', '对应评估准则中的资产基础法'],
    ['特殊方法', C.yellow, C.yellow50, '常规方法用不上，怎么办？', ['SOTP', 'VC 法', 'rNPV', '实物期权'], '多元集团、初创公司、创新药', '常与前三类组合使用'],
  ];
  const html = cards.map(([name, col, tint, q, ms, fit, cn]) => `
    <div class="card">
      <div class="top"><i style="background:${col}"></i><b>${name}</b><span class="cn">${cn}</span></div>
      <div class="q">${q}</div>
      <div class="chips">${ms.map((m) => `<span style="background:${tint}">${m}</span>`).join('')}</div>
      <div class="fit"><em>适用</em>${fit}</div>
    </div>`).join('');
  const css = `
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.card{border:1px solid ${C.grid};border-radius:10px;padding:16px 16px 14px;display:flex;flex-direction:column;gap:10px}
.top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.top i{width:14px;height:14px;border-radius:4px}
.top b{font-size:21px;font-weight:900}
.cn{font-size:13px;color:${C.muted};width:100%;margin-left:22px;margin-top:-4px}
.q{font-size:17px;color:${C.ink};font-weight:500;line-height:1.5}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chips span{font-size:16px;font-weight:700;padding:3px 10px;border-radius:6px;color:${C.ink}}
.fit{font-size:15px;color:${C.ink2};line-height:1.5}
.fit em{font-style:normal;font-weight:700;color:${C.ink};margin-right:6px}`;
  return page(frame('图 1', '估值方法全景图', '四大类方法，分别回答四个不同的问题', `<div class="grid">${html}</div>`,
    '国内资产评估准则把企业价值评估的基本方法归为市场法、收益法和资产基础法三类。'), { extraCss: css });
}

/* ---------- 图2 EV 与股权价值 ---------- */
function fig02() {
  const bar = (title, parts, total) => `
    <div class="col">
      <div class="ct">${title}</div>
      <div class="stack">${parts.map(([label, val, h, col, txt]) => `
        <div class="seg" style="height:${h}px;background:${col};color:${txt || '#fff'}"><b>${label}</b><span>${val}</span></div>`).join('')}
      </div>
      <div class="total">${total}</div>
    </div>`;
  const css = `
.row{display:flex;gap:22px;align-items:flex-start}
.col{flex:1;min-width:0}
.ct{font-size:19px;font-weight:900;margin-bottom:10px}
.stack{display:flex;flex-direction:column;gap:2px}
.seg{border-radius:4px;padding:10px 14px;display:flex;flex-direction:column;justify-content:center}
.seg b{font-size:18px;font-weight:700}
.seg span{font-size:15px;opacity:.95;margin-top:2px}
.total{margin-top:10px;font-size:16px;color:${C.ink2};line-height:1.5}
.total b{color:${C.ink}}
.match{margin-top:22px;display:grid;grid-template-columns:1fr 1fr;gap:12px}
.m{border-radius:10px;padding:14px 16px;background:${C.panel}}
.m h3{font-size:17px;font-weight:900;margin-bottom:6px;display:flex;align-items:center;gap:8px}
.m h3 i{width:12px;height:12px;border-radius:3px;display:inline-block}
.m p{font-size:16px;line-height:1.6;color:${C.ink}}
.m .x{font-size:14px;color:${C.muted};margin-top:6px}`;
  const inner = `
    <div class="legend"><span><i style="background:${C.blue}"></i>属于股东</span><span><i style="background:${C.orange}"></i>属于债权人</span><span><i style="background:${C.aqua}"></i>属于其他出资方</span></div>
    <div class="row">
      ${bar('买一套房', [['首付', '200 万元', 120, C.blue], ['银行贷款', '300 万元', 180, C.orange]], '房屋总价 <b>500 万元</b><br>你的权益只有 <b>200 万元</b>')}
      ${bar('买一家公司', [['股权价值', '股东的部分', 160, C.blue], ['净负债', '有息负债 − 现金', 76, C.orange], ['少数股东权益', '子公司的其他股东', 64, C.aqua]], '<b>企业价值 EV</b> = 三块之和<br>股东只拥有其中的 <b>股权价值</b>')}
    </div>
    <div class="match">
      <div class="m"><h3><i style="background:${C.slate}"></i>EV 口径</h3><p>对应 EBITDA、EBIT、营收</p><div class="x">分给债权人和股东之前的指标</div></div>
      <div class="m"><h3><i style="background:${C.blue}"></i>股权口径（市值）</h3><p>对应净利润、净资产、股利</p><div class="x">只属于股东的指标</div></div>
    </div>`;
  return page(frame('图 2', '企业价值（EV）与股权价值', '用买房来类比：总价是企业价值，首付才是股东的部分', inner,
    'EV = 股权市值 + 有息负债 − 现金 + 少数股东权益 + 优先股。分子分母口径必须一致，例如 EV/EBITDA、市值/净利润。'), { extraCss: css });
}

/* ---------- 图3 可比公司表 ---------- */
function fig03() {
  const comps = [
    ['A 公司', 480, 20, 14.5, 0.12, 0.11],
    ['B 公司', 405, 15, 16.0, 0.15, 0.13],
    ['C 公司', 230, 11.5, 12.0, 0.08, 0.09],
    ['D 公司', 650, 26, 15.0, 0.11, 0.12],
    ['E 公司', 180, 3.6, 30.0, 0.35, 0.05],
  ];
  const pe = comps.map((c) => c[1] / c[2]);
  const ev = comps.map((c) => c[3]);
  const med = (a) => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
  const avg = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  const rows = comps.map((c, i) => `
    <tr class="${i === 4 ? 'out' : ''}"><td class="l">${c[0]}${i === 4 ? '<span class="tag">异常值</span>' : ''}</td><td>${c[1]}</td><td>${c[2]}</td><td><b>${f1(pe[i])}x</b></td><td><b>${f1(ev[i])}x</b></td><td>${pct(c[4], 0)}</td><td>${pct(c[5], 0)}</td></tr>`).join('');
  const css = `
table{width:100%;border-collapse:collapse;font-size:16px}
th{font-size:13.5px;font-weight:700;color:${C.ink2};text-align:right;padding:0 6px 10px;line-height:1.35;border-bottom:2px solid ${C.ink};vertical-align:bottom}
th.l,td.l{text-align:left;padding-left:2px}
td{text-align:right;padding:10px 6px;border-bottom:1px solid ${C.grid};white-space:nowrap}
td b{font-weight:700}
tr.out td{color:${C.muted}}
.tag{font-size:12px;font-weight:700;color:${C.orange};border:1px solid ${C.orange};border-radius:4px;padding:0 4px;margin-left:6px;vertical-align:1px}
tr.sum td{background:${C.panel};font-weight:500}
tr.med td{background:${C.blue50};font-weight:700;color:${C.brand}}
tr.tgt td{border-bottom:none;padding-top:14px}
tr.tgt td.l{font-weight:900}
tr.tgt td.pick{color:${C.orange};font-weight:900}
.cap{font-size:15px;color:${C.ink2};margin:16px 0 0;line-height:1.6}`;
  const inner = `
    <table>
      <thead><tr><th class="l">公司</th><th>市值<br>（亿元）</th><th>2027E<br>净利润</th><th>PE<br>2027E</th><th>EV/EBITDA<br>2027E</th><th>营收<br>增速</th><th>净<br>利率</th></tr></thead>
      <tbody>${rows}
        <tr class="sum"><td class="l">平均值</td><td></td><td></td><td>${f1(avg(pe))}x</td><td>${f1(avg(ev))}x</td><td>—</td><td>—</td></tr>
        <tr class="med"><td class="l">中位数</td><td></td><td></td><td>${f1(med(pe))}x</td><td>${f1(med(ev))}x</td><td>${pct(med(comps.map((c) => c[4])), 0)}</td><td>${pct(med(comps.map((c) => c[5])), 0)}</td></tr>
        <tr class="tgt"><td class="l">小鲜饮品</td><td>?</td><td>5.0</td><td class="pick">22–26x</td><td class="pick">12–15x</td><td>14%</td><td>10%</td></tr>
      </tbody>
    </table>
    <p class="cap">E 公司把 PE 平均值拉高到 ${f1(avg(pe))} 倍，中位数则稳定在 ${f1(med(pe))} 倍。小鲜饮品增速略高于同行，但净利率偏低、规模偏小，在中位数基础上小幅折价。</p>`;
  return page(frame('图 3', '可比公司估值表', '先算倍数、取中位数，再按目标公司特点做溢价或折价', inner,
    '公司与数据均为虚构，仅作教学演示。'), { extraCss: css });
}

/* ---------- 图4 周期股 PE 陷阱 ---------- */
function fig04() {
  const eps = [0.6, 1.2, 2.2, 3.0, 1.6, 0.3, 0.6, 1.4, 2.6, 2.0];
  const price = [12, 20, 28, 24, 15, 12, 18, 30, 34, 26];
  const pe = eps.map((e, i) => price[i] / e);
  const w = W - 52, padL = 40, padR = 12, plotW = w - padL - padR;
  const n = eps.length, step = plotW / n;
  const cx = (i) => padL + step * (i + 0.5);
  // EPS panel
  const h1 = 150, top1 = 26, base1 = top1 + h1, max1 = 3.5;
  const y1 = (v) => base1 - (v / max1) * h1;
  let s1 = '';
  [0, 1, 2, 3].forEach((t) => { s1 += `<line x1="${padL}" x2="${w - padR}" y1="${y1(t)}" y2="${y1(t)}" stroke="${t === 0 ? C.axis : C.grid}" stroke-width="1"/><text x="${padL - 8}" y="${y1(t) + 5}" font-size="13" fill="${C.muted}" text-anchor="end">${t.toFixed(1)}</text>`; });
  eps.forEach((e, i) => {
    const bw = step * 0.5, x = cx(i) - bw / 2, y = y1(e), hh = base1 - y;
    const hl = i === 3 || i === 5;
    s1 += `<path d="M${x},${base1} V${y + 4} q0,-4 4,-4 H${x + bw - 4} q4,0 4,4 V${base1} Z" fill="${hl ? C.blue : '#9ec5f4'}"/>`;
  });
  s1 += `<text x="${padL}" y="14" font-size="15" font-weight="700" fill="${C.ink}">每股收益 EPS（元）</text>`;
  // Price panel
  const top2 = 30, h2 = 160, base2 = top2 + h2, max2 = 40;
  const y2 = (v) => base2 - (v / max2) * h2;
  let s2 = '';
  [0, 10, 20, 30, 40].forEach((t) => { s2 += `<line x1="${padL}" x2="${w - padR}" y1="${y2(t)}" y2="${y2(t)}" stroke="${t === 0 ? C.axis : C.grid}" stroke-width="1"/><text x="${padL - 8}" y="${y2(t) + 5}" font-size="13" fill="${C.muted}" text-anchor="end">${t}</text>`; });
  s2 += `<polyline points="${price.map((p, i) => `${cx(i)},${y2(p)}`).join(' ')}" fill="none" stroke="${C.orange}" stroke-width="2.5" stroke-linejoin="round"/>`;
  price.forEach((p, i) => { const hl = i === 3 || i === 5; s2 += `<circle cx="${cx(i)}" cy="${y2(p)}" r="${hl ? 6 : 4}" fill="${C.orange}" stroke="#fff" stroke-width="2"/>`; });
  s2 += `<text x="${padL}" y="14" font-size="15" font-weight="700" fill="${C.ink}">股价（元）</text>`;
  // annotations
  s2 += `<text x="${cx(3) + 10}" y="${y2(24) - 14}" font-size="14" font-weight="700" fill="${C.ink}">利润见顶，PE 仅 8 倍</text>`;
  s2 += `<text x="${cx(3) + 10}" y="${y2(24) + 4}" font-size="13" fill="${C.ink2}">之后两年股价 −50%</text>`;
  s2 += `<text x="${cx(5) + 2}" y="${y2(12) + 24}" font-size="14" font-weight="700" fill="${C.ink}">利润见底，PE 40 倍</text>`;
  s2 += `<text x="${cx(5) + 2}" y="${y2(12) + 42}" font-size="13" fill="${C.ink2}">之后两年股价 +150%</text>`;
  const svgH2 = base2 + 8;
  // PE strip
  const strip = pe.map((v, i) => {
    const hl = i === 3 || i === 5;
    return `<div class="c${hl ? ' hl' : ''}"><span>${v.toFixed(0)}</span></div>`;
  }).join('');
  const years = eps.map((_, i) => `<div class="c y">${i + 1}</div>`).join('');
  const css = `
.strip,.yrs{display:grid;grid-template-columns:repeat(10,1fr);margin-left:${padL}px;margin-right:${padR}px}
.strip .c{text-align:center;font-size:15px;padding:7px 0;color:${C.ink2};border-top:1px solid ${C.grid};border-bottom:1px solid ${C.grid}}
.strip .c.hl{background:${C.orange50};color:${C.ink};font-weight:900}
.yrs .c{text-align:center;font-size:13px;color:${C.muted};padding-top:6px}
.sl{font-size:15px;font-weight:700;margin:4px 0 8px}`;
  const inner = `
    <svg width="${w}" height="${base1 + 10}" viewBox="0 0 ${w} ${base1 + 10}">${s1}</svg>
    <svg width="${w}" height="${svgH2}" viewBox="0 0 ${w} ${svgH2}">${s2}</svg>
    <div class="sl">市盈率 PE（倍）</div>
    <div class="strip">${strip}</div>
    <div class="yrs">${years}</div>`;
  return page(frame('图 4', '周期股的 PE 陷阱', '利润最高时 PE 最低、看似便宜；利润最低时 PE 最高、看似昂贵', inner,
    '示意数据，横轴为周期内第 1～10 年。周期股更适合用 PB 或完整周期的平均利润来估值。'), { extraCss: css });
}

/* ---------- 图5 DCF 测算表 ---------- */
function fig05() {
  const R = M.rows, b = M.base;
  const df = R.map((_, t) => 1 / Math.pow(1.085, t + 1));
  const line = (label, vals, cls = '') => `<tr class="${cls}"><td class="l">${label}</td>${vals.map((v) => `<td>${v}</td>`).join('')}</tr>`;
  const css = `
table{width:100%;border-collapse:collapse;font-size:16px}
th{font-size:15px;font-weight:700;color:${C.ink2};text-align:right;padding:0 6px 10px;border-bottom:2px solid ${C.ink}}
th.l,td.l{text-align:left;padding-left:2px}
td{text-align:right;padding:8px 6px;border-bottom:1px solid ${C.grid};white-space:nowrap}
tr.sub td{color:${C.muted};font-size:14px;padding-top:0;border-bottom:1px solid ${C.grid}}
tr.sub td.l{padding-left:14px}
tr.pre td{border-bottom:none}
tr.key td{background:${C.blue50};font-weight:900;color:${C.brand}}
tr.pv td{background:${C.orange50};font-weight:900}
.sumbox{margin-top:16px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.sumbox div{background:${C.panel};border-radius:8px;padding:10px 12px}
.sumbox span{display:block;font-size:13.5px;color:${C.ink2}}
.sumbox b{font-size:21px;font-weight:900}`;
  const inner = `
    <table>
      <thead><tr><th class="l">单位：亿元</th>${R.map((r) => `<th>${r.y}E</th>`).join('')}</tr></thead>
      <tbody>
        ${line('营业收入', R.map((r) => f2(r.rev)), 'pre')}
        ${line('增速', R.map((r) => pct(r.growth)), 'sub')}
        ${line('EBIT', R.map((r) => f2(r.ebit)), 'pre')}
        ${line('利润率', R.map((r) => pct(r.ebit / r.rev)), 'sub')}
        ${line('税后经营利润', R.map((r) => f2(r.nopat)))}
        ${line('+ 折旧摊销', R.map((r) => f2(r.da)))}
        ${line('− 资本开支', R.map((r) => f2(r.capex)))}
        ${line('− 营运资本增加', R.map((r) => f2(r.dnwc)))}
        ${line('= FCFF', R.map((r) => f2(r.fcff)), 'key')}
        ${line('折现系数', df.map((d) => d.toFixed(4)))}
        ${line('FCFF 现值', b.pvs.map(f2), 'pv')}
      </tbody>
    </table>
    <div class="sumbox">
      <div><span>预测期现值合计</span><b>${f2(b.pv_sum)}</b></div>
      <div><span>终值的现值</span><b>${f2(b.pv_tv)}</b></div>
      <div><span>企业价值 EV</span><b>${f2(b.ev)}</b></div>
    </div>`;
  return page(frame('图 5', '小鲜饮品 DCF 测算表', 'WACC 8.5%，永续增长率 2.5%，税率 25%', inner,
    `折现系数 = 1 ÷ (1 + 8.5%)ᵗ，t 为年数。终值 = ${f2(R[4].fcff)} × (1 + 2.5%) ÷ (8.5% − 2.5%) ≈ ${f2(b.tv)} 亿元。四舍五入可能导致合计存在尾差。`), { extraCss: css });
}

/* ---------- 图6 终值占比 ---------- */
function fig06() {
  const b = M.base;
  const vals = [...b.pvs, b.pv_tv];
  const labels = ['2027E', '2028E', '2029E', '2030E', '2031E', '终值'];
  const w = W - 52, padL = 40, padR = 8, top = 34, h = 230, base = top + h, max = 80;
  const y = (v) => base - (v / max) * h;
  const plotW = w - padL - padR, step = plotW / vals.length;
  let s = '';
  [0, 20, 40, 60, 80].forEach((t) => { s += `<line x1="${padL}" x2="${w - padR}" y1="${y(t)}" y2="${y(t)}" stroke="${t === 0 ? C.axis : C.grid}"/><text x="${padL - 8}" y="${y(t) + 5}" font-size="13" fill="${C.muted}" text-anchor="end">${t}</text>`; });
  vals.forEach((v, i) => {
    const bw = Math.min(24, step * 0.5), x = padL + step * (i + 0.5) - bw / 2, yy = y(v);
    const col = i === 5 ? C.orange : C.blue;
    s += `<path d="M${x},${base} V${yy + 4} q0,-4 4,-4 H${x + bw - 4} q4,0 4,4 V${base} Z" fill="${col}"/>`;
    s += `<text x="${x + bw / 2}" y="${base + 20}" font-size="14" fill="${C.ink2}" text-anchor="middle">${labels[i]}</text>`;
  });
  const x0 = padL + step * 0.5 - 12, x1 = padL + step * 4.5 + 12, yb = y(Math.max(...b.pvs)) - 14;
  s += `<path d="M${x0},${yb + 6} V${yb} H${x1} V${yb + 6}" fill="none" stroke="${C.ink2}" stroke-width="1.2"/>`;
  s += `<text x="${(x0 + x1) / 2}" y="${yb - 8}" font-size="15" font-weight="700" fill="${C.ink}" text-anchor="middle">预测期合计 ${f1(b.pv_sum)} 亿元</text>`;
  const xt = padL + step * 5.5;
  s += `<text x="${xt}" y="${y(b.pv_tv) - 10}" font-size="15" font-weight="700" fill="${C.ink}" text-anchor="middle">${f1(b.pv_tv)}</text>`;
  s += `<text x="${padL}" y="14" font-size="14" fill="${C.muted}">现值（亿元）</text>`;
  const share = b.pv_tv / b.ev;
  const css = `
.seg{display:flex;gap:2px;margin-top:8px}
.seg div{height:28px;border-radius:4px;color:#fff;font-size:14px;font-weight:700;display:flex;align-items:center;padding-left:8px;white-space:nowrap;overflow:hidden}
.segt{font-size:15px;font-weight:700;margin-top:22px}`;
  const inner = `
    <div class="legend"><span><i style="background:${C.blue}"></i>预测期各年 FCFF 现值</span><span><i style="background:${C.orange}"></i>终值的现值</span></div>
    <svg width="${w}" height="${base + 30}" viewBox="0 0 ${w} ${base + 30}">${s}</svg>
    <div class="segt">企业价值 ${f1(b.ev)} 亿元的构成</div>
    <div class="seg"><div style="flex:${1 - share};background:${C.blue}">${pct(1 - share, 0)}</div><div style="flex:${share};background:${C.orange}">终值 ${pct(share, 0)}</div></div>`;
  return page(frame('图 6', '终值往往占 DCF 价值的大头', `小鲜饮品的企业价值中，终值贡献了约 ${pct(share, 0)}`, inner,
    '终值占比通常在 60%～80%。占比越高，结论对永续增长率和 WACC 越敏感。'), { extraCss: css });
}

/* ---------- 图7 EV → 股权价值 ---------- */
function fig07() {
  const b = M.base;
  const steps = [
    ['企业价值', b.ev, 'total'], ['现金', 15, 'up'], ['有息负债', -10, 'down'],
    ['少数股东|权益', -2, 'down'], ['长期股权|投资', 3, 'up'], ['股权价值', b.equity, 'total'],
  ];
  const w = W - 52, padL = 40, padR = 8, top = 30, h = 280, base = top + h, max = 125;
  const y = (v) => base - (v / max) * h;
  const plotW = w - padL - padR, step = plotW / steps.length;
  let s = '', run = 0;
  [0, 25, 50, 75, 100, 125].forEach((t) => { s += `<line x1="${padL}" x2="${w - padR}" y1="${y(t)}" y2="${y(t)}" stroke="${t === 0 ? C.axis : C.grid}"/><text x="${padL - 8}" y="${y(t) + 5}" font-size="13" fill="${C.muted}" text-anchor="end">${t}</text>`; });
  steps.forEach(([label, v, kind], i) => {
    let lo, hi;
    if (kind === 'total') { lo = 0; hi = v; run = v; } else { lo = Math.min(run, run + v); hi = Math.max(run, run + v); run += v; }
    const bw = step * 0.56, x = padL + step * (i + 0.5) - bw / 2;
    const col = kind === 'total' ? C.slate : kind === 'up' ? C.blue : C.red;
    const yt = y(hi), yb = y(lo), r = Math.min(4, (yb - yt) / 2);
    s += kind === 'total'
      ? `<path d="M${x},${yb} V${yt + r} q0,-${r} ${r},-${r} H${x + bw - r} q${r},0 ${r},${r} V${yb} Z" fill="${col}"/>`
      : `<rect x="${x}" y="${yt}" width="${bw}" height="${Math.max(yb - yt, 2)}" rx="${r}" fill="${col}"/>`;
    const txt = kind === 'total' ? f1(v) : (v > 0 ? '+' : '−') + Math.abs(v);
    s += `<text x="${x + bw / 2}" y="${yt - 8}" font-size="15" font-weight="700" fill="${C.ink}" text-anchor="middle">${txt}</text>`;
    label.split('|').forEach((t, k) => { s += `<text x="${x + bw / 2}" y="${base + 22 + k * 18}" font-size="13.5" fill="${C.ink2}" text-anchor="middle">${t}</text>`; });
    if (i < steps.length - 1) {
      const nx = padL + step * (i + 1.5) - bw / 2;
      s += `<line x1="${x + bw}" x2="${nx}" y1="${y(run)}" y2="${y(run)}" stroke="${C.axis}" stroke-width="1"/>`;
    }
  });
  s += `<text x="${padL}" y="14" font-size="14" fill="${C.muted}">亿元</text>`;
  const css = `.res{margin-top:12px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;background:${C.panel};border-radius:8px;padding:12px 14px}.res span{font-size:16px;color:${C.ink2}}.res b{font-size:24px;font-weight:900}`;
  const inner = `
    <div class="legend"><span><i style="background:${C.slate}"></i>合计</span><span><i style="background:${C.blue}"></i>加项</span><span><i style="background:${C.red}"></i>减项</span></div>
    <svg width="${w}" height="${base + 50}" viewBox="0 0 ${w} ${base + 50}">${s}</svg>
    <div class="res"><span>股权价值 ${f1(b.equity)} 亿元 ÷ 总股本 10 亿股 =</span><b>每股 ${f2(b.equity / 10)} 元</b></div>`;
  return page(frame('图 7', '从企业价值到股权价值', 'DCF 算出的是企业价值，还要“过桥”才能得到股东的价值', inner,
    '常被漏掉的项目：租赁负债、离职后福利、已宣告未发放的股利、可转债，以及闲置资产等非经营性资产。'), { extraCss: css });
}

/* ---------- 图8 敏感性分析 ---------- */
function fig08() {
  const { sens, waccs, gs } = M;
  const flat = sens.flat(), lo = Math.min(...flat), hi = Math.max(...flat);
  const color = (v) => RAMP[Math.round(((v - lo) / (hi - lo)) * (RAMP.length - 1))];
  const ink = (v) => (Math.round(((v - lo) / (hi - lo)) * (RAMP.length - 1)) >= 6 ? '#fff' : C.ink);
  const cell = (v, i, j) => {
    const base = i === 2 && j === 2, band = i >= 1 && i <= 3 && j >= 1 && j <= 3;
    return `<td class="${base ? 'base' : ''}${band ? ' band' : ''} r${i} c${j}" style="background:${color(v)};color:${ink(v)}">${f2(v)}</td>`;
  };
  const css = `
.wrap{display:flex;flex-direction:column;align-items:stretch}
.xl{font-size:15px;font-weight:700;color:${C.ink2};text-align:center;margin-left:92px;margin-bottom:8px}
table{border-collapse:separate;border-spacing:3px;width:100%;font-size:17px}
th{font-size:15px;font-weight:700;color:${C.ink2};padding:6px 4px}
th.rowh{text-align:right;padding-right:10px;width:88px}
td{text-align:center;padding:14px 0;border-radius:4px;font-weight:500;position:relative}
td.base{font-weight:900;box-shadow:inset 0 0 0 3px ${C.orange}}
.key{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px;font-size:15px;color:${C.ink2}}
.key i{display:inline-block;width:14px;height:14px;border-radius:3px;margin-right:6px;vertical-align:-2px}
.ramp{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:14px;color:${C.ink2}}
.ramp div{display:flex;height:10px;flex:0 0 180px;border-radius:3px;overflow:hidden}
.ramp div span{flex:1}
.sum{margin-top:14px;background:${C.panel};border-radius:8px;padding:12px 14px;font-size:16px;line-height:1.6}`;
  const inner = `
    <div class="wrap">
      <div class="xl">永续增长率 g →</div>
      <table>
        <thead><tr><th class="rowh">WACC ↓</th>${gs.map((g) => `<th>${pct(g)}</th>`).join('')}</tr></thead>
        <tbody>${sens.map((row, i) => `<tr><th class="rowh">${pct(waccs[i])}</th>${row.map((v, j) => cell(v, i, j)).join('')}</tr>`).join('')}</tbody>
      </table>
      <div class="key"><span><i style="box-shadow:inset 0 0 0 3px ${C.orange}"></i>基准情形：WACC 8.5%，g 2.5%</span></div>
      <div class="ramp"><span>${f1(lo)} 元</span><div>${RAMP.map((c) => `<span style="background:${c}"></span>`).join('')}</div><span>${f1(hi)} 元</span></div>
      <div class="sum">WACC 取 8%～9%、g 取 2%～3% 时（表格中间的 9 个格子），每股价值为 ${f2(sens[3][1])}～${f2(sens[1][3])} 元，即股权价值约 ${Math.round(M.dcf_band[0])}～${Math.round(M.dcf_band[1])} 亿元。</div>
    </div>`;
  return page(frame('图 8', '敏感性分析：每股价值（元）', '两个参数各变动 1 个百分点，结果就能相差将近一倍', inner,
    '在 Excel 中可用“数据 → 模拟分析 → 模拟运算表”一次生成。'), { extraCss: css });
}

/* ---------- 图9 方法选择速查 ---------- */
function fig09() {
  const rows = [
    ['成熟盈利型（消费、医药等）', 'PE、DCF', 'PEG、EV/EBITDA'],
    ['银行', 'PB-ROE、DDM', '剩余收益模型'],
    ['保险', 'P/EV', 'PB'],
    ['券商', 'PB', 'PE'],
    ['公用事业、高速、水电', 'DDM、DCF', 'EV/EBITDA、股息率'],
    ['周期行业（钢铁、化工、有色、航运）', 'PB、正常化 PE', 'EV/EBITDA、重置成本'],
    ['重资产高负债（电信、物流）', 'EV/EBITDA', 'DCF'],
    ['科技成长、SaaS', 'PS、EV/Sales', 'DCF、PEG'],
    ['互联网平台', 'EV/Sales、DCF', '用户价值、SOTP'],
    ['创新药', 'rNPV', 'PS、可比交易'],
    ['房地产开发', 'NAV', 'PB'],
    ['矿业、油气', 'NAV', 'EV/储量、EV/EBITDA'],
    ['REITs', 'P/FFO、P/NAV', '分派率'],
    ['多元化集团', 'SOTP', '各分部按其行业'],
    ['初创企业', 'VC 法、可比融资', 'PS、用户价值'],
    ['困境、破产企业', '清算价值', '重置成本'],
  ];
  const css = `
table{width:100%;border-collapse:collapse;font-size:16px}
th{font-size:14px;font-weight:700;color:${C.ink2};text-align:left;padding:0 8px 10px;border-bottom:2px solid ${C.ink}}
td{padding:9px 8px;border-bottom:1px solid ${C.grid};vertical-align:middle;line-height:1.45}
td.t{font-weight:500;width:37%}
td.p{white-space:nowrap}
td.p b{display:inline-block;background:${C.blue50};color:${C.brand};font-weight:900;border-radius:5px;padding:2px 8px}
td.a{color:${C.ink2};font-size:14.5px}`;
  const inner = `<table><thead><tr><th>公司类型</th><th>首选方法</th><th>辅助方法</th></tr></thead><tbody>${rows.map(([t, p, a]) => `<tr><td class="t">${t}</td><td class="p"><b>${p}</b></td><td class="a">${a}</td></tr>`).join('')}</tbody></table>`;
  return page(frame('图 9', '按公司类型选择估值方法', '没有万能的模型，先看行业属性和发展阶段', inner,
    '无论选哪种方法，都至少再用一种方法交叉验证。'), { extraCss: css });
}

/* ---------- 图10 工作流程 ---------- */
function fig10() {
  const steps = [
    ['明确估值目的', '投资、融资、并购还是财务报告？决定了方法和价值类型', '估值范围'],
    ['理解业务', '商业模式、收入驱动因素、竞争格局、管理层', '投资逻辑'],
    ['收集数据', '财报公告、数据终端、行业数据、可比名单', '数据底稿'],
    ['财务分析与调整', '历史分析、剔除一次性项目、统一会计口径', '正常化财务数据'],
    ['建模，多方法估值', '三表预测、DCF、可比公司、可比交易', '估值模型'],
    ['交叉验证', '足球场图、敏感性分析、情景分析', '估值区间'],
    ['形成结论', '区间与中枢、关键假设、风险提示', '估值报告'],
  ];
  const css = `
.list{display:flex;flex-direction:column}
.st{display:grid;grid-template-columns:44px 1fr;gap:14px;position:relative;padding-bottom:16px}
.st:not(:last-child)::before{content:"";position:absolute;left:21px;top:44px;bottom:0;width:2px;background:${C.grid}}
.n{width:44px;height:44px;border-radius:50%;background:${C.brand};color:#fff;font-size:20px;font-weight:900;display:flex;align-items:center;justify-content:center}
.tx{padding-top:2px;min-width:0}
.tx b{font-size:19px;font-weight:900;margin-right:8px}
.tx .o{font-size:13.5px;font-weight:700;color:${C.orange};border:1px solid ${C.orange};border-radius:4px;padding:0 6px;vertical-align:2px;white-space:nowrap}
.tx p{font-size:16px;color:${C.ink2};margin-top:4px;line-height:1.55}
.loop{margin-top:4px;background:${C.panel};border-radius:8px;padding:12px 14px;font-size:15px;color:${C.ink2};line-height:1.6}`;
  const inner = `<div class="list">${steps.map(([t, d, o], i) => `<div class="st"><div class="n">${i + 1}</div><div class="tx"><b>${t}</b><span class="o">产出：${o}</span><p>${d}</p></div></div>`).join('')}</div>
    <div class="loop">出现新财报、行业变化或利率变化时，回到第 2 步更新假设。估值要定期复盘，而不是算完就结束。</div>`;
  return page(frame('图 10', '估值工作七步法', '从接到任务到交付报告的完整流程', inner, ''), { extraCss: css });
}

/* ---------- 图11 足球场图 ---------- */
function fig11() {
  const ranges = [
    ['可比公司 PE', '22–26 倍 × 5.0 亿元', 110, 130, null, false],
    ['可比公司 EV/EBITDA', '12–15 倍 × 8.25 亿元，加 6 亿元调整项', 105, 130, null, false],
    ['DCF', 'WACC 8%–9%，g 2%–3%', Math.round(M.dcf_band[0]), Math.round(M.dcf_band[1]), M.base.equity, false],
    ['先例交易', '15–18 倍 EV/EBITDA，含控制权溢价', 130, 155, null, true],
  ];
  const w = W - 52, padL = 16, padR = 14, lo = 80, hi = 170;
  const x = (v) => padL + ((v - lo) / (hi - lo)) * (w - padL - padR);
  const rowH = 74, top = 20, plotH = ranges.length * rowH;
  let s = '';
  // overlap band
  s += `<rect x="${x(110)}" y="${top - 8}" width="${x(125) - x(110)}" height="${plotH + 8}" fill="${C.orange50}"/>`;
  s += `<text x="${(x(110) + x(125)) / 2}" y="${top + plotH + 24}" font-size="14" font-weight="700" fill="${C.orange}" text-anchor="middle">重叠区间 110–125</text>`;
  [80, 100, 120, 140, 160].forEach((t) => {
    s += `<line x1="${x(t)}" x2="${x(t)}" y1="${top - 8}" y2="${top + plotH}" stroke="${C.grid}"/>`;
    s += `<text x="${x(t)}" y="${top + plotH + 44}" font-size="13" fill="${C.muted}" text-anchor="middle">${t}</text>`;
  });
  s += `<text x="${w - padR}" y="${top + plotH + 44}" font-size="13" fill="${C.muted}" text-anchor="end">亿元</text>`;
  ranges.forEach(([name, note, a, b, mid, ref], i) => {
    const yy = top + i * rowH;
    s += `<text x="${padL}" y="${yy + 14}" font-size="16" font-weight="700" fill="${ref ? C.ink2 : C.ink}">${name}${ref ? '（仅并购参考）' : ''}</text>`;
    s += `<text x="${padL}" y="${yy + 32}" font-size="13" fill="${C.muted}">${note}</text>`;
    const by = yy + 42, bh = 18;
    s += `<rect x="${x(a)}" y="${by}" width="${x(b) - x(a)}" height="${bh}" rx="4" fill="${ref ? '#b9c0ca' : C.blue}"/>`;
    s += `<text x="${x(a) - 6}" y="${by + 14}" font-size="14" fill="${C.ink2}" text-anchor="end">${a}</text>`;
    s += `<text x="${x(b) + 6}" y="${by + 14}" font-size="14" fill="${C.ink2}">${b}</text>`;
    if (mid) {
      s += `<line x1="${x(mid)}" x2="${x(mid)}" y1="${by - 4}" y2="${by + bh + 4}" stroke="${C.ink}" stroke-width="2.5"/>`;
    }
  });
  const H = top + plotH + 52;
  const inner = `
    <div class="legend"><span><i style="background:${C.blue}"></i>股权价值区间</span><span><i style="background:${C.ink};width:3px;border-radius:0"></i>DCF 基准值 ${f1(M.base.equity)}</span><span><i style="background:${C.orange50};border:1px solid ${C.orange}"></i>主要方法的重叠区间</span></div>
    <svg width="${w}" height="${H}" viewBox="0 0 ${w} ${H}">${s}</svg>`;
  return page(frame('图 11', '估值足球场图', '把各方法的结果放在一起，看它们在哪里重叠', inner,
    '结论：股权价值约 110～125 亿元，对应每股 11.0～12.5 元（总股本 10 亿股）。先例交易含控制权溢价，不用于少数股权投资。'));
}

/* ---------- 图12 公式速查卡 ---------- */
function fig12() {
  const groups = [
    ['相对估值', C.blue, [
      ['PE', '市值 ÷ 净利润'], ['PB', '市值 ÷ 净资产 = PE × ROE'], ['PS', '市值 ÷ 营收 = PE × 净利率'],
      ['PEG', 'PE ÷ (净利润增速 × 100)'], ['EV', '市值 + 有息负债 − 现金 + 少数股东权益'],
      ['合理 PB', '(ROE − g) ÷ (Ke − g)'],
    ]],
    ['绝对估值', C.orange, [
      ['FCFF', 'EBIT × (1 − t) + 折旧摊销 − 资本开支 − 营运资本增加'], ['FCFE', 'FCFF − 利息 × (1 − t) + 净借款'],
      ['Ke', 'Rf + β × ERP'], ['WACC', 'E/V × Ke + D/V × Kd × (1 − t)'], ['有杠杆 β', '无杠杆 β × [1 + (1 − t) × D/E]'],
      ['终值', 'FCFFₙ × (1 + g) ÷ (WACC − g)'], ['股权价值', 'EV − 净负债 − 少数股东权益 + 非经营性资产'],
      ['DDM', '每股价值 = D₁ ÷ (Ke − g)'],
    ]],
    ['口径与检查', C.aqua, [
      ['口径匹配', 'EV 配 EBITDA / EBIT / 营收；市值配净利润 / 净资产'], ['折现匹配', 'FCFF 配 WACC；FCFE 配 Ke'],
      ['永续增长', 'g 不超过长期名义 GDP 增速'], ['稳态再投资', '再投资率 = g ÷ ROIC'], ['终值占比', '通常 60%～80%，过高要警惕'],
    ]],
  ];
  const css = `
.g{margin-bottom:16px}
.g h2{font-size:18px;font-weight:900;display:flex;align-items:center;gap:8px;margin-bottom:6px}
.g h2 i{width:14px;height:14px;border-radius:4px;display:inline-block}
.r{display:grid;grid-template-columns:96px 1fr;gap:12px;padding:8px 0;border-bottom:1px solid ${C.grid};align-items:baseline}
.r b{font-size:16px;font-weight:900;color:${C.ink}}
.r span{font-size:16px;color:${C.ink};line-height:1.5}
.abbr{font-size:13.5px;color:${C.muted};line-height:1.7;margin-top:4px}`;
  const inner = groups.map(([name, col, items]) => `<div class="g"><h2><i style="background:${col}"></i>${name}</h2>${items.map(([k, v]) => `<div class="r"><b>${k}</b><span>${v}</span></div>`).join('')}</div>`).join('') +
    `<div class="abbr">t：税率　g：增长率　Ke：股权成本　Kd：债务成本　Rf：无风险利率　ERP：市场风险溢价　E/V、D/V：股权、债务占总资本比重　D₁：下一年每股股利</div>`;
  return page(frame('图 12', '估值公式速查卡', '建议保存，建模时随手对照', inner, ''), { extraCss: css });
}

/* ---------- 封面 ---------- */
function coverArt(wd, ht, bars = 7) {
  // 抽象的“现金流折现”柱：外框是名义现金流，实心是折现后的现值
  const gap = wd / bars, bw = gap * 0.46;
  let s = '';
  for (let i = 0; i < bars; i++) {
    const cf = 0.42 + i * 0.075, pv = cf / Math.pow(1.17, i + 1);
    const x = i * gap + (gap - bw) / 2;
    const hcf = ht * cf, hpv = ht * pv;
    s += `<rect x="${x}" y="${ht - hcf}" width="${bw}" height="${hcf}" rx="5" fill="none" stroke="#6da7ec" stroke-opacity=".55" stroke-width="2"/>`;
    s += `<rect x="${x}" y="${ht - hpv}" width="${bw}" height="${hpv}" rx="5" fill="${i === bars - 1 ? C.orange : '#3987e5'}"/>`;
  }
  return s;
}

function cover() {
  const css = `
.cv{width:900px;height:383px;background:#0f2340;position:relative;overflow:hidden;color:#fff;padding:52px 0 0 60px}
.kick{font-size:20px;font-weight:700;color:#86b6ef;letter-spacing:.2em}
.t{font-size:76px;font-weight:900;line-height:1.1;margin-top:16px;letter-spacing:.02em}
.s{font-size:24px;font-weight:500;color:#cde2fb;margin-top:22px;line-height:1.5}
.s b{color:#fff;font-weight:900}
.art{position:absolute;right:46px;bottom:0}
.eq{position:absolute;right:52px;top:44px;font-size:22px;color:#86b6ef;font-weight:500;letter-spacing:.04em}`;
  const body = `<div class="cv"><div class="kick">估值实务 · 收藏级长文</div><div class="t">估值模型全攻略</div>
    <div class="s">PE · PB · EV/EBITDA · DCF<br><b>怎么选 · 怎么用 · 怎么避坑</b></div>
    <div class="eq">V = Σ CFₜ ÷ (1 + r)ᵗ</div>
    <svg class="art" width="300" height="250" viewBox="0 0 300 250">${coverArt(300, 250)}</svg></div>`;
  return page(body, { width: 900, extraCss: css });
}

function coverSquare() {
  const css = `
.cv{width:500px;height:500px;background:#0f2340;position:relative;overflow:hidden;color:#fff;padding:56px 0 0 50px}
.kick{font-size:18px;font-weight:700;color:#86b6ef;letter-spacing:.2em}
.t{font-size:74px;font-weight:900;line-height:1.15;margin-top:14px}
.s{font-size:21px;color:#cde2fb;margin-top:18px;font-weight:500}
.art{position:absolute;right:40px;bottom:0}`;
  const body = `<div class="cv"><div class="kick">估值实务</div><div class="t">估值模型<br>全攻略</div><div class="s">怎么选 · 怎么用 · 怎么避坑</div>
    <svg class="art" width="230" height="150" viewBox="0 0 230 150">${coverArt(230, 150, 6)}</svg></div>`;
  return page(body, { width: 500, extraCss: css });
}

const FIGS = {
  'cover': [cover, '.cv', 2],
  'cover-square': [coverSquare, '.cv', 2],
  'fig01-methods-map': [fig01],
  'fig02-ev-vs-equity': [fig02],
  'fig03-comps-table': [fig03],
  'fig04-cyclical-pe': [fig04],
  'fig05-dcf-table': [fig05],
  'fig06-tv-share': [fig06],
  'fig07-ev-bridge': [fig07],
  'fig08-sensitivity': [fig08],
  'fig09-method-selector': [fig09],
  'fig10-workflow': [fig10],
  'fig11-football-field': [fig11],
  'fig12-cheatsheet': [fig12],
};

(async () => {
  const only = process.argv[2];
  fs.mkdirSync(OUT, { recursive: true });
  fs.mkdirSync(CACHE, { recursive: true });
  const browser = await chromium.launch();
  for (const [name, [fn, sel = '.fig', dsf = 3]] of Object.entries(FIGS)) {
    if (only && !name.includes(only)) continue;
    const ctx = await browser.newContext({ deviceScaleFactor: dsf, viewport: { width: 1000, height: 800 } });
    const pg = await ctx.newPage();
    const file = path.join(CACHE, name + '.html');
    fs.writeFileSync(file, fn());
    await pg.goto('file://' + file);
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(150);
    await pg.locator(sel).screenshot({ path: path.join(OUT, name + '.png') });
    await ctx.close();
    console.log('✓', name);
  }
  await browser.close();
})();
