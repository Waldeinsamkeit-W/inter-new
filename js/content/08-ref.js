(function () {
  const { box, table, xl, checklist } = FM.h;

  FM.add({
    id: 'ref-functions',
    ch: 'ref',
    num: 'R1',
    title: '建模常用 Excel 函数',
    lede: '按用途分组，每个函数给出一个建模中真实会用到的例子和容易出错的地方。',
    wide: true,
    body: `
<h2>查找与汇总</h2>
${table(
  ['函数', '用途', '例子', '注意'],
  [
    ['<code>SUMIFS</code>', '按条件求和', '<code class="wrap">=SUMIFS(原始!D:D, 原始!$G:$G, $A5)</code>', '多对一合并科目的核心函数；条件区域和求和区域要一样大'],
    ['<code>INDEX</code> + <code>MATCH</code>', '按名称查找', '<code class="wrap">=INDEX($B:$B, MATCH(A5, $A:$A, 0))</code>', 'MATCH 最后一个参数写 0（精确匹配）'],
    ['<code>XLOOKUP</code>', '新版查找（365/2021）', '<code class="wrap">=XLOOKUP(A5, 映射!A:A, 映射!B:B, "未映射")</code>', '老版本 Excel 和部分 WPS 没有'],
    ['<code>VLOOKUP</code>', '老式查找', '<code class="wrap">=VLOOKUP(A5, 映射!$A:$B, 2, FALSE)</code>', '一定要写 FALSE；插入列后列号会错'],
    ['<code>SUMPRODUCT</code>', '对应相乘再求和', '<code class="wrap">=SUMPRODUCT(G27:K27, G29:K29)</code>', '一行算出现值合计；也能做带条件的加权求和'],
  ]
)}

<h2>逻辑与容错</h2>
${table(
  ['函数', '用途', '例子', '注意'],
  [
    ['<code>IF</code>', '条件判断', '<code class="wrap">=IF(G28<0, 0, G28*G30)</code>', '嵌套不要超过 2–3 层，太长就拆开'],
    ['<code>IFERROR</code>', '出错时显示替代值', '<code class="wrap">=IFERROR(G10/F10-1, "")</code>', '<b>只用在确实可能出错的地方</b>，否则会把真正的错误藏起来'],
    ['<code>MIN</code> / <code>MAX</code>', '取较小 / 较大值', '<code class="wrap">=MIN(计划还款, 期初借款)</code><br><code class="wrap">=MAX(0, 税前利润×税率)</code>', '建模里最常用的"保护"写法'],
    ['<code>AND</code> / <code>OR</code>', '多个条件', '<code class="wrap">=AND(G96:K96)</code>', '检查区汇总'],
    ['<code>CHOOSE</code>', '按序号选择', '<code class="wrap">=CHOOSE($C$2, G7, G8, G9)</code>', '情景切换'],
    ['<code>ABS</code>', '绝对值', '<code class="wrap">=ABS(G76)<0.001</code>', '平衡检查要用容差'],
  ]
)}

<h2>财务函数</h2>
${table(
  ['函数', '用途', '例子', '注意'],
  [
    ['<code>NPV</code>', '净现值', '<code class="wrap">=NPV(WACC, G27:K27)</code>', '第一笔现金流默认在第 1 期末；<b>不要把第 0 期放进去</b>'],
    ['<code>XNPV</code>', '按具体日期折现', '<code class="wrap">=XNPV(WACC, 现金流, 日期)</code>', '第一笔现金流必须是第 0 期（日期最早）'],
    ['<code>IRR</code>', '内部收益率', '<code class="wrap">=IRR(B5:G5)</code>', '现金流第一笔通常是负数（投入）'],
    ['<code>XIRR</code>', '按具体日期的 IRR', '<code class="wrap">=XIRR(现金流, 日期)</code>', 'LBO、项目投资常用'],
    ['<code>PMT</code>', '等额还款额', '<code class="wrap">=PMT(5%, 10, -1000)</code>', '按揭、融资租赁'],
  ]
)}

<h2>文本清洗</h2>
${table(
  ['函数', '用途', '例子'],
  [
    ['<code>TRIM</code>', '去掉首尾和多余空格', '<code class="wrap">=TRIM(A5)</code>'],
    ['<code>CLEAN</code>', '去掉换行等不可见字符', '<code class="wrap">=CLEAN(A5)</code>'],
    ['<code>SUBSTITUTE</code>', '替换字符', '<code class="wrap">=SUBSTITUTE(B5, ",", "")</code>'],
    ['<code>VALUE</code>', '文本转数字', '<code class="wrap">=VALUE(SUBSTITUTE(B5, ",", ""))</code>'],
    ['<code>LEFT</code> / <code>MID</code> / <code>LEN</code>', '截取文本', '<code class="wrap">=LEFT(TRIM(B5),1)="("</code>'],
    ['<code>TEXT</code>', '数字转为指定格式的文本', '<code class="wrap">=TEXT(G41, "0.00")&"元"</code>'],
  ]
)}

<h2>日期</h2>
${table(
  ['函数', '用途', '例子'],
  [
    ['<code>EOMONTH</code>', '某月最后一天', '<code class="wrap">=EOMONTH(D3, 12)</code>：一年后的月末'],
    ['<code>EDATE</code>', '加减月份', '<code class="wrap">=EDATE(D3, 3)</code>'],
    ['<code>YEARFRAC</code>', '两个日期之间相差多少年', '<code class="wrap">=YEARFRAC(估值日, 现金流日期)</code>：计算折现期数'],
    ['<code>YEAR</code>', '取年份', '<code class="wrap">=YEAR(C4)</code>'],
  ]
)}

${box('warn', `<p><b>尽量不用的函数</b>：<code>OFFSET</code>、<code>INDIRECT</code>、<code>TODAY</code>、<code>NOW</code>。它们是"易失性函数"，每次任何单元格变化都会重算，让大模型变慢；而且 OFFSET/INDIRECT 的引用关系追踪不到，别人很难检查。</p>`)}

<h2>模拟分析工具</h2>
${table(
  ['工具', '位置', '用途'],
  [
    ['模拟运算表', '数据 → 模拟分析 → 模拟运算表', '敏感性分析（单变量 / 双变量）'],
    ['单变量求解', '数据 → 模拟分析 → 单变量求解', '反向求解：股价隐含的增长率、IRR 达到 20% 的最高出价'],
    ['方案管理器', '数据 → 模拟分析 → 方案管理器', '保存多组假设（一般用情景开关更直观）'],
  ]
)}

<h2>快捷键</h2>
<p>完整列表见 <a href="#setup">0.2 准备工具与建模规范</a>。最重要的 5 个：<kbd>F2</kbd> 编辑、<kbd>F4</kbd> 切换 $、<kbd>Ctrl</kbd>+<kbd>R</kbd> 向右填充、<kbd>Ctrl</kbd>+<kbd>[</kbd> 跳到引用源、<kbd>Ctrl</kbd>+<kbd>\`</kbd> 显示公式。</p>
`,
  });

  FM.add({
    id: 'ref-glossary',
    ch: 'ref',
    num: 'R2',
    title: '术语表（中英对照）',
    lede: '财务建模和估值中最常见的术语。英文缩写在研报和面试中经常直接使用，值得记住。',
    wide: true,
    body: `<div data-widget="glossary"></div>`,
  });

  FM.add({
    id: 'ref-checklist',
    ch: 'ref',
    num: 'R3',
    title: '交付前总检查清单',
    lede: '把模型交给老板、客户或者面试官之前，从头到尾过一遍。',
    body: `
<h2>数据</h2>
${checklist([
  '用的是合并报表，单位、币种统一',
  '原始数据有来源记录（网站、文件、页码、日期）',
  '历史数据全部用公式从原始数据取数',
  '历史期资产负债表平衡，利润表和现金流校验通过',
  '一次性项目已识别并在预测中剔除',
])}
<h2>结构与规范</h2>
${checklist([
  '所有工作表的同一列是同一年',
  '蓝色输入、黑色公式、绿色链接',
  '公式里没有写死的数字（365、100 等常数除外）',
  '每个假设只输入一次，模型只引用假设页的"使用中"行',
  '预测期每一行公式一致（Ctrl+` 检查过）',
  '没有合并单元格、隐藏行，没有意外的循环引用',
])}
<h2>三表</h2>
${checklist([
  '预测期资产负债表每年平衡（不是靠调平项）',
  '现金流量表期末现金 = 资产负债表货币资金',
  '折旧在利润表、现金流量表、固定资产表三处一致',
  '留存收益 = 上年 + 净利润 − 股利',
  '现金、借款、固定资产不为负（或有意为之并说明）',
])}
<h2>估值与分析</h2>
${checklist([
  '方法适合公司类型，至少两种方法交叉验证',
  'FCFF 的税用 EBIT × 税率；营运资本增加是减项',
  'g &lt; WACC，终值占比合理，检查了隐含倍数',
  '企业价值到股权价值的调整项齐全',
  '做了敏感性分析和情景分析，基准值与主结果一致',
  '做了压力测试，模型没有崩溃',
])}
<h2>呈现</h2>
${checklist([
  '说明页写清了目的、版本、日期、关键假设、使用方法',
  '结论先行，给出区间，写清关键假设和风险',
  '结论里的每个数字都能在模型里找到出处',
  '文件名带版本号和日期',
])}
`,
  });
})();
