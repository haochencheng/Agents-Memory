---
created_at: 2026-04-07
updated_at: 2026-04-13
doc_status: active
---

# Agents-Memory Web UI — 运维手册

## 服务概览

| 服务 | 端口 | 进程 | 作用 |
|------|------|------|------|
| FastAPI | 10100 | uvicorn | REST API，供 UI + 外部调用 |
| React Frontend | 10000 | vite | SPA Web UI |

## 一键启动

```bash
# 启动全部（API + UI）
bash scripts/web-start.sh

# 只启动 API
bash scripts/web-start.sh api

# 只启动 UI
bash scripts/web-start.sh ui

# 停止全部
bash scripts/web-start.sh stop

# 重启全部
bash scripts/web-start.sh restart

# 查看状态
bash scripts/web-start.sh status

# 运行健康检查
bash scripts/web-start.sh health
```

## 访问地址

| 入口 | URL |
|------|-----|
| React UI | http://localhost:10000 |
| FastAPI REST | http://localhost:10100 |
| API Swagger UI | http://localhost:10100/docs |
| API ReDoc | http://localhost:10100/redoc |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGENTS_MEMORY_ROOT` | 自动检测（项目根目录） | 数据目录根路径 |
| `AGENTS_MEMORY_API_PORT` | `10100` | FastAPI 监听端口 |
| `AGENTS_MEMORY_UI_PORT` | `10000` | React 前端监听端口 |

## 前提依赖

```bash
# 推荐：使用项目虚拟环境
python3 -m venv .venv
.venv/bin/pip install fastapi "uvicorn[standard]" requests markdown httpx pytest

# Python 版本
python3.12 --version   # >= 3.12

# Node 版本
node --version         # >= 18
npm --version

# 安装后端依赖（如果不使用 .venv）
pip3.12 install fastapi "uvicorn[standard]" requests \
    markdown httpx pytest --break-system-packages

# 安装前端依赖
cd frontend && npm install
```

`bash scripts/web-start.sh` 会优先使用项目根目录下的 `.venv/bin/python`；只有在 `.venv` 不存在时，才会回退到系统 `python3.12 / python3`。

脚本还会额外做两层 API 版本校验：
- 如果 `10100` 端口上已经是兼容的 `Agents-Memory API`，会直接接管 PID，不重复起进程
- 如果端口上是旧版 `agents_memory.web.api`，且缺少 `/api/scheduler/task-groups`，脚本会先替换旧进程再启动

## 健康检查

```bash
# 脚本方式（人类可读）
python3.12 scripts/web-health.py

# JSON 格式（CI 友好）
python3.12 scripts/web-health.py --json

# 指定服务地址
python3.12 scripts/web-health.py --api http://localhost:10100 --ui http://localhost:10000

# 只检查 API（跳过 UI）
python3.12 scripts/web-health.py --skip-ui
```

健康检查覆盖的端点：

| 检查项 | 期望 |
|--------|------|
| `GET /api/stats` | 200，含 wiki_count/error_count |
| `GET /api/wiki` | 200，含 topics 数组 |
| `GET /api/wiki/lint` | 200，含 issues 数组 |
| `GET /api/errors` | 200，含 errors 数组 |
| `GET /api/search?q=test` | 200，含 results 数组 |
| `GET /api/ingest/log` | 200，含 entries 数组 |
| `GET /api/rules` | 200，含 raw 字段 |
| `POST /api/ingest (dry_run=true)` | 200，dry_run=true |
| `GET /api/search (无 q)` | 422（参数验证） |
| `GET /api/wiki/:topic (不存在)` | 404 |
| React UI `/` | 200，HTML |

## 自动化测试

```bash
# API 单元测试（40 个，覆盖所有端点）
python3.12 -m pytest tests/test_web_api.py -v

# 前端单元测试
cd frontend && npm test -- --run

# 前端端到端测试
cd frontend && npx playwright test

# 后端 API 测试
python3.12 -m pytest tests/test_web_api.py -v

# 全量验证
python3.12 -m pytest tests/test_web_api.py -v
cd frontend && npm run build && npm test -- --run
```

## 日志

| 文件 | 内容 |
|------|------|
| `logs/web-api.log` | FastAPI (uvicorn) 请求日志 |
| `logs/web-ui.log` | Vite 前端启动/访问日志 |

```bash
# 实时查看 API 日志
tail -f logs/web-api.log

# 查看最后 50 行错误
grep -i error logs/web-api.log | tail -50
```

## PID 文件

| 文件 | 描述 |
|------|------|
| `.web_api.pid` | FastAPI 进程 PID |
| `.web_ui.pid` | React 前端进程 PID |

手动停止（若脚本失效）：

```bash
kill $(cat .web_api.pid)
kill $(cat .web_ui.pid)
# 或按端口强制停止
lsof -ti tcp:10100 | xargs kill -9
lsof -ti tcp:10000 | xargs kill -9
```

## 故障排查

### API 无法启动

```bash
# 检查端口占用
lsof -i tcp:10100

# 检查依赖
python3.12 -c "import fastapi, uvicorn; print('OK')"

# 查看启动日志
cat logs/web-api.log
```

### React 前端无法访问

```bash
# 检查端口
lsof -i tcp:10000

# 检查 API 是否先启动
curl http://localhost:10100/api/stats

# 查看 UI 日志
cat logs/web-ui.log
```

### 测试失败

```bash
# 重新安装依赖
pip3.12 install -r requirements.txt --break-system-packages

# 运行前端单测
cd frontend && npm test -- --run

# 运行前端 E2E
cd frontend && npx playwright test
```

## Bugfix 记录

前端相关 bugfix 记录在 `docs/bugfix/frontend/` 目录，格式参见 `docs/frontend/05-test-strategy.md`。
