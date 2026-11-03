/* 应用：导航、路由、进度、搜索、首页 */
(function () {
  const FM = window.FM;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = FM.esc;

  const lessons = FM.lessons;
  const byId = Object.fromEntries(lessons.map((l) => [l.id, l]));
  const chOf = Object.fromEntries(FM.chapters.map((c) => [c.id, c]));
  const order = FM.chapters.flatMap((c) => lessons.filter((l) => l.ch === c.id));
  const countable = order.filter((l) => l.ch !== 'tools' && l.ch !== 'ref');

  let done = new Set(FM.store.get('done', []));
  const saveDone = () => FM.store.set('done', Array.from(done));

  /* ---------- 主题 ---------- */
  const themes = ['system', 'light', 'dark'];
  const themeLabel = { system: '主题：跟随系统', light: '主题：浅色', dark: '主题：深色' };
  function applyTheme(t) {
    if (t === 'system') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', t);
    const b = $('#themeBtn');
    if (b) b.textContent = themeLabel[t];
  }
  let theme = FM.store.get('theme', 'system');
  if (!themes.includes(theme)) theme = 'system';

  /* ---------- 侧边栏 ---------- */
  const closed = new Set(FM.store.get('closed', []));
  function renderNav(current) {
    const nav = $('#nav');
    nav.innerHTML = FM.chapters
      .map((c) => {
        const ls = lessons.filter((l) => l.ch === c.id);
        if (!ls.length) return '';
        const n = ls.filter((l) => done.has(l.id)).length;
        const showCnt = c.id !== 'tools' && c.id !== 'ref';
        const isClosed = closed.has(c.id) && !ls.some((l) => l.id === current);
        return `<div class="nav-ch${isClosed ? ' closed' : ''}" data-ch="${c.id}">
          <button type="button" aria-expanded="${!isClosed}"><span class="nav-no">${c.no}</span><span>${c.title}</span>${
          showCnt ? `<span class="nav-cnt">${n}/${ls.length}</span>` : ''
        }</button>
          <ul class="nav-list">${ls
            .map(
              (l) =>
                `<li><a href="#${l.id}" class="${l.id === current ? 'on' : ''} ${done.has(l.id) ? 'done' : ''}">${
                  showCnt ? '<span class="dot" aria-hidden="true"></span>' : '<span class="dot" aria-hidden="true" style="border-style:dashed"></span>'
                }<span>${l.title}</span></a></li>`
            )
            .join('')}</ul></div>`;
      })
      .join('');
    $$('.nav-ch > button', nav).forEach((b) =>
      b.addEventListener('click', () => {
        const box = b.parentElement;
        box.classList.toggle('closed');
        const id = box.dataset.ch;
        if (box.classList.contains('closed')) closed.add(id);
        else closed.delete(id);
        b.setAttribute('aria-expanded', !box.classList.contains('closed'));
        FM.store.set('closed', Array.from(closed));
      })
    );
    const n = countable.filter((l) => done.has(l.id)).length;
    $('#progTxt').textContent = `${n} / ${countable.length} 节`;
    $('#progPct').textContent = Math.round((n / countable.length) * 100) + '%';
    $('#progBar').style.width = (n / countable.length) * 100 + '%';
  }

  /* ---------- 搜索 ---------- */
  let index = null;
  function buildIndex() {
    const tmp = document.createElement('div');
    index = lessons.map((l) => {
      tmp.innerHTML = (l.body || '') + ' ' + (l.lede || '');
      return { l, text: (l.title + ' ' + tmp.textContent).replace(/\s+/g, ' ') };
    });
  }
  function doSearch(q) {
    const res = $('#searchRes');
    const nav = $('#nav');
    q = q.trim();
    if (!q) {
      res.hidden = true;
      nav.hidden = false;
      return;
    }
    if (!index) buildIndex();
    const ql = q.toLowerCase();
    const hits = index
      .map(({ l, text }) => {
        const i = text.toLowerCase().indexOf(ql);
        if (i < 0) return null;
        const inTitle = l.title.toLowerCase().includes(ql);
        const s = Math.max(0, i - 18);
        const snip = text.slice(s, i + q.length + 40);
        return { l, inTitle, snip };
      })
      .filter(Boolean)
      .sort((a, b) => b.inTitle - a.inTitle)
      .slice(0, 30);
    nav.hidden = true;
    res.hidden = false;
    if (!hits.length) {
      res.innerHTML = `<p class="search-empty">没有找到"${esc(q)}"。试试更短的词，比如"折旧""WACC""不平"。</p>`;
      return;
    }
    const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig');
    res.innerHTML = `<ul class="search-res">${hits
      .map(
        (h) =>
          `<li><a href="#${h.l.id}">${esc(h.l.title)}<small>…${esc(h.snip).replace(re, (m) => `<mark>${m}</mark>`)}…</small></a></li>`
      )
      .join('')}</ul>`;
  }

  /* ---------- 首页 ---------- */
  function renderHome() {
    const C = window.FM_CASE;
    const first = order[0];
    const resume = order.find((l) => !done.has(l.id) && l.ch !== 'tools' && l.ch !== 'ref') || first;
    const started = done.size > 0;
    const tabs = FM.chapters
      .filter((c) => c.id !== 'tools' && c.id !== 'ref')
      .map((c, i) => {
        const l0 = lessons.find((l) => l.ch === c.id);
        return `<a href="#${l0.id}" class="${i === 4 ? 'on' : ''}"><small>${c.no}</small>${c.tab}</a>`;
      })
      .join('');
    const v = C ? C.scen['1'].val : null;
    const mini = C
      ? FM.h.sheet({
          rows: [
            ['#青禾饮品（虚构）', '#单位', '#2025A', '#2026E', '#2027E'],
            ['销量增长率', '%', '11.1%', '^9.0%', '^8.0%'],
            ['营业收入', '百万元', '2,600.0', '=F6*G8/100', '=G6*H8/100'],
            ['EBITDA', '百万元', FM.fmt.num(C.scen['1'].lines.ebitda['2025']), FM.fmt.num(C.scen['1'].lines.ebitda['2026']), FM.fmt.num(C.scen['1'].lines.ebitda['2027'])],
            ['平衡检查', '百万元', '0.0', '0.0', '0.0'],
            ['每股价值（DCF）', '元/股', '', '!' + v.per_share.toFixed(2), ''],
          ],
          r0: 9,
        })
      : '';
    const chCards = FM.chapters
      .map((c) => {
        const ls = lessons.filter((l) => l.ch === c.id);
        if (!ls.length) return '';
        const n = ls.filter((l) => done.has(l.id)).length;
        const desc = FM.chapterDesc[c.id] || '';
        const showP = c.id !== 'tools' && c.id !== 'ref';
        return `<a class="ch-card" href="#${ls[0].id}">
          <div class="ch-top"><span class="ch-no">${c.id === 'tools' ? '工具' : c.id === 'ref' ? '速查' : '第 ' + c.no + ' 章'}</span><h3>${c.title}</h3></div>
          <p>${desc}</p>
          <div class="ch-foot">${
            showP
              ? `<span>${ls.length} 节</span><span class="prog-bar"><i style="width:${(n / ls.length) * 100}%"></i></span><span>${n}/${ls.length}</span>`
              : `<span>${ls.map((l) => l.title).join(' · ')}</span>`
          }</div></a>`;
      })
      .join('');
    return `<div class="page wide"><section class="hero">
      <div class="crumb"><span class="tag">财务建模实操课</span><span>免费 · 中文 · 配套 Excel 练习</span></div>
      <h1>财务建模，<br>从<em>下载第一张报表</em>开始</h1>
      <p class="lede">一步一步教你：去哪下载数据、怎么清洗、怎么从空白 Excel 搭出三张报表，再根据问题选对分析方法、算出估值。每一步都写清楚要注意什么、会出什么错、该怎么想。</p>
      <div class="hero-cta">
        <a class="btn" href="#${resume.id}">${started ? '继续学习：' + esc(resume.title) : '从第一节开始'}</a>
        <a class="btn sec" href="#case">直接看实战案例</a>
      </div>
      <div class="wb" aria-label="课程结构示意">
        <div class="wb-fx"><span>G8</span><span><i>fx</i></span><code>=F8*(1+假设!G11)</code></div>
        <div class="wb-body">${mini.replace('xl-wrap', 'xl-wrap" style="margin:0').replace('class="xl-scroll"', 'class="xl-scroll" style="border:0;border-radius:0"')}</div>
        <nav class="wb-tabs" aria-label="章节">${tabs}</nav>
      </div>
      <p class="xl-note">上图就是课程的结构：每一章是工作簿里的一张工作表，按从左到右的顺序完成，最后得到一个能算出每股价值的完整模型。</p>
    </section>

    <h2 class="sec-h">每一节都按同一个结构写</h2>
    <p class="sec-sub">看完一节，你应该能马上在 Excel 里做出来。</p>
    <div class="how">
      <div><b style="color:var(--accent)">本节目标</b><p>学完能做出什么，先知道终点在哪。</p></div>
      <div><b style="color:var(--think)">怎么想</b><p>为什么这样做、遇到选择时怎么判断。</p></div>
      <div><b style="color:var(--ink)">操作步骤</b><p>按顺序编号，附带可以照抄的 Excel 公式。</p></div>
      <div><b style="color:var(--warn)">注意</b><p>最容易忽略、做错就会出大问题的地方。</p></div>
      <div><b style="color:var(--bad)">常见问题</b><p>现象 → 原因 → 解决，卡住时来这里查。</p></div>
      <div><b style="color:var(--good)">自检清单</b><p>逐条打勾，确认这一步真的做对了。</p></div>
    </div>

    <h2 class="sec-h">学习路线</h2>
    <p class="sec-sub">建议按顺序学。全部学完并完成实战案例，大约需要 12–15 小时。</p>
    <div class="ch-grid">${chCards}</div>

    <h2 class="sec-h">配套练习：青禾饮品（虚构公司）</h2>
    <p class="sec-sub">一家虚构的饮料公司，3 年历史数据 + 5 年预测。从一份"脏"的原始数据开始，一路做到 DCF 估值。所有检查点数字都给出，做完可以逐项核对。</p>
    <div class="copy-row"><a class="btn" href="#case">打开实战案例</a><a class="btn sec" href="practice/青禾饮品_练习模板.xlsx" download>下载练习模板</a><a class="btn sec" href="practice/青禾饮品_参考答案.xlsx" download>下载参考答案</a></div>
    </div>`;
  }

  /* ---------- 课程页 ---------- */
  function renderLesson(l) {
    const c = chOf[l.ch];
    const i = order.indexOf(l);
    const prev = order[i - 1];
    const next = order[i + 1];
    const isTool = l.ch === 'tools' || l.ch === 'ref';
    const chLabel = l.ch === 'tools' ? '互动工具' : l.ch === 'ref' ? '速查手册' : `第 ${c.no} 章 · ${c.title}`;
    const isDone = done.has(l.id);
    return `<article class="page${l.wide ? ' wide' : ''}">
      <div class="crumb"><span class="tag">${l.num || c.no}</span><span>${chLabel}</span></div>
      <h1>${l.title}</h1>
      ${l.lede ? `<p class="lede">${l.lede}</p>` : ''}
      <div class="meta">${l.time ? `<span>阅读 + 动手约 ${l.time}</span>` : ''}${l.level ? `<span>难度：${l.level}</span>` : ''}</div>
      <div class="body">${l.body || ''}</div>
      ${
        isTool
          ? ''
          : `<div class="done-bar"><p>${isDone ? '这一节已完成。' : '做完自检清单后，标记为完成，进度会保存在这台设备的浏览器里。'}</p>
        <button type="button" class="btn${isDone ? ' is-done' : ''}" id="doneBtn">${isDone ? '✓ 已完成' : '标记为已完成'}</button></div>`
      }
      <nav class="pager" aria-label="上一节和下一节">
        ${prev ? `<a href="#${prev.id}" class="prev"><small>上一节</small>${prev.title}</a>` : '<span></span>'}
        ${next ? `<a href="#${next.id}" class="next"><small>下一节</small>${next.title}</a>` : ''}
      </nav>
    </article>`;
  }

  function wireLesson(l) {
    // 自检清单
    $$('.check', $('#view')).forEach((ul, ui) => {
      $$('li', ul).forEach((li, k) => {
        const key = `chk:${l.id}:${ui}:${k}`;
        const id = `c-${l.id}-${ui}-${k}`;
        const html = li.innerHTML;
        li.innerHTML = `<label for="${id}"><input type="checkbox" id="${id}"><span>${html}</span></label>`;
        const cb = $('input', li);
        cb.checked = !!FM.store.get(key, false);
        cb.addEventListener('change', () => FM.store.set(key, cb.checked));
      });
    });
    const b = $('#doneBtn');
    if (b)
      b.addEventListener('click', () => {
        if (done.has(l.id)) done.delete(l.id);
        else done.add(l.id);
        saveDone();
        const isDone = done.has(l.id);
        b.classList.toggle('is-done', isDone);
        b.textContent = isDone ? '✓ 已完成' : '标记为已完成';
        b.previousElementSibling.textContent = isDone ? '这一节已完成。' : '做完自检清单后，标记为完成，进度会保存在这台设备的浏览器里。';
        renderNav(l.id);
      });
    // 小组件
    $$('[data-widget]', $('#view')).forEach((el) => {
      const w = FM.widgets[el.dataset.widget];
      if (w) {
        try {
          w(el, el.dataset);
        } catch (e) {
          el.innerHTML = `<p class="flag bad">这个互动组件加载失败：${esc(e.message)}</p>`;
          console.error(e);
        }
      }
    });
  }

  /* ---------- 路由 ---------- */
  function route() {
    const id = decodeURIComponent(location.hash.slice(1));
    const l = byId[id];
    const view = $('#view');
    if (l) {
      view.innerHTML = renderLesson(l);
      document.title = `${l.title} · 财务建模实操课`;
      $('#topTitle').textContent = l.title;
      wireLesson(l);
    } else {
      view.innerHTML = renderHome();
      document.title = '财务建模实操课';
      $('#topTitle').textContent = '财务建模实操课';
    }
    renderNav(l ? l.id : null);
    closeSide();
    window.scrollTo(0, 0);
    const on = $('#nav a.on');
    if (on && on.scrollIntoView) {
      const side = $('#side');
      const r = on.getBoundingClientRect();
      if (r.top < 0 || r.bottom > window.innerHeight) side.scrollTop = on.offsetTop - 160;
    }
  }

  function openSide() {
    $('#side').classList.add('open');
    $('#scrim').classList.add('open');
  }
  function closeSide() {
    $('#side').classList.remove('open');
    $('#scrim').classList.remove('open');
  }

  function init() {
    applyTheme(theme);
    $('#themeBtn').addEventListener('click', () => {
      theme = themes[(themes.indexOf(theme) + 1) % themes.length];
      FM.store.set('theme', theme);
      applyTheme(theme);
    });
    $('#resetBtn').addEventListener('click', (e) => {
      const b = e.currentTarget;
      if (b.dataset.armed !== '1') {
        b.dataset.armed = '1';
        b.textContent = '再点一次确认清空';
        setTimeout(() => {
          b.dataset.armed = '';
          b.textContent = '清空学习进度';
        }, 3000);
        return;
      }
      done = new Set();
      saveDone();
      b.dataset.armed = '';
      b.textContent = '已清空';
      route();
    });
    $('#menuBtn').addEventListener('click', openSide);
    $('#scrim').addEventListener('click', closeSide);
    $('#q').addEventListener('input', (e) => doSearch(e.target.value));
    $('#searchRes').addEventListener('click', (e) => {
      if (e.target.closest('a')) {
        $('#q').value = '';
        doSearch('');
      }
    });
    window.addEventListener('hashchange', route);
    route();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
