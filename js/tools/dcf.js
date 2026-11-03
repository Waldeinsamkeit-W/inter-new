/* DCF 计算器：预填青禾饮品基准情景 */
(function () {
  const FM = window.FM;
  const f = FM.fmt;

  function caseDefaults() {
    const C = window.FM_CASE;
    const L = C.scen['1'].lines;
    const yrs = C.fc.map(String);
    const nwcRow = C.rows.find((r) => r.key === 'nwc');
    const rev = (y) => L.rev[y];
    return {
      base: 2600,
      years: C.fc,
      growth: yrs.map((y) => L.rev_g[y] * 100),
      ebitm: yrs.map((y) => (L.ebit[y] / rev(y)) * 100),
      dap: yrs.map((y) => (L.da[y] / rev(y)) * 100),
      capexp: yrs.map((y) => (L.capex[y] / rev(y)) * 100),
      nwcp: (nwcRow.values['2026'] / rev('2026')) * 100,
      nwc0: nwcRow.values['2025'],
      tax: C.assume.tax * 100,
      rf: C.valIn.rf * 100,
      beta: C.valIn.beta,
      erp: C.valIn.erp * 100,
      kd: C.valIn.kd * 100,
      dv: C.valIn.dv * 100,
      g: C.valIn.g * 100,
      exitm: 9.0,
      debt: L.debt_close['2025'],
      cash: L.cash['2025'],
      shares: C.shares,
      price: C.price,
    };
  }

  function compute(p, overrides) {
    const o = overrides || {};
    const t = p.tax / 100;
    const ke = p.rf / 100 + p.beta * (p.erp / 100);
    const kdat = (p.kd / 100) * (1 - t);
    const wacc = o.wacc !== undefined ? o.wacc : (1 - p.dv / 100) * ke + (p.dv / 100) * kdat;
    const g = o.g !== undefined ? o.g : p.g / 100;
    const n = p.years.length;
    const rows = [];
    let rev = p.base;
    let nwcPrev = p.nwc0;
    let sumPv = 0;
    for (let i = 0; i < n; i++) {
      rev = rev * (1 + p.growth[i] / 100);
      const ebit = (rev * p.ebitm[i]) / 100;
      const da = (rev * p.dap[i]) / 100;
      const capex = (rev * p.capexp[i]) / 100;
      const nwc = (rev * p.nwcp) / 100;
      const dnwc = nwc - nwcPrev;
      nwcPrev = nwc;
      const nopat = ebit * (1 - t);
      const fcff = nopat + da - capex - dnwc;
      const tt = p.mid ? i + 0.5 : i + 1;
      const df = 1 / Math.pow(1 + wacc, tt);
      const pv = fcff * df;
      sumPv += pv;
      rows.push({ year: p.years[i], rev, ebit, nopat, da, capex, dnwc, fcff, tt, df, pv, ebitda: ebit + da });
    }
    const last = rows[n - 1];
    let tv, tvT;
    if (p.tvm === 'exit') {
      tv = last.ebitda * p.exitm;
      tvT = n;
    } else {
      tv = (last.fcff * (1 + g)) / (wacc - g);
      tvT = p.mid ? n - 0.5 : n;
    }
    const pvTv = tv / Math.pow(1 + wacc, tvT);
    const ev = sumPv + pvTv;
    const equity = ev - p.debt + p.cash;
    const ps = equity / p.shares;
    const impliedMult = tv / last.ebitda;
    const impliedG = p.tvm === 'exit' ? (tv * wacc - last.fcff) / (tv + last.fcff) : g;
    return { ke, kdat, wacc, g, rows, tv, pvTv, sumPv, ev, equity, ps, tvShare: pvTv / ev, impliedMult, impliedG, ev1: ev / rows[0].ebitda };
  }

  FM.widgets.dcf = function (el) {
    const p = caseDefaults();
    p.mid = false;
    p.tvm = 'perp';
    const yrInputs = (key, label, hint) =>
      `<div class="fgroup"><legend>${label}</legend><div class="yrs">${p.years
        .map(
          (y, i) =>
            `<label for="dcf-${key}-${i}">${y}E<input class="inp" id="dcf-${key}-${i}" data-k="${key}" data-i="${i}" type="number" step="0.1" value="${p[key][i].toFixed(2)}"></label>`
        )
        .join('')}</div>${hint ? `<small class="xl-note" style="margin:0">${hint}</small>` : ''}</div>`;
    const one = (key, label, step, dec) =>
      `<div class="field"><label for="dcf-${key}">${label}</label><input id="dcf-${key}" data-k="${key}" type="number" step="${step}" value="${(+p[key]).toFixed(dec)}"></div>`;

    el.innerHTML = `<div class="tool">
      <p class="xl-note" style="margin-top:0">预填数据为青禾饮品基准情景（单位：百万元）。蓝色数字都可以修改；四舍五入后结果可能与 Excel 模型相差 0.01 元。</p>
      <div class="tool-grid">
        <div class="fields">
          <fieldset class="fgroup"><legend>经营假设</legend>
            ${one('base', '基期收入（2025A）', 10, 1)}
            ${one('tax', '所得税率 %', 0.5, 1)}
            ${one('nwcp', '营运资本占收入 %', 0.1, 2)}
            ${one('nwc0', '基期营运资本', 1, 1)}
          </fieldset>
          ${yrInputs('growth', '收入增长率 %')}
          ${yrInputs('ebitm', 'EBIT 利润率 %')}
          ${yrInputs('dap', '折旧摊销 / 收入 %')}
          ${yrInputs('capexp', '资本开支 / 收入 %')}
          <fieldset class="fgroup"><legend>折现率（WACC）</legend>
            ${one('rf', '无风险利率 %', 0.1, 2)}
            ${one('beta', '贝塔 β', 0.05, 2)}
            ${one('erp', '市场风险溢价 %', 0.1, 2)}
            ${one('kd', '税前债务成本 %', 0.1, 2)}
            ${one('dv', '负债占比 D/(D+E) %', 1, 1)}
          </fieldset>
          <fieldset class="fgroup"><legend>终值与股权价值</legend>
            <div class="field"><label for="dcf-tvm">终值方法</label><select id="dcf-tvm" data-k="tvm"><option value="perp">永续增长法</option><option value="exit">退出倍数法</option></select></div>
            ${one('g', '永续增长率 g %', 0.1, 2)}
            ${one('exitm', '退出 EV/EBITDA 倍数', 0.5, 1)}
            <div class="field"><label for="dcf-mid">年中折现</label><select id="dcf-mid" data-k="mid"><option value="0">否（年末）</option><option value="1">是（年中）</option></select></div>
            ${one('debt', '借款', 1, 1)}
            ${one('cash', '现金', 1, 1)}
            ${one('shares', '总股本（百万股）', 1, 1)}
            ${one('price', '当前股价（元）', 0.1, 2)}
          </fieldset>
          <button type="button" class="btn-ghost" id="dcf-reset">恢复青禾饮品默认值</button>
        </div>
        <div style="min-width:0" id="dcf-out"></div>
      </div></div>`;

    const out = el.querySelector('#dcf-out');
    const read = () => {
      el.querySelectorAll('[data-k]').forEach((inp) => {
        const k = inp.dataset.k;
        if (k === 'tvm') p.tvm = inp.value;
        else if (k === 'mid') p.mid = inp.value === '1';
        else if (inp.dataset.i !== undefined) p[k][+inp.dataset.i] = parseFloat(inp.value) || 0;
        else p[k] = parseFloat(inp.value) || 0;
      });
    };
    const render = () => {
      read();
      const r = compute(p);
      const flags = [];
      if (p.tvm === 'perp' && r.g >= r.wacc) {
        flags.push(['bad', `永续增长率（${f.pct(r.g, 2)}）必须小于 WACC（${f.pct(r.wacc, 2)}），否则终值公式没有意义。`]);
      } else {
        if (r.tvShare > 0.85) flags.push(['warn', `终值占企业价值 ${f.pct(r.tvShare)}，超过 85%：估值主要依赖遥远的未来，结论很脆弱。`]);
        if (p.tvm === 'perp' && r.g > 0.04) flags.push(['warn', `永续增长率 ${f.pct(r.g)} 偏高，一般不超过长期名义 GDP 增速（2%–3%）。`]);
        if (r.wacc < 0.05 || r.wacc > 0.15) flags.push(['warn', `WACC ${f.pct(r.wacc, 2)} 不在常见区间（约 6%–12%），检查参数单位。`]);
        const last = r.rows[r.rows.length - 1];
        if (last.capex < last.da) flags.push(['warn', '预测末年资本开支低于折旧：资产在萎缩，却假设永续增长，两者不一致。']);
        if (r.rows.some((x) => x.fcff < 0)) flags.push(['warn', '部分年份自由现金流为负，检查利润率和资本开支假设。']);
        if (p.tvm === 'exit') flags.push(['ok', `退出倍数 ${f.x(p.exitm)} 隐含永续增长率 ${f.pct(r.impliedG, 2)}。`]);
        else flags.push(['ok', `终值隐含 2030E EV/EBITDA 为 ${f.x(r.impliedMult)}，可以和可比公司对比。`]);
      }
      const bad = flags.some((x) => x[0] === 'bad');
      const up = r.ps / p.price - 1;
      const head = ['项目', ...r.rows.map((x) => x.year + 'E'), 'Excel 写法（第一年）'];
      const line = (label, key, cls, fn, fml) =>
        `<tr class="${cls || ''}"><td>${label}</td>${r.rows.map((x) => `<td>${fn ? fn(x[key]) : f.num(x[key])}</td>`).join('')}<td class="fml">${fml || ''}</td></tr>`;
      const sens = (() => {
        const ws = [-0.01, -0.005, 0, 0.005, 0.01].map((d) => r.wacc + d);
        const gs = [-0.01, -0.005, 0, 0.005, 0.01].map((d) => r.g + d);
        let h = `<table class="mtable heat"><thead><tr><th>WACC ↓ g →</th>${gs.map((g) => `<th>${f.pct(g)}</th>`).join('')}</tr></thead><tbody>`;
        ws.forEach((w, i) => {
          h += `<tr><td>${f.pct(w, 2)}</td>`;
          gs.forEach((g, j) => {
            const v = g >= w ? NaN : compute(Object.assign({}, p, { tvm: 'perp' }), { wacc: w, g }).ps;
            const k = isNaN(v) ? 0 : Math.max(-1, Math.min(1, (v / p.price - 1) / 0.4));
            const bg = isNaN(v) ? '' : `background:color-mix(in srgb, ${k >= 0 ? 'var(--good)' : 'var(--bad)'} ${Math.round(Math.abs(k) * 28)}%, transparent)`;
            h += `<td class="c${i === 2 && j === 2 ? ' base' : ''}" style="${bg}">${isNaN(v) ? 'n/a' : v.toFixed(2)}</td>`;
          });
          h += `</tr>`;
        });
        return h + `</tbody></table>`;
      })();
      out.innerHTML = `
        <div class="kpis">
          <div class="kpi main"><small>每股价值</small><b>${bad ? '–' : r.ps.toFixed(2)}</b></div>
          <div class="kpi"><small>相对股价 ${p.price.toFixed(2)}</small><b style="color:${up >= 0 ? 'var(--good)' : 'var(--bad)'}">${bad ? '–' : (up >= 0 ? '+' : '') + f.pct(up)}</b></div>
          <div class="kpi"><small>企业价值 EV</small><b>${bad ? '–' : f.num(r.ev)}</b></div>
          <div class="kpi"><small>WACC</small><b>${f.pct(r.wacc, 2)}</b></div>
          <div class="kpi"><small>终值占比</small><b>${bad ? '–' : f.pct(r.tvShare)}</b></div>
          <div class="kpi"><small>EV / 2026E EBITDA</small><b>${bad ? '–' : f.x(r.ev1)}</b></div>
        </div>
        ${flags.map(([c, t]) => `<div class="flag ${c}">${t}</div>`).join('')}
        <h3 style="margin:18px 0 8px;font-size:15px">自由现金流与折现</h3>
        <div class="tbl-scroll" style="margin:0"><table class="mtable"><thead><tr>${head.map((h) => `<th>${h}</th>`).join('')}</tr></thead><tbody>
          ${line('营业收入', 'rev', '', null, '上年 ×（1 + 增长率）')}
          ${line('EBIT', 'ebit', '', null, '收入 × EBIT 利润率')}
          ${line('NOPAT = EBIT ×（1 − 税率）', 'nopat', '', null, '=EBIT*(1-税率)')}
          ${line('加：折旧摊销', 'da', '', null, '收入 × 折旧率')}
          ${line('减：资本开支', 'capex', '', (v) => f.num(-v), '收入 × 资本开支率')}
          ${line('减：营运资本增加', 'dnwc', '', (v) => f.num(-v), '本年营运资本 − 上年')}
          ${line('FCFF', 'fcff', 'b', null, '=NOPAT+折旧-资本开支-营运资本增加')}
          ${line('折现期数', 'tt', 's', (v) => v.toFixed(1), p.mid ? '年中：0.5, 1.5, …' : '年末：1, 2, …')}
          ${line('折现因子', 'df', 's', (v) => v.toFixed(4), '=1/(1+WACC)^t')}
          ${line('现值', 'pv', 'b', null, '=FCFF*折现因子')}
        </tbody></table></div>
        <div class="cp" style="margin-top:14px">
          <div><span>预测期现值合计</span><b>${f.num(r.sumPv)}</b></div>
          <div><span>终值（${p.tvm === 'exit' ? '2030E EBITDA × ' + f.x(p.exitm) : 'FCFF × (1+g) ÷ (WACC − g)'}）</span><b>${bad ? '–' : f.num(r.tv)}</b></div>
          <div><span>终值现值</span><b>${bad ? '–' : f.num(r.pvTv)}</b></div>
          <div><span>企业价值 EV</span><b>${bad ? '–' : f.num(r.ev)}</b></div>
          <div><span>减：借款　加：现金</span><b>${f.num(-p.debt)}　${f.num(p.cash)}</b></div>
          <div><span>股权价值 ÷ 总股本 ${f.num(p.shares, 0)}</span><b>${bad ? '–' : f.num(r.equity) + ' → ' + r.ps.toFixed(2) + ' 元'}</b></div>
        </div>
        <h3 style="margin:18px 0 8px;font-size:15px">敏感性：每股价值（元），永续增长法</h3>
        <div class="tbl-scroll" style="margin:0">${sens}</div>
        <p class="xl-note">绿色表示高于当前股价，红色表示低于；框出的格子是当前假设。</p>`;
    };
    el.addEventListener('input', render);
    el.addEventListener('change', render);
    el.querySelector('#dcf-reset').addEventListener('click', () => {
      FM.widgets.dcf(el);
    });
    render();
  };

  FM.dcfCompute = compute;
})();
