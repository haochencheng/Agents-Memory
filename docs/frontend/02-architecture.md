---
created_at: 2026-04-07
updated_at: 2026-04-13
doc_status: active
---

# 系统架构设计

## 分层架构

```
┌─────────────────────────────────────────────────────┐
│                浏览器 / React SPA                    │
│         http://localhost:10000 (Vite Dev)            │
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

frontend/
  src/
    api/            ← TanStack Query hooks
    components/     ← 共享 UI 组件
    layouts/        ← 根布局 / 侧边栏布局
    pages/          ← Dashboard + Wiki 页面
    store/          ← Zustand 状态管理
    lib/            ← axios client / utils / graph view-model helpers

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
1. React 页面发起 GET /api/wiki/synapse-architecture
2. FastAPI api.py：wiki_detail("synapse-architecture")
3. 调用 read_wiki_page(ctx.wiki_dir, "synapse-architecture")
4. 返回原始 Markdown
5. renderer.py 转换为 sanitized HTML
6. JSON 响应：{topic, content_html, frontmatter, word_count}
7. 前端渲染详情页
```

## 数据流（全文搜索请求）

```
1. React 搜索框触发 GET /api/search?q=JWT+auth&mode=hybrid&limit=10
2. FastAPI：调用 hybrid_search(ctx, "JWT auth", limit=10)
3. 同时调用 search_wiki(ctx.wiki_dir, "JWT auth", limit=5)
4. 合并结果，加 type 字段区分 error/wiki
5. 返回 {errors: [...], wiki: [...], total: N}
```

## 数据流（知识图谱多视图）

```
1. React 进入 /wiki/graph
2. 页面读取 URL 参数（view / node）
3. 调用 GET /api/wiki/graph 获取 typed concept nodes + edges
4. 前端在 lib/knowledgeGraph.ts 内构建三种 view-model：
   - Schema: 类型/项目/关系汇总
   - Explore: 焦点节点的 1-hop / 2-hop 局部子图
   - Table: 可过滤的结构化节点列表
5. 页面按视图切换，不再把全量节点默认压进同一张画布
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

# React 前端（独立进程，通过 REST API 访问后端）
cd frontend && npm run dev -- --host 0.0.0.0 --port 10000

# 前后端共享同一份磁盘数据来源，写操作统一经 API 执行
```

## CORS 配置

仅允许 localhost（v1 本地工具，不对外）：

```python
origins = ["http://localhost:10000", "http://127.0.0.1:10000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"])
```
