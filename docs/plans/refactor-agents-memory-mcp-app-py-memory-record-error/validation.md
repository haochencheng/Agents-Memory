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
- expected outcome: `agents_memory/mcp_app.py::memory_record_error` is no longer the first hotspot, or its issue list is smaller.

## Hotspot Snapshot
```json
{
  "identifier": "agents_memory/mcp_app.py::memory_record_error",
  "rank_token": "hotspot-27d26ab2550d",
  "relative_path": "agents_memory/mcp_app.py",
  "function_name": "memory_record_error",
  "qualified_name": "memory_record_error",
  "line": 271,
  "status": "WARN",
  "effective_lines": 45,
  "branches": 4,
  "nesting": 1,
  "local_vars": 9,
  "has_guiding_comment": false,
  "issues": [
    "lines=45>40",
    "locals=9>8",
    "branches=4",
    "missing_guiding_comment"
  ],
  "score": 22
}
```
