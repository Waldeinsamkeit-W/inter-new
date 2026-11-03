"""生成带公式的 Excel 底稿。

除了“数据”和“数据来源”两张录入表，其余各表全部是引用“数据”表的公式：改数据或假设后，
Excel 会自动重算。颜色约定：蓝字=录入值，黑字=公式，绿字=跨表引用，黄底=关键假设。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from analysis import (
    BASE_YEAR,
    CHECK_TOLERANCE,
    FORECAST_YEARS,
    SENS_G,
    SENS_MARGIN,
    SENS_WACC,
    YEARS,
)

FONT = "Arial"
BLUE, BLACK, GREEN, GREY = "0000FF", "000000", "008000", "666666"
YELLOW_FILL = PatternFill("solid", fgColor="FFFF00")
HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
SECTION_FILL = PatternFill("solid", fgColor="F2F2F2")
QUALITY_FILL = {"B": PatternFill("solid", fgColor="DDEBF7"), "C": PatternFill("solid", fgColor="FCE4D6")}
THIN = Side(style="thin", color="BFBFBF")
THICK = Side(style="medium", color="000000")

NUM = '#,##0.00;(#,##0.00);"-"'
PCT = '0.0%;(0.0%);"-"'
PCT2 = '0.00%;(0.00%);"-"'
MULT = '0.00"x"'
YUAN = "0.00"

DATA_ITEMS = [
    ("revenue", "营业收入"),
    ("cogs", "营业成本"),
    ("selling", "销售费用"),
    ("admin", "管理费用"),
    ("rnd", "研发费用"),
    ("finance", "财务费用（负数=净利息收入）"),
    ("np_parent", "归母净利润"),
    ("np_parent_deducted", "扣非归母净利润"),
    ("ocf", "经营活动现金流量净额"),
    ("capex", "购建固定资产等长期资产支付的现金"),
    ("total_assets", "总资产"),
    ("equity_parent", "归母净资产"),
    ("total_liabilities", "负债合计"),
    ("cash", "货币资金"),
    ("trading_fin_assets", "交易性金融资产"),
    ("short_debt", "短期借款"),
    ("dividend_final", "2025年度末期现金红利"),
    ("shares", "参与分配股本（亿股）"),
]
DATA_FIRST_ROW = 5
DATA_ROW = {code: DATA_FIRST_ROW + i for i, (code, _) in enumerate(DATA_ITEMS)}
DATA_YEARS = list(range(2018, BASE_YEAR + 1))
DATA_COL = {y: get_column_letter(3 + i) for i, y in enumerate(DATA_YEARS)}  # 2018 -> C

# 分析表统一把 2019–2025 放在 B..H 列
ACOL = {y: get_column_letter(2 + i) for i, y in enumerate(YEARS)}


def d(code: str, year: int, absolute: bool = False) -> str:
    """“数据”表某科目某年的单元格引用。"""
    col, row = DATA_COL[year], DATA_ROW[code]
    return f"数据!${col}${row}" if absolute else f"数据!{col}{row}"


def _font(color=BLACK, bold=False, size=10, italic=False):
    return Font(name=FONT, color=color, bold=bold, size=size, italic=italic)


def _set(ws, ref, value, fmt=None, color=BLACK, bold=False, fill=None, align=None):
    c = ws[ref]
    c.value = value
    c.font = _font(color, bold)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if align:
        c.alignment = Alignment(horizontal=align, vertical="center")
    return c


def _title(ws, text, note=None):
    ws["A1"] = text
    ws["A1"].font = _font(bold=True, size=14)
    if note:
        ws["A2"] = note
        ws["A2"].font = _font(GREY, size=9)


def _header(ws, row, labels, start_col=1):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=lab)
        c.font = _font(bold=True)
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = Border(bottom=THIN)


def _section(ws, row, text, ncols):
    for col in range(1, ncols + 1):
        ws.cell(row=row, column=col).fill = SECTION_FILL
    c = ws.cell(row=row, column=1, value=text)
    c.font = _font(bold=True)


def _widths(ws, widths: dict[str, float]):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


# ---------------------------------------------------------------- 各表


def _sheet_readme(wb, a):
    ws = wb.active
    ws.title = "说明"
    lines = [
        ("海天味业（603288）财务分析底稿", True),
        ("", False),
        ("各表内容", True),
        ("数据：2018–2025 年财务数据（亿元），每个单元格批注里写了来源链接和取数质量。改数字只改这张表。", False),
        ("数据来源：逐条列出原始金额（元）、来源链接和备注，方便对照年报核对。", False),
        ("利润率与费用率：毛利率、四项费用率、净利率，公式引用“数据”表。", False),
        ("杜邦拆解：ROE = 归母净利率 × 总资产周转率 × 权益乘数（资产、净资产取期初期末平均），并做 2019→2025 归因。", False),
        ("现金流：经营现金流、资本开支、自由现金流，以及 DCF 用的调整后 FCF 率。", False),
        ("DCF：两阶段 DCF。黄底蓝字是可以改的假设，改完自动重算。", False),
        ("敏感性：WACC × 永续增长率、FCF 率 × WACC 两张表，每格都是独立公式。", False),
        ("勾稽检查：用数据算出的同比增速/毛利率 vs 年报披露值，差异超过容差的标“待核对”。", False),
        ("", False),
        ("颜色约定", True),
        ("蓝字 = 录入值或假设；黑字 = 公式；绿字 = 跨表引用；黄底 = 关键假设。", False),
        ("“数据”表底色：无底色 = A（年报/审计报告原文，精确到分）；浅蓝 = B（媒体或研报转述年报，亿元精度）；浅橙 = C（由其他已披露数推算）。", False),
        ("", False),
        ("口径说明", True),
        ("1. 2020 年起执行新收入准则，运费从销售费用调入营业成本，2019 年的毛利率、销售费用率与之后不完全可比。", False),
        ("2. 2024 年用原报数；2025 年报因同一控制下合并海天创新重述了 2024 年数（营收差 0.035 亿元，影响可忽略）。", False),
        ("3. 杜邦拆解用归母净利润和归母净资产；年报披露的加权平均 ROE 按股本变动时点加权，与这里的简单平均略有差异。", False),
        (f"4. DCF 估值基准日 {BASE_YEAR}-12-31；与 2026-11-02 股价比较时，把每股价值按 WACC 滚动到股价日，并扣除期间已派发的 2025 年末期红利。", False),
        ("5. 海天账上现金多，财务费用为负。存款利息在经营现金流里，DCF 又单独加回净现金，所以先从 FCF 里剔除税后利息收入，避免重复计算。", False),
        ("6. 净现金只算货币资金 + 交易性金融资产 − 短期借款；其他非流动资产中可能还有大额存单，未计入，属于保守处理。", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=text)
        c.font = _font(bold=bold, size=14 if i == 1 else 10)
    ws.column_dimensions["A"].width = 130


def _sheet_data(wb, w: pd.DataFrame, long: pd.DataFrame):
    ws = wb.create_sheet("数据")
    _title(ws, "海天味业财务数据（亿元）", "蓝字=录入值；批注=来源与取数质量；底色：浅蓝=B 二手转述，浅橙=C 推算，无底色=A 年报原文")
    _header(ws, 4, ["科目代码", "科目"] + [str(y) for y in DATA_YEARS])
    meta = long.set_index(["年份", "科目代码"])
    for code, name in DATA_ITEMS:
        r = DATA_ROW[code]
        _set(ws, f"A{r}", code, color=GREY)
        _set(ws, f"B{r}", name)
        for y in DATA_YEARS:
            if (y, code) not in meta.index:
                continue
            m = meta.loc[(y, code)]
            ref = f"{DATA_COL[y]}{r}"
            fmt = "0.0000" if code == "shares" else NUM
            c = _set(ws, ref, float(m["金额_元"]) / 1e8, fmt, color=BLUE, fill=QUALITY_FILL.get(m["质量"]))
            c.comment = Comment(f"质量 {m['质量']}｜{m['备注']}\n{m['来源']}", "数据整理", width=420, height=110)
    ws.freeze_panes = "C5"
    _widths(ws, {"A": 20, "B": 32, **{DATA_COL[y]: 12 for y in DATA_YEARS}})


def _sheet_sources(wb, long: pd.DataFrame):
    ws = wb.create_sheet("数据来源")
    _title(ws, "数据来源明细", "质量：A=年报/审计报告原文（精确到分）；B=媒体或研报转述年报（亿元精度）；C=由其他已披露数推算")
    cols = ["年份", "科目代码", "科目", "金额（元）", "质量", "来源", "备注"]
    _header(ws, 4, cols)
    for i, row in enumerate(long.itertuples(index=False), start=5):
        _set(ws, f"A{i}", str(row.年份))
        _set(ws, f"B{i}", row.科目代码, color=GREY)
        _set(ws, f"C{i}", row.科目)
        _set(ws, f"D{i}", float(row.金额_元), "#,##0.00", color=BLUE)
        _set(ws, f"E{i}", row.质量, align="center", fill=QUALITY_FILL.get(row.质量))
        c = _set(ws, f"F{i}", row.来源, color="0563C1")
        c.hyperlink = row.来源
        _set(ws, f"G{i}", row.备注)
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = f"A4:G{4 + len(long)}"
    _widths(ws, {"A": 7, "B": 18, "C": 22, "D": 20, "E": 6, "F": 60, "G": 80})


def _sheet_margins(wb, w):
    ws = wb.create_sheet("利润率与费用率")
    _title(ws, "利润率与费用率", "公式引用“数据”表；2019 年为旧收入准则口径（运费在销售费用）")
    _header(ws, 3, ["指标"] + [str(y) for y in YEARS])
    rows = [
        ("营业收入（亿元）", lambda y: f"={d('revenue', y)}", NUM, GREEN),
        ("营收同比", lambda y: f"={d('revenue', y)}/{d('revenue', y - 1)}-1", PCT, BLACK),
        ("归母净利润（亿元）", lambda y: f"={d('np_parent', y)}", NUM, GREEN),
        (
            "归母净利润同比",
            lambda y: f"={d('np_parent', y)}/{d('np_parent', y - 1)}-1" if pd.notna(w.at[y - 1, "np_parent"]) else "—",
            PCT,
            BLACK,
        ),
        ("毛利率", lambda y: f"=1-{d('cogs', y)}/{d('revenue', y)}", PCT, BLACK),
        ("销售费用率", lambda y: f"={d('selling', y)}/{d('revenue', y)}", PCT2, BLACK),
        ("管理费用率", lambda y: f"={d('admin', y)}/{d('revenue', y)}", PCT2, BLACK),
        ("研发费用率", lambda y: f"={d('rnd', y)}/{d('revenue', y)}", PCT2, BLACK),
        ("财务费用率", lambda y: f"={d('finance', y)}/{d('revenue', y)}", PCT2, BLACK),
        ("期间费用率（四项合计）", lambda y: f"=SUM({ACOL[y]}9:{ACOL[y]}12)", PCT2, BLACK),
        ("归母净利率", lambda y: f"={ACOL[y]}6/{ACOL[y]}4", PCT, BLACK),
        ("扣非净利率", lambda y: f"={d('np_parent_deducted', y)}/{ACOL[y]}4", PCT, BLACK),
    ]
    for i, (label, f, fmt, color) in enumerate(rows, start=4):
        _set(ws, f"A{i}", label, bold=label in ("毛利率", "期间费用率（四项合计）", "归母净利率"))
        for y in YEARS:
            v = f(y)
            _set(ws, f"{ACOL[y]}{i}", v, fmt if v != "—" else None, color=color, align="right" if v == "—" else None)
    ws.freeze_panes = "B4"
    _widths(ws, {"A": 26, **{ACOL[y]: 11 for y in YEARS}})


def _sheet_dupont(wb):
    ws = wb.create_sheet("杜邦拆解")
    _title(ws, "杜邦拆解", "ROE = 归母净利率 × 总资产周转率 × 权益乘数；资产与净资产取期初期末平均")
    _header(ws, 3, ["指标"] + [str(y) for y in YEARS])
    rows = [
        ("归母净利润（亿元）", lambda y: f"={d('np_parent', y)}", NUM, GREEN),
        ("营业收入（亿元）", lambda y: f"={d('revenue', y)}", NUM, GREEN),
        ("平均总资产（亿元）", lambda y: f"=({d('total_assets', y)}+{d('total_assets', y - 1)})/2", NUM, BLACK),
        ("平均归母净资产（亿元）", lambda y: f"=({d('equity_parent', y)}+{d('equity_parent', y - 1)})/2", NUM, BLACK),
        ("① 归母净利率", lambda y: f"={ACOL[y]}4/{ACOL[y]}5", PCT, BLACK),
        ("② 总资产周转率（次）", lambda y: f"={ACOL[y]}5/{ACOL[y]}6", "0.00", BLACK),
        ("③ 权益乘数", lambda y: f"={ACOL[y]}6/{ACOL[y]}7", MULT, BLACK),
        ("ROE（①×②×③）", lambda y: f"={ACOL[y]}8*{ACOL[y]}9*{ACOL[y]}10", PCT, BLACK),
        ("ROE（直接：净利润÷平均净资产）", lambda y: f"={ACOL[y]}4/{ACOL[y]}7", PCT, BLACK),
        ("校验差异", lambda y: f"={ACOL[y]}11-{ACOL[y]}12", "0.0000", BLACK),
    ]
    for i, (label, f, fmt, color) in enumerate(rows, start=4):
        _set(ws, f"A{i}", label, bold=label.startswith("ROE（①"))
        for y in YEARS:
            _set(ws, f"{ACOL[y]}{i}", f(y), fmt, color=color)

    s, e = ACOL[YEARS[0]], ACOL[BASE_YEAR]
    _section(ws, 15, f"ROE 变化归因：{YEARS[0]} → {BASE_YEAR}（对数法，三项贡献之和 = ROE 变化）", 8)
    _header(ws, 16, ["项目", "百分点"])
    attr_rows = [
        (f"{YEARS[0]} 年 ROE", f"={s}11"),
        ("归母净利率的贡献", f"=(${e}$11-${s}$11)*LN({e}8/{s}8)/LN(${e}$11/${s}$11)"),
        ("总资产周转率的贡献", f"=(${e}$11-${s}$11)*LN({e}9/{s}9)/LN(${e}$11/${s}$11)"),
        ("权益乘数的贡献", f"=(${e}$11-${s}$11)*LN({e}10/{s}10)/LN(${e}$11/${s}$11)"),
        (f"{BASE_YEAR} 年 ROE", f"={e}11"),
        ("校验（应为 0）", "=B17+SUM(B18:B20)-B21"),
        ("总资产周转率贡献占 ROE 降幅比例", "=B19/(B21-B17)"),
    ]
    for i, (label, f) in enumerate(attr_rows, start=17):
        _set(ws, f"A{i}", label)
        _set(ws, f"B{i}", f, "0.0000" if "校验" in label else PCT)
    ws.freeze_panes = "B4"
    _widths(ws, {"A": 32, **{ACOL[y]: 11 for y in YEARS}})


def _sheet_cash(wb, w):
    ws = wb.create_sheet("现金流")
    _title(ws, "现金流与自由现金流", "自由现金流 = 经营现金流 − 购建长期资产支付的现金；2020 年资本开支为推算值（可信度低）")
    _header(ws, 3, ["指标"] + [str(y) for y in YEARS])
    has_capex = {y: pd.notna(w.at[y, "capex"]) for y in YEARS}

    def need_capex(fn):
        return lambda y: fn(y) if has_capex[y] else "—"

    rows = [
        ("归母净利润（亿元）", lambda y: f"={d('np_parent', y)}", NUM, GREEN),
        ("经营现金流（亿元）", lambda y: f"={d('ocf', y)}", NUM, GREEN),
        ("资本开支（亿元）", need_capex(lambda y: f"={d('capex', y)}"), NUM, GREEN),
        ("自由现金流（亿元）", need_capex(lambda y: f"={ACOL[y]}5-{ACOL[y]}6"), NUM, BLACK),
        ("经营现金流 ÷ 归母净利润", lambda y: f"={ACOL[y]}5/{ACOL[y]}4", MULT, BLACK),
        ("资本开支 ÷ 营收", need_capex(lambda y: f"={ACOL[y]}6/{d('revenue', y)}"), PCT, BLACK),
        ("税后利息净收益（亿元）", lambda y: f"=-{d('finance', y)}*(1-DCF!$B$11)", NUM, BLACK),
        ("调整后自由现金流（亿元）", need_capex(lambda y: f"={ACOL[y]}7-{ACOL[y]}10"), NUM, BLACK),
        ("调整后 FCF 率（占营收）", need_capex(lambda y: f"={ACOL[y]}11/{d('revenue', y)}"), PCT, BLACK),
    ]
    for i, (label, f, fmt, color) in enumerate(rows, start=4):
        _set(ws, f"A{i}", label, bold=label.startswith("调整后 FCF"))
        for y in YEARS:
            v = f(y)
            _set(ws, f"{ACOL[y]}{i}", v, fmt if v != "—" else None, color=color, align="right" if v == "—" else None)
    _set(ws, "A14", "2023–2025 年调整后 FCF 率均值", bold=True)
    _set(ws, "B14", f"=AVERAGE({ACOL[2023]}12:{ACOL[2025]}12)", PCT)
    _set(ws, "A15", "注：存款利息在经营现金流里，DCF 又单独加回净现金，所以 DCF 用的是剔除税后利息收入后的 FCF 率。", color=GREY)
    ws.freeze_panes = "B4"
    _widths(ws, {"A": 30, **{ACOL[y]: 11 for y in YEARS}})


def _sheet_dcf(wb, a):
    ws = wb.create_sheet("DCF")
    _title(ws, "简易两阶段 DCF", f"估值基准日 {BASE_YEAR}-12-31；黄底蓝字为可改假设，改完自动重算；单位：亿元，每股为元")
    _section(ws, 4, "一、假设", 7)
    assumptions = [
        (5, "无风险利率", a["rf"], PCT2, "参考中国 10 年期国债收益率；发文前按估值日更新", False),
        (6, "Beta", a["beta"], "0.00", "假设值：必需消费龙头常见 0.7–0.9", False),
        (7, "股权风险溢价", a["erp"], PCT2, "假设值：A 股常用 6%–7%", False),
        (9, "永续增长率", a["terminal_g"], PCT2, "假设值", True),
        (10, "自由现金流率（占营收）", a["fcf_margin"], PCT, "参考 2023–2025 年调整后 FCF 率均值（见 B44）", True),
        (11, "利息收入税率", a["tax_rate"], PCT, "只用于从 FCF 中剔除税后利息收入", False),
        (12, "A 股股价（元）", a["price"], YUAN, "2026-11-02 收盘价（雪球）", False),
        (13, "估值基准日至股价日天数", a["days_to_price"], "0", "2025-12-31 至 2026-11-02", False),
    ]
    for r, label, v, fmt, note, key in assumptions:
        _set(ws, f"A{r}", label)
        _set(ws, f"B{r}", v, fmt, color=BLUE, fill=YELLOW_FILL if key else None)
        _set(ws, f"C{r}", note, color=GREY)
    _set(ws, "A8", "WACC（有息负债可忽略，取股权成本）", bold=True)
    _set(ws, "B8", "=B5+B6*B7", PCT2)
    _set(ws, "C8", "公式：无风险利率 + Beta × 股权风险溢价", color=GREY)

    _section(ws, 15, "二、预测", 7)
    fcols = {y: get_column_letter(3 + i) for i, y in enumerate(FORECAST_YEARS)}  # 2026 -> C
    first, last = fcols[FORECAST_YEARS[0]], fcols[FORECAST_YEARS[-1]]
    _header(ws, 16, ["项目", f"{BASE_YEAR}A"] + [f"{y}E" for y in FORECAST_YEARS])
    _set(ws, "A17", "收入增速")
    _set(ws, "A18", "营业收入")
    _set(ws, "A19", "自由现金流")
    _set(ws, "A20", "折现期（年）")
    _set(ws, "A21", "折现因子")
    _set(ws, "A22", "自由现金流现值")
    _set(ws, "B18", f"={d('revenue', BASE_YEAR)}", NUM, color=GREEN)
    prev = "B"
    for i, y in enumerate(FORECAST_YEARS, start=1):
        c = fcols[y]
        _set(ws, f"{c}17", a[f"g_{y}"], PCT, color=BLUE, fill=YELLOW_FILL)
        _set(ws, f"{c}18", f"={prev}18*(1+{c}17)", NUM)
        _set(ws, f"{c}19", f"={c}18*$B$10", NUM)
        _set(ws, f"{c}20", i, "0")
        _set(ws, f"{c}21", f"=1/(1+$B$8)^{c}20", "0.0000")
        _set(ws, f"{c}22", f"={c}19*{c}21", NUM)
        prev = c

    _section(ws, 24, "三、估值", 7)
    j = BASE_YEAR
    val_rows = [
        (25, "预测期自由现金流现值合计", f"=SUM({first}22:{last}22)", NUM, BLACK),
        (26, f"终值（{FORECAST_YEARS[-1]} 年末）", f"={last}19*(1+B9)/(B8-B9)", NUM, BLACK),
        (27, "终值现值", f"=B26*{last}21", NUM, BLACK),
        (28, "企业价值", "=B25+B27", NUM, BLACK),
        (29, "货币资金", f"={d('cash', j)}", NUM, GREEN),
        (30, "交易性金融资产", f"={d('trading_fin_assets', j)}", NUM, GREEN),
        (31, "短期借款", f"={d('short_debt', j)}", NUM, GREEN),
        (32, "净现金", "=B29+B30-B31", NUM, BLACK),
        (33, "少数股东权益（总资产−负债−归母净资产）", f"={d('total_assets', j)}-{d('total_liabilities', j)}-{d('equity_parent', j)}", NUM, BLACK),
        (34, "股权价值", "=B28+B32-B33", NUM, BLACK),
        (35, "参与分配股本（亿股）", f"={d('shares', j)}", "0.0000", GREEN),
        (36, f"每股价值（{BASE_YEAR}-12-31，元）", "=B34/B35", YUAN, BLACK),
        (37, "估值日后已派 2025 年末期红利（元/股）", f"={d('dividend_final', j)}/{d('shares', j)}", YUAN, BLACK),
        (38, "每股价值（滚动至股价日、扣除已派红利，元）", "=B36*(1+B8)^(B13/365)-B37", YUAN, BLACK),
        (39, "当前股价（元）", "=B12", YUAN, BLACK),
        (40, "相对现价空间", "=B38/B39-1", PCT, BLACK),
        (41, "终值占企业价值", "=B27/B28", PCT, BLACK),
    ]
    for r, label, f, fmt, color in val_rows:
        _set(ws, f"A{r}", label, bold=r in (28, 34, 38, 40))
        _set(ws, f"B{r}", f, fmt, color=color, bold=r in (38, 40))

    _section(ws, 43, "四、历史参考", 7)
    _set(ws, "A44", "2023–2025 年调整后 FCF 率均值")
    _set(ws, "B44", "=现金流!B14", PCT, color=GREEN)
    ws.freeze_panes = "A4"
    _widths(ws, {"A": 42, "B": 13, "C": 13, "D": 13, "E": 13, "F": 13, "G": 13})
    return fcols


def _sheet_sensitivity(wb, fcols, price: float, base_wacc: float, base_g: float, base_m: float):
    ws = wb.create_sheet("敏感性")
    _title(ws, "DCF 敏感性：每股价值（元，滚动至股价日、扣除已派红利）", "每格是独立公式，引用“DCF”表的预测和资产负债项；蓝字为测试取值")
    first, last = fcols[FORECAST_YEARS[0]], fcols[FORECAST_YEARS[-1]]
    fcf = f"DCF!${first}$19:${last}$19"
    rev = f"DCF!${first}$18:${last}$18"
    per = f"DCF!${first}$20:${last}$20"
    n = f"DCF!${last}$20"
    tail = "+DCF!$B$32-DCF!$B$33)/DCF!$B$35)"
    roll = "*(1+{w})^(DCF!$B$13/365)-DCF!$B$37"
    border = Border(left=THICK, right=THICK, top=THICK, bottom=THICK)

    def color_scale(rng):
        ws.conditional_formatting.add(
            rng,
            ColorScaleRule(
                start_type="min", start_color="F2A3A2", mid_type="num", mid_value=price, mid_color="F0EFEC",
                end_type="max", end_color="86B6EF",
            ),
        )

    # 表一：WACC × 永续增长率
    _section(ws, 4, "表一：WACC（行）× 永续增长率（列）；FCF 率取 DCF 表假设", 8)
    _set(ws, "B5", "WACC \\ g", bold=True, fill=HEADER_FILL, align="center")
    for j, g in enumerate(SENS_G):
        _set(ws, f"{get_column_letter(3 + j)}5", g, PCT, color=BLUE, bold=True, fill=HEADER_FILL, align="center")
    for i, wv in enumerate(SENS_WACC):
        r = 6 + i
        _set(ws, f"B{r}", wv, PCT, color=BLUE, bold=True, fill=HEADER_FILL, align="center")
        for j, g in enumerate(SENS_G):
            c = get_column_letter(3 + j)
            w_, g_ = f"$B{r}", f"{c}$5"
            f = (
                f"=((SUMPRODUCT({fcf},1/(1+{w_})^{per})"
                f"+DCF!${last}$19*(1+{g_})/({w_}-{g_})/(1+{w_})^{n}{tail}{roll.format(w=w_)}"
            )
            cell = _set(ws, f"{c}{r}", f, YUAN, align="center")
            if abs(wv - base_wacc) < 1e-9 and abs(g - base_g) < 1e-9:
                cell.border, cell.font = border, _font(bold=True)
    color_scale(f"C6:{get_column_letter(2 + len(SENS_G))}{5 + len(SENS_WACC)}")

    # 表二：FCF 率 × WACC
    top = 8 + len(SENS_WACC)
    _section(ws, top, "表二：FCF 率（行）× WACC（列）；永续增长率取 DCF 表假设", 10)
    _set(ws, f"B{top + 1}", "FCF率 \\ WACC", bold=True, fill=HEADER_FILL, align="center")
    for j, wv in enumerate(SENS_WACC):
        _set(ws, f"{get_column_letter(3 + j)}{top + 1}", wv, PCT, color=BLUE, bold=True, fill=HEADER_FILL, align="center")
    for i, m in enumerate(SENS_MARGIN):
        r = top + 2 + i
        _set(ws, f"B{r}", m, PCT, color=BLUE, bold=True, fill=HEADER_FILL, align="center")
        for j, wv in enumerate(SENS_WACC):
            c = get_column_letter(3 + j)
            w_, m_ = f"{c}${top + 1}", f"$B{r}"
            f = (
                f"=((SUMPRODUCT({rev}*{m_},1/(1+{w_})^{per})"
                f"+DCF!${last}$18*{m_}*(1+DCF!$B$9)/({w_}-DCF!$B$9)/(1+{w_})^{n}{tail}{roll.format(w=w_)}"
            )
            cell = _set(ws, f"{c}{r}", f, YUAN, align="center")
            if abs(wv - base_wacc) < 1e-9 and abs(m - base_m) < 1e-9:
                cell.border, cell.font = border, _font(bold=True)
    color_scale(f"C{top + 2}:{get_column_letter(2 + len(SENS_WACC))}{top + 1 + len(SENS_MARGIN)}")
    _set(ws, f"A{top + 3 + len(SENS_MARGIN)}", f"底色：以现价 {price:.2f} 元为中点，蓝=高于现价，红=低于现价；粗框为基准情形。", color=GREY)
    _widths(ws, {"A": 3, "B": 14, **{get_column_letter(3 + j): 10 for j in range(len(SENS_WACC))}})


def _sheet_checks(wb, checks: pd.DataFrame):
    ws = wb.create_sheet("勾稽检查")
    _title(ws, "勾稽检查：用录入数据算出的增速/毛利率 vs 年报披露值", "差异超过容差标“待核对”；容差可改（B3）")
    _set(ws, "A3", "容差")
    _set(ws, "B3", CHECK_TOLERANCE, PCT2, color=BLUE, fill=YELLOW_FILL)
    _header(ws, 5, ["年份", "科目", "指标", "按数据计算", "年报披露", "差异", "结果", "出处"])
    for i, row in enumerate(checks.itertuples(index=False), start=6):
        y, item = int(row.年份), row.科目
        if row.指标 == "同比":
            f = f"={d(item, y)}/{d(item, y - 1)}-1"
        else:
            f = f"=1-{d('cogs', y)}/{d('revenue', y)}"
        _set(ws, f"A{i}", str(y))
        _set(ws, f"B{i}", item, color=GREY)
        _set(ws, f"C{i}", row.指标)
        _set(ws, f"D{i}", f, PCT2)
        _set(ws, f"E{i}", float(row.年报披露), PCT2, color=BLUE)
        _set(ws, f"F{i}", f"=D{i}-E{i}", PCT2)
        _set(ws, f"G{i}", f'=IF(ABS(F{i})<=$B$3,"通过","待核对")', align="center")
        _set(ws, f"H{i}", row.出处, color=GREY)
    last = 5 + len(checks)
    _set(ws, f"A{last + 2}", "通过项数", bold=True)
    _set(ws, f"B{last + 2}", f'=COUNTIF(G6:G{last},"通过")&"/"&COUNTA(G6:G{last})', bold=True)
    ws.freeze_panes = "A6"
    _widths(ws, {"A": 8, "B": 20, "C": 8, "D": 12, "E": 12, "F": 10, "G": 9, "H": 30})


# ---------------------------------------------------------------- 入口


def write_workbook(path: Path, w: pd.DataFrame, long: pd.DataFrame, a: dict, checks: pd.DataFrame) -> Path:
    from analysis import wacc_from

    wb = Workbook()
    _sheet_readme(wb, a)
    _sheet_data(wb, w, long)
    _sheet_sources(wb, long)
    _sheet_margins(wb, w)
    _sheet_dupont(wb)
    _sheet_cash(wb, w)
    fcols = _sheet_dcf(wb, a)
    _sheet_sensitivity(wb, fcols, a["price"], wacc_from(a), a["terminal_g"], a["fcf_margin"])
    _sheet_checks(wb, checks)
    wb.calculation.fullCalcOnLoad = True  # openpyxl 不写缓存值，让 Excel/WPS 打开时全表重算
    wb.save(path)
    return path
