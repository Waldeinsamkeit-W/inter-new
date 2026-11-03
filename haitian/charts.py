"""公众号配图。白底、细线、直接标注，手机竖屏阅读也能看清。"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

# 配色：分类色按固定顺序取用（已用色盲模拟校验相邻对）。青、黄两色在白底对比度不足 3:1，
# 用到它们的系列一律直接标数。
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
NEG = "#e34948"  # 发散色的负极（与蓝色构成冷暖两极）
BLUE_DARK = "#184f95"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SURFACE, SHADE = "#e1e0d9", "#c3c2b7", "#ffffff", "#f3f2ee"

SOURCE = "来源：海天味业 2018–2025 年年报及审计报告；2025 年部分科目为媒体/研报转述，明细见 data/financials.csv"

FIG_W, FIG_H = 7.5, 4.8
DPI = 220


def _setup() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Noto Sans SC",
                "Source Han Sans SC",
                "PingFang SC",
                "Microsoft YaHei",
                "WenQuanYi Zen Hei",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
            "font.size": 10.5,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": BASELINE,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.7,
            "grid.linestyle": "-",
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelcolor": INK2,
            "ytick.labelcolor": MUTED,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
            "legend.frameon": False,
            "legend.fontsize": 10,
            "savefig.dpi": DPI,
            "savefig.facecolor": SURFACE,
        }
    )


def _frame(fig, title: str, subtitle: str, note: str | None = None, top: float = 0.80, bottom: float = 0.13):
    fig.text(0.035, 0.955, title, fontsize=15, fontweight="bold", color=INK, va="top")
    fig.text(0.035, 0.885, subtitle, fontsize=10.5, color=INK2, va="top")
    foot = SOURCE if note is None else f"{note}\n{SOURCE}"
    fig.text(0.035, 0.022, foot, fontsize=7.8, color=MUTED, va="bottom", linespacing=1.5)
    fig.subplots_adjust(left=0.09, right=0.97, top=top, bottom=bottom)


def _pct(decimals: int = 0):
    return FuncFormatter(lambda v, _: f"{v * 100:.{decimals}f}%")


def _save(fig, path: Path) -> Path:
    fig.savefig(path)
    plt.close(fig)
    return path


def _line(ax, x, y, color, label, end_label: str | None = None, marker_every=True):
    ax.plot(x, y, color=color, lw=2, label=label, zorder=3, solid_capstyle="round")
    if marker_every:
        ax.plot(x, y, "o", color=color, ms=5.5, mec=SURFACE, mew=1.5, zorder=4)
    if end_label:
        ax.annotate(
            end_label,
            (x[-1], y[-1]),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=10,
            color=INK,
        )


# ------------------------------------------------------------------ 图 1


def chart_revenue_profit(m: pd.DataFrame, out: Path) -> Path:
    years = list(m.index)
    x = np.arange(len(years))
    rev, np_ = m["营业收入"].values, m["归母净利润"].values
    n = len(years) - 1
    rev_cagr = (rev[-1] / rev[0]) ** (1 / n) - 1
    np_cagr = (np_[-1] / np_[0]) ** (1 / n) - 1

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    bw = 0.36
    ax.bar(x - bw / 2 - 0.01, rev, bw, color=BLUE, label="营业收入", edgecolor=SURFACE, linewidth=1, zorder=3)
    ax.bar(x + bw / 2 + 0.01, np_, bw, color=ORANGE, label="归母净利润", edgecolor=SURFACE, linewidth=1, zorder=3)
    for i in (0, int(np.argmin(np.diff(rev))) + 1, len(years) - 1):
        ax.annotate(f"{rev[i]:.0f}", (x[i] - bw / 2, rev[i]), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9.5, color=INK)
        ax.annotate(f"{np_[i]:.1f}", (x[i] + bw / 2, np_[i]), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9.5, color=INK)
    ax.set_xticks(x, [str(y) for y in years])
    ax.set_ylim(0, rev.max() * 1.15)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.02))
    _frame(
        fig,
        f"营收六年复合增长 {rev_cagr:.1%}，利润增速慢于收入（{np_cagr:.1%}）",
        f"营业收入与归母净利润，亿元，{years[0]}–{years[-1]}",
    )
    return _save(fig, out / "01_营收与归母净利润.png")


# ------------------------------------------------------------------ 图 2


def chart_margins(m: pd.DataFrame, out: Path) -> Path:
    years = list(m.index)
    gm, nm = m["毛利率"].values, m["归母净利率"].values
    lo = int(np.argmin(gm))

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.axvspan(years[0] - 0.5, years[0] + 0.5, color=SHADE, zorder=0, lw=0)
    ax.text(years[0], 0.165, "旧收入准则\n运费计入销售费用", ha="center", va="bottom", fontsize=8.5, color=INK2,
            linespacing=1.4)
    _line(ax, years, gm, BLUE, "毛利率", f"毛利率 {gm[-1]:.1%}")
    _line(ax, years, nm, ORANGE, "归母净利率", f"归母净利率 {nm[-1]:.1%}")
    ax.annotate(f"{gm[0]:.1%}", (years[0], gm[0]), xytext=(0, 9), textcoords="offset points", ha="center",
                fontsize=9.5, color=INK)
    ax.annotate(f"{gm[lo]:.1%}", (years[lo], gm[lo]), xytext=(0, -16), textcoords="offset points", ha="center",
                fontsize=9.5, color=INK)
    ax.annotate(f"{nm[0]:.1%}", (years[0], nm[0]), xytext=(0, 9), textcoords="offset points", ha="center",
                fontsize=9.5, color=INK)
    ax.set_xlim(years[0] - 0.5, years[-1] + 1.6)
    ax.set_xticks(years, [str(y) for y in years])
    ax.set_ylim(0.15, 0.50)
    ax.yaxis.set_major_formatter(_pct())
    ax.legend(loc="upper right", ncol=2, bbox_to_anchor=(1, 1.02))
    _frame(
        fig,
        f"毛利率 {years[lo]} 年见底（{gm[lo]:.1%}），{years[-1]} 年回到 {gm[-1]:.1%}",
        "毛利率与归母净利率",
        note="注：2020 年起执行新收入准则，运费从销售费用调入营业成本，2019 年毛利率与之后年份不完全可比。",
        bottom=0.16,
    )
    return _save(fig, out / "02_毛利率与净利率.png")


# ------------------------------------------------------------------ 图 3


def chart_expenses(m: pd.DataFrame, out: Path, start: int = 2020) -> Path:
    d = m.loc[start:]
    years = list(d.index)
    series = [
        ("销售费用率", "销售", BLUE),
        ("管理费用率", "管理", ORANGE),
        ("研发费用率", "研发", AQUA),
        ("财务费用率", "财务", YELLOW),
    ]
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.axhline(0, color=BASELINE, lw=1, zorder=2)
    for col, short, color in series:
        _line(ax, years, d[col].values, color, short + "费用率", f"{short} {d[col].iloc[-1]:.1%}")
    ax.set_xlim(years[0] - 0.4, years[-1] + 1.1)
    ax.set_xticks(years, [str(y) for y in years])
    ax.set_ylim(-0.035, 0.08)
    ax.yaxis.set_major_formatter(_pct())
    ax.legend(loc="upper left", ncol=4, bbox_to_anchor=(0, 1.02))
    base = 2023
    delta = m.at[years[-1], "期间费用率"] - m.at[base, "期间费用率"]
    d_sell = m.at[years[-1], "销售费用率"] - m.at[base, "销售费用率"]
    d_fin = m.at[years[-1], "财务费用率"] - m.at[base, "财务费用率"]
    _frame(
        fig,
        f"{base} 年以来期间费用率抬升 {delta * 100:.1f} 个百分点",
        f"四项费用占营收比例；其中销售 +{d_sell * 100:.1f} 个点，利息收入减少使财务费用率 +{d_fin * 100:.1f} 个点",
        note=f"注：财务费用为负表示利息收入大于利息支出。2019 年运费在销售费用中（销售费用率 {m.at[2019, '销售费用率']:.1%}），与 2020 年后不可比，未画入。",
        bottom=0.16,
    )
    return _save(fig, out / "03_费用率.png")


# ------------------------------------------------------------------ 图 4


def chart_dupont(dp: pd.DataFrame, out: Path) -> Path:
    years = list(dp.index)
    panels = [
        ("ROE", "ROE（归母，平均净资产）", _pct(0), lambda v: f"{v:.1%}", 0.05),
        ("归母净利率", "① 归母净利率", _pct(0), lambda v: f"{v:.1%}", 0.02),
        ("总资产周转率", "② 总资产周转率（次）", FuncFormatter(lambda v, _: f"{v:.1f}"), lambda v: f"{v:.2f}", 0.1),
        ("权益乘数", "③ 权益乘数（倍）", FuncFormatter(lambda v, _: f"{v:.1f}"), lambda v: f"{v:.2f}", 0.1),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(FIG_W, FIG_H * 1.25))
    for ax, (col, name, fmt, lab, step) in zip(axes.flat, panels):
        y = dp[col].values
        color = INK2 if col == "ROE" else BLUE
        ax.plot(years, y, color=color, lw=2, zorder=3)
        ax.plot(years, y, "o", color=color, ms=5, mec=SURFACE, mew=1.3, zorder=4)
        for i, va, dy in ((0, "bottom", 7), (len(y) - 1, "bottom", 7)):
            ax.annotate(lab(y[i]), (years[i], y[i]), xytext=(0, dy), textcoords="offset points", ha="center",
                        va=va, fontsize=9.5, color=INK)
        lo, hi = y.min(), y.max()
        pad = (hi - lo) * 0.45 or hi * 0.1
        ax.set_ylim(max(0, lo - pad * 0.6), hi + pad)
        ax.set_xlim(years[0] - 0.5, years[-1] + 0.5)
        ax.set_xticks(years[::2], [str(v) for v in years[::2]])
        ax.yaxis.set_major_formatter(fmt)
        ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(step))
        ax.set_title(name, loc="left", fontsize=10.5, color=INK, pad=6)
    _frame(
        fig,
        f"ROE 从 {dp['ROE'].iloc[0]:.1%} 降到 {dp['ROE'].iloc[-1]:.1%}",
        "杜邦拆解：ROE = ① 归母净利率 × ② 总资产周转率 × ③ 权益乘数（资产与净资产取期初期末平均）",
        top=0.80,
        bottom=0.10,
    )
    fig.subplots_adjust(hspace=0.45, wspace=0.28, left=0.08)
    return _save(fig, out / "04_杜邦三因子.png")


# ------------------------------------------------------------------ 图 5


def chart_roe_bridge(attr: pd.Series, out: Path, start: int, end: int) -> Path:
    labels = [f"{start} ROE", "归母净利率", "总资产周转率", "权益乘数", f"{end} ROE"]
    vals = [attr["起点ROE"], attr["归母净利率"], attr["总资产周转率"], attr["权益乘数"], attr["终点ROE"]]
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    running = vals[0]
    x = np.arange(len(labels))
    bw = 0.56
    for i, v in enumerate(vals):
        if i in (0, len(vals) - 1):
            ax.bar(i, v, bw, color=BLUE, zorder=3)
            ax.annotate(f"{v:.1%}", (i, v), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=10.5,
                        color=INK, fontweight="bold")
        else:
            bottom = running + v if v < 0 else running
            ax.bar(i, abs(v), bw, bottom=bottom, color=NEG if v < 0 else BLUE, zorder=3)
            ax.plot([i - 1 + bw / 2, i - bw / 2], [running, running], color=BASELINE, lw=1, zorder=2)
            running += v
            ax.annotate(f"{v * 100:+.1f} 个点", (i, bottom), xytext=(0, -14), textcoords="offset points",
                        ha="center", fontsize=10, color=INK)
    ax.plot([len(vals) - 2 + bw / 2, len(vals) - 1 - bw / 2], [running, running], color=BASELINE, lw=1, zorder=2)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, vals[0] * 1.15)
    ax.yaxis.set_major_formatter(_pct())
    share = attr["总资产周转率"] / (attr["终点ROE"] - attr["起点ROE"])
    _frame(
        fig,
        f"ROE 下降的约 {share:.0%} 来自总资产周转变慢",
        f"{start}→{end} 年 ROE 变化按对数法分摊到三个因子（三项之和等于总变化）",
    )
    return _save(fig, out / "05_ROE变化归因.png")


# ------------------------------------------------------------------ 图 6


def chart_cashflow(cf: pd.DataFrame, out: Path, start: int = 2021) -> Path:
    d = cf.loc[start:]
    years = list(d.index)
    x = np.arange(len(years))
    bw = 0.26
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.bar(x - bw - 0.02, d["归母净利润"], bw, color=ORANGE, label="归母净利润", zorder=3)
    ax.bar(x, d["经营现金流"], bw, color=BLUE, label="经营现金流", zorder=3)
    bars = ax.bar(x + bw + 0.02, d["自由现金流"], bw, color=AQUA, label="自由现金流", zorder=3)
    for b, v in zip(bars, d["自由现金流"]):
        ax.annotate(f"{v:.0f}", (b.get_x() + b.get_width() / 2, v), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=9, color=INK)
    ratio = d["经营现金流/归母净利润"]
    for i, r in enumerate(ratio):
        ax.annotate(f"现金流/利润 {r:.2f}", (x[i], 0), xytext=(0, -30), textcoords="offset points", ha="center",
                    fontsize=8.5, color=INK if r < 0.8 else INK2,
                    fontweight="bold" if r < 0.8 else "normal")
    ax.set_xticks(x, [str(y) for y in years])
    ax.tick_params(axis="x", pad=4)
    ax.set_ylim(0, d[["归母净利润", "经营现金流"]].values.max() * 1.18)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    ax.legend(loc="upper left", ncol=3, bbox_to_anchor=(0, 1.02))
    worst = ratio.idxmin()
    _frame(
        fig,
        f"{worst} 年经营现金流只有利润的 {ratio[worst]:.0%}，之后恢复到 1 倍以上",
        "亿元；自由现金流 = 经营现金流 − 购建固定资产等长期资产支付的现金",
        bottom=0.19,
    )
    return _save(fig, out / "06_现金流.png")


# ------------------------------------------------------------------ 图 7


def chart_dcf_bridge(r, out: Path) -> Path:
    steps = [
        ("预测期 FCF\n现值", r.pv_fcf, "add"),
        ("终值现值", r.pv_terminal, "add"),
        ("企业价值", r.enterprise_value, "total"),
        ("净现金", r.net_cash, "add"),
        ("少数股东\n权益", -r.minority, "add"),
        ("股权价值", r.equity_value, "total"),
    ]
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    running = 0.0
    bw = 0.58
    for i, (name, v, kind) in enumerate(steps):
        if kind == "total":
            ax.bar(i, v, bw, color=BLUE_DARK, zorder=3)
            top = v
            running = v
        else:
            bottom = running + v if v < 0 else running
            ax.bar(i, abs(v), bw, bottom=bottom, color=NEG if v < 0 else BLUE, zorder=3)
            running += v
            top = max(bottom + abs(v), running)
        ax.annotate(f"{v:,.0f}", (i, top), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=10,
                    color=INK, fontweight="bold" if kind == "total" else "normal")
        if i < len(steps) - 1:
            ax.plot([i + bw / 2, i + 1 - bw / 2], [running, running], color=BASELINE, lw=1, zorder=2)
    ax.set_xticks(range(len(steps)), [s[0] for s in steps])
    ax.set_ylim(0, r.equity_value * 1.55)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    txt = (
        f"÷ {r.shares:.2f} 亿股 = 每股 {r.value_per_share_val_date:.2f} 元（2025-12-31）\n"
        f"滚动至 2026-11-02 并扣除已派末期红利 {r.dps_after_val_date:.2f} 元 → {r.value_per_share_price_date:.2f} 元\n"
        f"现价 {r.price:.2f} 元，差 {r.upside:+.1%}"
    )
    ax.text(0.02, 0.97, txt, transform=ax.transAxes, va="top", ha="left", fontsize=9.5, color=INK, linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.5", fc=SHADE, ec="none"))
    _frame(
        fig,
        f"DCF：每股约 {r.value_per_share_price_date:.1f} 元，与现价 {r.price:.2f} 元接近",
        f"亿元；WACC {r.wacc:.1%}，永续增长 {r.terminal_g:.1%}，FCF 率 {r.fcf_margin:.0%}；"
        f"终值占企业价值 {r.terminal_share:.0%}",
    )
    return _save(fig, out / "07_DCF估值构成.png")


# ------------------------------------------------------------------ 图 8


def chart_sensitivity(s: pd.DataFrame, r, out: Path) -> Path:
    vals = s.values
    span = max(abs(vals.max() - r.price), abs(vals.min() - r.price))
    cmap = LinearSegmentedColormap.from_list("div", ["#f2a3a2", "#f0efec", "#86b6ef"])
    norm = TwoSlopeNorm(vcenter=r.price, vmin=r.price - span, vmax=r.price + span)
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H * 1.05))
    ax.imshow(vals, cmap=cmap, norm=norm, aspect="auto")
    ax.grid(False)
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            base = np.isclose(s.index[i], r.wacc) and np.isclose(s.columns[j], r.terminal_g)
            ax.text(j, i, f"{vals[i, j]:.1f}", ha="center", va="center", fontsize=10.5, color=INK,
                    fontweight="bold" if base else "normal")
            if base:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=INK, lw=2))
    ax.set_xticks(range(len(s.columns)), [f"{g:.1%}" for g in s.columns])
    ax.set_yticks(range(len(s.index)), [f"{w:.1%}" for w in s.index])
    ax.set_xlabel("永续增长率", color=INK2)
    ax.set_ylabel("WACC", color=INK2)
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()
    ax.tick_params(axis="both", labelcolor=INK2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    i0 = list(s.index).index(min(s.index, key=lambda v: abs(v - r.wacc)))
    j0 = list(s.columns).index(min(s.columns, key=lambda v: abs(v - r.terminal_g)))
    step = (abs(s.iloc[i0 - 1, j0] - s.iloc[i0, j0]) + abs(s.iloc[i0 + 1, j0] - s.iloc[i0, j0])) / 2
    _frame(
        fig,
        f"WACC 每变动 0.5 个点，每股价值变动约 {step:.1f} 元",
        f"每股价值（元，滚动至 2026-11-02）；蓝色高于现价 {r.price:.2f} 元，红色低于；粗框为基准情形",
        top=0.74,
        bottom=0.08,
    )
    fig.subplots_adjust(left=0.13)
    return _save(fig, out / "08_DCF敏感性.png")


# ------------------------------------------------------------------ 入口


def make_all_charts(out: Path, margins, dupont, attrib, cash, dcf, sens_wg) -> list[Path]:
    _setup()
    out.mkdir(parents=True, exist_ok=True)
    start, end = dupont.index[0], dupont.index[-1]
    return [
        chart_revenue_profit(margins, out),
        chart_margins(margins, out),
        chart_expenses(margins, out),
        chart_dupont(dupont, out),
        chart_roe_bridge(attrib, out, start, end),
        chart_cashflow(cash, out),
        chart_dcf_bridge(dcf, out),
        chart_sensitivity(sens_wg, dcf, out),
    ]
