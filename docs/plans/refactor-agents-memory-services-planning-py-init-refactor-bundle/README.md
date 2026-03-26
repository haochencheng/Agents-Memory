# Refactor hotspot: agents_memory/services/planning.py::init_refactor_bundle

这是当前任务的 planning bundle。

建议使用顺序：

1. 先写 `spec.md`
2. 再补 `plan.md`
3. 再确认 `task-graph.md`
4. 最后在 `validation.md` 里写最小验证路线

## Refactor Hotspot
- hotspot: `agents_memory/services/planning.py::init_refactor_bundle`
- hotspot token: `hotspot-d43db02a2258`
- current rank index: `1`
- line: `493`
- status: `WARN`
- issues: `lines=68>40, branches=7>5, locals=13>8, nesting=3, missing_guiding_comment`
- bundle entry command: `amem refactor-bundle . --token hotspot-d43db02a2258`
- verify with: `amem doctor .`
