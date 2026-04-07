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
| Markdown 渲染 | **markdown** (Python) | ≥3.6 | 轻量，无额外依赖，服务端渲染为 HTML |
| 测试客户端 | **httpx** + **pytest** | ≥0.27 | FastAPI 推荐 TestClient，asyncio 友好 |
| MVP UI | **Streamlit** | ≥1.32 | 纯 Python，零前端构建，验证快 |
| 未来前端 | **Vite + React 18 + TailwindCSS** | — | 生产级，VS Code Simple Browser 可嵌入 |
| 图谱可视化 | **D3.js** v7 | — | 力导向图，Wiki 交叉链接可视化 |

## 为什么不选 Flask / Django

- Flask 无内置类型验证，Pydantic 整合需额外配置
- Django 过重，Agents-Memory 业务逻辑已在 `services/` 层，无需 ORM
- FastAPI 自动生成 `/docs` OpenAPI UI，方便手动探索

## 为什么先做 Streamlit 而非直接 React

- 复用现有 Python 服务层，无需额外进程
- `amem wiki-list` / `hybrid_search` 等可直接调用
- 验证 UX 后再决定是否需要完整 React 版
- 当前团队是开发者，Streamlit 对内使用足够

## 约束

- **后端不引入数据库**：所有数据读自 `memory/wiki/*.md`、`errors/*.md`、`memory/ingest_log.jsonl`
- **只读操作默认开放**，写操作（wiki-update、ingest）需在 API 中标注 `# WRITE`
- **无认证（v1）**：仅本地 localhost 使用，不对外暴露
- **Python 3.12 only**：与 `agents_memory` 主包保持一致

## 依赖清单

```
# requirements-web.txt（追加到 requirements.txt）
fastapi>=0.110.0
uvicorn>=0.29.0
markdown>=3.6
httpx>=0.27.0          # 测试用
streamlit>=1.32.0      # MVP UI
```
