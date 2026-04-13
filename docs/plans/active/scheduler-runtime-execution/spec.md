---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution Spec

## Acceptance Criteria

1. `POST /api/scheduler/tasks` 为已注册项目创建固定的 `docs` / `profile` / `plan` 三个调度任务。
2. 调度任务写入 `memory/scheduler_tasks.json`，重启 API 后仍然能从 `GET /api/scheduler/tasks` 读到。
3. Scheduler 后台循环会扫描到期任务并执行对应检查。
4. 每次检查执行都会追加到 `memory/check_runs.jsonl`。
5. 每次检查执行都会在 `memory/workflow_records/` 生成一条 `source_type=scheduler_check` 的 workflow 记录。
6. `GET /api/checks` 和 `GET /api/checks/summary` 返回真实运行结果，而不是空壳数据。
7. 前端 Scheduler / Checks / Overview 页面能消费新的响应结构。
