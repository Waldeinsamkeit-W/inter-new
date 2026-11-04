# 公众号推文：三表勾稽 / 三表联动

| 文件 | 用途 |
| --- | --- |
| `article.md` | 正文 Markdown 稿，开头注释里有备选标题和摘要。可直接贴进 mdnice 等 Markdown 排版工具 |
| `index.html` | 排好版的预览页。用浏览器打开，点“复制正文（带排版）”，粘贴到公众号编辑器 |
| `wechat-paste.html` | 备用粘贴版：只有正文，全部内联样式、没有脚本。电脑浏览器打开后 Ctrl+A、Ctrl+C，粘贴到公众号后台。由 `index.html` 的复制逻辑生成，正文改动后需重新生成 |
| `images/cover.png` | 封面图，900 × 383（2.35 : 1） |
| `images/linkage.png` | 正文配图：三表联动关系图，1080 × 1560 |
| `images/01-logic.png` … `06-bridge-full.png` | 六张图解（1080 宽）：底层逻辑、逐笔追踪、公式推导、间接法四类调整、奶茶店的桥、完整版的桥 |
| `source/posters.html` | 六张图解的源文件；`node source/render-posters.js images` 重新渲染 |
| `images/pages/01.png` … `20.png` | **全文图片版**：20 张 3:4 图片（1080 × 1440），可直接发“贴图”，也可按顺序插入图文 |
| `source/pages.html` | 图片版源文件；`node source/render-pages.js images/pages` 重新渲染（会提示哪页内容超出） |

## 发布方式一：图片版（贴图）

1. 在公众号后台新建“贴图”（图片消息），按顺序上传 `images/pages/01.png` 到 `20.png`。
2. 标题用备选标题之一，描述用 `index.html` 里的“贴图文案”。

## 发布方式二：图文版

1. 用浏览器打开 `index.html`，从“备选标题”里选一个复制到标题栏，摘要同理。
2. 点“复制正文（带排版）”，在**电脑版**公众号后台的正文区粘贴。如果标题、加粗没过去，改用 `wechat-paste.html`（打开 → Ctrl+A → Ctrl+C → 粘贴）。
3. 图片要单独上传：正文里每张图的位置都有“在这里插入图片”的提示框（共 7 张），插入对应图片后删掉提示框。
4. 封面上传 `images/cover.png`。

例子里的数字已核对过：利润表、现金流量表、资产负债表三表相互勾稽，间接法推出的经营现金流与直接法一致。
