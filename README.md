# inter-new

## interview-coach · 面试陪练台

一个单页网页工具，用来练习金融岗位面试：

- 按投递方向切换题库，也可以自己输入题目，或让 Claude 扮演面试官出新题
- 根据你的简历与研究作品生成参考答案（含答题思路、可能的追问、30 秒精简版）
- 先自己作答，再让 Claude 点评并给出改进版
- 把满意的答案存入「答题手册」（保存在浏览器本地）

### 使用

页面在 claude.ai 中以 Artifact 形式打开时，可以直接调用 Claude；在别处打开时，可以点「复制提示词」，再粘贴到 Claude 对话里。

### 背景资料

- `interview-coach/profile.example.json` 是格式示例。复制为 `profile.json` 后填入自己的经历、作品摘要和各方向题库。
- 作品原文放在 `interview-coach/materials/`，并在 `profile.json` 的 `works[].files` 里引用。
- `profile.json` 和 `materials/` 已加入 `.gitignore`，不会提交到这个公开仓库。
