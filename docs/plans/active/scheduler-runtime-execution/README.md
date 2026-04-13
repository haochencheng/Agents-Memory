---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution planning bundle

## Goal

把 `/scheduler` 从纯内存配置页升级成真正可执行的调度能力：

- 任务持久化到磁盘
- 服务启动后自动恢复
- 定时执行 `docs` / `profile` / `plan` 检查
- 把运行结果同时写入 `checks` 与 `workflow`

## Scope

- `agents_memory/services/scheduler.py`
- `agents_memory/web/api.py`
- `frontend/src/pages/dashboard/Scheduler.tsx`
- `frontend/src/pages/dashboard/Checks.tsx`
- `frontend/src/api/useScheduler.ts`

## Acceptance Snapshot

- API 重启后调度任务仍可读
- 到期任务会自动执行并产生检查记录
- Workflow 中可以看到 `scheduler_check` 记录
- Overview / Checks / Scheduler 页面能展示真实运行状态
