"""
案例测算：虚构公司「小鲜饮品」的 DCF、敏感性分析与反向 DCF。
文中所有案例数字都由本脚本算出，修改假设后重新运行即可：

    python3 model.py          # 打印结果并写出 model.json（供 figures.cjs 画图）

单位：亿元（每股价值为元）。估值基准日假设为 2026-12-31，预测期 2027E–2031E。
"""
import json
import os

YEARS = [2027, 2028, 2029, 2030, 2031]
REV_2026 = 44.0                     # 基期营收
REV_2027 = 50.0                     # 第一年预测营收
GROWTH = [0.12, 0.10, 0.08, 0.06]   # 2028E–2031E 营收增速
EBIT_MARGIN = [0.135, 0.14, 0.145, 0.145, 0.145]
DA_PCT = 0.03                       # 折旧摊销 / 营收
CAPEX_PCT = [0.045, 0.042, 0.040, 0.038, 0.036]
NWC_PCT_OF_INCREMENT = 0.08         # 营运资本增加 = 营收增量 × 8%
TAX = 0.25

# 折现率（CAPM + WACC）
RF, BETA, ERP = 0.02, 1.1, 0.065
KD, W_E, W_D = 0.04, 0.9, 0.1
WACC, G = 0.085, 0.025              # 取整后的 WACC 与永续增长率

# EV → 股权价值的调整项
CASH, DEBT, MINORITY, LT_INVEST, SHARES = 15.0, 10.0, 2.0, 3.0, 10.0
BRIDGE = CASH - DEBT - MINORITY + LT_INVEST


def forecast(rev_growth=GROWTH):
    revs = [REV_2027]
    for g in rev_growth:
        revs.append(revs[-1] * (1 + g))
    rows, prev = [], REV_2026
    for i, (y, r) in enumerate(zip(YEARS, revs)):
        ebit = r * EBIT_MARGIN[i]
        nopat = ebit * (1 - TAX)
        da = r * DA_PCT
        capex = r * CAPEX_PCT[i]
        dnwc = (r - prev) * NWC_PCT_OF_INCREMENT
        rows.append(dict(y=y, rev=r, growth=r / prev - 1, ebit=ebit, nopat=nopat, da=da,
                         capex=capex, dnwc=dnwc, fcff=nopat + da - capex - dnwc, ebitda=ebit + da))
        prev = r
    return rows


def dcf(rows, wacc=WACC, g=G):
    pvs = [row["fcff"] / (1 + wacc) ** t for t, row in enumerate(rows, 1)]
    tv = rows[-1]["fcff"] * (1 + g) / (wacc - g)
    pv_tv = tv / (1 + wacc) ** len(rows)
    ev = sum(pvs) + pv_tv
    return dict(pvs=pvs, pv_sum=sum(pvs), tv=tv, pv_tv=pv_tv, ev=ev, equity=ev + BRIDGE)


def solve(f, target, lo, hi):
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < target else (lo, mid)
    return mid


def advanced_examples():
    """第十二部分「进阶六问」用到的示例（与小鲜饮品无关的独立虚构公司）。单位：亿元，调整桥为万元。"""
    # 同一门生意、不同杠杆：EBITDA 25、EBIT 20、EV 250，B 借了 150 亿元
    ebitda, ebit, ev = 25.0, 20.0, 250.0

    def levered(net_debt, rate):
        interest = net_debt * rate
        ni = (ebit - interest) * (1 - TAX)
        mcap = ev - net_debt
        return dict(net_debt=net_debt, rate=rate, interest=interest, ni=ni, mcap=mcap, pe=mcap / ni,
                    ev=ev, ebitda=ebitda, ebit=ebit, ev_ebitda=ev / ebitda, nd_ebitda=net_debt / ebitda,
                    coverage=(ebitda / interest) if interest else None)

    leverage = dict(a=levered(0, 0.06), b=levered(150, 0.06), b_hike=levered(150, 0.08))

    # 发债 30 亿元：EV 100、净负债 20、股权 80
    issuance = [
        dict(name="发债前", ev=100, nd=20, note=""),
        dict(name="钱留在账上", ev=100, nd=20, note=""),
        dict(name="分红或回购", ev=100, nd=50, note="股东另得 30"),
        dict(name="投好项目", ev=100 + 30 + 5, nd=50, note="项目值 35"),
        dict(name="投坏项目", ev=100 + 30 - 8, nd=50, note="项目值 22"),
    ]
    for x in issuance:
        x["equity"] = x["ev"] - x["nd"]

    # PE 相同的两家公司：市值 200、净利润 10；B 有 100 亿元净负债、利率 5%
    def same_pe(net_debt, rate=0.05, da=5 / 3):
        ni, mcap = 10.0, 200.0
        interest = net_debt * rate
        e = ni / (1 - TAX) + interest + da
        return dict(mcap=mcap, ni=ni, pe=mcap / ni, net_debt=net_debt, interest=interest,
                    ev=mcap + net_debt, ebitda=e, ev_ebitda=(mcap + net_debt) / e, nd_ebitda=net_debt / e)

    same = dict(a=same_pe(0), b=same_pe(100))

    # 归一化 EBITDA 与 FDD（某连锁餐饮公司，万元）
    adjustments = [
        ("剔除一次性政府补助", -800), ("剔除出售门店物业的收益", -500),
        ("加回一次性诉讼和解费", 200), ("加回关店重组费用", 300),
        ("老板薪酬调到市场水平", -300), ("关联方租金调到市价", -200),
        ("补足每年少缴的社保公积金", -200),
    ]
    reported = 12000
    normalized = reported + sum(v for _, v in adjustments)
    multiple, net_debt, debt_like = 10, 1.0, 0.3
    fdd = dict(reported=reported, normalized=normalized, adjustments=adjustments, multiple=multiple,
               net_debt=net_debt, debt_like=debt_like,
               ev_before=reported / 1e4 * multiple, ev_after=normalized / 1e4 * multiple,
               ask=reported / 1e4 * multiple - net_debt,
               after=normalized / 1e4 * multiple - net_debt - debt_like)
    return dict(leverage=leverage, issuance=issuance, same_pe=same, fdd=fdd)


def main():
    rows = forecast()
    base = dcf(rows)
    ke = RF + BETA * ERP
    wacc_calc = W_E * ke + W_D * KD * (1 - TAX)

    waccs = [0.075, 0.08, 0.085, 0.09, 0.095]
    gs = [0.015, 0.02, 0.025, 0.03, 0.035]
    sens = [[dcf(rows, w, g)["equity"] / SHARES for g in gs] for w in waccs]
    band = [dcf(rows, w, g)["equity"] for w in (0.08, 0.085, 0.09) for g in (0.02, 0.025, 0.03)]

    # 反向 DCF：当前市值 150 亿，市场隐含了什么？
    implied_g = solve(lambda g: dcf(rows, WACC, g)["equity"], 150, 0.0, 0.08)
    implied_growth = solve(lambda x: dcf(forecast([x] * 4))["equity"], 150, 0.0, 0.6)

    # 结论不一致时的拆解：要达到可比公司中位数（25 倍 × 5 亿元 = 125 亿元）需要什么增速
    comps_median_equity = 25 * 5.0
    growth_for_comps = solve(lambda x: dcf(forecast([x] * 4))["equity"], comps_median_equity, 0.0, 0.6)
    # 常见技术错误示例：终值忘记折现
    tv_not_discounted = base["pv_sum"] + base["tv"] + BRIDGE
    # 加权平均：DCF 40%，PE 法与 EV/EBITDA 法各 30%（取区间中值）
    weighted = 0.4 * base["equity"] + 0.3 * (110 + 130) / 2 + 0.3 * (105 + 130) / 2

    # 稳态自洽检查：再投资率与隐含 ROIC
    reinvest = 1 - rows[-1]["fcff"] / rows[-1]["nopat"]

    out = dict(
        rows=rows, base=base, ke=ke, wacc_calc=wacc_calc, bridge=BRIDGE, shares=SHARES,
        waccs=waccs, gs=gs, sens=sens, dcf_band=[min(band), max(band)],
        implied_g_150=implied_g, implied_growth_150=implied_growth,
        reinvest=reinvest, implied_roic=G / reinvest,
        implied_exit_multiple=base["tv"] / rows[-1]["ebitda"],
        growth_for_comps=growth_for_comps, tv_not_discounted=tv_not_discounted, weighted=weighted,
        adv=advanced_examples(),
    )

    print(f"Ke = {ke:.2%}, WACC = {wacc_calc:.3%}（取 {WACC:.1%}）")
    for r, pv in zip(rows, base["pvs"]):
        print(f"{r['y']}E 营收 {r['rev']:6.2f}  EBIT {r['ebit']:5.2f}  NOPAT {r['nopat']:5.2f}  "
              f"D&A {r['da']:4.2f}  Capex {r['capex']:4.2f}  ΔNWC {r['dnwc']:4.2f}  "
              f"FCFF {r['fcff']:5.2f}  现值 {pv:5.2f}")
    print(f"预测期现值合计 {base['pv_sum']:.2f}，终值 {base['tv']:.2f}，终值现值 {base['pv_tv']:.2f}")
    print(f"EV {base['ev']:.2f}（终值占比 {base['pv_tv'] / base['ev']:.1%}），"
          f"股权价值 {base['equity']:.2f}，每股 {base['equity'] / SHARES:.2f} 元")
    print(f"隐含 PE {base['equity'] / 5:.1f}x，隐含 EV/EBITDA {base['ev'] / rows[0]['ebitda']:.1f}x，"
          f"隐含退出倍数 {out['implied_exit_multiple']:.1f}x")
    print(f"WACC 8–9%、g 2–3% 区间：{min(band):.1f}–{max(band):.1f} 亿元")
    print(f"反向 DCF（市值 150 亿）：隐含永续增长 {implied_g:.2%}；或 2028–31 年营收年增 {implied_growth:.1%}")
    print(f"要达到可比公司中位数 125 亿元：2028–31 年营收需年增 {growth_for_comps:.1%}")
    print(f"终值忘记折现时股权价值 {tv_not_discounted:.1f} 亿元（虚高 {tv_not_discounted / base['equity'] - 1:.1%}）")
    print(f"加权平均（DCF 40% / PE 30% / EV/EBITDA 30%）：{weighted:.1f} 亿元")
    print(f"稳态再投资率 {reinvest:.1%}，隐含 ROIC {G / reinvest:.1%}")
    print("敏感性（每股，元）：")
    for w, line in zip(waccs, sens):
        print(f"  WACC {w:.1%}: " + "  ".join(f"{v:5.2f}" for v in line))

    adv = out["adv"]
    lv = adv["leverage"]
    print("—— 进阶六问 ——")
    for k in ("a", "b", "b_hike"):
        x = lv[k]
        print(f"杠杆示例 {k}: 净负债 {x['net_debt']:.0f} 利息 {x['interest']:.1f} 净利润 {x['ni']:.2f} "
              f"市值 {x['mcap']:.0f} PE {x['pe']:.1f}x EV/EBITDA {x['ev_ebitda']:.1f}x 净负债/EBITDA {x['nd_ebitda']:.1f}x")
    print(f"加息后 B 净利润变化 {lv['b_hike']['ni'] / lv['b']['ni'] - 1:.1%}，利息保障倍数 {lv['b']['coverage']:.1f}x")
    for x in adv["issuance"]:
        print(f"发债 {x['name']}: EV {x['ev']} 净负债 {x['nd']} 股权 {x['equity']}")
    for k, x in adv["same_pe"].items():
        print(f"同 PE {k}: EV {x['ev']:.0f} EBITDA {x['ebitda']:.2f} EV/EBITDA {x['ev_ebitda']:.2f}x 净负债/EBITDA {x['nd_ebitda']:.1f}x")
    f = adv["fdd"]
    print(f"归一化 EBITDA {f['reported']} → {f['normalized']} 万元（{f['normalized'] / f['reported'] - 1:.1%}），"
          f"EV {f['ev_before']:.1f} → {f['ev_after']:.1f} 亿元；报价 {f['ask']:.1f} → {f['after']:.1f} 亿元"
          f"（{f['after'] / f['ask'] - 1:.1%}）")

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
