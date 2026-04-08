---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

---
title: Frontend Docs Index
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# Agents-Memory 前端文档中心

本目录包含 Agents-Memory Web UI 的全部规划、架构、API 约定和测试文档。

## 文档索引

| 文件 | 说明 |
|------|------|
| [01-tech-stack.md](01-tech-stack.md) | 技术选型与依赖决策 |
| [02-architecture.md](02-architecture.md) | 系统架构设计（前后端分层）|
| [03-api-contract.md](03-api-contract.md) | REST API 完整接口规范（请求/响应格式）|
| [04-plans.md](04-plans.md) | 实施 Plan（阶段任务拆解）|
| [05-test-strategy.md](05-test-strategy.md) | 自动化测试策略 |
| [06-ops.md](06-ops.md) | 启停、健康检查、故障排查 |
| [08-product-frontend-design.md](08-product-frontend-design.md) | 当前 React 前端产品设计 |

## 快速启动

```bash
# 一键启动前后端
cd /Users/cliff/workspace/agent/Agents-Memory
bash scripts/web-start.sh restart

# 前端构建验证
cd frontend && npm run build

# 前端测试
cd frontend && npm test -- --run
```

## 目录规范

- 后端代码：`agents_memory/web/`
- 前端代码：`frontend/`
- 后端测试：`tests/test_web_api.py`
- 前端测试：`frontend/src/test/`、`frontend/tests/`
- Bugfix 记录：`docs/bugfix/frontend/`
