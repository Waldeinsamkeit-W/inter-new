/* 分析方法选择器 */
(function () {
  const FM = window.FM;

  const Q = [
    {
      id: 'goal',
      q: '1. 你想回答什么问题？',
      opts: [
        ['value', '这家公司值多少钱？现在的股价贵不贵？'],
        ['ma', '收购这家公司（或它的控股权）应该出多少钱？'],
        ['lbo', '借大量资金收购它，几年后卖出能赚多少（私募视角）？'],
        ['project', '一个具体项目（建厂、开店、上新产品线）值不值得投？'],
        ['credit', '借给它的钱能不能按时收回？'],
        ['budget', '公司明年的经营计划和现金够不够用？'],
      ],
    },
    {
      id: 'type',
      q: '2. 这是一家什么样的公司？',
      opts: [
        ['mature', '成熟稳定：盈利，现金流比较稳定可预测'],
        ['growth', '高速成长，但已经盈利'],
        ['loss', '还在亏损，或者处于早期阶段'],
        ['cyclical', '强周期：利润随行业景气大起大落（钢铁、化工、航运、养殖…）'],
        ['fin', '银行、保险、券商等金融企业'],
        ['asset', '价值主要在资产：房地产、矿产资源、控股公司'],
      ],
    },
    {
      id: 'peers',
      q: '3. 能找到相似的上市公司或并购交易吗？',
      opts: [
        ['many', '能找到 5 家以上业务很相似的公司'],
        ['few', '只有 1–4 家，或者差异比较大'],
        ['none', '几乎找不到'],
      ],
    },
    {
      id: 'data',
      q: '4. 你手上的数据有多完整？',
      opts: [
        ['full', '有完整的三张报表，还有销量、门店等经营数据'],
        ['partial', '只有简单的财务数据（收入、利润等几个数）'],
      ],
    },
  ];

  const M = {
    dcf: { name: 'DCF 现金流折现', link: 'method-dcf', what: '用未来自由现金流折现得到内在价值。' },
    comps: { name: '可比公司法', link: 'method-comps', what: '用同类上市公司的估值倍数定价。' },
    prec: { name: '先例交易法', link: 'method-precedent', what: '用历史并购交易的倍数定价，包含控制权溢价。' },
    lbo: { name: 'LBO 杠杆收购模型', link: 'method-lbo', what: '计算借钱收购后的 IRR 和投资回报倍数。' },
    ddm: { name: 'DDM 股利折现 / P/B–ROE', link: 'method-ddm', what: '金融企业的股权口径估值方法。' },
    nav: { name: 'NAV 资产净值法', link: 'method-choose', what: '逐项评估资产的公允价值，减去负债。' },
    npv: { name: '项目 NPV / IRR', link: 'method-dcf', what: '只看这个项目新增的现金流，折现算净现值和内部收益率。' },
    credit: { name: '三表模型 + 偿债能力分析', link: 'build-review', what: '预测现金流，看净负债/EBITDA、利息保障倍数、现金缺口。' },
    budget: { name: '三表模型 + 情景分析', link: 'build-layout', what: '按月或按年预测三表，重点看现金。' },
  };

  function recommend(a) {
    const s = { dcf: 0, comps: 0, prec: 0, lbo: 0, ddm: 0, nav: 0, npv: 0, credit: 0, budget: 0 };
    const notes = {};
    const add = (k, v) => (s[k] += v);
    const note = (k, t) => (notes[k] = (notes[k] || []).concat(t));
    switch (a.goal) {
      case 'value': add('dcf', 3); add('comps', 3); break;
      case 'ma': add('prec', 3); add('dcf', 3); add('comps', 2); add('lbo', 1); note('lbo', '可以看财务投资者（私募）最多愿意出多少，作为报价下限的参考。'); break;
      case 'lbo': add('lbo', 6); add('comps', 1); add('dcf', 1); note('comps', '用来确定合理的入场和退出倍数。'); break;
      case 'project': add('npv', 6); note('npv', '只算"做这个项目"比"不做"多出来的现金流（增量现金流），沉没成本不算。'); break;
      case 'credit': add('credit', 6); note('credit', '重点做悲观情景：收入下滑 20% 时还能不能付利息？'); break;
      case 'budget': add('budget', 6); note('budget', '预算模型通常按月预测，重点关注现金最低点。'); break;
    }
    const valuing = ['value', 'ma', 'lbo'].includes(a.goal);
    switch (a.type) {
      case 'mature': add('dcf', 1); add('lbo', 1); break;
      case 'growth': add('dcf', 1); note('dcf', '预测期拉长到 7–10 年，让增速逐步回落到稳定水平后再算终值。'); note('comps', '可以用 PEG（P/E ÷ 增速）比较增速不同的公司。'); break;
      case 'loss':
        add('comps', 1); add('lbo', -4); add('ddm', -3);
        note('comps', '亏损公司 P/E 没有意义，用 EV/Sales（市销率）或行业专用指标（如每用户价值）。');
        note('dcf', '必须做多情景（成功 / 一般 / 失败），预测期要足够长，直到公司盈利稳定。');
        break;
      case 'cyclical':
        add('comps', 1);
        note('comps', '用周期中枢（多年平均）利润乘以 P/E，或者用 P/B；不要用景气高点的利润。');
        note('dcf', '收入和利润率要用一个完整周期的平均水平，而不是最近一年。');
        break;
      case 'fin':
        if (valuing) { add('ddm', 6); add('dcf', -6); add('lbo', -4); }
        note('comps', '用 P/B 和 P/E，<b>不要用 EV/EBITDA</b>：金融企业的负债是经营的一部分。');
        note('ddm', '核心公式：合理 P/B = (ROE − g) ÷ (Ke − g)。');
        break;
      case 'asset':
        if (valuing) add('nav', 4);
        note('nav', '对土地储备、矿产储量、持有的股权逐项估值，再减去负债。');
        note('comps', '常用 P/B、P/NAV（股价相对资产净值的折价率）。');
        break;
    }
    if (a.peers === 'none') { add('comps', -4); add('prec', -4); }
    if (a.peers === 'few') { add('comps', -1); add('prec', -1); note('comps', '可比公司太少时只作参考，并说明它们和目标公司的差异。'); }
    if (a.peers === 'many') { add('comps', 1); add('prec', 0.5); }
    if (a.data === 'partial') {
      add('dcf', -1); add('comps', 1); add('credit', -1);
      note('dcf', '数据不足时 DCF 只能做粗略版：用收入增长率和利润率，不做详细三表。');
    }
    const ranked = Object.keys(s)
      .filter((k) => s[k] > 0)
      .sort((x, y) => s[y] - s[x]);
    return { ranked, s, notes };
  }

  FM.widgets.selector = function (el) {
    const ans = { goal: 'value', type: 'mature', peers: 'many', data: 'full' };
    el.innerHTML = `<div class="tool"><div class="tool-grid" style="grid-template-columns:minmax(0,1fr) minmax(0,1fr)">
      <div id="sel-q">${Q.map(
        (q) => `<div class="q-block" role="radiogroup" aria-label="${q.q}"><h4>${q.q}</h4><div class="opt-list">${q.opts
          .map(
            ([v, t]) =>
              `<label class="opt${ans[q.id] === v ? ' sel' : ''}" for="sel-${q.id}-${v}"><input type="radio" name="sel-${q.id}" id="sel-${q.id}-${v}" value="${v}"${ans[q.id] === v ? ' checked' : ''}><span>${t}</span></label>`
          )
          .join('')}</div></div>`
      ).join('')}</div>
      <div id="sel-out" style="min-width:0"></div></div></div>`;
    const out = el.querySelector('#sel-out');
    const render = () => {
      const r = recommend(ans);
      const roles = ['主方法', '验证方法', '补充参考'];
      const items = r.ranked.slice(0, 3);
      let h = `<h3 style="margin-top:0">推荐结果</h3>`;
      items.forEach((k, i) => {
        const m = M[k];
        h += `<div class="rec"><h4><span class="pill p${i + 1}">${roles[i]}</span>${m.name}</h4><p>${m.what}</p>${(r.notes[k] || [])
          .map((t) => `<p>· ${t}</p>`)
          .join('')}<p><a href="#${m.link}">去学这个方法 →</a></p></div>`;
      });
      h += `<div class="rec"><h4><span class="pill p3">必做</span>敏感性分析与情景分析</h4><p>不管用哪种方法，都要看关键假设变化时结论会不会改变。</p><p><a href="#method-sens">去学 →</a></p></div>`;
      if (ans.type === 'fin' && ['value', 'ma', 'lbo'].includes(ans.goal))
        h += `<div class="flag warn">金融企业不适合用 FCFF、EV/EBITDA 和典型的 LBO 结构。</div>`;
      if (ans.peers === 'none' && ans.goal === 'value')
        h += `<div class="flag warn">没有可比公司时，DCF 是唯一的主方法，一定要做多情景并给出区间。</div>`;
      out.innerHTML = h;
    };
    el.querySelector('#sel-q').addEventListener('change', (e) => {
      const t = e.target;
      if (t.type !== 'radio') return;
      ans[t.name.replace('sel-', '')] = t.value;
      t.closest('.opt-list').querySelectorAll('.opt').forEach((o) => o.classList.toggle('sel', o.querySelector('input').checked));
      render();
    });
    render();
  };
})();
