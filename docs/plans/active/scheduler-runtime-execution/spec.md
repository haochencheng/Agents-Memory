---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution Spec

## Acceptance Criteria

1. `POST /api/scheduler/task-groups` 为已注册项目创建一个逻辑任务组，内部固定包含 `docs` / `profile` / `plan` 三个检查 step。
2. 任务组写入 `memory/scheduler_tasks.json`，重启 API 后仍然能从 `GET /api/scheduler/task-groups` 读到。
3. Scheduler 后台循环会扫描到期任务组并执行对应 batch。
4. 每次执行会把 batch + steps 追加到 `memory/scheduler_runs.jsonl`，并兼容派生 `checks` 结果。
5. 每个 step 执行都会在 `memory/workflow_records/` 生成一条 `source_type=scheduler_check` 的 workflow 记录。
6. `GET /api/checks` 和 `GET /api/checks/summary` 返回真实运行结果，而不是空壳数据。
7. 前端 Scheduler 列表页和详情页能消费新的任务组 / 批次响应结构。
