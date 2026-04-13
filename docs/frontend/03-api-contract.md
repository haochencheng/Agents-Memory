---
created_at: 2026-04-07
updated_at: 2026-04-12
doc_status: active
---

# REST API Contract

Base URL: `http://localhost:10100`

---

## GET /api/stats

系统统计摘要（Dashboard 首页用）。

**响应 200:**
```json
{
  "wiki_count": 12,
  "error_count": 34,
  "ingest_count": 78,
  "projects": ["synapse-network", "agents-memory"]
}
```

---

## GET /api/wiki

列出所有 wiki 话题。

**查询参数:**
- `q` — 标题 / 标签 / 项目 / 路径 / 正文全文检索（可选）
- `page` — 页码，默认 `1`
- `page_size` — 每页条数，默认 `20`，最大 `100`

**响应 200:**
```json
{
  "topics": [
    {
      "topic": "synapse-architecture",
      "title": "Synapse Architecture",
      "tags": ["backend", "design"],
      "doc_type": "architecture",
      "word_count": 420,
      "updated_at": "2026-03-14",
      "project": "synapse-network",
      "source_path": "docs/architecture/overview.md"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "query": ""
}
```

---

## GET /api/wiki/lint

运行 wiki lint 检查，返回所有问题列表。

**响应 200:**
```json
{
  "issues": [
    {
      "topic": "synapse-architecture",
      "line": 10,
      "level": "warning",
      "message": "Missing compiled_truth section"
    }
  ],
  "total": 3
}
```

---

## GET /api/wiki/{topic}

获取单个 wiki 页面内容。

**路径参数:** `topic` — 文件名（不含 .md）

**响应 200:**
```json
{
  "topic": "synapse-architecture",
  "title": "Synapse Architecture",
  "tags": ["backend", "design"],
  "doc_type": "architecture",
  "updated_at": "2026-03-14",
  "project": "synapse-network",
  "source_path": "docs/architecture/overview.md",
  "frontmatter": {"tags": ["backend"], "updated_at": "2026-03-14"},
  "content_html": "<h1>Synapse Architecture</h1>...",
  "raw": "# Synapse Architecture\n...",
  "word_count": 420,
  "links": [
    {
      "topic": "billing-recharge",
      "title": "Billing Recharge",
      "relation": "explicit",
      "reason": "显式 wiki 链接",
      "score": 3.0,
      "project": "synapse-network",
      "tags": ["billing", "recharge"]
    }
  ],
  "backlinks": [],
  "related_topics": []
}
```

**响应 404:**
```json
{"detail": "Topic 'foo' not found"}
```

---

## PUT /api/wiki/{topic}

更新 wiki 页面 `compiled_truth` 字段。**写操作 # WRITE**

**请求体:**
```json
{"compiled_truth": "The canonical fact about this topic is..."}
```

**响应 200:**
```json
{"topic": "synapse-architecture", "updated": true}
```

---

## POST /api/wiki/{topic}/compile

触发 wiki-compile（LLM 异步任务）。**写操作 # WRITE**

**响应 202:**
```json
{"task_id": "compile-synapse-architecture-20260407", "status": "pending"}
```

---

## GET /api/wiki/graph

返回 wiki 关系图。

- `type=explicit` 表示 frontmatter `links` 里的显式引用
- `type=inferred` 表示基于同项目 / 共享标签 / 主题词做的轻量推断关系
- `type=contains` 表示项目节点到 concept 节点的归属边
- `type=mentions` 表示同一页面内主概念到次级概念的正文提及边

**响应 200:**
```json
{
  "nodes": [
    {
      "id": "decision:synapse-architecture",
      "title": "Synapse Architecture",
      "node_type": "decision",
      "project": "synapse-network",
      "word_count": 420,
      "tags": ["backend", "design"],
      "primary_topic": "synapse-architecture",
      "topic_count": 1
    }
  ],
  "edges": [
    {
      "source": "module:auth-design",
      "target": "decision:synapse-architecture",
      "type": "explicit",
      "weight": 3.0
    },
    {
      "source": "decision:synapse-architecture",
      "target": "module:billing-recharge",
      "type": "inferred",
      "weight": 2.4
    },
    {
      "source": "project:synapse-network",
      "target": "decision:synapse-architecture",
      "type": "contains",
      "weight": 1.0
    }
  ]
}
```

---

## GET /api/errors

列出错误记录（支持过滤）。

**查询参数:**
- `status` — `open` | `resolved` | `archived` （可选）
- `project` — 项目名过滤（可选）
- `page` — 页码，默认 1
- `page_size` — 每页条数，默认 20
- `limit` — 兼容旧调用；传入时等价于 `page=1&page_size=limit`

**响应 200:**
```json
{
  "errors": [
    {
      "id": "ERR-2026-0312-001",
      "title": "Token validation fails on refresh",
      "status": "open",
      "project": "synapse-network",
      "created_at": "2026-03-12",
      "tags": ["auth", "jwt"]
    }
  ],
  "total": 34,
  "page": 1,
  "page_size": 20,
  "total_pages": 2
}
```

---

## GET /api/errors/{id}

获取单个错误记录完整内容。

**响应 200:**
```json
{
  "id": "ERR-2026-0312-001",
  "title": "Token validation fails on refresh",
  "status": "open",
  "project": "synapse-network",
  "content_html": "<h2>Problem</h2>...",
  "raw": "## Problem\n...",
  "created_at": "2026-03-12"
}
```

**响应 404:**
```json
{"detail": "Error 'ERR-XXX' not found"}
```

---

## GET /api/search

全文混合搜索（wiki + 错误记录 + workflow 记录）。

- 基础召回：
  - errors 走 `FTS5 + LanceDB vector`
  - wiki/workflow 走 `FTS5 + deterministic semantic vector`
- 统一排序：会叠加 concept graph rerank，把 query 命中的概念沿 `explicit / inferred / mentions / contains` 关系向相关结果传播

**查询参数:**
- `q` — 搜索词（必填）
- `mode` — `keyword` | `semantic` | `hybrid`，默认 `hybrid`
- `limit` — 结果数上限，默认 10

**响应 200:**
```json
{
  "query": "JWT refresh token",
  "mode": "hybrid",
  "results": [
    {
      "type": "error",
      "id": "ERR-2026-0312-001",
      "title": "Token validation fails on refresh",
      "snippet": "...refresh token lifecycle...",
      "score": 0.92,
      "rerank_boost": 0.18,
      "rerank_reasons": ["命中概念: JWT Refresh", "命中概念: synapse-network"],
      "matched_concepts": [
        {
          "id": "module:jwt-refresh",
          "title": "JWT Refresh",
          "node_type": "module",
          "score": 0.72,
          "primary_topic": "auth-design",
          "project": "synapse-network"
        }
      ]
    },
    {
      "type": "wiki",
      "id": "auth-design",
      "title": "Auth Design",
      "snippet": "...JWT best practices...",
      "score": 0.87,
      "rerank_boost": 0.24,
      "rerank_reasons": ["命中概念: JWT Refresh", "命中概念: Auth Design"],
      "matched_concepts": [
        {
          "id": "decision:auth-design",
          "title": "Auth Design",
          "node_type": "decision",
          "score": 1.35,
          "primary_topic": "auth-design",
          "project": "synapse-network"
        }
      ]
    }
  ],
  "total": 2
}
```

---

## GET /api/workflow

列出 workflow 记录（完成 task / requirement 的执行证据，不计入错误记录）。

**查询参数:**
- `project` — 项目名过滤（可选）
- `source_type` — `task_completion` | `requirement_completion` 等（可选）
- `limit` — 返回条数，默认 50

**响应 200:**
```json
{
  "records": [
    {
      "id": "TASK-42",
      "title": "Apply planned changes",
      "source_type": "task_completion",
      "project": "synapse-network-growing",
      "status": "completed",
      "created_at": "2026-04-12T10:00:00Z",
      "storage_kind": "workflow"
    }
  ],
  "total": 1
}
```

---

## GET /api/workflow/{id}

获取单条 workflow 记录详情。

**响应 200:**
```json
{
  "id": "TASK-42",
  "title": "Apply planned changes",
  "source_type": "task_completion",
  "project": "synapse-network-growing",
  "status": "completed",
  "created_at": "2026-04-12T10:00:00Z",
  "storage_kind": "workflow",
  "content_html": "<h2>执行结果</h2>...",
  "raw": "---\nid: TASK-42\n..."
}
```

---

## POST /api/ingest

摄入文档到记忆系统。**写操作 # WRITE**

- `error_record` → 写入 `errors/`
- 其他类型（如 `task_completion` / `requirement_completion`）→ 写入 `memory/workflow_records/`

**请求体:**
```json
{
  "content": "# Problem\nAuth tokens expire after 1h...",
  "source_type": "error_record",
  "project": "synapse-network",
  "dry_run": false
}
```

**响应 200:**
```json
{"ingested": true, "id": "ERR-2026-0407-003", "dry_run": false, "storage_kind": "error"}
```

---

## GET /api/ingest/log

获取最近摄入日志。

**查询参数:** `limit` — 默认 50

**响应 200:**
```json
{
  "entries": [
    {
      "ts": "2026-04-07T10:32:00Z",
      "source_type": "error_record",
      "project": "synapse-network",
      "id": "ERR-2026-0407-003",
      "status": "ok",
      "storage_kind": "error"
    }
  ],
  "total": 50
}
```

---

## GET /api/rules

获取 `memory/rules.md` 原始内容。

**响应 200:**
```json
{
  "content_html": "<h1>Rules</h1>...",
  "raw": "# Rules\n...",
  "word_count": 211
}
```

---

## GET /api/tasks/{task_id}

查询异步任务状态。

**响应 200:**
```json
{
  "task_id": "compile-synapse-architecture-20260407",
  "status": "done",
  "elapsed_s": 12.3,
  "result": {"topic": "synapse-architecture", "compiled_truth": "..."}
}
```

**status 枚举:** `pending` | `running` | `done` | `failed`

---

## 错误格式（所有端点）

```json
{"detail": "Human-readable error message"}
```

HTTP 状态码：400 参数错误、404 资源不存在、500 服务器错误。
