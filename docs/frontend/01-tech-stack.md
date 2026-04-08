---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# 技术选型

## 决策矩阵

| 层 | 选型 | 版本 | 原因 |
|----|------|------|------|
| 后端框架 | **FastAPI** | ≥0.11 | 异步、自动 OpenAPI 文档、Pydantic 类型安全 |
| 后端服务器 | **uvicorn** | ≥0.30 | ASGI，支持 `--reload` 热重载 |
| 前端框架 | **Vite + React 18 + TypeScript** | Vite 6 / React 18 | SPA 架构，组件化、类型安全、开发体验更好 |
| UI 样式 | **TailwindCSS** | 3.x | 快速构建控制台 UI，样式一致性高 |
| 路由 | **React Router v6** | 6.x | 前端多页面路由管理 |
| 状态管理 | **Zustand** | 5.x | 轻量、低样板代码 |
| 数据请求 | **TanStack Query** | 5.x | 缓存、状态同步、重试和请求管理 |
| 测试客户端 | **httpx** + **pytest** | ≥0.27 | FastAPI 推荐 TestClient，asyncio 友好 |
| 图谱可视化 | **D3.js** v7 | — | 力导向图，Wiki 交叉链接可视化 |

## 为什么不选 Flask / Django

- Flask 无内置类型验证，Pydantic 整合需额外配置
- Django 过重，Agents-Memory 业务逻辑已在 `services/` 层，无需 ORM
- FastAPI 自动生成 `/docs` OpenAPI UI，方便手动探索

## 当前前端决策

- 已采用 React SPA 作为唯一前端实现，不再保留 Python UI 双轨维护
- 前端运行在 `frontend/`，通过 Vite 开发服务器监听 `:10000`
- 所有页面通过 REST API 访问 `agents_memory/web/api.py`
- 控制台、Wiki、Scheduler、Checks 等页面统一在 React 中维护

## 约束

- **后端不引入数据库**：所有数据读自 `memory/wiki/*.md`、`errors/*.md`、`memory/ingest_log.jsonl`
- **只读操作默认开放**，写操作（wiki-update、ingest）需在 API 中标注 `# WRITE`
- **无认证（v1）**：仅本地 localhost 使用，不对外暴露
- **Python 3.12 only**：与 `agents_memory` 主包保持一致
- **前端端口固定为 `10000`**：与当前运维脚本和测试配置保持一致

## 依赖清单

```
# Python 依赖（追加到 requirements.txt）
fastapi>=0.110.0
uvicorn>=0.29.0
markdown>=3.6
httpx>=0.27.0          # 测试用

# 前端依赖（frontend/package.json 管理）
# react, react-dom, vite, tailwindcss, @tanstack/react-query,
# react-router-dom, zustand, vitest, playwright
```
