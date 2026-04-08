---
created_at: 2026-04-07
updated_at: 2026-04-08
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

- `python3.12 -m unittest discover -s tests -p 'test_ingest_service.py' -v`
- `python3.12 scripts/memory.py doctor .`
- `python3.12 scripts/memory.py plan-check .`

## Review Notes

- docs diff: 计划分类增加 `deprecated/`，记录 `BUG-004`
- code diff: `cmd_ingest` 拆分 helper，ingest log 改为 timezone-aware UTC
- test diff: `tests/test_ingest_service.py` 新增 helper 单测

## Refactor Verification
- primary verification command: `amem doctor .`
- expected outcome: `agents_memory/services/ingest.py::cmd_ingest` 不再出现在 hotspot 列表中。

## Hotspot Snapshot
```json
{
  "identifier": "agents_memory/services/ingest.py::cmd_ingest",
  "rank_token": "hotspot-0e832c6afc58",
  "relative_path": "agents_memory/services/ingest.py",
  "function_name": "cmd_ingest",
  "qualified_name": "cmd_ingest",
  "line": 312,
  "status": "WARN",
  "effective_lines": 79,
  "branches": 16,
  "nesting": 7,
  "local_vars": 11,
  "has_guiding_comment": false,
  "issues": [
    "lines=79>40",
    "branches=16>5",
    "nesting=7>=4",
    "locals=11>8",
    "missing_guiding_comment"
  ],
  "score": 41
}
```
