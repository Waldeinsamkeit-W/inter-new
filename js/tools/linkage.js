/* 三表联动模拟器 */
(function () {
  const FM = window.FM;

  // 每个事件：给出利润表和资产负债表中"非现金"科目的直接变化；现金和留存收益由规则推导
  const EVENTS = [
    {
      id: 'dep', name: '折旧增加 X', note: '面试最常考。折旧是费用但不花现金。',
      is: (x) => ({ da: x }), bs: (x) => ({ ppe: -x }), cf: (x) => ({ add_da: x }),
      story: (x, t) => [
        `利润表：折旧 +${x}，税前利润 −${x}，少交税 ${r(x * t)}，净利润 −${r(x * (1 - t))}。`,
        `现金流量表：净利润 −${r(x * (1 - t))}，但折旧不花现金要加回 +${x}，现金净增加 +${r(x * t)}（就是少交的税）。`,
        `资产负债表：固定资产 −${x}，现金 +${r(x * t)}，资产合计 −${r(x * (1 - t))}；留存收益 −${r(x * (1 - t))}。两边相等。`,
      ],
    },
    {
      id: 'credit_sale', name: '赊销收入 X（不考虑成本）', note: '有利润，但钱还没收到。',
      is: (x) => ({ rev: x }), bs: (x) => ({ ar: x }), cf: (x) => ({ d_ar: -x }),
      story: (x, t) => [
        `利润表：收入 +${x}，交税 ${r(x * t)}（假设税当年用现金付清），净利润 +${r(x * (1 - t))}。`,
        `现金流量表：净利润 +${r(x * (1 - t))}，但应收账款增加 ${x} 要减掉，现金净变化 −${r(x * t)}——赚了钱，现金反而少了（因为交了税却还没收到货款）。`,
        `资产负债表：应收账款 +${x}，现金 −${r(x * t)}，资产 +${r(x * (1 - t))}；留存收益 +${r(x * (1 - t))}。`,
      ],
    },
    {
      id: 'sell_inv', name: '卖出存货：售价 X，成本 0.6X，收现金', note: '最普通的一笔生意。',
      is: (x) => ({ rev: x, cogs: 0.6 * x }), bs: (x) => ({ inv: -0.6 * x }), cf: (x) => ({ d_inv: 0.6 * x }),
      story: (x, t) => [
        `利润表：收入 +${x}，营业成本 +${r(0.6 * x)}，毛利 ${r(0.4 * x)}，交税 ${r(0.4 * x * t)}，净利润 +${r(0.4 * x * (1 - t))}。`,
        `现金流量表：净利润 +${r(0.4 * x * (1 - t))}，存货减少 ${r(0.6 * x)} 加回，现金 +${r(x - 0.4 * x * t)}（收到 ${x}，付税 ${r(0.4 * x * t)}）。`,
        `资产负债表：存货 −${r(0.6 * x)}，现金 +${r(x - 0.4 * x * t)}，资产净增 ${r(0.4 * x * (1 - t))}；留存收益 +${r(0.4 * x * (1 - t))}。`,
      ],
    },
    {
      id: 'buy_inv_cash', name: '用现金采购存货 X', note: '利润表没变化，现金却少了。',
      bs: (x) => ({ inv: x }), cf: (x) => ({ d_inv: -x }),
      story: (x) => [
        '利润表：没有变化（货还没卖出去，不确认成本）。',
        `现金流量表：经营活动"存货增加"−${x}，现金 −${x}。`,
        `资产负债表：存货 +${x}，现金 −${x}，资产合计不变。`,
      ],
    },
    {
      id: 'buy_inv_credit', name: '赊购存货 X（欠供应商）', note: '供应商帮你垫钱。',
      bs: (x) => ({ inv: x, ap: x }), cf: (x) => ({ d_inv: -x, d_ap: x }),
      story: (x) => [
        '利润表：没有变化。',
        `现金流量表：存货增加 −${x}，应付账款增加 +${x}，现金不变。`,
        `资产负债表：存货 +${x}（资产），应付账款 +${x}（负债），两边同时增加。`,
      ],
    },
    {
      id: 'capex', name: '用现金购买设备 X', note: '大额现金流出，但当年不进利润表。',
      bs: (x) => ({ ppe: x }), cf: (x) => ({ capex: -x }),
      story: (x) => [
        '利润表：当下没有变化（以后每年通过折旧慢慢进入利润表）。',
        `现金流量表：投资活动"资本开支"−${x}。`,
        `资产负债表：固定资产 +${x}，现金 −${x}，资产合计不变。`,
      ],
    },
    {
      id: 'borrow', name: '从银行借款 X', note: '',
      bs: (x) => ({ debt: x }), cf: (x) => ({ d_debt: x }),
      story: (x) => [
        '利润表：借款当下没有变化（以后产生利息）。',
        `现金流量表：筹资活动"借款"+${x}。`,
        `资产负债表：现金 +${x}，借款 +${x}。`,
      ],
    },
    {
      id: 'repay', name: '偿还借款本金 X', note: '还本金不是费用。',
      bs: (x) => ({ debt: -x }), cf: (x) => ({ d_debt: -x }),
      story: (x) => [
        '利润表：没有变化。本金不是费用，只有利息才是。',
        `现金流量表：筹资活动 −${x}。`,
        `资产负债表：现金 −${x}，借款 −${x}。`,
      ],
    },
    {
      id: 'interest', name: '支付利息 X', note: '利息可以抵税。',
      is: (x) => ({ int: x }), bs: () => ({}), cf: () => ({}),
      story: (x, t) => [
        `利润表：利息费用 +${x}，少交税 ${r(x * t)}，净利润 −${r(x * (1 - t))}。`,
        `现金流量表（间接法）：净利润 −${r(x * (1 - t))} 已经包含了利息和税的影响，现金 −${r(x * (1 - t))}。中国准则下利息支出列在筹资活动，但总的现金变化一样。`,
        `资产负债表：现金 −${r(x * (1 - t))}，留存收益 −${r(x * (1 - t))}。`,
      ],
    },
    {
      id: 'equity', name: '发行新股 X', note: '',
      bs: (x) => ({ paidin: x }), cf: (x) => ({ d_eq: x }),
      story: (x) => [
        '利润表：没有变化。',
        `现金流量表：筹资活动"发行股票"+${x}。`,
        `资产负债表：现金 +${x}，实收资本 +${x}。`,
      ],
    },
    {
      id: 'dividend', name: '支付现金股利 X', note: '分红不是费用。',
      bs: () => ({}), cf: (x) => ({ div: -x }), re: (x) => -x,
      story: (x) => [
        '利润表：没有变化。分红是利润的分配，不是费用。',
        `现金流量表：筹资活动"支付股利"−${x}。`,
        `资产负债表：现金 −${x}，留存收益 −${x}。`,
      ],
    },
    {
      id: 'prepay', name: '收到客户预付款 X（还没发货）', note: '先收钱，后确认收入。',
      bs: (x) => ({ defrev: x }), cf: (x) => ({ d_def: x }),
      story: (x) => [
        '利润表：没有变化（还没发货，不能确认收入）。',
        `现金流量表：经营活动"合同负债增加"+${x}。`,
        `资产负债表：现金 +${x}，合同负债（预收款）+${x}——欠客户一批货。`,
      ],
    },
    {
      id: 'impair', name: '存货减值 X', note: '非现金费用，和折旧类似。',
      is: (x) => ({ opex: x }), bs: (x) => ({ inv: -x }), cf: (x) => ({ add_imp: x }),
      story: (x, t) => [
        `利润表：资产减值损失 +${x}，净利润 −${r(x * (1 - t))}（这里为了简单，假设减值可以抵税；实际税法上通常要等实际损失才能扣除，会形成递延所得税资产）。`,
        `现金流量表：减值不花现金，加回 +${x}，现金 +${r(x * t)}。`,
        `资产负债表：存货 −${x}，现金 +${r(x * t)}，留存收益 −${r(x * (1 - t))}。`,
      ],
    },
  ];

  function r(v) {
    return Math.round(v * 100) / 100;
  }

  function run(ev, x, t) {
    const is = Object.assign({ rev: 0, cogs: 0, opex: 0, da: 0, int: 0 }, ev.is ? ev.is(x) : {});
    is.pretax = is.rev - is.cogs - is.opex - is.da - is.int;
    is.tax = is.pretax * t;
    is.ni = is.pretax - is.tax;
    const cf0 = Object.assign({ add_da: 0, add_imp: 0, d_ar: 0, d_inv: 0, d_ap: 0, d_def: 0, capex: 0, d_debt: 0, d_eq: 0, div: 0 }, ev.cf ? ev.cf(x) : {});
    const cf = Object.assign({ ni: is.ni }, cf0);
    cf.cfo = cf.ni + cf.add_da + cf.add_imp + cf.d_ar + cf.d_inv + cf.d_ap + cf.d_def;
    cf.cfi = cf.capex;
    cf.cff = cf.d_debt + cf.d_eq + cf.div;
    cf.net = cf.cfo + cf.cfi + cf.cff;
    const bs = Object.assign({ ar: 0, inv: 0, ppe: 0, ap: 0, defrev: 0, debt: 0, paidin: 0 }, ev.bs ? ev.bs(x) : {});
    bs.cash = cf.net;
    bs.ta = bs.cash + bs.ar + bs.inv + bs.ppe;
    bs.tl = bs.ap + bs.defrev + bs.debt;
    bs.re = is.ni + (ev.re ? ev.re(x) : 0);
    bs.te = bs.paidin + bs.re;
    bs.tle = bs.tl + bs.te;
    return { is, cf, bs };
  }

  function rowsHtml(list, data) {
    return list
      .map(([k, label, tot]) => {
        const v = data[k];
        const z = Math.abs(v) < 1e-9;
        const cls = [tot ? 't' : '', z ? 'z' : v > 0 ? 'pos' : 'neg'].join(' ');
        return `<tr class="${cls}"><td>${label}</td><td>${z ? '—' : (v > 0 ? '+' : '−') + Math.abs(r(v)).toLocaleString('zh-CN')}</td></tr>`;
      })
      .join('');
  }

  FM.widgets.linkage = function (el) {
    let cur = EVENTS[0];
    el.innerHTML = `<div class="tool">
      <div class="tool-grid">
        <div class="fields">
          <div class="field"><label for="lk-x">金额 X</label><input id="lk-x" type="number" value="100" step="10"></div>
          <div class="field"><label for="lk-t">所得税率 %</label><input id="lk-t" type="number" value="25" step="1"></div>
          <fieldset class="fgroup"><legend>选择一个业务事件</legend>
          <div class="opt-list" id="lk-ev">${EVENTS.map(
            (e, i) =>
              `<label class="opt${i === 0 ? ' sel' : ''}" for="lk-${e.id}"><input type="radio" name="lk-ev" id="lk-${e.id}" value="${e.id}"${i === 0 ? ' checked' : ''}><span>${e.name}${e.note ? `<br><small style="color:var(--ink-3)">${e.note}</small>` : ''}</span></label>`
          ).join('')}</div></fieldset>
        </div>
        <div id="lk-out" style="min-width:0"></div>
      </div></div>`;
    const out = el.querySelector('#lk-out');
    const render = () => {
      const x = parseFloat(el.querySelector('#lk-x').value) || 0;
      const t = (parseFloat(el.querySelector('#lk-t').value) || 0) / 100;
      const d = run(cur, x, t);
      const ok = Math.abs(d.bs.ta - d.bs.tle) < 1e-6;
      out.innerHTML = `
        <h3 style="margin-top:0">${cur.name.replace('X', x)}</h3>
        <div class="stmt3">
          <div class="stmt"><h4>利润表</h4><table>${rowsHtml(
            [['rev', '营业收入'], ['cogs', '营业成本'], ['opex', '减值等费用'], ['da', '折旧'], ['int', '利息费用'], ['pretax', '税前利润', 1], ['tax', '所得税'], ['ni', '净利润', 1]],
            d.is
          )}</table></div>
          <div class="stmt"><h4>现金流量表</h4><table>${rowsHtml(
            [['ni', '净利润'], ['add_da', '加：折旧'], ['add_imp', '加：减值'], ['d_ar', '应收账款变动'], ['d_inv', '存货变动'], ['d_ap', '应付账款变动'], ['d_def', '合同负债变动'], ['cfo', '经营活动', 1], ['capex', '资本开支'], ['cfi', '投资活动', 1], ['d_debt', '借款'], ['d_eq', '发行股票'], ['div', '支付股利'], ['cff', '筹资活动', 1], ['net', '现金净增加', 1]],
            d.cf
          )}</table></div>
          <div class="stmt"><h4>资产负债表</h4><table>${rowsHtml(
            [['cash', '现金'], ['ar', '应收账款'], ['inv', '存货'], ['ppe', '固定资产'], ['ta', '资产合计', 1], ['ap', '应付账款'], ['defrev', '合同负债'], ['debt', '借款'], ['tl', '负债合计', 1], ['paidin', '实收资本'], ['re', '留存收益'], ['te', '所有者权益', 1], ['tle', '负债和权益', 1]],
            d.bs
          )}</table></div>
        </div>
        <div class="flag ${ok ? 'ok' : 'bad'}">${ok ? `✓ 资产变化 ${r(d.bs.ta)} = 负债和权益变化 ${r(d.bs.tle)}，资产负债表依然平衡。` : '不平衡'}</div>
        <h3 style="font-size:15px;margin:16px 0 6px">一步一步看</h3>
        <ol class="story">${cur.story(x, t).map((s) => `<li>${s}</li>`).join('')}</ol>
        <p class="xl-note">简化假设：所得税当期用现金付清；现金流量表用间接法。</p>`;
    };
    el.querySelector('#lk-ev').addEventListener('change', (e) => {
      cur = EVENTS.find((x) => x.id === e.target.value);
      el.querySelectorAll('#lk-ev .opt').forEach((o) => o.classList.toggle('sel', o.querySelector('input').checked));
      render();
    });
    el.querySelector('#lk-x').addEventListener('input', render);
    el.querySelector('#lk-t').addEventListener('input', render);
    render();
  };
})();
