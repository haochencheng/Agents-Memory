---
title: "Phase 3: Wiki 交叉引用 links / wiki-link / wiki-backlinks"
status: completed
created_at: 2026-04-07
updated_at: 2026-04-07
scope: agents_memory/services/wiki.py, agents_memory/commands/wiki.py
tests: tests/test_wiki_compile.py
---

# Phase 3 — Wiki 交叉引用

## 设计目标

Wiki 页面之间存在逻辑关联，但缺乏结构化索引，导致：
- Agent 无法快速发现相关 Topic
- 孤岛页面无法被 `wiki-lint` 检测
- 无法表达"该 Topic 与哪些 Topic 有关联"

本阶段在 **frontmatter `links:` 字段**中存储双向引用关系，提供：
- `wiki-link` 命令创建有向链接（A → B）
- `wiki-backlinks` 命令查询反向链接（谁链接了 B）

---

## 数据模型

### frontmatter `links:` 字段格式

```yaml
---
topic: finance-safety
links:
  - topic: smart-contract-errors
    context: "Reentrancy 与 finance-safety 有重叠"
  - topic: audit-log
---
```

- `links` 是一个 YAML list，每个 entry 有 `topic`（必须）和 `context`（可选）
- 链接是**有向的**：A 的 links 列表记录了"A 引用了谁"
- 反向链接通过扫描所有页面的 links 列表获得

---

## 公开 API

### `agents_memory/services/wiki.py`

| 函数 | 签名 | 作用 |
|------|--------|------|
| `get_wiki_links(content)` | `-> list[dict[str,str]]` | 从页面 content 解析 frontmatter links 字段 |
| `set_wiki_links(wiki_dir, topic, links)` | `-> Path` | 覆盖写入 frontmatter links 字段 |
| `cmd_wiki_link(ctx, args)` | `-> int` | CLI：创建有向链接（幂等：重复创建只更新 context）|
| `cmd_wiki_backlinks(ctx, args)` | `-> int` | CLI：扫描并输出反向链接 |

### `get_wiki_links` 返回格式

```python
[
    {"topic": "smart-contract-errors", "context": "Reentrancy 重叠"},
    {"topic": "audit-log"},          # 无 context 时省略该字段
]
```

---

## CLI 命令

```bash
# 创建链接（A → B），幂等
amem wiki-link <from-topic> <to-topic> [--context "关联说明"]

# 查看所有链接到 target 的页面（反向链接）
amem wiki-backlinks <topic>
```

**示例：**

```bash
amem wiki-link finance-safety smart-contract-errors --context "Reentrancy 模式"
# → ✅ 链接已创建: finance-safety → smart-contract-errors

amem wiki-backlinks smart-contract-errors
# → 链接到 'smart-contract-errors' 的页面 (1 条):
#     • finance-safety  context: Reentrancy 模式
```

---

## 实现细节

### 幂等链接创建

`cmd_wiki_link` 在创建链接前检查目标是否已存在：
- 如果 `to-topic` 已在 links 列表中，只更新 `context`（如果提供）
- 如果不存在，追加新 entry

### 反向链接查询（O(n)）

`cmd_wiki_backlinks` 线性扫描所有 wiki 页面，检查每页的 `links:` 字段。
适合 wiki 页面数量在百篇以内的场景。

---

## 测试覆盖

文件：`tests/test_wiki_compile.py`（相关测试类）

| 测试类 | 覆盖内容 |
|---------|----------|
| `TestWikiLinks` | `get_wiki_links` 解析、空 links、带 context |
| `TestWikiLinkCommands` | `cmd_wiki_link` 创建、幂等、context 更新、目标不存在报错 |
| `TestWikiLint` (backlinks 部分) | 孤岛页面检测（无入链）|

---

## 状态

✅ 已实现并测试通过。291 个全局测试 OK。
