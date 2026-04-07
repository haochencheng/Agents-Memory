---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# 前端实施计划

## Phase 1 — 核心只读端点（完成验收 ✓）

| # | 任务 | 产出 |
|---|------|------|
| 1.1 | 实现 `renderer.py`（md → HTML） | `agents_memory/web/renderer.py` |
| 1.2 | 实现 Pydantic 模型 | `agents_memory/web/models.py` |
| 1.3 | 实现 `GET /api/stats` | api.py 端点 |
| 1.4 | 实现 `GET /api/wiki` | api.py 端点 |
| 1.5 | 实现 `GET /api/wiki/{topic}` | api.py 端点 |
| 1.6 | 实现 `GET /api/wiki/lint` | api.py 端点 |
| 1.7 | 实现 `GET /api/errors` | api.py 端点 |
| 1.8 | 实现 `GET /api/errors/{id}` | api.py 端点 |
| 1.9 | 实现 `GET /api/rules` | api.py 端点 |
| 1.10 | 写 Phase 1 测试 | `tests/test_web_api.py` |

**验收标准:** `pytest tests/test_web_api.py::TestPhase1` 全绿。

---

## Phase 2 — 搜索与摄入

| # | 任务 | 产出 |
|---|------|------|
| 2.1 | 实现 `GET /api/search` | api.py 端点 |
| 2.2 | 实现 `POST /api/ingest` | api.py 端点 # WRITE |
| 2.3 | 实现 `PUT /api/wiki/{topic}` | api.py 端点 # WRITE |
| 2.4 | 实现 `GET /api/ingest/log` | api.py 端点 |
| 2.5 | 写 Phase 2 测试 | `tests/test_web_api.py` |

**验收标准:** `pytest tests/test_web_api.py::TestPhase2` 全绿。

---

## Phase 3 — 异步任务

| # | 任务 | 产出 |
|---|------|------|
| 3.1 | 实现 `POST /api/wiki/{topic}/compile` | api.py 端点 # WRITE |
| 3.2 | 实现 `GET /api/tasks/{task_id}` | api.py 端点 |
| 3.3 | 实现 task_store 内存字典 | api.py 内部 |
| 3.4 | 写 Phase 3 测试 | `tests/test_web_api.py` |

**验收标准:** `pytest tests/test_web_api.py::TestPhase3` 全绿。

---

## Phase 4 — Streamlit MVP UI（5 页面）

| # | 任务 | 产出 |
|---|------|------|
| 4.1 | 实现概览页（stats + lint 摘要） | streamlit_app.py |
| 4.2 | 实现 Wiki 浏览页（列表 + 搜索 + 详情） | streamlit_app.py |
| 4.3 | 实现搜索页（混合搜索结果） | streamlit_app.py |
| 4.4 | 实现错误记录页（表格 + 过滤） | streamlit_app.py |
| 4.5 | 实现 Ingest 页（表单提交） | streamlit_app.py |

**验收标准:** 手动逐页截图验证，无崩溃，无 JS console 错误。

---

## Phase 5 — 集成收尾

| # | 任务 | 产出 |
|---|------|------|
| 5.1 | 修复所有 bugfix 记录的问题 | `docs/bugfix/frontend/` |
| 5.2 | 将 API 约定摄入 wiki | `memory/wiki/agents-memory-web-api.md` |
| 5.3 | 更新 `memory/rules.md` 添加 API 约束 | `memory/rules.md` |
| 5.4 | Commit + Push | git |

**验收标准:** `pytest tests/` 全绿，`git status` 干净。

---

## 风险与依赖

| 风险 | 缓解 |
|------|------|
| `services/` 接口不稳定 | api.py 通过 try/except 降级，端点不崩溃 |
| wiki-compile 需要 Ollama | Phase 3 测试 mock LLM，不依赖本地模型启动 |
| Streamlit 版本不兼容 | 固定 `streamlit>=1.32` |
