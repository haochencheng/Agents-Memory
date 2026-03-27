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
- expected outcome: `agents_memory/services/planning.py::init_refactor_bundle` is no longer the first hotspot, or its issue list is smaller.

## Hotspot Snapshot
```json
{
  "identifier": "agents_memory/services/planning.py::init_refactor_bundle",
  "rank_token": "hotspot-d43db02a2258",
  "relative_path": "agents_memory/services/planning.py",
  "function_name": "init_refactor_bundle",
  "qualified_name": "init_refactor_bundle",
  "line": 493,
  "status": "WARN",
  "effective_lines": 68,
  "branches": 7,
  "nesting": 3,
  "local_vars": 13,
  "has_guiding_comment": false,
  "issues": [
    "lines=68>40",
    "branches=7>5",
    "locals=13>8",
    "nesting=3",
    "missing_guiding_comment"
  ],
  "score": 32
}
```
