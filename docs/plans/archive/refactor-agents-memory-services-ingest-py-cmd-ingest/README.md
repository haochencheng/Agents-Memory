---
created_at: 2026-04-07
updated_at: 2026-04-08
doc_status: active
---

# Refactor hotspot: agents_memory/services/ingest.py::cmd_ingest

这是当前任务的 planning bundle。

建议使用顺序：

1. 先写 `spec.md`
2. 再补 `plan.md`
3. 再确认 `task-graph.md`
4. 最后在 `validation.md` 里写最小验证路线

## Refactor Hotspot
- hotspot: `agents_memory/services/ingest.py::cmd_ingest`
- hotspot token: `hotspot-0e832c6afc58`
- previous rank index: `1`
- line: `312`
- status: `RESOLVED`
- previous issues: `lines=79>40, branches=16>5, nesting=7>=4, locals=11>8, missing_guiding_comment`
- bundle entry command: `amem refactor-bundle . --token hotspot-0e832c6afc58`
- verify with: `amem doctor .`

## Outcome

- `cmd_ingest` 已拆分为更小的验证和执行 helper
- 行为保持不变，目标测试全部通过
- `amem doctor .` 中该 hotspot 已不再出现，bundle 已归档
