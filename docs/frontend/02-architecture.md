---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# 系统架构设计

## 分层架构

```
┌─────────────────────────────────────────────────────┐
│              浏览器 / Streamlit UI                   │
│         http://localhost:10000 (Streamlit)           │
│         http://localhost:5173 (React, 未来)          │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP JSON
┌──────────────────────▼──────────────────────────────┐
│         FastAPI REST API  :10100                     │
│         agents_memory/web/api.py                     │
│                                                      │
│  GET /api/wiki           POST /api/ingest            │
│  GET /api/wiki/:topic    GET  /api/search            │
│  GET /api/errors         GET  /api/stats             │
│  GET /api/wiki/lint      GET  /api/rules             │
└──────────────────────┬──────────────────────────────┘
                       │ 直接调用（同进程）
┌──────────────────────▼──────────────────────────────┐
│         agents_memory/services/                      │
│                                                      │
│  wiki.py          search.py        records.py        │
│  wiki_compile.py  ingest.py        projects.py       │
└──────────────────────┬──────────────────────────────┘
                       │ 文件读写
┌──────────────────────▼──────────────────────────────┐
│              磁盘（本地 Markdown 文件）               │
│                                                      │
│  memory/wiki/*.md    errors/*.md                     │
│  memory/rules.md     memory/ingest_log.jsonl         │
│  vectors/fts.db                                      │
└─────────────────────────────────────────────────────┘
```

## 目录结构

```
agents_memory/
  web/
    __init__.py
    api.py          ← FastAPI app + 所有路由
    models.py       ← Pydantic 请求/响应模型
    renderer.py     ← Markdown → safe HTML

  ui/
    __init__.py
    streamlit_app.py  ← Streamlit MVP（5 页面）

tests/
  test_web_api.py     ← httpx TestClient 测试（覆盖所有端点）

docs/
  frontend/
    README.md
    01-tech-stack.md
    02-architecture.md  ← 本文件
    03-api-contract.md
    04-plans.md
    05-test-strategy.md
  bugfix/
    frontend/           ← 前端相关 bugfix 记录
```

## 数据流（Wiki 详情请求）

```
1. 浏览器 GET /api/wiki/synapse-architecture
2. FastAPI api.py：wiki_detail("synapse-architecture")
3. 调用 read_wiki_page(ctx.wiki_dir, "synapse-architecture")
4. 返回原始 Markdown
5. renderer.py 转换为 sanitized HTML
6. JSON 响应：{topic, content_html, frontmatter, word_count}
7. 浏览器渲染 HTML
```

## 数据流（全文搜索请求）

```
1. 浏览器 GET /api/search?q=JWT+auth&mode=hybrid&limit=10
2. FastAPI：调用 hybrid_search(ctx, "JWT auth", limit=10)
3. 同时调用 search_wiki(ctx.wiki_dir, "JWT auth", limit=5)
4. 合并结果，加 type 字段区分 error/wiki
5. 返回 {errors: [...], wiki: [...], total: N}
```

## 异步任务（wiki-compile）

wiki-compile 调用 LLM，耗时 5-30s，需异步模式：

```
POST /api/wiki/:topic/compile
→ 202 Accepted {task_id: "compile-...", status: "pending"}

# 后台 asyncio.create_task 执行 compile_wiki_topic
# 结果存入内存 dict task_store

GET /api/tasks/:task_id
→ {status: "running" | "done" | "failed", result: {}, elapsed_s: 3.2}
```

## 进程模型

```
# 开发环境
uvicorn agents_memory.web.api:app --reload --port 10100

# Streamlit（独立进程，调用 services 直接读文件）
streamlit run agents_memory/ui/streamlit_app.py --server.port 10000

# 两者共享同一份磁盘数据，无冲突（read-heavy，write 追加）
```

## CORS 配置

仅允许 localhost（v1 本地工具，不对外）：

```python
origins = ["http://localhost:5173", "http://localhost:10000", "http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"])
```
