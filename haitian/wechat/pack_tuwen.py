#!/usr/bin/env python3
"""把图文版要用的图片收进一个文件夹：wechat/图文版配图/

按 index.html 正文里出现的顺序收集插图，加上两张封面，并写一份插图顺序说明。
文件名和正文里虚线占位框写的文件名一致，照着框里的名字上传即可。
build_images.py 生成配图后会自动调用；也可以单独运行：
  python wechat/pack_tuwen.py
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "images"
DEST = HERE / "图文版配图"
COVERS = [("00_封面_2.35比1.png", "头条封面，2.35:1"), ("00_封面_1比1.png", "分享卡片的方形裁切参考，1:1")]


def figures_in_order() -> list[tuple[str, str]]:
    """返回 [(文件名, 所在小节)]，按正文顺序。"""
    html = (HERE / "index.html").read_text(encoding="utf-8")
    art = html[html.index('<article class="paper" id="article">'):html.index("</article>")]
    out, section = [], "开头"
    for line in art.splitlines():
        if 'data-role="sec"' in line:
            no = re.search(r'data-no="([^"]*)"', line).group(1)
            title = re.findall(r"<p[^>]*>(.*?)</p>", line)[1]
            section = f"{no} {re.sub(r'<[^>]+>', '', title)}"
        elif 'data-role="fig"' in line:
            out.append((re.search(r'data-file="([^"]+)"', line).group(1), section))
    return out


def main() -> Path:
    figs = figures_in_order()
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir()
    for name, _ in COVERS:
        shutil.copy2(SRC / name, DEST / name)
    for name, _ in figs:
        shutil.copy2(SRC / name, DEST / name)

    lines = [f"海天七年财报拆解 · 图文版配图（共 {len(COVERS) + len(figs)} 张）", "", "封面："]
    lines += [f"  {name}  —— {note}" for name, note in COVERS]
    lines += ["", "正文插图，按出现顺序（文件名与正文虚线框里写的一致）："]
    lines += [f"  {k:>2}. {name}  —— {section}" for k, (name, section) in enumerate(figs, 1)]
    lines += ["", "图片均为 1080 像素宽、单张不超过 600 万像素，可直接上传公众号。"]
    (DEST / "插图顺序.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已收集 {len(COVERS) + len(figs)} 张图到 {DEST}")
    return DEST


if __name__ == "__main__":
    main()
