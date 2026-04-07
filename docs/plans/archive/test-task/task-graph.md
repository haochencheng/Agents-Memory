---
created_at: 2026-03-27
updated_at: 2026-04-07
doc_status: active
---

# Task Graph

## Work Items

1. 基础设施或模板改动
2. 核心代码改动
3. 测试改动
4. 文档改动
5. 收尾清理

## Dependencies

- 哪些任务必须先完成？
- 哪些任务可以并行？

## Exit Criteria

- 任务完成时必须满足哪些条件？

## Task Status
```json
{
  "task_name": "test task",
  "task_slug": "test-task",
  "bundle_path": "docs/plans/test-task",
  "status": "completed",
  "closed_at": "2026-03-27T07:04:33.491055+00:00",
  "validation_overall": "PARTIAL",
  "required_failures": 0,
  "recommended_warnings": 5,
  "sections": [
    {
      "name": "bundle_gate",
      "overall": "OK"
    },
    {
      "name": "docs",
      "overall": "OK"
    },
    {
      "name": "profile",
      "overall": "OK"
    },
    {
      "name": "planning",
      "overall": "OK"
    },
    {
      "name": "doctor",
      "overall": "PARTIAL"
    }
  ],
  "verify_command": "amem validate ."
}
```
