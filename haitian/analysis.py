#!/usr/bin/env python3
"""海天味业（603288）财务分析：杜邦拆解、毛利率与费用率趋势、简易 DCF。

读取 data/financials.csv 和 data/dcf_assumptions.csv，生成：
  output/haitian_analysis.xlsx   带公式的分析底稿（改假设后 Excel 会自动重算）
  output/charts/*.png            公众号配图

用法：
  python analysis.py

金额单位统一为亿元，股本为亿股，每股价值为元。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "output"

YEARS = list(range(2019, 2026))  # 分析期；2018 年只用来算 2019 年的平均余额
BASE_YEAR = 2025
FORECAST_YEARS = list(range(2026, 2031))

# 年报披露的同比增速和比率，用来勾稽检查 data/financials.csv 里的绝对数有没有录错。
# (年份, 指标类型, 科目, 披露值, 出处)
REPORTED_CHECKS = [
    (2019, "yoy", "revenue", 0.1622, "2019年报"),
    (2020, "yoy", "revenue", 0.1513, "2020年报"),
    (2021, "yoy", "revenue", 0.0971, "2021年报"),
    (2022, "yoy", "revenue", 0.0242, "2022年报"),
    (2023, "yoy", "revenue", -0.0410, "2023年报"),
    (2024, "yoy", "revenue", 0.0953, "2024年报"),
    (2025, "yoy", "revenue", 0.0732, "2025年报（对比重述后2024年）"),
    (2020, "yoy", "np_parent", 0.1961, "2020年报"),
    (2021, "yoy", "np_parent", 0.0418, "2021年报"),
    (2022, "yoy", "np_parent", -0.0709, "2022年报"),
    (2023, "yoy", "np_parent", -0.0921, "2023年报"),
    (2024, "yoy", "np_parent", 0.1275, "2024年报"),
    (2025, "yoy", "np_parent", 0.1095, "2025年报"),
    (2021, "yoy", "np_parent_deducted", 0.0409, "2021年报"),
    (2022, "yoy", "np_parent_deducted", -0.0722, "2022年报"),
    (2023, "yoy", "np_parent_deducted", -0.0957, "2023年报"),
    (2025, "yoy", "np_parent_deducted", 0.1281, "2025年报"),
    (2019, "yoy", "cogs", 0.1844, "2019年报"),
    (2021, "yoy", "cogs", 0.1636, "2021年报"),
    (2022, "yoy", "cogs", 0.0740, "2022年报"),
    (2023, "yoy", "cogs", -0.0269, "2023年报"),
    (2025, "yoy", "cogs", 0.0184, "媒体转述2025年报"),
    (2019, "yoy", "selling", -0.0327, "2019年报"),
    (2021, "yoy", "selling", -0.0063, "2021年报"),
    (2022, "yoy", "selling", 0.0156, "2022年报"),
    (2023, "yoy", "selling", -0.0525, "2023年报"),
    (2024, "yoy", "selling", 0.2473, "2024年报"),
    (2025, "yoy", "selling", 0.1870, "2025年报"),
    (2019, "yoy", "admin", 0.1806, "2019年报"),
    (2021, "yoy", "admin", 0.0903, "2021年报"),
    (2022, "yoy", "admin", 0.1211, "2022年报"),
    (2023, "yoy", "admin", 0.1900, "2023年报"),
    (2024, "yoy", "admin", 0.1226, "2024年报"),
    (2025, "yoy", "admin", 0.2073, "证券之星转述2025年报"),
    (2019, "yoy", "rnd", 0.1915, "2019年报"),
    (2022, "yoy", "rnd", -0.0267, "2022年报"),
    (2023, "yoy", "rnd", -0.0478, "2023年报"),
    (2024, "yoy", "rnd", 0.1735, "2024年报"),
    (2025, "yoy", "rnd", 0.0899, "媒体转述2025年报"),
    (2025, "yoy", "finance", -0.1043, "2025年报（负数费用的变动）"),
    (2019, "yoy", "ocf", 0.0953, "2019年报"),
    (2023, "yoy", "ocf", 0.9204, "2023年报"),
    (2025, "yoy", "ocf", 0.1324, "2025年报（对比重述后2024年）"),
    (2019, "yoy", "total_assets", 0.2289, "2019年报"),
    (2021, "yoy", "total_assets", 0.1288, "2021年报"),
    (2022, "yoy", "total_assets", 0.0216, "2022年报"),
    (2024, "yoy", "total_assets", 0.0634, "2024年报"),
    (2025, "yoy", "total_assets", 0.2770, "2025年报"),
    (2019, "yoy", "equity_parent", 0.1951, "2019年报"),
    (2020, "yoy", "equity_parent", 0.2103, "2020年报"),
    (2021, "yoy", "equity_parent", 0.1661, "2021年报"),
    (2024, "yoy", "equity_parent", 0.0829, "2024年报"),
    (2025, "yoy", "equity_parent", 0.3380, "2025年报"),
    (2020, "gross_margin", "cogs", 0.4217, "2020年报"),
    (2023, "gross_margin", "cogs", 0.3474, "研报转述2023年报"),
    (2025, "gross_margin", "cogs", 0.4022, "媒体转述2025年报"),
]
CHECK_TOLERANCE = 0.0015  # 0.15 个百分点：亿元精度的数字算出来的增速会有这么大的舍入误差


# ---------------------------------------------------------------- 数据读取


def load_financials(path: Path = DATA_DIR / "financials.csv") -> tuple[pd.DataFrame, pd.DataFrame]:
    """返回 (wide, long)。wide 以年份为行、科目代码为列，单位亿元（股本为亿股）。"""
    long = pd.read_csv(path, encoding="utf-8-sig", dtype={"年份": int})
    dup = long.duplicated(["年份", "科目代码"], keep=False)
    if dup.any():
        raise ValueError(f"financials.csv 有重复行：\n{long[dup]}")
    wide = long.pivot(index="年份", columns="科目代码", values="金额_元") / 1e8
    return wide.sort_index(), long


def load_assumptions(path: Path = DATA_DIR / "dcf_assumptions.csv") -> dict[str, float]:
    df = pd.read_csv(path, encoding="utf-8-sig")
    return dict(zip(df["参数代码"], df["取值"].astype(float)))


# ---------------------------------------------------------------- 利润率与费用率


def margin_table(w: pd.DataFrame) -> pd.DataFrame:
    rev = w["revenue"]
    t = pd.DataFrame(index=w.index)
    t["营业收入"] = rev
    t["营收同比"] = rev.pct_change()
    t["归母净利润"] = w["np_parent"]
    t["归母净利润同比"] = w["np_parent"].pct_change()
    t["毛利率"] = 1 - w["cogs"] / rev
    t["销售费用率"] = w["selling"] / rev
    t["管理费用率"] = w["admin"] / rev
    t["研发费用率"] = w["rnd"] / rev
    t["财务费用率"] = w["finance"] / rev
    t["期间费用率"] = t[["销售费用率", "管理费用率", "研发费用率", "财务费用率"]].sum(axis=1)
    t["归母净利率"] = w["np_parent"] / rev
    t["扣非净利率"] = w["np_parent_deducted"] / rev
    return t.loc[YEARS]


# ---------------------------------------------------------------- 杜邦拆解


def dupont_table(w: pd.DataFrame) -> pd.DataFrame:
    """三因子杜邦：ROE = 归母净利率 × 总资产周转率 × 权益乘数，资产和权益用期初期末平均。"""
    avg_ta = (w["total_assets"] + w["total_assets"].shift(1)) / 2
    avg_eq = (w["equity_parent"] + w["equity_parent"].shift(1)) / 2
    t = pd.DataFrame(index=w.index)
    t["归母净利润"] = w["np_parent"]
    t["营业收入"] = w["revenue"]
    t["平均总资产"] = avg_ta
    t["平均归母净资产"] = avg_eq
    t["归母净利率"] = w["np_parent"] / w["revenue"]
    t["总资产周转率"] = w["revenue"] / avg_ta
    t["权益乘数"] = avg_ta / avg_eq
    t["ROE"] = t["归母净利率"] * t["总资产周转率"] * t["权益乘数"]
    return t.loc[YEARS]


def roe_attribution(d: pd.DataFrame, start: int, end: int) -> pd.Series:
    """对数法把 ROE 的变化分摊到三个因子上，三项之和正好等于 ROE 变化。"""
    factors = ["归母净利率", "总资产周转率", "权益乘数"]
    total = d.at[end, "ROE"] - d.at[start, "ROE"]
    log_total = math.log(d.at[end, "ROE"] / d.at[start, "ROE"])
    out = {f: total * math.log(d.at[end, f] / d.at[start, f]) / log_total for f in factors}
    return pd.Series({"起点ROE": d.at[start, "ROE"], **out, "终点ROE": d.at[end, "ROE"]})


# ---------------------------------------------------------------- 现金流


def cashflow_table(w: pd.DataFrame, tax_rate: float) -> pd.DataFrame:
    t = pd.DataFrame(index=w.index)
    t["归母净利润"] = w["np_parent"]
    t["经营现金流"] = w["ocf"]
    t["资本开支"] = w["capex"]
    t["自由现金流"] = w["ocf"] - w["capex"]
    t["经营现金流/归母净利润"] = w["ocf"] / w["np_parent"]
    t["资本开支/营收"] = w["capex"] / w["revenue"]
    # 海天账上现金多，财务费用为负（利息收入>利息支出）。存款利息收入在经营现金流里，
    # DCF 又会单独加回净现金，所以先把税后利息净收益从 FCF 里剔掉，避免重复计算。
    t["税后利息净收益"] = -w["finance"] * (1 - tax_rate)
    t["调整后自由现金流"] = t["自由现金流"] - t["税后利息净收益"]
    t["调整后FCF率"] = t["调整后自由现金流"] / w["revenue"]
    return t.loc[YEARS]


# ---------------------------------------------------------------- DCF


@dataclass
class DCFResult:
    wacc: float
    terminal_g: float
    fcf_margin: float
    projection: pd.DataFrame  # 行：年份；列：营业收入、增速、FCF、折现期、折现因子、FCF现值
    pv_fcf: float
    terminal_value: float
    pv_terminal: float
    enterprise_value: float
    net_cash: float
    minority: float
    equity_value: float
    shares: float
    value_per_share_val_date: float  # 估值基准日（2025-12-31）每股价值
    dps_after_val_date: float  # 估值日后已派发的 2025 年末期红利（每股）
    value_per_share_price_date: float  # 滚动到股价日并扣除已派红利后的每股价值
    price: float

    @property
    def upside(self) -> float:
        return self.value_per_share_price_date / self.price - 1

    @property
    def terminal_share(self) -> float:
        return self.pv_terminal / self.enterprise_value


def wacc_from(a: dict[str, float]) -> float:
    # 海天有息负债极少（2025 年末短期借款 1.4 亿元），资本成本直接取股权成本。
    return a["rf"] + a["beta"] * a["erp"]


def balance_items(w: pd.DataFrame) -> dict[str, float]:
    y = w.loc[BASE_YEAR]
    net_cash = y["cash"] + y["trading_fin_assets"] - y["short_debt"]
    minority = y["total_assets"] - y["total_liabilities"] - y["equity_parent"]
    return {
        "net_cash": net_cash,
        "minority": minority,
        "shares": y["shares"],
        "dps": y["dividend_final"] / y["shares"],
    }


def run_dcf(
    w: pd.DataFrame,
    a: dict[str, float],
    wacc: float | None = None,
    terminal_g: float | None = None,
    fcf_margin: float | None = None,
) -> DCFResult:
    wacc = wacc_from(a) if wacc is None else wacc
    g = a["terminal_g"] if terminal_g is None else terminal_g
    m = a["fcf_margin"] if fcf_margin is None else fcf_margin
    if wacc <= g:
        raise ValueError(f"WACC({wacc:.2%}) 必须大于永续增长率({g:.2%})")

    growth = np.array([a[f"g_{y}"] for y in FORECAST_YEARS])
    revenue = w.at[BASE_YEAR, "revenue"] * np.cumprod(1 + growth)
    t = np.arange(1, len(FORECAST_YEARS) + 1)
    fcf = revenue * m
    disc = 1 / (1 + wacc) ** t
    proj = pd.DataFrame(
        {"营业收入": revenue, "增速": growth, "FCF": fcf, "折现期": t, "折现因子": disc, "FCF现值": fcf * disc},
        index=FORECAST_YEARS,
    )
    pv_fcf = proj["FCF现值"].sum()
    tv = fcf[-1] * (1 + g) / (wacc - g)
    pv_tv = tv * disc[-1]
    ev = pv_fcf + pv_tv

    b = balance_items(w)
    equity = ev + b["net_cash"] - b["minority"]
    v0 = equity / b["shares"]
    # 估值日是 2025-12-31，股价是 2026-11-02 的。把每股价值按资本成本滚动到股价日，
    # 再扣掉这期间已经派发的 2025 年末期红利，两边才可比。
    v_now = v0 * (1 + wacc) ** (a["days_to_price"] / 365) - b["dps"]

    return DCFResult(
        wacc=wacc,
        terminal_g=g,
        fcf_margin=m,
        projection=proj,
        pv_fcf=pv_fcf,
        terminal_value=tv,
        pv_terminal=pv_tv,
        enterprise_value=ev,
        net_cash=b["net_cash"],
        minority=b["minority"],
        equity_value=equity,
        shares=b["shares"],
        value_per_share_val_date=v0,
        dps_after_val_date=b["dps"],
        value_per_share_price_date=v_now,
        price=a["price"],
    )


SENS_WACC = [0.060, 0.065, 0.070, 0.075, 0.080, 0.085, 0.090]
SENS_G = [0.015, 0.020, 0.025, 0.030, 0.035]
SENS_MARGIN = [0.17, 0.18, 0.19, 0.20, 0.21, 0.22, 0.23]


def sensitivity_wacc_g(w, a) -> pd.DataFrame:
    return pd.DataFrame(
        [[run_dcf(w, a, wacc=r, terminal_g=g).value_per_share_price_date for g in SENS_G] for r in SENS_WACC],
        index=SENS_WACC,
        columns=SENS_G,
    )


def sensitivity_margin_wacc(w, a) -> pd.DataFrame:
    return pd.DataFrame(
        [[run_dcf(w, a, wacc=r, fcf_margin=m).value_per_share_price_date for r in SENS_WACC] for m in SENS_MARGIN],
        index=SENS_MARGIN,
        columns=SENS_WACC,
    )


def implied_terminal_g(w, a) -> float:
    """当前股价隐含的永续增长率（其他假设不变），二分法求解。"""
    wacc = wacc_from(a)
    lo, hi = -0.05, wacc - 0.001
    f = lambda g: run_dcf(w, a, terminal_g=g).value_per_share_price_date - a["price"]  # noqa: E731
    if f(lo) > 0 or f(hi) < 0:
        return float("nan")
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2


def implied_fcf_margin(w, a) -> float:
    """当前股价隐含的 FCF 率。每股价值对 FCF 率是线性的，两点定直线即可。"""
    v1 = run_dcf(w, a, fcf_margin=0.10).value_per_share_price_date
    v2 = run_dcf(w, a, fcf_margin=0.30).value_per_share_price_date
    return 0.10 + (a["price"] - v1) * (0.30 - 0.10) / (v2 - v1)


# ---------------------------------------------------------------- 勾稽检查


def reported_checks(w: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, kind, item, reported, src in REPORTED_CHECKS:
        if kind == "yoy":
            computed = w.at[year, item] / w.at[year - 1, item] - 1
            label = "同比"
        else:
            computed = 1 - w.at[year, "cogs"] / w.at[year, "revenue"]
            label = "毛利率"
        diff = computed - reported
        rows.append(
            {
                "年份": year,
                "科目": item,
                "指标": label,
                "按数据计算": computed,
                "年报披露": reported,
                "差异": diff,
                "结果": "通过" if abs(diff) <= CHECK_TOLERANCE else "待核对",
                "出处": src,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 入口


def main() -> None:
    from charts import make_all_charts
    from excel_export import write_workbook

    w, long = load_financials()
    a = load_assumptions()

    margins = margin_table(w)
    dupont = dupont_table(w)
    attrib = roe_attribution(dupont, YEARS[0], BASE_YEAR)
    cash = cashflow_table(w, a["tax_rate"])
    dcf = run_dcf(w, a)
    sens_wg = sensitivity_wacc_g(w, a)
    sens_mw = sensitivity_margin_wacc(w, a)
    checks = reported_checks(w)

    OUT_DIR.mkdir(exist_ok=True)
    xlsx = write_workbook(OUT_DIR / "haitian_analysis.xlsx", w, long, a, checks)
    charts = make_all_charts(OUT_DIR / "charts", margins, dupont, attrib, cash, dcf, sens_wg)

    pd.set_option("display.width", 160)
    pd.set_option("display.float_format", lambda v: f"{v:,.4f}")
    print("== 利润率与费用率 ==")
    print(margins.T)
    print("\n== 杜邦拆解 ==")
    print(dupont.T)
    print(f"\n== ROE 归因 {YEARS[0]}→{BASE_YEAR} ==")
    print(attrib)
    print("\n== 现金流 ==")
    print(cash.T)
    print("\n== DCF ==")
    print(dcf.projection)
    print(
        f"WACC {dcf.wacc:.2%}  g {dcf.terminal_g:.2%}  FCF率 {dcf.fcf_margin:.0%}\n"
        f"预测期现值 {dcf.pv_fcf:,.1f}  终值现值 {dcf.pv_terminal:,.1f}  企业价值 {dcf.enterprise_value:,.1f}"
        f"（终值占 {dcf.terminal_share:.0%}）\n"
        f"净现金 {dcf.net_cash:,.1f}  少数股东权益 {dcf.minority:,.1f}  股权价值 {dcf.equity_value:,.1f} 亿元\n"
        f"每股价值：估值日 {dcf.value_per_share_val_date:.2f} 元 → 股价日 {dcf.value_per_share_price_date:.2f} 元"
        f"（已扣末期红利 {dcf.dps_after_val_date:.2f}）  股价 {dcf.price:.2f}  空间 {dcf.upside:+.1%}"
    )
    print(f"股价隐含永续增长率 {implied_terminal_g(w, a):.2%}，隐含 FCF 率 {implied_fcf_margin(w, a):.1%}")
    print("\n== 敏感性：WACC × 永续增长率（每股，元） ==")
    print(sens_wg.round(2))
    print("\n== 勾稽检查 ==")
    bad = checks[checks["结果"] != "通过"]
    print(f"{len(checks) - len(bad)}/{len(checks)} 项通过")
    if len(bad):
        print(bad.to_string(index=False))
    print(f"\n已生成 {xlsx.relative_to(ROOT)} 和 {len(charts)} 张图（{(OUT_DIR / 'charts').relative_to(ROOT)}/）")


if __name__ == "__main__":
    main()
