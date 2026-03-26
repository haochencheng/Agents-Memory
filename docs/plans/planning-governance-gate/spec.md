# Spec

## Task

planning governance gate

## Problem

- `plan-init` 已经能生成 planning bundle，但系统还无法校验这些工件是否存在、是否齐备、是否保留最小治理语义。
- 这导致 Planning 层仍偏向“模板能力”，还没有进入 Shared Engineering Brain 的质量门禁。

## Goal

- 新增 `plan-check` 命令，校验 `docs/plans/` 下 bundle 的完整性和关键语义。
- 让 README、`llms.txt`、getting-started 和架构文档把 `plan-check` 作为正式能力公开出来。
- 用仓库自己的 `docs/plans/planning-governance-gate/` 作为 dogfooding 样本，让系统开始治理自己的 planning 工件。

## Non-Goals

- 这次不实现 planning bundle 的双向同步或 merge 策略。
- 这次不要求所有仓库必须已有 planning bundle 才能通过 `docs-check`。
- 这次不做 planning 语义的深度 lint，只做第一版结构与关键章节校验。

## Acceptance Criteria

- [x] `python3 scripts/memory.py plan-check .` 可以输出 planning bundle 校验结果。
- [x] 缺失 `spec.md` / `task-graph.md` / `validation.md` 等关键文件时会报 `FAIL`。
- [x] 健康的 planning bundle 可以通过命令和测试验证。
- [x] 本次改动同步更新 docs / code / tests。
