---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# Agents-Memory Web UI — 运维手册

## 服务概览

| 服务 | 端口 | 进程 | 作用 |
|------|------|------|------|
| FastAPI | 10100 | uvicorn | REST API，供 UI + 外部调用 |
| Streamlit | 10000 | streamlit | MVP Web UI，5 页面 |

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
| Streamlit UI | http://localhost:10000 |
| FastAPI REST | http://localhost:10100 |
| API Swagger UI | http://localhost:10100/docs |
| API ReDoc | http://localhost:10100/redoc |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGENTS_MEMORY_ROOT` | 自动检测（项目根目录） | 数据目录根路径 |
| `AGENTS_MEMORY_API_PORT` | `10100` | FastAPI 监听端口 |
| `AGENTS_MEMORY_UI_PORT` | `10000` | Streamlit 监听端口 |
| `AGENTS_MEMORY_API` | `http://localhost:10100` | Streamlit 调用 API 的地址 |

## 前提依赖

```bash
# Python 版本
python3.12 --version   # >= 3.12

# 安装 Web 依赖
pip3.12 install fastapi "uvicorn[standard]" streamlit requests \
    markdown httpx pytest --break-system-packages
```

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
| Streamlit UI `/` | 200，HTML |

## 自动化测试

```bash
# API 单元测试（40 个，覆盖所有端点）
python3.12 -m pytest tests/test_web_api.py -v

# 页面级端到端冒烟测试（45+ 个，覆盖 5 个 UI 页面）
python3.12 -m pytest tests/test_web_e2e.py -v

# 全部测试（含覆盖率报告）
python3.12 -m pytest tests/test_web_api.py tests/test_web_e2e.py \
    --cov=agents_memory/web --cov-report=term-missing -v

# 按 Phase 运行
python3.12 -m pytest tests/test_web_api.py -v -k TestPhase1
python3.12 -m pytest tests/test_web_api.py -v -k TestPhase2
python3.12 -m pytest tests/test_web_e2e.py -v -k E2EOverview
```

## 日志

| 文件 | 内容 |
|------|------|
| `logs/web-api.log` | FastAPI (uvicorn) 请求日志 |
| `logs/web-ui.log` | Streamlit 启动/访问日志 |

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
| `.web_ui.pid` | Streamlit 进程 PID |

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

### Streamlit 无法访问

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

# 运行单个测试类调试
python3.12 -m pytest tests/test_web_e2e.py::TestE2EWikiPage -v -s
```

## Bugfix 记录

前端相关 bugfix 记录在 `docs/bugfix/frontend/` 目录，格式参见 `docs/frontend/05-test-strategy.md`。

已记录：
- [FE-001](../bugfix/frontend/FE-001-h1-toc-id-attribute-assertion.md) — toc 扩展生成带 id 的 h1 标签
- [FE-002](../bugfix/frontend/FE-002-datetime-utcnow-deprecated.md) — datetime.utcnow() 废弃
