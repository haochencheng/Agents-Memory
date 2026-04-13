---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution Plan

## Change Set

1. 升级 scheduler 服务模型
   - 从平铺任务切到 `task_group + run_batch + run_step`
   - cron 校验与 next-run 计算
   - 任务组磁盘持久化与历史保留（每组 200 次）
   - 到期 / 手动执行 `docs` / `profile` / `plan`
2. 改造 API
   - 保留 `/api/scheduler/tasks` 兼容映射
   - 新增 `/api/scheduler/task-groups/*` 主接口
   - checks 从 batch/step 日志派生统一结果
3. 改造前端
   - Scheduler 列表页按任务组展示与过滤
   - Scheduler 详情页支持编辑、启停、立即执行、删除
   - 展示最近执行历史、step 明细、workflow/checks 入口
4. 补文档与自动化测试
   - API contract / runbook / planning bundle
   - scheduler service / web api / scheduler page / scheduler detail tests
