---
created_at: 2026-03-26
updated_at: 2026-03-27
doc_status: active
---

# Validation Route

## Required Checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile $(find agents_memory scripts -name '*.py' -print)
python3 scripts/memory.py docs-check .
python3 scripts/memory.py plan-check .
```

## Task-Specific Checks

- `python3 scripts/memory.py plan-init "planning governance gate" . --dry-run`
- `python3 scripts/memory.py plan-check docs/plans/planning-governance-gate`

## Review Notes

- docs diff: 新增 planning bundle，并把 `plan-check` 写入公开入口。
- code diff: validation registry 与 planning gate 逻辑扩展。
- test diff: 新增 `plan-check` 相关用例，并更新 docs command coverage。
