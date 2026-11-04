#!/usr/bin/env python3
"""把公众号正文排成一张 1080 像素宽的长图。

正文文字从 index.html 读取（只维护一处），图表和数据卡复用 build_images.py 里的组件，
所以长图、配图和预览页的内容始终一致。

输出（wechat/longimage/）：
  海天七年财报拆解_长图.jpg       完整长图
  海天七年财报拆解_长图_第N段.jpg  按小节切开的分段版，用于上传公众号正文：
                                   公众号要求单张图片宽×高不超过 600 万像素，1080 宽时每段不超过 5400 像素高

用法（在 haitian/ 目录下）：
  python wechat/build_long_image.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_images as bi  # noqa: E402

OUT = HERE / "longimage"
BUILD = HERE / "_build" / "long"
W = 420  # 设计宽度（CSS 像素），和配图卡片一致
SCALE = 1080 / W
MAX_PX = 6_000_000  # 公众号正文单图像素上限（宽×高）
MAX_PART = 2100  # 分段版每段最高 2100 CSS 像素 ≈ 5400 像素，1080×5400 = 583 万像素

INK, INK2, MUTED, RULE, SOY, NUM = bi.INK, bi.INK2, bi.MUTED, bi.RULE, bi.SOY, bi.NUM
BODY = "#3d3632"

CSS = f"""
html, body {{ margin: 0; background: #fff; }}
#page {{ width: {W}px; background: #fff; color: {INK};
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif; }}
.n {{ font-family: "{NUM}", sans-serif; font-weight: 600; letter-spacing: .2px; }}
.em {{ font-style: normal; color: {SOY}; }}
.chart svg {{ width: 100%; height: auto; display: block; }}
.note {{ font-size: 12px; line-height: 1.6; color: {INK2}; background: {bi.PAPER}; border-radius: 6px; padding: 9px 12px; margin-top: 12px; }}

.hero {{ background: #2a1810; color: #fbf6f0; padding: 40px 24px 26px; }}
.hero .k {{ color: #f0a24a; font-size: 12px; letter-spacing: 3px; font-weight: 500; }}
.hero h1 {{ font-size: 31px; font-weight: 900; line-height: 1.3; margin: 20px 0 0; letter-spacing: .5px; }}
.hero .sub {{ color: #d9c6b5; font-size: 15px; margin: 12px 0 0; line-height: 1.6; }}
.hero .roe {{ margin-top: 28px; display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; }}
.hero .lab {{ font-family: "{NUM}", sans-serif; font-weight: 600; font-size: 13px; color: #c9b7a6; letter-spacing: 1px; }}
.hero .fig {{ font-family: "{NUM}", sans-serif; font-weight: 700; font-size: 50px; color: #f0a24a; line-height: 1; margin-top: 6px; white-space: nowrap; }}
.hero .fig b {{ color: #fbf6f0; }}
.hero .fig i {{ font-style: normal; color: #8f7b6a; margin: 0 6px; font-weight: 600; }}
.hero svg {{ width: 118px; height: auto; display: block; margin-bottom: 6px; }}
.hero .meta {{ margin-top: 24px; padding-top: 12px; border-top: 1px solid rgba(251, 246, 240, .16);
  display: flex; justify-content: space-between; gap: 12px; font-size: 11.5px; color: #a8927f; }}

.body {{ padding: 10px 22px 0; }}
.lp-native {{ margin: 0; }}
.lp-lead {{ margin: 22px 0 14px; font-size: 16.5px; line-height: 1.8; color: {INK}; font-weight: 500; }}
.lp-p {{ margin: 0 0 13px; font-size: 15px; line-height: 1.85; letter-spacing: .3px; color: {BODY}; text-align: justify; }}
.lp-p strong, .lp-key strong {{ color: {INK}; }}
.lp-p strong.hl, .lp-lead strong.hl {{ color: {SOY}; }}
.lp-sec {{ display: flex; align-items: flex-start; gap: 12px; margin: 42px 0 16px; padding-bottom: 10px; border-bottom: 1px solid {RULE}; }}
.lp-sec .no {{ font-family: "{NUM}", sans-serif; font-weight: 700; font-size: 36px; color: {SOY}; line-height: 1; }}
.lp-sec h2 {{ margin: 0; font-size: 20px; line-height: 1.4; font-weight: 700; text-wrap: balance; }}
.lp-sec .kicker {{ margin: 4px 0 0; font-size: 13px; line-height: 1.6; color: {MUTED}; }}
.lp-fig {{ margin: 16px 0 20px; border: 1px solid {RULE}; border-radius: 10px; padding: 16px 14px 14px; }}
.lp-fig figcaption {{ margin: 0 0 12px; }}
.lp-fig figcaption > b {{ display: block; font-size: 16.5px; line-height: 1.45; text-wrap: balance; }}
.lp-fig figcaption > b em {{ font-style: normal; color: {SOY}; }}
.lp-fig figcaption > span {{ display: block; font-size: 12px; color: {INK2}; line-height: 1.6; margin-top: 4px; }}
.lp-key {{ margin: 6px 0 18px; padding: 13px 15px; background: #f7f1ec; border-radius: 8px; }}
.lp-key b {{ display: block; font-size: 12.5px; letter-spacing: 2px; color: {SOY}; margin-bottom: 5px; }}
.lp-key p {{ margin: 0; font-size: 14.5px; line-height: 1.8; color: {BODY}; text-align: justify; }}
.lp-small {{ margin: 0 0 13px; font-size: 12.5px; line-height: 1.7; color: {MUTED}; text-align: justify; }}
.lp-foot {{ margin: 38px 0 0; padding: 16px 0 34px; border-top: 2px solid {INK}; }}
.lp-foot p {{ margin: 0 0 10px; font-size: 12px; line-height: 1.75; color: {MUTED}; text-align: justify; }}
.lp-foot strong {{ color: {INK2}; }}
.lp-end {{ display: flex; justify-content: space-between; gap: 12px; margin-top: 16px; font-size: 11.5px; color: {SOY}; }}
"""


def scope(css: str, prefix: str) -> str:
    """给组件样式的每条选择器加上前缀，避免多张卡的样式在一页里互相覆盖。"""
    out = []
    for block in css.split("}"):
        if "{" not in block:
            continue
        sel, body = block.split("{", 1)
        sels = ", ".join(f"{prefix} {s.strip()}" for s in sel.split(",") if s.strip())
        out.append(f"{sels} {{{body}}}")
    return "\n".join(out)


def figure(no: int, used_css: dict, section_title: str = "") -> str:
    c = bi.COMPONENTS[no]
    used_css[no] = scope(c["css"], f".c{no}") if c["css"] else ""
    plain = re.sub(r"<[^>]+>", "", c["title"])
    # 图标题和所在小节标题重复时只保留副标题
    title = "" if plain and plain in re.sub(r"<[^>]+>", "", section_title) else f'<b>{c["title"]}</b>'
    sub = f'<span>{c["sub"]}</span>' if c["sub"] else ""
    return f'<figure class="lp-fig c{no}" data-break="fig"><figcaption>{title}{sub}</figcaption>{c["inner"]}</figure>'


def _attr(line: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', line)
    return m.group(1) if m else ""


def _clean(fragment: str) -> str:
    fragment = re.sub(r'<strong style="color:#8c3510;">', '<strong class="hl">', fragment)
    return re.sub(r'<strong style="[^"]*">', "<strong>", fragment)


def article_body(used_css: dict) -> str:
    """按 index.html 里每块的 data-role 排版：正文一块一行，长图和预览页共用同一份文字。"""
    src = (HERE / "index.html").read_text(encoding="utf-8")
    art = src[src.index('<article class="paper" id="article">'):src.index("</article>")]
    lines = [ln.strip() for ln in art.splitlines()[1:] if ln.strip()]
    out, sec_title = [], ""
    for ln in lines:
        role = _attr(ln, "data-role")
        ps = re.findall(r"<p[^>]*>(.*?)</p>", ln)
        if role == "hero":
            continue  # 长图有自己的头图
        if role == "sec":
            sec_title = ps[1]
            out.append(f'<div class="lp-sec" data-break="sec"><span class="no">{_attr(ln, "data-no")}</span>'
                       f'<div><h2>{sec_title}</h2><p class="kicker">{_attr(ln, "data-kicker")}</p></div></div>')
        elif role == "fig":
            no = int(re.match(r"(\d+)_", _attr(ln, "data-file")).group(1))
            out.append(figure(no, used_css, sec_title))
        elif role == "key":
            out.append(f'<div class="lp-key"><b>划重点</b><p>{_clean(ps[-1])}</p></div>')
        elif role in ("native", "quote"):
            out.append(f'<div class="lp-native" data-break="fig">{ln}</div>')
        elif role == "foot":
            foot = "".join(f"<p>{_clean(x)}</p>" for x in ps)
            foot += ("<p><strong>主要来源：</strong>海天味业 2019—2025 年年度报告及摘要、2024 与 2025 年度审计报告、"
                     "2025 年度利润分配与权益分派公告；行情数据来自雪球。</p>"
                     '<div class="lp-end"><span>海天味业 · 七年财报拆解</span><span>勾稽 60/60 ✓</span></div>')
            out.append(f'<div class="lp-foot" data-break="sec">{foot}</div>')
        elif role == "small":
            out.append(f'<p class="lp-small">{_clean(ps[0])}</p>')
        elif role in ("lead", "p"):
            out.append(f'<p class="lp-{role}">{_clean(ps[0])}</p>')
        else:
            raise ValueError(f"index.html 里有未知的块：{ln[:80]}")
    return "\n".join(out)


def hero(dp) -> str:
    roe = [float(v) for v in dp["ROE"].values]
    lo, hi = 0.15, 0.40
    yy = lambda v: 8 + (hi - v) / (hi - lo) * 64  # noqa: E731
    pts = " ".join(f"{6 + k * 21:.0f},{yy(v):.1f}" for k, v in enumerate(roe))
    spark = (f'<svg viewBox="0 0 140 80"><polyline points="{pts}" fill="none" stroke="#f0a24a" stroke-width="2.4" '
             f'stroke-linejoin="round" stroke-linecap="round" opacity=".6"/>'
             f'<circle cx="6" cy="{yy(roe[0]):.1f}" r="3.6" fill="#f0a24a"/>'
             f'<circle cx="{6 + 6 * 21}" cy="{yy(roe[-1]):.1f}" r="4.2" fill="#fbf6f0"/></svg>')
    return f"""<header class="hero" data-break="sec">
  <div class="k">海天味业 · 七年财报拆解</div>
  <h1>一年赚 70 亿，<br>ROE 却掉了将近一半</h1>
  <p class="sub">毛利率回来了，钱去哪了？现在 35 块的股价贵不贵？</p>
  <div class="roe"><div><div class="lab">ROE · 净资产收益率 · 2019 → 2025</div>
    <div class="fig">{roe[0]:.1%}<i>→</i><b>{roe[-1]:.1%}</b></div></div>{spark}</div>
  <div class="meta"><span>七份年报 · 98 个数字 · 勾稽 60/60</span><span>2026 年 11 月</span></div>
</header>"""


def split_points(height: int, breaks: list[dict]) -> list[int]:
    """在小节或图的开头切分，每段不超过 MAX_PART；优先切在小节开头。"""
    cuts, start = [0], 0
    secs = sorted({b["y"] for b in breaks if b["kind"] == "sec" and b["y"] > 0})
    figs = sorted({b["y"] for b in breaks if b["kind"] == "fig" and b["y"] > 0})
    while height - start > MAX_PART:
        limit = start + MAX_PART
        cand = [y for y in secs if start + MAX_PART * 0.45 < y <= limit] or [y for y in figs if start < y <= limit]
        cut = max(cand) if cand else limit
        cuts.append(cut)
        start = cut
    cuts.append(height)
    return cuts


def main() -> None:
    _, dp = bi.build_pages()
    used_css: dict = {}
    body = article_body(used_css)
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        + CSS + "\n".join(used_css.values())
        + f"</style></head><body><div id='page'>{hero(dp)}<main class='body'>{body}</main></div></body></html>"
    )
    BUILD.mkdir(parents=True, exist_ok=True)
    for f in BUILD.glob("seg_*.png"):
        f.unlink()
    html_path = BUILD / "long.html"
    html_path.write_text(page, encoding="utf-8")
    subprocess.run(["node", str(HERE / "shoot_long.cjs"), str(html_path), str(BUILD), str(W), f"{SCALE:.6f}"], check=True)

    meta = json.loads((BUILD / "meta.json").read_text())
    total_h = round(meta["height"] * SCALE)
    canvas = Image.new("RGB", (1080, total_h), "white")
    for seg in meta["segs"]:
        im = Image.open(seg["file"]).convert("RGB")
        canvas.paste(im, (0, round(seg["y"] * SCALE)))

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    name = "海天七年财报拆解_长图"
    canvas.save(OUT / f"{name}.jpg", quality=90, subsampling=0, optimize=True, progressive=True)
    cuts = split_points(meta["height"], meta["breaks"])
    for k in range(len(cuts) - 1):
        part = canvas.crop((0, round(cuts[k] * SCALE), 1080, round(cuts[k + 1] * SCALE)))
        part.save(OUT / f"{name}_第{k + 1}段.jpg", quality=90, subsampling=0, optimize=True, progressive=True)
    for f in sorted(OUT.iterdir()):
        with Image.open(f) as im:
            px = im.size[0] * im.size[1]
            flag = "可上传公众号" if px <= MAX_PX else "超过 600 万像素，公众号正文传不了"
            print(f"{f.name}  {im.size[0]}×{im.size[1]}  {px / 1e4:.0f} 万像素  {f.stat().st_size / 1e6:.1f} MB  {flag}")
    secs = {b["y"] for b in meta["breaks"] if b["kind"] == "sec"}
    figs = {b["y"] for b in meta["breaks"] if b["kind"] == "fig"}
    print("切分位置：", ["小节开头" if c in secs else "图的开头" if c in figs else "硬切" for c in cuts[1:-1]])


if __name__ == "__main__":
    main()
