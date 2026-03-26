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
- expected outcome: `agents_memory/services/integration.py::cmd_sync` is no longer the first hotspot, or its issue list is smaller.

## Hotspot Snapshot
```json
{
  "identifier": "agents_memory/services/integration.py::cmd_sync",
  "rank_token": "hotspot-b963d3c1470f",
  "relative_path": "agents_memory/services/integration.py",
  "function_name": "cmd_sync",
  "qualified_name": "cmd_sync",
  "line": 208,
  "status": "WARN",
  "effective_lines": 57,
  "branches": 11,
  "nesting": 3,
  "local_vars": 15,
  "has_guiding_comment": true,
  "issues": [
    "lines=57>40",
    "branches=11>5",
    "locals=15>8",
    "nesting=3"
  ],
  "score": 31
}
```
