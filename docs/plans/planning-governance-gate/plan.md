# Execution Plan

## Scope

- 影响模块：`agents_memory/services/validation.py`、`agents_memory/commands/validation.py`
- 影响命令：`plan-check`
- 影响文档：`README.md`、`docs/getting-started.md`、`docs/ai-engineering-operating-system.md`、`llms.txt`

## Design Notes

- 关键设计决策：复用现有 validation 输出风格，让 `plan-check` 和 `docs-check` / `profile-check` 保持一致。
- 模块边界：planning scaffold 继续留在 `services/planning.py`；planning gate 留在 `services/validation.py`。
- 兼容性风险：当前如果仓库还没有 `docs/plans/`，`plan-check` 返回 `PARTIAL` 而不是 `FAIL`，避免强行阻断未接入仓库。

## Change Set

- 代码改动：新增 `plan-check` CLI 接线与 planning bundle 校验逻辑。
- 文档改动：把 `plan-check` 纳入 README、getting-started、架构文档和 `llms.txt`。
- 测试改动：补 `test_planning_service.py` 和 `test_docs_check.py` 的 coverage。
