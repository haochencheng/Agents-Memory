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

## Refactor Verification
- primary verification command: `amem doctor .`
- expected outcome: `agents_memory/services/integration.py::cmd_register` is no longer the first hotspot, or its issue list is smaller.

## Hotspot Snapshot
```json
{
  "identifier": "agents_memory/services/integration.py::cmd_register",
  "rank_token": "hotspot-1c511b0626bb",
  "relative_path": "agents_memory/services/integration.py",
  "function_name": "cmd_register",
  "qualified_name": "cmd_register",
  "line": 1477,
  "status": "WARN",
  "effective_lines": 56,
  "branches": 7,
  "nesting": 2,
  "local_vars": 14,
  "has_guiding_comment": true,
  "issues": [
    "lines=56>40",
    "branches=7>5",
    "locals=14>8"
  ],
  "score": 30
}
```
