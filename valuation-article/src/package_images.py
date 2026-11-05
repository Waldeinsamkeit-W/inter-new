"""
把配图整理成一个文件夹并打包成 zip：按文章顺序编号、中文命名，附《说明.txt》写明每张图插在哪里。

    python3 package_images.py [输出目录]      # 默认输出到当前目录

生成「估值模型全攻略-配图/」文件夹和同名 zip。
"""
import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NAME = "估值模型全攻略-配图"
TITLES = {
    "fig01-methods-map": "估值方法全景图",
    "fig02-ev-vs-equity": "企业价值与股权价值",
    "fig03-comps-table": "可比公司估值表",
    "fig04-cyclical-pe": "周期股的PE陷阱",
    "fig05-dcf-table": "DCF测算表",
    "fig06-tv-share": "终值占比",
    "fig07-ev-bridge": "从企业价值到股权价值",
    "fig08-sensitivity": "敏感性分析",
    "fig09-method-selector": "按公司类型选择估值方法",
    "fig10-workflow": "估值工作七步法",
    "fig11-football-field": "估值足球场图",
    "fig12-divergence": "估值结论不一致怎么办",
    "fig13-leverage-pe": "同一门生意杠杆不同PE不同",
    "fig14-debt-issuance": "发债后EV和股权价值怎么变",
    "fig15-normalized-ebitda": "归一化EBITDA调整桥",
    "fig16-cheatsheet": "估值公式速查卡",
}


def main(out_dir):
    folder = os.path.join(out_dir, NAME)
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
    img = os.path.join(ROOT, "images")
    shutil.copy(os.path.join(img, "cover.png"), os.path.join(folder, "00-封面-头图.png"))
    shutil.copy(os.path.join(img, "cover-square.png"), os.path.join(folder, "00-封面-方形.png"))

    notes = ["《估值模型全攻略》配图说明", "",
             "封面（在公众号后台“封面”处上传，不放进正文）：",
             "  00-封面-头图.png：头图，2.35:1",
             "  00-封面-方形.png：分享卡片，1:1", "",
             "正文配图（按顺序插入，位置如下）："]
    heading, prev = "", ""
    with open(os.path.join(ROOT, "article.md"), encoding="utf-8") as f:
        for line in f.read().splitlines():
            if line.startswith("```"):
                continue
            if line.startswith("#"):
                heading, prev = line.lstrip("#").strip(), ""
                continue
            m = re.match(r"!\[[^\]]*\]\(images/(fig(\d+)[^)]*)\.png\)", line)
            if m:
                key, no = m.group(1), m.group(2)
                fn = f"{no}-{TITLES[key]}.png"
                shutil.copy(os.path.join(img, key + ".png"), os.path.join(folder, fn))
                where = f"「{heading}」这一节"
                if prev:
                    snip = re.sub(r"[*`]", "", prev)[-24:]
                    where += f"，紧接在“…{snip}”之后"
                else:
                    where += "标题下方"
                notes.append(f"  {fn}：{where}")
            elif line.strip():
                prev = line.strip()
    notes += ["", "正文配图宽 1680 像素，可直接上传，公众号会自动压缩。"]
    with open(os.path.join(folder, "说明.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes) + "\n")

    zpath = folder + ".zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in sorted(os.listdir(folder)):
            zf.write(os.path.join(folder, fn), f"{NAME}/{fn}")
    print("\n".join(notes))
    print(f"\n→ {folder}\n→ {zpath}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
