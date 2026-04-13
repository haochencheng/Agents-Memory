---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution Validation

## Required Checks

- `python3 -m py_compile agents_memory/services/scheduler.py agents_memory/services/workflow_records.py agents_memory/web/api.py agents_memory/web/models.py tests/test_scheduler_service.py tests/test_web_api.py`
- `.venv/bin/python -m unittest tests.test_scheduler_service tests.test_web_api -v`
- `npm exec vitest run src/test/SchedulerPage.test.tsx src/test/ChecksPage.test.tsx`
- `npm exec tsc --noEmit`

## Task-Specific Checks

- [x] 创建调度任务后，`memory/scheduler_tasks.json` 会写入 3 条 `docs/profile/plan`
- [x] API 重载后 `/api/scheduler/tasks` 仍能读回已创建任务
- [x] 到期任务会把结果写入 `memory/check_runs.jsonl`
- [x] 到期任务会在 workflow 中生成 `source_type=scheduler_check`
