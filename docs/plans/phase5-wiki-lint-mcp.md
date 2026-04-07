---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# Phase 5 — Wiki Lint + MCP 工具完整化

## 设计目标

本阶段完成两件事：

1. **`amem wiki-lint`**：Wiki 健康检查工具，检测孤立页面、过期 compiled_truth、未记录链接
2. **MCP 工具层完整化**：将 `memory_search` 升级为 hybrid FTS+vector，新增 `memory_ingest` 和 `memory_wiki_lint`

---

## cmd_wiki_lint 设计

### 检查模式

| 模式 | 含义 |
|------|------|
| `orphans` | 没有任何其他页面引用该页面（入链为 0）|
| `stale` | `compiled_at` 字段超过 30 天未更新 |
| `missing-links` | body 中提及了某个 topic 名但未在 `links` 中建立链接 |
| `all`（默认）| 依次执行以上全部三种检查 |

### 孤立页面检测（orphans）

```
所有 topic 入链计数初始化为 0
对每个页面扫描其 links 字段：
    每发现一个 links.topic 引用 → 目标 topic 的入链 +1
入链仍为 0 的 topic → [orphan]
```

时间复杂度：O(n) where n = wiki 页面数 × 平均链接数

### 过期检测（stale）

- 读取 frontmatter 中 `compiled_at` 字段（格式 `YYYY-MM-DD`）
- `(today - compiled_at).days > 30` → `[stale]`
- 无 `compiled_at` 的旧版页面会跳过（不报 stale）

### 缺失链接检测（missing-links）

- 对每个页面，在 `compiled_truth` + `timeline` 区块文本中检查是否含有其他 topic 名称（大小写不敏感，`-` 替换为空格的形式也检查）
- 若提及但 `links` 中未记录 → `[missing-link]`

---

## 函数签名

```python
# agents_memory/services/wiki.py
def cmd_wiki_lint(ctx: AppContext, args: list[str]) -> int:
    """Health-check the wiki: detect orphan pages, stale compiled_truth, missing links.

    Usage: amem wiki-lint [--check orphans|stale|missing-links|all]
    Exits 0 even when issues are found; issues are printed to stdout.
    """
```

返回值始终为 `0`（不以退出码暴露问题，仅通过 stdout 输出）。

---

## CLI 命令

```bash
amem wiki-lint [--check orphans|stale|missing-links|all]
```

**示例：**

```bash
# 检查所有问题（默认）
amem wiki-lint

# 只检查孤立页面
amem wiki-lint --check orphans

# 只检查过期 compiled_truth
amem wiki-lint --check stale

# 只检查缺失链接
amem wiki-lint --check missing-links
```

**正常输出：**

```
✅ Wiki 健康检查通过（5 个页面，无问题）
```

**发现问题时：**

```
⚠️  发现 2 个问题:

  • [orphan] 'auth' 无入链（无其他页面引用它）
  • [stale] 'backend' 的 compiled_truth 已超过 30 天未更新 (compiled_at=2025-12-01)
```

---

## MCP Tool

```python
@mcp.tool()
def memory_wiki_lint(check: str = "all") -> str:
    """Lint all wiki pages for structural issues."""
```

实现细节：
1. `contextlib.redirect_stdout` 捕获 `cmd_wiki_lint` stdout
2. MCP 调用：`cmd_wiki_lint(ctx, ["--check=<mode>"])` 或 `cmd_wiki_lint(ctx, [])` (all)
3. 返回捕获的输出（若为空则返回 "✅ Wiki lint 通过：未发现问题。"）

---

## MCP 工具层完整化（Phase 5 全局变更）

本阶段同步完成 MCP 工具层升级：

| MCP Tool | 变化 |
|----------|------|
| `memory_search` | 升级为 hybrid FTS+vector（旧关键字版本删除）|
| `memory_ingest` | 新增（见 Phase 4 文档）|
| `memory_wiki_lint` | 新增（本阶段）|

**`memory_search` 新签名：**

```python
@mcp.tool()
def memory_search(
    query: str,
    limit: int = 10,
    mode: str = "hybrid",      # "hybrid" | "fts" | "vector"
) -> str: ...
```

---

## 测试覆盖

文件：`tests/test_wiki_compile.py` → `class TestWikiLint`（5 个测试）

| 测试方法 | 覆盖内容 |
|----------|----------|
| `test_lint_detects_orphan` | 两个互不链接页面 → 输出含 `orphan` |
| `test_lint_no_orphan_when_linked` | A→B 链接 → B 不报孤立，A 仍报孤立 |
| `test_lint_detects_stale_compiled_truth` | `compiled_at=2025-01-01` → 输出含 `stale` + topic 名 |
| `test_lint_no_issues_message` | A↔B 互链 → 输出含 `✅`，exit code 0 |
| `test_lint_empty_wiki` | 空 wiki 目录 → exit code 0，无崩溃 |

MCP tool 覆盖：`tests/test_mcp_tools.py`（含 `memory_wiki_lint` mock 测试）

---

## 状态

✅ 已实现并测试通过。291 个全局测试 OK。
