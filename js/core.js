/* 核心：命名空间、章节、内容辅助函数 */
(function () {
  const FM = (window.FM = window.FM || {});
  FM.lessons = [];
  FM.widgets = {};

  FM.chapters = [
    { id: 'c0', no: '0', title: '开始之前', tab: '准备' },
    { id: 'c1', no: '1', title: '获取数据', tab: '原始数据' },
    { id: 'c2', no: '2', title: '处理数据', tab: '清洗' },
    { id: 'c3', no: '3', title: '分析历史', tab: '历史分析' },
    { id: 'c4', no: '4', title: '从零搭建三表模型', tab: '三表模型' },
    { id: 'c5', no: '5', title: '选择与搭建分析方法', tab: '估值' },
    { id: 'c6', no: '6', title: '实战案例：青禾饮品', tab: '实战' },
    { id: 'tools', no: 'T', title: '互动工具', tab: '工具' },
    { id: 'ref', no: 'R', title: '速查手册', tab: '速查' },
  ];

  FM.chapterDesc = {
    c0: '财务建模是什么、要准备什么工具、建模规范，以及用 10 分钟看懂三张报表怎么联动。',
    c1: '先想清楚要什么数据，再去巨潮、披露易、EDGAR 等网站下载，避开合并/母公司、单位、重述这些坑。',
    c2: '把下载来的"脏数据"变成模型能用的干净数据：转数字、统一单位、科目映射、勾稽校验。',
    c3: '算比率、找驱动因素，把历史数字变成"这家公司怎么赚钱"的故事，为假设打基础。',
    c4: '从空白 Excel 开始：骨架、假设、收入、成本、营运资本、固定资产、借款，最后让三张表配平。',
    c5: '根据问题选方法：DCF、可比公司、先例交易、DDM、LBO，以及敏感性分析和结论汇总。',
    c6: '用一家虚构饮料公司把全流程走一遍，配套模板、参考答案和逐步检查点。',
    tools: '方法选择器、DCF 计算器、三表联动模拟器、配平排错助手、LBO 回报计算器。',
    ref: 'Excel 常用函数、快捷键和中英文术语对照，随时查。',
  };

  FM.add = function (lesson) {
    FM.lessons.push(lesson);
  };

  /* ---------- 内容辅助函数 ---------- */
  const esc = (s) =>
    String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  FM.esc = esc;

  const BOX_TITLES = {
    goal: '本节目标',
    tip: '技巧',
    warn: '注意',
    think: '怎么想',
    eg: '举个例子',
    do: '动手做',
    key: '一句话记住',
  };

  /** 带"工作表标签"的提示框 */
  function box(type, html, title) {
    return `<div class="box box-${type}"><span class="box-t">${title || BOX_TITLES[type] || ''}</span>${html}</div>`;
  }

  /**
   * 迷你工作表。单元格写法：
   *   '=…' 公式（等宽字体）     '^…' 输入值（蓝色）
   *   '~…' 链接其他表（绿色）   '#…' 加粗标题
   *   '!…' 关键结果（黄色底）   '_…' 灰色说明
   *   数字或看起来像数字的字符串会右对齐
   */
  function sheet(spec) {
    const rows = spec.rows || [];
    const ncol = Math.max(...rows.map((r) => r.length));
    const c0 = (spec.c0 || 'A').charCodeAt(0);
    // 可以用 cols 指定真实列号（例如 ['A','B','E','F']），跳过的列像 Excel 隐藏列一样显示一条双线
    const letters = spec.cols || Array.from({ length: ncol }, (_, i) => String.fromCharCode(c0 + i));
    const gap = letters.map((l, i) => i > 0 && l.charCodeAt(0) - letters[i - 1].charCodeAt(0) > 1);
    const r0 = spec.r0 || 1;
    let h = `<figure class="xl-wrap">`;
    if (spec.title) h += `<figcaption class="xl-cap">${spec.title}</figcaption>`;
    if (spec.fx) {
      const parts = spec.fx.split('|');
      h += `<div class="xl-fx"><span class="xl-ref">${esc(parts[0].trim())}</span><span class="xl-fx-i">fx</span><code>${esc((parts[1] || '').trim())}</code></div>`;
    }
    h += `<div class="xl-scroll"><table class="xl"><thead><tr><th class="xl-corner"></th>`;
    for (let i = 0; i < ncol; i++) h += `<th${gap[i] ? ' class="gap"' : ''}>${letters[i]}</th>`;
    h += `</tr></thead><tbody>`;
    rows.forEach((r, ri) => {
      h += `<tr><th>${r0 + ri}</th>`;
      for (let i = 0; i < ncol; i++) {
        let v = r[i] === undefined || r[i] === null ? '' : String(r[i]);
        let cls = [];
        if (v.startsWith('=')) cls.push('f');
        else if (v.startsWith('^')) { cls.push('in'); v = v.slice(1); }
        else if (v.startsWith('~')) { cls.push('ln'); v = v.slice(1); }
        else if (v.startsWith('#')) { cls.push('hd'); v = v.slice(1); }
        else if (v.startsWith('!')) { cls.push('hl'); v = v.slice(1); }
        else if (v.startsWith('_')) { cls.push('mu'); v = v.slice(1); }
        if (/^[-−+(]?[¥$]?[\d,]*\.?\d+%?\)?[x天]?$/.test(v)) cls.push('num');
        if (gap[i]) cls.push('gap');
        h += `<td class="${cls.join(' ')}">${esc(v)}</td>`;
      }
      h += `</tr>`;
    });
    h += `</tbody></table></div>`;
    if (spec.note) h += `<p class="xl-note">${spec.note}</p>`;
    h += `</figure>`;
    return h;
  }

  /** 常见问题：[[现象, 原因, 解决], ...] */
  function trouble(items) {
    return (
      `<div class="trouble">` +
      items
        .map(
          ([sym, why, fix]) =>
            `<div class="tr-item"><p class="tr-sym">${sym}</p><p><span class="tr-l">原因</span>${why}</p><p><span class="tr-l tr-fix">解决</span>${fix}</p></div>`
        )
        .join('') +
      `</div>`
    );
  }

  /** 自检清单（勾选状态会保存在本机浏览器） */
  function checklist(items) {
    return `<ul class="check">${items.map((t) => `<li>${t}</li>`).join('')}</ul>`;
  }

  /** 小测验：[[问题, 答案], ...] */
  function quiz(items) {
    return (
      `<div class="quiz">` +
      items
        .map(
          ([q, a], i) =>
            `<details><summary><span class="q-no">Q${i + 1}</span>${q}</summary><div class="q-a">${a}</div></details>`
        )
        .join('') +
      `</div>`
    );
  }

  /** 公式块 */
  function xl(code, label) {
    return `<div class="code-wrap">${label ? `<span class="code-l">${label}</span>` : ''}<pre class="code"><code>${esc(code.trim())}</code></pre></div>`;
  }

  /** 普通表格：head 为表头数组，rows 为二维数组（可含 HTML） */
  function table(head, rows, opts) {
    const o = opts || {};
    return `<div class="tbl-scroll"><table class="tbl${o.cls ? ' ' + o.cls : ''}"><thead><tr>${head
      .map((h) => `<th>${h}</th>`)
      .join('')}</tr></thead><tbody>${rows
      .map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join('')}</tr>`)
      .join('')}</tbody></table></div>`;
  }

  /** 步骤：[[标题, 内容HTML], ...] */
  function steps(items) {
    return `<ol class="steps">${items
      .map(([t, b]) => `<li><h4>${t}</h4>${b}</li>`)
      .join('')}</ol>`;
  }

  /** 流程图（横向） */
  function flow(items) {
    return `<div class="flow">${items
      .map((t, i) => `<span class="flow-i">${t}</span>${i < items.length - 1 ? '<span class="flow-a" aria-hidden="true">→</span>' : ''}`)
      .join('')}</div>`;
  }

  FM.h = { box, sheet, trouble, checklist, quiz, xl, table, steps, flow, esc };

  /* ---------- 格式化 ---------- */
  FM.fmt = {
    num(v, d = 1) {
      if (v === null || v === undefined || isNaN(v)) return '–';
      const s = Math.abs(v).toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d });
      return v < 0 ? `(${s})` : s;
    },
    pct(v, d = 1) {
      if (v === null || v === undefined || isNaN(v)) return '–';
      return (v * 100).toFixed(d) + '%';
    },
    x(v, d = 1) {
      if (v === null || v === undefined || !isFinite(v)) return '–';
      return v.toFixed(d) + 'x';
    },
  };

  /* ---------- 本机存储（失败时静默降级） ---------- */
  FM.store = {
    get(k, d) {
      try {
        const v = localStorage.getItem('fm:' + k);
        return v === null ? d : JSON.parse(v);
      } catch (e) {
        return d;
      }
    },
    set(k, v) {
      try {
        localStorage.setItem('fm:' + k, JSON.stringify(v));
      } catch (e) {}
    },
  };

  /* ---------- 复制到剪贴板 ---------- */
  FM.copy = function (text, btn, fallbackEl) {
    const done = (ok) => {
      if (!btn) return;
      const old = btn.dataset.label || btn.textContent;
      btn.dataset.label = old;
      btn.textContent = ok ? '已复制' : '请手动选中复制';
      setTimeout(() => (btn.textContent = old), 1800);
    };
    try {
      navigator.clipboard.writeText(text).then(
        () => done(true),
        () => {
          if (fallbackEl) { fallbackEl.hidden = false; fallbackEl.select(); }
          done(false);
        }
      );
    } catch (e) {
      if (fallbackEl) { fallbackEl.hidden = false; fallbackEl.select(); }
      done(false);
    }
  };
})();
