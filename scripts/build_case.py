#!/usr/bin/env python3
"""
生成「青禾饮品（虚构公司）」实战案例的全部练习材料。

这是案例数据的唯一来源（single source of truth）：
  - practice/青禾饮品_原始数据.csv      故意保留"脏数据"特征，用于练习数据清洗
  - practice/青禾饮品_参考答案.xlsx    完整的三表模型 + DCF 估值（全部为公式）
  - practice/青禾饮品_练习模板.xlsx    同样的结构，预测期留空（黄色单元格）让你自己填
  - js/case-data.js                    网站"实战案例"页面和工具使用的数据

用法：
    python3 scripts/build_case.py

改动假设后重新运行即可，网站和 Excel 会保持一致。
"""
import csv
import json
import os
import sys
from copy import deepcopy

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PRACTICE = os.path.join(ROOT, "practice")
OUT_JS = os.path.join(ROOT, "js", "case-data.js")

COMPANY = "青禾饮品"
SHARES = 500.0          # 总股本，百万股（5 亿股）
PRICE = 9.00            # 当前股价，元/股（虚构）

HIST = [2023, 2024, 2025]
FC = [2026, 2027, 2028, 2029, 2030]
YEARS = HIST + FC

# ---------------------------------------------------------------------------
# 1. 历史数据（虚构，单位：百万元，除特别注明）
# ---------------------------------------------------------------------------
opening = dict(  # 2022-12-31 资产负债表
    cash=300.0, ar=200.0, inv=220.0,
    fa=800.0, cip=80.0, intang=120.0, other=100.0,
    ap=200.0, st_debt=120.0, cur_ltd=30.0, lt_debt=350.0,
    share_cap=500.0, apic=300.0, surplus=100.0, undist=220.0,
)

hist_drv = {
    2023: dict(vol=4000, price=50.0, cogs_pct=0.55, sell_pct=0.20, mgmt=90.0, rnd=40.0, biz_tax=30.0,
               capex=150.0, dep=92.0, amort=3.0, dso=40, dio=75, dpo=70,
               borrow=100.0, repay=120.0, nonop_in=0.0, nonop_out=0.0,
               cip=95.0, st_debt=110.0, cur_ltd=30.0),
    2024: dict(vol=4500, price=51.0, cogs_pct=0.54, sell_pct=0.205, mgmt=100.0, rnd=46.0, biz_tax=33.0,
               capex=161.0, dep=97.0, amort=3.0, dso=41, dio=74, dpo=70,
               borrow=80.0, repay=110.0, nonop_in=30.0, nonop_out=0.0,
               cip=106.0, st_debt=100.0, cur_ltd=30.0),
    2025: dict(vol=5000, price=52.0, cogs_pct=0.535, sell_pct=0.202, mgmt=108.0, rnd=50.0, biz_tax=37.0,
               capex=169.0, dep=103.0, amort=3.0, dso=40, dio=73, dpo=71,
               borrow=90.0, repay=120.0, nonop_in=0.0, nonop_out=0.0,
               cip=125.0, st_debt=100.0, cur_ltd=30.0),
}

INT_RATE = 0.05      # 借款利率（按期初借款）
CASH_RATE = 0.01     # 存款利率（按期初现金）
TAX = 0.25
PAYOUT = 0.30

# ---------------------------------------------------------------------------
# 2. 预测假设（三种情景）
# ---------------------------------------------------------------------------
ASSUME = dict(
    vol_g={1: [0.09, 0.08, 0.07, 0.06, 0.05],      # 基准
           2: [0.11, 0.10, 0.09, 0.08, 0.07],      # 乐观
           3: [0.05, 0.04, 0.03, 0.02, 0.02]},     # 悲观
    price_g=[0.02, 0.02, 0.02, 0.015, 0.015],
    cogs_pct={1: [0.535] * 5, 2: [0.525] * 5, 3: [0.55] * 5},
    sell_pct=[0.20] * 5,
    admin_pct=[0.075] * 5,
    dep_rate=[0.095] * 5,
    capex_pct=[0.06] * 5,
    dso=[40] * 5, dio=[73] * 5, dpo=[70] * 5,
    repay=[30.0] * 5,
    int_rate=[INT_RATE] * 5,
    cash_rate=[CASH_RATE] * 5,
    tax=[TAX] * 5,
    payout=[PAYOUT] * 5,
    nonop=[0.0] * 5,
)
SCEN_NAMES = {1: "基准", 2: "乐观", 3: "悲观"}

VAL = dict(rf=0.02, beta=1.0, erp=0.065, kd=0.05, dv=0.10, g=0.02)


def r1(x):
    return round(x + 0.0, 1)


# ---------------------------------------------------------------------------
# 3. 计算历史期（生成"年报"数字）
# ---------------------------------------------------------------------------
def build_history():
    H = {}
    prev = dict(cash=opening["cash"], ar=opening["ar"], inv=opening["inv"],
                ppe=opening["fa"] + opening["cip"] + opening["intang"],
                intang=opening["intang"], other=opening["other"], ap=opening["ap"],
                debt=opening["st_debt"] + opening["cur_ltd"] + opening["lt_debt"],
                paid_in=opening["share_cap"] + opening["apic"],
                surplus=opening["surplus"], re=opening["surplus"] + opening["undist"])
    H[2022] = dict(prev)
    for y in HIST:
        d = hist_drv[y]
        rev = d["vol"] * d["price"] / 100
        cogs = rev * d["cogs_pct"]
        sell = rev * d["sell_pct"]
        admin = d["mgmt"] + d["rnd"] + d["biz_tax"]
        ebitda = rev - cogs - sell - admin
        da = d["dep"] + d["amort"]
        ebit = ebitda - da
        int_exp = prev["debt"] * INT_RATE
        int_inc = prev["cash"] * CASH_RATE
        nonop = d["nonop_in"] - d["nonop_out"]
        ebt = ebit - int_exp + int_inc + nonop
        tax = ebt * TAX
        ni = ebt - tax
        div = ni * PAYOUT
        ar = r1(rev * d["dso"] / 365)
        inv = r1(cogs * d["dio"] / 365)
        ap = r1(cogs * d["dpo"] / 365)
        ppe = prev["ppe"] + d["capex"] - da
        intang = prev["intang"] - d["amort"]
        debt = prev["debt"] + d["borrow"] - d["repay"]
        re = prev["re"] + ni - div
        surplus = prev["surplus"] + ni * 0.10
        cfo = ni + da - (ar - prev["ar"]) - (inv - prev["inv"]) + (ap - prev["ap"])
        cfi = -d["capex"]
        cff = (debt - prev["debt"]) - div
        cash = prev["cash"] + cfo + cfi + cff
        cur = dict(rev=rev, cogs=cogs, sell=sell, admin=admin, ebitda=ebitda, da=da, ebit=ebit,
                   int_exp=int_exp, int_inc=int_inc, nonop=nonop, ebt=ebt, tax=tax, ni=ni, div=div,
                   ar=ar, inv=inv, ap=ap, ppe=ppe, intang=intang, other=prev["other"], debt=debt,
                   paid_in=prev["paid_in"], re=re, surplus=surplus, cash=cash,
                   cfo=cfo, cfi=cfi, cff=cff, capex=d["capex"], vol=d["vol"], price=d["price"])
        H[y] = cur
        prev = cur
    return H


# ---------------------------------------------------------------------------
# 4. 预测期 + 估值（Python 版本，用来校验 Excel 公式结果）
# ---------------------------------------------------------------------------
def build_forecast(H, scen=1):
    A = ASSUME
    rows = {k: {} for k in [
        "vol", "vol_g", "price", "price_g", "rev", "rev_g", "cogs", "cogs_pct", "sell", "sell_pct",
        "admin", "admin_pct", "ebitda", "ebitda_m", "da", "ebit", "int_exp", "int_inc", "nonop", "ebt",
        "tax", "tax_rate", "ni", "ni_m", "eps", "ar", "dso", "inv", "dio", "ap", "dpo", "nwc", "dnwc",
        "ppe_open", "capex", "ppe_da", "ppe_close", "capex_pct", "dep_rate",
        "debt_open", "repay", "debt_close", "int_rate", "cash_rate",
        "cash", "other", "ta", "tl", "paid_in", "re", "te", "tle", "bs_chk",
        "cf_ni", "cf_da", "cf_ar", "cf_inv", "cf_ap", "cfo", "cf_capex", "cfi", "cf_debt", "cf_div",
        "payout", "cff", "cf_net", "cash_open", "cash_close"]}
    prev_y = 2022
    for y in HIST:
        h, p = H[y], H[prev_y]
        rows["vol"][y] = h["vol"]; rows["price"][y] = h["price"]; rows["rev"][y] = h["rev"]
        rows["cogs"][y] = h["cogs"]; rows["sell"][y] = h["sell"]; rows["admin"][y] = h["admin"]
        rows["da"][y] = h["da"]; rows["int_exp"][y] = h["int_exp"]; rows["int_inc"][y] = h["int_inc"]
        rows["nonop"][y] = h["nonop"]; rows["tax"][y] = h["tax"]
        rows["ar"][y] = h["ar"]; rows["inv"][y] = h["inv"]; rows["ap"][y] = h["ap"]
        rows["ppe_open"][y] = p["ppe"]; rows["capex"][y] = h["capex"]
        rows["debt_open"][y] = p["debt"]; rows["debt_close"][y] = h["debt"]
        rows["repay"][y] = p["debt"] - h["debt"]
        rows["cash"][y] = h["cash"]; rows["other"][y] = h["other"]
        rows["paid_in"][y] = h["paid_in"]; rows["re"][y] = h["re"]
        rows["cf_div"][y] = -h["div"]
        rows["cash_open"][y] = p["cash"]
        prev_y = y

    def g(k, y):
        return rows[k][y]

    for i, y in enumerate(FC):
        py = y - 1
        rows["vol_g"][y] = A["vol_g"][scen][i]
        rows["price_g"][y] = A["price_g"][i]
        rows["vol"][y] = g("vol", py) * (1 + rows["vol_g"][y])
        rows["price"][y] = g("price", py) * (1 + rows["price_g"][y])
        rows["rev"][y] = rows["vol"][y] * rows["price"][y] / 100
        rows["cogs_pct"][y] = A["cogs_pct"][scen][i]
        rows["sell_pct"][y] = A["sell_pct"][i]
        rows["admin_pct"][y] = A["admin_pct"][i]
        rows["cogs"][y] = rows["rev"][y] * rows["cogs_pct"][y]
        rows["sell"][y] = rows["rev"][y] * rows["sell_pct"][y]
        rows["admin"][y] = rows["rev"][y] * rows["admin_pct"][y]
        # 固定资产
        rows["ppe_open"][y] = g("ppe_close", py) if py in FC else H[py]["ppe"]
        rows["dep_rate"][y] = A["dep_rate"][i]
        rows["capex_pct"][y] = A["capex_pct"][i]
        rows["capex"][y] = rows["rev"][y] * rows["capex_pct"][y]
        rows["da"][y] = rows["ppe_open"][y] * rows["dep_rate"][y]
        # 借款
        rows["debt_open"][y] = g("debt_close", py)
        rows["repay"][y] = min(A["repay"][i], rows["debt_open"][y])
        rows["debt_close"][y] = rows["debt_open"][y] - rows["repay"][y]
        rows["int_rate"][y] = A["int_rate"][i]
        rows["cash_rate"][y] = A["cash_rate"][i]
        rows["int_exp"][y] = rows["debt_open"][y] * rows["int_rate"][y]
        rows["cash_open"][y] = g("cash", py)
        rows["int_inc"][y] = rows["cash_open"][y] * rows["cash_rate"][y]
        rows["nonop"][y] = A["nonop"][i]
        ebitda = rows["rev"][y] - rows["cogs"][y] - rows["sell"][y] - rows["admin"][y]
        ebit = ebitda - rows["da"][y]
        ebt = ebit - rows["int_exp"][y] + rows["int_inc"][y] + rows["nonop"][y]
        rows["tax_rate"][y] = A["tax"][i]
        rows["tax"][y] = max(0.0, ebt * rows["tax_rate"][y])
        ni = ebt - rows["tax"][y]
        # 营运资本
        rows["dso"][y] = A["dso"][i]; rows["dio"][y] = A["dio"][i]; rows["dpo"][y] = A["dpo"][i]
        rows["ar"][y] = rows["rev"][y] * rows["dso"][y] / 365
        rows["inv"][y] = rows["cogs"][y] * rows["dio"][y] / 365
        rows["ap"][y] = rows["cogs"][y] * rows["dpo"][y] / 365
        rows["ppe_close"][y] = rows["ppe_open"][y] + rows["capex"][y] - rows["da"][y]
        rows["other"][y] = g("other", py)
        rows["paid_in"][y] = g("paid_in", py)
        rows["payout"][y] = A["payout"][i]
        div = ni * rows["payout"][y]
        rows["re"][y] = g("re", py) + ni - div
        cfo = ni + rows["da"][y] - (rows["ar"][y] - g("ar", py)) - (rows["inv"][y] - g("inv", py)) \
            + (rows["ap"][y] - g("ap", py))
        cfi = -rows["capex"][y]
        cff = -rows["repay"][y] - div
        rows["cash"][y] = rows["cash_open"][y] + cfo + cfi + cff
        rows["cf_div"][y] = -div

    # 公共派生行（历史 + 预测）
    for y in YEARS:
        py = y - 1
        rev = rows["rev"][y]
        ebitda = rev - rows["cogs"][y] - rows["sell"][y] - rows["admin"][y]
        ebit = ebitda - rows["da"][y]
        ebt = ebit - rows["int_exp"][y] + rows["int_inc"][y] + rows["nonop"][y]
        ni = ebt - rows["tax"][y]
        rows["ebitda"][y] = ebitda; rows["ebit"][y] = ebit; rows["ebt"][y] = ebt; rows["ni"][y] = ni
        rows["ebitda_m"][y] = ebitda / rev; rows["ni_m"][y] = ni / rev
        rows["tax_rate"][y] = rows["tax"][y] / ebt
        rows["eps"][y] = ni / SHARES
        rows["cogs_pct"][y] = rows["cogs"][y] / rev
        rows["sell_pct"][y] = rows["sell"][y] / rev
        rows["admin_pct"][y] = rows["admin"][y] / rev
        rows["dso"][y] = rows["ar"][y] / rev * 365
        rows["dio"][y] = rows["inv"][y] / rows["cogs"][y] * 365
        rows["dpo"][y] = rows["ap"][y] / rows["cogs"][y] * 365
        rows["nwc"][y] = rows["ar"][y] + rows["inv"][y] - rows["ap"][y]
        prev_nwc = (rows["nwc"][py] if py in rows["nwc"] else H[2022]["ar"] + H[2022]["inv"] - H[2022]["ap"])
        rows["dnwc"][y] = rows["nwc"][y] - prev_nwc
        rows["ppe_da"][y] = rows["da"][y]
        rows["ppe_close"][y] = rows["ppe_open"][y] + rows["capex"][y] - rows["da"][y]
        rows["capex_pct"][y] = rows["capex"][y] / rev
        rows["dep_rate"][y] = rows["da"][y] / rows["ppe_open"][y]
        rows["int_rate"][y] = rows["int_exp"][y] / rows["debt_open"][y]
        rows["cash_rate"][y] = rows["int_inc"][y] / rows["cash_open"][y]
        rows["ta"][y] = rows["cash"][y] + rows["ar"][y] + rows["inv"][y] + rows["ppe_close"][y] + rows["other"][y]
        rows["tl"][y] = rows["ap"][y] + rows["debt_close"][y]
        rows["te"][y] = rows["paid_in"][y] + rows["re"][y]
        rows["tle"][y] = rows["tl"][y] + rows["te"][y]
        rows["bs_chk"][y] = rows["ta"][y] - rows["tle"][y]
        pv = (lambda k: rows[k][py] if py in rows[k] else H[2022][k])
        rows["cf_ni"][y] = ni
        rows["cf_da"][y] = rows["da"][y]
        rows["cf_ar"][y] = -(rows["ar"][y] - pv("ar"))
        rows["cf_inv"][y] = -(rows["inv"][y] - pv("inv"))
        rows["cf_ap"][y] = rows["ap"][y] - pv("ap")
        rows["cfo"][y] = ni + rows["da"][y] + rows["cf_ar"][y] + rows["cf_inv"][y] + rows["cf_ap"][y]
        rows["cf_capex"][y] = -rows["capex"][y]
        rows["cfi"][y] = rows["cf_capex"][y]
        rows["cf_debt"][y] = rows["debt_close"][y] - rows["debt_open"][y]
        rows["payout"][y] = -rows["cf_div"][y] / ni
        rows["cff"][y] = rows["cf_debt"][y] + rows["cf_div"][y]
        rows["cf_net"][y] = rows["cfo"][y] + rows["cfi"][y] + rows["cff"][y]
        rows["cash_close"][y] = rows["cash_open"][y] + rows["cf_net"][y]
        prev_rev = rows["rev"][py] if py in rows["rev"] else None
        prev_vol = rows["vol"][py] if py in rows["vol"] else None
        prev_price = rows["price"][py] if py in rows["price"] else None
        if prev_rev:
            rows["rev_g"][y] = rev / prev_rev - 1
            rows["vol_g"][y] = rows["vol"][y] / prev_vol - 1
            rows["price_g"][y] = rows["price"][y] / prev_price - 1
    return rows


def valuation(M, wacc=None, g=None):
    v = dict(VAL)
    ke = v["rf"] + v["beta"] * v["erp"]
    kd_at = v["kd"] * (1 - TAX)
    w = wacc if wacc is not None else (1 - v["dv"]) * ke + v["dv"] * kd_at
    g = g if g is not None else v["g"]
    fcff, pv = {}, {}
    sum_pv = 0
    for t, y in enumerate(FC, start=1):
        nopat = M["ebit"][y] * (1 - TAX)
        fcff[y] = nopat + M["da"][y] - M["capex"][y] - M["dnwc"][y]
        pv[y] = fcff[y] / (1 + w) ** t
        sum_pv += pv[y]
    tv = fcff[2030] * (1 + g) / (w - g)
    pv_tv = tv / (1 + w) ** 5
    ev = sum_pv + pv_tv
    net_debt = M["debt_close"][2025] - M["cash"][2025]
    eq = ev - net_debt
    ps = eq / SHARES
    return dict(ke=ke, kd_at=kd_at, wacc=w, g=g, fcff=fcff, pv=pv, sum_pv=sum_pv, tv=tv, pv_tv=pv_tv,
                ev=ev, net_debt=net_debt, equity=eq, per_share=ps, tv_share=pv_tv / ev,
                upside=ps / PRICE - 1, ev_ebitda_26=ev / M["ebitda"][2026], tv_ebitda=tv / M["ebitda"][2030])


# ---------------------------------------------------------------------------
# 5. 原始数据（模拟"从网站下载的报表"）
# ---------------------------------------------------------------------------
def raw_rows(H):
    """返回 [(报表, 原始科目, {year: 元或原值 or None})]，按下载网站的常见格式。"""
    rows = []
    o = opening
    bs = {2022: dict(cash=o["cash"], ar=o["ar"], inv=o["inv"], fa=o["fa"], cip=o["cip"], intang=o["intang"],
                     other=o["other"], ap=o["ap"], st=o["st_debt"], cur=o["cur_ltd"], lt=o["lt_debt"],
                     cap=o["share_cap"], apic=o["apic"], surplus=o["surplus"], undist=o["undist"])}
    for y in HIST:
        h, d = H[y], hist_drv[y]
        fa = h["ppe"] - d["cip"] - h["intang"]
        lt = h["debt"] - d["st_debt"] - d["cur_ltd"]
        bs[y] = dict(cash=h["cash"], ar=h["ar"], inv=h["inv"], fa=fa, cip=d["cip"], intang=h["intang"],
                     other=h["other"], ap=h["ap"], st=d["st_debt"], cur=d["cur_ltd"], lt=lt,
                     cap=o["share_cap"], apic=o["apic"], surplus=h["surplus"], undist=h["re"] - h["surplus"])

    def yen(x):
        return None if x is None else round(x * 1_000_000, 2)

    def is_row(name, f):
        rows.append(("利润表", name, {y: yen(f(H[y], hist_drv[y])) for y in HIST} | {2022: None}))

    is_row("一、营业总收入", lambda h, d: h["rev"])
    is_row("其中：营业收入", lambda h, d: h["rev"])
    is_row("二、营业总成本", lambda h, d: h["cogs"] + h["da"] + h["sell"] + h["admin"] + h["int_exp"] - h["int_inc"])
    is_row("其中：营业成本", lambda h, d: h["cogs"] + h["da"])
    is_row("税金及附加", lambda h, d: d["biz_tax"])
    is_row("销售费用", lambda h, d: h["sell"])
    is_row("管理费用", lambda h, d: d["mgmt"])
    is_row("研发费用", lambda h, d: d["rnd"])
    is_row("财务费用", lambda h, d: h["int_exp"] - h["int_inc"])
    is_row("其中：利息费用", lambda h, d: h["int_exp"])
    is_row("利息收入", lambda h, d: h["int_inc"])
    is_row("三、营业利润", lambda h, d: h["ebit"] - h["int_exp"] + h["int_inc"])
    is_row("加：营业外收入", lambda h, d: d["nonop_in"])
    is_row("减：营业外支出", lambda h, d: d["nonop_out"])
    is_row("四、利润总额", lambda h, d: h["ebt"])
    is_row("减：所得税费用", lambda h, d: h["tax"])
    is_row("五、净利润", lambda h, d: h["ni"])

    def bs_row(name, f):
        rows.append(("资产负债表", name, {y: yen(f(bs[y])) for y in [2022] + HIST}))

    bs_row("货币资金", lambda b: b["cash"])
    bs_row("应收账款", lambda b: b["ar"])
    bs_row("存货", lambda b: b["inv"])
    bs_row("流动资产合计", lambda b: b["cash"] + b["ar"] + b["inv"])
    bs_row("固定资产", lambda b: b["fa"])
    bs_row("在建工程", lambda b: b["cip"])
    bs_row("无形资产", lambda b: b["intang"])
    bs_row("其他非流动资产", lambda b: b["other"])
    bs_row("非流动资产合计", lambda b: b["fa"] + b["cip"] + b["intang"] + b["other"])
    bs_row("资产总计", lambda b: b["cash"] + b["ar"] + b["inv"] + b["fa"] + b["cip"] + b["intang"] + b["other"])
    bs_row("短期借款", lambda b: b["st"])
    bs_row("应付账款", lambda b: b["ap"])
    bs_row("一年内到期的非流动负债", lambda b: b["cur"])
    bs_row("流动负债合计", lambda b: b["st"] + b["ap"] + b["cur"])
    bs_row("长期借款", lambda b: b["lt"])
    bs_row("非流动负债合计", lambda b: b["lt"])
    bs_row("负债合计", lambda b: b["st"] + b["ap"] + b["cur"] + b["lt"])
    bs_row("实收资本（或股本）", lambda b: b["cap"])
    bs_row("资本公积", lambda b: b["apic"])
    bs_row("盈余公积", lambda b: b["surplus"])
    bs_row("未分配利润", lambda b: b["undist"])
    bs_row("所有者权益（或股东权益）合计", lambda b: b["cap"] + b["apic"] + b["surplus"] + b["undist"])
    bs_row("负债和所有者权益（或股东权益）总计",
           lambda b: b["st"] + b["ap"] + b["cur"] + b["lt"] + b["cap"] + b["apic"] + b["surplus"] + b["undist"])

    def cf_row(name, f):
        rows.append(("现金流量表", name, {y: yen(f(H[y], hist_drv[y])) for y in HIST} | {2022: None}))

    cf_row("经营活动产生的现金流量净额", lambda h, d: h["cfo"] + h["int_exp"])
    cf_row("购建固定资产、无形资产和其他长期资产支付的现金", lambda h, d: d["capex"])
    cf_row("投资活动产生的现金流量净额", lambda h, d: -d["capex"])
    cf_row("取得借款收到的现金", lambda h, d: d["borrow"])
    cf_row("偿还债务支付的现金", lambda h, d: d["repay"])
    cf_row("分配股利、利润或偿付利息支付的现金", lambda h, d: h["div"] + h["int_exp"])
    cf_row("筹资活动产生的现金流量净额", lambda h, d: d["borrow"] - d["repay"] - h["div"] - h["int_exp"])
    cf_row("现金及现金等价物净增加额", lambda h, d: h["cfo"] + h["cfi"] + h["cff"])
    cf_row("期末现金及现金等价物余额", lambda h, d: h["cash"])
    cf_row("固定资产折旧、油气资产折耗、生产性生物资产折旧", lambda h, d: d["dep"])
    cf_row("无形资产摊销", lambda h, d: d["amort"])

    rows.append(("经营数据", "销量（万箱）", {y: float(hist_drv[y]["vol"]) for y in HIST} | {2022: None}))
    rows.append(("经营数据", "平均售价（元/箱）", {y: hist_drv[y]["price"] for y in HIST} | {2022: None}))
    return rows


# 映射表：原始科目 → 标准科目
MAPPING = [
    ("一、营业总收入", "忽略", "合计行，和下面的营业收入重复"),
    ("其中：营业收入", "营业收入", ""),
    ("二、营业总成本", "忽略", "小计行"),
    ("其中：营业成本", "营业成本（含折旧）", "报表里的营业成本包含了生产设备的折旧"),
    ("税金及附加", "管理及其他费用", "三项合并成一个预测科目"),
    ("销售费用", "销售费用", ""),
    ("管理费用", "管理及其他费用", ""),
    ("研发费用", "管理及其他费用", ""),
    ("财务费用", "忽略", "用下面的利息费用、利息收入拆开看"),
    ("其中：利息费用", "利息费用", ""),
    ("利息收入", "利息收入", ""),
    ("三、营业利润", "忽略", "小计行"),
    ("加：营业外收入", "营业外收入", "一次性项目，预测期一般取 0"),
    ("减：营业外支出", "营业外支出", ""),
    ("四、利润总额", "利润总额（报告）", "只用于校验"),
    ("减：所得税费用", "所得税", ""),
    ("五、净利润", "净利润（报告）", "只用于校验"),
    ("货币资金", "货币资金", ""),
    ("应收账款", "应收账款", ""),
    ("存货", "存货", ""),
    ("流动资产合计", "忽略", "小计行"),
    ("固定资产", "固定资产（净）", "固定资产+在建工程+无形资产合并"),
    ("在建工程", "固定资产（净）", ""),
    ("无形资产", "固定资产（净）", ""),
    ("其他非流动资产", "其他非流动资产", ""),
    ("非流动资产合计", "忽略", "小计行"),
    ("资产总计", "资产总计（报告）", "只用于校验"),
    ("短期借款", "银行借款", "三项有息负债合并"),
    ("应付账款", "应付账款", ""),
    ("一年内到期的非流动负债", "银行借款", ""),
    ("流动负债合计", "忽略", "小计行"),
    ("长期借款", "银行借款", ""),
    ("非流动负债合计", "忽略", "小计行"),
    ("负债合计", "负债合计（报告）", "只用于校验"),
    ("实收资本（或股本）", "实收资本", "股本+资本公积"),
    ("资本公积", "实收资本", ""),
    ("盈余公积", "留存收益", "盈余公积+未分配利润"),
    ("未分配利润", "留存收益", ""),
    ("所有者权益（或股东权益）合计", "所有者权益合计（报告）", "只用于校验"),
    ("负债和所有者权益（或股东权益）总计", "忽略", "与资产总计相等"),
    ("经营活动产生的现金流量净额", "经营活动现金流（报告）", "注意：中国准则把利息支出放在筹资活动"),
    ("购建固定资产、无形资产和其他长期资产支付的现金", "资本开支", ""),
    ("投资活动产生的现金流量净额", "忽略", "小计行"),
    ("取得借款收到的现金", "取得借款", ""),
    ("偿还债务支付的现金", "偿还借款", ""),
    ("分配股利、利润或偿付利息支付的现金", "支付股利及利息", "股利和利息混在一行，需要拆开"),
    ("筹资活动产生的现金流量净额", "忽略", "小计行"),
    ("现金及现金等价物净增加额", "忽略", "小计行"),
    ("期末现金及现金等价物余额", "期末现金（报告）", "只用于校验"),
    ("固定资产折旧、油气资产折耗、生产性生物资产折旧", "折旧摊销", "来自现金流量表补充资料"),
    ("无形资产摊销", "折旧摊销", ""),
    ("销量（万箱）", "销量", "来自年报经营情况讨论"),
    ("平均售价（元/箱）", "均价", ""),
]


# ---------------------------------------------------------------------------
# 6. 脏数据 CSV
# ---------------------------------------------------------------------------
def fmt_text(v, style):
    if v is None:
        return "--"
    if style == "plain":
        return f"{v:.2f}"
    s = f"{abs(v):,.2f}"
    if v < 0:
        return f"({s})" if style == "paren" else f"-{s}"
    return s


def write_csv(rows):
    path = os.path.join(OUT_PRACTICE, f"{COMPANY}_原始数据.csv")
    years = [2025, 2024, 2023, 2022]  # 下载网站常见：最新年份在最左边
    lines = []
    lines.append([f"{COMPANY}（虚构）主要财务报表", "", "", "", ""])
    lines.append(["单位：元", "", "", "", ""])
    lines.append(["报表项目"] + [f"{y}-12-31" for y in years])
    messy_names = {"销售费用": "  销售费用 ", "存货": "存货　", "应付账款": " 应付账款"}
    current = None
    for sheet, name, vals in rows:
        if sheet != current:
            lines.append([f"【{sheet}】", "", "", "", ""])
            current = sheet
        shown = messy_names.get(name, name)
        style = "paren" if sheet == "现金流量表" else "comma"
        if sheet == "经营数据":
            style = "plain"
        lines.append([shown] + [fmt_text(vals.get(y), style) for y in years])
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(lines)
    return lines


# ---------------------------------------------------------------------------
# 7. Excel 工作簿
# ---------------------------------------------------------------------------
BLUE = Font(name="Arial", size=10, color="0000FF")
BLACK = Font(name="Arial", size=10, color="000000")
GREEN = Font(name="Arial", size=10, color="008000")
BOLD = Font(name="Arial", size=10, bold=True)
TITLE = Font(name="Arial", size=14, bold=True)
SECTION = Font(name="Arial", size=11, bold=True, color="FFFFFF")
GREY = Font(name="Arial", size=9, color="666666")
HEAD_FILL = PatternFill("solid", fgColor="1F3864")
SEC_FILL = PatternFill("solid", fgColor="2F5496")
SUB_FILL = PatternFill("solid", fgColor="EEF2F8")
YELLOW = PatternFill("solid", fgColor="FFFF00")
TODO = PatternFill("solid", fgColor="FFF2CC")
THIN = Side(style="thin", color="999999")
TOP_LINE = Border(top=THIN)

NUM = '#,##0.0;(#,##0.0);"-"'
NUM0 = '#,##0;(#,##0);"-"'
PCT = '0.0%;(0.0%);"-"'
DAYS = '0.0;(0.0);"-"'
PRICE_FMT = '0.00;(0.00);"-"'
MULT = '0.0"x"'

COLS_HIST = ["D", "E", "F"]
COLS_FC = ["G", "H", "I", "J", "K"]
COLS = COLS_HIST + COLS_FC
YEAR_OF = dict(zip(COLS, YEARS))


def prev_col(c):
    return get_column_letter(ord(c) - 64 - 1)


def note(ws, row, col, text, font=None):
    """写说明文字。以 = 开头的说明会被 Excel 当成公式，所以换成全角＝。"""
    if isinstance(text, str) and text.startswith("="):
        text = "＝" + text[1:]
    c = ws.cell(row=row, column=col, value=text)
    c.font = font or GREY
    return c


def set_widths(ws, widths):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def build_workbook(rows_raw, H, M, template=False):
    wb = Workbook()
    ws0 = wb.active
    ws0.title = "说明"

    # ---------------- 映射表 ----------------
    wm = wb.create_sheet("映射表")
    wm["A1"] = "科目映射表：把下载来的原始科目名称，对应到模型使用的标准科目"; wm["A1"].font = TITLE
    wm["A2"] = "标准科目填\"忽略\"的行不会被汇总（合计行、小计行要忽略，否则会重复计算）"; wm["A2"].font = GREY
    for i, h in enumerate(["原始科目", "标准科目", "说明"]):
        c = wm.cell(row=4, column=i + 1, value=h); c.font = Font(name="Arial", bold=True, color="FFFFFF"); c.fill = HEAD_FILL
    for i, (a, b, n) in enumerate(MAPPING):
        r = 5 + i
        wm.cell(row=r, column=1, value=a).font = BLACK
        wm.cell(row=r, column=2, value=b).font = BLUE
        wm.cell(row=r, column=3, value=n).font = GREY
    map_last = 4 + len(MAPPING)
    set_widths(wm, {"A": 46, "B": 26, "C": 40})

    # ---------------- 原始数据 ----------------
    wr = wb.create_sheet("原始数据")
    wr["A1"] = f"{COMPANY}（虚构）原始财务数据——按\"下载\"的样子原样保存，不要在这里改数字"; wr["A1"].font = TITLE
    wr["A2"] = "来源：虚构练习数据（真实建模时写明：网站/文件名/页码/下载日期）。单位：元（经营数据除外）。年份从新到旧排列。"
    wr["A2"].font = GREY
    hdr = ["报表", "原始科目", 2025, 2024, 2023, 2022, "标准科目（公式自动映射）"]
    for i, h in enumerate(hdr):
        c = wr.cell(row=4, column=i + 1, value=h); c.font = Font(name="Arial", bold=True, color="FFFFFF"); c.fill = HEAD_FILL
    raw_first = 5
    for i, (sheet, name, vals) in enumerate(rows_raw):
        r = raw_first + i
        wr.cell(row=r, column=1, value=sheet).font = GREY
        wr.cell(row=r, column=2, value=name).font = BLACK
        for j, y in enumerate([2025, 2024, 2023, 2022]):
            v = vals.get(y)
            c = wr.cell(row=r, column=3 + j, value=v)
            c.font = BLUE
            c.number_format = '#,##0.00' if sheet != "经营数据" else '0.00'
        wr.cell(row=r, column=7,
                value=f'=IFERROR(INDEX(映射表!$B$5:$B$200,MATCH(TRIM(B{r}),映射表!$A$5:$A$200,0)),"未映射")').font = BLACK
    raw_last = raw_first + len(rows_raw) - 1
    set_widths(wr, {"A": 10, "B": 46, "C": 18, "D": 18, "E": 18, "F": 18, "G": 26})
    wr.freeze_panes = "C5"

    # ---------------- 历史数据（清洗 + 汇总 + 校验）----------------
    wh = wb.create_sheet("历史数据")
    wh["A1"] = "历史数据：用 SUMIFS 按标准科目从原始数据汇总（单位：百万元）"; wh["A1"].font = TITLE
    wh["A2"] = "单位换算：原始数据（元）除以"; wh["A2"].font = BOLD
    wh["C2"] = 1_000_000; wh["C2"].font = BLUE; wh["C2"].fill = YELLOW; wh["C2"].number_format = "#,##0"
    wh["D2"] = "← 只在这里输入一次，所有公式引用它"; wh["D2"].font = GREY
    for i, h in enumerate(["标准科目", "单位", 2022, 2023, 2024, 2025]):
        c = wh.cell(row=3, column=i + 1, value=h); c.font = Font(name="Arial", bold=True, color="FFFFFF"); c.fill = HEAD_FILL
    wh["G3"] = "公式说明"; wh["G3"].font = Font(name="Arial", bold=True, color="FFFFFF"); wh["G3"].fill = HEAD_FILL

    HR = {}
    hist_items = [
        ("sec", "利润表"),
        ("rev", "营业收入", "百万元", "money"),
        ("cogs_r", "营业成本（含折旧）", "百万元", "money"),
        ("da", "折旧摊销", "百万元", "money"),
        ("cogs", "营业成本（不含折旧摊销）", "百万元", "calc"),
        ("sell", "销售费用", "百万元", "money"),
        ("admin", "管理及其他费用", "百万元", "money"),
        ("int_exp", "利息费用", "百万元", "money"),
        ("int_inc", "利息收入", "百万元", "money"),
        ("nonop_in", "营业外收入", "百万元", "money"),
        ("nonop_out", "营业外支出", "百万元", "money"),
        ("nonop", "营业外收支净额", "百万元", "calc"),
        ("tax", "所得税", "百万元", "money"),
        ("ebt_r", "利润总额（报告）", "百万元", "money"),
        ("ni_r", "净利润（报告）", "百万元", "money"),
        ("ni", "净利润（重算）", "百万元", "calc"),
        ("sec", "资产负债表"),
        ("cash", "货币资金", "百万元", "money"),
        ("ar", "应收账款", "百万元", "money"),
        ("inv", "存货", "百万元", "money"),
        ("ppe", "固定资产（净）", "百万元", "money"),
        ("other", "其他非流动资产", "百万元", "money"),
        ("ta", "资产合计（重算）", "百万元", "calc"),
        ("ta_r", "资产总计（报告）", "百万元", "money"),
        ("ap", "应付账款", "百万元", "money"),
        ("debt", "银行借款", "百万元", "money"),
        ("tl", "负债合计（重算）", "百万元", "calc"),
        ("tl_r", "负债合计（报告）", "百万元", "money"),
        ("paid_in", "实收资本", "百万元", "money"),
        ("re", "留存收益", "百万元", "money"),
        ("te", "所有者权益合计（重算）", "百万元", "calc"),
        ("te_r", "所有者权益合计（报告）", "百万元", "money"),
        ("sec", "现金流量表（报告数，用于拆分和校验）"),
        ("cfo_r", "经营活动现金流（报告）", "百万元", "money"),
        ("capex", "资本开支", "百万元", "money"),
        ("borrow", "取得借款", "百万元", "money"),
        ("repay", "偿还借款", "百万元", "money"),
        ("divint", "支付股利及利息", "百万元", "money"),
        ("div", "其中：支付股利（拆分）", "百万元", "calc"),
        ("cash_r", "期末现金（报告）", "百万元", "money"),
        ("sec", "经营数据"),
        ("vol", "销量", "万箱", "op"),
        ("price", "均价", "元/箱", "op"),
        ("sec", "模型口径现金流量表（间接法重建）"),
        ("cf_ni", "净利润", "百万元", "calc"),
        ("cf_da", "加：折旧摊销", "百万元", "calc"),
        ("cf_wc", "减：营运资本增加", "百万元", "calc"),
        ("cfo", "经营活动现金流（模型口径）", "百万元", "calc"),
        ("cfi", "投资活动现金流", "百万元", "calc"),
        ("cff", "筹资活动现金流（不含利息）", "百万元", "calc"),
        ("cf_net", "现金净增加", "百万元", "calc"),
        ("sec", "校验（全部应为 TRUE）"),
        ("chk_ni", "净利润：重算 = 报告", "", "chk"),
        ("chk_ta", "资产：重算 = 报告", "", "chk"),
        ("chk_bs", "资产 = 负债 + 所有者权益", "", "chk"),
        ("chk_cash", "现金：期初 + 净增加 = 期末", "", "chk"),
        ("chk_cfo", "经营现金流：模型口径 + 利息 = 报告口径", "", "chk"),
        ("chk_all", "全部通过？", "", "chk"),
    ]
    r = 4
    for it in hist_items:
        if it[0] == "sec":
            c = wh.cell(row=r, column=1, value=it[1]); c.font = SECTION
            for col in range(1, 8):
                wh.cell(row=r, column=col).fill = SEC_FILL
        else:
            HR[it[0]] = r
        r += 1
    std_name = {it[0]: it[1] for it in hist_items if it[0] != "sec"}
    rawsum = ("=SUMIFS(INDEX(原始数据!$C${a}:$F${b},0,MATCH({c}$3,原始数据!$C$4:$F$4,0)),"
              "原始数据!$G${a}:$G${b},$A{r}){div}")
    notes_h = {
        "rev": "=SUMIFS(该年那一列, 标准科目列, \"营业收入\") / 单位",
        "cogs": "= 营业成本（含折旧）− 折旧摊销（假设折旧都在营业成本里）",
        "nonop": "= 营业外收入 − 营业外支出",
        "ni": "= 收入 − 成本 − 费用 − 利息 + 利息收入 + 营业外 − 所得税",
        "ta": "= 各项资产相加",
        "div": "= 支付股利及利息 − 利息费用（假设利息当年付清）",
        "cf_wc": "= −[(应收+存货−应付)本年 − 上年]",
        "cff": "= 取得借款 − 偿还借款 − 股利",
        "chk_cfo": "中国准则把利息支出放在筹资活动，模型放在经营活动",
    }
    for key, row in HR.items():
        name = std_name[key]
        typ = next(it[3] for it in hist_items if it[0] == key)
        wh.cell(row=row, column=1, value=name).font = BOLD if typ in ("calc",) and key in ("ta", "tl", "te", "cfo", "cf_net", "ni") else BLACK
        unit = next(it[2] for it in hist_items if it[0] == key)
        wh.cell(row=row, column=2, value=unit).font = GREY
        if key in notes_h:
            note(wh, row, 7, notes_h[key])
        for col in ["C", "D", "E", "F"]:
            y = {"C": 2022, "D": 2023, "E": 2024, "F": 2025}[col]
            pc = prev_col(col)
            is_flow = key in ("rev", "cogs_r", "da", "cogs", "sell", "admin", "int_exp", "int_inc", "nonop_in",
                              "nonop_out", "nonop", "tax", "ebt_r", "ni_r", "ni", "cfo_r", "capex", "borrow",
                              "repay", "divint", "div", "cash_r", "vol", "price", "cf_ni", "cf_da", "cf_wc",
                              "cfo", "cfi", "cff", "cf_net", "chk_ni", "chk_cfo")
            if y == 2022 and (is_flow or key in ("chk_cash",)):
                continue
            f = None
            if typ == "money":
                f = rawsum.format(a=raw_first, b=200, c=col, r=row, div="/$C$2")
            elif typ == "op":
                f = rawsum.format(a=raw_first, b=200, c=col, r=row, div="")
            elif key == "cogs":
                f = f"={col}{HR['cogs_r']}-{col}{HR['da']}"
            elif key == "nonop":
                f = f"={col}{HR['nonop_in']}-{col}{HR['nonop_out']}"
            elif key == "ni":
                f = (f"={col}{HR['rev']}-{col}{HR['cogs']}-{col}{HR['da']}-{col}{HR['sell']}-{col}{HR['admin']}"
                     f"-{col}{HR['int_exp']}+{col}{HR['int_inc']}+{col}{HR['nonop']}-{col}{HR['tax']}")
            elif key == "ta":
                f = f"={col}{HR['cash']}+{col}{HR['ar']}+{col}{HR['inv']}+{col}{HR['ppe']}+{col}{HR['other']}"
            elif key == "tl":
                f = f"={col}{HR['ap']}+{col}{HR['debt']}"
            elif key == "te":
                f = f"={col}{HR['paid_in']}+{col}{HR['re']}"
            elif key == "div":
                f = f"={col}{HR['divint']}-{col}{HR['int_exp']}"
            elif key == "cf_ni":
                f = f"={col}{HR['ni']}"
            elif key == "cf_da":
                f = f"={col}{HR['da']}"
            elif key == "cf_wc":
                f = (f"=-(({col}{HR['ar']}+{col}{HR['inv']}-{col}{HR['ap']})"
                     f"-({pc}{HR['ar']}+{pc}{HR['inv']}-{pc}{HR['ap']}))")
            elif key == "cfo":
                f = f"={col}{HR['cf_ni']}+{col}{HR['cf_da']}+{col}{HR['cf_wc']}"
            elif key == "cfi":
                f = f"=-{col}{HR['capex']}"
            elif key == "cff":
                f = f"={col}{HR['borrow']}-{col}{HR['repay']}-{col}{HR['div']}"
            elif key == "cf_net":
                f = f"={col}{HR['cfo']}+{col}{HR['cfi']}+{col}{HR['cff']}"
            elif key == "chk_ni":
                f = f"=ABS({col}{HR['ni']}-{col}{HR['ni_r']})<0.01"
            elif key == "chk_ta":
                f = f"=ABS({col}{HR['ta']}-{col}{HR['ta_r']})<0.01"
            elif key == "chk_bs":
                f = f"=ABS({col}{HR['ta']}-{col}{HR['tl']}-{col}{HR['te']})<0.01"
            elif key == "chk_cash":
                f = f"=ABS({pc}{HR['cash']}+{col}{HR['cf_net']}-{col}{HR['cash']})<0.01"
            elif key == "chk_cfo":
                f = f"=ABS({col}{HR['cfo']}+{col}{HR['int_exp']}-{col}{HR['cfo_r']})<0.01"
            elif key == "chk_all":
                f = (f"=AND({col}{HR['chk_ta']},{col}{HR['chk_bs']}" +
                     ("" if y == 2022 else f",{col}{HR['chk_ni']},{col}{HR['chk_cash']},{col}{HR['chk_cfo']}") + ")")
            if f:
                c = wh.cell(row=row, column=ord(col) - 64, value=f)
                c.font = BLACK
                c.number_format = {"op": PRICE_FMT if key == "price" else NUM0}.get(typ, NUM)
                if typ == "calc":
                    c.font = BLACK
    set_widths(wh, {"A": 34, "B": 8, "C": 12, "D": 12, "E": 12, "F": 12, "G": 52})
    wh.freeze_panes = "C4"

    # ---------------- 假设 ----------------
    wa = wb.create_sheet("假设")
    # ---------------- 模型 ----------------
    wmod = wb.create_sheet("模型")
    # ---------------- 估值 ----------------
    wv = wb.create_sheet("估值")

    # 模型行布局
    layout = [
        ("sec", "一、收入预测（量 × 价）"),
        ("vol", "销量", "万箱"), ("vol_g", "  销量增长率", "%"),
        ("price", "均价", "元/箱"), ("price_g", "  均价增长率", "%"),
        ("rev", "营业收入", "百万元"), ("rev_g", "  收入增长率", "%"),
        ("blank",),
        ("sec", "二、利润表"),
        ("is_rev", "营业收入", "百万元"),
        ("cogs", "营业成本（不含折旧摊销）", "百万元"), ("cogs_pct", "  成本率", "%"),
        ("sell", "销售费用", "百万元"), ("sell_pct", "  销售费用率", "%"),
        ("admin", "管理及其他费用", "百万元"), ("admin_pct", "  管理及其他费用率", "%"),
        ("ebitda", "EBITDA", "百万元"), ("ebitda_m", "  EBITDA 利润率", "%"),
        ("da", "折旧摊销", "百万元"),
        ("ebit", "EBIT（息税前利润）", "百万元"),
        ("int_exp", "利息费用", "百万元"), ("int_inc", "利息收入", "百万元"),
        ("nonop", "营业外收支净额", "百万元"),
        ("ebt", "税前利润", "百万元"),
        ("tax", "所得税", "百万元"), ("tax_rate", "  有效税率", "%"),
        ("ni", "净利润", "百万元"), ("ni_m", "  净利率", "%"),
        ("eps", "每股收益（EPS）", "元/股"),
        ("blank",),
        ("sec", "三、营运资本"),
        ("ar", "应收账款", "百万元"), ("dso", "  应收账款周转天数（DSO）", "天"),
        ("inv", "存货", "百万元"), ("dio", "  存货周转天数（DIO）", "天"),
        ("ap", "应付账款", "百万元"), ("dpo", "  应付账款周转天数（DPO）", "天"),
        ("nwc", "营运资本（应收+存货−应付）", "百万元"),
        ("dnwc", "营运资本增加", "百万元"),
        ("blank",),
        ("sec", "四、固定资产（含在建工程、无形资产）"),
        ("ppe_open", "期初净值", "百万元"), ("capex", "加：资本开支", "百万元"),
        ("ppe_da", "减：折旧摊销", "百万元"), ("ppe_close", "期末净值", "百万元"),
        ("capex_pct", "  资本开支 / 收入", "%"), ("dep_rate", "  折旧率（占期初净值）", "%"),
        ("blank",),
        ("sec", "五、借款与利息"),
        ("debt_open", "期初借款", "百万元"), ("repay", "减：偿还借款", "百万元"),
        ("debt_close", "期末借款", "百万元"),
        ("int_rate", "  借款利率（按期初余额）", "%"), ("int_exp2", "利息费用", "百万元"),
        ("cash_rate", "  存款利率（按期初现金）", "%"), ("int_inc2", "利息收入", "百万元"),
        ("blank",),
        ("sec", "六、资产负债表"),
        ("cash", "货币资金", "百万元"), ("bs_ar", "应收账款", "百万元"), ("bs_inv", "存货", "百万元"),
        ("bs_ppe", "固定资产（净）", "百万元"), ("other", "其他非流动资产", "百万元"),
        ("ta", "资产合计", "百万元"),
        ("bs_ap", "应付账款", "百万元"), ("bs_debt", "银行借款", "百万元"),
        ("tl", "负债合计", "百万元"),
        ("paid_in", "实收资本（股本+资本公积）", "百万元"), ("re", "留存收益", "百万元"),
        ("te", "所有者权益合计", "百万元"),
        ("tle", "负债和所有者权益合计", "百万元"),
        ("bs_chk", "平衡检查：资产 − 负债和权益（应为 0）", "百万元"),
        ("blank",),
        ("sec", "七、现金流量表（间接法）"),
        ("cf_ni", "净利润", "百万元"), ("cf_da", "加：折旧摊销", "百万元"),
        ("cf_ar", "减：应收账款增加", "百万元"), ("cf_inv", "减：存货增加", "百万元"),
        ("cf_ap", "加：应付账款增加", "百万元"),
        ("cfo", "经营活动现金流", "百万元"),
        ("cf_capex", "资本开支", "百万元"), ("cfi", "投资活动现金流", "百万元"),
        ("cf_debt", "借款净变动", "百万元"), ("cf_div", "支付股利", "百万元"), ("payout", "  分红率", "%"),
        ("cff", "筹资活动现金流", "百万元"),
        ("cf_net", "现金净增加", "百万元"), ("cash_open", "期初现金", "百万元"),
        ("cash_close", "期末现金", "百万元"),
        ("blank",),
        ("sec", "八、检查"),
        ("chk_bs", "资产负债表平衡", ""), ("chk_cash", "现金流量表期末现金 = 资产负债表货币资金", ""),
        ("chk_pos", "现金不为负", ""),
    ]
    R = {}
    row = 5
    for it in layout:
        if it[0] not in ("sec", "blank"):
            R[it[0]] = row
        row += 1
    last_row = row - 1

    # 假设页布局
    a_layout = [
        ("sec", "收入"),
        ("vol_g_1", "销量增长率 — 基准", "%"), ("vol_g_2", "销量增长率 — 乐观", "%"),
        ("vol_g_3", "销量增长率 — 悲观", "%"), ("vol_g", "销量增长率 — 使用中", "%"),
        ("price_g", "均价增长率", "%"),
        ("sec", "成本费用"),
        ("cogs_1", "成本率 — 基准", "%"), ("cogs_2", "成本率 — 乐观", "%"), ("cogs_3", "成本率 — 悲观", "%"),
        ("cogs_pct", "成本率 — 使用中", "%"),
        ("sell_pct", "销售费用率", "%"), ("admin_pct", "管理及其他费用率", "%"),
        ("sec", "营运资本"),
        ("dso", "应收账款周转天数", "天"), ("dio", "存货周转天数", "天"), ("dpo", "应付账款周转天数", "天"),
        ("sec", "固定资产"),
        ("capex_pct", "资本开支 / 收入", "%"), ("dep_rate", "折旧率（占期初净值）", "%"),
        ("sec", "融资与其他"),
        ("repay", "每年偿还借款", "百万元"), ("int_rate", "借款利率", "%"), ("cash_rate", "存款利率", "%"),
        ("tax", "所得税率", "%"), ("payout", "分红率（占净利润）", "%"), ("nonop", "营业外收支净额", "百万元"),
    ]
    AR_ = {}
    row = 6
    for it in a_layout:
        if it[0] != "sec":
            AR_[it[0]] = row
        row += 1

    # ---- 写假设页 ----
    wa["A1"] = "假设：所有预测参数只在这里输入一次（蓝色 = 输入，黄色 = 关键开关）"; wa["A1"].font = TITLE
    wa["A2"] = "情景选择（1=基准，2=乐观，3=悲观）"; wa["A2"].font = BOLD
    wa["C2"] = 1; wa["C2"].font = BLUE; wa["C2"].fill = YELLOW
    dv = DataValidation(type="list", formula1='"1,2,3"', allow_blank=False)
    wa.add_data_validation(dv); dv.add("C2")
    wa["D2"] = '=CHOOSE($C$2,"基准情景","乐观情景","悲观情景")'; wa["D2"].font = BOLD
    wa["A3"] = "历史列（D–F）显示实际比率，帮你判断假设是否合理；预测列（G–K）是输入。"; wa["A3"].font = GREY
    for i, h in enumerate(["假设", "单位", "依据 / 说明"] + [f"{y}A" for y in HIST] + [f"{y}E" for y in FC]):
        c = wa.cell(row=4, column=i + 1, value=h); c.font = Font(name="Arial", bold=True, color="FFFFFF"); c.fill = HEAD_FILL
    a_notes = {
        "vol_g_1": "增速逐年放缓，向行业增速（约 5%）回归",
        "vol_g_2": "新品类成功 + 渠道扩张",
        "vol_g_3": "竞争加剧，接近行业平均以下",
        "vol_g": "=CHOOSE(情景, 基准, 乐观, 悲观)",
        "price_g": "略高于通胀，品牌提价能力有限",
        "cogs_1": "维持 2025 年水平",
        "cogs_pct": "=CHOOSE(情景, 基准, 乐观, 悲观)",
        "sell_pct": "历史 20%–20.5%",
        "admin_pct": "规模效应，略低于历史",
        "dso": "接近历史平均", "dio": "接近 2025 年", "dpo": "接近历史平均",
        "capex_pct": "扩产高峰已过，略低于历史",
        "dep_rate": "历史约 9.5%",
        "repay": "按借款合同还款计划",
        "tax": "法定税率 25%",
        "payout": "历史分红率 30%",
        "nonop": "一次性项目不做预测",
    }
    hist_link = {"vol_g": "vol_g", "price_g": "price_g", "cogs_pct": "cogs_pct", "sell_pct": "sell_pct",
                 "admin_pct": "admin_pct", "dso": "dso", "dio": "dio", "dpo": "dpo", "capex_pct": "capex_pct",
                 "dep_rate": "dep_rate", "int_rate": "int_rate", "cash_rate": "cash_rate", "tax": "tax_rate",
                 "payout": "payout", "nonop": "nonop", "repay": "repay"}
    row = 6
    for it in a_layout:
        if it[0] == "sec":
            c = wa.cell(row=row, column=1, value=it[1]); c.font = SECTION
            for col in range(1, 12):
                wa.cell(row=row, column=col).fill = SEC_FILL
            row += 1
            continue
        key, label, unit = it
        wa.cell(row=row, column=1, value=label).font = BOLD if key in ("vol_g", "cogs_pct") else BLACK
        wa.cell(row=row, column=2, value=unit).font = GREY
        if key in a_notes:
            note(wa, row, 3, a_notes[key])
        fmt = PCT if unit == "%" else (DAYS if unit == "天" else NUM)
        if key in hist_link:
            for col in COLS_HIST:
                if key in ("vol_g", "price_g") and col == "D":
                    continue
                c = wa.cell(row=row, column=ord(col) - 64, value=f"=模型!{col}{R[hist_link[key]]}")
                c.font = GREEN; c.number_format = fmt
        for i, col in enumerate(COLS_FC):
            if key == "vol_g":
                v = f"=CHOOSE($C$2,{col}{AR_['vol_g_1']},{col}{AR_['vol_g_2']},{col}{AR_['vol_g_3']})"
                font = BLACK
            elif key == "cogs_pct":
                v = f"=CHOOSE($C$2,{col}{AR_['cogs_1']},{col}{AR_['cogs_2']},{col}{AR_['cogs_3']})"
                font = BLACK
            else:
                src = {"vol_g_1": ASSUME["vol_g"][1], "vol_g_2": ASSUME["vol_g"][2], "vol_g_3": ASSUME["vol_g"][3],
                       "cogs_1": ASSUME["cogs_pct"][1], "cogs_2": ASSUME["cogs_pct"][2],
                       "cogs_3": ASSUME["cogs_pct"][3]}.get(key) or ASSUME[key]
                v = src[i]
                font = BLUE
            c = wa.cell(row=row, column=ord(col) - 64, value=v)
            c.font = font; c.number_format = fmt
        row += 1
    set_widths(wa, {"A": 26, "B": 8, "C": 34, **{c: 10 for c in COLS}})
    wa.freeze_panes = "D5"

    # ---- 写模型页 ----
    wmod["A1"] = f"{COMPANY}（虚构） 三表模型　单位：百万元（除特别注明）"; wmod["A1"].font = TITLE
    wmod["A2"] = "模型检查："; wmod["A2"].font = BOLD
    wmod["C2"] = '=IF(AND(K{a},K{b},K{c}),"✔ 全部通过","✘ 有错误，请看第八部分")'.format(
        a=R["chk_bs"], b=R["chk_cash"], c=R["chk_pos"])
    wmod["C2"].font = Font(name="Arial", size=11, bold=True, color="C00000")
    wmod["D2"] = '=假设!D2'; wmod["D2"].font = GREEN
    for i, h in enumerate(["科目", "单位", "预测期计算逻辑"] + [f"{y}A" for y in HIST] + [f"{y}E" for y in FC]):
        c = wmod.cell(row=3, column=i + 1, value=h); c.font = Font(name="Arial", bold=True, color="FFFFFF"); c.fill = HEAD_FILL
        c.alignment = Alignment(horizontal="center" if i > 2 else "left")
    wmod["D4"] = "← 实际（历史）"; wmod["G4"] = "预测 →"
    wmod["D4"].font = GREY; wmod["G4"].font = GREY

    A_ = lambda k, c: f"假设!{c}{AR_[k]}"
    HD = lambda k, c: f"历史数据!{c}{HR[k]}"

    # 历史列公式
    def hist_formula(key, c):
        p = prev_col(c)
        first = c == "D"
        m = {
            "vol": f"={HD('vol', c)}",
            "vol_g": None if first else f"={c}{R['vol']}/{p}{R['vol']}-1",
            "price": f"={HD('price', c)}",
            "price_g": None if first else f"={c}{R['price']}/{p}{R['price']}-1",
            "rev": f"={HD('rev', c)}",
            "rev_g": None if first else f"={c}{R['rev']}/{p}{R['rev']}-1",
            "cogs": f"={HD('cogs', c)}", "sell": f"={HD('sell', c)}", "admin": f"={HD('admin', c)}",
            "da": f"={c}{R['ppe_da']}",
            "int_exp": f"={HD('int_exp', c)}", "int_inc": f"={HD('int_inc', c)}",
            "nonop": f"={HD('nonop', c)}", "tax": f"={HD('tax', c)}",
            "ar": f"={HD('ar', c)}", "inv": f"={HD('inv', c)}", "ap": f"={HD('ap', c)}",
            "dnwc": f"={c}{R['nwc']}-({HD('ar', p)}+{HD('inv', p)}-{HD('ap', p)})" if first
            else f"={c}{R['nwc']}-{p}{R['nwc']}",
            "ppe_open": f"={HD('ppe', p)}" if first else f"={p}{R['ppe_close']}",
            "capex": f"={HD('capex', c)}",
            "ppe_da": f"={HD('da', c)}",
            "debt_open": f"={HD('debt', p)}" if first else f"={p}{R['debt_close']}",
            "repay": f"={c}{R['debt_open']}-{c}{R['debt_close']}",
            "debt_close": f"={HD('debt', c)}",
            "int_rate": f"={c}{R['int_exp']}/{c}{R['debt_open']}",
            "int_exp2": f"={c}{R['int_exp']}",
            "cash_rate": f"={c}{R['int_inc']}/{c}{R['cash_open']}",
            "int_inc2": f"={c}{R['int_inc']}",
            "cash": f"={HD('cash', c)}",
            "other": f"={HD('other', c)}",
            "paid_in": f"={HD('paid_in', c)}", "re": f"={HD('re', c)}",
            "cf_div": f"=-{HD('div', c)}",
            "cash_open": f"={HD('cash', p)}" if first else f"={p}{R['cash']}",
        }
        return m.get(key, "COMMON")

    def fc_formula(key, c):
        p = prev_col(c)
        m = {
            "vol": f"={p}{R['vol']}*(1+{c}{R['vol_g']})",
            "vol_g": f"={A_('vol_g', c)}",
            "price": f"={p}{R['price']}*(1+{c}{R['price_g']})",
            "price_g": f"={A_('price_g', c)}",
            "rev": f"={c}{R['vol']}*{c}{R['price']}/100",
            "rev_g": f"={c}{R['rev']}/{p}{R['rev']}-1",
            "cogs": f"={c}{R['is_rev']}*{c}{R['cogs_pct']}",
            "cogs_pct": f"={A_('cogs_pct', c)}",
            "sell": f"={c}{R['is_rev']}*{c}{R['sell_pct']}",
            "sell_pct": f"={A_('sell_pct', c)}",
            "admin": f"={c}{R['is_rev']}*{c}{R['admin_pct']}",
            "admin_pct": f"={A_('admin_pct', c)}",
            "da": f"={c}{R['ppe_da']}",
            "int_exp": f"={c}{R['int_exp2']}",
            "int_inc": f"={c}{R['int_inc2']}",
            "nonop": f"={A_('nonop', c)}",
            "tax": f"=MAX(0,{c}{R['ebt']}*{c}{R['tax_rate']})",
            "tax_rate": f"={A_('tax', c)}",
            "ar": f"={c}{R['is_rev']}*{c}{R['dso']}/365",
            "dso": f"={A_('dso', c)}",
            "inv": f"={c}{R['cogs']}*{c}{R['dio']}/365",
            "dio": f"={A_('dio', c)}",
            "ap": f"={c}{R['cogs']}*{c}{R['dpo']}/365",
            "dpo": f"={A_('dpo', c)}",
            "dnwc": f"={c}{R['nwc']}-{p}{R['nwc']}",
            "ppe_open": f"={p}{R['ppe_close']}",
            "capex": f"={c}{R['is_rev']}*{c}{R['capex_pct']}",
            "capex_pct": f"={A_('capex_pct', c)}",
            "ppe_da": f"={c}{R['ppe_open']}*{c}{R['dep_rate']}",
            "dep_rate": f"={A_('dep_rate', c)}",
            "debt_open": f"={p}{R['debt_close']}",
            "repay": f"=MIN({A_('repay', c)},{c}{R['debt_open']})",
            "debt_close": f"={c}{R['debt_open']}-{c}{R['repay']}",
            "int_rate": f"={A_('int_rate', c)}",
            "int_exp2": f"={c}{R['debt_open']}*{c}{R['int_rate']}",
            "cash_rate": f"={A_('cash_rate', c)}",
            "int_inc2": f"={c}{R['cash_open']}*{c}{R['cash_rate']}",
            "cash": f"={c}{R['cash_close']}",
            "other": f"={p}{R['other']}",
            "paid_in": f"={p}{R['paid_in']}",
            "re": f"={p}{R['re']}+{c}{R['ni']}+{c}{R['cf_div']}",
            "cf_div": f"=-{c}{R['ni']}*{c}{R['payout']}",
            "payout": f"={A_('payout', c)}",
            "cash_open": f"={p}{R['cash']}",
        }
        return m.get(key, "COMMON")

    def common_formula(key, c):
        p = prev_col(c)
        m = {
            "is_rev": f"={c}{R['rev']}",
            "cogs_pct": f"={c}{R['cogs']}/{c}{R['is_rev']}",
            "sell_pct": f"={c}{R['sell']}/{c}{R['is_rev']}",
            "admin_pct": f"={c}{R['admin']}/{c}{R['is_rev']}",
            "ebitda": f"={c}{R['is_rev']}-{c}{R['cogs']}-{c}{R['sell']}-{c}{R['admin']}",
            "ebitda_m": f"={c}{R['ebitda']}/{c}{R['is_rev']}",
            "ebit": f"={c}{R['ebitda']}-{c}{R['da']}",
            "ebt": f"={c}{R['ebit']}-{c}{R['int_exp']}+{c}{R['int_inc']}+{c}{R['nonop']}",
            "tax_rate": f"=IF({c}{R['ebt']}=0,0,{c}{R['tax']}/{c}{R['ebt']})",
            "ni": f"={c}{R['ebt']}-{c}{R['tax']}",
            "ni_m": f"={c}{R['ni']}/{c}{R['is_rev']}",
            "eps": f"={c}{R['ni']}/估值!$C${{SHARES_ROW}}",
            "dso": f"={c}{R['ar']}/{c}{R['is_rev']}*365",
            "dio": f"={c}{R['inv']}/{c}{R['cogs']}*365",
            "dpo": f"={c}{R['ap']}/{c}{R['cogs']}*365",
            "nwc": f"={c}{R['ar']}+{c}{R['inv']}-{c}{R['ap']}",
            "ppe_close": f"={c}{R['ppe_open']}+{c}{R['capex']}-{c}{R['ppe_da']}",
            "capex_pct": f"={c}{R['capex']}/{c}{R['is_rev']}",
            "dep_rate": f"={c}{R['ppe_da']}/{c}{R['ppe_open']}",
            "bs_ar": f"={c}{R['ar']}", "bs_inv": f"={c}{R['inv']}", "bs_ppe": f"={c}{R['ppe_close']}",
            "ta": f"={c}{R['cash']}+{c}{R['bs_ar']}+{c}{R['bs_inv']}+{c}{R['bs_ppe']}+{c}{R['other']}",
            "bs_ap": f"={c}{R['ap']}", "bs_debt": f"={c}{R['debt_close']}",
            "tl": f"={c}{R['bs_ap']}+{c}{R['bs_debt']}",
            "te": f"={c}{R['paid_in']}+{c}{R['re']}",
            "tle": f"={c}{R['tl']}+{c}{R['te']}",
            "bs_chk": f"={c}{R['ta']}-{c}{R['tle']}",
            "cf_ni": f"={c}{R['ni']}",
            "cf_da": f"={c}{R['da']}",
            "cf_ar": (f"=-({c}{R['ar']}-{p}{R['ar']})" if c != "D"
                      else f"=-({c}{R['ar']}-{HD('ar', 'C')})"),
            "cf_inv": (f"=-({c}{R['inv']}-{p}{R['inv']})" if c != "D"
                       else f"=-({c}{R['inv']}-{HD('inv', 'C')})"),
            "cf_ap": (f"={c}{R['ap']}-{p}{R['ap']}" if c != "D" else f"={c}{R['ap']}-{HD('ap', 'C')}"),
            "cfo": f"=SUM({c}{R['cf_ni']}:{c}{R['cf_ap']})",
            "cf_capex": f"=-{c}{R['capex']}",
            "cfi": f"={c}{R['cf_capex']}",
            "cf_debt": f"={c}{R['debt_close']}-{c}{R['debt_open']}",
            "payout": f"=-{c}{R['cf_div']}/{c}{R['ni']}",
            "cff": f"={c}{R['cf_debt']}+{c}{R['cf_div']}",
            "cf_net": f"={c}{R['cfo']}+{c}{R['cfi']}+{c}{R['cff']}",
            "cash_close": f"={c}{R['cash_open']}+{c}{R['cf_net']}",
            "chk_bs": f"=ABS({c}{R['bs_chk']})<0.001",
            "chk_cash": f"=ABS({c}{R['cash_close']}-{c}{R['cash']})<0.001",
            "chk_pos": f"={c}{R['cash']}>=0",
        }
        return m.get(key)

    fmt_of = {"%": PCT, "天": DAYS, "元/股": PRICE_FMT, "元/箱": PRICE_FMT, "万箱": NUM0, "百万元": NUM, "": "General"}
    logic = {
        "vol": "上年 ×（1 + 销量增长率）", "vol_g": "链接假设页", "price": "上年 ×（1 + 均价增长率）",
        "price_g": "链接假设页", "rev": "销量 × 均价 ÷ 100（万箱×元=万元，÷100=百万元）",
        "rev_g": "本年 ÷ 上年 − 1", "is_rev": "链接收入预测",
        "cogs": "收入 × 成本率", "sell": "收入 × 销售费用率", "admin": "收入 × 费用率",
        "ebitda": "收入 − 成本 − 销售费用 − 管理费用", "da": "链接固定资产表",
        "ebit": "EBITDA − 折旧摊销", "int_exp": "链接借款表", "int_inc": "链接借款表",
        "nonop": "一次性项目，预测为 0", "ebt": "EBIT − 利息费用 + 利息收入 + 营业外",
        "tax": "MAX(0, 税前利润 × 税率)", "ni": "税前利润 − 所得税", "eps": "净利润 ÷ 总股本",
        "ar": "收入 × DSO ÷ 365", "inv": "营业成本 × DIO ÷ 365", "ap": "营业成本 × DPO ÷ 365",
        "nwc": "应收 + 存货 − 应付", "dnwc": "本年营运资本 − 上年",
        "ppe_open": "= 上年期末净值", "capex": "收入 × 资本开支比例", "ppe_da": "期初净值 × 折旧率",
        "ppe_close": "期初 + 资本开支 − 折旧", "debt_open": "= 上年期末借款", "repay": "MIN(计划还款, 期初借款)",
        "debt_close": "期初 − 偿还", "int_exp2": "期初借款 × 利率（不产生循环引用）",
        "int_inc2": "期初现金 × 存款利率", "cash": "链接现金流量表期末现金",
        "other": "保持不变 = 上年", "paid_in": "= 上年（无增发）", "re": "上年 + 净利润 − 股利",
        "bs_chk": "必须每年都是 0", "cf_ar": "−（本年 − 上年）：资产增加占用现金",
        "cf_inv": "−（本年 − 上年）", "cf_ap": "+（本年 − 上年）：负债增加提供现金",
        "cfo": "以上加总", "cf_capex": "−资本开支", "cf_debt": "期末借款 − 期初借款",
        "cf_div": "−净利润 × 分红率", "cash_open": "= 上年期末货币资金", "cash_close": "期初 + 净增加",
    }
    bold_keys = {"rev", "is_rev", "ebitda", "ebit", "ebt", "ni", "nwc", "ppe_close", "debt_close", "ta",
                 "tl", "te", "tle", "cfo", "cfi", "cff", "cash_close"}
    todo_cells = []
    row = 5
    for it in layout:
        if it[0] == "blank":
            row += 1
            continue
        if it[0] == "sec":
            c = wmod.cell(row=row, column=1, value=it[1]); c.font = SECTION
            for col in range(1, 12):
                wmod.cell(row=row, column=col).fill = SEC_FILL
            row += 1
            continue
        key, label, unit = it
        wmod.cell(row=row, column=1, value=label).font = BOLD if key in bold_keys else BLACK
        wmod.cell(row=row, column=2, value=unit).font = GREY
        if key in logic:
            note(wmod, row, 3, logic[key])
        for col in COLS:
            is_hist = col in COLS_HIST
            if key in ("chk_bs", "chk_cash", "chk_pos"):
                f = common_formula(key, col)
            else:
                f = hist_formula(key, col) if is_hist else fc_formula(key, col)
                if f == "COMMON":
                    f = common_formula(key, col)
            if f is None:
                continue
            cell = wmod.cell(row=row, column=ord(col) - 64, value=f)
            font = BLACK
            if "假设!" in f or "历史数据!" in f or "估值!" in f:
                font = GREEN
            cell.font = Font(name="Arial", size=10, bold=key in bold_keys, color=font.color)
            cell.number_format = fmt_of.get(unit, NUM)
            if key in ("chk_bs", "chk_cash", "chk_pos"):
                cell.number_format = "General"
            if key in ("ta", "tle", "cfo", "cash_close", "ni", "ebit"):
                cell.border = TOP_LINE
            if not is_hist:
                todo_cells.append(cell)
        row += 1
    set_widths(wmod, {"A": 36, "B": 8, "C": 40, **{c: 11 for c in COLS}})
    wmod.freeze_panes = "D4"

    # ---- 估值页 ----
    wv["A1"] = "估值：DCF（自由现金流折现）　单位：百万元"; wv["A1"].font = TITLE
    wv["A2"] = "估值基准日：2025-12-31（年末折现，不使用年中惯例）"; wv["A2"].font = GREY
    VR = {}
    v_inputs = [
        ("sec", "第 1 步：折现率 WACC"),
        ("rf", "无风险利率 Rf", "%", VAL["rf"], "10 年期国债收益率（示例取值，使用时请查最新数据）"),
        ("beta", "贝塔 β", "", VAL["beta"], "可比公司去杠杆再加杠杆后的 β（示例）"),
        ("erp", "市场风险溢价 ERP", "%", VAL["erp"], "示例取值；常见区间 5%–7%"),
        ("ke", "股权成本 Ke = Rf + β × ERP", "%", None, ""),
        ("kd", "税前债务成本 Kd", "%", VAL["kd"], "与借款利率一致"),
        ("t", "所得税率", "%", None, "链接假设页"),
        ("kd_at", "税后债务成本 = Kd × (1 − 税率)", "%", None, ""),
        ("dv", "目标负债占比 D/(D+E)", "%", VAL["dv"], "参考行业平均资本结构（市值口径）"),
        ("ev_w", "股权占比 E/(D+E)", "%", None, ""),
        ("wacc", "WACC", "%", None, ""),
        ("g", "永续增长率 g", "%", VAL["g"], "不高于长期名义 GDP 增速；必须小于 WACC"),
        ("shares", "总股本", "百万股", SHARES, "5 亿股"),
        ("price", "当前股价", "元/股", PRICE, "虚构"),
    ]
    row = 4
    for it in v_inputs:
        if it[0] == "sec":
            c = wv.cell(row=row, column=1, value=it[1]); c.font = SECTION
            for col in range(1, 12):
                wv.cell(row=row, column=col).fill = SEC_FILL
            row += 1
            continue
        VR[it[0]] = row
        row += 1
    for it in v_inputs:
        if it[0] == "sec":
            continue
        key, label, unit, val, note_txt = it
        r_ = VR[key]
        wv.cell(row=r_, column=1, value=label).font = BOLD if key in ("wacc", "ke") else BLACK
        wv.cell(row=r_, column=2, value=unit).font = GREY
        fmt = PCT if unit == "%" else (PRICE_FMT if unit in ("元/股", "") else NUM)
        if key == "beta":
            fmt = "0.00"
        if val is not None:
            c = wv.cell(row=r_, column=3, value=val); c.font = BLUE; c.number_format = fmt
        else:
            fml = {"ke": f"=C{VR['rf']}+C{VR['beta']}*C{VR['erp']}",
                   "t": f"=假设!G{AR_['tax']}",
                   "kd_at": f"=C{VR['kd']}*(1-C{VR['t']})",
                   "ev_w": f"=1-C{VR['dv']}",
                   "wacc": f"=C{VR['ev_w']}*C{VR['ke']}+C{VR['dv']}*C{VR['kd_at']}"}[key]
            c = wv.cell(row=r_, column=3, value=fml)
            c.font = GREEN if "假设!" in fml else BLACK
            c.number_format = fmt
            if key == "wacc":
                c.font = Font(name="Arial", size=10, bold=True)
                c.fill = SUB_FILL
            if key != "t":
                todo_cells.append(c)
        if note_txt:
            note(wv, r_, 4, note_txt)

    row += 1
    c = wv.cell(row=row, column=1, value="第 2 步：自由现金流 FCFF"); c.font = SECTION
    for col in range(1, 12):
        wv.cell(row=row, column=col).fill = SEC_FILL
    row += 1
    for i, h in enumerate(["项目", "单位", "计算逻辑", "", "", ""] + [f"{y}E" for y in FC]):
        if h:
            cc = wv.cell(row=row, column=i + 1, value=h); cc.font = Font(name="Arial", bold=True, color="FFFFFF"); cc.fill = HEAD_FILL
    for col in "DEF":
        wv[f"{col}{row}"].fill = HEAD_FILL
    row += 1
    f_rows = [
        ("f_ebit", "EBIT", "链接模型", lambda c: f"=模型!{c}{R['ebit']}"),
        ("f_tax", "减：EBIT × 税率", "EBIT × 税率（不是实际所得税）", lambda c: f"=-{c}{{f_ebit}}*假设!{c}{AR_['tax']}"),
        ("f_nopat", "NOPAT（税后经营利润）", "EBIT − 税", lambda c: f"={c}{{f_ebit}}+{c}{{f_tax}}"),
        ("f_da", "加：折旧摊销", "非现金费用加回", lambda c: f"=模型!{c}{R['da']}"),
        ("f_capex", "减：资本开支", "", lambda c: f"=-模型!{c}{R['capex']}"),
        ("f_dnwc", "减：营运资本增加", "", lambda c: f"=-模型!{c}{R['dnwc']}"),
        ("f_fcff", "FCFF", "NOPAT + 折旧 − 资本开支 − 营运资本增加", lambda c: f"={c}{{f_nopat}}+{c}{{f_da}}+{c}{{f_capex}}+{c}{{f_dnwc}}"),
        ("f_t", "折现期数 t", "距估值基准日的年数", None),
        ("f_df", "折现因子", "1 ÷（1 + WACC）^ t", lambda c: f"=1/(1+$C${VR['wacc']})^{c}{{f_t}}"),
        ("f_pv", "FCFF 现值", "FCFF × 折现因子", lambda c: f"={c}{{f_fcff}}*{c}{{f_df}}"),
    ]
    for key, *_ in f_rows:
        VR[key] = row
        row += 1
    for key, label, note_txt, fn in f_rows:
        r_ = VR[key]
        wv.cell(row=r_, column=1, value=label).font = BOLD if key in ("f_fcff", "f_nopat") else BLACK
        wv.cell(row=r_, column=2, value="" if key == "f_t" else ("" if key == "f_df" else "百万元")).font = GREY
        note(wv, r_, 3, note_txt)
        for i, col in enumerate(COLS_FC):
            if key == "f_t":
                c = wv.cell(row=r_, column=ord(col) - 64, value=i + 1); c.font = BLUE; c.number_format = "0"
                continue
            f = fn(col)
            for k2, rr in VR.items():
                f = f.replace("{" + k2 + "}", str(rr))
            c = wv.cell(row=r_, column=ord(col) - 64, value=f)
            c.font = Font(name="Arial", size=10, bold=key == "f_fcff",
                          color="008000" if ("模型!" in f or "假设!" in f) else "000000")
            c.number_format = "0.0000" if key == "f_df" else NUM
            todo_cells.append(c)

    row += 1
    c = wv.cell(row=row, column=1, value="第 3 步：终值、企业价值与每股价值"); c.font = SECTION
    for col in range(1, 12):
        wv.cell(row=row, column=col).fill = SEC_FILL
    row += 1
    bridge = [
        ("sum_pv", "预测期 FCFF 现值合计", NUM, f"=SUM(G{VR['f_pv']}:K{VR['f_pv']})", ""),
        ("tv", "终值 TV（2030 年末）", NUM, f"=K{VR['f_fcff']}*(1+C{VR['g']})/(C{VR['wacc']}-C{VR['g']})",
         "= FCFF₂₀₃₀ ×（1 + g）÷（WACC − g）"),
        ("pv_tv", "终值现值", NUM, f"=C{{tv}}*K{VR['f_df']}", "= TV × 第 5 年折现因子"),
        ("ev", "企业价值 EV", NUM, f"=C{{sum_pv}}+C{{pv_tv}}", ""),
        ("tv_share", "  终值占企业价值比例", PCT, f"=C{{pv_tv}}/C{{ev}}", "通常 60%–80%；太高说明价值过于依赖远期"),
        ("debt", "减：借款（2025 年末）", NUM, f"=-模型!F{R['debt_close']}", ""),
        ("cash", "加：现金（2025 年末）", NUM, f"=模型!F{R['cash']}", ""),
        ("equity", "股权价值", NUM, f"=C{{ev}}+C{{debt}}+C{{cash}}", ""),
        ("ps", "每股价值", PRICE_FMT, f"=C{{equity}}/C{VR['shares']}", "元/股"),
        ("upside", "相对当前股价的上涨空间", PCT, f"=C{{ps}}/C{VR['price']}-1", ""),
        ("imp_mult", "隐含 EV / EBITDA（2026E）", MULT, f"=C{{ev}}/模型!G{R['ebitda']}", "和可比公司倍数对比，做交叉验证"),
        ("imp_exit", "终值隐含 EV / EBITDA（2030E）", MULT, f"=C{{tv}}/模型!K{R['ebitda']}", ""),
    ]
    for key, *_ in bridge:
        VR[key] = row
        row += 1
    for key, label, fmt, f, note_txt in bridge:
        r_ = VR[key]
        for k2, rr in VR.items():
            f = f.replace("{" + k2 + "}", str(rr))
        wv.cell(row=r_, column=1, value=label).font = BOLD if key in ("ev", "equity", "ps") else BLACK
        c = wv.cell(row=r_, column=3, value=f)
        c.font = Font(name="Arial", size=10, bold=key in ("ev", "equity", "ps"),
                      color="008000" if "模型!" in f else "000000")
        c.number_format = fmt
        if key == "ps":
            c.fill = SUB_FILL
        if note_txt:
            note(wv, r_, 4, note_txt)
        todo_cells.append(c)

    row += 1
    c = wv.cell(row=row, column=1, value="第 4 步：敏感性分析——每股价值（元）随 WACC 和 g 变化"); c.font = SECTION
    for col in range(1, 12):
        wv.cell(row=row, column=col).fill = SEC_FILL
    row += 1
    wv.cell(row=row, column=1, value="用公式直接计算（任何 Excel/WPS 都能用）。也可以用\"模拟运算表\"做，见网站第 5 章。").font = GREY
    row += 1
    hdr_r = row
    wv.cell(row=hdr_r, column=3, value="WACC ↓  /  g →").font = BOLD
    g_steps = [-0.01, -0.005, 0, 0.005, 0.01]
    w_steps = [-0.01, -0.005, 0, 0.005, 0.01]
    gcols = ["D", "E", "F", "G", "H"]
    for gc, st in zip(gcols, g_steps):
        cc = wv[f"{gc}{hdr_r}"]; cc.value = f"=$C${VR['g']}+({st})"; cc.number_format = PCT; cc.font = BOLD; cc.fill = SUB_FILL
    sens_rows = []
    for i, st in enumerate(w_steps):
        rr = hdr_r + 1 + i
        sens_rows.append(rr)
        cc = wv[f"C{rr}"]; cc.value = f"=$C${VR['wacc']}+({st})"; cc.number_format = PCT; cc.font = BOLD; cc.fill = SUB_FILL
        for gc in gcols:
            fml = (f"=(SUMPRODUCT($G${VR['f_fcff']}:$K${VR['f_fcff']},1/(1+$C{rr})^$G${VR['f_t']}:$K${VR['f_t']})"
                   f"+$K${VR['f_fcff']}*(1+{gc}${hdr_r})/($C{rr}-{gc}${hdr_r})/(1+$C{rr})^$K${VR['f_t']}"
                   f"+$C${VR['debt']}+$C${VR['cash']})/$C${VR['shares']}")
            cc = wv[f"{gc}{rr}"]; cc.value = fml; cc.number_format = PRICE_FMT; cc.font = BLACK
            todo_cells.append(cc)
    set_widths(wv, {"A": 34, "B": 8, "C": 16, "D": 12, "E": 12, "F": 12, "G": 12, "H": 12, "I": 11, "J": 11, "K": 11})

    # EPS 公式里的股本行号
    for col in COLS:
        cell = wmod[f"{col}{R['eps']}"]
        if isinstance(cell.value, str):
            cell.value = cell.value.replace("{SHARES_ROW}", str(VR["shares"]))
            cell.font = Font(name="Arial", size=10, color="008000")

    # ---------------- 说明页 ----------------
    write_readme(ws0, template)
    wb.move_sheet("原始数据", offset=-1)  # 顺序：说明、原始数据、映射表、历史数据……

    # 模板：清空预测期公式，标黄
    if template:
        for cell in todo_cells:
            cell.value = None
            cell.fill = TODO
        wmod["C2"] = "完成预测后，在第八部分写检查公式"
        wmod["C2"].font = GREY
        for col in COLS_FC:
            for key in ("chk_bs", "chk_cash", "chk_pos"):
                wmod[f"{col}{R[key]}"].value = None
                wmod[f"{col}{R[key]}"].fill = TODO
        # 估值页：保留输入，清空计算
    # 打印/视图
    for ws in (wmod, wa, wv, wh):
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 90
    wb.active = wb.sheetnames.index("说明")
    return wb, R, AR_, VR, HR, sens_rows, gcols


def write_readme(ws, template):
    ws.sheet_view.showGridLines = False
    lines = [
        (f"{COMPANY}（虚构公司）财务建模练习" + ("　——　练习模板" if template else "　——　参考答案"), TITLE),
        ("", None),
        ("这个文件配合网站《财务建模实操课》第 6 章使用。公司和数据都是虚构的，仅用于练习。", None),
        ("", None),
        ("颜色规范", BOLD),
        ("蓝色数字 = 手动输入（原始数据、假设）", BLUE),
        ("黑色数字 = 本表公式", BLACK),
        ("绿色数字 = 引用其他工作表", GREEN),
        ("黄色底色 = 关键开关 / 练习时需要你填写的单元格", None),
        ("", None),
        ("工作表顺序（也是建模顺序）", BOLD),
        ("1. 原始数据：从网站\"下载\"的报表，原样保存，单位为元，年份从新到旧", None),
        ("2. 映射表：原始科目 → 标准科目（多对一合并，合计行标\"忽略\"）", None),
        ("3. 历史数据：SUMIFS 按标准科目汇总、换算为百万元，并做勾稽校验", None),
        ("4. 假设：所有预测参数，含情景开关（C2 单元格：1 基准 / 2 乐观 / 3 悲观）", None),
        ("5. 模型：收入 → 利润表 → 营运资本 → 固定资产 → 借款 → 资产负债表 → 现金流量表 → 检查", None),
        ("6. 估值：WACC → FCFF → 终值 → 企业价值 → 每股价值 → 敏感性分析", None),
        ("", None),
    ]
    if template:
        lines += [
            ("怎么用这个模板", BOLD),
            ("· 原始数据、映射表、历史数据、假设已经做好，你从\"模型\"页 G 列（2026E）开始写公式。", None),
            ("· 每一行的 C 列写了计算逻辑，照着写；写好 G 列后向右拖到 K 列（Ctrl+R）。", None),
            ("· 推荐顺序：收入 → 利润表到 EBIT → 固定资产 → 借款 → 利润表其余 → 营运资本 → 资产负债表 → 现金流量表。", None),
            ("· 写完后第 76 行的\"平衡检查\"每年都应该是 0；不平就看网站 4.11 节的排错方法。", None),
            ("· 再完成\"估值\"页的黄色单元格。对照网站上的检查点数字核对。", None),
        ]
    else:
        lines += [
            ("怎么用参考答案", BOLD),
            ("· 先自己用练习模板做，卡住了再来看对应单元格的公式（选中单元格看编辑栏，或按 Ctrl+` 显示全部公式）。", None),
            ("· 试试把\"假设\"页 C2 改成 2 或 3，看估值怎么变。", None),
            ("· 试试改任何一个蓝色假设，\"模型\"页 C2 的检查结果应该始终是\"✔ 全部通过\"。", None),
        ]
    for i, (t, f) in enumerate(lines):
        c = ws.cell(row=i + 1, column=1, value=t)
        if f is not None:
            c.font = f
        else:
            c.font = Font(name="Arial", size=10)
        if "黄色底色" in t:
            c.fill = YELLOW
    ws.column_dimensions["A"].width = 110


# ---------------------------------------------------------------------------
# 8. 网站数据
# ---------------------------------------------------------------------------
def main():
    os.makedirs(OUT_PRACTICE, exist_ok=True)
    H = build_history()
    models = {s: build_forecast(H, s) for s in (1, 2, 3)}
    vals = {s: valuation(models[s]) for s in (1, 2, 3)}
    rows_raw = raw_rows(H)
    lines = write_csv(rows_raw)

    wb, R, AR_, VR, HR, sens_rows, gcols = build_workbook(rows_raw, H, models[1], template=False)
    ans_path = os.path.join(OUT_PRACTICE, f"{COMPANY}_参考答案.xlsx")
    wb.save(ans_path)
    wbt, *_ = build_workbook(rows_raw, H, models[1], template=True)
    tpl_path = os.path.join(OUT_PRACTICE, f"{COMPANY}_练习模板.xlsx")
    wbt.save(tpl_path)

    # 可选：输出行号信息，供外部校验脚本使用（python3 scripts/build_case.py --meta 路径）
    if "--meta" in sys.argv:
        meta = dict(R=R, AR=AR_, VR=VR, HR=HR, sens_rows=sens_rows, gcols=gcols)
        with open(sys.argv[sys.argv.index("--meta") + 1], "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)

    # 网站数据 ------------------------------------------------------------
    web_rows = []
    M = models[1]
    # 网站展示用的公式：从 Excel 实际写入的公式里取 2026E（G 列）
    ws = wb["模型"]
    for r in range(5, ws.max_row + 1):
        a = ws.cell(row=r, column=1).value
        if a is None:
            continue
        key = next((k for k, v in R.items() if v == r), None)
        if key is None:
            web_rows.append(dict(sec=a))
            continue
        if key.startswith("chk_"):
            continue
        unit = ws.cell(row=r, column=2).value or ""
        logic_txt = ws.cell(row=r, column=3).value or ""
        g_formula = ws.cell(row=r, column=7).value
        src_key = {"is_rev": "rev", "bs_ar": "ar", "bs_inv": "inv", "bs_ppe": "ppe_close", "bs_ap": "ap",
                   "bs_debt": "debt_close", "int_exp2": "int_exp", "int_inc2": "int_inc"}.get(key, key)
        values = {}
        for y in YEARS:
            v = M.get(src_key, {}).get(y)
            if v is not None:
                values[str(y)] = round(v, 6)
        web_rows.append(dict(key=key, row=r, label=a.strip(), unit=unit, logic=logic_txt,
                             formula=g_formula, values=values,
                             indent=a.startswith("  ")))

    def pick(model, keys):
        return {k: {str(y): round(model[k][y], 6) for y in YEARS if y in model[k]} for k in keys}

    keys_small = ["rev", "ebitda", "ebit", "ni", "eps", "cash", "debt_close", "ta", "cfo", "capex", "dnwc", "da",
                  "ebitda_m", "rev_g"]
    scen = {}
    for s in (1, 2, 3):
        v = vals[s]
        scen[str(s)] = dict(name=SCEN_NAMES[s], lines=pick(models[s], keys_small),
                            val={k: (round(x, 6) if isinstance(x, float) else x) for k, x in v.items()
                                 if not isinstance(x, dict)},
                            fcff={str(y): round(v["fcff"][y], 6) for y in FC})
    # 敏感性（基准）
    sens = []
    base = vals[1]
    for dw in [-0.01, -0.005, 0, 0.005, 0.01]:
        rowv = []
        for dg in [-0.01, -0.005, 0, 0.005, 0.01]:
            rowv.append(round(valuation(M, wacc=base["wacc"] + dw, g=base["g"] + dg)["per_share"], 4))
        sens.append(rowv)

    raw_tsv = "\n".join("\t".join(l) for l in lines)
    mapping = [dict(raw=a, std=b, note=n) for a, b, n in MAPPING]

    hist_table = {}
    for y in [2022] + HIST:
        h = H[y]
        hist_table[str(y)] = {k: round(v, 6) for k, v in h.items() if isinstance(v, (int, float))}

    data = dict(
        company=COMPANY, shares=SHARES, price=PRICE, hist=HIST, fc=FC,
        assume=dict(
            vol_g=ASSUME["vol_g"], price_g=ASSUME["price_g"], cogs_pct=ASSUME["cogs_pct"],
            sell_pct=ASSUME["sell_pct"][0], admin_pct=ASSUME["admin_pct"][0], dep_rate=ASSUME["dep_rate"][0],
            capex_pct=ASSUME["capex_pct"][0], dso=ASSUME["dso"][0], dio=ASSUME["dio"][0], dpo=ASSUME["dpo"][0],
            repay=ASSUME["repay"][0], int_rate=INT_RATE, cash_rate=CASH_RATE, tax=TAX, payout=PAYOUT),
        valIn=VAL,
        rows=web_rows,
        scen=scen,
        sens=dict(wacc=[round(base["wacc"] + d, 6) for d in [-0.01, -0.005, 0, 0.005, 0.01]],
                  g=[round(base["g"] + d, 6) for d in [-0.01, -0.005, 0, 0.005, 0.01]], grid=sens),
        rawTsv=raw_tsv,
        mapping=mapping,
        histTable=hist_table,
        layout=dict(model=R, assume=AR_, val=VR),
    )
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("/* 由 scripts/build_case.py 自动生成，请勿手动修改 */\n")
        f.write("window.FM_CASE = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    # 打印关键数字
    b = vals[1]
    print("历史：")
    for y in HIST:
        h = H[y]
        print(f"  {y}: 收入 {h['rev']:.1f} 净利 {h['ni']:.2f} 现金 {h['cash']:.3f} 借款 {h['debt']:.1f}")
    print("基准预测：")
    for y in FC:
        print(f"  {y}: 收入 {M['rev'][y]:.1f} EBITDA {M['ebitda'][y]:.1f} 净利 {M['ni'][y]:.1f} "
              f"现金 {M['cash'][y]:.1f} FCFF {b['fcff'][y]:.1f} 平衡 {M['bs_chk'][y]:.6f}")
    for s in (1, 2, 3):
        v = vals[s]
        print(f"情景{s}: WACC {v['wacc']:.4%} EV {v['ev']:.1f} 股权 {v['equity']:.1f} 每股 {v['per_share']:.2f} "
              f"TV占比 {v['tv_share']:.1%} 上涨 {v['upside']:.1%} EV/EBITDA26 {v['ev_ebitda_26']:.1f}x")
    print("已生成：", ans_path, tpl_path, OUT_JS)


if __name__ == "__main__":
    main()
