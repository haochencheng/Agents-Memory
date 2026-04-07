---
title: "API 接口约定"
updated_at: 2026-04-07
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

**响应 200:**
```json
{
  "topics": [
    {
      "topic": "synapse-architecture",
      "title": "Synapse Architecture",
      "tags": ["backend", "design"],
      "word_count": 420,
      "updated_at": "2026-03-14"
    }
  ]
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
  "frontmatter": {"tags": ["backend"], "updated_at": "2026-03-14"},
  "content_html": "<h1>Synapse Architecture</h1>...",
  "raw": "# Synapse Architecture\n...",
  "word_count": 420
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

## GET /api/errors

列出错误记录（支持过滤）。

**查询参数:**
- `status` — `open` | `resolved` | `archived` （可选）
- `project` — 项目名过滤（可选）
- `limit` — 返回条数，默认 20

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
  "total": 34
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

全文混合搜索（wiki + 错误记录）。

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
      "score": 0.92
    },
    {
      "type": "wiki",
      "topic": "auth-design",
      "title": "Auth Design",
      "snippet": "...JWT best practices...",
      "score": 0.87
    }
  ],
  "total": 2
}
```

---

## POST /api/ingest

摄入文档到记忆系统。**写操作 # WRITE**

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
{"ingested": true, "id": "ERR-2026-0407-003", "dry_run": false}
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
      "status": "ok"
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
