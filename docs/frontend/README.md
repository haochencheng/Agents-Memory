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

## 快速启动

```bash
# 启动 FastAPI 后端
cd /Users/cliff/workspace/agent/Agents-Memory
python3.12 -m uvicorn agents_memory.web.api:app --reload --port 8000

# 启动 Streamlit MVP UI（另一个终端）
python3.12 -m streamlit run agents_memory/ui/streamlit_app.py --server.port 10000

# 运行后端 API 测试
python3.12 -m pytest tests/test_web_api.py -v
```

## 目录规范

- 后端代码：`agents_memory/web/`
- UI 代码：`agents_memory/ui/`
- 测试：`tests/test_web_api.py`
- Bugfix 记录：`docs/bugfix/frontend/`
