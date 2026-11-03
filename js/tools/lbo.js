/* 迷你 LBO 计算器 */
(function () {
  const FM = window.FM;
  const f = FM.fmt;

  function compute(p) {
    const ev0 = p.e0 * p.entry;
    const fees = (ev0 * p.fees) / 100;
    const debt0 = p.e0 * p.lev;
    const eqIn = ev0 + fees - debt0;
    let debt = debt0, cash = 0, e = p.e0;
    const rows = [];
    for (let y = 1; y <= p.years; y++) {
      e = e * (1 + p.g / 100);
      const interest = (debt * p.rate) / 100;
      const da = (e * p.da) / 100;
      const ebt = e - da - interest;
      const tax = Math.max(0, (ebt * p.tax) / 100);
      const reinv = (e * p.capex) / 100;
      const fcf = e - interest - tax - reinv;
      const repay = Math.min(debt, Math.max(0, fcf));
      debt -= repay;
      cash += fcf - repay;
      rows.push({ y, e, interest, tax, reinv, fcf, repay, debt, cash, lev: debt / e });
    }
    const evExit = e * p.exit;
    const eqOut = evExit - debt + cash;
    const moic = eqOut / eqIn;
    const irr = moic > 0 ? Math.pow(moic, 1 / p.years) - 1 : -1;
    const attr = {
      growth: p.entry * (e - p.e0),
      multiple: (p.exit - p.entry) * e,
      delever: debt0 - debt + cash,
      fees: -fees,
    };
    return { ev0, fees, debt0, eqIn, rows, evExit, eqOut, moic, irr, attr, debtEnd: debt, cashEnd: cash };
  }

  FM.widgets.lbo = function (el) {
    const p = { e0: 100, entry: 8, fees: 2, lev: 4, rate: 7, g: 5, da: 10, capex: 20, tax: 25, years: 5, exit: 8 };
    const one = (k, label, step) =>
      `<div class="field"><label for="lbo-${k}">${label}</label><input id="lbo-${k}" data-k="${k}" type="number" step="${step}" value="${p[k]}"></div>`;
    el.innerHTML = `<div class="tool"><div class="tool-grid">
      <div class="fields">
        <fieldset class="fgroup"><legend>入场</legend>
          ${one('e0', '入场 EBITDA', 10)}${one('entry', '入场倍数（x EBITDA）', 0.5)}${one('fees', '交易费用 % EV', 0.5)}
          ${one('lev', '债务（x EBITDA）', 0.5)}${one('rate', '借款利率 %', 0.5)}
        </fieldset>
        <fieldset class="fgroup"><legend>经营</legend>
          ${one('g', 'EBITDA 年增长 %', 1)}${one('da', '折旧 % EBITDA（用于算税）', 1)}${one('capex', '资本开支 + 营运资本 % EBITDA', 1)}${one('tax', '所得税率 %', 1)}
        </fieldset>
        <fieldset class="fgroup"><legend>退出</legend>
          ${one('years', '持有年数', 1)}${one('exit', '退出倍数（x EBITDA）', 0.5)}
        </fieldset>
      </div>
      <div id="lbo-out" style="min-width:0"></div></div></div>`;
    const out = el.querySelector('#lbo-out');
    const render = () => {
      el.querySelectorAll('[data-k]').forEach((i) => (p[i.dataset.k] = parseFloat(i.value) || 0));
      p.years = Math.max(1, Math.min(10, Math.round(p.years)));
      const r = compute(p);
      const flags = [];
      if (r.eqIn <= 0) flags.push(['bad', '股权投入 ≤ 0：债务已经超过收购价，这在现实中不可能。降低杠杆倍数。']);
      if (r.rows.some((x) => x.fcf < 0)) flags.push(['bad', '某些年份可用现金为负：公司付不起利息和必要投资，交易不可行。']);
      if (p.lev > 6) flags.push(['warn', '杠杆超过 6 倍 EBITDA，在大多数市场都很难借到。']);
      if (p.exit > p.entry) flags.push(['warn', '退出倍数高于入场倍数：回报依赖市场估值上升，比较冒险。保守做法是假设退出倍数不高于入场倍数。']);
      if (!flags.length) flags.push(['ok', `私募基金常见的目标 IRR 约 20% 以上；当前 ${f.pct(r.irr)}。`]);
      const a = r.attr;
      const tot = a.growth + a.multiple + a.delever + a.fees;
      const bar = (label, v) => {
        const w = Math.min(100, (Math.abs(v) / Math.max(1, Math.abs(a.growth) + Math.abs(a.multiple) + Math.abs(a.delever) + Math.abs(a.fees))) * 100);
        return `<div style="display:grid;grid-template-columns:7.5em 1fr 4.5em;gap:8px;align-items:center;font-size:13px;margin:4px 0"><span>${label}</span><span style="height:12px;background:var(--sheet-2);border-radius:3px;overflow:hidden"><i style="display:block;height:100%;width:${w}%;background:${v >= 0 ? 'var(--good)' : 'var(--bad)'}"></i></span><span class="res-num" style="text-align:right">${f.num(v)}</span></div>`;
      };
      out.innerHTML = `
        <div class="kpis">
          <div class="kpi main"><small>IRR（年化）</small><b>${r.eqIn > 0 ? f.pct(r.irr) : '–'}</b></div>
          <div class="kpi"><small>MOIC（倍数）</small><b>${r.eqIn > 0 ? f.x(r.moic, 2) : '–'}</b></div>
          <div class="kpi"><small>股权投入</small><b>${f.num(r.eqIn)}</b></div>
          <div class="kpi"><small>退出股权价值</small><b>${f.num(r.eqOut)}</b></div>
        </div>
        ${flags.map(([c, t]) => `<div class="flag ${c}">${t}</div>`).join('')}
        <div class="cp">
          <div><span>入场企业价值 = ${f.num(p.e0)} × ${f.x(p.entry)}</span><b>${f.num(r.ev0)}</b></div>
          <div><span>加：交易费用</span><b>${f.num(r.fees)}</b></div>
          <div><span>资金来源：债务 ${f.num(p.e0)} × ${f.x(p.lev)}</span><b>${f.num(r.debt0)}</b></div>
          <div><span>资金来源：股权投入</span><b>${f.num(r.eqIn)}</b></div>
        </div>
        <div class="tbl-scroll"><table class="mtable"><thead><tr><th>年份</th>${r.rows.map((x) => `<th>第 ${x.y} 年</th>`).join('')}</tr></thead><tbody>
          <tr><td>EBITDA</td>${r.rows.map((x) => `<td>${f.num(x.e)}</td>`).join('')}</tr>
          <tr><td>减：利息（期初债务 × 利率）</td>${r.rows.map((x) => `<td>${f.num(-x.interest)}</td>`).join('')}</tr>
          <tr><td>减：所得税</td>${r.rows.map((x) => `<td>${f.num(-x.tax)}</td>`).join('')}</tr>
          <tr><td>减：资本开支 + 营运资本</td>${r.rows.map((x) => `<td>${f.num(-x.reinv)}</td>`).join('')}</tr>
          <tr class="b"><td>可用于还债的现金</td>${r.rows.map((x) => `<td>${f.num(x.fcf)}</td>`).join('')}</tr>
          <tr><td>还款 = MIN(期初债务, 可用现金)</td>${r.rows.map((x) => `<td>${f.num(x.repay)}</td>`).join('')}</tr>
          <tr class="b"><td>期末债务</td>${r.rows.map((x) => `<td>${f.num(x.debt)}</td>`).join('')}</tr>
          <tr><td>累计现金</td>${r.rows.map((x) => `<td>${f.num(x.cash)}</td>`).join('')}</tr>
          <tr class="s"><td>债务 / EBITDA</td>${r.rows.map((x) => `<td>${f.x(x.lev)}</td>`).join('')}</tr>
        </tbody></table></div>
        <div class="cp">
          <div><span>退出企业价值 = ${f.num(r.rows[r.rows.length - 1].e)} × ${f.x(p.exit)}</span><b>${f.num(r.evExit)}</b></div>
          <div><span>减：剩余债务　加：累计现金</span><b>${f.num(-r.debtEnd)}　${f.num(r.cashEnd)}</b></div>
          <div><span>退出股权价值</span><b>${f.num(r.eqOut)}</b></div>
        </div>
        <h3 style="font-size:15px;margin:16px 0 6px">股权增值 ${f.num(tot)} 来自哪里</h3>
        ${bar('EBITDA 增长', a.growth)}${bar('倍数变化', a.multiple)}${bar('还债 + 累计现金', a.delever)}${bar('交易费用', a.fees)}
        <p class="xl-note">IRR = MOIC^(1/年数) − 1（假设中间没有分红）。利息按期初债务计算，避免循环引用。</p>`;
    };
    el.addEventListener('input', render);
    render();
  };
})();
