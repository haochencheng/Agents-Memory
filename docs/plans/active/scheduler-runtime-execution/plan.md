---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# Scheduler Runtime Execution Plan

## Change Set

1. 新增 `agents_memory/services/scheduler.py`
   - cron 校验与 next-run 计算
   - 调度任务磁盘持久化
   - checks 运行记录存储
   - 到期执行 `docs` / `profile` / `plan`
2. 改造 `agents_memory/web/api.py`
   - lifespan 启动/停止调度 runtime
   - scheduler/checks 端点接真实数据
3. 改造前端
   - Scheduler 展示持久化任务、上次/下次运行结果
   - Checks 消费结构化响应
   - Overview 读取真实 summary
4. 补文档与自动化测试
   - API contract
   - runbook
   - service/api/frontend tests
