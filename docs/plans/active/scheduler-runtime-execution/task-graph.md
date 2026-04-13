---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution Task Graph

## Work Items

- [x] 把 scheduler task store 从内存迁到 `memory/scheduler_tasks.json`
- [x] 增加 cron 校验和下次执行时间计算
- [x] 增加后台 runtime，服务启动自动恢复
- [x] 调用现有 docs/profile/plan 检查能力
- [x] 把检查结果写入 `memory/check_runs.jsonl`
- [x] 把检查结果写入 workflow record
- [x] API 返回真实 scheduler / checks 数据
- [x] 前端页面接新数据结构
- [x] 增加 service/api/frontend tests

## Exit Criteria

- [x] `.venv/bin/python -m unittest tests.test_scheduler_service tests.test_web_api -v`
- [x] `npm exec vitest run src/test/SchedulerPage.test.tsx src/test/ChecksPage.test.tsx`
- [x] `npm exec tsc --noEmit`
