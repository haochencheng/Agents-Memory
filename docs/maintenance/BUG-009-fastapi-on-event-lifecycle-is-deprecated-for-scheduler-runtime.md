---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# BUG-009 FastAPI on_event Lifecycle Is Deprecated For Scheduler Runtime

## Summary

在给 Scheduler 增加启动恢复和后台执行后，`tests.test_web_api` 开始稳定输出 FastAPI `@app.on_event("startup" / "shutdown")` 的弃用警告。

## Trigger

- 运行 `.venv/bin/python -m unittest tests.test_scheduler_service tests.test_web_api -v`
- FastAPI / Starlette 新版本对 `on_event` 给出 `DeprecationWarning`

## Root Cause

Scheduler runtime 是新加的生命周期行为，但仍然挂在旧的 `on_event` API 上；当前 FastAPI 推荐统一改用 `lifespan`。

## Fix

1. 用 `asynccontextmanager` 定义应用 `lifespan`
2. 在 `lifespan` 里启动 Scheduler runtime
3. 在退出时显式停止 runtime，避免后台任务泄漏

## Rule

新增应用级启动/关闭逻辑时，优先使用 FastAPI `lifespan`，不要继续往 `@app.on_event` 上堆新行为。
