#!/usr/bin/env python3
"""把 Markdown 文章转换成可直接粘贴到微信公众号后台的 HTML。

公众号编辑器会丢弃 <style> 和 class，只保留行内样式，所以这里把所有样式都写成 style 属性。

用法:
    pip install markdown beautifulsoup4
    python3 articles/tools/md2wechat.py articles/profit-quality/profit-quality.md

输出与输入同目录、同名的 .html 文件。用浏览器打开，点击“复制正文”，再粘贴到公众号编辑器即可。
文章的一级标题（# 标题）不进入正文，请手动填写到公众号的标题栏。
"""

import sys
from pathlib import Path

import markdown
from bs4 import BeautifulSoup

ACCENT = "#1e5aa8"
TEXT = "#333333"
MUTED = "#666666"
LIGHT_BG = "#f4f7fb"
BORDER = "#dfe5ee"

STYLES = {
    "h2": f"margin:40px 0 18px;padding:0 0 0 12px;border-left:4px solid {ACCENT};"
          f"font-size:19px;font-weight:bold;line-height:1.5;color:{TEXT};",
    "h3": f"margin:28px 0 12px;font-size:17px;font-weight:bold;line-height:1.5;color:{ACCENT};",
    "h4": f"margin:22px 0 10px;font-size:16px;font-weight:bold;line-height:1.5;color:{TEXT};",
    "p": f"margin:0 0 16px;font-size:15px;line-height:1.8;letter-spacing:0.5px;"
         f"color:{TEXT};text-align:justify;",
    "strong": f"font-weight:bold;color:{ACCENT};",
    "em": f"font-style:normal;color:{MUTED};",
    "blockquote": f"margin:20px 0;padding:14px 16px;background:{LIGHT_BG};"
                  f"border-left:3px solid {ACCENT};border-radius:4px;",
    "ul": "margin:0 0 16px;padding-left:22px;",
    "ol": "margin:0 0 16px;padding-left:22px;",
    "li": f"margin:0 0 8px;font-size:15px;line-height:1.8;letter-spacing:0.5px;color:{TEXT};",
    "table": "width:100%;margin:0 0 20px;border-collapse:collapse;font-size:13px;line-height:1.6;",
    "th": f"padding:8px 6px;background:{ACCENT};color:#ffffff;font-weight:bold;"
          f"border:1px solid {ACCENT};text-align:left;white-space:nowrap;",
    "td": f"padding:8px 6px;border:1px solid {BORDER};color:{TEXT};vertical-align:top;",
    "hr": f"margin:36px auto;width:40%;border:0;border-top:1px dashed {BORDER};",
}

PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
</head>
<body style="margin:0;background:#eef1f5;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;">
<div style="position:sticky;top:0;z-index:1;background:#ffffff;border-bottom:1px solid #dfe5ee;padding:12px 16px;">
  <div style="max-width:677px;margin:0 auto;display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
    <button id="copy" style="padding:8px 16px;border:0;border-radius:6px;background:{accent};color:#fff;font-size:14px;cursor:pointer;">复制正文</button>
    <span id="tip" style="font-size:13px;color:#666;">复制后粘贴到公众号编辑器；标题请填写到公众号标题栏。</span>
  </div>
</div>
<div style="max-width:677px;margin:24px auto;padding:0 16px;">
  <div style="font-size:22px;font-weight:bold;line-height:1.5;color:#222;margin:0 0 16px;">{title}</div>
  <section id="article" style="background:#ffffff;padding:24px 18px;border-radius:8px;">
{body}
  </section>
</div>
<script>
document.getElementById('copy').addEventListener('click', function () {{
  var range = document.createRange();
  range.selectNodeContents(document.getElementById('article'));
  var sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
  var ok = false;
  try {{ ok = document.execCommand('copy'); }} catch (e) {{ ok = false; }}
  sel.removeAllRanges();
  document.getElementById('tip').textContent = ok
    ? '已复制，去公众号编辑器粘贴即可。'
    : '自动复制失败，请手动全选正文后复制。';
}});
</script>
</body>
</html>
"""


def convert(md_text: str) -> tuple[str, str]:
    html = markdown.markdown(md_text, extensions=["tables", "sane_lists"])
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)
        h1.decompose()

    # 任务列表 “[ ]” 在公众号里不会渲染成复选框，换成方框字符，并去掉列表圆点。
    checklists = set()
    for li in soup.find_all("li"):
        first = li.contents[0] if li.contents else None
        if isinstance(first, str) and first.startswith("[ ] "):
            first.replace_with("☐ " + first[4:])
            checklists.add(id(li.parent))

    for tag_name, style in STYLES.items():
        for tag in soup.find_all(tag_name):
            tag["style"] = style

    for ul in soup.find_all("ul"):
        if id(ul) in checklists:
            ul["style"] = "margin:0 0 16px;padding-left:0;list-style:none;"

    # 引用块里的段落：去掉多余底边距，最后一段不留空。
    for bq in soup.find_all("blockquote"):
        paragraphs = bq.find_all("p")
        for i, p in enumerate(paragraphs):
            margin = "0" if i == len(paragraphs) - 1 else "0 0 8px"
            p["style"] = STYLES["p"].replace("margin:0 0 16px;", f"margin:{margin};")

    # 表格放进可横向滚动的容器，避免手机上撑破版面。
    for table in soup.find_all("table"):
        wrapper = soup.new_tag("section", style="overflow-x:auto;margin:0 0 4px;")
        table.wrap(wrapper)

    # 表格隔行底色，便于手机阅读。
    for table in soup.find_all("table"):
        body = table.find("tbody")
        if body:
            for i, tr in enumerate(body.find_all("tr")):
                if i % 2 == 1:
                    for td in tr.find_all("td"):
                        td["style"] = td["style"] + f"background:{LIGHT_BG};"

    return title, str(soup)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("用法: python3 md2wechat.py <article.md>")
    src = Path(sys.argv[1])
    title, body = convert(src.read_text(encoding="utf-8"))
    out = src.with_suffix(".html")
    out.write_text(PAGE.format(title=title, body=body, accent=ACCENT), encoding="utf-8")
    print(f"已生成 {out}")


if __name__ == "__main__":
    main()
