---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution Task Graph

## Work Items

- [x] 把 scheduler 主模型升级成 `task_group + run_batch + run_step`
- [x] 保留 `/api/scheduler/tasks` 兼容映射
- [x] 新增 `/api/scheduler/task-groups/*` 主接口
- [x] 增加 cron 校验和下次执行时间计算
- [x] 增加后台 runtime，服务启动自动恢复
- [x] 调用现有 docs/profile/plan 检查能力
- [x] 把 batch 写入 `memory/scheduler_runs.jsonl`
- [x] 把 checks 结果写入 `memory/check_runs.jsonl`
- [x] 把检查结果写入 workflow record
- [x] 前端提供任务组列表页 + 详情页
- [x] 增加 service/api/frontend tests

## Exit Criteria

- [x] `.venv/bin/python -m unittest tests.test_scheduler_service tests.test_web_api -v`
- [x] `npm exec vitest run src/test/SchedulerPage.test.tsx src/test/SchedulerDetailPage.test.tsx src/test/ChecksPage.test.tsx`
- [x] `npm exec tsc --noEmit`
