---
created_at: 2026-03-27
updated_at: 2026-04-07
doc_status: active
---

# Validation Route

## Required Checks

```bash
python3 -m py_compile agents_memory/services/integration.py tests/test_integration_service.py
python3 -m unittest tests.test_integration_service
python3 scripts/memory.py doctor .
```

## Task-Specific Checks

- 确认 `enable --dry-run` 分组输出保持不变
- 确认 `enable --full --dry-run --json` 仍返回结构化 preview payload

## Review Notes

- docs diff: 增加 `cmd_enable` 重构的 planning bundle
- code diff: 拆出 enable 校验、preview 渲染、profile 应用、full follow-up helper
- test diff: 无需新增测试，现有 focused integration tests 覆盖主行为

## Refactor Verification
- primary verification command: `amem doctor .`
- expected outcome: `agents_memory/services/integration.py::cmd_enable` is no longer listed in `refactor_watch`.
