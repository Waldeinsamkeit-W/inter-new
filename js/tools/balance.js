/* 配平排错助手 */
(function () {
  const FM = window.FM;
  const TOL = 0.05;
  const near = (a, b) => Math.abs(a - b) <= Math.max(TOL, Math.abs(b) * 0.005);

  function diagnose(diffs, items) {
    const n = diffs.length;
    const inc = diffs.map((d, i) => (i === 0 ? d : d - diffs[i - 1]));
    const allZero = diffs.every((d) => Math.abs(d) <= TOL);
    const res = { inc, kind: '', title: '', text: '', steps: [], matches: [] };
    if (allZero) {
      res.kind = 'ok';
      res.title = '每年都平衡';
      res.text = '差额全部为 0（或小于 0.05），不需要排查。记得切换情景、做压力测试后再看一次。';
      return res;
    }
    const firstNZ = diffs.findIndex((d) => Math.abs(d) > TOL);
    const after = inc.slice(firstNZ + 1);
    const constAfter = after.every((d) => Math.abs(d) <= TOL);
    const sameSign = inc.slice(firstNZ).every((d) => Math.abs(d) > TOL && Math.sign(d) === Math.sign(inc[firstNZ]));
    if (constAfter && firstNZ === 0) {
      res.kind = 'const';
      res.title = '第一年出现差额，之后每年不变';
      res.text = '错误只发生了一次，而且就在预测期的起点：通常是<b>期初衔接</b>出了问题。';
      res.steps = [
        '历史最后一年（2025A）的资产负债表本身平衡吗？',
        '第一个预测年的期初现金是否引用了上年资产负债表的货币资金？',
        '留存收益是否从上年留存收益开始累加？（=上年 + 净利润 − 股利）',
        '期初固定资产、期初借款是否引用了上年期末，而不是手动输入的数字？',
        `差额 ${diffs[0].toFixed(2)} 是否刚好等于历史期某个科目的金额？`,
      ];
    } else if (constAfter) {
      res.kind = 'once';
      res.title = `差额从第 ${firstNZ + 1} 个预测年开始出现，之后不变`;
      res.text = '错误只在那一年发生了一次。看那一列的公式和前一列有什么不同，或者那一年有什么特殊假设（借款到期、某项假设变成 0…）。';
      res.steps = ['按 Ctrl+` 显示公式，对比这一列和前一列。', '看那一年的假设是否有特殊值。', '检查有没有"只在那一年"手动改过的单元格。'];
    } else if (sameSign) {
      res.kind = 'grow';
      res.title = '差额逐年累积';
      res.text = '每年都多出（或少了）一笔：有一个<b>每年都在变动的科目</b>没有进入现金流量表、重复进入了，或者符号反了。';
      res.steps = [
        `差额为${inc[firstNZ] > 0 ? '正：资产多了（通常是现金多了）→ 现金流量表里少扣了一项资产的增加，或少算了一项负债的减少，或者把一项流出写成了流入' : '负：资产少了（通常是现金少了）→ 现金流量表里多扣了一项，或者漏掉了一项负债 / 权益的增加'}。`,
        '拿出"资产负债表 ↔ 现金流量表"对照表，逐个科目核对：有没有？出现几次？符号对吗？',
        '把每年新增的差额和各科目每年的变动额比较（可以在下面填入科目变动）。',
        '等于 1 倍 → 漏了或重复了；等于 2 倍 → 符号反了。',
      ];
    } else {
      res.kind = 'mixed';
      res.title = '差额没有规律';
      res.text = '可能同时存在多个错误，或者有循环引用没有收敛。先确认没有意外的循环引用（看 Excel 状态栏），然后从最早出现差额的那一年开始，一次只修一个错误，每修一个看一次差额的变化。';
      res.steps = ['检查状态栏是否提示"循环引用"。', '如果开启了迭代计算，把断路开关设为 1 看看。', '从第一个出现差额的年份开始逐项排查。'];
    }
    // 与科目变动比对
    items.forEach((it) => {
      if (!it.name) return;
      const vals = it.vals;
      if (vals.every((v) => isNaN(v))) return;
      const check = (target, label) => {
        let hit = 0, hit2 = 0, hitN = 0, cnt = 0;
        target.forEach((d, i) => {
          const v = vals[i];
          if (isNaN(v) || Math.abs(v) <= TOL || Math.abs(d) <= TOL) return;
          cnt++;
          if (near(Math.abs(d), Math.abs(v))) hit++;
          else if (near(Math.abs(d), Math.abs(2 * v))) hit2++;
          if (near(d, v) || near(d, 2 * v)) hitN++;
        });
        if (cnt && hit === cnt) res.matches.push(`<b>${it.name}</b>：${label}和它每年的变动额<b>相等</b> → 这一项很可能<b>漏了</b>或者<b>重复</b>了。`);
        else if (cnt && hit2 === cnt) res.matches.push(`<b>${it.name}</b>：${label}正好是它每年变动额的<b>两倍</b> → 这一项在现金流量表里的<b>符号很可能反了</b>。`);
      };
      check(inc, '每年新增的差额');
      if (res.kind !== 'grow') check(diffs, '差额');
    });
    return res;
  }

  FM.widgets.balance = function (el) {
    const years = ['2026E', '2027E', '2028E', '2029E', '2030E'];
    const example = [31.9, 64.1, 96.0, 124.9, 151.8];
    const exItems = [
      ['应收账款增加', [31.9, 32.2, 31.9, 28.9, 26.9]],
      ['存货增加', [31.1, 31.4, 31.1, 28.2, 26.3]],
      ['应付账款增加', [26.0, 30.1, 29.9, 27.1, 25.2]],
    ];
    const yrRow = (prefix, vals) =>
      `<div class="yrs">${years
        .map((y, i) => `<label for="${prefix}-${i}">${y}<input class="inp" id="${prefix}-${i}" type="number" step="0.1" value="${vals[i] !== undefined ? vals[i] : ''}"></label>`)
        .join('')}</div>`;
    el.innerHTML = `<div class="tool">
      <p class="xl-note" style="margin-top:0">已经预填了 4.11 节的例子（漏写了"应收账款增加"）。换成你自己模型的数字试试。</p>
      <div class="tool-grid">
        <div class="fields">
          <fieldset class="fgroup"><legend>平衡检查行：资产 − 负债和权益</legend>${yrRow('bl-d', example)}</fieldset>
          <fieldset class="fgroup"><legend>科目变动（可选，本年 − 上年）</legend>
          ${exItems
            .map(
              ([n, v], k) =>
                `<div style="display:grid;gap:6px;margin-bottom:10px"><input class="inp" id="bl-n-${k}" value="${n}" aria-label="科目名称" style="text-align:left;color:var(--ink);font-family:var(--f-body)">${yrRow('bl-i' + k, v)}</div>`
            )
            .join('')}
          </fieldset>
          <button type="button" class="btn-ghost" id="bl-clear">清空，输入我自己的数字</button>
        </div>
        <div id="bl-out" style="min-width:0"></div>
      </div></div>`;
    const out = el.querySelector('#bl-out');
    const num = (id) => parseFloat(el.querySelector('#' + id).value);
    const render = () => {
      const diffs = years.map((_, i) => num('bl-d-' + i) || 0);
      const items = exItems.map((_, k) => ({ name: el.querySelector('#bl-n-' + k).value.trim(), vals: years.map((_, i) => num(`bl-i${k}-${i}`)) }));
      const r = diagnose(diffs, items);
      const cls = r.kind === 'ok' ? 'ok' : r.kind === 'mixed' ? 'bad' : 'warn';
      out.innerHTML = `
        <div class="tbl-scroll" style="margin-top:0"><table class="mtable"><thead><tr><th>年份</th>${years.map((y) => `<th>${y}</th>`).join('')}</tr></thead><tbody>
          <tr><td>差额</td>${diffs.map((d) => `<td>${d.toFixed(2)}</td>`).join('')}</tr>
          <tr><td>每年新增</td>${r.inc.map((d) => `<td>${d.toFixed(2)}</td>`).join('')}</tr>
          <tr class="s"><td>差额 ÷ 2</td>${diffs.map((d) => `<td>${(d / 2).toFixed(2)}</td>`).join('')}</tr>
        </tbody></table></div>
        <div class="flag ${cls}"><div><b>${r.title}</b><br>${r.text}</div></div>
        ${r.matches.map((m) => `<div class="flag bad"><div>找到线索：${m}</div></div>`).join('')}
        ${r.steps.length ? `<h3 style="font-size:15px;margin:16px 0 6px">建议的排查顺序</h3><ol class="story">${r.steps.map((s) => `<li>${s}</li>`).join('')}</ol>` : ''}
        <p class="xl-note">记住：永远不要用"调平项"强行配平。</p>`;
    };
    el.addEventListener('input', render);
    el.querySelector('#bl-clear').addEventListener('click', () => {
      el.querySelectorAll('input').forEach((i) => (i.value = ''));
      render();
    });
    render();
  };
})();
