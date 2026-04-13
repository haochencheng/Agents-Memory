---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution planning bundle

## Goal

把 `/scheduler` 从“平铺 3 条子任务”的配置页升级成“逻辑任务组管理台 + 可执行 runtime”：

- 一个任务组绑定一个项目和一条 cron
- 内部固定执行 `docs` / `profile` / `plan`
- 支持编辑、启停、立即执行、删除
- 支持查看最近 200 次执行历史和每次 step 结果
- 把 batch / checks / workflow 统一串起来

## Scope

- `agents_memory/services/scheduler.py`
- `agents_memory/web/api.py`
- `frontend/src/pages/dashboard/Scheduler.tsx`
- `frontend/src/pages/dashboard/SchedulerDetail.tsx`
- `frontend/src/pages/dashboard/Checks.tsx`
- `frontend/src/api/useScheduler.ts`
- `frontend/src/test/SchedulerDetailPage.test.tsx`

## Acceptance Snapshot

- API 重启后任务组仍可读
- 到期任务组会自动执行并产生 batch / checks / workflow
- Scheduler 列表页支持过滤、失败视图和快捷操作
- Scheduler 详情页能展示最近执行历史、step 明细和 workflow/checks 入口
