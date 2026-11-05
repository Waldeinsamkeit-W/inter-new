# 公众号文章

| 文章 | Markdown | 公众号排版版 |
| --- | --- | --- |
| 收入增长30%，你敢信吗？一文讲透“利润质量” | [profit-quality.md](articles/profit-quality/profit-quality.md) | [profit-quality.html](articles/profit-quality/profit-quality.html) |

## 发布到公众号

1. 用浏览器打开对应的 `.html` 文件，点击“复制正文”。
2. 粘贴到公众号编辑器；文章标题手动填写到标题栏。

修改 Markdown 后重新生成排版版：

```bash
pip install markdown beautifulsoup4
python3 articles/tools/md2wechat.py articles/profit-quality/profit-quality.md
```
