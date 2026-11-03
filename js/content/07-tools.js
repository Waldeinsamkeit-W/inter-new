(function () {
  const { box, table } = FM.h;

  FM.add({
    id: 'tool-selector',
    ch: 'tools',
    num: 'T1',
    title: '分析方法选择器',
    lede: '回答 4 个问题，得到推荐的主方法、验证方法，以及每种方法要注意的地方。',
    wide: true,
    body: `<div data-widget="selector"></div>
${box('tip', `<p>推荐结果只是起点。最终选哪种方法，还要看你能拿到什么数据，以及读者（老板、客户、投资委员会）习惯看什么。详细的选择思路见 <a href="#method-choose">5.1 方法选择指南</a>。</p>`)}`,
  });

  FM.add({
    id: 'tool-dcf',
    ch: 'tools',
    num: 'T2',
    title: 'DCF 计算器',
    lede: '用青禾饮品的基准数据预填。改任何一个假设，自由现金流、企业价值、每股价值和敏感性表都会立刻更新，并提示不合理的地方。',
    wide: true,
    body: `<div data-widget="dcf"></div>
${box('think', `<p>试试这几个实验：</p>
<ol><li>把永续增长率从 2% 改成 4%，每股价值变了多少？终值占比变成多少？</li>
<li>把 WACC 改成 7%，再改成 9%，感受一下 DCF 对折现率有多敏感。</li>
<li>把资本开支占收入改成 3%，自由现金流大增——但如果资本开支长期低于折旧，公司还能保持增长吗？</li>
<li>打开"年中折现"，估值提高了多少？</li></ol>`)}`,
  });

  FM.add({
    id: 'tool-linkage',
    ch: 'tools',
    num: 'T3',
    title: '三表联动模拟器',
    lede: '选一个业务事件，看它如何同时影响利润表、现金流量表和资产负债表，以及为什么资产负债表依然平衡。',
    wide: true,
    body: `<div data-widget="linkage"></div>
${box('key', `<p>每个事件都按同一个顺序思考：<b>① 利润表变不变？② 现金实际进出了吗？③ 资产负债表哪些科目变了？④ 资产的变化 = 负债 + 权益的变化吗？</b>面试时遇到三表联动的问题，按这四步回答就不会乱。</p>`)}`,
  });

  FM.add({
    id: 'tool-balance',
    ch: 'tools',
    num: 'T4',
    title: '配平排错助手',
    lede: '输入资产负债表每年的差额（资产 − 负债和权益），助手根据差额的"形状"判断最可能的错误类型，并给出排查顺序。',
    wide: true,
    body: `<div data-widget="balance"></div>
${box('tip', `<p>如果你还知道每年主要科目的变动额，可以填在下面的"科目变动"里，助手会帮你找出差额刚好等于（或是两倍于）哪个科目的变动。方法原理见 <a href="#build-debug">4.11 系统排错法</a>。</p>`)}`,
  });

  FM.add({
    id: 'tool-lbo',
    ch: 'tools',
    num: 'T5',
    title: 'LBO 回报计算器',
    lede: '一个简化的杠杆收购模型：调整入场倍数、杠杆、增长和退出倍数，看 MOIC 和 IRR 怎么变，以及回报来自哪里。',
    wide: true,
    body: `<div data-widget="lbo"></div>
${box('think', `<p>试试：把杠杆从 4.0x 提高到 6.0x，IRR 上升了；再把 EBITDA 增长改成 −5%，看看高杠杆时回报下降得有多快。这就是"杠杆是双刃剑"。</p>`)}`,
  });
})();
