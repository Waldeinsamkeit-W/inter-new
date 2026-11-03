/* 与"青禾饮品"案例数据相关的小组件 */
(function () {
  const FM = window.FM;
  const f = FM.fmt;
  const C = () => window.FM_CASE;
  const esc = FM.esc;

  /* ---------- 可比公司（虚构） ---------- */
  const PEERS = [
    { name: '山泉饮料', mcap: 12000, nd: -500, ebitda: 1150, ni: 720, g: '8%' },
    { name: '果园食品', mcap: 6300, nd: 400, ebitda: 640, ni: 390, g: '9%' },
    { name: '北岸茶业', mcap: 3900, nd: -200, ebitda: 420, ni: 270, g: '6%' },
    { name: '蓝湾乳饮', mcap: 9800, nd: 1200, ebitda: 1020, ni: 560, g: '7%' },
    { name: '星禾新饮', mcap: 2600, nd: 100, ebitda: 150, ni: -40, g: '35%' },
  ];
  // 与 Excel PERCENTILE.INC / QUARTILE.INC 一致的线性插值
  function pctile(arr, p) {
    const a = arr.slice().sort((x, y) => x - y);
    if (!a.length) return NaN;
    const h = (a.length - 1) * p;
    const lo = Math.floor(h);
    return a[lo] + (h - lo) * ((a[lo + 1] !== undefined ? a[lo + 1] : a[lo]) - a[lo]);
  }
  function compsStats(include) {
    const c = C();
    const L = c.scen['1'].lines;
    const ebitda = L.ebitda['2026'];
    const ni = L.ni['2026'];
    const netCash = L.cash['2025'] - L.debt_close['2025'];
    const ps = PEERS.filter((_, i) => include[i]);
    const evm = ps.map((p) => (p.mcap + p.nd) / p.ebitda);
    const pe = ps.filter((p) => p.ni > 0).map((p) => p.mcap / p.ni);
    const evPs = (m) => (ebitda * m + netCash) / c.shares;
    const pePs = (m) => (ni * m) / c.shares;
    return {
      ebitda, ni, netCash, evm, pe,
      ev: { q1: pctile(evm, 0.25), med: pctile(evm, 0.5), q3: pctile(evm, 0.75) },
      p: { q1: pctile(pe, 0.25), med: pctile(pe, 0.5), q3: pctile(pe, 0.75) },
      evPs, pePs,
    };
  }
  FM.compsStats = compsStats;

  FM.widgets.comps = function (el) {
    const inc = PEERS.map(() => true);
    const render = () => {
      const s = compsStats(inc);
      const rows = PEERS.map((p, i) => {
        const ev = p.mcap + p.nd;
        return `<tr style="${inc[i] ? '' : 'opacity:.45'}"><td><label style="display:flex;gap:8px;align-items:center;cursor:pointer"><input type="checkbox" data-i="${i}"${inc[i] ? ' checked' : ''}>${p.name}</label></td>
          <td>${f.num(p.mcap, 0)}</td><td>${f.num(p.nd, 0)}</td><td>${f.num(ev, 0)}</td><td>${f.num(p.ebitda, 0)}</td><td>${f.num(p.ni, 0)}</td><td>${p.g}</td>
          <td><b>${f.x(ev / p.ebitda)}</b></td><td><b>${p.ni > 0 ? f.x(p.mcap / p.ni) : 'NM'}</b></td></tr>`;
      }).join('');
      const stat = (label, k) =>
        `<tr class="b"><td>${label}</td><td colspan="6"></td><td>${isNaN(s.ev[k]) ? '–' : f.x(s.ev[k])}</td><td>${isNaN(s.p[k]) ? '–' : f.x(s.p[k])}</td></tr>`;
      el.innerHTML = `<div class="tbl-scroll"><table class="mtable"><thead><tr><th>公司（虚构）</th><th>市值</th><th>净债务</th><th>EV</th><th>EBITDA</th><th>净利润</th><th>增速</th><th>EV/EBITDA</th><th>P/E</th></tr></thead>
        <tbody>${rows}${stat('第 25 百分位', 'q1')}${stat('中位数', 'med')}${stat('第 75 百分位', 'q3')}</tbody></table></div>
        <div class="tbl-scroll"><table class="mtable"><thead><tr><th>应用到青禾饮品</th><th>指标（2026E）</th><th>低（25%）</th><th>中位数</th><th>高（75%）</th></tr></thead><tbody>
          <tr><td>EV/EBITDA → 每股价值（元）</td><td>EBITDA ${f.num(s.ebitda)}</td><td>${isNaN(s.ev.q1) ? '–' : s.evPs(s.ev.q1).toFixed(2)}</td><td><b>${isNaN(s.ev.med) ? '–' : s.evPs(s.ev.med).toFixed(2)}</b></td><td>${isNaN(s.ev.q3) ? '–' : s.evPs(s.ev.q3).toFixed(2)}</td></tr>
          <tr><td>P/E → 每股价值（元）</td><td>净利润 ${f.num(s.ni)}</td><td>${isNaN(s.p.q1) ? '–' : s.pePs(s.p.q1).toFixed(2)}</td><td><b>${isNaN(s.p.med) ? '–' : s.pePs(s.p.med).toFixed(2)}</b></td><td>${isNaN(s.p.q3) ? '–' : s.pePs(s.p.q3).toFixed(2)}</td></tr>
        </tbody></table></div>
        <p class="xl-note">EV/EBITDA 法：每股价值 = (EBITDA × 倍数 − 净债务) ÷ 总股本。青禾饮品 2025 年末是净现金 ${f.num(s.netCash)}，所以要加上。P/E 法：每股价值 = 净利润 × 倍数 ÷ 总股本。Excel 里中位数用 <code>=MEDIAN()</code>，分位数用 <code>=QUARTILE.INC()</code>，"NM"文本会被自动忽略。</p>`;
      el.querySelectorAll('input[type=checkbox]').forEach((cb) =>
        cb.addEventListener('change', () => {
          inc[+cb.dataset.i] = cb.checked;
          render();
        })
      );
    };
    render();
  };

  /* ---------- 历史比率 ---------- */
  FM.widgets['hist-ratios'] = function (el) {
    const H = C().histTable;
    const ys = ['2023', '2024', '2025'];
    const prev = (y) => String(+y - 1);
    const te = (y) => H[y].paid_in + H[y].re;
    const R = [
      ['sec', '增长'],
      ['收入增长率', (y) => (H[prev(y)].rev ? H[y].rev / H[prev(y)].rev - 1 : NaN), 'p'],
      ['销量增长率', (y) => (H[prev(y)].vol ? H[y].vol / H[prev(y)].vol - 1 : NaN), 'p'],
      ['均价增长率', (y) => (H[prev(y)].price ? H[y].price / H[prev(y)].price - 1 : NaN), 'p'],
      ['sec', '盈利'],
      ['毛利率（含折旧）', (y) => (H[y].rev - H[y].cogs - H[y].da) / H[y].rev, 'p'],
      ['成本率（不含折旧）', (y) => H[y].cogs / H[y].rev, 'p'],
      ['销售费用率', (y) => H[y].sell / H[y].rev, 'p'],
      ['管理及其他费用率', (y) => H[y].admin / H[y].rev, 'p'],
      ['EBITDA 利润率', (y) => H[y].ebitda / H[y].rev, 'p'],
      ['净利率', (y) => H[y].ni / H[y].rev, 'p'],
      ['有效税率', (y) => H[y].tax / H[y].ebt, 'p'],
      ['sec', '营运（期末余额）'],
      ['应收账款周转天数 DSO', (y) => (H[y].ar / H[y].rev) * 365, 'd'],
      ['存货周转天数 DIO', (y) => (H[y].inv / H[y].cogs) * 365, 'd'],
      ['应付账款周转天数 DPO', (y) => (H[y].ap / H[y].cogs) * 365, 'd'],
      ['现金转换周期', (y) => ((H[y].ar / H[y].rev) + (H[y].inv - H[y].ap) / H[y].cogs) * 365, 'd'],
      ['sec', '投资'],
      ['资本开支 / 收入', (y) => H[y].capex / H[y].rev, 'p'],
      ['资本开支 / 折旧', (y) => H[y].capex / H[y].da, 'x'],
      ['折旧率（占期初固定资产）', (y) => H[y].da / H[prev(y)].ppe, 'p'],
      ['sec', '回报与偿债'],
      ['ROE（平均所有者权益）', (y) => H[y].ni / ((te(y) + te(prev(y))) / 2), 'p'],
      ['净负债 / EBITDA', (y) => (H[y].debt - H[y].cash) / H[y].ebitda, 'x2'],
      ['利息保障倍数 EBIT / 利息', (y) => H[y].ebit / H[y].int_exp, 'x'],
    ];
    const fm = (v, t) => (isNaN(v) ? '–' : t === 'p' ? f.pct(v) : t === 'd' ? v.toFixed(1) : t === 'x2' ? f.x(v, 2) : f.x(v));
    el.innerHTML = `<div class="tbl-scroll"><table class="mtable"><thead><tr><th>比率</th>${ys.map((y) => `<th>${y}A</th>`).join('')}</tr></thead><tbody>${R.map((r) =>
      r[0] === 'sec' ? `<tr class="sec"><td colspan="4">${r[1]}</td></tr>` : `<tr><td>${r[0]}</td>${ys.map((y) => `<td>${fm(r[1](y), r[2])}</td>`).join('')}</tr>`
    ).join('')}</tbody></table></div>
    <p class="xl-note">2023 年的增长率需要 2022 年利润表数据，练习数据里没有，所以显示"–"。净负债为负表示现金多于借款（净现金）。</p>`;
  };

  /* ---------- 敏感性表 ---------- */
  FM.widgets.sens = function (el) {
    const s = C().sens;
    const price = C().price;
    let h = `<div class="tbl-scroll"><table class="mtable heat"><thead><tr><th>WACC ↓　g →</th>${s.g.map((g) => `<th>${f.pct(g)}</th>`).join('')}</tr></thead><tbody>`;
    s.grid.forEach((row, i) => {
      h += `<tr><td>${f.pct(s.wacc[i], 2)}</td>`;
      row.forEach((v, j) => {
        const k = Math.max(-1, Math.min(1, (v / price - 1) / 0.4));
        h += `<td class="c${i === 2 && j === 2 ? ' base' : ''}" style="background:color-mix(in srgb, ${k >= 0 ? 'var(--good)' : 'var(--bad)'} ${Math.round(Math.abs(k) * 28)}%, transparent)">${v.toFixed(2)}</td>`;
      });
      h += `</tr>`;
    });
    h += `</tbody></table></div><p class="xl-note">当前股价 ${price.toFixed(2)} 元：绿色高于股价，红色低于股价。与练习文件"估值"工作表第 4 步的表格一致。WACC 只变动 ±1%，每股价值就在 ${Math.min(...s.grid.flat()).toFixed(2)}–${Math.max(...s.grid.flat()).toFixed(2)} 元之间变化。</p>`;
    el.innerHTML = h;
  };

  /* ---------- 情景对比 ---------- */
  FM.widgets.scen = function (el) {
    const c = C();
    const sc = ['3', '1', '2'];
    const row = (label, fn) => `<tr><td>${label}</td>${sc.map((k) => `<td>${fn(c.scen[k])}</td>`).join('')}</tr>`;
    el.innerHTML = `<div class="tbl-scroll"><table class="mtable"><thead><tr><th>情景（假设页 C2）</th>${sc
      .map((k) => `<th>${k} · ${c.scen[k].name}</th>`)
      .join('')}</tr></thead><tbody>
      ${row('销量增长率 2026E → 2030E', (s) => '')}
      ${row('2030E 营业收入', (s) => f.num(s.lines.rev['2030']))}
      ${row('2030E EBITDA 利润率', (s) => f.pct(s.lines.ebitda_m['2030']))}
      ${row('2026E 每股收益（元）', (s) => s.lines.eps['2026'].toFixed(2))}
      ${row('企业价值', (s) => f.num(s.val.ev))}
      <tr class="b">${'<td>每股价值（元）</td>' + sc.map((k) => `<td>${c.scen[k].val.per_share.toFixed(2)}</td>`).join('')}</tr>
      ${row('相对股价 9.00 元', (s) => (s.val.upside >= 0 ? '+' : '') + f.pct(s.val.upside))}
    </tbody></table></div>`;
    // 填销量增长率
    const tds = el.querySelectorAll('tbody tr:first-child td');
    sc.forEach((k, i) => {
      const g = c.assume.vol_g[k];
      tds[i + 1].textContent = f.pct(g[0], 0) + ' → ' + f.pct(g[4], 0);
    });
  };

  /* ---------- 足球场图 ---------- */
  FM.widgets.football = function (el) {
    const c = C();
    const s = c.sens.grid;
    const inner = [s[1][1], s[1][2], s[1][3], s[2][1], s[2][2], s[2][3], s[3][1], s[3][2], s[3][3]];
    const cs = compsStats(PEERS.map(() => true));
    const bars = [
      ['DCF（WACC、g 各 ±0.5%）', Math.min(...inner), Math.max(...inner), c.scen['1'].val.per_share],
      ['DCF 情景（悲观 → 乐观）', c.scen['3'].val.per_share, c.scen['2'].val.per_share, c.scen['1'].val.per_share],
      ['可比公司 EV/EBITDA', cs.evPs(cs.ev.q1), cs.evPs(cs.ev.q3), cs.evPs(cs.ev.med)],
      ['可比公司 P/E', cs.pePs(cs.p.q1), cs.pePs(cs.p.q3), cs.pePs(cs.p.med)],
      ['52 周股价区间（虚构）', 7.2, 10.4, null],
    ];
    const lo = 6, hi = 13;
    const W = 640, L = 190, R = 20, rowH = 38, top = 30;
    const H = top + bars.length * rowH + 34;
    const x = (v) => L + ((v - lo) / (hi - lo)) * (W - L - R);
    let svg = `<svg class="ff" viewBox="0 0 ${W} ${H}" role="img" aria-label="青禾饮品估值足球场图">`;
    for (let v = lo; v <= hi; v++) {
      svg += `<line x1="${x(v)}" x2="${x(v)}" y1="${top - 4}" y2="${H - 28}" stroke="var(--grid)" stroke-width="1"/>`;
      svg += `<text x="${x(v)}" y="${H - 12}" text-anchor="middle" font-size="12" fill="var(--ink-3)" font-family="var(--f-mono)">${v}</text>`;
    }
    bars.forEach(([label, a, b, mid], i) => {
      const y = top + i * rowH;
      svg += `<text x="${L - 10}" y="${y + 18}" text-anchor="end" font-size="13" fill="var(--ink)">${esc(label)}</text>`;
      svg += `<rect x="${x(a)}" y="${y + 5}" width="${Math.max(2, x(b) - x(a))}" height="18" rx="3" fill="${i === 4 ? 'var(--sheet-3)' : 'var(--accent)'}" fill-opacity="${i === 4 ? 1 : 0.85}"/>`;
      if (mid) svg += `<line x1="${x(mid)}" x2="${x(mid)}" y1="${y + 3}" y2="${y + 25}" stroke="var(--ink)" stroke-width="2"/>`;
      svg += `<text x="${x(a) - 4}" y="${y + 18}" text-anchor="end" font-size="11" fill="var(--ink-2)" font-family="var(--f-mono)">${a.toFixed(1)}</text>`;
      svg += `<text x="${x(b) + 4}" y="${y + 18}" font-size="11" fill="var(--ink-2)" font-family="var(--f-mono)">${b.toFixed(1)}</text>`;
    });
    const px = x(c.price);
    svg += `<line x1="${px}" x2="${px}" y1="${top - 8}" y2="${H - 28}" stroke="var(--bad)" stroke-width="2" stroke-dasharray="5 4"/>`;
    svg += `<text x="${px}" y="${top - 13}" text-anchor="middle" font-size="11.5" fill="var(--bad)">当前股价 ${c.price.toFixed(2)}</text>`;
    svg += `</svg>`;
    el.innerHTML = `<div class="tbl-scroll" style="padding:12px 8px 4px"><div style="min-width:520px">${svg}</div></div><p class="xl-note">条形是估值区间，黑色竖线是该方法的中间值（基准或中位数），红色虚线是当前股价。单位：元/股。</p>`;
  };

  /* ---------- 原始数据复制 ---------- */
  FM.widgets['raw-copy'] = function (el) {
    const tsv = C().rawTsv;
    const lines = tsv.split('\n');
    const prev = lines.slice(0, 12).map((l) => l.split('\t'));
    el.innerHTML = `${FM.h.sheet({ title: '预览（前 12 行，共 ' + lines.length + ' 行）', rows: prev.map((r) => r.map((c) => (c === '' ? '' : '_' === c[0] ? c : c))) })}
      <div class="copy-row"><button type="button" class="btn" id="raw-btn">复制全部原始数据</button><a class="btn sec" href="practice/青禾饮品_原始数据.csv" download>下载 CSV</a><span class="xl-note" style="margin:0">复制后在 Excel 里选中 A1 粘贴，数据会自动分列。</span></div>
      <textarea class="copy-fallback" id="raw-ta" hidden readonly aria-label="原始数据文本">${esc(tsv)}</textarea>`;
    el.querySelector('#raw-btn').addEventListener('click', (e) => FM.copy(tsv, e.currentTarget, el.querySelector('#raw-ta')));
  };

  /* ---------- 检查点 ---------- */
  FM.widgets.checkpoints = function (el) {
    const c = C();
    const row = (k) => c.rows.find((r) => r.key === k).values;
    const H = c.histTable;
    const v = c.scen['1'].val;
    const n = (x, d = 1) => f.num(x, d);
    const steps = [
      ['1', '清洗原始数据', 'clean-steps', [
        ['2025 营业收入（百万元）', n(H['2025'].rev)],
        ['2025 资产总计', n(H['2025'].cash + H['2025'].ar + H['2025'].inv + H['2025'].ppe + H['2025'].other)],
        ['2025 投资活动现金流', n(-H['2025'].capex)],
      ]],
      ['2', '映射与汇总', 'clean-map', [
        ['2025 管理及其他费用', n(H['2025'].admin)],
        ['2025 营业成本（不含折旧摊销）', n(H['2025'].cogs)],
        ['2025 固定资产（净）', n(H['2025'].ppe)],
        ['2025 银行借款 / 留存收益', n(H['2025'].debt) + ' / ' + n(H['2025'].re)],
      ]],
      ['3', '历史数据校验', 'clean-check', [
        ['所有校验', 'TRUE'],
        ['2025 模型口径经营现金流（+ 利息 = 报告值）', n(H['2025'].cfo) + ' + ' + n(H['2025'].int_exp) + ' = ' + n(H['2025'].cfo + H['2025'].int_exp)],
        ['2024 正常化净利润（剔除营业外收入）', n(H['2024'].ni - 30 * 0.75)],
      ]],
      ['4', '历史比率', 'hist-ratios', [
        ['2025 EBITDA 利润率', f.pct(H['2025'].ebitda / H['2025'].rev)],
        ['2025 DSO / DIO / DPO（天）', [H['2025'].ar / H['2025'].rev, H['2025'].inv / H['2025'].cogs, H['2025'].ap / H['2025'].cogs].map((x) => (x * 365).toFixed(1)).join(' / ')],
      ]],
      ['5', '收入预测', 'build-revenue', [
        ['2026E 营业收入', n(row('rev')['2026'])],
        ['2030E 营业收入', n(row('rev')['2030'])],
      ]],
      ['6', '成本费用、折旧、利息、利润表', 'build-is', [
        ['2026E EBITDA', n(row('ebitda')['2026'])],
        ['2026E 折旧摊销 / 利息费用 / 利息收入', [row('da')['2026'], row('int_exp')['2026'], row('int_inc')['2026']].map((x) => n(x)).join(' / ')],
        ['2026E 净利润 / EPS（元）', n(row('ni')['2026']) + ' / ' + row('eps')['2026'].toFixed(2)],
      ]],
      ['7', '营运资本、固定资产、借款', 'build-wc', [
        ['2026E 营运资本增加', n(row('dnwc')['2026'])],
        ['2026E 固定资产期末净值', n(row('ppe_close')['2026'])],
        ['2026E 期末借款', n(row('debt_close')['2026'])],
      ]],
      ['8', '资产负债表与现金流量表', 'build-cf', [
        ['2026E 经营活动现金流', n(row('cfo')['2026'])],
        ['2026E 期末现金 / 资产合计', n(row('cash')['2026']) + ' / ' + n(row('ta')['2026'])],
        ['2030E 期末现金', n(row('cash')['2030'])],
        ['2026E–2030E 平衡检查', '全部为 0'],
      ]],
      ['9', 'DCF 估值', 'method-dcf', [
        ['WACC', f.pct(v.wacc, 2)],
        ['2026E FCFF', n(c.scen['1'].fcff['2026'])],
        ['终值 / 企业价值', n(v.tv) + ' / ' + n(v.ev)],
        ['每股价值（元）', v.per_share.toFixed(2)],
      ]],
      ['10', '敏感性与情景', 'method-sens', [
        ['乐观 / 悲观情景每股价值（元）', c.scen['2'].val.per_share.toFixed(2) + ' / ' + c.scen['3'].val.per_share.toFixed(2)],
        ['WACC 7.03%、g 2.5% 时每股价值', c.sens.grid[0][3].toFixed(2)],
      ]],
    ];
    el.innerHTML = `<div class="tbl-scroll"><table class="tbl"><thead><tr><th>步骤</th><th>任务</th><th>检查点</th><th style="text-align:right">应得结果</th></tr></thead><tbody>${steps
      .map(([no, t, link, cps]) =>
        cps
          .map(
            ([k, val], i) =>
              `<tr>${i === 0 ? `<td rowspan="${cps.length}" style="font-family:var(--f-mono);font-weight:700">${no}</td><td rowspan="${cps.length}"><b>${t}</b><br><a href="#${link}" style="font-size:13px">对应课程 →</a></td>` : ''}<td>${k}</td><td class="num"><b>${val}</b></td></tr>`
          )
          .join('')
      )
      .join('')}</tbody></table></div>`;
  };

  /* ---------- 完整模型 ---------- */
  FM.widgets['case-model'] = function (el) {
    const c = C();
    const yrs = c.hist.concat(c.fc).map(String);
    let mode = 'formula';
    const fmtv = (v, unit) => {
      if (v === undefined || v === null) return '';
      if (unit === '%') return f.pct(v);
      if (unit === '天') return v.toFixed(1);
      if (unit === '元/箱' || unit === '元/股') return v.toFixed(2);
      if (unit === '万箱') return f.num(v, 0);
      return f.num(v);
    };
    const render = () => {
      const head = `<tr><th>行</th><th>科目</th><th>单位</th>${yrs.map((y, i) => `<th>${y}${i < 3 ? 'A' : 'E'}</th>`).join('')}<th style="text-align:left">${mode === 'formula' ? 'G 列（2026E）公式' : '计算逻辑'}</th></tr>`;
      const body = c.rows
        .map((r) => {
          if (r.sec) return `<tr class="sec"><td colspan="${yrs.length + 4}">${esc(r.sec)}</td></tr>`;
          const b = ['rev', 'is_rev', 'ebitda', 'ebit', 'ebt', 'ni', 'nwc', 'ppe_close', 'debt_close', 'ta', 'tl', 'te', 'tle', 'cfo', 'cfi', 'cff', 'cash_close'].includes(r.key);
          return `<tr class="${b ? 'b' : r.indent ? 's' : ''}"><td class="fml">${r.row}</td><td>${esc(r.label)}</td><td class="fml">${esc(r.unit)}</td>${yrs
            .map((y, i) => `<td class="${i >= 3 ? 'e' : ''}">${fmtv(r.values[y], r.unit)}</td>`)
            .join('')}<td class="fml">${esc(mode === 'formula' ? r.formula || '' : r.logic || '')}</td></tr>`;
        })
        .join('');
      el.innerHTML = `<div class="copy-row"><div class="seg" role="group" aria-label="最后一列显示"><button type="button" data-m="formula" class="${mode === 'formula' ? 'on' : ''}">显示公式</button><button type="button" data-m="logic" class="${mode === 'logic' ? 'on' : ''}">显示计算逻辑</button></div></div>
        <div class="tbl-scroll"><table class="mtable"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
      el.querySelectorAll('.seg button').forEach((b) =>
        b.addEventListener('click', () => {
          mode = b.dataset.m;
          render();
        })
      );
    };
    render();
  };

  FM.widgets['case-val'] = function (el) {
    const c = C();
    const v = c.scen['1'].val;
    const vi = c.valIn;
    const fc = c.scen['1'].fcff;
    el.innerHTML = `<div class="tbl-scroll"><table class="mtable"><thead><tr><th>估值工作表</th><th>数值</th><th style="text-align:left">公式 / 说明</th></tr></thead><tbody>
      <tr class="sec"><td colspan="3">WACC</td></tr>
      <tr><td>无风险利率 / β / 市场风险溢价</td><td>${f.pct(vi.rf)} / ${vi.beta.toFixed(2)} / ${f.pct(vi.erp)}</td><td class="fml">示例取值</td></tr>
      <tr><td>股权成本 Ke</td><td>${f.pct(v.ke, 2)}</td><td class="fml">=Rf+β×ERP</td></tr>
      <tr><td>税后债务成本</td><td>${f.pct(v.kd_at, 2)}</td><td class="fml">=5.0%×(1−25%)</td></tr>
      <tr class="b"><td>WACC</td><td>${f.pct(v.wacc, 3)}</td><td class="fml">=90%×Ke+10%×税后债务成本</td></tr>
      <tr class="sec"><td colspan="3">自由现金流 FCFF</td></tr>
      ${Object.keys(fc).map((y) => `<tr><td>${y}E</td><td>${f.num(fc[y])}</td><td class="fml">NOPAT + 折旧 − 资本开支 − 营运资本增加</td></tr>`).join('')}
      <tr class="sec"><td colspan="3">从企业价值到每股价值</td></tr>
      <tr><td>预测期现值合计</td><td>${f.num(v.sum_pv)}</td><td class="fml">=SUM(G30:K30)</td></tr>
      <tr><td>终值 TV</td><td>${f.num(v.tv)}</td><td class="fml">=K27*(1+g)/(WACC−g)</td></tr>
      <tr><td>终值现值</td><td>${f.num(v.pv_tv)}</td><td class="fml">=TV×K29</td></tr>
      <tr class="b"><td>企业价值 EV</td><td>${f.num(v.ev)}</td><td class="fml">终值占 ${f.pct(v.tv_share)}</td></tr>
      <tr><td>减：净债务（净现金为负）</td><td>${f.num(-v.net_debt)}</td><td class="fml">−借款 420.0 + 现金 442.3</td></tr>
      <tr class="b"><td>股权价值</td><td>${f.num(v.equity)}</td><td class="fml"></td></tr>
      <tr class="b"><td>每股价值（元）</td><td>${v.per_share.toFixed(2)}</td><td class="fml">÷ 500 百万股；相对股价 ${(v.upside >= 0 ? '+' : '') + f.pct(v.upside)}</td></tr>
      <tr><td>隐含 EV / 2026E EBITDA</td><td>${f.x(v.ev_ebitda_26)}</td><td class="fml">终值隐含 2030E 倍数 ${f.x(v.tv_ebitda)}</td></tr>
    </tbody></table></div>`;
  };

  FM.widgets.mapping = function (el) {
    const m = C().mapping;
    el.innerHTML = FM.h.table(
      ['原始科目', '标准科目', '说明'],
      m.map((r) => [esc(r.raw), r.std === '忽略' ? `<span style="color:var(--ink-3)">忽略</span>` : `<b>${esc(r.std)}</b>`, esc(r.note)])
    );
  };

  /* ---------- 术语表 ---------- */
  const GLOSSARY = [
    ['营业收入', 'Revenue / Sales', '卖产品和服务的收入'],
    ['营业成本', 'COGS（Cost of Goods Sold）', '直接生产或采购产品的成本'],
    ['毛利 / 毛利率', 'Gross Profit / Gross Margin', '收入 − 营业成本'],
    ['销售费用 / 管理费用', 'S&M / G&A（合称 SG&A）', '经营费用'],
    ['息税折旧摊销前利润', 'EBITDA', 'EBIT + 折旧摊销；衡量经营层面的现金盈利'],
    ['息税前利润', 'EBIT', '扣利息和所得税之前的经营利润'],
    ['税后经营利润', 'NOPAT', 'EBIT ×（1 − 税率）'],
    ['净利润 / 归母净利润', 'Net Income / NI attributable to parent', '归母：归属于母公司股东'],
    ['每股收益', 'EPS', '净利润 ÷ 股本'],
    ['折旧与摊销', 'D&A（Depreciation & Amortization）', '固定资产折旧 + 无形资产摊销'],
    ['资本开支', 'Capex（Capital Expenditure）', '购建固定资产、无形资产的支出'],
    ['营运资本', 'NWC（Net Working Capital）', '经营性流动资产 − 经营性流动负债'],
    ['应收账款周转天数', 'DSO（Days Sales Outstanding）', '应收 ÷ 收入 × 365'],
    ['存货周转天数', 'DIO（Days Inventory Outstanding）', '存货 ÷ 营业成本 × 365'],
    ['应付账款周转天数', 'DPO（Days Payable Outstanding）', '应付 ÷ 营业成本 × 365'],
    ['现金转换周期', 'CCC（Cash Conversion Cycle）', 'DSO + DIO − DPO'],
    ['企业自由现金流', 'FCFF（Free Cash Flow to Firm）', 'NOPAT + 折旧 − 资本开支 − 营运资本增加'],
    ['股权自由现金流', 'FCFE（Free Cash Flow to Equity）', 'FCFF − 税后利息 + 净借款'],
    ['企业价值', 'EV（Enterprise Value）', '股权价值 + 净债务 + 少数股东权益 + …'],
    ['股权价值', 'Equity Value', '属于股东的价值；上市公司 = 市值'],
    ['净债务', 'Net Debt', '有息负债 − 现金'],
    ['少数股东权益', 'Minority Interest / NCI', '子公司中不属于母公司的部分'],
    ['加权平均资本成本', 'WACC', '股权成本和税后债务成本按资本结构加权'],
    ['资本资产定价模型', 'CAPM', 'Ke = Rf + β × ERP'],
    ['无风险利率', 'Risk-free Rate（Rf）', '通常用 10 年期国债收益率'],
    ['市场风险溢价', 'ERP（Equity Risk Premium）', '股票市场相对无风险资产的超额回报要求'],
    ['贝塔', 'Beta（β）', '股票相对市场的波动程度'],
    ['终值', 'TV（Terminal Value）', '预测期之后所有现金流在预测期末的价值'],
    ['永续增长率', 'Perpetual Growth Rate（g）', '预测期之后的长期增长率'],
    ['年中折现惯例', 'Mid-year Convention', '假设现金流在年中发生'],
    ['可比公司分析', 'Trading Comps', '用同类上市公司的倍数估值'],
    ['先例交易分析', 'Precedent Transactions', '用历史并购交易的倍数估值'],
    ['市盈率', 'P/E', '市值 ÷ 净利润'],
    ['市净率', 'P/B', '市值 ÷ 净资产'],
    ['市销率', 'P/S、EV/Sales', '估值 ÷ 收入'],
    ['最近十二个月', 'LTM / TTM', 'Last / Trailing Twelve Months'],
    ['日历化', 'Calendarization', '把不同财年的数据换算到同一自然年'],
    ['股利折现模型', 'DDM（Dividend Discount Model）', '用未来股利折现估值'],
    ['资产净值法', 'NAV（Net Asset Value）', '逐项评估资产减负债'],
    ['杠杆收购', 'LBO（Leveraged Buyout）', '用大量借款收购公司'],
    ['内部收益率', 'IRR', '使净现值为 0 的折现率'],
    ['投资回报倍数', 'MOIC', '退出时股权价值 ÷ 投入股权'],
    ['现金扫款', 'Cash Sweep', '用多余现金提前还债'],
    ['循环信用额度', 'Revolver', '可随借随还的银行授信'],
    ['净资产收益率', 'ROE', '净利润 ÷ 平均所有者权益'],
    ['投入资本回报率', 'ROIC', 'NOPAT ÷ 投入资本'],
    ['非经常性损益', 'Non-recurring Items', '一次性的收益或损失'],
    ['敏感性分析', 'Sensitivity Analysis', '看结果随某个假设变化的程度'],
    ['情景分析', 'Scenario Analysis', '一组假设一起变化（基准/乐观/悲观）'],
    ['模拟运算表', 'Data Table', 'Excel 做敏感性分析的工具'],
    ['单变量求解', 'Goal Seek', 'Excel 反向求解工具'],
    ['循环引用', 'Circular Reference', '公式直接或间接引用了自己'],
    ['螺旋结构', 'Corkscrew', '期初 + 增加 − 减少 = 期末，下年期初 = 本年期末'],
    ['硬编码', 'Hard-code', '在公式里直接写数字（应避免）'],
  ];
  FM.widgets.glossary = function (el) {
    el.innerHTML = `<label for="glo-q" class="xl-note" style="display:block">筛选（中文、英文或缩写都可以）</label><input id="glo-q" class="glo-filter" type="search" placeholder="例如：WACC、折旧、EV" autocomplete="off"><div id="glo-t"></div>`;
    const t = el.querySelector('#glo-t');
    const render = (q) => {
      q = (q || '').trim().toLowerCase();
      const rows = GLOSSARY.filter((r) => !q || r.join(' ').toLowerCase().includes(q));
      t.innerHTML = rows.length
        ? FM.h.table(['中文', '英文', '一句话解释'], rows.map((r) => [`<b>${r[0]}</b>`, r[1], r[2]]), { cls: 'nowrap1' })
        : `<p class="xl-note">没有匹配的术语。</p>`;
    };
    el.querySelector('#glo-q').addEventListener('input', (e) => render(e.target.value));
    render('');
  };
})();
