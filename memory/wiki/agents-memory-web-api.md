---
topic: agents-memory-web-api
created_at: 2026-04-07
updated_at: 2026-04-07
compiled_at: 2026-04-07
confidence: high
sources: [docs/frontend/03-api-contract.md]
tags: [api, fastapi, web-ui]
---

# Agents-Memory Web API

FastAPI REST 层，将 `agents_memory/services/` 暴露为 JSON HTTP 接口。

Base URL: `http://localhost:8000`  
启动: `uvicorn agents_memory.web.api:app --reload --port 8000`

## 核心约束

- 无数据库，所有数据从磁盘文件读取（`memory/wiki/*.md`, `errors/*.md`, `memory/ingest_log.jsonl`）
- v1 不需要认证（localhost 内网工具）
- 写操作在函数注释中标注 `# WRITE`
- 所有 HTML 输出经过 `renderer.md_to_html()` XSS 消毒

## 端点索引

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 统计摘要 |
| GET | `/api/wiki` | 列出所有 wiki 话题 |
| GET | `/api/wiki/lint` | Lint 检查 |
| GET | `/api/wiki/{topic}` | 单页内容 |
| PUT | `/api/wiki/{topic}` | 更新 compiled_truth # WRITE |
| POST | `/api/wiki/{topic}/compile` | 触发 LLM 编译异步任务 # WRITE |
| GET | `/api/errors` | 错误记录列表 |
| GET | `/api/errors/{id}` | 单条错误记录 |
| GET | `/api/search` | 混合全文搜索 |
| POST | `/api/ingest` | 摄入文档 # WRITE |
| GET | `/api/ingest/log` | 摄入日志 |
| GET | `/api/rules` | rules.md 内容 |
| GET | `/api/tasks/{task_id}` | 异步任务状态 |

## 模块位置

- `agents_memory/web/api.py` — FastAPI 路由
- `agents_memory/web/models.py` — Pydantic 模型
- `agents_memory/web/renderer.py` — Markdown → HTML

---

## 时间线

- 2026-04-07: 初版实现完成，40 个自动化测试全部通过
