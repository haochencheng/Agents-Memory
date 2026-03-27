---
created_at: 2026-03-27
updated_at: 2026-03-27
doc_status: active
---

# Validation Route

## Required Checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile $(find agents_memory scripts -name '*.py' -print)
python3 scripts/memory.py docs-check .
```

## Task-Specific Checks

- 写下本任务额外需要跑的命令

## Review Notes

- docs diff:
- code diff:
- test diff:

## Close-Out Summary
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
