---
created_at: 2026-03-27
updated_at: 2026-04-07
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
- expected outcome: `agents_memory/services/profiles.py::_print_profile` is no longer the first hotspot, or its issue list is smaller.

## Hotspot Snapshot
```json
{
  "identifier": "agents_memory/services/profiles.py::_print_profile",
  "rank_token": "hotspot-5ae7cd31a053",
  "relative_path": "agents_memory/services/profiles.py",
  "function_name": "_print_profile",
  "qualified_name": "_print_profile",
  "line": 611,
  "status": "WARN",
  "effective_lines": 40,
  "branches": 11,
  "nesting": 3,
  "local_vars": 5,
  "has_guiding_comment": false,
  "issues": [
    "branches=11>5",
    "lines=40",
    "nesting=3",
    "missing_guiding_comment"
  ],
  "score": 13
}
```
