# FE-001: `<h1>` assertion fails — toc extension adds id attributes

**发现时间:** 2026-04-07  
**严重级别:** low (test bug, not production bug)  
**状态:** resolved

## 问题描述

`test_heading_converts_to_h1` 断言 `<h1>` 出现在 HTML 中失败：

```
AssertionError: '<h1>' not found in '<h1 id="hello-world">Hello World</h1>'
```

同样问题出现在 `test_wiki_detail_ok`。

## 根因

`agents_memory/web/renderer.py` 使用了 `toc` Markdown 扩展，该扩展为所有标题自动添加 `id` 属性：
`# Hello` → `<h1 id="hello">Hello</h1>`

测试错误地断言 `"<h1>" in html`（精确字符串匹配），而实际输出是 `"<h1 id=...">`。

## 修复

将测试断言从 `assertIn("<h1>", html)` 改为 `assertIn("<h1", html)` — 前缀匹配，容忍属性存在。

## 防止复发

- 测试中避免对带属性的 HTML 标签使用精确闭合标签字符串匹配。
- **约束（已添加到 rules.md）:** HTML 断言应使用前缀匹配 `assertIn("<h1", ...)` 或正则，不使用精确标签字符串。

## 受影响文件

- `tests/test_web_api.py` — TestPhase1.test_wiki_detail_ok, TestRenderer.test_heading_converts_to_h1
