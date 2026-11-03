#!/usr/bin/env python3
"""生成公众号配图：两张封面 + 14 张手机竖屏卡片（1080 像素宽）。

每张卡片先写成 HTML（图表部分由 matplotlib 输出 SVG，文字交给浏览器排版），
再用 Playwright 截图，所以标题、正文、数字在所有图里是同一套字体和版式。

用法（在 haitian/ 目录下）：
  python wechat/build_images.py
依赖：pandas、matplotlib，以及 node + playwright（截图用）。
字体：Noto Sans SC（中文）、Barlow Condensed（数字），未安装时会退回系统字体。
"""
from __future__ import annotations

import io
import json
import math
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from analysis import (  # noqa: E402
    BASE_YEAR,
    SENS_G,
    SENS_WACC,
    cashflow_table,
    dupont_table,
    implied_terminal_g,
    load_assumptions,
    load_financials,
    margin_table,
    roe_attribution,
    run_dcf,
    sensitivity_wacc_g,
)

BUILD = HERE / "_build"
OUT = HERE / "images"
TOTAL = 14
CARD_W = 420  # 按手机正文宽度设计，截图时放大到 1080 像素
CARD_SCALE = 1080 / CARD_W

# ---------------------------------------------------------------- 视觉规范
INK, INK2, MUTED, RULE = "#1f1a17", "#5b524b", "#8f867e", "#ebe6e0"
SOY = "#8c3510"  # 酱色：标签、重点数字
PAPER = "#f7f4f0"
BLUE, ORANGE, AQUA, RED, NAVY = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#184f95"
GRID, BASE = "#ece8e3", "#cfc8c0"
NUM = "Barlow Condensed"
SRC = "数据：海天味业 2019–2025 年年报、审计报告及公告"

CSS = f"""
html, body {{ margin: 0; background: #fff; }}
#card {{ width: {CARD_W}px; box-sizing: border-box; padding: 30px 22px 20px; background: #fff;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif; color: {INK}; }}
.tag {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px;
  font-size: 11.5px; letter-spacing: 1.5px; color: {SOY}; font-weight: 500; }}
.tag .no {{ font-family: "{NUM}", sans-serif; font-size: 15px; letter-spacing: .5px; color: {MUTED}; font-weight: 600; }}
h1 {{ font-size: 23px; line-height: 1.4; font-weight: 700; margin: 0 0 8px; letter-spacing: .3px; }}
h1 em, .em {{ font-style: normal; color: {SOY}; }}
.n {{ font-family: "{NUM}", sans-serif; font-weight: 600; letter-spacing: .2px; }}
.sub {{ font-size: 13.5px; line-height: 1.65; color: {INK2}; margin: 0 0 16px; }}
.chart svg {{ width: 100%; height: auto; display: block; }}
.note {{ font-size: 12px; line-height: 1.6; color: {INK2}; background: {PAPER}; border-radius: 6px; padding: 9px 12px; margin-top: 12px; }}
.foot {{ margin-top: 16px; padding-top: 9px; border-top: 1px solid {RULE}; display: flex; justify-content: space-between;
  gap: 12px; font-size: 10.5px; line-height: 1.5; color: {MUTED}; }}
.tick {{ color: {SOY}; white-space: nowrap; }}
"""


def page(body: str, extra_css: str = "") -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{CSS}{extra_css}</style></head><body>{body}</body></html>"
    )


COMPONENTS: dict[int, dict] = {}  # 每张卡的标题、副标题、内容和样式，长图复用


def card(no: int, title: str, sub: str, inner: str, foot: str = SRC, tick: bool = True, extra_css: str = "") -> str:
    COMPONENTS[no] = {"title": title, "sub": sub, "inner": inner, "css": extra_css}
    tick_html = '<span class="tick">勾稽 60/60 ✓</span>' if tick else ""
    return page(
        f"""<div id="card">
  <div class="tag"><span>海天味业 · 七年财报拆解</span><span class="no">{no:02d} / {TOTAL}</span></div>
  <h1>{title}</h1>
  {f'<p class="sub">{sub}</p>' if sub else ''}
  {inner}
  <div class="foot"><span>{foot}</span>{tick_html}</div>
</div>""",
        extra_css,
    )


# ---------------------------------------------------------------- matplotlib → SVG


def _setup_mpl() -> None:
    plt.rcParams.update(
        {
            "svg.fonttype": "none",  # 文字留成文字，由浏览器用同一套字体渲染
            "font.family": "sans-serif",
            "font.sans-serif": ["Noto Sans SC", "PingFang SC", "Microsoft YaHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 12.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.edgecolor": BASE,
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.7,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
            "xtick.color": INK2,
            "ytick.color": MUTED,
            "legend.frameon": False,
            "legend.fontsize": 12.5,
        }
    )


def svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    plt.close(fig)
    s = buf.getvalue()
    return s[s.index("<svg"):]


def numfont(ax, size: float = 14) -> None:
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        if any(ch.isdigit() for ch in lab.get_text()) and not any("一" <= ch <= "鿿" for ch in lab.get_text()):
            lab.set_fontfamily(NUM)
            lab.set_fontsize(size)


def label(ax, x, y, text, dy=5, size=15, color=INK, weight="semibold", ha="center", va="bottom", dx=0, family=NUM):
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va,
                fontsize=size, color=color, fontweight=weight, fontfamily=family)


def minus(v: float, fmt: str = "{:.1f}") -> str:
    s = fmt.format(abs(v))
    return ("+" if v > 0 else "−") + s


# ---------------------------------------------------------------- 各张图


def chart_revenue(m) -> str:
    years = list(m.index)
    x = np.arange(len(years))
    rev, np_ = m["营业收入"].values, m["归母净利润"].values
    fig, ax = plt.subplots(figsize=(5.2, 3.7))
    bw = 0.37
    ax.bar(x - bw / 2 - 0.015, rev, bw, color=BLUE, label="营业收入", zorder=3)
    ax.bar(x + bw / 2 + 0.015, np_, bw, color=ORANGE, label="归母净利润", zorder=3)
    dip = int(np.argmin(np.diff(rev))) + 1
    for i in (0, dip, len(years) - 1):
        label(ax, x[i] - bw / 2, rev[i], f"{rev[i]:.0f}")
        label(ax, x[i] + bw / 2, np_[i], f"{np_[i]:.1f}")
    ax.set_xticks(x, [str(y) for y in years])
    ax.set_ylim(0, 330)
    ax.set_yticks([0, 100, 200, 300])
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(-0.01, 1.1), handlelength=1, columnspacing=1.2)
    numfont(ax)
    fig.subplots_adjust(left=0.09, right=0.99, top=0.88, bottom=0.09)
    return svg(fig)


def chart_margins(m) -> str:
    years = list(m.index)
    gm, nm = m["毛利率"].values, m["归母净利率"].values
    lo = int(np.argmin(gm))
    fig, ax = plt.subplots(figsize=(5.2, 3.9))
    ax.axvspan(years[0] - 0.45, years[0] + 0.45, color=PAPER, zorder=0, lw=0)
    ax.text(years[0], 0.168, "旧准则\n运费在\n销售费用", ha="center", va="bottom", fontsize=10.5, color=MUTED, linespacing=1.35)
    for y, c, name in ((gm, BLUE, "毛利率"), (nm, ORANGE, "归母净利率")):
        ax.plot(years, y, color=c, lw=2.4, zorder=3, label=name, solid_capstyle="round")
        ax.plot(years, y, "o", color=c, ms=6.5, mec="white", mew=1.6, zorder=4)
    label(ax, years[0], gm[0], f"{gm[0]:.1%}", dy=8)
    label(ax, years[lo], gm[lo], f"{gm[lo]:.1%}", dy=-20, va="bottom")
    label(ax, years[-1], gm[-1], f"{gm[-1]:.1%}", dy=8, size=17, color=SOY, weight="bold")
    label(ax, years[0], nm[0], f"{nm[0]:.1%}", dy=8)
    label(ax, years[-1], nm[-1], f"{nm[-1]:.1%}", dy=8, size=17, color=SOY, weight="bold")
    ax.set_xlim(years[0] - 0.5, years[-1] + 0.5)
    ax.set_xticks(years, [str(y) for y in years])
    ax.set_ylim(0.15, 0.50)
    ax.set_yticks([0.2, 0.3, 0.4, 0.5])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend(loc="upper right", ncol=2, bbox_to_anchor=(1.01, 1.1), handlelength=1.4, columnspacing=1.2)
    numfont(ax)
    fig.subplots_adjust(left=0.11, right=0.99, top=0.88, bottom=0.09)
    return svg(fig)


def chart_margin_bridge(m) -> str:
    a, b = 2023, BASE_YEAR
    d = {k: (m.at[b, k] - m.at[a, k]) * 100 for k in ["毛利率", "销售费用率", "管理费用率", "研发费用率", "财务费用率", "归母净利率"]}
    other = d["归母净利率"] - (d["毛利率"] - d["销售费用率"] - d["管理费用率"] - d["研发费用率"] - d["财务费用率"])
    steps = [
        ("毛利率提升", d["毛利率"], "start"),
        ("销售费用多花", -d["销售费用率"], "step"),
        ("利息收入减少", -d["财务费用率"], "step"),
        ("管理费用多花", -d["管理费用率"], "step"),
        ("研发费用多花", -d["研发费用率"], "step"),
        ("所得税及其他", other, "step"),
        ("净利率只提升", d["归母净利率"], "total"),
    ]
    fig, ax = plt.subplots(figsize=(5.2, 4.1))
    ax.grid(False)
    ax.grid(True, axis="x", color=GRID, lw=0.7)
    running, h = 0.0, 0.62
    for i, (name, v, kind) in enumerate(steps):
        yy = -i
        if kind == "start":
            left, width, color = 0, v, BLUE
            running = v
        elif kind == "total":
            left, width, color = 0, v, NAVY
        else:
            left, width, color = running + min(v, 0), abs(v), RED if v < 0 else BLUE
            running += v
        ax.barh(yy, width, h, left=left, color=color, zorder=3)
        txt = f"+{v:.1f}" if kind in ("start", "total") else minus(v)
        ax.annotate(txt, (left + width if (kind != "step" or v > 0) else left, yy), xytext=(6 if (kind != "step" or v > 0) else -6, 0),
                    textcoords="offset points", ha="left" if (kind != "step" or v > 0) else "right", va="center",
                    fontsize=16, fontfamily=NUM, fontweight="bold" if kind != "step" else "semibold", color=INK)
        if i < len(steps) - 1 and kind != "total":
            ax.plot([running, running], [yy - h / 2, yy - 1 + h / 2], color=BASE, lw=1, zorder=2)
    ax.set_yticks([-i for i in range(len(steps))], [s[0] for s in steps])
    for lab in ax.get_yticklabels():
        lab.set_color(INK)
        lab.set_fontsize(13.5)
    ax.get_yticklabels()[0].set_fontweight("bold")
    ax.get_yticklabels()[-1].set_fontweight("bold")
    ax.spines["bottom"].set_visible(False)
    ax.set_xlim(-0.2, 6.6)
    ax.set_xticks([0, 2, 4, 6])
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}"))
    ax.tick_params(axis="x", colors=MUTED)
    numfont(ax, 13)
    fig.subplots_adjust(left=0.29, right=0.96, top=0.98, bottom=0.08)
    return svg(fig), d, other


def chart_dupont(dp) -> str:
    years = list(dp.index)
    panels = [
        ("ROE", "ROE（净资产收益率）", lambda v: f"{v:.1%}", 0.05, NAVY, lambda v, _: f"{v:.0%}"),
        ("归母净利率", "① 赚钱能力：净利率", lambda v: f"{v:.1%}", 0.02, BLUE, lambda v, _: f"{v:.0%}"),
        ("总资产周转率", "② 周转效率：总资产周转率", lambda v: f"{v:.2f}", 0.1, BLUE, lambda v, _: f"{v:.1f}"),
        ("权益乘数", "③ 杠杆：权益乘数", lambda v: f"{v:.2f}", 0.1, BLUE, lambda v, _: f"{v:.1f}"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(5.2, 5.0))
    for ax, (col, name, lab, step, color, tf) in zip(axes.flat, panels):
        y = dp[col].values
        ax.plot(years, y, color=color, lw=2.2, zorder=3)
        ax.plot(years, y, "o", color=color, ms=5, mec="white", mew=1.3, zorder=4)
        label(ax, years[0], y[0], lab(y[0]), dy=7, size=14)
        label(ax, years[-1], y[-1], lab(y[-1]), dy=7, size=15, color=SOY, weight="bold")
        lo, hi = y.min(), y.max()
        pad = (hi - lo) * 0.5
        ax.set_ylim(lo - pad * 0.5, hi + pad)
        ax.set_xlim(years[0] - 0.6, years[-1] + 0.6)
        ax.set_xticks([years[0], years[3], years[-1]], [str(years[0]), str(years[3]), str(years[-1])])
        ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(step))
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(tf))
        ax.set_title(name, loc="left", fontsize=13, color=INK, fontweight="bold", pad=8)
        numfont(ax, 13)
    fig.subplots_adjust(left=0.1, right=0.98, top=0.93, bottom=0.07, hspace=0.6, wspace=0.34)
    return svg(fig)


def chart_roe_bridge(attr) -> str:
    names = ["2019 年\nROE", "赚钱能力\n净利率", "周转效率\n周转率", "杠杆\n权益乘数", "2025 年\nROE"]
    vals = [attr["起点ROE"], attr["归母净利率"], attr["总资产周转率"], attr["权益乘数"], attr["终点ROE"]]
    fig, ax = plt.subplots(figsize=(5.2, 3.9))
    bw, running = 0.6, vals[0]
    for i, v in enumerate(vals):
        if i in (0, len(vals) - 1):
            ax.bar(i, v, bw, color=BLUE, zorder=3)
            label(ax, i, v, f"{v:.1%}", size=18, weight="bold")
        else:
            bottom = running + v
            ax.bar(i, -v, bw, bottom=bottom, color=RED, zorder=3)
            ax.plot([i - 1 + bw / 2, i - bw / 2], [running, running], color=BASE, lw=1, zorder=2)
            running += v
            label(ax, i, bottom, minus(v * 100) + " 个点", dy=-6, va="top", size=15)
    ax.plot([len(vals) - 2 + bw / 2, len(vals) - 1 - bw / 2], [running, running], color=BASE, lw=1, zorder=2)
    ax.set_xticks(range(len(names)), names)
    for lab in ax.get_xticklabels():
        lab.set_fontsize(12.5)
        lab.set_color(INK)
    ax.set_ylim(0, 0.40)
    ax.set_yticks([0, 0.1, 0.2, 0.3, 0.4])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0%}"))
    numfont(ax)
    fig.subplots_adjust(left=0.11, right=0.99, top=0.96, bottom=0.17)
    return svg(fig)


def chart_cash(cf, start=2021) -> str:
    d = cf.loc[start:]
    years = list(d.index)
    x = np.arange(len(years))
    bw = 0.27
    fig, ax = plt.subplots(figsize=(5.2, 3.9))
    ax.bar(x - bw - 0.02, d["归母净利润"], bw, color=ORANGE, label="净利润", zorder=3)
    ax.bar(x, d["经营现金流"], bw, color=BLUE, label="经营现金流", zorder=3)
    ax.bar(x + bw + 0.02, d["自由现金流"], bw, color=AQUA, label="自由现金流", zorder=3)
    for i, v in enumerate(d["自由现金流"]):
        label(ax, x[i] + bw + 0.02, v, f"{v:.0f}", size=14)
    ratio = d["经营现金流/归母净利润"]
    for i, r in enumerate(ratio):
        ax.annotate(f"{r:.2f}×", (x[i], 0), xytext=(0, -34), textcoords="offset points", ha="center",
                    fontsize=15, fontfamily=NUM, fontweight="bold" if r < 0.8 else "semibold",
                    color=SOY if r < 0.8 else INK2)
    ax.set_xticks(x, [str(y) for y in years])
    ax.set_ylim(0, 88)
    ax.set_yticks([0, 20, 40, 60, 80])
    ax.legend(loc="upper left", ncol=3, bbox_to_anchor=(-0.01, 1.1), handlelength=1, columnspacing=1.1)
    numfont(ax)
    fig.subplots_adjust(left=0.09, right=0.99, top=0.88, bottom=0.19)
    return svg(fig)


def chart_dcf(r) -> str:
    steps = [
        ("预测期\n现值", r.pv_fcf, "add"),
        ("终值\n现值", r.pv_terminal, "add"),
        ("企业\n价值", r.enterprise_value, "total"),
        ("净现金", r.net_cash, "add"),
        ("少数\n股东", -r.minority, "add"),
        ("股权\n价值", r.equity_value, "total"),
    ]
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    running, bw = 0.0, 0.62
    for i, (name, v, kind) in enumerate(steps):
        if kind == "total":
            ax.bar(i, v, bw, color=NAVY, zorder=3)
            running, top = v, v
        else:
            bottom = running + v if v < 0 else running
            ax.bar(i, abs(v), bw, bottom=bottom, color=RED if v < 0 else BLUE, zorder=3)
            running += v
            top = max(bottom + abs(v), running)
        label(ax, i, top, f"{v:,.0f}".replace("-", "−"), size=16 if kind == "total" else 15, weight="bold" if kind == "total" else "semibold")
        if i < len(steps) - 1:
            ax.plot([i + bw / 2, i + 1 - bw / 2], [running, running], color=BASE, lw=1, zorder=2)
    ax.set_xticks(range(len(steps)), [s[0] for s in steps])
    for lab in ax.get_xticklabels():
        lab.set_fontsize(12)
        lab.set_color(INK)
    ax.set_ylim(0, 2200)
    ax.set_yticks([0, 500, 1000, 1500, 2000])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    numfont(ax)
    fig.subplots_adjust(left=0.13, right=0.99, top=0.96, bottom=0.17)
    return svg(fig)


# ---------------------------------------------------------------- 文字卡片


def _mix(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def sensitivity_table(s, r) -> str:
    span = max(abs(s.values.max() - r.price), abs(s.values.min() - r.price))
    rows = []
    head = "".join(f'<th class="n">{g:.1%}</th>' for g in s.columns)
    rows.append(f'<tr><th class="corner">WACC ＼ 永续增长</th>{head}</tr>')
    for w_, row in s.iterrows():
        cells = []
        for g, v in row.items():
            t = (v - r.price) / span
            bg = _mix("#f3f1ee", "#a9c9f2", t) if t >= 0 else _mix("#f3f1ee", "#f2b0ae", -t)
            base = math.isclose(w_, r.wacc) and math.isclose(g, r.terminal_g)
            cls = ' class="base"' if base else ""
            cells.append(f'<td{cls} style="background:{bg}"><span class="n">{v:.1f}</span></td>')
        rows.append(f'<tr><th class="n">{w_:.1%}</th>{"".join(cells)}</tr>')
    return f"""<table class="sens">{''.join(rows)}</table>
<div class="legend"><span><i style="background:#a9c9f2"></i>高于现价 {r.price:.2f} 元</span>
<span><i style="background:#f2b0ae"></i>低于现价</span><span><i class="box"></i>基准情形</span></div>"""


SENS_CSS = f"""
.sens {{ width: 100%; border-collapse: separate; border-spacing: 3px; font-size: 13px; }}
.sens th {{ color: {INK2}; font-weight: 500; padding: 6px 2px; }}
.sens th.n {{ font-size: 16px; }}
.sens th.corner {{ font-size: 10.5px; color: {MUTED}; font-family: "Noto Sans SC", sans-serif; font-weight: 400; }}
.sens td {{ text-align: center; padding: 9px 0; border-radius: 4px; color: {INK}; }}
.sens td .n {{ font-size: 18px; }}
.sens td.base {{ outline: 2.5px solid {INK}; outline-offset: -2.5px; }}
.sens td.base .n {{ font-weight: 700; font-size: 20px; }}
.legend {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 10px; font-size: 11.5px; color: {INK2}; }}
.legend i {{ display: inline-block; width: 12px; height: 12px; border-radius: 3px; vertical-align: -1px; margin-right: 5px; }}
.legend i.box {{ background: #fff; outline: 2px solid {INK}; outline-offset: -2px; }}
"""


def card_summary(m, dp, r) -> str:
    rows = [
        (f"{m.at[BASE_YEAR, '毛利率']:.1%}", "毛利率回来了，但费用吃掉一半",
         f"毛利率从 2023 年低点 {m.at[2023, '毛利率']:.1%} 回到 {m.at[BASE_YEAR, '毛利率']:.1%}；同期费用率多了 2.7 个点，净利率只多了 1.5 个点。"),
        (f"{dp.at[BASE_YEAR, 'ROE']:.1%}", "ROE 掉了将近一半，因为钱太多",
         f"2019 年是 {dp.at[2019, 'ROE']:.1%}。约六成的下降来自资产周转变慢，账上现金和理财占了总资产的三分之二。"),
        (f"{r.value_per_share_price_date:.1f}<small>元</small>", "股价基本反映了预期",
         f"DCF 估出每股约 {r.value_per_share_price_date:.1f} 元，现价 {r.price:.2f} 元。不算贵，也没有明显的安全边际。"),
    ]
    items = "".join(
        f"""<div class="row"><div class="big n">{big}</div><div class="txt"><b>{head}</b><p>{body}</p></div></div>"""
        for big, head, body in rows
    )
    css = f"""
.row {{ display: grid; grid-template-columns: 128px 1fr; gap: 14px; padding: 16px 0; border-top: 1px solid {RULE}; align-items: start; }}
.row:first-of-type {{ border-top: none; padding-top: 4px; }}
.big {{ font-size: 44px; line-height: 1; color: {SOY}; font-weight: 700; }}
.big small {{ font-family: "Noto Sans SC", sans-serif; font-size: 16px; font-weight: 700; margin-left: 2px; }}
.txt b {{ font-size: 16px; display: block; margin-bottom: 5px; }}
.txt p {{ margin: 0; font-size: 13px; line-height: 1.65; color: {INK2}; }}
"""
    return card(1, "三句话看懂结论", "", f'<div class="rows">{items}</div>', extra_css=css)


def card_data(long) -> str:
    q = long["质量"].value_counts()
    a, b, c = int(q.get("A", 0)), int(q.get("B", 0)), int(q.get("C", 0))
    dots = "".join(f'<i class="{k}"></i>' for k in ["a"] * a + ["b"] * b + ["c"] * c)
    css = f"""
.stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 4px 0 18px; }}
.stat {{ background: {PAPER}; border-radius: 8px; padding: 14px 12px 12px; }}
.stat .n {{ font-size: 40px; line-height: 1; color: {SOY}; font-weight: 700; display: block; }}
.stat span {{ font-size: 12.5px; color: {INK2}; display: block; margin-top: 6px; line-height: 1.45; }}
.dots {{ display: grid; grid-template-columns: repeat(49, 1fr); gap: 2.5px; margin-bottom: 10px; }}
.dots i {{ height: 16px; border-radius: 2px; display: block; }}
.dots i.a {{ background: {SOY}; }} .dots i.b {{ background: #d9a988; }} .dots i.c {{ background: #eedccd; }}
.key {{ display: flex; gap: 14px; flex-wrap: wrap; font-size: 11.5px; color: {INK2}; margin-bottom: 14px; }}
.key i {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }}
ul {{ margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.7; color: {INK2}; }}
li + li {{ margin-top: 4px; }}
li b {{ color: {INK}; }}
"""
    inner = f"""<div class="stats">
  <div class="stat"><b class="n">{a + b + c}</b><span>个财务数字<br>2019–2025 年</span></div>
  <div class="stat"><b class="n">{a}</b><span>个来自年报<br>原文，精确到分</span></div>
  <div class="stat"><b class="n">60/60</b><span>项勾稽检查<br>全部对上</span></div>
</div>
<div class="dots">{dots}</div>
<div class="key"><span><i style="background:{SOY}"></i>年报原文 {a}</span><span><i style="background:#d9a988"></i>媒体转述 {b}</span><span><i style="background:#eedccd"></i>推算 {c}</span></div>
<ul>
  <li><b>勾稽怎么做：</b>用录入的数字反算 60 个同比增速和毛利率，和年报里公司自己披露的数字逐一比对，误差都在 0.15 个百分点以内。</li>
  <li><b>顺手纠了一个错：</b>有媒体把 2025 年管理费用写成 7.02 亿元，年报原文是 7.00 亿元。</li>
</ul>"""
    return card(2, "数据从哪来：逐个对过年报", "", inner, tick=False, extra_css=css)


def card_dupont_method(dp) -> str:
    f = [
        ("① 赚钱能力", "净利率", "每卖 100 元，最后落袋多少", f"{dp.at[2019, '归母净利率']:.1%}", f"{dp.at[BASE_YEAR, '归母净利率']:.1%}"),
        ("② 周转效率", "总资产周转率", "每 1 元资产，一年做多少生意", f"{dp.at[2019, '总资产周转率']:.2f}", f"{dp.at[BASE_YEAR, '总资产周转率']:.2f}"),
        ("③ 杠杆", "权益乘数", "除了自己的钱，还用了多少别人的钱", f"{dp.at[2019, '权益乘数']:.2f}", f"{dp.at[BASE_YEAR, '权益乘数']:.2f}"),
    ]
    boxes = []
    for i, (k, name, plain, v0, v1) in enumerate(f):
        if i:
            boxes.append('<div class="op">×</div>')
        boxes.append(
            f"""<div class="fbox"><div class="fl"><b>{k}</b><span>{name}</span><p>{plain}</p></div>
<div class="fv"><span class="n">{v0}</span><i>→</i><span class="n end">{v1}</span></div></div>"""
        )
    css = f"""
.fbox {{ display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center; background: {PAPER}; border-radius: 8px; padding: 12px 14px; }}
.fl b {{ font-size: 15.5px; }} .fl span {{ font-size: 12px; color: {MUTED}; margin-left: 6px; }}
.fl p {{ margin: 4px 0 0; font-size: 12.5px; color: {INK2}; }}
.fv {{ display: flex; align-items: baseline; gap: 6px; white-space: nowrap; }}
.fv .n {{ font-size: 22px; color: {INK2}; }} .fv .end {{ font-size: 26px; color: {SOY}; font-weight: 700; }}
.fv i {{ font-style: normal; color: {MUTED}; }}
.op {{ text-align: center; font-size: 20px; color: {MUTED}; line-height: 1; padding: 5px 0; }}
.result {{ margin-top: 6px; border-top: 2px solid {INK}; padding-top: 12px; display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 12px; }}
.result b {{ font-size: 16px; }} .result p {{ margin: 3px 0 0; font-size: 12.5px; color: {INK2}; }}
.result .fv .end {{ font-size: 30px; }}
"""
    inner = f"""{''.join(boxes)}
<div class="result"><div><b>= ROE（净资产收益率）</b><p>股东投入的每 100 元净资产，一年赚回多少</p></div>
<div class="fv"><span class="n">{dp.at[2019, 'ROE']:.1%}</span><i>→</i><span class="n end">{dp.at[BASE_YEAR, 'ROE']:.1%}</span></div></div>"""
    return card(6, "杜邦拆解：把 ROE 拆成三个数相乘", "像开一家酱油铺：赚钱能力 × 周转效率 × 杠杆。下面是海天 2019 → 2025 年的变化。",
                inner, extra_css=css)


def card_assets(w) -> str:
    y = w.loc[BASE_YEAR]
    parts = [("货币资金", y["cash"], SOY), ("银行理财", y["trading_fin_assets"], "#c9763f"), ("其他资产", y["total_assets"] - y["cash"] - y["trading_fin_assets"], "#e6dcd2")]
    total = y["total_assets"]
    cash_share = (y["cash"] + y["trading_fin_assets"]) / total
    segs = "".join(f'<div style="flex:{v:.1f};background:{c}"></div>' for _, v, c in parts)
    legend = "".join(
        f'<div class="li"><i style="background:{c}"></i><b>{n}</b><span class="n">{v:.1f}</span><em>亿元 · {v / total:.1%}</em></div>'
        for n, v, c in parts
    )
    css = f"""
.bar {{ display: flex; gap: 3px; height: 54px; border-radius: 6px; overflow: hidden; margin: 6px 0 6px; }}
.brace {{ display: flex; font-size: 12px; color: {SOY}; margin-bottom: 16px; }}
.brace div {{ border-top: 2px solid {SOY}; padding-top: 4px; text-align: center; font-weight: 500; }}
.li {{ display: grid; grid-template-columns: 14px 72px auto 1fr; gap: 8px; align-items: baseline; padding: 7px 0; border-bottom: 1px solid {RULE}; font-size: 13.5px; }}
.li i {{ width: 12px; height: 12px; border-radius: 3px; display: block; align-self: center; }}
.li .n {{ font-size: 22px; text-align: right; min-width: 56px; }}
.li em {{ font-style: normal; color: {MUTED}; font-size: 12px; }}
"""
    first_two = y["cash"] + y["trading_fin_assets"]
    inner = f"""<div class="bar">{segs}</div>
<div class="brace"><div style="flex:{first_two:.1f}">现金 + 理财 {first_two:.1f} 亿元，占 {cash_share:.1%}</div><div style="flex:{total - first_two:.1f};border:none"></div></div>
{legend}
<div class="note">这些钱不卖酱油，只赚利息和理财收益，回报远低于主业。2025 年 6 月 H 股上市又募资约 100 亿港元，净资产一年增加 33.8%，ROE 被进一步摊薄。</div>"""
    return card(9, "钱太多：现金理财占了<em>三分之二</em>", f"{BASE_YEAR} 年末资产构成，总资产 {total:.1f} 亿元", inner, extra_css=css)


def card_dcf_method(r, a) -> str:
    steps = [
        ("预测未来 5 年能赚多少现金", f"收入增速从 8% 逐步放缓到 5%；每 100 元收入产生 20 元自由现金流。"),
        ("估算 5 年以后的价值", f"假设 2030 年以后每年增长 {r.terminal_g:.1%}，这部分叫“终值”。"),
        ("折算成今天的钱", f"按 {r.wacc:.0%} 的折现率（投资者要求的年回报）往回折：企业价值 {r.enterprise_value:,.0f} 亿元，其中终值占 {r.terminal_share:.0%}。"),
        ("加上账上的钱，分到每一股", f"加净现金 {r.net_cash:.0f} 亿元、减少数股东权益 {r.minority:.0f} 亿元，除以 {r.shares:.2f} 亿股。"),
    ]
    items = "".join(
        f'<li><span class="k n">{i}</span><div><b>{h}</b><p>{b}</p></div></li>' for i, (h, b) in enumerate(steps, start=1)
    )
    css = f"""
ol {{ list-style: none; margin: 0; padding: 0; position: relative; }}
ol::before {{ content: ""; position: absolute; left: 15px; top: 18px; bottom: 18px; width: 2px; background: {RULE}; }}
li {{ display: grid; grid-template-columns: 32px 1fr; gap: 12px; padding: 8px 0; position: relative; }}
.k {{ width: 32px; height: 32px; border-radius: 50%; background: {SOY}; color: #fff; display: grid; place-items: center; font-size: 19px; }}
li b {{ font-size: 15.5px; display: block; margin: 4px 0 3px; }}
li p {{ margin: 0; font-size: 13px; line-height: 1.65; color: {INK2}; }}
.ans {{ margin-top: 10px; display: flex; align-items: baseline; justify-content: space-between; gap: 10px; background: {PAPER}; border-radius: 8px; padding: 12px 14px; }}
.ans b {{ font-size: 15px; }} .ans .n {{ font-size: 40px; color: {SOY}; font-weight: 700; }} .ans small {{ font-size: 14px; font-weight: 700; color: {SOY}; }}
"""
    inner = f"""<ol>{items}</ol>
<div class="ans"><b>每股价值约</b><span><span class="n">{r.value_per_share_price_date:.1f}</span><small> 元</small></span></div>"""
    return card(11, "DCF：一只会下蛋的母鸡值多少钱", "看它将来能下多少蛋，再把将来的蛋折算成今天的价值。分四步：", inner, extra_css=css)


def card_track(m) -> str:
    rows = [
        ("毛利率", f"{m.at[BASE_YEAR, '毛利率']:.1%}", "看原材料价格，每掉 1 个点少赚约 2.9 亿元"),
        ("销售费用率", f"{m.at[BASE_YEAR, '销售费用率']:.2%}", "两年多了 1.4 个点，看投入能不能换来收入提速"),
        ("收入增速", f"+{m.at[BASE_YEAR, '营收同比']:.1%}", "估值假设未来两年各增长 8%，跑不到要下调"),
        ("现金使用", "347 亿", "分红、回购的力度，决定 ROE 能不能回升"),
    ]
    items = "".join(
        f'<div class="tr"><div class="tn"><b>{n}</b><span class="n">{v}</span></div><p>{d}</p></div>' for n, v, d in rows
    )
    css = f"""
.tr {{ display: grid; gap: 4px; padding: 12px 0; border-top: 1px solid {RULE}; }}
.tr:first-child {{ border-top: 2px solid {INK}; }}
.tn {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }}
.tn b {{ font-size: 15.5px; }}
.tn .n {{ font-size: 26px; color: {SOY}; font-weight: 700; }}
.tr p {{ margin: 0; font-size: 13px; line-height: 1.65; color: {INK2}; }}
"""
    return card(14, "接下来，盯住这四个信号", "它们分别对应前面的毛利、费用、估值假设和 ROE。", f"<div>{items}</div>", tick=False, extra_css=css)


def covers(dp) -> list[tuple[str, str, int]]:
    roe = [float(v) for v in dp["ROE"].values]
    lo, hi = 0.15, 0.40
    yy = lambda v: 16 + (hi - v) / (hi - lo) * 150  # noqa: E731
    pts = " ".join(f"{16 + i * 61:.0f},{yy(v):.0f}" for i, v in enumerate(roe))
    spark = f"""<svg viewBox="0 0 400 190" class="spark" style="{{style}}"><polyline points="{pts}" fill="none" stroke="#f0a24a" stroke-width="4" stroke-linejoin="round" stroke-linecap="round" opacity=".55"/>
<circle cx="16" cy="{yy(roe[0]):.0f}" r="7" fill="#f0a24a"/><circle cx="{16 + 6 * 61}" cy="{yy(roe[-1]):.0f}" r="8" fill="#fbf6f0"/>
<text x="16" y="186" fill="#c9b7a6" font-size="17" font-family="Barlow Condensed" font-weight="600">2019</text>
<text x="382" y="186" fill="#c9b7a6" font-size="17" font-family="Barlow Condensed" font-weight="600" text-anchor="end">2025</text></svg>"""
    base_css = f"""
html, body {{ margin: 0; }}
#card {{ box-sizing: border-box; background: #2a1810; color: #fbf6f0; font-family: "Noto Sans SC", sans-serif; position: relative; overflow: hidden; }}
.k {{ color: #f0a24a; font-size: 13px; letter-spacing: 3px; font-weight: 500; }}
h1 {{ font-weight: 900; letter-spacing: 1px; margin: 0; line-height: 1.28; }}
.sub {{ color: #d9c6b5; margin: 0; }}
.lab {{ font-family: "{NUM}", sans-serif; font-weight: 600; color: #c9b7a6; letter-spacing: 1px; }}
.fig {{ font-family: "{NUM}", sans-serif; font-weight: 700; color: #f0a24a; line-height: 1; white-space: nowrap; }}
.fig b {{ color: #fbf6f0; }}
.fig i {{ font-style: normal; color: #8f7b6a; font-weight: 600; margin: 0 6px; }}
.spark {{ display: block; }}
.cap {{ font-size: 12px; color: #a8927f; letter-spacing: 1px; }}
"""
    wide = page(
        f"""<div id="card" style="width:900px;height:383px;padding:46px 52px;">
  <div style="position:absolute;left:52px;top:46px;width:470px">
    <div class="k">海天味业 · 七年财报拆解</div>
    <h1 style="font-size:44px;margin-top:24px">一年赚 70 亿，<br>ROE 却掉了将近一半</h1>
    <p class="sub" style="font-size:18px;margin-top:18px">毛利率回来了，钱去哪了？现在贵不贵？</p>
  </div>
  <div style="position:absolute;right:52px;top:58px;width:300px">
    <div class="lab" style="font-size:16px">ROE · 净资产收益率</div>
    <div class="fig" style="font-size:52px;margin-top:8px">35.2%<i>→</i><b>19.5%</b></div>
    {spark.replace("{style}", "width:300px;margin-top:18px")}
  </div>
  <div class="cap" style="position:absolute;left:52px;bottom:40px">年报原文数据 · 杜邦拆解 · DCF 估值</div>
</div>""",
        base_css,
    )
    square = page(
        f"""<div id="card" style="width:540px;height:540px;padding:46px 42px;">
  <div class="k">海天味业 · 七年财报拆解</div>
  <h1 style="font-size:38px;margin-top:26px">一年赚 70 亿，<br>ROE 却掉了将近一半</h1>
  <p class="sub" style="font-size:17px;margin-top:14px">毛利率回来了，钱去哪了？现在贵不贵？</p>
  <div style="position:absolute;left:42px;right:42px;bottom:40px">
    <div class="lab" style="font-size:15px">ROE · 净资产收益率</div>
    <div class="fig" style="font-size:64px;margin-top:8px">35.2%<i>→</i><b>19.5%</b></div>
  </div>
</div>""",
        base_css,
    )
    return [("00_封面_2.35比1.html", wide, 900), ("00_封面_1比1.html", square, 540)]


# ---------------------------------------------------------------- 入口


def build_pages():
    """生成全部卡片的 HTML，同时把每张卡的内容登记到 COMPONENTS。返回 (页面列表, 杜邦表)。"""
    _setup_mpl()
    w, long = load_financials()
    a = load_assumptions()
    m, dp, cf = margin_table(w), dupont_table(w), cashflow_table(w, a["tax_rate"])
    attr = roe_attribution(dp, 2019, BASE_YEAR)
    r = run_dcf(w, a)
    sens = sensitivity_wacc_g(w, a)
    rev, gm = m["营业收入"], m["毛利率"]
    n = len(rev) - 1
    rev_cagr = (rev.iloc[-1] / rev.iloc[0]) ** (1 / n) - 1
    np_cagr = (m["归母净利润"].iloc[-1] / m["归母净利润"].iloc[0]) ** (1 / n) - 1
    bridge_svg, d, other = chart_margin_bridge(m)
    cash_share = (w.at[BASE_YEAR, "cash"] + w.at[BASE_YEAR, "trading_fin_assets"]) / w.at[BASE_YEAR, "total_assets"]
    g_impl = implied_terminal_g(w, a)

    def chart_card(no, title, sub, chart, note="", extra_css="", tick=True):
        note_html = f'<div class="note">{note}</div>' if note else ""
        return card(no, title, sub, f'<div class="chart">{chart}</div>{note_html}', tick=tick, extra_css=extra_css)

    eq_css = f""".eq {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 8px; margin-top:12px; font-size:13px; color:{INK2}; background:{PAPER}; border-radius:8px; padding:10px 12px; }}
.eq .n {{ font-size:20px; color:{INK}; }} .eq .end {{ font-size:24px; color:{SOY}; font-weight:700; }}"""
    pages = [
        ("01_三句话结论.html", card_summary(m, dp, r), 540),
        ("02_数据从哪来.html", card_data(long), 540),
        ("03_营收与利润.html", chart_card(
            3, f"收入稳稳地涨，利润跑得慢",
            f"营业收入与归母净利润，亿元。六年复合增速：收入 <b class='em'>{rev_cagr:.1%}</b>，利润 <b class='em'>{np_cagr:.1%}</b>",
            chart_revenue(m),
            note="2022、2023 年利润连续下滑，2023 年收入也少了 4.1%；2024 年起重回增长。"), 540),
        ("04_毛利率.html", chart_card(
            4, f"毛利率先跌后涨，回到 <em>{gm.iloc[-1]:.1%}</em>",
            f"{gm.iloc[0]:.1%} → {gm.min():.1%}（2023 年低点）→ {gm.iloc[-1]:.1%}。毛利率 = 卖 100 元酱油，扣掉原料、包装、工厂和运费后剩下的钱",
            chart_margins(m),
            note="2020 年起运费计入成本，毛利率被动下降一截；2021–2023 年是原材料涨价；2025 年成本只涨 1.8%，毛利率回到 40% 以上。"), 540),
        ("05_毛利到净利.html", chart_card(
            5, f"毛利率升 <em>{d['毛利率']:.1f}</em> 点，净利率只升 <em>{d['归母净利率']:.1f}</em>",
            "2023 → 2025 年，各项目对净利率的影响，单位：百分点",
            bridge_svg,
            note="销售费用增长来自人工、股权激励和广告；海天几乎不借钱，财务费用常年为负，利率下行后利息收入变少，也吃掉了 0.8 个点。"), 540),
        ("06_杜邦拆解方法.html", card_dupont_method(dp), 540),
        ("07_杜邦三因子.html", chart_card(
            7, f"ROE 跌到 <em>{dp['ROE'].iloc[-1]:.1%}</em>，三个因子全下滑",
            "资产、净资产取期初期末平均；口径为归属于母公司股东", chart_dupont(dp)), 540),
        ("08_ROE归因.html", chart_card(
            8, f"ROE 下降的近 <em>{attr['总资产周转率'] / (attr['终点ROE'] - attr['起点ROE']):.0%}</em> 来自周转变慢",
            "2019 → 2025 年 ROE 下降 15.7 个点，按对数法分摊到三个因子（三项相加正好等于总变化）",
            chart_roe_bridge(attr)), 540),
        ("09_资产构成.html", card_assets(w), 540),
        ("10_现金流.html", chart_card(
            10, "利润基本都变成了真金白银",
            "亿元；自由现金流 = 经营现金流 − 建厂买设备的支出。年份下方是“经营现金流 ÷ 净利润”",
            chart_cash(cf),
            note="2022 年现金流只有利润的 0.62 倍，2023 年补了回来，两年合计 0.95 倍；2025 年自由现金流 64.6 亿元，为近几年最高。"), 540),
        ("11_DCF方法.html", card_dcf_method(r, a), 540),
        ("12_DCF结果.html", card(
            12, f"每股约 <em>{r.value_per_share_price_date:.1f}</em> 元，现价 {r.price:.2f} 元",
            "从企业价值到股权价值，亿元",
            f"""<div class="chart">{chart_dcf(r)}</div>
<div class="eq"><span>÷ {r.shares:.2f} 亿股 =</span><span class="n">{r.value_per_share_val_date:.2f}</span><span>元（2025 年末）</span>
<span>→ 滚动到 11 月 2 日、扣除 0.80 元红利 →</span><span class="n end">{r.value_per_share_price_date:.2f}</span><span>元</span></div>""",
            extra_css=eq_css), 540),
        ("13_DCF敏感性.html", card(
            13, "折现率每变 0.5 点，每股变约 <em>3</em> 元",
            f"每股价值（元）随折现率和永续增长率的变化。现价隐含的永续增长率是 {g_impl:.2%}，和基准假设几乎一样",
            sensitivity_table(sens, r), extra_css=SENS_CSS), 540),
        ("14_跟踪信号.html", card_track(m), 540),
    ]
    return covers(dp) + pages, dp


def main() -> None:
    pages, _ = build_pages()
    BUILD.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    jobs = []
    for name, html, width in pages:
        p = BUILD / name
        p.write_text(html, encoding="utf-8")
        is_cover = name.startswith("00_封面")
        jobs.append({
            "html": str(p),
            "out": str(OUT / name.replace(".html", ".png")),
            "width": width if is_cover else CARD_W,
            "scale": 2 if is_cover else CARD_SCALE,
        })
    jobs_file = BUILD / "jobs.json"
    jobs_file.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["node", str(HERE / "shoot.cjs"), str(jobs_file)], check=True)
    print(f"已生成 {len(jobs)} 张图：{OUT}")


if __name__ == "__main__":
    main()
