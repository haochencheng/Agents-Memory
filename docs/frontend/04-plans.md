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

## Phase 4 — 旧版 Python UI（已废弃）

该阶段原本为旧版 Python UI 预留，现已被 `frontend/` React SPA 替代，不再作为当前实现路径。

**说明:** 历史实现已清理，相关内容仅保留为演进记录，不再继续维护。

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

## Phase 6 — React 前端实现（✅ 已完成）

> 根据 `08-product-frontend-design.md` 设计文档实现，替代旧版 Python UI 方案。

| # | 任务 | 产出 | 状态 |
|---|------|------|------|
| 6.1 | 搭建 Vite + React 18 + TypeScript 项目 | `frontend/` 目录 | ✅ |
| 6.2 | 配置 TailwindCSS + React Router v6 + Zustand + TanStack Query | `frontend/src/` 配置文件 | ✅ |
| 6.3 | 实现 API hooks（stats / wiki / projects / memory / scheduler） | `frontend/src/api/` | ✅ |
| 6.4 | 实现共享组件（StatCard / HealthBadge / WorkflowStepper / WikiCard 等） | `frontend/src/components/` | ✅ |
| 6.5 | 实现 RootLayout 含侧边栏导航 | `frontend/src/layouts/` | ✅ |
| 6.6 | 实现 Dashboard 页面（Overview / ProjectList / ProjectDetail / MemoryRecords / Workflow / Checks / Scheduler）| `frontend/src/pages/dashboard/` | ✅ |
| 6.7 | 实现 Wiki 页面（WikiHome / TopicDetail / TopicEdit / KnowledgeGraph / LintReport / Ingest） | `frontend/src/pages/wiki/` | ✅ |
| 6.8 | 编写单元测试（28 个测试全部通过） | `frontend/src/test/` | ✅ |
| 6.9 | 构建验证（`npm run build` 无错误） | `frontend/dist/` | ✅ |
| 6.10 | 启动 Dev Server 验证（http://localhost:10000） | vite dev | ✅ |

**验收结果:** 
- TypeScript: 0 编译错误
- 构建: `vite build` 成功，输出 281KB JS
- 测试: 28/28 通过（5 个测试文件）
- Dev Server: http://localhost:10000 返回正常 HTML

---

## 风险与依赖

| 风险 | 缓解 |
|------|------|
| `services/` 接口不稳定 | api.py 通过 try/except 降级，端点不崩溃 |
| wiki-compile 需要 Ollama | Phase 3 测试 mock LLM，不依赖本地模型启动 |
| 前端依赖或 Node 版本不兼容 | 固定 Node 18+，依赖由 `frontend/package.json` 管理 |
