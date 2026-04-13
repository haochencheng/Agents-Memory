---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution Validation

## Required Checks

- `python3 -m py_compile agents_memory/services/scheduler.py agents_memory/services/workflow_records.py agents_memory/web/api.py agents_memory/web/models.py tests/test_scheduler_service.py tests/test_web_api.py`
- `.venv/bin/python -m unittest tests.test_scheduler_service tests.test_web_api -v`
- `npm exec vitest run src/test/SchedulerPage.test.tsx src/test/SchedulerDetailPage.test.tsx src/test/ChecksPage.test.tsx`
- `npm exec tsc --noEmit`

## Task-Specific Checks

- [x] 创建任务组后，`memory/scheduler_tasks.json` 会写入 `task_groups`
- [x] API 重载后 `/api/scheduler/task-groups` 仍能读回已创建任务组
- [x] 到期任务组会把 batch 写入 `memory/scheduler_runs.jsonl`
- [x] 到期任务会把结果写入 `memory/check_runs.jsonl`
- [x] 到期任务会在 workflow 中生成 `source_type=scheduler_check`
- [x] 任务组详情页能展示最近执行历史、step 结果和 workflow/checks 入口
