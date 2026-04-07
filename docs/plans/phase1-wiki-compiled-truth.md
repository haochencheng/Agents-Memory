---
title: Phase 1 — Wiki Compiled Truth + Timeline 格式升级 & wiki-compile 命令
status: in-progress
created_at: 2026-04-07
updated_at: 2026-04-07
scope: agents_memory/services/wiki.py, agents_memory/services/wiki_compile.py, agents_memory/commands/wiki.py, agents_memory/mcp_app.py
tests: tests/test_wiki_service.py, tests/test_wiki_compile.py
---

# Phase 1 实施计划

## 目标

借鉴 GBrain 的 **compiled truth + timeline 分线架构**，让 Wiki 页面支持：

1. **Compiled Truth 区**（LLM 维护，可整体重写）— 综合结论、已知 Pattern
2. **Timeline 区**（Append-only，只追加不修改）— 时间戳事件记录

新增 `wiki-compile` 命令让 LLM 自动从 errors 记录中提炼 Pattern，写入 wiki。

---

## 变更清单

### 1. `agents_memory/services/wiki.py`（扩展，不破坏现有 API）

| 新增函数 | 作用 |
|----------|------|
| `COMPILED_FRONTMATTER_TEMPLATE` | 带 `compiled_at`、`links` 字段的新 frontmatter 模板 |
| `parse_wiki_sections(content)` | 把页面分成 `{frontmatter_str, compiled_truth, timeline}` |
| `build_compiled_page(topic, compiled_truth, timeline, fm_extra)` | 用三部分重建完整页面字符串 |
| `append_timeline_entry(wiki_dir, topic, entry)` | append-only 追加 timeline 条目 |
| `update_compiled_truth(wiki_dir, topic, new_truth)` | 只重写 compiled_truth 区，保留 timeline |
| `get_wiki_links(content)` | 从 frontmatter links 字段读 list[dict] |
| `set_wiki_links(wiki_dir, topic, links)` | 写 frontmatter links 字段 |
| `cmd_wiki_link(ctx, args)` | CLI: wiki-link <from> <to> [--context "..."] |
| `cmd_wiki_backlinks(ctx, args)` | CLI: wiki-backlinks <topic> |
| `cmd_wiki_lint(ctx, args)` | CLI: wiki-lint（孤岛、过期、缺失引用）|

### 2. `agents_memory/services/wiki_compile.py`（新文件）

| 函数 | 作用 |
|------|------|
| `_call_llm(prompt, model, provider)` | 调用 LLM API（anthropic/openai/ollama），返回文本 |
| `_build_compile_prompt(topic, current_truth, error_summaries)` | 构建 synthesis prompt |
| `compile_wiki_topic(ctx, topic, recent_n, model, provider, dry_run)` | 核心：读 errors → LLM → 更新 wiki |
| `cmd_wiki_compile(ctx, args)` | CLI 入口 |

### 3. `agents_memory/commands/wiki.py`（注册新命令）

新增注册：`wiki-compile`, `wiki-link`, `wiki-backlinks`, `wiki-lint`

### 4. `agents_memory/mcp_app.py`（新增 MCP tool）

```python
@mcp.tool()
def memory_wiki_compile(topic: str, scope: str = "errors", recent_n: int = 20, dry_run: bool = False) -> str:
    ...
```

---

## 格式规范（Wiki 页面 v2）

```markdown
---
topic: finance-safety
created_at: 2026-04-07
updated_at: 2026-04-07
compiled_at: 2026-04-07
confidence: high
sources: [AME-001, AME-007]
links:
  - topic: smart-contract-errors
    context: "Reentrancy 与 finance-safety 有重叠"
---

## 结论（Compiled Truth）

> 最新综合评估：...

## 已知 Pattern

- 精度问题：使用 Decimal 而非 float
- ...

---

## 时间线

- **2026-04-07** | AME-023 — 发现 decimals 处理漏洞
- **2026-03-20** | AME-007 — 首次记录 USDT 精度问题
```

---

## 测试计划

文件：`tests/test_wiki_compile.py` + 扩展 `tests/test_wiki_service.py`

| 测试用例 | 验证点 |
|----------|--------|
| `test_parse_wiki_sections_with_timeline` | compiled_truth 和 timeline 正确分割 |
| `test_parse_wiki_sections_no_timeline` | 无 timeline 时返回空 timeline |
| `test_build_compiled_page_round_trip` | build → parse 来回无损 |
| `test_append_timeline_entry_creates_section` | 新页面追加 timeline 自动创建区段 |
| `test_append_timeline_entry_idempotent_order` | 多次追加顺序正确（最新在前）|
| `test_update_compiled_truth_preserves_timeline` | 更新 compiled_truth 不影响 timeline |
| `test_wiki_link_adds_frontmatter_entry` | wiki-link 写入 links 字段 |
| `test_wiki_backlinks_finds_references` | wiki-backlinks 返回正确引用列表 |
| `test_wiki_lint_detects_orphan` | 无入链的页面被标记为孤岛 |
| `test_compile_wiki_topic_dry_run` | dry_run 不写文件，返回 diff 预览 |
| `test_compile_wiki_topic_no_errors` | 无 errors 时正常返回空结果 |
| `test_call_llm_mock` | mock LLM 调用，验证 prompt 构建与响应解析 |

---

## 依赖

- `anthropic>=0.25.0`（optional，compile 功能需要；fallback 到 openai/ollama）
- 无其他新依赖（links 字段用纯 YAML 解析）

---

## 实施顺序

1. 扩展 `services/wiki.py`（parse_wiki_sections, build_compiled_page, append, update, link, backlinks, lint）
2. 新建 `services/wiki_compile.py`（_call_llm, compile_wiki_topic, cmd_wiki_compile）
3. 更新 `commands/wiki.py`（注册新命令）
4. 更新 `mcp_app.py`（memory_wiki_compile tool）
5. 写测试 `tests/test_wiki_compile.py`，扩展 `tests/test_wiki_service.py`
6. 跑测试，修 bug，直到全绿
7. 提交
