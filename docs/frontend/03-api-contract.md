---
created_at: 2026-04-07
updated_at: 2026-04-13
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

## GET /api/scheduler/tasks

兼容旧前端的平铺任务接口。当前真实主模型已经升级为“任务组 + 批次日志”，这里会把每个任务组映射成 `docs/profile/plan` 三条虚拟任务。

**响应 200:**
```json
{
  "tasks": [
    {
      "id": "group-1:docs",
      "name": "nightly-check-docs",
      "check_type": "docs",
      "project": "synapse-network",
      "cron_expr": "0 2 * * *",
      "status": "active",
      "created_at": "2026-04-13T01:50:00+08:00",
      "updated_at": "2026-04-13T01:50:00+08:00",
      "last_run": "2026-04-13T02:00:00+08:00",
      "next_run": "2026-04-14T02:00:00+08:00",
      "last_result": "fail",
      "last_summary": "FAIL:docs_entrypoint | FAIL:docs_contracts"
    }
  ]
}
```

## POST /api/scheduler/tasks

兼容旧调用。内部会创建一个任务组，再返回映射后的 `docs/profile/plan` 三条虚拟任务。

Cron 表达式采用标准 5 段格式：

```text
分钟 小时 日 月 星期
```

常用示例：
- `5 * * * *` — 每小时的第 5 分钟执行一次
- `0 * * * *` — 每小时整点执行一次
- `0 2 * * *` — 每天凌晨 2 点执行一次
- `30 9 * * 1-5` — 工作日每天 09:30 执行一次
- `0 8 * * 1` — 每周一早上 8 点执行一次

支持 `*`、范围 `1-5`、列表 `1,3,5`、步进 `*/2`。

**请求体:**
```json
{
  "name": "nightly-check",
  "project": "synapse-network",
  "cron_expr": "0 2 * * *"
}
```

**响应 201:**
```json
{
  "tasks": [
    { "id": "a1", "name": "nightly-check-docs", "check_type": "docs", "project": "synapse-network", "cron_expr": "0 2 * * *", "status": "active" },
    { "id": "a2", "name": "nightly-check-profile", "check_type": "profile", "project": "synapse-network", "cron_expr": "0 2 * * *", "status": "active" },
    { "id": "a3", "name": "nightly-check-plan", "check_type": "plan", "project": "synapse-network", "cron_expr": "0 2 * * *", "status": "active" }
  ]
}
```

**错误 400:**
```json
{"detail": "Project 'unknown-project' is not registered"}
```

---

## GET /api/scheduler/task-groups

返回任务组列表。前端 `/scheduler` 主页面现在优先消费这个接口。

**查询参数:**
- `q` — 按任务组名称 / 项目 / cron 模糊搜索
- `project` — 项目过滤
- `status` — `active` | `paused`
- `last_result` — `pass` | `warn` | `fail`
- `failed_only` — `true` 时只返回 `warn/fail`

**响应 200:**
```json
{
  "task_groups": [
    {
      "id": "group-1",
      "name": "nightly-check",
      "project": "synapse-network",
      "cron_expr": "0 2 * * *",
      "status": "active",
      "created_at": "2026-04-13T01:50:00+08:00",
      "updated_at": "2026-04-13T01:50:00+08:00",
      "last_run_at": "2026-04-13T02:00:00+08:00",
      "next_run_at": "2026-04-14T02:00:00+08:00",
      "last_result": "warn",
      "last_summary": "docs:pass | profile:warn | plan:pass",
      "recent_results": ["warn", "pass"],
      "latest_steps": [
        {
          "id": "step-1",
          "batch_id": "batch-1",
          "task_group_id": "group-1",
          "check_type": "profile",
          "status": "warn",
          "duration_ms": 28,
          "summary": "tests missing",
          "details": ["[WARN] tests: missing"],
          "workflow_record_id": "WF-1"
        }
      ]
    }
  ],
  "total": 1
}
```

## POST /api/scheduler/task-groups

创建一个逻辑任务组。第一版固定包含 `docs/profile/plan` 三个子检查。

**请求体:**
```json
{
  "name": "nightly-check",
  "project": "synapse-network",
  "cron_expr": "0 2 * * *"
}
```

**响应 201:**
```json
{
  "task_group": {
    "id": "group-1",
    "name": "nightly-check",
    "project": "synapse-network",
    "cron_expr": "0 2 * * *",
    "status": "active",
    "latest_steps": [],
    "recent_results": []
  },
  "latest_batch": null
}
```

## GET /api/scheduler/task-groups/{id}

返回单个任务组详情和最近一次执行摘要。

## PUT /api/scheduler/task-groups/{id}

编辑任务组的 `name / project / cron_expr / status`。

## POST /api/scheduler/task-groups/{id}/pause

暂停任务组，暂停后不会继续调度，并会清空 `next_run_at`。

## POST /api/scheduler/task-groups/{id}/resume

恢复任务组，恢复后重新计算下一次执行时间。

## POST /api/scheduler/task-groups/{id}/run

立即执行一次任务组，返回本次 `manual` 触发生成的批次记录。

## DELETE /api/scheduler/task-groups/{id}

删除任务组定义。已写入 workflow 的历史不会被删除。

## GET /api/scheduler/task-groups/{id}/runs

返回该任务组最近 200 次执行批次，支持分页。

**查询参数:**
- `page` — 页码，默认 1
- `page_size` — 每页条数，默认 10

**响应 200:**
```json
{
  "runs": [
    {
      "id": "batch-1",
      "task_group_id": "group-1",
      "task_group_name": "nightly-check",
      "project": "synapse-network",
      "run_at": "2026-04-13T02:00:00+08:00",
      "finished_at": "2026-04-13T02:00:05+08:00",
      "overall_status": "warn",
      "duration_ms": 5000,
      "trigger": "scheduled",
      "steps": [
        {
          "id": "step-1",
          "batch_id": "batch-1",
          "task_group_id": "group-1",
          "check_type": "docs",
          "status": "pass",
          "duration_ms": 20,
          "summary": "docs ok",
          "details": [],
          "workflow_record_id": "WF-1"
        }
      ]
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

## GET /api/scheduler/task-groups/{id}/runs/{run_id}

返回单次执行批次的完整 step 明细。

---

## GET /api/checks

返回调度器执行过的检查结果。当前主数据源是 `memory/scheduler_runs.jsonl`，同时兼容旧的 `memory/check_runs.jsonl`。

**查询参数:**
- `project` — 项目过滤（可选）
- `check_type` — `docs` | `profile` | `plan`
- `status` — `pass` | `warn` | `fail`

**响应 200:**
```json
{
  "checks": [
    {
      "id": "CHK-20260413020000-docs-a1b2c3d4",
      "task_id": "a1b2c3d4",
      "task_name": "nightly-check-docs",
      "task_group_id": "group-1",
      "task_group_name": "nightly-check",
      "batch_id": "batch-1",
      "project": "synapse-network",
      "check_type": "docs",
      "status": "fail",
      "trigger": "scheduled",
      "run_at": "2026-04-13T02:00:00+08:00",
      "duration_ms": 42,
      "summary": "FAIL:docs_entrypoint | FAIL:docs_contracts",
      "details": [
        "[FAIL] docs_entrypoint: missing docs/README.md"
      ],
      "workflow_record_id": "WF-1"
    }
  ],
  "total": 1
}
```

---

## GET /api/checks/summary

返回每类检查基于“每个任务最新一次运行结果”的聚合摘要。

**响应 200:**
```json
{
  "docs_pass": 0,
  "docs_warn": 0,
  "docs_fail": 1,
  "profile_pass": 0,
  "profile_warn": 1,
  "profile_fail": 0,
  "plan_pass": 1,
  "plan_warn": 0,
  "plan_fail": 0
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
