---
title: "Phase 2: 混合搜索 FTS + 向量"
status: completed
created_at: 2026-03-28
updated_at: 2026-04-07
scope: agents_memory/services/search.py, agents_memory/commands/search.py, agents_memory/mcp_app.py
tests: tests/test_search_service.py
---

# Phase 2 — 混合搜索 FTS + 向量

## 设计目标

现有搜索的问题：
- `cmd_search`：O(n) grep 扫描，无排序
- `cmd_vsearch`：需要提前构建 LanceDB 索引，冷启动
- 不支持关键词+语义综合查找

本阶段实现参考 Karpathy LLM Wiki query 算法和 GBrain ranked search 的**混合搜索层**。

---

## 架构设计

```
Query
  │
  ├─── SQLite FTS5 (BM25) ─── 归一化 [0,1] ─── 权重 × 0.4
  │
  └─── LanceDB 余弦相似度 ─── [0,1] ────────── 权重 × 0.6
              │
              └── 如果不可用，使用 FTS 权重 = 1.0
                                            │
                                    近期 boost +0.1
                                    (created < 30 天)
                                            │
                                    按 combined_score 降序
                                            │
                                         Top-N 结果
```

### 混合评分公式

```
combined_score = fts_score * 0.4 + vector_score * 0.6
# 若只有一个来源，则使用该来源的权重 = 1.0
# recent_boost: +0.1 if days_since_created <= 30
```

---

## FTS 索引实现

- **引擎**：Python stdlib `sqlite3` + FTS5 虚拟表（零附加依赖）
- **存储**：`vectors/fts.db`（随向量目录存放，gitignored）
- **分词器**：`unicode61`（支持 CJK 分词）
- **自动重建**：`errors/` 文件数与索引记录数不匹配时自动触发
- **索引字段**：`id, project, category, domain, content`（content = frontmatter + body）

### FTS DB 表结构

```sql
CREATE TABLE docs (
    id TEXT PRIMARY KEY,
    project TEXT, category TEXT, domain TEXT,
    severity TEXT, status TEXT, date_str TEXT, filepath TEXT, content TEXT
);
CREATE VIRTUAL TABLE docs_fts USING fts5(
    id, project, category, domain, content,
    content='docs', content_rowid='rowid',
    tokenize='unicode61'
);
```

---

## 公开 API

### `agents_memory/services/search.py`

| 函数 | 签名 | 作用 |
|------|--------|------|
| `build_fts_index(ctx, force)` | `-> int` | 构建 / 重建 FTS 索引，返回文档数 |
| `search_fts(ctx, query, limit)` | `-> list[dict]` | BM25 搜索，返回带 `fts_score` 的结果列表 |
| `hybrid_search(ctx, query, limit, fts_weight, vector_weight)` | `-> list[dict]` | FTS + 向量合并，返回带 `combined_score` |
| `cmd_fts_index(ctx, args)` | `-> int` | CLI 入口 |
| `cmd_hybrid_search(ctx, args)` | `-> int` | CLI 入口 |

### 返回结果字段

```python
{
    "id":            str,   # 错误记录 ID
    "project":       str,
    "category":      str,
    "domain":        str,
    "severity":      str,
    "status":        str,
    "date_str":      str,   # YYYY-MM-DD
    "filepath":      str,
    "fts_score":     float, # [0,1] BM25 归一化
    "vector_score":  float, # [0,1] 1 - cosine_distance (hybrid 模式)
    "combined_score":float, # 混合最终评分
}
```

---

## CLI 命令

```bash
amem fts-index [--force]              # 构建 / 重建 FTS5 索引
amem hybrid-search <query>            # 混合搜索
  [--limit 10]                        # 返回数量
  [--fts-only]                        # 仅 FTS，跳过向量层
  [--json]                            # JSON 输出
```

---

## MCP Tool

```python
@mcp.tool()
def memory_search(
    query: str,
    limit: int = 10,
    mode: str = "hybrid",  # "hybrid" | "fts" | "vector"
) -> str: ...
```

---

## 常量

```python
FTS_DB_NAME      = "fts.db"
FTS_SCORE_WEIGHT = 0.4
VECTOR_SCORE_WEIGHT = 0.6
RECENT_BOOST     = 0.1
RECENT_DAYS      = 30
```

---

## 测试覆盖

文件：`tests/test_search_service.py`（32 个测试）

| 测试类 | 覆盖内容 |
|---------|----------|
| `TestFtsDbPath` | 路径生成，自动创建目录 |
| `TestBuildFtsIndex` | 建索引、跳过重建、force、归档记录 |
| `TestSearchFts` | 匹配、非匹配、limit、字段、分数归一化、自动重建 |
| `TestIsRecent` | 近期日期 / 过期日期 / 边界值 |
| `TestHybridSearch` | FTS fallback、字段、近期 boost、limit、向量 merge mock |
| `TestCmdFtsIndex` | CLI exit code。force 标志 |
| `TestCmdHybridSearch` | CLI 输出、--json、--fts-only、--limit、无结果提示 |

---

## 状态

✅ 已实现并测试通过。291 个全局测试 OK。


## Motivation

The existing search (`cmd_search`) is a simple `grep`-based O(n) scan with no ranking.
The existing vector search (`cmd_vsearch`) requires an active LanceDB index (often cold on first use).
Neither supports a unified, ranked view combining keyword recall with semantic relevance.

This phase implements hybrid search inspired by Karpathy's LLM Wiki query pattern and GBrain's
ranked search approach.

## Design

```
Query
  │
  ├─── SQLite FTS5 (BM25) ─── normalize [0,1] ─── weight × 0.4
  │
  └─── LanceDB cosine sim ─── [0,1] ────────────── weight × 0.6
            │
            └── if unavailable, use FTS weight = 1.0
                                                      │
                                              recent boost +0.1
                                              (created < 30d)
                                                      │
                                              sort by combined_score
                                                      │
                                               top-N results
```

## Hybrid Score Formula

```
combined_score = fts_score * 0.4 + vector_score * 0.6 + recent_boost(0.1)
```

## FTS Implementation

- **Backend**: Python stdlib `sqlite3` with FTS5 virtual table
- **Storage**: `vectors/fts.db` (zero extra dependencies)
- **Tokenizer**: `unicode61` (handles CJK tokenization)
- **Index**: automatic rebuild when file count mismatch detected
- **Schema**: full-text over `id, project, category, domain, content`

## CLI Commands

```bash
amem fts-index [--force]               # Build / rebuild FTS5 index
amem hybrid-search <query>             # Hybrid search (FTS + vector)
  [--limit 10]                         # Result count
  [--fts-only]                         # Skip vector layer
  [--json]                             # Machine-readable output
```

## MCP Tool

```python
memory_search(query, limit=10, mode="hybrid")
# mode: "hybrid" | "fts" | "vector"
```

## Files Changed

- `agents_memory/services/search.py` — NEW: FTS index + hybrid search engine
- `agents_memory/commands/search.py` — NEW: command registration
- `agents_memory/app.py` — registered search commands
- `agents_memory/mcp_app.py` — added `memory_search` MCP tool
- `tests/test_search_service.py` — NEW: 32 tests covering all paths

## Status

✅ Implemented and tested. 276/276 tests green.
