---
created_at: 2026-03-27
updated_at: 2026-04-07
doc_status: active
---

# Execution Plan

## Scope

- 影响模块：`agents_memory/services/integration.py`
- 影响命令：`amem enable`
- 影响文档：当前 planning bundle

## Design Notes

- 关键设计决策：拆出 `_run_enable_dry_run`、`_render_enable_preview`、`_apply_enable_profile`、`_run_enable_full_followup`，保持 `cmd_enable` 只做流程编排。
- 模块边界：preview 组装与 real apply 分离，full-mode follow-up 状态写回单独封装。
- 兼容性风险：stdout 文案和 onboarding-state 写回必须保持兼容。

## Change Set

- 代码改动：拆分 `cmd_enable` 和 `_preview_enable_actions` 的阶段逻辑。
- 文档改动：补回本次 refactor 的 planning bundle。
- 测试改动：复用现有 `tests.test_integration_service` 回归测试覆盖行为一致性。

## Refactor Execution
- Target hotspot: `agents_memory/services/integration.py::cmd_enable`
- Split validation, preview rendering, and full follow-up persistence before adding more behavior.
- Preserve behavior with focused integration tests.
- Re-run `amem doctor .` after the refactor and confirm the hotspot disappears.
